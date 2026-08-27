import { moduleSchema } from './schema.js?v=10';

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

export async function loadSiteConfig() {
  const response = await fetch('./config/site-config.json?v=19');

  if (!response.ok) {
    throw new Error(`页面配置加载失败：${response.status}`);
  }

  return response.json();
}

function setMultilineText(element, value) {
  const lines = String(value).split('\n');
  const fragment = document.createDocumentFragment();

  lines.forEach((line, index) => {
    if (index > 0) {
      fragment.append(document.createElement('br'));
    }
    fragment.append(document.createTextNode(line));
  });

  element.replaceChildren(fragment);
}

function applyTextField(root, field, value) {
  if (field.all) {
    root.querySelectorAll(field.selector).forEach((element) => {
      applyTextFieldToElement(element, field, value);
    });
    return;
  }

  const element = root.querySelector(field.selector);

  if (!element || value === undefined || value === null) {
    return;
  }

  applyTextFieldToElement(element, field, value);
}

function applyTypography(root, field, typography) {
  const elements = field.all
    ? root.querySelectorAll(field.selector)
    : [root.querySelector(field.selector)].filter(Boolean);

  elements.forEach((element) => {
    const color = typography?.color || '';
    element.style.color = color;
    element.style.webkitTextFillColor = color;
    element.style.fontSize = Number.isFinite(typography?.sizePx)
      ? `${typography.sizePx}px`
      : '';
  });
}

function applyTextFieldToElement(element, field, value) {
  if (value === undefined || value === null) {
    return;
  }

  if (field.mode === 'lines') {
    setMultilineText(element, value);
    return;
  }

  if (field.preserveLastChild && element.lastElementChild) {
    const preservedChild = element.lastElementChild;
    element.replaceChildren(document.createTextNode(`${value} `), preservedChild);
    return;
  }

  element.textContent = String(value);
}

function applyModuleConfig(mountPoint, schema, moduleConfig = {}) {
  const root = mountPoint.querySelector(`[data-section="${schema.id}"]`);

  if (!root) {
    return;
  }

  root.hidden = moduleConfig.visible === false;

  for (const field of schema.content) {
    applyTextField(root, field, moduleConfig.content?.[field.key]);
    applyTypography(root, field, moduleConfig.typography?.[field.key]);
  }

  root.classList.toggle('config-motion-disabled', moduleConfig.motion?.enabled === false);

  if (schema.id === '04-cross-border-hero' && moduleConfig.motion?.enabled === false) {
    root.style.setProperty('--case-scale', '1');
    root.style.setProperty('--case-y', '0px');
    root.style.setProperty('--case-media-opacity', '1');
    root.style.setProperty('--case-copy-opacity', '1');
    root.style.setProperty('--case-copy-y', '0px');
  }

  if (schema.id === '08-brand-result' && moduleConfig.motion?.enabled === false) {
    root.style.setProperty('--brand-progress', '1');
    root.style.setProperty('--brand-summary-progress', '1');
  }

  if (schema.id === '09-brand-method' && moduleConfig.motion?.enabled === false) {
    root.style.setProperty('--method-word-size', '4960px');
    root.style.setProperty('--method-mask-opacity', '0');
    root.style.setProperty('--method-cover-opacity', '1');
    root.style.setProperty('--method-intro-opacity', '0');
    root.style.setProperty('--method-label-opacity', '0');
    root.style.setProperty('--method-large-opacity', '1');
    root.style.setProperty('--method-phone-progress', '1');
    root.style.setProperty('--method-phone-opacity', '1');
    root.style.setProperty('--method-scene-opacity', '0');
    root.style.setProperty('--method-final-phone-opacity', '0');
    root.style.setProperty('--method-detail-opacity', '1');
    root.style.setProperty('--method-detail-pan', '0');
  }

  for (const field of schema.motion) {
    if (!field.cssVar) {
      continue;
    }

    const value = moduleConfig.motion?.[field.key];
    if (typeof value === 'number' && Number.isFinite(value)) {
      root.style.setProperty(field.cssVar, `${value}${field.unit || ''}`);
    }
  }

  // 14-motion-cases：从 layout 配置渲染卡片
  if (schema.id === '14-motion-cases') {
    renderMotionCards(root, moduleConfig);
  }
}

function renderMotionCards(root, moduleConfig) {
  const container = root.querySelector('[data-motion-cards]');
  if (!container) return;

  const layout = moduleConfig.layout || {};
  const cards = Array.isArray(layout.cards) ? layout.cards : [];

  const cardHeight = Number.isFinite(layout.cardHeight) ? layout.cardHeight : 504;
  const gap = Number.isFinite(layout.gap) ? layout.gap : 20;
  root.style.setProperty('--motion-card-height', `${cardHeight}px`);
  root.style.setProperty('--motion-gap', `${gap}px`);

  // 保存滚动位置，避免重新渲染后跳回起点
  const gallery = root.querySelector('.motion-cases__gallery');
  const savedScrollLeft = gallery ? gallery.scrollLeft : 0;

  const existing = Array.from(container.children);

  if (existing.length === cards.length) {
    // 卡片数量未变 — 原地更新样式和内容，不重建 DOM
    cards.forEach((card, index) => {
      updateCardInPlace(existing[index], card);
    });
  } else {
    // 卡片数量变化 — 重建
    const fragment = document.createDocumentFragment();
    cards.forEach((card) => {
      const cardEl = document.createElement('div');
      cardEl.className = 'motion-cases__card';
      updateCardInPlace(cardEl, card);
      fragment.appendChild(cardEl);
    });
    container.replaceChildren(fragment);
  }

  // 恢复滚动位置
  if (gallery && gallery.scrollLeft !== savedScrollLeft) {
    gallery.scrollLeft = savedScrollLeft;
  }
}

