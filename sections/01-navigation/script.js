export function init() {
  const navItems = Array.from(document.querySelectorAll('.nav__item'));
  if (navItems.length === 0) return;

  // 建立 navItem -> 锚点映射（按 nav 顺序）
  // 只存 hash，不缓存元素引用：懒加载会用真实模块替换占位符，
  // 缓存的引用会指向已脱离文档的占位 div，导致进度计算失效
  const entries = [];
  navItems.forEach((item) => {
    const hash = item.getAttribute('href') || '';
    if (hash.startsWith('#')) entries.push({ hash, item });
  });
  if (entries.length === 0) return;

  let ticking = false;

  function update() {
    const scrollTop = window.scrollY || document.documentElement.scrollTop;

    // 实时解析锚点元素：占位符与真实模块共用同一 id，
    // 懒加载替换后这里的查询会自动指向新元素
    const active = entries
      .map((entry) => {
        const target = document.querySelector(entry.hash);
        if (!target) return null;
        const rect = target.getBoundingClientRect();
        return { item: entry.item, top: rect.top + scrollTop };
      })
      .filter(Boolean);

    if (active.length === 0) return;

    // 每个 navItem 的进度范围 = [自己 top, 下一个 navItem top]
    // 最后一个到文档底部
    const docBottom =
      document.documentElement.scrollHeight - window.innerHeight;

    let current = null;
    let currentRatio = -1;

    active.forEach((entry, index) => {
      const start = entry.top;
      const end = index + 1 < active.length ? active[index + 1].top : docBottom;

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
    active.forEach(({ item }) => {
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
