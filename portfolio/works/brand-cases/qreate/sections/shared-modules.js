const DESKTOP_BREAKPOINT = 900;

// 全局轻提示弹框：黑色卡片 + 橙色描边，居中显示，点击任意处 / Esc / Enter / 2.2s 自动关闭
export function showSiteAlert(message) {
  const overlay = document.createElement('div');
  overlay.className = 'site-alert';
  overlay.setAttribute('role', 'alert');
  overlay.innerHTML = `<div class="site-alert__box">${message}</div>`;
  document.body.appendChild(overlay);

  // 强制重排以触发 transition
  void overlay.offsetWidth;
  overlay.classList.add('is-visible');

  const close = () => {
    overlay.classList.remove('is-visible');
    overlay.addEventListener('transitionend', () => overlay.remove(), { once: true });
    overlay.removeEventListener('click', close);
    document.removeEventListener('keydown', onKey);
    clearTimeout(timer);
  };

  const onKey = (event) => {
    if (event.key === 'Escape' || event.key === 'Enter') close();
  };

  overlay.addEventListener('click', close);
  document.addEventListener('keydown', onKey);
  const timer = setTimeout(close, 2200);
}

export function initScaledSection(root, designHeight) {
  const stages = root.querySelectorAll('.module-stage');
  if (!stages.length) return () => {};

  const resize = () => {
    if (window.innerWidth <= DESKTOP_BREAKPOINT) {
      root.style.removeProperty('height');
      root.style.removeProperty('--stage-viewport-width');
      root.style.removeProperty('--motion-stage-scale');
      stages.forEach((stage) => stage.style.removeProperty('transform'));
      return;
    }

    const scale = Math.min(window.innerWidth / 1920, 1);
    const stageViewportWidth = window.innerWidth / scale;
    root.style.height = `${Math.round(designHeight * scale)}px`;
    root.style.setProperty('--stage-viewport-width', `${stageViewportWidth}px`);
    root.style.setProperty('--motion-stage-scale', String(scale));
    stages.forEach((stage) => {
      stage.style.transform = `translateX(-50%) scale(${scale})`;
    });
  };

  resize();
  window.addEventListener('resize', resize, { passive: true });
  return () => window.removeEventListener('resize', resize);
}

export function initReveal(root) {
  const items = [...root.querySelectorAll('[data-reveal]')];
  if (!items.length) return;

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    items.forEach((item) => item.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      observer.unobserve(entry.target);
    });
  }, {
    threshold: 0.01,
    rootMargin: '0px 0px 0px 0px'
  });

  items.forEach((item) => observer.observe(item));
}

