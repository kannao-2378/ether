import { showSiteAlert } from '../shared-modules.js?v=11';

export function init(root) {
  // CTA 拦截：弹出"暂未开启"提示
  const cta = root.querySelector('.brand-method__cta');
  if (cta) {
    cta.addEventListener('click', () => showSiteAlert('对不起，暂未开启'));
  }

  const motionRoot = root.querySelector('.brand-method__motion');
  const detailItems = [...root.querySelectorAll('[data-method-reveal]')];
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const clamp = (value, min = 0, max = 1) => Math.min(Math.max(value, min), max);
  const smoothstep = (value) => value * value * (3 - 2 * value);

  let targetProgress = 0;
  let frame = 0;

  // ---- 视频：遮罩动画结束后才播放（SVG mask 的第一帧图片已在 HTML 里静态引用） ----
  const largeVideo = root.querySelector('.brand-method__large-phone-image');
  const smallVideo = root.querySelector('.brand-method__final-phone-image');
  let videoStarted = false;

  // 确保视频初始暂停（无 autoplay，但作为安全保障）
  if (largeVideo) largeVideo.pause();
  if (smallVideo) smallVideo.pause();

  // 安全拦截：如果视频在遮罩动画结束前被浏览器或其他代码触发播放，立即暂停
  // 这里的 videoStarted 作为闸门，只有 startVideos() 显式调用后才会放行
  function guardPlay(video) {
    if (!video) return;
    video.addEventListener('play', () => {
      if (!videoStarted) {
        video.pause();
        video.currentTime = 0;
      }
    });
  }
  guardPlay(largeVideo);
  guardPlay(smallVideo);

  function startVideos() {
    if (videoStarted) return;
    videoStarted = true;
    if (largeVideo) largeVideo.play().catch(() => {});
    if (smallVideo) smallVideo.play().catch(() => {});
  }

  function setDesignScale() {
    if (window.innerWidth <= 900) {
      root.style.setProperty('--method-scale', '1');
      return;
    }

    const scale = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    root.style.setProperty('--method-scale', scale.toFixed(6));
  }

  function setStaticDetailState() {
    root.style.setProperty('--method-word-scale', '100');
    root.style.setProperty('--method-mask-opacity', '0');
    root.style.setProperty('--method-cover-opacity', '1');
    root.style.setProperty('--method-intro-opacity', '0');
    root.style.setProperty('--method-label-opacity', '0');
    root.style.setProperty('--method-large-opacity', '0');
    root.style.setProperty('--method-phone-progress', '1');
    root.style.setProperty('--method-scene-opacity', '0');
    root.style.setProperty('--method-final-phone-opacity', '1');
    root.style.setProperty('--method-detail-opacity', '1');
    detailItems.forEach((item) => item.classList.add('is-visible'));
    startVideos();
  }

  function applyProgress(progress) {
    // 0—45%：ETHER 遮罩动画（维持不变）
    const revealLinear = clamp(progress / .45);

    // 遮罩动画结束后（progress > 0.45）开始播放视频；
    // 遮罩动画期间（progress <= 0.45）强制暂停视频，确保只显示第一帧
    if (progress > 0.45) {
      startVideos();
    } else if (videoStarted) {
      // 已启动过但回滚到遮罩阶段：暂停并重置到第一帧
      if (largeVideo) { largeVideo.pause(); largeVideo.currentTime = 0; }
      if (smallVideo) { smallVideo.pause(); smallVideo.currentTime = 0; }
      videoStarted = false;
    }

    // 45—55%：大显示器停留；55—80%：4→5 显示器缩放（smoothstep 缓动确保流畅）
    const phoneLinear = clamp((progress - .55) / .25);
    const phone = smoothstep(phoneLinear);

    const introOpacity = 1 - smoothstep(clamp(revealLinear / .125));
    const labelOpacity = 1 - smoothstep(clamp((revealLinear - .015) / .11));
    const maskEntry = smoothstep(clamp((revealLinear - .015) / .1));
    const maskExit = smoothstep(clamp((revealLinear - .72) / .16));
    const maskOpacity = maskEntry * (1 - maskExit);
    const fullPhoneOpacity = smoothstep(clamp((revealLinear - .62) / .2));
    const wordScale = 1 + Math.pow(revealLinear, 3) * 99;

    // 80—90%：final-phone 提前淡入覆盖 large-phone（避免交叉淡入淡出时黑色背景透出）
    const finalPhoneOpacity = smoothstep(clamp((progress - .80) / .10));

    // 90—95%：large-phone 延迟淡出（final-phone 已完全显示，不会露出黑色背景）
    const largePhoneFadeOut = smoothstep(clamp((progress - .90) / .05));
    const largePhoneOpacity = fullPhoneOpacity * (1 - largePhoneFadeOut);

    // 90—100%：6 文字动画（维持原有逻辑不变）
    const detailOpacity = smoothstep(clamp((progress - .9) / .1));

    root.style.setProperty('--method-word-scale', wordScale.toFixed(5));
    root.style.setProperty('--method-mask-opacity', maskOpacity.toFixed(4));
    root.style.setProperty('--method-cover-opacity', '1');
    root.style.setProperty('--method-intro-opacity', introOpacity.toFixed(4));
    root.style.setProperty('--method-label-opacity', labelOpacity.toFixed(4));
    root.style.setProperty('--method-large-opacity', largePhoneOpacity.toFixed(4));
    root.style.setProperty('--method-phone-progress', phone.toFixed(4));
    root.style.setProperty('--method-scene-opacity', '0');
    root.style.setProperty('--method-final-phone-opacity', finalPhoneOpacity.toFixed(4));
    root.style.setProperty('--method-detail-opacity', detailOpacity.toFixed(4));
  }

  function render() {
    frame = 0;

    if (root.classList.contains('config-motion-disabled')) {
      setStaticDetailState();
      return;
    }

    applyProgress(targetProgress);
  }

  function updateProgress() {
    setDesignScale();

    if (window.innerWidth <= 900) {
      setStaticDetailState();
      return;
    }

    const rect = motionRoot.getBoundingClientRect();
    const distance = Math.max(motionRoot.offsetHeight - window.innerHeight, 1);
    targetProgress = clamp(-rect.top / distance);

    if (!frame) {
      frame = requestAnimationFrame(render);
    }
  }

  setDesignScale();

  if (reduceMotion) {
    setStaticDetailState();
    return;
  }

  const detailObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      detailObserver.unobserve(entry.target);
    });
  }, { threshold: 0.08, rootMargin: '-8% 0px -18% 0px' });

  detailItems.forEach((item) => detailObserver.observe(item));

  updateProgress();
  window.addEventListener('scroll', updateProgress, { passive: true });
  window.addEventListener('resize', updateProgress);
}
