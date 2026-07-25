/* =====================================================================
   Brand Portfolio — 流式布局
   不再做 transform:scale 整体缩放：
   - 导航/首屏背景全宽填满视口
   - 内容用 1920px 容器居中，字体固定 px 不缩放（清晰无锯齿）
   - 窗口小于 1920 时内容居中、两侧由背景填充（正常网页行为）
   ===================================================================== */
(function () {
  'use strict';

  var hero = document.querySelector('.hero');
  var heroVideo = document.querySelector('.hero__video');

  if (hero && heroVideo) {
    var hasPlayed = false;
    var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function showHero() {
      hero.classList.add('is-video-ready', 'is-playing');
    }

    function playHeroOnce() {
      if (hasPlayed || prefersReducedMotion) return;
      hasPlayed = true;
      showHero();

      var playPromise = heroVideo.play();
      if (playPromise) {
        playPromise.catch(function () {
          hero.classList.add('is-video-ended');
        });
      }
    }

    heroVideo.addEventListener('canplay', playHeroOnce, { once: true });
    heroVideo.addEventListener('ended', function () {
      hero.classList.add('is-video-ended');
    }, { once: true });

    if (prefersReducedMotion) {
      showHero();
    } else if (heroVideo.readyState >= 3) {
      playHeroOnce();
    } else {
      heroVideo.load();
    }
  }

  /* 平滑锚点（了解更多按钮） */
  var ability = document.querySelector('.ability');

  if (ability) {
    var reduceAbilityMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (reduceAbilityMotion || !('IntersectionObserver' in window)) {
      ability.classList.add('is-visible');
    } else {
      var abilityObserver = new IntersectionObserver(function (entries, observer) {
        if (!entries[0].isIntersecting) return;
        ability.classList.add('is-visible');
        observer.disconnect();
      }, { threshold: 0.2 });
      abilityObserver.observe(ability);
    }
  }

  /*
   * 04 - 跨境案例大屏
   * DJI 参考区由两段滚动进度组成：
   * 1) 章节抵达视口前：画面从 2/3 尺寸放大到全屏并淡入；
   * 2) 画面固定后：两行文案从下方 15px 同步淡入。
   */
  var crossBorderCase = document.querySelector('.cross-border-case');

  if (crossBorderCase) {
    var reduceCaseMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var caseTargetProgress = 0;
    var caseRenderedProgress = 0;
    var caseFrame = 0;

    function clamp(value, min, max) {
      return Math.min(Math.max(value, min), max);
    }

    function easeOutCubic(value) {
      return 1 - Math.pow(1 - value, 3);
    }

    function renderCaseMotion() {
      caseFrame = 0;
      caseRenderedProgress += (caseTargetProgress - caseRenderedProgress) * 0.16;

      if (Math.abs(caseTargetProgress - caseRenderedProgress) < 0.001) {
        caseRenderedProgress = caseTargetProgress;
      }

      var reveal = easeOutCubic(clamp(caseRenderedProgress / 0.32, 0, 1));
      var pinnedProgress = clamp((caseRenderedProgress - 0.32) / 0.68, 0, 1);
      var copy = easeOutCubic(clamp((pinnedProgress - 0.34) / 0.18, 0, 1));

      crossBorderCase.style.setProperty('--case-scale', (2 / 3 + reveal / 3).toFixed(5));
      crossBorderCase.style.setProperty('--case-y', (-16.6667 * (1 - reveal)).toFixed(4) + 'vh');
      crossBorderCase.style.setProperty('--case-media-opacity', reveal.toFixed(4));
      crossBorderCase.style.setProperty('--case-copy-opacity', copy.toFixed(4));
      crossBorderCase.style.setProperty('--case-copy-y', (15 * (1 - copy)).toFixed(3) + 'px');

      if (caseRenderedProgress !== caseTargetProgress) {
        caseFrame = requestAnimationFrame(renderCaseMotion);
      }
    }

    function updateCaseProgress() {
      var rect = crossBorderCase.getBoundingClientRect();
      var viewportHeight = window.innerHeight;
      var scrollRange = Math.max(crossBorderCase.offsetHeight - viewportHeight, 1);
      var entryDistance = viewportHeight;
      var travelled = entryDistance - rect.top;
      caseTargetProgress = clamp(travelled / (entryDistance + scrollRange), 0, 1);

      if (!caseFrame) {
        caseFrame = requestAnimationFrame(renderCaseMotion);
      }
    }

    if (!reduceCaseMotion) {
      updateCaseProgress();
      window.addEventListener('scroll', updateCaseProgress, { passive: true });
      window.addEventListener('resize', updateCaseProgress);
    }
  }

  document.querySelectorAll('a[href^="#"]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      var href = link.getAttribute('href');
      if (!href || href === '#') return;
      var target = document.querySelector(href);
      if (!target) { e.preventDefault(); return; }
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
})();
