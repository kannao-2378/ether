# GitHub与阿里云部署

## 2026-11-04 横线对齐静态修复

091a9d9已更新线上静态页，资源index-Csh3I7s9.js / index-BxnF4cJo.css。固定格子绘制横线，清除活动编辑器残留46px最小高度和自身边框，避免空格子基线及活动线高低跳动。移动尺寸检查输入前后各格矩形不变、同行底边一致，原焦点/逐词验证检查保持通过。未改中文题目、排课或后端。

静态页备份`/opt/pels/.before-underlines-20261104-201806`；首页及JS/CSS200、health正常，原作品集校验保持。只更新前端，未重启后端或写学习数据库。iOS真机效果未在模拟检查中冒充已验证。

## 2026-11-04 移动焦点与音节修复上线

4e74ec0（含7a14dc4、521d05a）已部署。前端实际资产index-Fdi7VSDd.js与index-DxxOj_uT.css，主线音节补齐版本2启用；旧复习卡只读元数据也可返回已有音节引用，未来新组合题创建时补引用。

最终备份`/var/lib/pels/before-keyboard-20261104-201222.zip`，回滚目录`/opt/pels/.before-keyboard-20261104-201222`。answers、feedback_events、progress、memory_states、questions、spelling_checks、review_queue、group_primary、composition_items九类原始行核对无改变或丢失，SQLite完整性ok，无伪造新掌握。当前课程选择保持，原有动态情境题保留。

首次上线核对脚本误把294固定题当成运行时动态题总数，已自动恢复代码与停服前快照；更正为保留更新前题目后重新部署成功，没有删除动态题来匹配计数。service active、health正常、HTTPS首页和新资源200、未登录profile401、原作品集校验一致。没有修改排课、FSRS或每日额度，未向线上提交模拟答案。

前端移动尺寸模拟验证保持同一输入节点、异步判词不意外失焦、错误色、缓冲、长按答案、键盘按钮、缩小/恢复视口及完整反馈。后端定向检查和生产构建通过；未声称iOS真机键盘动画已实测。实现与范围见30号说明。

## 2026-11-04 主线正式上线

用户授权上线后，运行代码770d6da已部署阿里云。启用`/etc/systemd/system/pels-english.service.d/mainline.conf`中的`PELS_MAINLINE_ENABLED=1`，默认新学路线已切换为`general-mainline`，实际登记148课题、294情境题，正式目录显示148项；不是只有测试入口。729目标仍不等于完整听说/开放能力认证。

一致性备份：`/var/lib/pels/before-mainline-20261104-191717.zip`（600权限）。原运行代码与静态页保留于`/opt/pels/.before-mainline-20261104-191717`。上线前另用最新云端快照在隔离临时目录试装。

停服备份后迁移核对：answers、feedback_events、progress、memory_states、questions、spelling_checks、review_queue、group_primary八类原始行均无丢失或改变；新知识项没有伪造掌握，SQLite完整性ok。service active、health正常，HTTPS首页及index-B6mUT8qJ.js/CSS均200，未登录profile401；原portfolio/index.html哈希保持。未向线上提交模拟答题。

仅增加课程启用drop-in，没有替换登录密码文件、Nginx或原网站后端。用户后续自行选择其他课程，重启不会再强行改回主线。真实iPhone键盘、发音与登录后的完整人工学习流程未在本轮冒充已验证。接入细节见29号说明。

## 当前已运行环境

| 项目 | 当前值 |
|---|---|
| 仓库/分支 | kannao-2378/ether，main |
| 仓库应用目录 | eng-app/ |
| 真主页 | https://kannao.top/kan/ |
| 英语入口 | https://kannao.top/eng/ |
| 服务器 | 阿里云 Ubuntu24.04，公网120.55.186.234 |
| 网站Git工作区 | /var/www/brand-portfolio |
| 运行代码 | /opt/pels/backend、scripts、deploy |
| 静态页面 | /var/www/pels-static/eng |
| 私人学习数据 | /var/lib/pels |
| 登录配置 | /etc/pels/english.env |
| 服务 | pels-english，运行用户pels |
| 后端监听 | 127.0.0.1:8010 |
| 原网站后端 | 127.0.0.1:8080，原/api/保持 |
| 主Nginx配置 | /etc/nginx/sites-enabled/brand-portfolio，实际目标在sites-available |
| 英语Nginx片段 | /etc/nginx/pels-eng.conf |

当前HTTPS server中已加入 `include /etc/nginx/pels-eng.conf;`。片段不是整个server配置，不要拿它覆盖原站。

