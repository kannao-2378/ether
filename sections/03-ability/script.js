export function init(root) {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    || root.classList.contains('config-motion-disabled');

  if (reduceMotion || !('IntersectionObserver' in window)) {
    root.classList.add('is-visible');
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    if (!entries[0].isIntersecting) return;
    root.classList.add('is-visible');
    observer.disconnect();
  }, { threshold: 0, rootMargin: '-10% 0px -35% 0px' });

  observer.observe(root);
}
