# 以后新增项目或App怎样接入

## 当前网站组织

ether仓库根目录是原站源码：index.html、main.js、server.py、portfolio/、kan/等；eng-app/是新增英语应用源码。运行时英语前端部署到/var/www/pels-static/eng，而不是让Nginx直接公开整个eng-app。

kan/content.json 的 modules 是主页主要数据源，kan/main.js按配置生成卡片；kan/index.html提供无脚本/加载失败备用内容。增加板块要同时维护数据与静态备用入口，否则JS加载后可能把新增卡片覆盖掉。

英语板块id=eng，title=英语学习，href=/eng/，enabled=true，kind=number，位于作品集后。根域名的作品集跳转无需改变。

## 新增一个项目建议步骤

1. 给项目选唯一前缀，例如 /notes/ 或 /finance/，不得抢占已有/eng/、/kan/、/portfolio/、/api/。
2. 在仓库新增独立源码目录，例如notes-app；不要把业务文件混入kan。
3. 前端构建BASE_URL使用对应前缀，所有API通过统一base函数拼接，避免写死根/api。
4. 后端使用新的仅本地监听端口，8010留给英语，8080是原站；先用ss核查空闲端口。
5. 代码、运行用户、数据目录、环境配置、systemd服务、Cookie名称和路径独立；可以共享服务器，不等于共享数据库和登录。
6. Nginx只在现有HTTPS server加入该应用的location/include；先备份并nginx -t，成功才reload。
7. 修改kan/content.json增加入口，并同步kan/index.html备用卡片；沿用当前样式，不随意新增动效。
8. 分别测试原网站和新项目；提交只包含对应项目及入口修改。
9. 为新项目独立配置快照、下载、说明和恢复流程，不让新任务覆盖英语备份。

## 若做App

- 当前iPhone“添加到主屏幕”是网页App方式，不等于已有完整PWA离线能力。没有实现所有课程/API离线存储、Service Worker更新管理或离线进度合并。
- 包装iOS/Android可继续调用线上API，但需另解决认证Origin/Cookie、跨域、HTTPS、键盘和媒体策略；不能把浏览器Cookie行为原样假设在原生WebView一定可用。
- 原生iOS安装签名、Mac/Xcode、分发方式需按当时Apple政策核实，本目录不固定未来规则。
- Tauri桌面端、微信小程序都没有现成完成版。小程序不是直接塞React页面，需要另写对应前端及审核/域名配置。
- 若未来跨端离线学习，必须设计事件ID、设备ID、版本和冲突合并，不能同步覆盖整个SQLite文件冒充双向同步。
- 单人密码服务没有多用户隔离，不要未经改造就让多人共用登录学各自课程。
