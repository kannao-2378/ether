import { moduleSchema } from '../config/schema.js?v=2';

const elements = {
  moduleList: document.querySelector('#moduleList'),
  moduleIndex: document.querySelector('#moduleIndex'),
  moduleTitle: document.querySelector('#moduleTitle'),
  moduleDescription: document.querySelector('#moduleDescription'),
  contentFields: document.querySelector('#contentFields'),
  motionFields: document.querySelector('#motionFields'),
  saveStatus: document.querySelector('#saveStatus'),
  saveButton: document.querySelector('#saveButton'),
  resetButton: document.querySelector('#resetButton'),
  adminSecret: document.querySelector('#adminSecret'),
  previewStage: document.querySelector('#previewStage'),
  previewCanvas: document.querySelector('#previewCanvas'),
  previewFrame: document.querySelector('#previewFrame'),
  previewMeta: document.querySelector('#previewMeta'),
  previewWidth: document.querySelector('#previewWidth'),
  previewHeight: document.querySelector('#previewHeight'),
  replayButton: document.querySelector('#replayButton'),
  toast: document.querySelector('#toast'),
  publishNote: document.querySelector('.publish-note')
};

const devices = {
  desktop: { width: 1280, height: 720, label: '桌面' },
  mobile: { width: 390, height: 844, label: '手机' }
};

const isLocalEnvironment = ['localhost', '127.0.0.1', '::1'].includes(location.hostname);
let publishedConfig;
let config;
let activeModuleId = moduleSchema[0].id;
let previewSize = { ...devices.desktop };
let previewScale = 1;
let dirty = false;
let toastTimer;
let previewSaveTimer;
let localSaveEndpoint = null;

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function showToast(message) {
  clearTimeout(toastTimer);
  elements.toast.textContent = message;
  elements.toast.classList.add('is-visible');
  toastTimer = setTimeout(() => elements.toast.classList.remove('is-visible'), 2600);
}

function setDirty(nextDirty, savedMessage) {
  dirty = nextDirty;
  elements.saveStatus.textContent = dirty
    ? '有未保存修改'
    : savedMessage || (isLocalEnvironment ? '本地配置已同步' : '线上配置已同步');
  elements.saveStatus.classList.toggle('is-dirty', dirty);
  elements.saveButton.disabled = !dirty;
}

function configsDiffer() {
  return JSON.stringify(config) !== JSON.stringify(publishedConfig);
}

function getActiveSchema() {
  return moduleSchema.find((item) => item.id === activeModuleId);
}

function postToPreview(type, details = {}) {
  elements.previewFrame.contentWindow?.postMessage(
    { type, ...details },
    window.location.origin
  );
}

function syncPreview({ focus = false } = {}) {
  postToPreview('portfolio-config-update', { config });
  if (focus) {
    setTimeout(() => {
      postToPreview('portfolio-preview-focus', { moduleId: activeModuleId });
    }, 60);
  }
}

function updateValue(section, key, value) {
  config.modules[activeModuleId][section][key] = value;
  setDirty(true);
  syncPreview();
}

function updateTypography(key, property, value) {
  const moduleConfig = config.modules[activeModuleId];
  moduleConfig.typography ||= {};
  moduleConfig.typography[key] ||= {};

  if (value === null || value === '') {
    delete moduleConfig.typography[key][property];
  } else {
    moduleConfig.typography[key][property] = value;
  }

  if (Object.keys(moduleConfig.typography[key]).length === 0) {
    delete moduleConfig.typography[key];
  }

  setDirty(true);
  syncPreview();
}

function toggleModuleVisibility(moduleId) {
  const moduleConfig = config.modules[moduleId];
  moduleConfig.visible = moduleConfig.visible === false;
  setDirty(true);
  renderModuleList();
  syncPreview({ focus: moduleConfig.visible && moduleId === activeModuleId });
}

