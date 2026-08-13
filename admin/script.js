import { moduleSchema } from '../config/schema.js?v=4';

const elements = {
  moduleList: document.querySelector('#moduleList'),
  moduleIndex: document.querySelector('#moduleIndex'),
  moduleTitle: document.querySelector('#moduleTitle'),
  moduleDescription: document.querySelector('#moduleDescription'),
  contentFields: document.querySelector('#contentFields'),
  motionFields: document.querySelector('#motionFields'),
  layoutSection: document.querySelector('#layoutSection'),
  layoutFields: document.querySelector('#layoutFields'),
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

let syncPreviewRaf = 0;
function syncPreview({ focus = false } = {}) {
  if (focus) {
    cancelAnimationFrame(syncPreviewRaf);
    syncPreviewRaf = 0;
    postToPreview('portfolio-config-update', { config });
    setTimeout(() => {
      postToPreview('portfolio-preview-focus', { moduleId: activeModuleId });
    }, 60);
    return;
  }
  // 用 rAF 合并连续滑块输入，避免每帧多次重建
  if (syncPreviewRaf) return;
  syncPreviewRaf = requestAnimationFrame(() => {
    syncPreviewRaf = 0;
    postToPreview('portfolio-config-update', { config });
  });
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

function updateLayout(field, value) {
  const moduleConfig = config.modules[activeModuleId];
  moduleConfig.layout ||= {};
  moduleConfig.layout[field] = value;
  setDirty(true);
  syncPreview();
}

function updateCardField(index, key, value) {
  const moduleConfig = config.modules[activeModuleId];
  const cards = moduleConfig.layout?.cards;
  if (!Array.isArray(cards) || !cards[index]) return;
  cards[index][key] = value;
  setDirty(true);
  syncPreview();
}

// 为指定卡片上传素材（仅上传文件，更新 src）
async function uploadCardAsset(index) {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.gif,.png,.jpg,.jpeg,.webp,.mp4,.svg';
  input.addEventListener('change', async () => {
    const file = input.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const endpoint = localSaveEndpoint
        ? new URL('/api/motion-cases/upload', localSaveEndpoint).href
        : '/api/motion-cases/upload';
      const response = await fetch(endpoint, { method: 'POST', body: formData });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || '上传失败');
      updateCardField(index, 'src', result.path);
      showToast('素材已上传');
      renderInspector();
    } catch (error) {
      console.error(error);
      showToast(error.message || '上传失败，请确认本地服务已启动');
    }
  });
  input.click();
}

// 新增空卡片并立即在预览中显示
function addCard() {
  const moduleConfig = config.modules[activeModuleId];
  moduleConfig.layout ||= { cardHeight: 504, gap: 20, cards: [] };
  moduleConfig.layout.cards ||= [];
  moduleConfig.layout.cards.push({
    src: '', alt: '', caption: '', description: '',
    sizeMode: 'fixed', materialScale: 1
  });
  setDirty(true);
  renderInspector();
  syncPreview();
  showToast('已新增卡片，请上传素材');
}

