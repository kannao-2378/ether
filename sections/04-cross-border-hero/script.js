export function init(root) {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    || root.classList.contains('config-motion-disabled');

  if (reduceMotion) {
    root.style.setProperty('--case-scale', '1');
    root.style.setProperty('--case-y', '0px');
    root.style.setProperty('--case-media-opacity', '1');
    root.style.setProperty('--case-copy-opacity', '1');
    root.style.setProperty('--case-copy-y', '0px');
    return;
  }

  let targetProgress = 0;
  let renderedProgress = 0;
  let frame = 0;

  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
  const easeOutCubic = (value) => 1 - Math.pow(1 - value, 3);

  function render() {
    frame = 0;
    const configuredStyle = getComputedStyle(root);
    const smoothing = Number.parseFloat(configuredStyle.getPropertyValue('--case-smoothing')) || 0.16;
    const copyStart = Number.parseFloat(configuredStyle.getPropertyValue('--case-copy-start')) || 0.44;
    const copySpan = Number.parseFloat(configuredStyle.getPropertyValue('--case-copy-span')) || 0.24;

    if (root.classList.contains('config-motion-disabled')) {
      root.style.setProperty('--case-scale', '1');
      root.style.setProperty('--case-y', '0px');
      root.style.setProperty('--case-media-opacity', '1');
      root.style.setProperty('--case-copy-opacity', '1');
      root.style.setProperty('--case-copy-y', '0px');
      return;
    }

    renderedProgress += (targetProgress - renderedProgress) * smoothing;

    if (Math.abs(targetProgress - renderedProgress) < 0.001) {
      renderedProgress = targetProgress;
    }

    const reveal = easeOutCubic(clamp(renderedProgress / 0.32, 0, 1));
    const pinnedProgress = clamp((renderedProgress - 0.32) / 0.68, 0, 1);
    const copy = easeOutCubic(clamp((pinnedProgress - copyStart) / copySpan, 0, 1));

    root.style.setProperty('--case-scale', (2 / 3 + reveal / 3).toFixed(5));
    root.style.setProperty('--case-y', `${(-16.6667 * (1 - reveal)).toFixed(4)}vh`);
    root.style.setProperty('--case-media-opacity', reveal.toFixed(4));
    root.style.setProperty('--case-copy-opacity', copy.toFixed(4));
    root.style.setProperty('--case-copy-y', `${(15 * (1 - copy)).toFixed(3)}px`);

    if (renderedProgress !== targetProgress) {
      frame = requestAnimationFrame(render);
    }
  }

  function updateProgress() {
    const rect = root.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    const scrollRange = Math.max(root.offsetHeight - viewportHeight, 1);
    const travelled = viewportHeight - rect.top;
    targetProgress = clamp(travelled / (viewportHeight + scrollRange), 0, 1);

    if (!frame) frame = requestAnimationFrame(render);
  }

  updateProgress();
  window.addEventListener('scroll', updateProgress, { passive: true });
  window.addEventListener('resize', updateProgress);
}
