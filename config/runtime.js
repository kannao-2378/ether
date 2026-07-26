import { moduleSchema } from './schema.js?v=2';

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

export async function loadSiteConfig() {
  const response = await fetch('./config/site-config.json?v=5');

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

  for (const field of schema.motion) {
    if (!field.cssVar) {
      continue;
    }

    const value = moduleConfig.motion?.[field.key];
    if (typeof value === 'number' && Number.isFinite(value)) {
      root.style.setProperty(field.cssVar, `${value}${field.unit || ''}`);
    }
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
        } else {
          revealSection(root);
        }
      }
    }
  });

}
