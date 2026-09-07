import { showSiteAlert } from '../shared-modules.js?v=11';

export function init(root) {
  // CTA 拦截：弹出"暂未开启"提示
  const cta = root.querySelector('.ability__conclusion a[href="#contact"]');
  if (cta) {
    cta.addEventListener('click', (event) => {
      event.preventDefault();
      showSiteAlert('对不起，暂未开启');
    });
  }

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
