export function init(root) {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    || root.classList.contains('config-motion-disabled');

  if (reduceMotion) {
    root.style.setProperty('--case-media-scale', '1.5');
    root.style.setProperty('--case-media-radius', '0px');
    root.style.setProperty('--case-overlay-opacity', '0.6');
    root.style.setProperty('--case-eyebrow-opacity', '1');
    root.style.setProperty('--case-eyebrow-y', '0px');
    root.style.setProperty('--case-title-opacity', '1');
    root.style.setProperty('--case-title-y', '0px');
    return;
  }

  let frame = 0;

  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
  const smoothstep = (value) => value * value * (3 - 2 * value);

  function render() {
    frame = 0;
    if (root.classList.contains('config-motion-disabled')) {
      root.style.setProperty('--case-media-scale', '1.5');
      root.style.setProperty('--case-media-radius', '0px');
      root.style.setProperty('--case-eyebrow-opacity', '1');
      root.style.setProperty('--case-eyebrow-y', '0px');
      root.style.setProperty('--case-title-opacity', '1');
      root.style.setProperty('--case-title-y', '0px');
      return;
    }

    const rect = root.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    const scrollRange = Math.max(root.offsetHeight - viewportHeight, 1);

    // 进入视口的一屏距离内，画面由 2/3 尺寸跟随滚动放大到全屏。
    const entryProgress = clamp((viewportHeight - rect.top) / viewportHeight, 0, 1);
    const mediaScale = 1 + entryProgress * .5;

    // 吸顶后继续滚动：先加遮罩，再渐显文字
    const pinnedProgress = clamp(-rect.top / scrollRange, 0, 1);
    const overlay = smoothstep(clamp((pinnedProgress - .15) / .35, 0, 1)) * .6;
    const eyebrow = clamp((pinnedProgress - .3) / .3, 0, 1);
    const title = smoothstep(clamp((pinnedProgress - .35) / .35, 0, 1));

    root.style.setProperty('--case-media-scale', mediaScale.toFixed(5));
    root.style.setProperty('--case-media-radius', `${(30 * (1 - entryProgress)).toFixed(3)}px`);
    root.style.setProperty('--case-overlay-opacity', overlay.toFixed(4));
    root.style.setProperty('--case-eyebrow-opacity', eyebrow.toFixed(4));
    root.style.setProperty('--case-eyebrow-y', `${(10 * (1 - eyebrow)).toFixed(3)}px`);
    root.style.setProperty('--case-title-opacity', title.toFixed(4));
    root.style.setProperty('--case-title-y', `${(15 * (1 - title)).toFixed(3)}px`);
  }

  function updateProgress() {
    if (!frame) frame = requestAnimationFrame(render);
  }

  updateProgress();
  window.addEventListener('scroll', updateProgress, { passive: true });
  window.addEventListener('resize', updateProgress);
}
