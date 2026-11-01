# 从 GitHub 拉取并部署

仓库：https://github.com/kannao-2378/ether ，分支 `main`，应用目录 `eng-app/`。
访问入口：https://kannao.top/eng/ 。本教程由你在阿里云执行，本地准备不修改服务器。

## 1. 拉取代码

```bash
cd /var/www/brand-portfolio
git pull origin main
```

`eng-app/frontend/dist` 已包含本地编译好的静态文件，服务器不需要 Node。

## 2. 安装独立运行目录

首次安装先检查 `/opt/pels`、8010 端口及磁盘，已有部署先备份。

```bash
sudo apt-get update
sudo apt-get install python3-venv espeak-ng
sudo useradd --system --user-group --home-dir /var/lib/pels --shell /usr/sbin/nologin pels
sudo install -d -m 755 /opt/pels /var/www/pels-static/eng
sudo install -d -m 750 -o pels -g pels /var/lib/pels
sudo install -d -m 700 /etc/pels
sudo cp -a /var/www/brand-portfolio/eng-app/backend /opt/pels/
sudo cp -a /var/www/brand-portfolio/eng-app/scripts /opt/pels/
sudo cp -a /var/www/brand-portfolio/eng-app/deploy /opt/pels/
sudo cp -a /var/www/brand-portfolio/eng-app/frontend/dist/. /var/www/pels-static/eng/
sudo python3 -m venv /opt/pels/.venv
sudo /opt/pels/.venv/bin/python -m pip install -r /opt/pels/backend/requirements-production.txt
sudo /opt/pels/.venv/bin/python /opt/pels/scripts/create_auth_env.py --output /etc/pels/english.env
```

最后一步交互设置独立学习密码，不要把密码发到聊天或提交 Git。
如要保留本机进度，在本地导出私有数据包并单独传到服务器，参考 [完整部署说明](README.md)，不要上传 GitHub。没有迁移数据会建立新学习档案。

## 3. 启动服务与配置网站

```bash
sudo cp /opt/pels/deploy/pels-english.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pels-english
curl -f http://127.0.0.1:8010/api/health
```

将 `eng-app/deploy/nginx-english.conf` 的 location 段添加到原站 HTTPS server 块内。保留原站其他配置，不替换整个配置文件。

```bash
sudo nginx -t
sudo systemctl reload nginx
```

检查 `/eng/` 登录、答题保存、复习、音频和退出登录；未登录访问 `/eng/api/profile` 应被拒绝。

## 4. 后续更新

先在应用里备份学习数据库，再执行：

```bash
cd /var/www/brand-portfolio
git pull origin main
sudo cp -a eng-app/backend/. /opt/pels/backend/
sudo cp -a eng-app/scripts/. /opt/pels/scripts/
sudo cp -a eng-app/deploy/. /opt/pels/deploy/
sudo cp -a eng-app/frontend/dist/. /var/www/pels-static/eng/
sudo /opt/pels/.venv/bin/python -m pip install -r /opt/pels/backend/requirements-production.txt
sudo systemctl restart pels-english
```

不要覆盖 `/var/lib/pels` 或 `/etc/pels/english.env`。只有修改 Nginx 配置时才需检查并重新加载 Nginx。
