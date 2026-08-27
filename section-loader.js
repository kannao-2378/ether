import {
  applySiteConfig,
  installConfigPreviewBridge,
  loadSiteConfig
} from './config/runtime.js?v=23';

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

// 模块 → 锚点 id 映射，导航栏点击 / 进度条依赖这些 id
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

const mountPoint = document.querySelector('#portfolio-sections');
const loadedSections = new Set();

async function fetchSectionHTML(name) {
  const response = await fetch(`sections/${name}/section.html?v=42`);

  if (!response.ok) {
    throw new Error(`${name} 加载失败：${response.status}`);
  }

  return response.text();
}

async function loadSection(name, siteConfig) {
  if (loadedSections.has(name)) return;
  loadedSections.add(name);

  const html = await fetchSectionHTML(name);

  // 用真实 section HTML 替换占位 div（outerHTML 同步替换，保留文档流位置）
  const placeholder = mountPoint.querySelector(
    `[data-section="${name}"].is-placeholder`
  );

  if (placeholder) {
    placeholder.outerHTML = html;
  } else {
    mountPoint.insertAdjacentHTML('beforeend', html);
  }

  // 重新应用配置（对已加载模块幂等，对新模块生效）
  if (siteConfig) {
    applySiteConfig(mountPoint, siteConfig);
  }

  // 导入并初始化该模块的脚本
  const sectionRoot = mountPoint.querySelector(
    `[data-section="${name}"]:not(.is-placeholder)`
  );

  if (sectionRoot) {
    try {
      const module = await import(`./sections/${name}/script.js?v=82`);

      if (typeof module.init === 'function') {
        module.init(sectionRoot);
      }
    } catch (error) {
      console.error(`模块 ${name} 脚本加载失败:`, error);
    }
  }
}

async function startPortfolio() {
  try {
    const siteConfig = await loadSiteConfig();

    // 1. 为所有模块创建占位 div，保留 id 供导航锚点使用
    for (const name of sectionManifest) {
      const div = document.createElement('div');
      div.className = 'is-placeholder';
      div.dataset.section = name;
      if (sectionIds[name]) {
        div.id = sectionIds[name];
      }
      div.style.minHeight = '80vh';
      mountPoint.appendChild(div);
    }

    // 2. 安装配置预览桥接（不依赖具体模块是否已加载）
    installConfigPreviewBridge(mountPoint);

    // 3. 首屏模块立即加载
    for (const name of immediateSections) {
      await loadSection(name, siteConfig);
    }

    // 4. 其余模块用 IntersectionObserver 按需加载
    const lazySections = sectionManifest.filter(
      (n) => !immediateSections.includes(n)
    );

    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              const name = entry.target.dataset.section;
              observer.unobserve(entry.target);
              loadSection(name, siteConfig);
            }
          }
        },
        { rootMargin: '0px 0px 300px 0px' }
      );

      for (const name of lazySections) {
        const placeholder = mountPoint.querySelector(
          `[data-section="${name}"].is-placeholder`
        );
        if (placeholder) {
          observer.observe(placeholder);
        }
      }
    } else {
      // 不支持 IntersectionObserver 的浏览器，直接加载全部
      for (const name of lazySections) {
        await loadSection(name, siteConfig);
      }
    }
  } catch (error) {
    console.error(error);
    mountPoint.innerHTML =
      '<p class="section-load-error">页面模块加载失败，请通过本地静态服务器打开项目。</p>';
  }
}

startPortfolio();