function createTextField(field, value) {
  const wrapper = document.createElement('div');
  wrapper.className = 'field';

  const label = document.createElement('label');
  label.className = 'field__label';
  label.textContent = field.label;

  const input = document.createElement(field.type === 'textarea' ? 'textarea' : 'input');
  if (input instanceof HTMLInputElement) input.type = 'text';
  input.id = `field-${activeModuleId}-${field.key}`;
  label.htmlFor = input.id;
  input.value = value ?? '';
  input.addEventListener('input', () => updateValue('content', field.key, input.value));

  const style = config.modules[activeModuleId].typography?.[field.key] || {};
  const controls = document.createElement('div');
  controls.className = 'text-style-controls';

  const colorLabel = document.createElement('label');
  colorLabel.className = 'text-style-control text-style-control--color';
  colorLabel.title = '文字颜色';
  const colorName = document.createElement('span');
  colorName.textContent = '颜色';
  const colorInput = document.createElement('input');
  colorInput.type = 'color';
  colorInput.value = /^#[0-9a-f]{6}$/i.test(style.color || '') ? style.color : '#ffffff';
  colorInput.classList.toggle('is-default', !style.color);
  colorInput.addEventListener('input', () => {
    colorInput.classList.remove('is-default');
    updateTypography(field.key, 'color', colorInput.value);
  });
  colorLabel.append(colorName, colorInput);

  const sizeLabel = document.createElement('label');
  sizeLabel.className = 'text-style-control text-style-control--size';
  const sizeName = document.createElement('span');
  sizeName.textContent = '字号';
  const sizeInput = document.createElement('input');
  sizeInput.type = 'number';
  sizeInput.min = '8';
  sizeInput.max = '160';
  sizeInput.step = '1';
  sizeInput.placeholder = '默认';
  sizeInput.value = Number.isFinite(style.sizePx) ? style.sizePx : '';
  sizeInput.addEventListener('input', () => {
    const parsed = Number(sizeInput.value);
    if (sizeInput.value !== '' && !Number.isFinite(parsed)) return;
    updateTypography(
      field.key,
      'sizePx',
      sizeInput.value === '' ? null : Math.min(160, Math.max(8, parsed))
    );
  });
  sizeLabel.append(sizeName, sizeInput);

  const resetButton = document.createElement('button');
  resetButton.type = 'button';
  resetButton.className = 'text-style-reset';
  resetButton.textContent = '跟随设计';
  resetButton.disabled = !style.color && !Number.isFinite(style.sizePx);
  resetButton.addEventListener('click', () => {
    const moduleConfig = config.modules[activeModuleId];
    if (moduleConfig.typography) {
      delete moduleConfig.typography[field.key];
    }
    setDirty(true);
    renderInspector();
    syncPreview();
  });

  controls.append(colorLabel, sizeLabel, resetButton);
  wrapper.append(label, input, controls);
  return wrapper;
}

function createToggleField(field, value) {
  const wrapper = document.createElement('div');
  wrapper.className = 'toggle-control';

  const label = document.createElement('span');
  label.className = 'field__label';
  label.textContent = field.label;

  const switchLabel = document.createElement('label');
  switchLabel.className = 'toggle-control__switch';

  const input = document.createElement('input');
  input.type = 'checkbox';
  input.checked = value !== false;
  input.addEventListener('change', () => updateValue('motion', field.key, input.checked));

  const track = document.createElement('span');
  track.className = 'toggle-control__track';
  switchLabel.append(input, track);
  wrapper.append(label, switchLabel);
  return wrapper;
}

