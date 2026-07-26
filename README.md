# Ether品牌方法论

基于 Figma 设计稿实现的深色长滚动品牌方法论网站。项目使用原生
HTML、CSS 和 JavaScript，不依赖前端框架，也不需要构建步骤。

页面动效以 Apple 风格的内容进入、媒体切换和稳定结束状态为基准，并参考
DJI 页面实现大屏滚动视觉。各屏结构、样式和交互相互隔离，方便后续单独修改。

## 项目结构

```text
brand-portfolio/
├── index.html                # 前台入口与各屏样式声明
├── section-loader.js         # 按顺序装载独立页面模块
├── admin.html                # 页面配置中心入口
├── admin/                    # 配置中心脚本与样式
├── config/
│   ├── site-config.json      # 文字、显隐、动效与预览尺寸
│   ├── schema.js             # 可配置字段定义
│   └── runtime.js            # 前台配置应用逻辑
├── styles/
│   └── base.css              # 重置、字体和全局变量
├── sections/
│   ├── 01-navigation/
│   ├── 02-hero/
│   ├── 03-ability/
│   ├── 04-cross-border-hero/
│   ├── 05-case-showcase/
│   ├── 06-organization-result/
│   └── 07-data-result/
│       ├── section.html      # 该屏独立结构
│       ├── style.css         # 该屏独立样式、响应式与动效
│       └── script.js         # 该屏独立交互入口
├── assets/
│   ├── images/
│   ├── svg/
│   └── video/                # 网页兼容的 H.264 MP4
├── netlify/
│   └── functions/            # 线上配置提交接口
├── dev-server.mjs            # 本地预览、配置写入与媒体分段服务
├── netlify.toml
├── package.json
└── README.md
```

每一屏只能查询和修改自己的根节点。后续调整某一屏时，进入对应的
`sections/<编号-名称>/` 目录即可，不需要修改其他屏的 HTML、CSS 或 JavaScript。

## 当前页面能力

- 01 导航：小窗口下仍以完整导航内容为中心。
- 02 首屏：全屏背景视频，静音单次播放。
- 03 能力：能力卡片、角色选择和 Apple 风格错峰进入。
- 04 案例大屏：滚动驱动的全屏放大与文字进入。
- 05 案例切换：五个独立面板和连续滑动的选中指示器。
  - APP 升级：两台手机展示重构前后长图，支持同步上下滚动。
  - 网站升级：不同高度的长图按滚动百分比同步，确保同时到达底部。
  - M 端升级：两段 H.264 视频静音单次播放，结束后可分别点击“重播”。
- 06 组织结果：渐变数据文字、数据卡片和行动按钮。
- 07 数据结果：三组前后数据、渐变结果文字和数据条动效。

交互和动效基准记录在：

```text
docs/apple-interaction-motion-guidelines.md
```

## 本地预览

在项目根目录启动项目自带的本地服务器：

```bash
npm run dev
```

然后浏览器打开：

```text
http://127.0.0.1:8001/
```

页面通过 `fetch` 装载独立 HTML 模块，因此必须使用本地服务器预览；
不要直接双击 `index.html`。

## 页面配置中心

启动本地服务器后打开：

```text
http://127.0.0.1:8001/admin.html
```

配置中心按 01—07 独立列出所有页面模块，支持：

- 修改每一屏文字，并在中间预览区实时查看。
- 单独调整每个文字字段的颜色和字号，也可恢复为设计稿样式。
- 独立显示或隐藏每一屏。
- 单独启用或关闭某一屏动效。
- 调整淡入、位移、错峰、面板切换、数据条生长等参数。
- 调整 04 大屏的桌面/移动端滚动高度、文字出现进度和平滑系数。
- 切换桌面与手机尺寸，或拖动预览框边缘自由调整窗口。
- 自动保存预览窗口尺寸。
- 点击“确认保存”写入实际配置文件，不使用浏览器本地草稿。

保存目标会根据运行环境自动切换：

- 本地通过 `npm run dev` 打开时，写入 `config/site-config.json`。
- GitHub/Netlify 线上打开时，通过 Netlify Function 提交到 GitHub，
  随后触发 Netlify 自动部署。

线上保存需要配置以下 Netlify 环境变量：

```text
ADMIN_SECRET       后台确认保存时输入的密钥
GITHUB_REPOSITORY  GitHub 仓库，格式为 owner/repository
GITHUB_TOKEN       仅授予该仓库 Contents 读写权限的令牌
GITHUB_BRANCH      保存分支，可省略，默认 main
```

GitHub Token 只存在于 Netlify 服务端环境变量中，不会发送到浏览器。

配置文件、字段定义和前台应用逻辑分别位于：

```text
config/site-config.json
config/schema.js
config/runtime.js
```

## 字体与媒体

页面优先通过 CDN 加载 MiSans，并使用以下回退顺序：

```text
MiSans → PingFang SC → Microsoft YaHei → system-ui
```

所有部署视频均使用 H.264 MP4，以兼容 Chrome、Edge、Firefox 和 Safari。
本地服务器支持 MP4 Range 分段读取；视频同时配置静态首帧，加载失败时不会显示空白。

## 部署到 Netlify

当前 GitHub 仓库：

```text
https://github.com/kannao-2378/ether
```

在 Netlify 中连接该 GitHub 仓库，并使用以下设置：

- Build command：留空
- Publish directory：`.`
- Production branch：`main`

之后每次 `git push` 到 `main`，Netlify 会自动重新部署。

## 浏览器支持

- Chrome、Edge、Firefox 和 Safari 的现代版本。
- 长图同步滚动支持鼠标滚轮、触控板、触摸和键盘。
- 视频使用 H.264、静音行内播放，并保留重播入口。
- 尊重 `prefers-reduced-motion`；启用系统“减少动态效果”时禁用非必要动画。

## 无障碍

- 使用语义化区域、标题、选项卡和状态属性。
- 内容图片包含替代文本，装饰性元素使用空替代文本或 `aria-hidden`。
- 提供清晰的 `:focus-visible` 状态。
- 选项卡支持方向键、Home 和 End 键操作。
- 长图区域和视频重播按钮均支持键盘访问。

## 占位内容说明

页面保留了 Figma 设计稿中的部分占位文字，例如 `xxxx`。这些文字可以直接通过
配置中心修改，或在对应独立模块的 `section.html` 中替换。