async function deleteCardRemote(index) {
  // 本地环境走接口同步磁盘文件
  if (localSaveEndpoint) {
    try {
      const endpoint = new URL(`/api/motion-cases/card?index=${index}`, localSaveEndpoint).href;
      const response = await fetch(endpoint, { method: 'DELETE' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || '删除失败');
      const moduleConfig = config.modules[activeModuleId];
      if (moduleConfig.layout) {
        moduleConfig.layout.cards = result.cards || [];
      }
      publishedConfig = clone(config);
      setDirty(false, '卡片已删除');
      renderInspector();
      syncPreview();
      return;
    } catch (error) {
      console.error(error);
    }
  }
  // 回退：仅改内存
  const moduleConfig = config.modules[activeModuleId];
  const cards = moduleConfig.layout?.cards;
  if (!Array.isArray(cards) || index < 0 || index >= cards.length) return;
  cards.splice(index, 1);
  setDirty(true);
  renderInspector();
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

function createLayoutNumberField(field, value) {
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
  range.value = value ?? field.min;

  const number = document.createElement('input');
  number.type = 'number';
  number.min = field.min;
  number.max = field.max;
  number.step = field.step;
  number.value = value ?? field.min;

  function commit(rawValue) {
    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) return;
    const clamped = Math.min(field.max, Math.max(field.min, parsed));
    range.value = clamped;
    number.value = clamped;
    updateLayout(field.key, clamped);
  }

  range.addEventListener('input', () => commit(range.value));
  number.addEventListener('input', () => commit(number.value));
  control.append(range, number);
  wrapper.append(header, control);
  return wrapper;
}

function createLayoutEditor(schema, moduleConfig) {
  const wrapper = document.createElement('div');
  wrapper.className = 'layout-editor';

  const layout = schema.layout;
  const layoutConfig = moduleConfig.layout || {};

  // 全局数值字段（cardHeight / gap）
  for (const field of layout.fields) {
    wrapper.append(createLayoutNumberField(field, layoutConfig[field.key]));
  }

  // 卡片列表
  const cardsLabel = document.createElement('div');
  cardsLabel.className = 'layout-cards-label';
  cardsLabel.innerHTML = '<span class="field__label">卡片列表</span>';
  wrapper.append(cardsLabel);

  const cards = Array.isArray(layoutConfig.cards) ? layoutConfig.cards : [];
  cards.forEach((card, index) => {
    wrapper.append(createCardEditor(card, index));
  });

  // 新增卡片按钮
  const actions = document.createElement('div');
  actions.className = 'layout-actions';
  const addBtn = document.createElement('button');
  addBtn.type = 'button';
  addBtn.className = 'admin-button admin-button--quiet';
  addBtn.textContent = '新增卡片';
  addBtn.addEventListener('click', addCard);
  actions.append(addBtn);
  wrapper.append(actions);

  return wrapper;
}

// 卡片滑块字段辅助函数
function createCardSliderField({ label, min, max, step, unit, value, onChange }) {
  const wrapper = document.createElement('label');
  wrapper.className = 'field';
  const header = document.createElement('span');
  header.className = 'field__header';
  const labelText = document.createElement('span');
  labelText.className = 'field__label';
  labelText.textContent = label;
  const meta = document.createElement('span');
  meta.className = 'field__meta';
  meta.textContent = `${min}—${max}${unit}`;
  header.append(labelText, meta);

  const control = document.createElement('span');
  control.className = 'number-control';
  const range = document.createElement('input');
  range.type = 'range';
  range.min = String(min);
  range.max = String(max);
  range.step = String(step);
  range.value = String(value);
  const number = document.createElement('input');
  number.type = 'number';
  number.min = String(min);
  number.max = String(max);
  number.step = String(step);
  number.value = value;
  const apply = (val) => {
    const parsed = Math.min(max, Math.max(min, Number(val)));
    if (Number.isFinite(parsed)) onChange(parsed);
  };
  range.addEventListener('input', () => {
    number.value = range.value;
    apply(range.value);
  });
  number.addEventListener('input', () => {
    range.value = number.value;
    apply(number.value);
  });
  control.append(range, number);
  wrapper.append(header, control);
  return wrapper;
}

// 单张卡片的编辑器（含尺寸模式切换、素材上传、缩放调节）
function createCardEditor(card, index) {
  const cardEl = document.createElement('div');
  cardEl.className = 'layout-card';

  // 卡片头部：标题 + 尺寸模式切换 + 删除
  const cardHeader = document.createElement('div');
  cardHeader.className = 'layout-card__header';

  const title = document.createElement('span');
  title.textContent = `卡片 ${index + 1}`;
  cardHeader.append(title);

  const sizeModeSwitch = document.createElement('div');
  sizeModeSwitch.className = 'device-switch layout-card__mode';
  const sizeMode = card.sizeMode || 'fixed';
  for (const option of ['fixed', 'free']) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'device-switch__button';
    btn.classList.toggle('is-active', sizeMode === option);
    btn.textContent = option === 'fixed' ? '固定高度' : '自由尺寸';
    btn.addEventListener('click', () => {
      updateCardField(index, 'sizeMode', option);
      renderInspector();
    });
    sizeModeSwitch.append(btn);
  }
  cardHeader.append(sizeModeSwitch);

  const deleteBtn = document.createElement('button');
  deleteBtn.type = 'button';
  deleteBtn.className = 'layout-card__delete';
  deleteBtn.textContent = '删除';
  deleteBtn.addEventListener('click', () => deleteCardRemote(index));
  cardHeader.append(deleteBtn);

  cardEl.append(cardHeader);

  // 素材上传 + 预览
  const uploadRow = document.createElement('div');
  uploadRow.className = 'layout-card__upload';
  const uploadBtn = document.createElement('button');
  uploadBtn.type = 'button';
  uploadBtn.className = 'admin-button admin-button--quiet';
  uploadBtn.textContent = card.src ? '替换素材' : '上传素材';
  uploadBtn.addEventListener('click', () => uploadCardAsset(index));
  uploadRow.append(uploadBtn);
  cardEl.append(uploadRow);

  if (card.src) {
    const preview = document.createElement('div');
    preview.className = 'layout-card__preview';
    const isVideo = /\.mp4$/i.test(card.src);
    const media = document.createElement(isVideo ? 'video' : 'img');
    media.src = card.src;
    if (isVideo) {
      media.muted = true;
      media.loop = true;
      media.autoplay = true;
      media.playsInline = true;
    }
    media.alt = '';
    preview.append(media);
    cardEl.append(preview);
  }

  // 自由尺寸模式：显示卡片宽度 + 素材缩放 + 位置控件（高度始终跟随全局设置）
  if (sizeMode === 'free') {
    // 卡片宽度
    cardEl.append(createCardSliderField({
      label: '卡片宽度', min: 100, max: 1200, step: 1, unit: 'px',
      value: Number.isFinite(card.cardWidth) ? card.cardWidth : 400,
      onChange: (val) => updateCardField(index, 'cardWidth', val)
    }));

    // 素材缩放
    cardEl.append(createCardSliderField({
      label: '素材缩放', min: 0.5, max: 5, step: 0.05, unit: '',
      value: Number.isFinite(card.materialScale) ? card.materialScale : 1,
      onChange: (val) => updateCardField(index, 'materialScale', val)
    }));

    // 素材X偏移
    cardEl.append(createCardSliderField({
      label: '素材水平偏移', min: -400, max: 400, step: 1, unit: 'px',
      value: Number.isFinite(card.offsetX) ? card.offsetX : 0,
      onChange: (val) => updateCardField(index, 'offsetX', val)
    }));

    // 素材Y偏移
    cardEl.append(createCardSliderField({
      label: '素材垂直偏移', min: -400, max: 400, step: 1, unit: 'px',
      value: Number.isFinite(card.offsetY) ? card.offsetY : 0,
      onChange: (val) => updateCardField(index, 'offsetY', val)
    }));
  }

  // 文本字段（alt / caption / description）— src 由上传按钮管理
  const textFields = [
    { key: 'alt', label: '替代文字' },
    { key: 'caption', label: '卡片标题' },
    { key: 'description', label: '卡片说明' }
  ];
  for (const field of textFields) {
    const fieldWrapper = document.createElement('label');
    fieldWrapper.className = 'field';
    const fieldLabel = document.createElement('span');
    fieldLabel.className = 'field__label';
    fieldLabel.textContent = field.label;
    const input = document.createElement('input');
    input.type = 'text';
    input.value = card[field.key] || '';
    input.addEventListener('input', () => updateCardField(index, field.key, input.value));
    fieldWrapper.append(fieldLabel, input);
    cardEl.append(fieldWrapper);
  }

  return cardEl;
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

  // 动效参数（仅 schema.motion 非空的模块）
  const motionSection = document.querySelector('#motionSection');
  if (schema.motion && schema.motion.length > 0) {
    if (motionSection) motionSection.hidden = false;
    moduleConfig.motion ||= {};
    for (const field of schema.motion) {
      elements.motionFields.append(
        field.type === 'toggle'
          ? createToggleField(field, moduleConfig.motion[field.key])
          : createNumberField(field, moduleConfig.motion[field.key])
      );
    }
  } else if (motionSection) {
    motionSection.hidden = true;
  }

  // 布局编辑器（仅 schema.layout 存在的模块）
  if (schema.layout && elements.layoutSection && elements.layoutFields) {
    elements.layoutSection.hidden = false;
    elements.layoutFields.replaceChildren(createLayoutEditor(schema, moduleConfig));
  } else if (elements.layoutSection) {
    elements.layoutSection.hidden = true;
    elements.layoutFields.replaceChildren();
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
  const response = await fetch('./config/site-config.json?v=10');
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
