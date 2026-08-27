import {
  applySiteConfig,
  installConfigPreviewBridge,
  loadSiteConfig
} from './config/runtime.js?v=22';

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

const mountPoint = document.querySelector('#portfolio-sections');

async function loadSection(name) {
  const response = await fetch(`sections/${name}/section.html?v=41`);

  if (!response.ok) {
    throw new Error(`${name} 加载失败：${response.status}`);
  }

  return response.text();
}

async function startPortfolio() {
  try {
    const [sectionMarkup, siteConfig] = await Promise.all([
      Promise.all(sectionManifest.map(loadSection)),
      loadSiteConfig()
    ]);
    mountPoint.innerHTML = sectionMarkup.join('\n');
    applySiteConfig(mountPoint, siteConfig);
    installConfigPreviewBridge(mountPoint);

    for (const name of sectionManifest) {
      const module = await import(`./sections/${name}/script.js?v=81`);
      const sectionRoot = mountPoint.querySelector(`[data-section="${name}"]`);

      if (typeof module.init === 'function' && sectionRoot) {
        module.init(sectionRoot);
      }
    }
  } catch (error) {
    console.error(error);
    mountPoint.innerHTML = '<p class="section-load-error">页面模块加载失败，请通过本地静态服务器打开项目。</p>';
  }
}

startPortfolio();
