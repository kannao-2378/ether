#!/usr/bin/env python3
"""Audit local web references and media before publishing."""

from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".html", ".css", ".js", ".json"}
MEDIA_SUFFIXES = {".avif", ".gif", ".jpeg", ".jpg", ".mp4", ".png", ".svg", ".webm", ".webp"}
SKIP_PREFIXES = ("#", "data:", "http:", "https:", "mailto:", "tel:", "javascript:", "blob:")
ATTR_RE = re.compile(r"\b(?:href|src|poster)\s*=\s*([\"'])(.*?)\1", re.I)
SRCSET_RE = re.compile(r"\bsrcset\s*=\s*([\"'])(.*?)\1", re.I)
CSS_URL_RE = re.compile(r"url\(\s*([\"']?)(.*?)\1\s*\)", re.I)
JS_REF_RE = re.compile(r"\b(?:fetch|import)\s*\(\s*([\"'])(.*?)\1", re.I)
JS_IMPORT_RE = re.compile(r"\b(?:import|export)\s+(?:[^;]*?\s+from\s+)?([\"'])(.*?)\1", re.I)


def display(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def reference_base(source: Path) -> Path:
    # QREATE section fragments are injected into qreate/index.html; browser URL
    # resolution therefore uses the case root, not the fragment's directory.
    parts = source.relative_to(ROOT).parts
    if source.suffix.lower() == ".html" and len(parts) >= 6 and parts[:5] == ("portfolio", "works", "brand-cases", "qreate", "sections"):
        return ROOT / "portfolio" / "works" / "brand-cases" / "qreate"
    return source.parent


def resolve_local(source: Path, raw: str, base: Path | None = None) -> Path | None:
    raw = raw.strip()
    if not raw or raw.lower().startswith(SKIP_PREFIXES) or raw.startswith("/api/") or "{{" in raw:
        return None
    path = unquote(urlsplit(raw).path)
    if not path or path == "/":
        return None
    target = ROOT / path.lstrip("/") if path.startswith("/") else (base or reference_base(source)) / path
    return target.resolve()


def iter_references(source: Path, text: str):
    suffix = source.suffix.lower()
    if suffix == ".html":
        for match in ATTR_RE.finditer(text):
            yield match.group(2), text.count("\n", 0, match.start()) + 1, None
        for match in SRCSET_RE.finditer(text):
            for item in match.group(2).split(","):
                yield item.strip().split()[0], text.count("\n", 0, match.start()) + 1, None
    if suffix in {".html", ".css"}:
        for match in CSS_URL_RE.finditer(text):
            yield match.group(2), text.count("\n", 0, match.start()) + 1, None
    if suffix == ".js":
        for match in JS_REF_RE.finditer(text):
            fetch_base = None
            if "qreate" in source.parts:
                fetch_base = ROOT / "portfolio" / "works" / "brand-cases" / "qreate"
            yield match.group(2), text.count("\n", 0, match.start()) + 1, fetch_base
        for match in JS_IMPORT_RE.finditer(text):
            yield match.group(2), text.count("\n", 0, match.start()) + 1, source.parent


def main() -> int:
    missing: list[tuple[Path, int, str, Path]] = []
    text_files = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES and ".git" not in p.parts and "_local-archive" not in p.parts]
    for source in text_files:
        try:
            text = source.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for raw, line, base in iter_references(source, text):
            target = resolve_local(source, raw, base)
            if target is not None and not target.exists():
                missing.append((source, line, raw, target))

    media = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower() in MEDIA_SUFFIXES and ".git" not in p.parts and "_local-archive" not in p.parts]
    empty = [p for p in media if p.stat().st_size == 0]
    oversized = [p for p in media if p.stat().st_size >= 100 * 1024 * 1024]
    case_map: dict[str, list[Path]] = {}
    for path in ROOT.rglob("*"):
        if path.is_file() and ".git" not in path.parts and "_local-archive" not in path.parts:
            case_map.setdefault(display(path).lower(), []).append(path)
    collisions = [paths for paths in case_map.values() if len(paths) > 1]

    ignored: list[str] = []
    if media:
        check = subprocess.run(
            ["git", "check-ignore", "--stdin"], cwd=ROOT, input="\n".join(display(p) for p in media),
            text=True, capture_output=True, check=False,
        )
        ignored = [line for line in check.stdout.splitlines() if line]

    counts = Counter(p.suffix.lower() for p in media)
    total_bytes = sum(p.stat().st_size for p in media)
    print(f"Scanned {len(text_files)} text files and {len(media)} media files ({total_bytes / 1024 / 1024:.1f} MiB).")
    print("Media:", ", ".join(f"{ext}={count}" for ext, count in sorted(counts.items())) or "none")
    if missing:
        print("\nMissing local references:")
        for source, line, raw, target in missing:
            print(f"  {display(source)}:{line}: {raw} -> {display(target)}")
    if empty:
        print("\nEmpty media files:")
        for path in empty:
            print(f"  {display(path)}")
    if oversized:
        print("\nMedia files at or above GitHub's 100 MiB limit:")
        for path in oversized:
            print(f"  {display(path)} ({path.stat().st_size / 1024 / 1024:.1f} MiB)")
    if collisions:
        print("\nCase-insensitive path collisions:")
        for paths in collisions:
            print("  " + " | ".join(display(p) for p in paths))
    if ignored:
        print("\nMedia ignored by Git:")
        for path in ignored:
            print(f"  {path}")

    problems = len(missing) + len(empty) + len(oversized) + len(collisions) + len(ignored)
    if problems:
        print(f"\nFAIL: {problems} publish-blocking issue(s) found.")
        return 1
    print("\nPASS: local references and media are publish-safe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