export function initGallery(root) {
  const scroller = root.querySelector('[data-gallery]');
  const dots = [...root.querySelectorAll('[data-gallery-dot]')];
  const playButton = root.querySelector('[data-gallery-play]');
  const controls = root.querySelector('.gallery-controls');
  if (!scroller) return;

  const cards = [...scroller.querySelectorAll('.gallery-card')];
  const track = scroller.firstElementChild;
  let startX = 0;
  let startScroll = 0;
  let dragging = false;
  let activeIndex = 0;
  let autoplayTimer = 0;
  let scrollFrame = 0;
  let motionFrame = 0;
  let trackTimer = 0;
  let trackX = 0;
  let autoplayStartTimer = 0;
  let hasAutoStarted = false;
  let userControlled = false;
  let pointerActive = false;
  let suppressClick = false;
  const DRAG_THRESHOLD = 5;

  const isDesktopGallery = () => window.innerWidth > DESKTOP_BREAKPOINT;
  const getLeadingInset = () => Number.parseFloat(getComputedStyle(track).paddingLeft) || 0;
  const getCardTarget = (card) => Math.max(card.offsetLeft - getLeadingInset(), 0);
  const getCardStep = () => cards.length > 1 ? cards[1].offsetLeft - cards[0].offsetLeft : cards[0]?.offsetWidth || 0;

  const restartProgress = () => {
    if (!controls || !autoplayTimer) return;
    controls.classList.remove('is-progressing');
    void controls.offsetWidth;
    controls.classList.add('is-progressing');
  };

  const setActive = (index) => {
    activeIndex = Math.max(0, Math.min(index, cards.length - 1));
    dots.forEach((dot, dotIndex) => {
      const selected = dotIndex === activeIndex;
      dot.classList.toggle('is-active', selected);
      dot.setAttribute('aria-selected', String(selected));
      dot.tabIndex = selected ? 0 : -1;
    });
    restartProgress();
  };

  const cancelScrollMotion = () => {
    window.cancelAnimationFrame(motionFrame);
    motionFrame = 0;
    scroller.classList.remove('is-animating');
  };

  const cancelTrackMotion = () => {
    if (trackTimer) {
      const matrix = new DOMMatrixReadOnly(getComputedStyle(track).transform);
      trackX = matrix.m41;
      track.style.transform = `translate3d(${trackX}px,0,0)`;
    }
    window.clearTimeout(trackTimer);
    trackTimer = 0;
    track.style.transition = 'none';
    scroller.classList.remove('is-animating');
  };

  const moveTrackTo = (index, animate = true) => {
    cancelTrackMotion();
    if (isDesktopGallery() && scroller.scrollLeft) {
      scroller.scrollLeft = 0;
    }
    const target = -(getCardStep() * index);
    trackX = target;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    track.style.transition = animate && !reduced
      ? 'transform 600ms cubic-bezier(.4,0,.2,1)'
      : 'none';
    track.style.transform = `translate3d(${target}px,0,0)`;
    if (animate && !reduced) {
      scroller.classList.add('is-animating');
      trackTimer = window.setTimeout(() => {
        trackTimer = 0;
        scroller.classList.remove('is-animating');
      }, 600);
    }
  };

  const animateScrollTo = (target) => {
    cancelScrollMotion();
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      scroller.scrollLeft = target;
      return;
    }

    const start = scroller.scrollLeft;
    const distance = target - start;
    const startedAt = performance.now();
    scroller.classList.add('is-animating');

    const step = (now) => {
      const progress = Math.min((now - startedAt) / 600, 1);
      const eased = -(Math.cos(Math.PI * progress) - 1) / 2;
      scroller.scrollLeft = start + distance * eased;
      if (progress < 1) {
        motionFrame = window.requestAnimationFrame(step);
        return;
      }
      motionFrame = 0;
      scroller.classList.remove('is-animating');
    };

    motionFrame = window.requestAnimationFrame(step);
  };

  const scrollToCard = (index, behavior = 'smooth') => {
    const card = cards[index];
    if (!card) return;
    if (isDesktopGallery()) {
      moveTrackTo(index, behavior !== 'auto');
      setActive(index);
      return;
    }
    const target = getCardTarget(card);
    if (behavior === 'auto') {
      cancelScrollMotion();
      scroller.scrollLeft = target;
    } else {
      animateScrollTo(target);
    }
    setActive(index);
  };

  const stopAutoplay = () => {
    window.clearInterval(autoplayTimer);
    autoplayTimer = 0;
    playButton?.classList.remove('is-playing');
    controls?.classList.remove('is-playing', 'is-progressing');
    playButton?.setAttribute('aria-pressed', 'false');
    playButton?.setAttribute('aria-label', '播放案例轮播');
  };

  const stopByUser = () => {
    userControlled = true;
    window.clearTimeout(autoplayStartTimer);
    autoplayStartTimer = 0;
    stopAutoplay();
  };

  const startAutoplay = () => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    stopAutoplay();
    playButton?.classList.add('is-playing');
    controls?.classList.add('is-playing');
    playButton?.setAttribute('aria-pressed', 'true');
    playButton?.setAttribute('aria-label', '暂停案例轮播');
    autoplayTimer = window.setInterval(() => {
      const nextIndex = activeIndex >= cards.length - 1 ? 0 : activeIndex + 1;
      scrollToCard(nextIndex);
    }, 4000);
    restartProgress();
  };

  scroller.addEventListener('pointerdown', (event) => {
    if (event.pointerType !== 'mouse') return;
    event.preventDefault();
    cancelScrollMotion();
    cancelTrackMotion();
    pointerActive = true;
    startX = event.clientX;
    startScroll = isDesktopGallery() ? trackX : scroller.scrollLeft;
    scroller.setPointerCapture(event.pointerId);
  });

  scroller.addEventListener('dragstart', (event) => event.preventDefault());

  scroller.addEventListener('pointermove', (event) => {
    if (!pointerActive) return;
    if (!dragging) {
      const dx = Math.abs(event.clientX - startX);
      if (dx < DRAG_THRESHOLD) return;
      dragging = true;
      stopByUser();
      scroller.classList.add('is-dragging');
    }
    const ratio = scroller.clientWidth / scroller.getBoundingClientRect().width;
    if (isDesktopGallery()) {
      const min = -(getCardStep() * (cards.length - 1));
      trackX = Math.max(min, Math.min(0, startScroll + ((event.clientX - startX) * ratio)));
      track.style.transform = `translate3d(${trackX}px,0,0)`;
      return;
    }
    scroller.scrollLeft = startScroll - ((event.clientX - startX) * ratio);
  });

  const finishDrag = (event) => {
    if (!pointerActive) return;
    pointerActive = false;
    if (dragging) {
      dragging = false;
      suppressClick = true;
      scroller.classList.remove('is-dragging');
      if (isDesktopGallery()) {
        const nextIndex = Math.max(0, Math.min(Math.round(-trackX / getCardStep()), cards.length - 1));
        scrollToCard(nextIndex);
        return;
      }
      const nearest = cards.reduce((best, card, index) => {
        const distance = Math.abs(getCardTarget(card) - scroller.scrollLeft);
        return distance < best.distance ? { index, distance } : best;
      }, { index: 0, distance: Number.POSITIVE_INFINITY });
      scrollToCard(nearest.index);
      return;
    }
    // 纯点击（未拖动）：切换到被点击的卡片
    if (!event || event.type === 'pointercancel') return;
    suppressClick = true;
    const target = document.elementFromPoint(event.clientX, event.clientY);
    if (!target) return;
    const card = target.closest('.gallery-card');
    if (!card) return;
    const index = cards.indexOf(card);
    if (index < 0 || index === activeIndex) return;
    stopByUser();
    scrollToCard(index);
  };

  scroller.addEventListener('pointerup', finishDrag);
  scroller.addEventListener('pointercancel', finishDrag);
  scroller.addEventListener('wheel', () => {
    cancelScrollMotion();
  }, { passive: true });

  scroller.addEventListener('scroll', () => {
    if (isDesktopGallery() && scroller.scrollLeft) {
      scroller.scrollLeft = 0;
      return;
    }
    if (scrollFrame) return;
    scrollFrame = window.requestAnimationFrame(() => {
      scrollFrame = 0;
      if (isDesktopGallery()) return;
      if (motionFrame) return;
      const nearest = cards.reduce((best, card, index) => {
        const distance = Math.abs(getCardTarget(card) - scroller.scrollLeft);
        return distance < best.distance ? { index, distance } : best;
      }, { index: 0, distance: Number.POSITIVE_INFINITY });
      setActive(nearest.index);
    });
  });

  scroller.addEventListener('keydown', (event) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    event.preventDefault();
    stopByUser();
    scrollToCard(activeIndex + (event.key === 'ArrowRight' ? 1 : -1));
  });

  dots.forEach((dot, index) => dot.addEventListener('click', () => {
    stopByUser();
    scrollToCard(index);
  }));

  scroller.addEventListener('click', (event) => {
    if (suppressClick) {
      suppressClick = false;
      return;
    }
    if (dragging) return;
    const card = event.target.closest('.gallery-card');
    if (!card) return;
    const index = cards.indexOf(card);
    if (index < 0 || index === activeIndex) return;
    stopByUser();
    scrollToCard(index);
  });

  playButton?.addEventListener('click', () => {
    userControlled = true;
    window.clearTimeout(autoplayStartTimer);
    autoplayStartTimer = 0;
    if (autoplayTimer) {
      stopAutoplay();
      return;
    }
    if (activeIndex >= cards.length - 1) scrollToCard(0);
    startAutoplay();
  });

  if (isDesktopGallery()) scroller.scrollLeft = 0;
  scrollToCard(0, 'auto');

  // 提前触发控件显示：当画廊底部进入视口时即显示控件
  if (controls && scroller && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    let controlsRevealed = false;
    let revealPending = false;
    const checkControlsReveal = () => {
      revealPending = false;
      if (controlsRevealed) return;
      const rect = scroller.getBoundingClientRect();
      if (rect.bottom <= window.innerHeight + 1) {
        controlsRevealed = true;
        controls.classList.add('is-visible');
        window.removeEventListener('scroll', onControlsScroll);
        window.removeEventListener('resize', onControlsScroll);
      }
    };
    const onControlsScroll = () => {
      if (revealPending || controlsRevealed) return;
      revealPending = true;
      requestAnimationFrame(checkControlsReveal);
    };
    window.addEventListener('scroll', onControlsScroll, { passive: true });
    window.addEventListener('resize', onControlsScroll, { passive: true });
    checkControlsReveal();
  }

  if (controls && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const autoplayObserver = new IntersectionObserver((entries) => {
      const entry = entries[0];
      const isVisible = Boolean(entry?.isIntersecting && entry.intersectionRatio >= 0.01);
      if (!isVisible) {
        window.clearTimeout(autoplayStartTimer);
        autoplayStartTimer = 0;
        if (autoplayTimer) stopAutoplay();
        return;
      }
      if (userControlled || autoplayTimer) return;
      const delay = hasAutoStarted ? 250 : 600;
      hasAutoStarted = true;
      autoplayStartTimer = window.setTimeout(() => {
        autoplayStartTimer = 0;
        if (!userControlled) startAutoplay();
      }, delay);
    }, { threshold: [0.01] });
    autoplayObserver.observe(controls);
  }
}
