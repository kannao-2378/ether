/* 全站公共交互：内容进入、视口内视频播放与占位入口提示。 */
(function () {
  "use strict";

  window.addEventListener("storage", function (event) {
    if (event.key === "kan-content-updated" || event.key === "portfolio-content-updated") {
      location.reload();
    }
  });

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.body.classList.add("motion-ready");

  var groups = document.querySelectorAll(".motion-group");
  if (reduceMotion || !("IntersectionObserver" in window)) {
    Array.prototype.forEach.call(groups, function (group) {
      group.classList.add("is-visible");
    });
  } else {
    var groupObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        groupObserver.unobserve(entry.target);
      });
    }, { threshold: 0.15 });

    Array.prototype.forEach.call(groups, function (group) {
      groupObserver.observe(group);
    });
  }

  var inlineVideos = document.querySelectorAll(".pv2-motion-gallery video");
  if (inlineVideos.length) {
    if (reduceMotion || !("IntersectionObserver" in window)) {
      Array.prototype.forEach.call(inlineVideos, function (video) {
        video.pause();
      });
    } else {
      var videoObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          var video = entry.target;
          if (!entry.isIntersecting) {
            video.pause();
            return;
          }
          var playRequest = video.play();
          if (playRequest && typeof playRequest.catch === "function") {
            playRequest.catch(function () {});
          }
        });
      }, { threshold: 0.2 });

      Array.prototype.forEach.call(inlineVideos, function (video) {
        videoObserver.observe(video);
      });
    }
  }

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

  if (!alertEl) return;

  document.addEventListener("click", function (event) {
    var trigger = event.target.closest("[data-unavailable]");
    if (!trigger) return;
    event.preventDefault();
    previousFocus = trigger;
    clearTimeout(hideTimer);
    alertEl.hidden = false;
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        alertEl.classList.add("is-visible");
        if (closeButton) closeButton.focus();
      });
    });
  });

  alertEl.addEventListener("click", function (event) {
    if (event.target === alertEl) hideAlert();
  });
  if (closeButton) closeButton.addEventListener("click", hideAlert);
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") hideAlert();
  });
})();
