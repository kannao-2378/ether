/* 新页面公共脚本：一次性内容进入 + 未开放入口提示 */
(function () {
  "use strict";

  window.addEventListener("storage", function (event) {
    if (event.key === "kan-content-updated" || event.key === "portfolio-content-updated") location.reload();
  });

  function applyHubContent(config) {
    if (!config || typeof config !== "object") return;
    if (config.siteTitle) document.title = config.siteTitle;
    var description = document.querySelector('meta[name="description"]');
    if (description && config.metaDescription) description.content = config.metaDescription;

    document.querySelectorAll("[data-hub-field]").forEach(function (node) {
      var key = node.dataset.hubField;
      if (typeof config[key] === "string") node.textContent = config[key];
      var type = config.typography && config.typography[key];
      if (type) {
        if (Number(type.size)) node.style.fontSize = Number(type.size) + "px";
        if (Number(type.weight)) node.style.fontWeight = String(Number(type.weight));
      }
    });

    var grid = document.querySelector("#hubEntryGrid");
    if (!grid || !Array.isArray(config.modules)) return;
    grid.replaceChildren();
    config.modules.filter(function (item) { return item && item.enabled !== false; }).forEach(function (item, index) {
      var entry = document.createElement(item.href ? "a" : "button");
      entry.className = "hub-entry motion-item" + (item.id === "portfolio" ? " hub-entry--active hub-entry--portfolio" : "");
      if (item.href) entry.href = item.href;
      else {
        entry.type = "button";
        entry.dataset.unavailable = "";
      }

      var visual = document.createElement("span");
      if (item.kind === "portfolio-poster") {
        visual.className = "hub-entry__visual";
        visual.setAttribute("aria-hidden", "true");
        var image = document.createElement("img");
        image.src = "/portfolio/uploads/home--poster-v2.jpg";
        image.alt = "";
        visual.appendChild(image);
      } else {
        visual.className = "hub-entry__blank";
        visual.setAttribute("aria-hidden", "true");
        visual.textContent = String(index + 1).padStart(2, "0");
      }

      var copy = document.createElement("span");
      copy.className = "hub-entry__copy";
      var title = document.createElement("strong");
      title.textContent = item.title || "未命名入口";
      var subtitle = document.createElement("small");
      subtitle.textContent = item.subtitle || "";
      copy.append(title, subtitle);
      var arrow = document.createElement("span");
      arrow.className = "hub-entry__arrow";
      arrow.setAttribute("aria-hidden", "true");
      arrow.textContent = "↗";
      entry.append(visual, copy, arrow);
      grid.appendChild(entry);
    });
  }

  fetch("content.json", { cache: "no-store" })
    .then(function (response) { if (!response.ok) throw new Error("Hub content unavailable"); return response.json(); })
    .then(applyHubContent)
    .catch(function () { /* Keep the complete HTML fallback. */ });

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.body.classList.add("motion-ready");

  /* 内容进入：滚动到视口时为 motion-group 添加 is-visible（一次性） */
  var groups = document.querySelectorAll(".motion-group");

  if (reduceMotion || !("IntersectionObserver" in window)) {
    Array.prototype.forEach.call(groups, function (g) {
      g.classList.add("is-visible");
    });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });

    Array.prototype.forEach.call(groups, function (g) {
      io.observe(g);
    });
  }

  /* 动态案例视频：只在进入视口时解码播放，离屏立即暂停。 */
  var inlineVideos = document.querySelectorAll(".pv2-motion-gallery video");
  if (inlineVideos.length) {
    if (reduceMotion || !("IntersectionObserver" in window)) {
      Array.prototype.forEach.call(inlineVideos, function (video) { video.pause(); });
    } else {
      var videoObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          var video = entry.target;
          if (entry.isIntersecting) {
            var playRequest = video.play();
            if (playRequest && typeof playRequest.catch === "function") playRequest.catch(function () {});
          } else {
            video.pause();
          }
        });
      }, { threshold: 0.2 });
      Array.prototype.forEach.call(inlineVideos, function (video) { videoObserver.observe(video); });
    }
  }

  /* 占位入口：轻量对话框，支持键盘焦点与 Esc 关闭 */
  var alertEl = document.querySelector(".site-alert");
  var closeButton = document.querySelector("[data-alert-close]");
  var hideTimer = null;
  var previousFocus = null;

  function hideAlert() {
    if (!alertEl || alertEl.hidden) return;
    alertEl.classList.remove("is-visible");
    clearTimeout(hideTimer);
    hideTimer = setTimeout(function () {
      alertEl.hidden = true;
      if (previousFocus) previousFocus.focus();
    }, reduceMotion ? 0 : 250);
  }

  if (alertEl) {
    document.addEventListener("click", function (e) {
      var el = e.target.closest("[data-unavailable]");
      if (!el) return;
      e.preventDefault();
      previousFocus = el;
      clearTimeout(hideTimer);
      alertEl.hidden = false;
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          alertEl.classList.add("is-visible");
          if (closeButton) closeButton.focus();
        });
      });
    });
    alertEl.addEventListener("click", function (e) {
      if (e.target === alertEl) hideAlert();
    });
    if (closeButton) closeButton.addEventListener("click", hideAlert);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") hideAlert();
    });
  }
})();
