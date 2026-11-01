# 备份策略更新

阿里云每天03:00运行检查；距最新备份满5天、数据库逻辑内容有变化才生成，校验成功后保留2份。Windows每周日16:00及到期登录时下载，至少7天间隔，避开服务器最新备份后的12小时；成功校验后保留2份。

在阿里云终端执行以下命令，不会修改学习数据库：

```bash
cd /var/www/brand-portfolio
git pull origin main
sudo cp eng-app/scripts/server_backup_policy.py /opt/pels/scripts/
printf '#!/bin/sh\nexec /opt/pels/.venv/bin/python /opt/pels/scripts/server_backup_policy.py\n' | sudo tee /usr/local/sbin/pels-backup >/dev/null
sudo chmod 700 /usr/local/sbin/pels-backup
sudo /usr/local/sbin/pels-backup
```

原 /etc/cron.d/pels-backup 的每天03:00入口保留，实际是否备份由策略决定。SKIP是正常结果。脚本通过flock防止并行、SQLite backup API获取一致快照、integrity_check和ZIP校验，失败不删除旧文件。
首次从旧策略切换，若已存在超过两份，只有下一次成功创建新备份才清理；不会因一次无变化检查贸然删除旧备份。