Nginx把 /eng/api/ 代理到8010的 /api/，静态文件从独立root提供；/eng/assets/和/eng/用 ^~ 防止原站正则资源规则抢先。Cookie路径是/eng/。若修改前缀，构建BASE_URL、Nginx、Cookie和入口必须一同修改。

## 更新代码（在阿里云终端）

先确认最近备份成功；出现本地Git修改或合并冲突先停下检查，不用reset --hard抹掉。

```bash
cd /var/www/brand-portfolio
git status --short
git pull origin main
sudo cp -a eng-app/backend/. /opt/pels/backend/
sudo cp -a eng-app/scripts/. /opt/pels/scripts/
sudo cp -a eng-app/deploy/. /opt/pels/deploy/
sudo cp -a eng-app/frontend/dist/. /var/www/pels-static/eng/
sudo /opt/pels/.venv/bin/python -m pip install -r /opt/pels/backend/requirements-production.txt
sudo systemctl restart pels-english
sudo systemctl status pels-english --no-pager
curl -f http://127.0.0.1:8010/api/health
```

只改前端时仅需git pull和复制dist，不用重启后端。修改部署模板不会自动更新/etc里的已安装文件，需核对后明确复制、nginx -t或daemon-reload。常规更新不修改配置与数据。

## 验证

首页/kan/有英语入口，/eng/可登录；未登录的/eng/api/profile返回401；已登录答题保存、刷新继续、发音、设置、退出均正常。健康检查ok不等于所有业务流程都没问题。

## 首次部署与回滚

完整首次安装见 deploy/GITHUB.md。需要python3-venv、espeak-ng、pels系统用户、独立目录、密码配置、systemd和Nginx片段。线上不用Vite，不需要安装Node，不开放8010公网端口。

当前用户已完成首次部署，不能每次更新都重新建用户、生成密码或导入旧库。

仅代码有问题时，先备份，提取已知良好Git提交到临时目录再替换运行代码，重启服务验证；数据库结构变更后旧代码不一定兼容，不能只盲目回滚代码。恢复数据库见备份说明。原站曾备份到 /etc/nginx/sites-available/brand-portfolio.backup-20261101-145014；后续备份以实际文件为准。

本次没有配置GitHub Actions自动部署或Webhook。推送只是更新GitHub，阿里云仍由用户执行拉取与安装。

学习组版本必须复制整个backend目录，包括group_learning.py，不能沿用只复制app.py的简版命令。升级前用export_learning_bundle.py制作一致数据库快照；第一次启动建立组关系但保留旧答题和卡。


2026-11-01学习组发布提交：fe8a67b，已推送，未代用户部署阿里云。本地服务8000已重启、health通过；迁移前一致快照在.tools/pre-group-migration/20261101-194101，旧answers/feedback_events/progress全行对比未减少或改变。104项后端回归、60天随机模拟及393px页面端到端通过。线上更新：

```bash
cd /var/www/brand-portfolio && git pull origin main
sudo /opt/pels/.venv/bin/python /opt/pels/scripts/export_learning_bundle.py --data /var/lib/pels --output /var/lib/pels/before-groups-$(date +%Y%m%d-%H%M%S).zip
sudo cp -a eng-app/backend/. /opt/pels/backend/
sudo cp -a eng-app/frontend/dist/. /var/www/pels-static/eng/
sudo systemctl restart pels-english
sudo systemctl status pels-english --no-pager
curl -f http://127.0.0.1:8010/api/health
```

每步成功再执行下一步。上述迁移快照在数据目录，不属于滚动备份的两次保留策略；确认稳定后可人工归档。不要将数据目录纳入Git。

2026-11-01 19:46：用户授权后已通过admin SSH实际部署fe8a67b至阿里云。更新前快照：/var/lib/pels/before-groups-20261101-194626.zip（600权限）。服务active、health正常；HTTPS /eng/与新JS均200、未登录profile为401。原answers/feedback_events/progress与快照全行比较无丢失或变更，SQLite完整性通过。保留原portfolio/index.html未提交修改，未改Nginx或密码。未登录真实账号答题，避免制造学习记录。

2026-11-01：501cb21已部署本地及阿里云，新增只读当天学习和计划接口、日期查询及两页清单。107项隔离测试、393px排版通过。未修改调度规则、真实学习记录、密码或Nginx；保留原站未提交修改。

2026-11-01：0a34fa4已更新本地及阿里云；学习档案去掉当天内容清单，显示实际练习组数及去重内容分类计数。针对性测试、构建及服务健康检查通过，未改学习记录与调度算法。