function createNumberField(field, value) {
  const wrapper = document.createElement('label');
  wrapper.className = 'field';

  const header = document.createElement('span');
  header.className = 'field__header';

  const label = document.createElement('span');
  label.className = 'field__label';
  label.textContent = field.label;

  const meta = document.createElement('span');
  meta.className = 'field__meta';
  meta.textContent = `${field.min}—${field.max}${field.unit || ''}`;
  header.append(label, meta);

  const control = document.createElement('span');
  control.className = 'number-control';

  const range = document.createElement('input');
  range.type = 'range';
  range.min = field.min;
  range.max = field.max;
  range.step = field.step;
  range.value = value;

  const number = document.createElement('input');
  number.type = 'number';
  number.min = field.min;
  number.max = field.max;
  number.step = field.step;
  number.value = value;

  function commit(rawValue) {
    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) return;
    const clamped = Math.min(field.max, Math.max(field.min, parsed));
    range.value = clamped;
    number.value = clamped;
    updateValue('motion', field.key, clamped);
  }

  range.addEventListener('input', () => commit(range.value));
  number.addEventListener('input', () => commit(number.value));
  control.append(range, number);
  wrapper.append(header, control);
  return wrapper;
}

function renderModuleList() {
  elements.moduleList.replaceChildren();

  for (const schema of moduleSchema) {
    const moduleConfig = config.modules[schema.id];
    const isVisible = moduleConfig.visible !== false;
    const row = document.createElement('div');
    row.className = 'module-row';
    row.classList.toggle('is-hidden', !isVisible);

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'module-button';
    button.classList.toggle('is-active', schema.id === activeModuleId);

    const label = document.createElement('span');
    label.className = 'module-button__label';
    label.textContent = schema.label;

    const description = document.createElement('span');
    description.className = 'module-button__description';
    description.textContent = schema.description;
    button.append(label, description);
    button.addEventListener('click', () => {
      activeModuleId = schema.id;
      render();
      syncPreview({ focus: isVisible });
    });

    const visibilityButton = document.createElement('button');
    visibilityButton.type = 'button';
    visibilityButton.className = 'module-visibility';
    visibilityButton.textContent = isVisible ? '隐藏' : '显示';
    visibilityButton.setAttribute('aria-label', `${isVisible ? '隐藏' : '显示'}${schema.label}`);
    visibilityButton.setAttribute('aria-pressed', String(isVisible));
    visibilityButton.addEventListener('click', () => toggleModuleVisibility(schema.id));

    row.append(button, visibilityButton);
    elements.moduleList.append(row);
  }
}

function renderInspector() {
  const schema = getActiveSchema();
  const moduleConfig = config.modules[schema.id];
  const [index, title] = schema.label.split(' · ');

  elements.moduleIndex.textContent = index;
  elements.moduleTitle.textContent = title;
  elements.moduleDescription.textContent = schema.description;
  elements.contentFields.replaceChildren();
  elements.motionFields.replaceChildren();

  for (const field of schema.content) {
    elements.contentFields.append(createTextField(field, moduleConfig.content[field.key]));
  }

  for (const field of schema.motion) {
    elements.motionFields.append(
      field.type === 'toggle'
        ? createToggleField(field, moduleConfig.motion[field.key])
        : createNumberField(field, moduleConfig.motion[field.key])
    );
  }
}

function render() {
  renderModuleList();
  renderInspector();
}

function clampPreviewSize(width, height) {
  return {
    width: Math.round(Math.min(1920, Math.max(320, width))),
    height: Math.round(Math.min(1200, Math.max(420, height)))
  };
}

function resizePreview(width = previewSize.width, height = previewSize.height, shouldSaveSize = false) {
  previewSize = clampPreviewSize(width, height);
  const bounds = elements.previewStage.getBoundingClientRect();
  const margin = 34;
  previewScale = Math.min(
    (bounds.width - margin * 2) / previewSize.width,
    (bounds.height - margin * 2) / previewSize.height,
    1
  );
  previewScale = Math.max(previewScale, .1);

  elements.previewCanvas.style.width = `${previewSize.width}px`;
  elements.previewCanvas.style.height = `${previewSize.height}px`;
  elements.previewCanvas.style.transform = `translate(-50%, -50%) scale(${previewScale})`;
  elements.previewWidth.value = previewSize.width;
  elements.previewHeight.value = previewSize.height;
  elements.previewMeta.textContent = `自由预览 · ${previewSize.width} × ${previewSize.height}`;

  if (shouldSaveSize && config) {
    config.preview = {
      width: previewSize.width,
      height: previewSize.height
    };
    setDirty(true);
    schedulePreviewSizeSave();
  }
}

