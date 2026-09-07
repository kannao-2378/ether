from __future__ import annotations

import json
import html
import hashlib
import hmac
import mimetypes
import os
import re
import secrets
import sys
import tempfile
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parent
PORTFOLIO_DIR = ROOT / "portfolio"
HUB_CONTENT_FILE = ROOT / "kan" / "content.json"
AUTH_FILE = ROOT / ".local-data" / "admin-auth.json"
CONTENT_FILE = PORTFOLIO_DIR / "content.json"
PORTFOLIO_INDEX_FILE = PORTFOLIO_DIR / "index.html"
UPLOAD_DIR = PORTFOLIO_DIR / "uploads"
QREATE_DIR = PORTFOLIO_DIR / "works" / "brand-cases" / "qreate"
QREATE_CONFIG_FILE = QREATE_DIR / "config" / "site-config.json"
QREATE_MOTION_DIR = QREATE_DIR / "assets" / "modules-251-390"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_JSON_BYTES = 512 * 1024
ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
KEY_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9:_/.-]{0,239}$")
SLOT_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9-]{0,100}$")
PAGE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9-]{0,120}$")
ADMIN_COOKIE = "kannao_admin"
ADMIN_SESSIONS: dict[str, float] = {}
ADMIN_SESSION_SECONDS = 12 * 60 * 60


def sync_home_initial_content(page: dict[str, dict[str, str]]) -> None:
    """Keep the home page's first paint aligned with its saved editor state."""
    if not PORTFOLIO_INDEX_FILE.is_file():
        return
    source = PORTFOLIO_INDEX_FILE.read_text(encoding="utf-8")

    for key, value in page.get("texts", {}).items():
        pattern = re.compile(
            r'(<(?P<tag>[a-zA-Z][\w:-]*)\b[^>]*\bdata-edit="'
            + re.escape(key)
            + r'"[^>]*>)(?P<text>[^<]*)(</(?P=tag)>)'
        )
        source = pattern.sub(
            lambda match: match.group(1) + html.escape(value, quote=False) + match.group(4),
            source,
            count=1,
        )

    for slot, url in page.get("images", {}).items():
        tag_pattern = re.compile(
            r'<[^>]*\bdata-image-slot="' + re.escape(slot) + r'"[^>]*>', re.IGNORECASE
        )

        def update_image_tag(match: re.Match[str]) -> str:
            tag = match.group(0)
            class_match = re.search(r'class="([^"]*)"', tag)
            if class_match and "has-uploaded-image" not in class_match.group(1).split():
                classes = class_match.group(1) + " has-uploaded-image"
                tag = tag[:class_match.start(1)] + classes + tag[class_match.end(1):]
            image_style = "background-image: url('" + html.escape(url, quote=True) + "')"
            style_match = re.search(r'style="([^"]*)"', tag)
            if style_match:
                styles = re.sub(
                    r"background-image\s*:\s*url\([^)]*\)\s*;?\s*",
                    "",
                    style_match.group(1),
                ).strip("; ")
                styles = (styles + "; " if styles else "") + image_style
                tag = tag[:style_match.start(1)] + styles + tag[style_match.end(1):]
            else:
                tag = tag[:-1] + ' style="' + image_style + '">'
            return tag

        source = tag_pattern.sub(update_image_tag, source, count=1)

        if slot == "poster":
            source = re.sub(
                r'(<link\s+rel="preload"\s+as="image"\s+href=")[^"]+("[^>]*>)',
                lambda match: match.group(1) + html.escape(url, quote=True) + match.group(2),
                source,
                count=1,
            )

    atomic_write(PORTFOLIO_INDEX_FILE, source.encode("utf-8"))


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # mkstemp creates files as 0600. That is correct for authentication data,
    # but replacing a public HTML/JSON/media file with that mode prevents the
    # Nginx www-data user from reading it and turns the page into a 403.
    target_mode = 0o600 if AUTH_FILE.parent in path.parents else 0o644
    handle, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as temp_file:
            temp_file.write(data)
        os.chmod(temp_name, target_mode)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


