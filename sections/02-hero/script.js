import { showSiteAlert } from '../shared-modules.js?v=11';

export function init(root) {
  const video = root.querySelector('.hero__video');

  // CTA 拦截：弹出"暂未开启"提示
  const cta = root.querySelector('.hero__cta');
  if (cta) {
    cta.addEventListener('click', (event) => {
      event.preventDefault();
      showSiteAlert('对不起，暂未开启');
    });
  }

  if (!video) return;

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    || root.classList.contains('config-motion-disabled');
  let hasPlayed = false;
  let animationFrame = 0;

  const clamp = (value, min = 0, max = 1) => Math.min(Math.max(value, min), max);
  const easeOutCubic = (value) => 1 - Math.pow(1 - value, 3);

  function setCopyProgress(progress) {
    const eyebrow = easeOutCubic(clamp((progress - .68) / .2));
    const wordmark = easeOutCubic(clamp((progress - .72) / .2));
    const cta = easeOutCubic(clamp((progress - .86) / .14));

    root.style.setProperty('--hero-eyebrow-progress', eyebrow.toFixed(4));
    root.style.setProperty('--hero-eyebrow-y', `${(34 * (1 - eyebrow)).toFixed(3)}px`);
    root.style.setProperty('--hero-eyebrow-scale', (.96 + eyebrow * .04).toFixed(5));
    root.style.setProperty('--hero-wordmark-progress', wordmark.toFixed(4));
    root.style.setProperty('--hero-wordmark-y', `${(42 * (1 - wordmark)).toFixed(3)}px`);
    root.style.setProperty('--hero-wordmark-scale', (.94 + wordmark * .06).toFixed(5));
    root.style.setProperty('--hero-cta-progress', cta.toFixed(4));
    root.style.setProperty('--hero-cta-y', `${(24 * (1 - cta)).toFixed(3)}px`);
  }

  function syncCopyToVideo() {
    animationFrame = 0;
    const duration = Number.isFinite(video.duration) && video.duration > 0 ? video.duration : 3.033333;
    setCopyProgress(video.currentTime / duration);

    if (!video.paused && !video.ended) {
      animationFrame = requestAnimationFrame(syncCopyToVideo);
    }
  }

  function startCopySync() {
    if (!animationFrame) animationFrame = requestAnimationFrame(syncCopyToVideo);
  }

  function revealVideo() {
    root.classList.add('is-video-ready');
  }

  function playOnce() {
    if (hasPlayed || reduceMotion) return;
    hasPlayed = true;

    const playPromise = video.play();
    if (playPromise) {
      playPromise.catch(() => root.classList.add('is-video-error'));
    }
  }

  video.addEventListener('loadeddata', revealVideo, { once: true });
  video.addEventListener('canplay', revealVideo, { once: true });
  video.addEventListener('play', startCopySync);
  video.addEventListener('timeupdate', startCopySync);
  video.addEventListener('ended', () => {
    root.classList.add('is-video-ended');
    setCopyProgress(1);
  }, { once: true });
  video.addEventListener('error', () => root.classList.add('is-video-error'), { once: true });

  if (reduceMotion) {
    setCopyProgress(1);
    return;
  }

  if (video.readyState >= 2) {
    revealVideo();
    playOnce();
  } else {
    video.preload = 'auto';
    video.load();
    playOnce();
  }
}