function schedulePreviewSizeSave() {
  if (!isLocalEnvironment || !localSaveEndpoint) return;
  clearTimeout(previewSaveTimer);
  previewSaveTimer = setTimeout(savePreviewSize, 500);
}

async function savePreviewSize() {
  try {
    const endpoint = new URL('/api/preview-size', localSaveEndpoint).href;
    const response = await fetch(endpoint, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify(config.preview)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || '预览尺寸保存失败');

    publishedConfig.preview = clone(config.preview);
    setDirty(configsDiffer(), configsDiffer() ? undefined : '预览尺寸已自动保存');
  } catch (error) {
    console.error(error);
  }
}

async function detectLocalSaveEndpoint() {
  const candidates = [
    `${location.origin}/api/site-config`,
    'http://127.0.0.1:8001/api/site-config'
  ];

  for (const candidate of candidates) {
    try {
      const response = await fetch(candidate, { cache: 'no-store' });
      if (response.ok) return candidate;
    } catch {
      // Continue to the fallback local writer.
    }
  }

  return null;
}

function installResizeHandles() {
  document.querySelectorAll('[data-resize]').forEach((handle) => {
    handle.addEventListener('pointerdown', (event) => {
      event.preventDefault();
      const direction = handle.dataset.resize;
      const start = {
        x: event.clientX,
        y: event.clientY,
        width: previewSize.width,
        height: previewSize.height,
        scale: previewScale
      };

      handle.setPointerCapture(event.pointerId);

      function move(moveEvent) {
        const deltaX = (moveEvent.clientX - start.x) / start.scale;
        const deltaY = (moveEvent.clientY - start.y) / start.scale;
        let width = start.width;
        let height = start.height;

        if (direction.includes('e')) width += deltaX * 2;
        if (direction.includes('w')) width -= deltaX * 2;
        if (direction.includes('s')) height += deltaY * 2;
        if (direction.includes('n')) height -= deltaY * 2;
        document.querySelectorAll('[data-device]').forEach((item) => item.classList.remove('is-active'));
        resizePreview(width, height, true);
      }

      function stop(stopEvent) {
        handle.releasePointerCapture(stopEvent.pointerId);
        handle.removeEventListener('pointermove', move);
        handle.removeEventListener('pointerup', stop);
        handle.removeEventListener('pointercancel', stop);
      }

      handle.addEventListener('pointermove', move);
      handle.addEventListener('pointerup', stop);
      handle.addEventListener('pointercancel', stop);
    });
  });
}

async function saveConfirmed() {
  if (!dirty) return;

  const endpoint = isLocalEnvironment
    ? localSaveEndpoint
    : '/.netlify/functions/site-config';
  const headers = { 'Content-Type': 'application/json' };

  if (!isLocalEnvironment) {
    if (!elements.adminSecret.value) {
      elements.adminSecret.focus();
      showToast('请输入后台密钥后再保存');
      return;
    }
    headers['X-Admin-Secret'] = elements.adminSecret.value;
  } else if (!endpoint) {
    showToast('本地保存服务未连接，请运行 npm run dev');
    return;
  }

  elements.saveButton.disabled = true;
  elements.saveButton.textContent = '保存中…';

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(config)
    });
    const result = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(result.error || `保存失败（${response.status}）`);
    }

    publishedConfig = clone(config);
    setDirty(false, isLocalEnvironment ? '已写入本地文件' : '已提交 GitHub');
    showToast(isLocalEnvironment ? '配置已写入本地项目' : '配置已提交，Netlify 正在部署');
  } catch (error) {
    console.error(error);
    setDirty(true);
    showToast(
      isLocalEnvironment && error.message.includes('404')
        ? '请使用 npm run dev 启动本地配置服务'
        : error.message
    );
  } finally {
    elements.saveButton.textContent = '确认保存';
    elements.saveButton.disabled = !dirty;
  }
}