// 原地更新单张卡片：仅修改样式/属性，不重建 DOM，保留视频播放状态
function updateCardInPlace(cardEl, card) {
  const sizeMode = card.sizeMode || 'fixed';

  // 尺寸模式 class
  cardEl.classList.toggle('is-free', sizeMode === 'free');

  if (sizeMode === 'free') {
    const scale = Number.isFinite(card.materialScale) ? card.materialScale : 1;
    cardEl.style.setProperty('--motion-material-scale', String(scale));
    // 卡片宽度（自由模式独有）— 未设置时使用默认 400px
    cardEl.style.width = Number.isFinite(card.cardWidth) ? `${card.cardWidth}px` : '400px';
    // 卡片高度始终使用全局 cardHeight（CSS 变量），不单独设置
    cardEl.style.height = '';
    // 素材位置偏移
    const offsetX = Number.isFinite(card.offsetX) ? card.offsetX : 0;
    const offsetY = Number.isFinite(card.offsetY) ? card.offsetY : 0;
    cardEl.style.setProperty('--motion-offset-x', `${offsetX}px`);
    cardEl.style.setProperty('--motion-offset-y', `${offsetY}px`);
  } else {
    // 清除自由模式残留样式
    cardEl.style.width = '';
    cardEl.style.height = '';
    cardEl.style.removeProperty('--motion-material-scale');
    cardEl.style.removeProperty('--motion-offset-x');
    cardEl.style.removeProperty('--motion-offset-y');
  }

  // 更新素材（img / video）
  const existingMedia = cardEl.querySelector('img, video');
  const existingPlaceholder = cardEl.querySelector('.motion-cases__card-placeholder');

  if (card.src) {
    const isVideo = /\.mp4$/i.test(card.src);
    const tagName = isVideo ? 'VIDEO' : 'IMG';

    if (existingPlaceholder) existingPlaceholder.remove();

    if (existingMedia && existingMedia.tagName === tagName) {
      // 复用已有元素，仅在 src 变化时更新
      if (existingMedia.getAttribute('src') !== card.src) {
        existingMedia.src = card.src;
      }
      existingMedia.alt = card.alt || '';
    } else {
      if (existingMedia) existingMedia.remove();
      const media = document.createElement(tagName.toLowerCase());
      media.src = card.src;
      media.alt = card.alt || '';
      media.style.webkitUserDrag = 'none';
      if (isVideo) {
        media.muted = true;
        media.loop = true;
        media.autoplay = true;
        media.playsInline = true;
      }
      cardEl.insertBefore(media, cardEl.firstChild);
    }
    cardEl.classList.remove('is-empty');
  } else {
    if (existingMedia) existingMedia.remove();
    cardEl.classList.add('is-empty');
    if (!existingPlaceholder) {
      const placeholder = document.createElement('div');
      placeholder.className = 'motion-cases__card-placeholder';
      placeholder.textContent = '待上传素材';
      cardEl.insertBefore(placeholder, cardEl.firstChild);
    }
  }

  // 更新标题
  const existingCaption = cardEl.querySelector('.motion-cases__card-caption');
  if (card.caption || card.description) {
    let caption = existingCaption;
    if (!caption) {
      caption = document.createElement('div');
      caption.className = 'motion-cases__card-caption';
      cardEl.appendChild(caption);
    }
    caption.replaceChildren();
    if (card.caption) {
      const h3 = document.createElement('h3');
      h3.textContent = card.caption;
      caption.appendChild(h3);
    }
    if (card.description) {
      const p = document.createElement('p');
      p.textContent = card.description;
      caption.appendChild(p);
    }
  } else if (existingCaption) {
    existingCaption.remove();
  }
}

export function applySiteConfig(mountPoint, config) {
  if (!mountPoint || !isPlainObject(config?.modules)) {
    return;
  }

  for (const schema of moduleSchema) {
    applyModuleConfig(mountPoint, schema, config.modules[schema.id]);
  }
}

function revealSection(root) {
  root.classList.remove('is-visible');
  void root.offsetWidth;
  root.classList.add('is-visible');

  if (root.matches('[data-section="02-hero"]')) {
    root.classList.remove('is-playing');
    void root.offsetWidth;
    root.classList.add('is-playing');
  }
}

export function installConfigPreviewBridge(mountPoint) {
  window.addEventListener('message', (event) => {
    if (event.origin !== window.location.origin || !isPlainObject(event.data)) {
      return;
    }

    if (event.data.type === 'portfolio-config-update') {
      applySiteConfig(mountPoint, event.data.config);
      window.dispatchEvent(new Event('scroll'));
    }

    if (event.data.type === 'portfolio-preview-focus') {
      const root = mountPoint.querySelector(`[data-section="${event.data.moduleId}"]`);
      root?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    if (event.data.type === 'portfolio-preview-replay') {
      const root = mountPoint.querySelector(`[data-section="${event.data.moduleId}"]`);
      if (root) {
        if (event.data.moduleId === '04-cross-border-hero') {
          window.scrollTo({ top: root.offsetTop, behavior: 'smooth' });
        } else if (event.data.moduleId === '08-brand-result' || event.data.moduleId === '09-brand-method') {
          window.scrollTo({
            top: Math.max(root.offsetTop - window.innerHeight * 0.8, 0),
            behavior: 'smooth'
          });
        } else {
          revealSection(root);
        }
      }
    }
  });

}
