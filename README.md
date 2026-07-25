# Brand Portfolio — 品牌体系作品集

A dark, Apple-style long-scroll brand portfolio page. Pure HTML/CSS/vanilla JS — no build step, no frameworks, no external network dependencies (except the local image assets in `assets/images/`).

## 项目结构

```
brand-portfolio/
├── index.html          # 页面结构（S0–S9 共 10 个区块）
├── style.css           # 设计令牌 + 全部样式 + 响应式 + 动效
├── script.js           # 8 项交互（滚动揭示、视差、Tab、复制等）
├── README.md
├── .gitignore
└── assets/
    └── images/
        ├── bg-section.png      # 全屏视差分隔背景
        ├── battery-wide.png    # 滚动同步对比产品图
        ├── brand-vector.svg    # Hero 主视觉字标（橙色渐变）
        ├── case-logo.svg       # 渲染案例视频控件 UI
        └── cta-button-bg.png   # CTA 按钮背景（作为 Hero CTA 增强层，CSS 纯色兜底）
```

## 本地预览

在项目根目录任选一种方式启动本地静态服务器：

```bash
# 方式一：Python（大多数系统自带）
python -m http.server 8000

# 方式二：Node（需全局安装）
npx serve
```

然后浏览器打开 `http://localhost:8000`。

> 直接双击 `index.html` 也能查看，但部分浏览器对 `file://` 协议下的图片/字体加载有限制，建议使用本地服务器。

## 可选：启用 MiSans 字体

页面默认使用 `MiSans → PingFang SC → Microsoft YaHei → system-ui` 字体栈，在没有 MiSans 时会自动回退到系统字体。

如需启用 MiSans：

1. 将字体文件放到 `assets/fonts/MiSans.woff2`。
2. 打开 `style.css`，找到顶部被注释的 `@font-face` 块，取消注释即可。

## 部署到 Netlify（通过 GitHub）

### 1. 初始化 Git 仓库并提交

```bash
cd brand-portfolio
git init
git add .
git commit -m "Initial commit: Brand Portfolio static site"
```

### 2. 在 GitHub 创建仓库并推送

1. 打开 [github.com/new](https://github.com/new)，创建一个新仓库（例如 `brand-portfolio`），**不要**勾选初始化 README。
2. 按页面提示推送本地仓库：

```bash
git remote add origin https://github.com/<你的用户名>/brand-portfolio.git
git branch -M main
git push -u origin main
```

### 3. 连接 Netlify 并部署

1. 打开 [app.netlify.com](https://app.netlify.com/)，用 GitHub 账号登录。
2. 点击 **Add new site → Import an existing project**。
3. 选择刚才推送的 GitHub 仓库 `brand-portfolio`。
4. 部署配置填写如下：
   - **Build command**：留空（无需构建）
   - **Publish directory**：`.`（根目录，或填 `brand-portfolio` 如果仓库根目录上一层就是项目）
   - **Production branch**：`main`
5. 点击 **Deploy site**，等待几秒即可获得一个 `https://<随机>.netlify.app` 的在线地址。

之后每次 `git push` 到 `main`，Netlify 会自动重新部署。

### 其他静态托管

同样适用于 Vercel、Cloudflare Pages、GitHub Pages 等：均为纯静态文件，无需构建命令，发布目录设为项目根目录即可。

## 浏览器支持

- 现代浏览器（Chrome / Edge / Firefox / Safari 最新版）。
- 视差与滚动同步在触屏/移动端会自动降级为静态展示，以保证性能。
- 尊重 `prefers-reduced-motion`：开启系统“减少动态效果”时，所有动画与位移将被禁用。

## 无障碍

- 语义化 HTML（`header` / `main` / `section` / `article` / `footer` / `nav`）。
- 所有图片含 `alt` 文本，装饰性元素标 `aria-hidden`。
- 可见焦点样式（`:focus-visible`）。
- 深色背景下文字对比度满足可读性要求。

## 占位内容说明

页面忠实还原了 Figma 设计稿，包括其中的占位文本（如 `xxxx`、`待补充内容`、`your@email.com` 等）均原样保留，方便后续按插槽替换为真实内容。需要替换的位置已在 HTML 中以注释或 `.slot` / `data-slot` 形式标注。
