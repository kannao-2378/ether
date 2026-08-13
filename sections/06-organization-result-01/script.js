import { showSiteAlert } from '../shared-modules.js?v=11';

export function init(root) {
  // CTA 拦截：弹出"暂未开启"提示
  const cta = root.querySelector('.org-v2__cta');
  if (cta) {
    cta.addEventListener('click', (event) => {
      event.preventDefault();
      showSiteAlert('对不起，暂未开启');
    });
  }

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    || root.classList.contains('config-motion-disabled');
  const isMobile = () => window.innerWidth <= 900;

  if (reduceMotion || isMobile()) return;

  const visual = root.querySelector('.org-v2__visual');
  const content = root.querySelector('.org-v2__content');
  if (!visual || !content) return;

  // 图片自然尺寸（4K）
  const IMG_W = 3840;
  const IMG_H = 2560;

  // Figma 基准（1920×1280 画板），运行时按视口等比缩放
  const FIG_H = 1280;
  const FIG_TARGET_W = 1292;
  const FIG_TARGET_H = 861;
  const FIG_FINAL_LEFT = -521;
  const FIG_FINAL_TOP = 140;
  const FIG_CONTENT_TOP = 294;
  const FIG_CONTENT_LEFT = 902;
  const CTA_GAP = 140; // 图片底部到 CTA 的间距（Figma 基准，按 s 缩放）

  // 三阶段分界点
  const STAGE1_END = 0.4;  // 阶段1：图片居中缩放（文字/CTA 隐藏）
  const STAGE2_END = 0.75; // 阶段2：图片左移 + 文字滑入（CTA 隐藏）
  // 阶段3（0.75→1）：CTA 居中弹出

  let ticking = false;

  // 文字缩放原点设为左上角，配合 scale(s) 实现整体等比缩放
  content.style.transformOrigin = '0 0';

  // 初始隐藏
  content.style.opacity = '0';
  if (cta) {
    cta.style.opacity = '0';
    cta.style.transform = 'translateX(-50%) scale(0.6)';
  }

  const update = () => {
    ticking = false;
    const rect = root.getBoundingClientRect();
    const scrollable = root.offsetHeight - window.innerHeight;
    if (scrollable <= 0) return;

    const progress = Math.max(0, Math.min(1, -rect.top / scrollable));
    const viewportW = window.innerWidth;
    const viewportH = window.innerHeight;

    // 等比缩放因子：以视口高度为基准（Figma 画板高 1280），不超过 1
    const s = Math.min(1, viewportH / FIG_H);

    // 缩放后的图片目标尺寸与位置
    const TARGET_W = FIG_TARGET_W * s;
    const TARGET_H = FIG_TARGET_H * s;
    const FINAL_LEFT = FIG_FINAL_LEFT * s;
    const FINAL_TOP = FIG_FINAL_TOP * s;

    // 文字位置同步缩放（CSS 中是 Figma 绝对值，这里覆盖）
    content.style.top = (FIG_CONTENT_TOP * s) + 'px';
    content.style.left = (FIG_CONTENT_LEFT * s) + 'px';

    // CTA 顶部 = 图片实际底部 + 间距（图片垂直居中在 sticky 中，
    // sticky 高 100vh+40px，所以图片底部 = stickyH/2 + TARGET_H/2）
    // 若间距过大导致 CTA 超出视口，自动缩减间距保证 CTA 可见。
    if (cta) {
      const stickyH = viewportH + 40;
      const imageBottom = stickyH / 2 + TARGET_H / 2;
      const desiredTop = imageBottom + CTA_GAP * s;
      const maxTop = viewportH - 56 - 20; // CTA 高 56px + 底部留 20px
      cta.style.top = Math.min(desiredTop, maxTop) + 'px';
    }

    const scaleEnd = TARGET_W / IMG_W;
    const initCenterX = viewportW / 2;
    const initCenterY = viewportH / 2;
    const finalCenterX = FINAL_LEFT + TARGET_W / 2;
    const finalCenterY = FINAL_TOP + TARGET_H / 2;

    // ---- 图片：阶段1居中缩放，阶段2只横向左移（不垂直移动）----
    let scale, tx, ty;
    if (progress <= STAGE1_END) {
      const p1 = progress / STAGE1_END;
      scale = 1 + (scaleEnd - 1) * p1;
      tx = 0;
      ty = 0;
    } else {
      const p2 = Math.min(1, (progress - STAGE1_END) / (STAGE2_END - STAGE1_END));
      scale = scaleEnd;
      tx = (finalCenterX - initCenterX) * p2;
      ty = 0;
    }
    visual.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;

    // ---- 文字：阶段1隐藏，阶段2与图片同步左移，整体按 s 缩放 ----
    const textStage1Offset = initCenterX - finalCenterX;
    let contentTx, contentOpacity;
    if (progress <= STAGE1_END) {
      contentTx = textStage1Offset;
      contentOpacity = 0;
    } else if (progress <= STAGE2_END) {
      const p2 = (progress - STAGE1_END) / (STAGE2_END - STAGE1_END);
      contentTx = textStage1Offset * (1 - p2);
      contentOpacity = Math.min(1, p2 * 3);
    } else {
      contentTx = 0;
      contentOpacity = 1;
    }
    content.style.opacity = contentOpacity;
    content.style.transform = `translateX(${contentTx}px) scale(${s})`;

    // ---- CTA：阶段3弹出（垂直位置由 JS 根据图片底部动态计算） ----
    if (cta) {
      let ctaScale, ctaOpacity;
      if (progress <= STAGE2_END) {
        ctaScale = 0.6;
        ctaOpacity = 0;
      } else {
        const p3 = (progress - STAGE2_END) / (1 - STAGE2_END);
        const eased = 1 - Math.pow(1 - p3, 3);
        ctaScale = 0.6 + 0.4 * eased;
        ctaOpacity = Math.min(1, p3 * 2.5);
      }
      cta.style.opacity = ctaOpacity;
      cta.style.transform = `translateX(-50%) scale(${ctaScale})`;
    }
  };

  const onScroll = () => {
    if (!ticking) {
      window.requestAnimationFrame(update);
      ticking = true;
    }
  };

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  update();
}
