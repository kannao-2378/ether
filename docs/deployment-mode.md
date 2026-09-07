# 网站部署模式

更新时间：2026-09-06

## 当前线上结构

- 域名：`kannao.top`、`www.kannao.top`
- 服务器：阿里云轻量应用服务器（Ubuntu）
- Web 服务：Nginx
- Nginx 网站根目录：`/var/www/brand-portfolio`
- Git 分支：`main`
- GitHub 仓库：`https://github.com/kannao-2378/ether.git`
- 服务器 Git 远程地址：`https://ghfast.top/https://github.com/kannao-2378/ether.git`
- 2026-09-06 检查时线上提交：`8846816`
- 2026-09-06 检查时服务器工作区干净，`HEAD`、`origin/main` 一致。

## 发布流程

1. 在本地项目完成修改和验证。
2. 在本地提交并推送到 GitHub 的 `main` 分支。
3. 登录阿里云轻量应用服务器。
4. 更新服务器代码：

   ```bash
   cd /var/www/brand-portfolio
   git pull origin main
   ```

5. 静态 HTML、CSS、JavaScript 和媒体文件更新通常不需要重启 Nginx。
6. 如果修改了 Nginx 配置，先检查再重新加载：

   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

## 后台功能的部署方向

现阶段继续使用轻量应用服务器即可：

- Nginx 提供静态网页。
- 独立后台服务处理登录、内容保存、图片上传、新闻和股票数据。
- Nginx 将 `/api/` 请求反向代理到后台服务。
- 图片和视频后续可迁移到阿里云 OSS，并通过 CDN 分发。

后台计划采用按模块划分的路径：

- `/kan/admin/`
- `/news/admin/`
- `/stocks/admin/`
- `/portfolio/admin/`
- `/writing/admin/`
- `/apps/admin/`

这些后台可以共用同一套服务端登录会话，但每个后台提供各自所需的编辑功能。

## 安全规则

- 不在 GitHub、HTML、JavaScript或部署脚本中保存密码、AccessKey或Secret。
- 后台密码必须由服务器验证并以安全摘要保存。
- 上传接口和内容保存接口必须要求登录。
- 服务器原则上只执行 `git pull`，不直接修改并推送网站代码。
