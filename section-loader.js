import {
  applySiteConfig,
  installConfigPreviewBridge,
  loadSiteConfig
} from './config/runtime.js?v=24';

const sectionManifest = [
  '01-navigation',
  '02-hero',
  '03-ability',
  '04-cross-border-hero',
  '05-case-showcase',
  '06-organization-result-01',
  '07-data-result',
  '08-brand-result',
  '09-brand-method',
  '10-other-cases',
  '11-management-tools',
  '12-ai-workflow',
  '13-render-cases',
  '14-motion-cases',
  '15-contact'
];

// 模块 → 锚点 id 映射：占位符先顶上这些 id，导航栏锚点/进度条在任何时刻都有效
const sectionIds = {
  '03-ability': 'role',
  '04-cross-border-hero': 'cross-border-case',
  '05-case-showcase': 'case-showcase',
  '06-organization-result-01': 'organization-result',
  '07-data-result': 'data-result',
  '08-brand-result': 'brand-result',
  '09-brand-method': 'brand-method',
  '10-other-cases': 'domestic-cases',
  '11-management-tools': 'management-tools',
  '12-ai-workflow': 'ai-workflow',
  '13-render-cases': 'render-cases',
  '14-motion-cases': 'motion-cases',
  '15-contact': 'contact'
};

// 首屏立即可见的模块——不经过 IntersectionObserver，直接加载
const immediateSections = ['01-navigation', '02-hero'];

// 按需加载的预取边距（遵循项目动效规范：媒体至少提前 100vh 开始加载）
const OBSERVER_OPTIONS = {
  rootMargin: '600px 0px 1200px 0px'
};

const mountPoint = document.querySelector('#portfolio-sections');
const loadedSections = new Set();

// 站点配置单独加载：失败只降级为"不替换文案"，绝不阻塞模块渲染
const siteConfigPromise = loadSiteConfig().catch((error) => {
  console.error('站点配置加载失败（模块仍会正常展示）：', error);
  return null;
});

function createPlaceholder(name) {
  const div = document.createElement('div');
  div.className = 'is-placeholder';
  div.dataset.section = name;
  if (sectionIds[name]) {
    div.id = sectionIds[name];
  }
  // 占位高度接近多数模块的真实高度，减少替换时的滚动跳动
  div.style.minHeight = '80vh';
  return div;
}

async function fetchSectionHTML(name, attempts = 3) {
  let lastError;

  for (let attempt = 0; attempt < attempts; attempt++) {
    try {
      const response = await fetch(`sections/${name}/section.html?v=43`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.text();
    } catch (error) {
      lastError = error;
      if (attempt < attempts - 1) {
        await new Promise((resolve) => setTimeout(resolve, 500 * (attempt + 1)));
      }
    }
  }

  throw lastError;
}

// 单个模块彻底加载失败时，在占位符里放一个重试入口，页面其余部分不受影响
function markSectionError(name) {
  const placeholder = mountPoint.querySelector(
    `[data-section="${name}"].is-placeholder`
  );

  if (!placeholder) return;

  placeholder.classList.add('is-load-error');
  placeholder.replaceChildren();

  const retry = document.createElement('button');
  retry.type = 'button';
  retry.className = 'section-retry';
  retry.textContent = '模块加载失败，点击重试';
  retry.addEventListener('click', () => {
    placeholder.classList.remove('is-load-error');
    placeholder.replaceChildren();
    loadSection(name);
  });

  placeholder.appendChild(retry);
}

async function loadSection(name) {
  if (loadedSections.has(name)) return;
  loadedSections.add(name);

  let html;

  try {
    html = await fetchSectionHTML(name);
  } catch (error) {
    console.error(`模块 ${name} HTML 加载失败：`, error);
    loadedSections.delete(name);
    markSectionError(name);
    return;
  }

  // 用真实 section 替换占位 div（outerHTML 同步替换，保留文档流位置与锚点 id）
  const placeholder = mountPoint.querySelector(
    `[data-section="${name}"].is-placeholder`
  );

  if (placeholder) {
    placeholder.outerHTML = html;
  } else {
    mountPoint.insertAdjacentHTML('beforeend', html);
  }

  // 配置就绪后应用（对已加载模块幂等，可安全重复调用）
  const siteConfig = await siteConfigPromise;
  if (siteConfig) {
    applySiteConfig(mountPoint, siteConfig);
  }

  const sectionRoot = mountPoint.querySelector(
    `[data-section="${name}"]:not(.is-placeholder)`
  );

  if (!sectionRoot) return;

  // 脚本失败只损失该模块的动效，内容仍可展示
  try {
    const module = await import(`./sections/${name}/script.js?v=83`);

    if (typeof module.init === 'function') {
      module.init(sectionRoot);
    }
  } catch (error) {
    console.error(`模块 ${name} 脚本初始化失败：`, error);
  }
}

function startPortfolio() {
  // 1. 同步创建全部占位符：页面立即拥有完整高度和导航锚点
  const fragment = document.createDocumentFragment();

  for (const name of sectionManifest) {
    fragment.appendChild(createPlaceholder(name));
  }

  mountPoint.replaceChildren(fragment);

  // 2. 预览桥接（admin 面板用，不依赖模块是否已加载）
  installConfigPreviewBridge(mountPoint);

  // 3. 首屏模块立即加载（不 await，多个模块并行）
  for (const name of immediateSections) {
    loadSection(name);
  }

  // 4. 其余模块接近视口时按需加载
  const lazySections = sectionManifest.filter(
    (name) => !immediateSections.includes(name)
  );

  if (!('IntersectionObserver' in window)) {
    for (const name of lazySections) {
      loadSection(name);
    }
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      observer.unobserve(entry.target);
      loadSection(entry.target.dataset.section);
    }
  }, OBSERVER_OPTIONS);

  for (const name of lazySections) {
    const placeholder = mountPoint.querySelector(
      `[data-section="${name}"].is-placeholder`
    );
    if (placeholder) {
      observer.observe(placeholder);
    }
  }
}

startPortfolio();