class PortfolioHandler(SimpleHTTPRequestHandler):
    server_version = "PortfolioLocalServer/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK, cookie: str | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def admin_session_token(self) -> str:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookie.get(ADMIN_COOKIE)
        return morsel.value if morsel else ""

    def is_admin_authenticated(self) -> bool:
        token = self.admin_session_token()
        expires = ADMIN_SESSIONS.get(token, 0)
        if expires <= __import__("time").time():
            ADMIN_SESSIONS.pop(token, None)
            return False
        return True

    def create_admin_session(self) -> str:
        token = secrets.token_urlsafe(32)
        ADMIN_SESSIONS[token] = __import__("time").time() + ADMIN_SESSION_SECONDS
        secure = "; Secure" if self.headers.get("X-Forwarded-Proto", "").lower() == "https" else ""
        return f"{ADMIN_COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={ADMIN_SESSION_SECONDS}{secure}"

    def read_admin_password(self) -> str:
        payload = json.loads(self.read_body(16 * 1024).decode("utf-8"))
        password = payload.get("password", "") if isinstance(payload, dict) else ""
        if not isinstance(password, str) or len(password) < 8:
            raise ValueError("密码至少需要8个字符")
        return password

    @staticmethod
    def password_digest(password: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000).hex()

    def read_body(self, limit: int) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Invalid Content-Length") from error
        if length <= 0 or length > limit:
            raise ValueError("Request body is empty or too large")
        return self.rfile.read(length)

    def do_POST(self) -> None:
        route = urlparse(self.path)
        try:
            if route.path == "/api/admin/setup":
                if AUTH_FILE.exists():
                    self.send_json({"error": "管理密码已经设置"}, HTTPStatus.CONFLICT)
                    return
                password = self.read_admin_password()
                salt = secrets.token_bytes(24)
                record = {"salt": salt.hex(), "digest": self.password_digest(password, salt)}
                atomic_write(AUTH_FILE, (json.dumps(record, indent=2) + "\n").encode("utf-8"))
                self.send_json({"ok": True}, cookie=self.create_admin_session())
                return
            if route.path == "/api/admin/login":
                if not AUTH_FILE.exists():
                    self.send_json({"error": "请先设置管理密码"}, HTTPStatus.CONFLICT)
                    return
                password = self.read_admin_password()
                record = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
                expected = record.get("digest", "")
                actual = self.password_digest(password, bytes.fromhex(record.get("salt", "")))
                if not hmac.compare_digest(expected, actual):
                    self.send_json({"error": "密码错误"}, HTTPStatus.UNAUTHORIZED)
                    return
                self.send_json({"ok": True}, cookie=self.create_admin_session())
                return
            if route.path == "/api/admin/logout":
                ADMIN_SESSIONS.pop(self.admin_session_token(), None)
                self.send_json({"ok": True}, cookie=f"{ADMIN_COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0")
                return
            protected = {
                "/api/hub/content", "/api/portfolio/content", "/api/portfolio/upload",
                "/api/site-config", "/api/motion-cases/upload", "/api/motion-cases/card"
            }
            if route.path in protected and not self.is_admin_authenticated():
                self.send_json({"error": "请先登录后台"}, HTTPStatus.UNAUTHORIZED)
                return
            if route.path == "/api/hub/content":
                self.save_hub_content()
                return
            if route.path == "/api/portfolio/content":
                self.save_content()
                return
            if route.path == "/api/portfolio/upload":
                self.save_upload(parse_qs(route.query))
                return
            if route.path == "/api/site-config":
                self.save_qreate_config()
                return
            if route.path == "/api/motion-cases/upload":
                self.save_qreate_motion_upload()
                return
            if route.path == "/api/motion-cases/card":
                self.add_qreate_motion_card()
                return
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except ValueError as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception as error:
            self.log_error("POST failed: %s", error)
            self.send_json({"error": "The local server could not save this change."}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_DELETE(self) -> None:
        route = urlparse(self.path)
        if not self.is_admin_authenticated():
            self.send_json({"error": "请先登录后台"}, HTTPStatus.UNAUTHORIZED)
            return
        if route.path != "/api/motion-cases/card":
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            index = int(parse_qs(route.query).get("index", [""])[0])
            config = json.loads(QREATE_CONFIG_FILE.read_text(encoding="utf-8"))
            cards = config["modules"]["14-motion-cases"]["layout"]["cards"]
            if index < 0 or index >= len(cards):
                raise ValueError("Invalid card index")
            cards.pop(index)
            atomic_write(QREATE_CONFIG_FILE, (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            self.send_json({"ok": True, "cards": cards})
        except (ValueError, KeyError, TypeError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def do_GET(self) -> None:
        route = urlparse(self.path)
        if route.path == "/api/admin/session":
            self.send_json({"authenticated": self.is_admin_authenticated(), "needsSetup": not AUTH_FILE.exists()})
            return
        if route.path == "/api/site-config":
            self.send_json({"ok": True, "mode": "local", "path": "config/site-config.json"})
            return
        super().do_GET()

    def do_PATCH(self) -> None:
        route = urlparse(self.path)
        if not self.is_admin_authenticated():
            self.send_json({"error": "请先登录后台"}, HTTPStatus.UNAUTHORIZED)
            return
        if route.path != "/api/preview-size":
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            preview = json.loads(self.read_body(16 * 1024).decode("utf-8"))
            width = round(float(preview.get("width", 0)))
            height = round(float(preview.get("height", 0)))
            if not 320 <= width <= 1920 or not 420 <= height <= 1200:
                raise ValueError("Preview size is outside the allowed range")
            config = json.loads(QREATE_CONFIG_FILE.read_text(encoding="utf-8"))
            config["preview"] = {"width": width, "height": height}
            atomic_write(QREATE_CONFIG_FILE, (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            self.send_json({"ok": True, "preview": config["preview"]})
        except ValueError as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def save_qreate_config(self) -> None:
        if "application/json" not in self.headers.get("Content-Type", ""):
            raise ValueError("Content must be JSON")
        payload = json.loads(self.read_body(MAX_JSON_BYTES).decode("utf-8"))
        modules = payload.get("modules") if isinstance(payload, dict) else None
        required = {"01-navigation", "02-hero", "05-case-showcase", "09-brand-method", "15-contact"}
        if not isinstance(modules, dict) or not required.issubset(modules):
            raise ValueError("Invalid QREATE configuration")
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
        atomic_write(QREATE_CONFIG_FILE, data)
        self.send_json({"ok": True, "mode": "local", "path": "config/site-config.json"})

    def save_hub_content(self) -> None:
        if "application/json" not in self.headers.get("Content-Type", ""):
            raise ValueError("Content must be JSON")
        payload = json.loads(self.read_body(MAX_JSON_BYTES).decode("utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("modules"), list):
            raise ValueError("Hub content is invalid")
        clean = {}
        for key in ("siteTitle", "metaDescription", "navRole", "navContact", "heroEyebrow", "heroTitle", "heroSubtitle", "directoryTitle", "directorySubtitle"):
            value = payload.get(key, "")
            clean[key] = str(value).strip()[:5000]
        clean["typography"] = {}
        typography = payload.get("typography", {})
        if isinstance(typography, dict):
            for key, value in typography.items():
                if not isinstance(value, dict):
                    continue
                size = max(8, min(200, int(value.get("size", 16))))
                weight = max(100, min(900, int(value.get("weight", 400))))
                clean["typography"][str(key)[:80]] = {"size": size, "weight": weight}
        clean_modules = []
        for index, item in enumerate(payload["modules"][:40]):
            if not isinstance(item, dict):
                continue
            module_id = re.sub(r"[^a-zA-Z0-9_-]", "-", str(item.get("id", f"module-{index + 1}")))[:80]
            clean_modules.append({
                "id": module_id or f"module-{index + 1}",
                "title": str(item.get("title", "未命名入口"))[:200],
                "subtitle": str(item.get("subtitle", ""))[:300],
                "href": str(item.get("href", ""))[:500],
                "enabled": item.get("enabled") is not False,
                "kind": "portfolio-poster" if item.get("kind") == "portfolio-poster" else "number"
            })
        clean["modules"] = clean_modules
        atomic_write(HUB_CONTENT_FILE, (json.dumps(clean, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        self.send_json({"ok": True})

    def save_qreate_motion_upload(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            raise ValueError("Upload must use multipart/form-data")
        body = self.read_body(50 * 1024 * 1024)
        message = BytesParser(policy=policy.default).parsebytes(
            ("Content-Type: " + content_type + "\r\nMIME-Version: 1.0\r\n\r\n").encode("utf-8") + body
        )
        file_part = next((part for part in message.iter_attachments() if part.get_filename()), None)
        if file_part is None:
            raise ValueError("No upload file was found")
        extension = Path(file_part.get_filename() or "").suffix.lower()
        if extension not in {".gif", ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".svg"}:
            raise ValueError("Unsupported QREATE media type")
        QREATE_MOTION_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{secrets.token_hex(8)}{extension}"
        atomic_write(QREATE_MOTION_DIR / filename, file_part.get_payload(decode=True) or b"")
        self.send_json({"ok": True, "path": f"assets/modules-251-390/{filename}", "filename": filename})

    def add_qreate_motion_card(self) -> None:
        card = json.loads(self.read_body(16 * 1024).decode("utf-8"))
        if not isinstance(card, dict) or not str(card.get("src", "")).startswith("assets/modules-251-390/"):
            raise ValueError("Invalid QREATE card")
        config = json.loads(QREATE_CONFIG_FILE.read_text(encoding="utf-8"))
        layout = config["modules"]["14-motion-cases"].setdefault("layout", {})
        cards = layout.setdefault("cards", [])
        cards.append({
            "src": str(card["src"]), "alt": str(card.get("alt", "")),
            "caption": str(card.get("caption", "")), "description": str(card.get("description", "")),
            "sizeMode": str(card.get("sizeMode", "fixed")), "materialScale": float(card.get("materialScale", 1)),
            "cardWidth": card.get("cardWidth"), "cardHeight": card.get("cardHeight"),
            "offsetX": float(card.get("offsetX", 0)), "offsetY": float(card.get("offsetY", 0))
        })
        atomic_write(QREATE_CONFIG_FILE, (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        self.send_json({"ok": True, "card": cards[-1]})

    def save_content(self) -> None:
        if "application/json" not in self.headers.get("Content-Type", ""):
            raise ValueError("Content must be JSON")
        payload = json.loads(self.read_body(MAX_JSON_BYTES).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Invalid content data")

        pages = payload.get("pages", {})
        if not isinstance(pages, dict):
            raise ValueError("Invalid page content data")

        clean_pages = {}
        for page_key, page_value in pages.items():
            if not PAGE_RE.fullmatch(str(page_key)) or not isinstance(page_value, dict):
                continue
            texts = page_value.get("texts", {})
            images = page_value.get("images", {})
            if not isinstance(texts, dict) or not isinstance(images, dict):
                continue
            clean_texts = {
                str(key)[:240]: value.strip()[:5000]
                for key, value in texts.items()
                if KEY_RE.fullmatch(str(key)) and isinstance(value, str)
            }
            clean_images = {
                str(key): value[:300]
                for key, value in images.items()
                if SLOT_RE.fullmatch(str(key)) and isinstance(value, str)
                and value.startswith("/portfolio/uploads/")
            }
            clean_pages[str(page_key)] = {"texts": clean_texts, "images": clean_images}

        data = json.dumps({"pages": clean_pages}, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
        atomic_write(CONTENT_FILE, data)
        if "home" in clean_pages:
            sync_home_initial_content(clean_pages["home"])
        self.send_json({"ok": True})

    def save_upload(self, query: dict[str, list[str]]) -> None:
        page = query.get("page", [""])[0]
        slot = query.get("slot", [""])[0]
        if not PAGE_RE.fullmatch(page) or not SLOT_RE.fullmatch(slot):
            raise ValueError("Unknown image position")

        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].lower()
        extension = ALLOWED_TYPES.get(content_type)
        if not extension:
            filename = unquote(self.headers.get("X-Filename", ""))
            guessed_type, _ = mimetypes.guess_type(filename)
            extension = ALLOWED_TYPES.get(guessed_type or "")
        if not extension:
            raise ValueError("Please choose a JPG, PNG, WebP, or GIF image")

        body = self.read_body(MAX_UPLOAD_BYTES)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        file_stem = page + "--" + slot
        for old_file in UPLOAD_DIR.glob(file_stem + ".*"):
            if old_file.is_file() and old_file.name != ".gitkeep":
                old_file.unlink()

        target = UPLOAD_DIR / (file_stem + extension)
        atomic_write(target, body)
        self.send_json({"ok": True, "url": "/portfolio/uploads/" + target.name})

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = ThreadingHTTPServer(("127.0.0.1", port), PortfolioHandler)
    print(f"Website server running at http://localhost:{port}/kan/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
