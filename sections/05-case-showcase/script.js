export function init(root) {
  const tabs = Array.from(root.querySelectorAll('[data-case]'));
  const panels = Array.from(root.querySelectorAll('[data-case-panel]'));
  const tabList = root.querySelector('.case-showcase__tabs');
  const indicator = root.querySelector('.case-showcase__indicator');
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    || root.classList.contains('config-motion-disabled');

  function createSyncGroup(comparison) {
    const panes = Array.from(comparison.querySelectorAll('[data-sync-pane]'));
    const assignedScrollTops = new WeakMap();
    let pendingSource = null;
    let frame = 0;

    function syncFrom(source) {
      const sourceMax = Math.max(0, source.scrollHeight - source.clientHeight);
      const progress = sourceMax > 0 ? source.scrollTop / sourceMax : 0;

      panes.forEach((target) => {
        if (target === source) return;
        const targetMax = Math.max(0, target.scrollHeight - target.clientHeight);
        const targetTop = progress * targetMax;
        assignedScrollTops.set(target, targetTop);
        target.scrollTop = targetTop;
      });
    }

    function queueSync(source) {
      const assignedTop = assignedScrollTops.get(source);
      if (assignedTop !== undefined && Math.abs(source.scrollTop - assignedTop) < 1) {
        assignedScrollTops.delete(source);
        return;
      }

      assignedScrollTops.delete(source);
      pendingSource = source;
      if (frame) return;

      frame = window.requestAnimationFrame(() => {
        frame = 0;
        const activeSource = pendingSource;
        pendingSource = null;
        if (activeSource) syncFrom(activeSource);
      });
    }

    panes.forEach((pane) => {
      pane.addEventListener('scroll', () => queueSync(pane), { passive: true });
    });

    return {
      comparison,
      syncFromFirst() {
        if (panes[0]) syncFrom(panes[0]);
      }
    };
  }

  const syncGroups = Array.from(root.querySelectorAll('[data-sync-comparison]'))
    .map(createSyncGroup);

  function setReplayVisible(button, visible) {
    if (!button) return;
    button.classList.toggle('is-visible', visible);
    button.setAttribute('aria-hidden', String(!visible));
    button.tabIndex = visible ? 0 : -1;
  }

  function playVideo(video) {
    const replayButton = video.parentElement?.querySelector('[data-video-replay]');
    setReplayVisible(replayButton, false);

    try {
      video.currentTime = 0;
      const playback = video.play();
      playback?.catch(() => setReplayVisible(replayButton, true));
    } catch {
      setReplayVisible(replayButton, true);
    }
  }

  root.querySelectorAll('[data-video-replay]').forEach((button) => {
    const video = button.parentElement?.querySelector('video');
    if (!video) return;

    button.addEventListener('click', () => playVideo(video));
    video.addEventListener('play', () => setReplayVisible(button, false));
    video.addEventListener('ended', () => setReplayVisible(button, true));
    video.addEventListener('error', () => setReplayVisible(button, true));

    if (reduceMotion) setReplayVisible(button, true);
  });

  function updatePanelVideos(activePanel) {
    panels.forEach((panel) => {
      panel.querySelectorAll('video').forEach((video) => video.pause());
    });

    if (!activePanel || reduceMotion) return;

    activePanel.querySelectorAll('video').forEach((video) => {
      const playFromStart = () => {
        if (!activePanel.classList.contains('is-active')) return;
        playVideo(video);
      };

      if (video.readyState >= 2) playFromStart();
      else video.addEventListener('canplay', playFromStart, { once: true });
    });
  }

  function updateIndicator(tab, animate = true) {
    if (indicator && tab) {
      if (!animate) {
        indicator.style.transition = 'none';
      }

      indicator.style.left = `${tab.offsetLeft}px`;
      indicator.style.width = `${tab.offsetWidth}px`;

      if (!animate) {
        void indicator.offsetWidth;
        indicator.style.removeProperty('transition');
      }
    }
  }

  function centerTab(tab, behavior) {
    if (!tabList || !tab) return;
    tabList.scrollTo({
      left: tab.offsetLeft - (tabList.clientWidth - tab.offsetWidth) / 2,
      behavior
    });
  }

  function selectCase(tab, shouldFocus = false) {
    if (!tab || tab.classList.contains('is-active')) return;

    const selectedCase = tab.dataset.case;
    const nextPanel = panels.find((panel) => panel.dataset.casePanel === selectedCase);

    tabs.forEach((item) => {
      const selected = item === tab;
      item.classList.toggle('is-active', selected);
      item.setAttribute('aria-selected', String(selected));
      item.setAttribute('tabindex', selected ? '0' : '-1');
    });

    panels.forEach((panel) => {
      const selected = panel === nextPanel;
      panel.classList.toggle('is-active', selected);
      panel.setAttribute('aria-hidden', String(!selected));
    });

    updateIndicator(tab);
    centerTab(tab, reduceMotion ? 'auto' : 'smooth');
    window.requestAnimationFrame(() => {
      syncGroups
        .filter((group) => nextPanel?.contains(group.comparison))
        .forEach((group) => group.syncFromFirst());
    });
    updatePanelVideos(nextPanel);
    if (shouldFocus) tab.focus();
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectCase(tab));
    tab.addEventListener('keydown', (event) => {
      let nextIndex = index;

      if (event.key === 'ArrowRight') nextIndex = (index + 1) % tabs.length;
      else if (event.key === 'ArrowLeft') nextIndex = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === 'Home') nextIndex = 0;
      else if (event.key === 'End') nextIndex = tabs.length - 1;
      else return;

      event.preventDefault();
      selectCase(tabs[nextIndex], true);
    });
  });

  const initialTab = root.querySelector('.case-showcase__tab.is-active');
  updateIndicator(initialTab, false);

  window.addEventListener('resize', () => {
    updateIndicator(root.querySelector('.case-showcase__tab.is-active'), false);
    syncGroups
      .filter((group) => group.comparison.closest('[data-case-panel]')?.classList.contains('is-active'))
      .forEach((group) => group.syncFromFirst());
  });

  function reveal() {
    root.classList.add('is-visible');
    centerTab(initialTab, 'auto');
  }

  if (reduceMotion || !('IntersectionObserver' in window)) {
    reveal();
  } else {
    const observer = new IntersectionObserver((entries) => {
      if (!entries[0].isIntersecting) return;
      reveal();
      observer.disconnect();
    }, { threshold: 0.15 });
    observer.observe(root);
  }
}
