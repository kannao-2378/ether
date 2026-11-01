# kannao.top 独立英语学习应用部署

本次配置只负责 `/eng/` 和 `/eng/api/`，保留作品集的目录、Git 仓库、登录、原 `/api/` 和 HTTPS 配置。还没有登录服务器或执行上线。

这是单人私有学习应用：一个独立学习密码对应原有学习档案，不是多用户注册平台。

主要发布流程为 GitHub 仓库 `ether` 的 `eng-app/` 目录 → 服务器拉取，见 [GitHub 部署教程](GITHUB.md)。以下 ZIP 方式作为手动迁移备选。

## 1. 本地构建与打包

```powershell
$env:Path = 'C:\Program Files\nodejs;' + $env:Path
npm.cmd run build --prefix frontend -- --base=/eng/
.\.venv\Scripts\python.exe scripts/package_release.py
```

生成 `.tools/releases/english-app.zip`。它不包含学习数据、音频、密码、`.venv`、Node 依赖和测试日志。服务器不需要安装 Node 或重新构建，不需要课程生成用的 spaCy。

在准备迁移的当天另外生成私有数据包（不要提交 Git 或放进公开网站目录）：

```powershell
.\.venv\Scripts\python.exe scripts/export_learning_bundle.py --output .tools/releases/learning-private.zip --with-audio
```

这会用 SQLite 备份 API 制作一致快照，保留课程、答案、FSRS、复习、设置和已缓存的单词音频，不复制测试数据和登录会话。原文件不会被修改。

不要同时在旧电脑和网站持续答题：本次是迁移至网站共享数据，不含双向离线同步。正式切换前停止旧端答题，导出最终快照。

## 2. 服务器检查与目录

先通过你原来的 SSH 方式登录阿里云。不要发送服务器密码或私钥到聊天中。

```bash
free -h
df -h /var
python3 --version
sudo ss -lntp
sudo nginx -t
```

确认 8010 未被其他应用使用。截图里的 2 核/2 GB/40 GB 适合先做个人使用，但要以实际剩余资源为准。不要覆盖 `/var/www/brand-portfolio`。

以下为首次安装，若 `/opt/pels` 已有内容，先检查旧部署并备份，不直接覆盖。

```bash
sudo apt-get update
sudo apt-get install python3-venv unzip
sudo apt-get install espeak-ng
sudo useradd --system --user-group --home-dir /var/lib/pels --shell /usr/sbin/nologin pels
sudo install -d -m 755 /opt/pels /var/www/pels-static/eng
sudo install -d -m 750 -o pels -g pels /var/lib/pels
sudo install -d -m 700 /etc/pels
```

用你原来的上传方式把两个 ZIP 传到 `/tmp/`。也可以在本机用 `scp`，将 `YOUR_SSH_USER` 换成实际登录用户名：

```powershell
scp .tools/releases/english-app.zip YOUR_SSH_USER@120.55.186.234:/tmp/
scp .tools/releases/learning-private.zip YOUR_SSH_USER@120.55.186.234:/tmp/
```

```bash
sudo unzip /tmp/english-app.zip -d /opt/pels
sudo cp -a /opt/pels/frontend/dist/. /var/www/pels-static/eng/
sudo chmod -R a+rX /var/www/pels-static
sudo python3 -m venv /opt/pels/.venv
sudo /opt/pels/.venv/bin/python -m pip install -r /opt/pels/backend/requirements-production.txt
sudo unzip /tmp/learning-private.zip -d /var/lib/pels
sudo chown -R pels:pels /var/lib/pels
```

数据只在 `/var/lib/pels`；Nginx 只暴露 `/var/www/pels-static/eng`。没有私人数据包时，首次启动会建立新档案；不要在这种情况下误以为旧进度已迁移。

## 3. 建立独立学习密码

在服务器终端执行；输入不会回显。生成器只保存随机加盐的 PBKDF2 摘要，且拒绝覆盖已有配置。

```bash
sudo /opt/pels/.venv/bin/python /opt/pels/scripts/create_auth_env.py --output /etc/pels/english.env
```

真实配置在 Git、网页目录以外，权限为 600。启用登录但没有有效密码时，后端会拒绝启动，不会降级成公开访问。

当前以 `https://kannao.top` 为唯一登录来源。若需要从 www 域名访问，在现有 Nginx 的对应入口重定向到 kannao.top，而非共用原后台会话。

## 4. 启动英语后端

```bash
sudo cp /opt/pels/deploy/pels-english.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pels-english
sudo systemctl status pels-english --no-pager
curl -f http://127.0.0.1:8010/api/health
```

服务仅监听本机 8010，单 worker，不开放公网 8010，不使用 Vite 开发服务器。正式环境禁用测试模式，学习接口、导出和音频都要求登录。

## 5. 接入现有 HTTPS 网站

先备份现有 Nginx 配置。把 `deploy/nginx-english.conf` 的 location 段加入 **kannao.top 现有 HTTPS server 块内部**；它不是可直接替换整个网站的配置。

```bash
sudo nginx -t
sudo systemctl reload nginx
```

访问 `https://kannao.top/eng/`。检查：登录、今日学习、提交并保存、手机竖屏、重新打开后续学、退出登录后不能读取 `/eng/api/profile`。

如果出现问题，移除新增的 location 段并检查、重载 Nginx，停止 `pels-english` 即可撤回入口；保留 `/var/lib/pels` 数据，不重置作品集。

## 6. 更新与数据保护

后续更新仅替换 `/opt/pels` 下的代码和静态页面，重新安装锁定运行依赖、重启英语服务；不要再次覆盖 `/var/lib/pels/learning.db`。更新前先通过应用创建数据库备份并下载导出文件。

正式使用现有 ether 仓库的 eng-app/ 独立目录；源码与编译后的前端一起提交，服务器 git pull 后复制到独立运行目录。

日志：`sudo journalctl -u pels-english -n 100 --no-pager`。不要在排错时把 `/etc/pels/english.env` 或完整 Cookie 发出来。

电脑使用设备自己的美式语音；iPhone 使用下段的录音链路。牛津单词录音可从私有数据包迁移。音频自动播放受手机浏览器规则约束，可能需要先点一次播放。本次不包含完整离线学习或 App Store 打包。

iPhone 的搭配、句子通过 `/eng/api/pronunciation/device-us` 播放 WAV 媒体文件，避免依赖受静音开关影响的浏览器语音合成。Windows 本地服务使用已安装的 Zira 美式声音生成并缓存；Ubuntu 使用 `espeak-ng`（音色与 Windows 不同）。也可以迁移电脑已生成的 `audio/device-us` 录音，已有缓存不会重新合成。以上均不调用付费 AI 接口。后台仅允许课程已有内容，公开访问仍需独立登录。
