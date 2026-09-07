(function () {
  "use strict";
  var adminPreview = new URLSearchParams(location.search).get("portfolio-admin") === "1";
  document.body.classList.toggle("portfolio-admin-preview", adminPreview);
  var root = "/portfolio/";
  var relative = location.pathname.indexOf(root) === 0 ? location.pathname.slice(root.length) : "";
  var pageKey = (relative.replace(/\/?index\.html$/, "").replace(/^\/+|\/+$/g, "") || "home").replace(/[^a-zA-Z0-9/_-]+/g, "-").replace(/\//g, "--").slice(0, 120);
  var documentState = { pages: {} };
  var pageState = { texts: {}, images: {} };
  var editing = false;
  var activeImage = null;
  var updateKey = "portfolio-content-updated";

  function announceUpdate() {
    try { localStorage.setItem(updateKey, String(Date.now())); } catch (error) { /* Storage may be unavailable. */ }
  }

  window.addEventListener("storage", function (event) {
    if (event.key === updateKey && !editing && !adminPreview) location.reload();
  });

  function elementPath(element) {
    var parts = [], node = element;
    while (node && node !== document.body) {
      var parent = node.parentElement;
      if (!parent) break;
      var peers = Array.prototype.filter.call(parent.children, function (child) { return child.tagName === node.tagName; });
      parts.unshift(node.tagName.toLowerCase() + (peers.length > 1 ? ":" + (peers.indexOf(node) + 1) : ""));
      node = parent;
    }
    return parts.join("/");
  }

  function isEditableText(element) {
    if (element.closest(".portfolio-editor, .portfolio-image-hint, .portfolio-global-nav, .pv2-footer")) return false;
    if (/^(SCRIPT|STYLE|NOSCRIPT|IMG|VIDEO|SOURCE)$/.test(element.tagName)) return false;
    return Array.prototype.some.call(element.childNodes, function (node) {
      return node.nodeType === Node.TEXT_NODE && node.nodeValue.trim();
    });
  }

  var textNodes = Array.prototype.filter.call(document.body.querySelectorAll("*"), isEditableText);
  textNodes.forEach(function (node) { if (!node.dataset.edit) node.dataset.edit = elementPath(node); });
  var imageNodes = Array.prototype.filter.call(document.querySelectorAll("[data-image-slot], img"), function (node) {
    return !node.closest(".portfolio-global-nav, .pv2-footer");
  });
  imageNodes.forEach(function (node, index) {
    if (!node.dataset.imageSlot) node.dataset.imageSlot = "image-" + (index + 1);
    if (!node.dataset.imageSize) {
      var width = node.getAttribute("width"), height = node.getAttribute("height");
      node.dataset.imageSize = width && height ? width + " × " + height + " px" : "1600 × 1200 px";
    }
    node.tabIndex = 0;
  });

  var input = document.createElement("input");
  input.type = "file";
  input.accept = "image/jpeg,image/png,image/webp,image/gif";
  input.hidden = true;
  document.body.appendChild(input);

  var toolbar = document.createElement("aside");
  toolbar.className = "portfolio-editor";
  toolbar.setAttribute("aria-label", "作品集内容编辑器");
  toolbar.innerHTML = '<button class="portfolio-editor__toggle" type="button">编辑本页全部内容</button><div class="portfolio-editor__actions" hidden><p>虚线框可改文字；图片区域可逐张上传。</p><button class="portfolio-editor__save" type="button">保存本页</button><button class="portfolio-editor__cancel" type="button">退出编辑</button></div><output class="portfolio-editor__status" aria-live="polite"></output>';
  document.body.appendChild(toolbar);
  var toggle = toolbar.querySelector(".portfolio-editor__toggle");
  var actions = toolbar.querySelector(".portfolio-editor__actions");
  var save = toolbar.querySelector(".portfolio-editor__save");
  var cancel = toolbar.querySelector(".portfolio-editor__cancel");
  var status = toolbar.querySelector(".portfolio-editor__status");

  var copyToast = document.createElement("output");
  copyToast.className = "portfolio-copy-toast";
  copyToast.setAttribute("aria-live", "polite");
  document.body.appendChild(copyToast);
  var copyToastTimer = null;

  function setStatus(message, error) {
    status.textContent = message;
    status.classList.toggle("is-error", Boolean(error));
  }

  function showCopyToast(message, error) {
    window.clearTimeout(copyToastTimer);
    copyToast.textContent = message;
    copyToast.classList.toggle("is-error", Boolean(error));
    copyToast.classList.add("is-visible");
    copyToastTimer = window.setTimeout(function () {
      copyToast.classList.remove("is-visible");
    }, 1800);
  }

  function copyText(value) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(value);
    return new Promise(function (resolve, reject) {
      var field = document.createElement("textarea");
      field.value = value;
      field.setAttribute("readonly", "");
      field.style.position = "fixed";
      field.style.opacity = "0";
      document.body.appendChild(field);
      field.select();
      field.setSelectionRange(0, field.value.length);
      try {
        if (!document.execCommand("copy")) throw new Error("copy failed");
        resolve();
      } catch (error) {
        reject(error);
      } finally {
        field.remove();
      }
    });
  }

  function applyImage(node, url) {
    if (!url) return;
    if (node.tagName === "IMG") node.src = url;
    else {
      node.style.backgroundImage = 'url("' + String(url).replace(/"/g, "%22") + '")';
      node.classList.add("has-uploaded-image");
    }
  }

  function applyState(next) {
    documentState = next && typeof next === "object" ? next : {};
    if (!documentState.pages) documentState = { pages: { home: { texts: documentState.texts || {}, images: documentState.images || {} } } };
    pageState = documentState.pages[pageKey] || { texts: {}, images: {} };
    pageState.texts = pageState.texts || {};
    pageState.images = pageState.images || {};
    textNodes.forEach(function (node) {
      var value = pageState.texts[node.dataset.edit];
      if (typeof value === "string") node.textContent = value;
    });
    imageNodes.forEach(function (node) { applyImage(node, pageState.images[node.dataset.imageSlot]); });
    document.documentElement.classList.remove("portfolio-content-pending");
  }

  function collect() {
    textNodes.forEach(function (node) { pageState.texts[node.dataset.edit] = node.textContent.trim(); });
    documentState.pages[pageKey] = pageState;
    return documentState;
  }

  function setEditing(value) {
    editing = value;
    document.body.classList.toggle("portfolio-editing", editing);
    actions.hidden = !editing;
    toggle.hidden = editing;
    textNodes.forEach(function (node) { node.contentEditable = editing ? "true" : "false"; node.spellcheck = editing; });
    setStatus(editing ? "正在编辑当前页面" : "", false);
  }

  function saveContent(message) {
    setStatus("正在保存…", false);
    return fetch("/api/portfolio/content", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(collect()) })
      .then(function (response) {
        if (!response.ok) throw new Error("保存失败");
        setStatus(message || "已保存", false);
        announceUpdate();
      })
      .catch(function (error) { setStatus(error.message + "，请通过 start.vbs 启动网站。", true); throw error; });
  }

  function chooseImage(node) { if (editing) { activeImage = node; input.value = ""; input.click(); } }
  toggle.addEventListener("click", function () { setEditing(true); });
  cancel.addEventListener("click", function () { setEditing(false); });
  save.addEventListener("click", function () { saveContent("当前页面已保存").then(function () { setEditing(false); }); });

  imageNodes.forEach(function (node) {
    var hint = document.createElement("span");
    hint.className = "portfolio-image-hint";
    hint.innerHTML = "<b>更换图片</b><small>建议尺寸 " + node.dataset.imageSize + "<br>等比覆盖，不会拉伸</small>";
    if (node.tagName === "IMG") {
      var wrapper = document.createElement("span");
      wrapper.className = "portfolio-editable-image";
      node.parentNode.insertBefore(wrapper, node);
      wrapper.appendChild(node);
      wrapper.appendChild(hint);
      wrapper.addEventListener("click", function (event) { if (editing) { event.preventDefault(); chooseImage(node); } });
    } else {
      node.appendChild(hint);
      node.addEventListener("click", function (event) { if (editing) { event.preventDefault(); event.stopPropagation(); chooseImage(node); } });
    }
    node.addEventListener("keydown", function (event) { if (editing && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); chooseImage(node); } });
  });

  document.addEventListener("click", function (event) {
    if (editing && event.target.closest("a")) event.preventDefault();
    var copyButton = event.target.closest("[data-copy-contact]");
    if (!copyButton || editing) return;
    var valueNode = copyButton.querySelector("strong");
    var value = valueNode ? valueNode.textContent.trim() : "";
    if (!value) return;
    copyText(value).then(function () {
      setStatus("已复制：" + value, false);
      showCopyToast("已复制：" + value, false);
    }).catch(function () {
      setStatus("复制失败，请手动选择文字复制", true);
      showCopyToast("复制失败，请手动选择文字复制", true);
    });
  });
  input.addEventListener("change", function () {
    var file = input.files && input.files[0];
    if (!file || !activeImage) return;
    if (file.size > 15 * 1024 * 1024) { setStatus("图片不能超过 15 MB", true); return; }
    var slot = activeImage.dataset.imageSlot, target = activeImage;
    setStatus("正在上传 " + file.name + "…", false);
    fetch("/api/portfolio/upload?page=" + encodeURIComponent(pageKey) + "&slot=" + encodeURIComponent(slot), {
      method: "POST", headers: { "Content-Type": file.type || "application/octet-stream", "X-Filename": encodeURIComponent(file.name) }, body: file
    }).then(function (response) {
      if (!response.ok) return response.json().then(function (body) { throw new Error(body.error || "上传失败"); });
      return response.json();
    }).then(function (result) {
      var versionedUrl = result.url + "?v=" + Date.now();
      pageState.images[slot] = versionedUrl;
      applyImage(target, versionedUrl);
      return saveContent("图片已上传并保存");
    }).catch(function (error) { setStatus(error.message, true); });
  });

  fetch(root + "content.json", { cache: "no-store" }).then(function (response) { return response.ok ? response.json() : { pages: {} }; }).then(applyState).catch(function () { applyState({ pages: {} }); });
})();
