import { initReveal, initScaledSection, showSiteAlert } from '../shared-modules.js?v=11';

export function init(root) {
  initScaledSection(root, 1387);
  initReveal(root);

  // CTA 拦截：弹出"暂未开启"提示
  const cta = root.querySelector('.motion-cases__cta');
  if (cta) {
    cta.addEventListener('click', () => showSiteAlert('对不起，暂未开启'));
  }

  const gallery = root.querySelector('.motion-cases__gallery');
  const cardsContainer = root.querySelector('[data-motion-cards]');
  const prevButton = root.querySelector('[data-motion-prev]');
  const nextButton = root.querySelector('[data-motion-next]');
  const nav = root.querySelector('.motion-cases__nav');

  let currentIndex = 0;
  let isAnimating = false;
  let scrollAnimRaf = 0;
  // 当前 transform 偏移量（正值表示向左移动，即查看右侧内容）
  let currentOffset = 0;

  // —— 布局缓存 ——
  // 读取 scrollWidth / clientWidth / offsetLeft / getComputedStyle 会强制同步布局或样式重算。
  // 动画与拖拽过程中反复读取会引发「读-写-读-写」重排抖动（表现为一顿一顿）。
  // 这里把所有几何量一次性测量并缓存，仅在布局可能变化时失效。
  let layoutCache = null;
  function invalidateLayout() { layoutCache = null; }
  function measureLayout() {
    if (layoutCache) return layoutCache;
    const cardEls = root.querySelectorAll('.motion-cases__card');
    const scale = parseFloat(getComputedStyle(root).getPropertyValue('--motion-stage-scale')) || 1;
    const clientWidth = gallery ? gallery.clientWidth : 0;
    const alignX = clientWidth ? Math.max(0, (clientWidth - 1920 * scale) / 2 + 330 * scale) : 0;
    const scrollWidth = cardsContainer ? cardsContainer.scrollWidth : 0;
    const maxOffset = Math.max(0, scrollWidth - clientWidth);
    const cardLefts = Array.from(cardEls).map((c) => c.offsetLeft);
    layoutCache = { maxOffset, alignX, cardLefts, cardCount: cardEls.length };
    return layoutCache;
  }

  // 同步对齐变量到 CSS（用于 cards 容器的 padding-left）
  function syncAlignVar() {
    if (!gallery) return;
    gallery.style.setProperty('--motion-align-x', `${measureLayout().alignX}px`);
  }

  // 应用 transform 偏移（GPU 合成层，不触发 scroll 事件/重排）
  function applyOffset(offset) {
    currentOffset = offset;
    cardsContainer.style.transform = `translate3d(${-offset}px, 0, 0)`;
  }

  // 动画/拖拽期间开启 will-change 提升合成层，结束后移除以释放 GPU 内存
  function setWillChange(on) {
    cardsContainer && (cardsContainer.style.willChange = on ? 'transform' : 'auto');
  }

  // —— 离屏暂停视频：gallery 不在视口时暂停所有视频，回到视口再播放 ——
  // 6 张卡片含 3 个 4K 视频 + 3 个 GIF，离屏仍在解码会压满 GPU 导致垂直滚动卡顿。
  // 在视口内时所有视频正常播放（保持视觉一致），GIF 不动（浏览器原生优化）。
  let isGalleryVisible = true;
  if (gallery && typeof IntersectionObserver !== 'undefined') {
    const galleryObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        isGalleryVisible = entry.isIntersecting;
        const videos = root.querySelectorAll('.motion-cases__card video');
        if (!isGalleryVisible) {
          // 离开视口：暂停所有视频
          videos.forEach((v) => { v.pause(); });
        } else {
          // 回到视口：恢复播放
          videos.forEach((v) => { v.play().catch(() => {}); });
        }
      });
    }, { threshold: 0.01 });
    galleryObserver.observe(gallery);
  }

  // 更新箭头 disabled 状态
  function updateNavState() {
    if (!gallery) return;
    const { maxOffset } = measureLayout();
    prevButton && (prevButton.disabled = currentOffset <= 2);
    nextButton && (nextButton.disabled = currentOffset >= maxOffset - 2);
  }

  // 自定义 rAF 平滑滚动：transform 动画在 GPU 合成层完成，不触发重排
  function smoothScrollTo(target) {
    if (!cardsContainer) return;
    cancelAnimationFrame(scrollAnimRaf);
    const { maxOffset } = measureLayout();
    const clampedTarget = Math.min(Math.max(target, 0), maxOffset);
    const start = currentOffset;
    const diff = clampedTarget - start;
    if (Math.abs(diff) < 1) {
      applyOffset(clampedTarget);
      isAnimating = false;
      updateNavState();
      return;
    }
    const duration = 360;
    const startTime = performance.now();
    isAnimating = true;
    setWillChange(true);
    function step(now) {
      const t = Math.min(1, (now - startTime) / duration);
      const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
      applyOffset(start + diff * eased);
      if (t < 1) {
        scrollAnimRaf = requestAnimationFrame(step);
      } else {
        applyOffset(clampedTarget);
        isAnimating = false;
        setWillChange(false);
        updateNavState();
      }
    }
    scrollAnimRaf = requestAnimationFrame(step);
  }

  // 滚动使第 index 张卡片的左边缘对齐到文字位置
  function scrollToCard(index) {
    if (!gallery) return;
    const { cardLefts, alignX, cardCount } = measureLayout();
    if (!cardCount) return;
    const clamped = Math.min(Math.max(index, 0), cardCount - 1);
    currentIndex = clamped;
    // 卡片 offsetLeft 已含 cardsContainer 的 padding-left(=alignX)，故偏移 = offsetLeft - alignX
    smoothScrollTo(cardLefts[clamped] - alignX);
  }

  function scrollByCard(direction) {
    scrollToCard(currentIndex + direction);
  }

  // 拖拽后把 currentIndex 同步到最接近对齐位置的卡片（使用缓存，不触发重排）
  function syncIndexFromOffset() {
    const { cardLefts, alignX, cardCount } = measureLayout();
    if (!cardCount) return;
    const target = currentOffset + alignX;
    let best = 0;
    let bestDist = Infinity;
    for (let i = 0; i < cardCount; i++) {
      const dist = Math.abs(cardLefts[i] - target);
      if (dist < bestDist) { bestDist = dist; best = i; }
    }
    currentIndex = best;
  }

  // 监听素材加载完成（加载会改变卡片宽度，需失效缓存）
  function onMediaChange() {
    invalidateLayout();
    if (!isDragging) updateNavState();
  }
  function attachMediaListeners() {
    if (!cardsContainer) return;
    cardsContainer.querySelectorAll('img').forEach((img) => {
      if (img.complete) {
        onMediaChange();
      } else {
        img.addEventListener('load', onMediaChange, { once: true });
        img.addEventListener('error', onMediaChange, { once: true });
      }
    });
    cardsContainer.querySelectorAll('video').forEach((video) => {
      if (video.readyState >= 1) {
        onMediaChange();
      } else {
        video.addEventListener('loadedmetadata', onMediaChange, { once: true });
        video.addEventListener('loadeddata', onMediaChange, { once: true });
      }
    });
  }

  prevButton?.addEventListener('click', () => scrollByCard(-1));
  nextButton?.addEventListener('click', () => scrollByCard(1));

  // —— 手动拖拽（pointer events + rAF 合并） ——
  // 关键：拖拽期间冻结一份布局快照，pointermove 中只读快照 + 写 transform，不再触碰几何量；
  // 并用 requestAnimationFrame 合并同一帧内的多次 pointermove，避免排队丢帧。
  let isDragging = false;
  let dragStartX = 0;
  let dragStartOffset = 0;
  let hasDragged = false;
  let dragSnapshot = null;
  let dragRafPending = false;
  let dragLastX = 0;
  // pointerdown 时记录被点击的卡片（此时 target 还未被 setPointerCapture 改变），
  // 避免 pointerup 时用 document.elementFromPoint 触发重排
  let pointerDownCard = null;
  // 缓存卡片列表，避免每次点击都 querySelectorAll
  let cardsCache = null;
  function getCardsList() {
    if (!cardsCache) cardsCache = Array.from(root.querySelectorAll('.motion-cases__card'));
    return cardsCache;
  }

  gallery?.addEventListener('pointerdown', (e) => {
    if (isAnimating) return;
    isDragging = true;
    hasDragged = false;
    dragStartX = e.clientX;
    dragLastX = e.clientX;
    dragStartOffset = currentOffset;
    dragSnapshot = measureLayout(); // 冻结快照，拖拽期间不再读取几何量
    // 在 setPointerCapture 之前记录被点击的卡片
    pointerDownCard = e.target.closest('.motion-cases__card');
    gallery.setPointerCapture(e.pointerId);
    cancelAnimationFrame(scrollAnimRaf);
    setWillChange(true);
  });

  gallery?.addEventListener('pointermove', (e) => {
    if (!isDragging) return;
    dragLastX = e.clientX;
    if (dragRafPending) return; // 同一帧已有待处理回调，丢弃中间事件
    dragRafPending = true;
    requestAnimationFrame(() => {
      dragRafPending = false;
      if (!isDragging || !dragSnapshot) return;
      const delta = dragLastX - dragStartX;
      if (Math.abs(delta) > 3) hasDragged = true;
      const { maxOffset } = dragSnapshot;
      const newOffset = Math.min(Math.max(dragStartOffset - delta, 0), maxOffset);
      applyOffset(newOffset);
    });
  });

  function endDrag(event) {
    if (!isDragging) return;
    isDragging = false;
    dragSnapshot = null;
    if (hasDragged) {
      // 拖拽结束后吸附到最近的卡片
      // smoothScrollTo 会重新 setWillChange(true)，这里先关掉释放 GPU
      setWillChange(false);
      syncIndexFromOffset();
      scrollToCard(currentIndex);
      return;
    }
    // 纯点击（未拖动）：把被点击的卡片对齐到文字位置
    if (!event || event.type === 'pointercancel') {
      setWillChange(false);
      return;
    }
    // 使用 pointerdown 时记录的卡片，避免 elementFromPoint 触发重排
    if (!pointerDownCard) {
      setWillChange(false);
      return;
    }
    const index = getCardsList().indexOf(pointerDownCard);
    pointerDownCard = null;
    if (index < 0 || index === currentIndex) {
      setWillChange(false);
      return;
    }
    // 点击切换：保持 will-change 开启，直接由 smoothScrollTo 接管动画，
    // 避免 will-change 先关再开导致 GPU 合成层销毁重建（这是点击卡顿的主因）
    scrollToCard(index);
    // smoothScrollTo 会在动画结束时调用 setWillChange(false)
  }
  gallery?.addEventListener('pointerup', (e) => {
    try { gallery.releasePointerCapture(e.pointerId); } catch (_) {}
    endDrag(e);
  });
  gallery?.addEventListener('pointercancel', endDrag);

  // 阻止图片默认拖拽
  cardsContainer?.addEventListener('dragstart', (e) => e.preventDefault());

  // ResizeObserver：卡片容器尺寸变化时重新对齐当前卡片并更新箭头状态
  if (cardsContainer && typeof ResizeObserver !== 'undefined') {
    const resizeObserver = new ResizeObserver(() => {
      if (isAnimating || isDragging) return;
      invalidateLayout();
      syncAlignVar();
      const { cardCount } = measureLayout();
      if (currentIndex > cardCount - 1) currentIndex = Math.max(0, cardCount - 1);
      scrollToCard(currentIndex);
    });
    resizeObserver.observe(cardsContainer);
  }

  // 控制器延迟显示（内容先进入，控制器后出现 — Apple 基准 2.4）
  if (nav) {
    const navObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        setTimeout(() => nav.classList.add('is-visible'), 740);
        navObserver.unobserve(entry.target);
      });
    }, { threshold: 0.1 });
    navObserver.observe(nav);
  }

  // 初始监听素材加载
  attachMediaListeners();
  syncAlignVar();

  // 初始化箭头状态
  setTimeout(updateNavState, 100);
  setTimeout(updateNavState, 600);
  setTimeout(updateNavState, 1500);

  // 窗口尺寸变化：重新计算对齐位置并对齐当前卡片
  window.addEventListener('resize', () => {
    invalidateLayout();
    syncAlignVar();
    if (!isAnimating && !isDragging) scrollToCard(currentIndex);
    updateNavState();
  });

  // 后台配置更新后重新监听素材并更新状态
  window.addEventListener('message', (event) => {
    if (event.origin !== window.location.origin) return;
    if (event.data?.type === 'portfolio-config-update') {
      setTimeout(() => {
        invalidateLayout();
        cardsCache = null; // 卡片可能增减，失效缓存
        syncAlignVar();
        attachMediaListeners();
        const { cardCount } = measureLayout();
        if (currentIndex > cardCount - 1) currentIndex = Math.max(0, cardCount - 1);
        scrollToCard(currentIndex);
      }, 200);
      setTimeout(updateNavState, 800);
    }
  });
}
