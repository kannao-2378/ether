export const moduleSchema = [
  {
    id: '01-navigation',
    label: '01 · 导航',
    description: '顶部导航文字与反馈时间',
    content: [
      { key: 'ability', label: '能力定位', selector: '.nav__item:nth-child(1)' },
      { key: 'crossBorder', label: '跨境案例', selector: '.nav__item:nth-child(2)' },
      { key: 'domestic', label: '其他案例', selector: '.nav__item:nth-child(3)' },
      { key: 'management', label: '管理工具', selector: '.nav__item:nth-child(4)' },
      { key: 'ai', label: 'AI 嵌入', selector: '.nav__item:nth-child(5)' },
      { key: 'render', label: '渲染案例', selector: '.nav__item:nth-child(6)' },
      { key: 'motion', label: '动态表现', selector: '.nav__item:nth-child(7)' },
      { key: 'contact', label: '联系合作', selector: '.nav__item:nth-child(8)' }
    ],
    motion: [
      { key: 'enabled', label: '启用动效', type: 'toggle' },
      { key: 'feedbackMs', label: '悬停反馈', min: 0, max: 1000, step: 10, unit: 'ms', cssVar: '--nav-feedback-ms' }
    ]
  },
  {
    id: '02-hero',
    label: '02 · 首屏',
    description: '首屏标题、按钮和进入节奏',
    content: [
      { key: 'eyebrow', label: '英文标题', selector: '.hero__eyebrow' },
      { key: 'cta', label: '按钮文字', selector: '.hero__cta' }
    ],
    motion: [
      { key: 'enabled', label: '启用动效', type: 'toggle' },
      { key: 'opacityMs', label: '淡入时长', min: 0, max: 2000, step: 50, unit: 'ms', cssVar: '--hero-opacity-ms' },
      { key: 'moveMs', label: '移动时长', min: 0, max: 2000, step: 50, unit: 'ms', cssVar: '--hero-move-ms' },
      { key: 'staggerMs', label: '错峰间隔', min: 0, max: 1000, step: 10, unit: 'ms', cssVar: '--hero-stagger-ms' },
      { key: 'distancePx', label: '进入距离', min: 0, max: 120, step: 1, unit: 'px', cssVar: '--hero-distance' },
      { key: 'videoFadeMs', label: '视频淡入', min: 0, max: 1500, step: 10, unit: 'ms', cssVar: '--hero-video-fade-ms' }
    ]
  },
  {
    id: '03-ability',
    label: '03 · 能力',
    description: '能力定位文字、选项和卡片进入',
    content: [
      { key: 'title', label: '主标题', selector: '.ability__title', type: 'textarea', mode: 'lines' },
      { key: 'subheadingPrimary', label: '角色标题', selector: '.ability__subheading span:first-child' },
      { key: 'subheadingSecondary', label: '模型说明', selector: '.ability__subheading span:last-child' },
      { key: 'rolePrompt', label: '对比说明', selector: '.ability__role > span:first-child', type: 'textarea', mode: 'lines' },
      { key: 'optionDirector', label: '选项 1', selector: '.ability__select option:nth-child(1)' },
      { key: 'optionDesigner', label: '选项 2', selector: '.ability__select option:nth-child(2)' },
      { key: 'optionBrand', label: '选项 3', selector: '.ability__select option:nth-child(3)' },
      { key: 'radarFlow', label: '雷达标签：流程', selector: '.ability-radar__label--flow' },
      { key: 'radarVisual', label: '雷达标签：视觉', selector: '.ability-radar__label--visual' },
      { key: 'radarContent', label: '雷达标签：内容', selector: '.ability-radar__label--content' },
      { key: 'radarBusiness', label: '雷达标签：商业', selector: '.ability-radar__label--business' },
      { key: 'radarBrand', label: '雷达标签：品牌', selector: '.ability-radar__label--brand' },
      { key: 'radarProduct', label: '雷达标签：产品', selector: '.ability-radar__label--product' },
      { key: 'conclusionTitle', label: '结论标题', selector: '.ability__conclusion h3' },
      { key: 'conclusionIntro', label: '结论引导语', selector: '.ability__conclusion-intro' },
      { key: 'conclusionKey1', label: '结论重点 1', selector: '.ability__conclusion-key:nth-of-type(2)' },
      { key: 'conclusionKey2', label: '结论重点 2', selector: '.ability__conclusion-key:nth-of-type(3)' },
      { key: 'conclusionKey3', label: '结论重点 3', selector: '.ability__conclusion-key:nth-of-type(4)' },
      { key: 'conclusionKey4', label: '结论重点 4', selector: '.ability__conclusion-key:nth-of-type(5)' },
      { key: 'conclusionEnding', label: '结论收束语', selector: '.ability__conclusion-ending' },
      { key: 'conclusionLink', label: '结论链接', selector: '.ability__conclusion a', preserveLastChild: true }
    ],
    motion: [
      { key: 'enabled', label: '启用动效', type: 'toggle' },
      { key: 'opacityMs', label: '淡入时长', min: 0, max: 2000, step: 50, unit: 'ms', cssVar: '--ability-opacity-ms' },
      { key: 'moveMs', label: '移动时长', min: 0, max: 2000, step: 50, unit: 'ms', cssVar: '--ability-move-ms' },
      { key: 'staggerMs', label: '卡片错峰', min: 0, max: 800, step: 10, unit: 'ms', cssVar: '--ability-stagger-ms' },
      { key: 'distancePx', label: '进入距离', min: 0, max: 120, step: 1, unit: 'px', cssVar: '--ability-distance' }
    ]
  },
  {
    id: '04-cross-border-hero',
    label: '04 · 案例大屏',
    description: '滚动放大、文字出现与章节长度',
    content: [
      { key: 'eyebrow', label: '眉题', selector: '.cross-border-case__eyebrow' },
      { key: 'title', label: '主标题', selector: '.cross-border-case__title' }
    ],
    motion: [
      { key: 'enabled', label: '启用滚动动效', type: 'toggle' },
      { key: 'scrollHeightVh', label: '桌面滚动高度', min: 120, max: 360, step: 5, unit: 'vh', cssVar: '--case-config-height' },
      { key: 'mobileScrollHeightVh', label: '移动端滚动高度', min: 120, max: 300, step: 5, unit: 'vh', cssVar: '--case-mobile-config-height' },
      { key: 'copyStart', label: '文字开始进度', min: 0, max: 0.8, step: 0.01, unit: '', cssVar: '--case-copy-start' },
      { key: 'copySpan', label: '文字进入区间', min: 0.05, max: 0.5, step: 0.01, unit: '', cssVar: '--case-copy-span' },
      { key: 'smoothing', label: '滚动平滑系数', min: 0.05, max: 0.5, step: 0.01, unit: '', cssVar: '--case-smoothing' }
    ]
  },
  {
    id: '05-case-showcase',
    label: '05 · 案例切换',
    description: '案例标题、标签与切换反馈',
    content: [
      { key: 'title', label: '主标题', selector: '.case-showcase__title', type: 'textarea', mode: 'lines' },
      { key: 'description', label: '说明文字', selector: '.case-showcase__description', type: 'textarea', mode: 'lines' },
      { key: 'materialTab', label: '物料标签', selector: '[data-case="material"]' },
      { key: 'appTab', label: 'APP 标签', selector: '[data-case="app"]' },
      { key: 'websiteTab', label: '网站标签', selector: '[data-case="website"]' },
      { key: 'mobileTab', label: 'M 端标签', selector: '[data-case="mobile"]' },
      { key: 'socialTab', label: '社媒标签', selector: '[data-case="social"]' },
      { key: 'hint', label: '操作提示', selector: '.case-showcase__hint' },
      { key: 'copy', label: '补充说明', selector: '.case-showcase__copy' }
    ],
    motion: [
      { key: 'enabled', label: '启用动效', type: 'toggle' },
      { key: 'opacityMs', label: '整屏淡入', min: 0, max: 2000, step: 50, unit: 'ms', cssVar: '--showcase-opacity-ms' },
      { key: 'moveMs', label: '整屏移动', min: 0, max: 2000, step: 50, unit: 'ms', cssVar: '--showcase-move-ms' },
      { key: 'staggerMs', label: '内容错峰', min: 0, max: 800, step: 10, unit: 'ms', cssVar: '--showcase-stagger-ms' },
      { key: 'distancePx', label: '进入距离', min: 0, max: 120, step: 1, unit: 'px', cssVar: '--showcase-distance' },
      { key: 'panelFadeMs', label: '面板淡入', min: 0, max: 1000, step: 10, unit: 'ms', cssVar: '--showcase-panel-ms' },
      { key: 'indicatorMs', label: '滑块移动', min: 0, max: 1000, step: 10, unit: 'ms', cssVar: '--showcase-indicator-ms' }
    ]
  },
  {
    id: '06-organization-result',
    label: '06 · 组织结果',
    description: '组织结果标题、数据和按钮',
    content: [
      { key: 'eyebrow', label: '眉题', selector: '.organization-result__eyebrow' },
      { key: 'title', label: '主标题', selector: '.organization-result__title', type: 'textarea', mode: 'lines' },
      { key: 'stat1Value', label: '数据 1 数值', selector: '.organization-stat:nth-child(1) .organization-stat__value' },
      { key: 'stat1Prefix', label: '数据 1 前缀', selector: '.organization-stat:nth-child(1) .organization-stat__prefix' },
      { key: 'stat1Label', label: '数据 1 说明', selector: '.organization-stat:nth-child(1) .organization-stat__label' },
      { key: 'stat2Value', label: '数据 2 数值', selector: '.organization-stat:nth-child(2) .organization-stat__value' },
      { key: 'stat2Prefix', label: '数据 2 前缀', selector: '.organization-stat:nth-child(2) .organization-stat__prefix' },
      { key: 'stat2Label', label: '数据 2 说明', selector: '.organization-stat:nth-child(2) .organization-stat__label' },
      { key: 'stat3Value', label: '数据 3 数值', selector: '.organization-stat:nth-child(3) .organization-stat__value' },
      { key: 'stat3Prefix', label: '数据 3 前缀', selector: '.organization-stat:nth-child(3) .organization-stat__prefix' },
      { key: 'stat3Label', label: '数据 3 说明', selector: '.organization-stat:nth-child(3) .organization-stat__label' },
      { key: 'cta', label: '按钮文字', selector: '.organization-result__cta > span:first-child' }
    ],
    motion: [
      { key: 'enabled', label: '启用动效', type: 'toggle' },
      { key: 'opacityMs', label: '淡入时长', min: 0, max: 2000, step: 50, unit: 'ms', cssVar: '--organization-opacity-ms' },
      { key: 'moveMs', label: '移动时长', min: 0, max: 2000, step: 50, unit: 'ms', cssVar: '--organization-move-ms' },
      { key: 'staggerMs', label: '数据错峰', min: 0, max: 800, step: 10, unit: 'ms', cssVar: '--organization-stagger-ms' },
      { key: 'distancePx', label: '进入距离', min: 0, max: 120, step: 1, unit: 'px', cssVar: '--organization-distance' }
    ]
  },
  {
    id: '07-data-result',
    label: '07 · 数据结果',
    description: '三组对比数据与数据条动效',
    content: [
      { key: 'eyebrow', label: '眉题', selector: '.data-result__eyebrow' },
      { key: 'title', label: '主标题', selector: '.data-result__title', type: 'textarea', mode: 'lines' },
      { key: 'beforeState', label: '重构前标签', selector: '.data-result__line--before .data-result__state', all: true },
      { key: 'afterState', label: '重构后标签', selector: '.data-result__line--after .data-result__state', all: true },
      { key: 'group1Title', label: '第一组标题', selector: '.data-result__group:nth-child(1) h3' },
      { key: 'group1Before', label: '第一组重构前', selector: '.data-result__group:nth-child(1) .data-result__line--before strong' },
      { key: 'group1After', label: '第一组重构后', selector: '.data-result__group:nth-child(1) .data-result__line--after strong' },
      { key: 'group2Title', label: '第二组标题', selector: '.data-result__group:nth-child(2) h3' },
      { key: 'group2Before', label: '第二组重构前', selector: '.data-result__group:nth-child(2) .data-result__line--before strong' },
      { key: 'group2After', label: '第二组重构后', selector: '.data-result__group:nth-child(2) .data-result__line--after strong' },
      { key: 'group3Title', label: '第三组标题', selector: '.data-result__group:nth-child(3) h3' },
      { key: 'group3Before', label: '第三组重构前', selector: '.data-result__group:nth-child(3) .data-result__line--before strong' },
      { key: 'group3After', label: '第三组重构后', selector: '.data-result__group:nth-child(3) .data-result__line--after strong' },
      { key: 'note', label: '数据说明', selector: '.data-result__note' }
    ],
    motion: [
      { key: 'enabled', label: '启用动效', type: 'toggle' },
      { key: 'opacityMs', label: '淡入时长', min: 0, max: 2000, step: 50, unit: 'ms', cssVar: '--data-opacity-ms' },
      { key: 'moveMs', label: '移动时长', min: 0, max: 2000, step: 50, unit: 'ms', cssVar: '--data-move-ms' },
      { key: 'staggerMs', label: '数据组错峰', min: 0, max: 800, step: 10, unit: 'ms', cssVar: '--data-stagger-ms' },
      { key: 'distancePx', label: '进入距离', min: 0, max: 120, step: 1, unit: 'px', cssVar: '--data-distance' },
      { key: 'barMs', label: '数据条生长', min: 0, max: 2000, step: 50, unit: 'ms', cssVar: '--data-bar-ms' }
    ]
  },
  {
    id: '08-brand-result',
    label: '08 · 品牌结果',
    description: '品牌结果文字与三屏滚动汇聚动效',
    content: [
      { key: 'eyebrow', label: '眉题', selector: '.brand-result__eyebrow' },
      { key: 'title', label: '主标题', selector: '.brand-result__title', type: 'textarea', mode: 'lines' },
      { key: 'path', label: '结果路径', selector: '.brand-result__path' },
      { key: 'description', label: '结果说明', selector: '.brand-result__description', type: 'textarea', mode: 'lines' }
    ],
    motion: [
      { key: 'enabled', label: '启用滚动动效', type: 'toggle' },
      { key: 'smoothing', label: '滚动平滑系数', min: 0.1, max: 0.8, step: 0.05, unit: '', cssVar: '--brand-smoothing' }
    ]
  },
  {
    id: '09-brand-method',
    label: '09 · 品牌方法论',
    description: 'ETHER 放大揭示、手机缩放与方法论内容',
    content: [
      { key: 'introLine1', label: '开场第一行', selector: '.brand-method__intro-line--first' },
      { key: 'introLine3', label: '开场第三行', selector: '.brand-method__intro-line--third' },
      { key: 'eyebrow', label: '眉题', selector: '.brand-method__eyebrow' },
      { key: 'title', label: '方法论标题', selector: '.brand-method__title' },
      { key: 'description', label: '方法论说明', selector: '.brand-method__description', type: 'textarea', mode: 'lines' },
      { key: 'principle1Title', label: '原则 1 标题', selector: '.brand-method__principle:nth-child(1) .brand-method__principle-title' },
      { key: 'principle1Copy', label: '原则 1 说明', selector: '.brand-method__principle:nth-child(1) .brand-method__principle-copy', type: 'textarea', mode: 'lines' },
      { key: 'principle2Title', label: '原则 2 标题', selector: '.brand-method__principle:nth-child(2) .brand-method__principle-title' },
      { key: 'principle2Copy', label: '原则 2 说明', selector: '.brand-method__principle:nth-child(2) .brand-method__principle-copy', type: 'textarea', mode: 'lines' },
      { key: 'principle3Title', label: '原则 3 标题', selector: '.brand-method__principle:nth-child(3) .brand-method__principle-title' },
      { key: 'principle3Copy', label: '原则 3 说明', selector: '.brand-method__principle:nth-child(3) .brand-method__principle-copy', type: 'textarea', mode: 'lines' },
      { key: 'cta', label: '按钮文字', selector: '.brand-method__cta > span:first-child' }
    ],
    motion: [
      { key: 'enabled', label: '启用滚动动效', type: 'toggle' },
      { key: 'smoothing', label: '滚动平滑系数', min: 0.1, max: 1, step: 0.05, unit: '', cssVar: '--method-smoothing' }
    ]
  },
  {
    id: '10-other-cases',
    label: '10 · 其他案例',
    description: '其他品牌案例标题与说明',
    content: [
      { key: 'title', label: '主标题', selector: '.other-cases h2', type: 'textarea', mode: 'lines' },
      { key: 'description', label: '说明文字', selector: '.other-cases__intro', type: 'textarea', mode: 'lines' },
      { key: 'hint', label: '操作提示', selector: '.other-cases__hint' }
    ],
    motion: []
  },
  {
    id: '11-management-tools',
    label: '11 · 管理工具',
    description: '配套管理工具内容',
    content: [
      { key: 'eyebrow', label: '眉题', selector: '.management-tools__eyebrow' },
      { key: 'title', label: '主标题', selector: '.management-tools h2', type: 'textarea', mode: 'lines' },
      { key: 'card1Title', label: '工具 1 标题', selector: '.management-card:nth-child(1) h3' },
      { key: 'card1Copy', label: '工具 1 说明', selector: '.management-card:nth-child(1) p', type: 'textarea' },
      { key: 'card2Title', label: '工具 2 标题', selector: '.management-card:nth-child(2) h3' },
      { key: 'card2Copy', label: '工具 2 说明', selector: '.management-card:nth-child(2) p', type: 'textarea' },
      { key: 'card3Title', label: '工具 3 标题', selector: '.management-card:nth-child(3) h3' },
      { key: 'card3Copy', label: '工具 3 说明', selector: '.management-card:nth-child(3) p', type: 'textarea' },
      { key: 'summary', label: '总结文字', selector: '.management-tools__summary p', type: 'textarea' }
    ],
    motion: []
  },
  {
    id: '12-ai-workflow',
    label: '12 · AI',
    description: 'AI 品牌工作流标题',
    content: [
      { key: 'eyebrow', label: '眉题', selector: '.ai-workflow__eyebrow' },
      { key: 'title', label: '主标题', selector: '.ai-workflow h2', type: 'textarea', mode: 'lines' }
    ],
    motion: []
  },
  {
    id: '13-render-cases',
    label: '13 · 渲染',
    description: '视觉渲染标题',
    content: [
      { key: 'eyebrow', label: '眉题', selector: '.render-cases__eyebrow' },
      { key: 'title', label: '主标题', selector: '.render-cases h2', type: 'textarea', mode: 'lines' }
    ],
    motion: []
  },
  {
    id: '14-motion-cases',
    label: '14 · 动态展示',
    description: '动态表达内容、卡片画廊与布局',
    content: [
      { key: 'title', label: '主标题', selector: '.motion-cases h2', type: 'textarea', mode: 'lines' },
      { key: 'description', label: '说明文字', selector: '.motion-cases__intro', type: 'textarea', mode: 'lines' },
      { key: 'hint1', label: '提示 1', selector: '.motion-cases__hint--one' },
      { key: 'hint2', label: '提示 2', selector: '.motion-cases__hint--two' },
      { key: 'cta', label: '按钮文字', selector: '.motion-cases__cta', preserveLastChild: true }
    ],
    motion: [],
    layout: {
      type: 'motion-gallery',
      fields: [
        { key: 'cardHeight', label: '卡片高度', min: 200, max: 800, step: 1, unit: 'px' },
        { key: 'gap', label: '卡片间距', min: 0, max: 60, step: 1, unit: 'px' }
      ],
      cardFields: [
        { key: 'src', label: '素材路径' },
        { key: 'alt', label: '替代文字' },
        { key: 'caption', label: '卡片标题' },
        { key: 'description', label: '卡片说明' },
        { key: 'sizeMode', label: '尺寸模式' },
        { key: 'materialScale', label: '素材缩放' },
        { key: 'cardWidth', label: '卡片宽度' },
        { key: 'cardHeight', label: '卡片高度' },
        { key: 'offsetX', label: '素材X偏移' },
        { key: 'offsetY', label: '素材Y偏移' }
      ]
    }
  },
  {
    id: '15-contact',
    label: '15 · 联系方式',
    description: '联系方式标题与号码',
    content: [
      { key: 'title', label: '主标题', selector: '.contact-section h2', type: 'textarea', mode: 'lines' },
      { key: 'email', label: '邮箱', selector: '.contact-card:nth-child(1) strong' },
      { key: 'wechat', label: '微信', selector: '.contact-card:nth-child(2) strong' },
      { key: 'phone', label: '电话', selector: '.contact-card:nth-child(3) strong' }
    ],
    motion: []
  }
];