2026-11-01 20:39：09b6437词典专项训练已在117项回归、隔离浏览器首次与重复6项专项全流程通过后部署本地及阿里云。云端快照/var/lib/pels/before-focus-20261101-203910.zip（600权限）；本地快照.tools/pre-focus-migration/20261101-203757。服务健康、新JS200、未登录专项接口401；原answers/feedback_events/progress对比均无丢失或改变，SQLite完整性通过。线上仅查询内容校验，未产生测试答题；保留原portfolio/index.html修改。

2026-11-01 21:07：78dc123查词预览与选择导入已更新本地及阿里云。123项测试、真实API查询与隔离浏览器选3项完整训练通过后部署。云端快照/var/lib/pels/before-lookup-20261101-210656.zip，本地.tools/pre-lookup-migration/20261101-210410。服务正常，服务用户离线参考查询11项无警告，新JS200、未登录查询401；原answers/feedback_events/progress与更新前比较均保留。新增公开资料缓存不是学习库，不备份进学习包。

2026-11-02：455c38d修复普通队列current[:12]误截断与回看组信息恢复，125项回归及线上快照隔离36次模糊回放、393px返回/刷新验证后更新本地和阿里云。云端备份/var/lib/pels/before-queue-fix-20261102-080413.zip，本地.tools/pre-queue-fix/20261102-080424；学习数据不重置，未向线上写模拟答案。原every day/learn English记录保留，组名与当前项显示分开。

2026-11-02 11:55：431b2d7 课程路线与复习分离已推送并部署本地及阿里云。133 项回归、60 天随机模拟及隔离393px连续答题通过。云端快照 /var/lib/pels/before-course-policy-20261102-115502.zip；本地 .tools/pre-course-policy/20261102-115439。上线后 answers、feedback_events、progress、memory_states 对比更新前均无丢失或改变，SQLite完整性通过；health正常，新JS200，未登录profile401。原portfolio/index.html校验一致。课程策略细节见17号说明；未向真实库提交模拟答题。

2026-11-02 21:48：689d5a9 句子词长横线与自动检查已推送并部署本地、阿里云。136项后端回归、10个前端用例、393px隔离浏览器和生产构建通过。云端快照 /var/lib/pels/before-sentence-input-20261102-214828.zip；本地 .tools/pre-sentence-input/20261102-214800。更新后 answers、feedback_events、progress、memory_states 与快照全行比较均无变化或丢失，SQLite完整性通过；health正常，新JS200，未登录profile401，作品集文件校验一致。真实设备声音及iOS键盘动画未在自动化环境中验证，音源没有改动。

2026-11-02 23:27：bcca6b7 统一课程编排已部署本地与阿里云。154项隔离测试、50组180次正向答题、60天1378次随机答题/151次迁移及393px浏览器通过。部署前用阿里云最新备份在临时隔离目录实际导入新代码并校验，才替换运行目录。云端快照 /var/lib/pels/before-unified-curriculum-20261102-232715.zip；本地 .tools/pre-unified-curriculum/20261102-232535。上线后 answers、feedback_events、progress、memory_states 与备份全行比较均无丢失或改变；SQLite完整性通过。服务健康、新JS200、未登录profile401，原作品集校验不变。已编排50目标；其他资料不再自动冒充新课，仍留词典/历史/专项。详见19号说明。

2026-11-02：a6d456e 拼写布局修复已更新本地及线上前端。430px深色/1280px浅色浏览器验证单词与句子横线、词性中文跨阶段一致、错误颜色、输入框坐标不变和横线间距，TypeScript/生产构建通过。线上JS/CSS200、health正常，原作品集校验一致。仅复制静态文件，未重启后端或写学习数据库，未修改课程和复习算法。

2026-11-03：3a96196 已推送 Git；中文区居中、旧短语材料先修及触摸看答案焦点修复。157 项隔离回归、50组180次答题、430px触摸焦点与草稿检查、生产构建通过。本地数据库已一致性备份并重启本地8000。阿里云部署被自动审批拒绝（缺少本轮明确上线授权），未执行生产覆盖或重启，等待用户确认。

2026-11-03 10:30：用户明确授权上线后，3a96196 已部署阿里云。更新前备份 /var/lib/pels/before-picture-peek-20261103-103026.zip（600权限）。后端启动约12秒后health正常、service active，新JS/CSS200、未登录profile401。answers、feedback_events、progress、memory_states 与备份全行比较均无改变或丢失，SQLite完整性ok，原portfolio/index.html校验一致。部署脚本末尾PowerShell额外CR空行报错发生在verified之后，未影响部署；另行检查服务正常。未向真实库提交测试答题，iPhone真机键盘动画待用户确认。