async function start() {
  const response = await fetch('./config/site-config.json?v=5');
  if (!response.ok) throw new Error(`配置加载失败：${response.status}`);

  publishedConfig = await response.json();
  config = clone(publishedConfig);
  if (isLocalEnvironment) {
    localSaveEndpoint = await detectLocalSaveEndpoint();
  }
  previewSize = clampPreviewSize(
    config.preview?.width || devices.desktop.width,
    config.preview?.height || devices.desktop.height
  );
  render();
  resizePreview(previewSize.width, previewSize.height);
  installResizeHandles();
  setDirty(false);

  if (isLocalEnvironment) {
    elements.adminSecret.closest('.admin-secret').hidden = true;
    elements.publishNote.innerHTML = localSaveEndpoint
      ? '<strong>本地写入已连接</strong><p>窗口尺寸会自动保存；文字与动效点击确认后写入 <code>config/site-config.json</code>。</p>'
      : '<strong>本地写入未连接</strong><p>请运行 <code>npm run dev</code>，否则当前页面只能预览，不能保存。</p>';
    if (!localSaveEndpoint) {
      elements.saveStatus.textContent = '本地保存服务未连接';
      elements.saveStatus.classList.add('is-dirty');
    }
  }

  elements.previewFrame.addEventListener('load', () => syncPreview({ focus: true }));

  document.querySelectorAll('[data-device]').forEach((button) => {
    button.addEventListener('click', () => {
      const device = devices[button.dataset.device];
      document.querySelectorAll('[data-device]').forEach((item) => {
        item.classList.toggle('is-active', item === button);
      });
      resizePreview(device.width, device.height, true);
    });
  });

  for (const input of [elements.previewWidth, elements.previewHeight]) {
    input.addEventListener('input', () => {
      const width = Number(elements.previewWidth.value);
      const height = Number(elements.previewHeight.value);
      if (width < 320 || width > 1920 || height < 420 || height > 1200) return;
      resizePreview(width, height, true);
      document.querySelectorAll('[data-device]').forEach((item) => item.classList.remove('is-active'));
    });
    input.addEventListener('change', () => {
      resizePreview(
        Number(elements.previewWidth.value),
        Number(elements.previewHeight.value),
        true
      );
      document.querySelectorAll('[data-device]').forEach((item) => item.classList.remove('is-active'));
    });
  }

  elements.saveButton.addEventListener('click', saveConfirmed);
  elements.resetButton.addEventListener('click', () => {
    config = clone(publishedConfig);
    previewSize = clampPreviewSize(
      config.preview?.width || devices.desktop.width,
      config.preview?.height || devices.desktop.height
    );
    render();
    resizePreview(previewSize.width, previewSize.height);
    syncPreview({ focus: true });
    setDirty(false, '修改已撤销');
    showToast('已恢复到最近一次保存的配置');
  });
  elements.replayButton.addEventListener('click', () => {
    postToPreview('portfolio-preview-replay', { moduleId: activeModuleId });
  });

  new ResizeObserver(() => resizePreview()).observe(elements.previewStage);
  window.addEventListener('beforeunload', (event) => {
    if (!dirty) return;
    event.preventDefault();
    event.returnValue = '';
  });
}

start().catch((error) => {
  console.error(error);
  elements.saveStatus.textContent = '配置加载失败';
  elements.saveStatus.classList.add('is-dirty');
  showToast('请通过项目服务器打开后台');
});
