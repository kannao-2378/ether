export function init() {
  const navItems = Array.from(document.querySelectorAll('.nav__item'));
  if (navItems.length === 0) return;

  // 建立 navItem -> section 映射（按 nav 顺序）
  const entries = [];
  navItems.forEach((item) => {
    const hash = item.getAttribute('href') || '';
    if (!hash.startsWith('#')) return;
    const target = document.querySelector(hash);
    if (target) entries.push({ target, item });
  });
  if (entries.length === 0) return;

  let ticking = false;

  function update() {
    const scrollTop = window.scrollY || document.documentElement.scrollTop;

    // 计算每个 navItem 对应 section 的绝对顶部位置
    const tops = entries.map(({ target }) => {
      const rect = target.getBoundingClientRect();
      return rect.top + (window.scrollY || document.documentElement.scrollTop);
    });

    // 每个 navItem 的进度范围 = [自己 top, 下一个 navItem top]
    // 最后一个到文档底部
    const docBottom =
      document.documentElement.scrollHeight - window.innerHeight;

    let current = null;
    let currentRatio = -1;

    entries.forEach((entry, index) => {
      const start = tops[index];
      const end = index + 1 < entries.length ? tops[index + 1] : docBottom;

      let ratio = 0;
      if (end > start) {
        ratio = (scrollTop - start) / (end - start);
        ratio = Math.min(1, Math.max(0, ratio));
      }

      // 当前 = 进度在 (0,1) 区间且 ratio 最大
      if (ratio > 0 && ratio < 1 && ratio > currentRatio) {
        currentRatio = ratio;
        current = entry.item;
      }
    });

    // 只给当前 navItem 设进度，其他清空
    entries.forEach(({ item }) => {
      if (item === current) {
        item.style.setProperty('--nav-item-progress', currentRatio.toFixed(4));
        item.classList.add('is-current');
      } else {
        item.style.removeProperty('--nav-item-progress');
        item.classList.remove('is-current');
      }
    });

    ticking = false;
  }

  function onScroll() {
    if (!ticking) {
      requestAnimationFrame(update);
      ticking = true;
    }
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  update();
}