2026-11-03：e7fe18a 已推送Git（自动补空格＋真正迁移与示范回忆分离）。168项隔离后端回归、22前端用例、50组180次回放、430px真实API浏览器及构建通过。本地已备份并重启8000；health正常，answers/feedback_events/progress/memory_states 与备份全行比较无改变或丢失，SQLite完整性ok。新表teaching_exposures/question_trials随DB及JSON导出，旧派生迁移统计重算，原始历史及FSRS保留。用户本轮要求推送，未部署阿里云。上线必须整个backend与最新dist一起复制，先备份；此版本不是只替换前端。

2026-11-03：ccf91ea 模糊后连刷修复已推送Git并应用本地。仅7项针对性检查、暂停/恢复浏览器及构建，未跑全套。只调整当天新题选择及单项暂停提示，保留真实拼错修复与未答恢复，不改FSRS/上限/掌握判定。本地更新前已一致性备份，重启health正常；answers/feedback_events/progress/memory_states 与备份逐行比较无丢失或变化。未部署阿里云。

2026-11-03 21:02：用户明确要求更新阿里云后，ccf91ea（含e7fe18a）已部署。云端更新前备份 /var/lib/pels/before-transfer-order-20261103-210243.zip，权限600。整个backend及dist更新，service active、health正常，新JS/CSS200、未登录profile401；原portfolio/index.html校验一致。answers/feedback_events/progress/memory_states与备份全行比较无改变或丢失，SQLite完整性ok，两张新证据表已创建；仅派生迁移统计按新标准重算。部署脚本全部verified后最后exit 0受到PowerShell管道CR换行影响报错，已另行核对服务，不影响前面已完成的部署与验证。未执行全套测试，未向线上提交模拟答题。

2026-11-03：4f2d797 逐词拼写验证已推送Git并更新本地8000。5项隔离后端检查、430px逐词真实API输入/颜色/焦点/快速输入/最终保存浏览器检查和生产构建通过；未跑全套。本地更新前一致备份，health正常，answers/feedback_events/progress/memory_states与备份逐行比较无变化。新前端需要/check-word后端接口，部署时必须同时更新整个backend和dist。尚未部署阿里云。

2026-11-03：5585a97 记忆/迁移分轴及迁移题标题已推送Git并应用本地。9项assessment和7项档案相关检查、2个词典独立状态渲染用例及生产构建通过，未跑全套。本地已一致性备份并重启，health正常；answers/feedback_events/progress/memory_states 与备份逐行比较无变动。证据缓存版本3只重算派生统计，原FSRS不改。尚未部署阿里云；当前线上ccf91ea，线上33个新trial均为recall，课程仅8组15变式，覆盖不足未在本次补齐。

2026-11-03：beb39c0 50组迁移课程补充已推送Git并更新本地。合计165条变式/150个不同英文句子；新资源transfer_practice.psv需与整个backend一并部署。7项针对性检查通过（未跑全套）；线上一致性快照的隔离试装确认17组已有可用真正迁移，完成当前未答题后下一题为transfer。快照仅用于隔离验证，未覆盖真实库，临时数据库已清理、保留汇总。原answers/feedback_events/progress/memory_states不变。本地已备份、health正常，逐行比较原始记录无变化。尚未部署阿里云。


2026-11-03 22:41：用户授权“检查组合，确认无问题后更新阿里云”。完成分步解锁、全50规则候选依赖检查、固定种子每目标抽样审查、实际小批落库及6项针对性检查，收紧生硬组合后6db12f9已部署。包含此前未部署的逐词输入、记忆/迁移分轴、165条静态变式和动态组合引擎。云端停服务后先备份 /var/lib/pels/before-composition-20261103-224143.zip（600）；旧运行代码和静态目录保留在 /opt/pels/.before-composition-20261103-224143（700）。离线初始化后、恢复服务前，answers/feedback_events/progress/memory_states相对快照逐行比较均0变更/丢失，SQLite完整性ok，新表存在。service active、health正常，HTTPS首页及新JS/CSS200、未登录profile401，原portfolio/index.html哈希不变。未向真实库提交模拟答题；未重跑全套或两个月模拟。

2026-11-05：8006b40已静态上线。中文提示并排显示、触摸答案和播放保留输入焦点。首页和新JS/CSS可访问、health正常、原作品集校验一致。回滚目录 /opt/pels/.before-meaning-touch-20261105-074037；未重启后端、未写学习数据库。移动尺寸隔离检查通过，iOS真机待用户复测。
