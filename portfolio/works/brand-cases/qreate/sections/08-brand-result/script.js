export function init(root) {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    || root.classList.contains('config-motion-disabled');

  if (reduceMotion) {
    root.style.setProperty('--brand-progress', '1');
    root.style.setProperty('--brand-summary-progress', '1');
    return;
  }

  let targetProgress = 0;
  let renderedProgress = 0;
  let frame = 0;

  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
  const easeInOutSine = (value) => -(Math.cos(Math.PI * value) - 1) / 2;

  function render() {
    frame = 0;
    const smoothing = Number.parseFloat(
      getComputedStyle(root).getPropertyValue('--brand-smoothing')
    ) || 0.5;

    if (root.classList.contains('config-motion-disabled')) {
      root.style.setProperty('--brand-progress', '1');
      root.style.setProperty('--brand-summary-progress', '1');
      return;
    }

    renderedProgress += (targetProgress - renderedProgress) * smoothing;

    if (Math.abs(targetProgress - renderedProgress) < 0.001) {
      renderedProgress = targetProgress;
    }

    const easedProgress = easeInOutSine(renderedProgress);
    const summaryProgress = easeInOutSine(clamp((renderedProgress - 0.62) / 0.28, 0, 1));
    root.style.setProperty('--brand-progress', easedProgress.toFixed(4));
    root.style.setProperty('--brand-summary-progress', summaryProgress.toFixed(4));

    if (renderedProgress !== targetProgress) {
      frame = requestAnimationFrame(render);
    }
  }

  function updateProgress() {
    const rect = root.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    const start = viewportHeight * 0.75;
    const distance = viewportHeight * 0.9;
    targetProgress = clamp((start - rect.top) / distance, 0, 1);

    if (!frame) frame = requestAnimationFrame(render);
  }

  updateProgress();
  window.addEventListener('scroll', updateProgress, { passive: true });
  window.addEventListener('resize', updateProgress);
}
