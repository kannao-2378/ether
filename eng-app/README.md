# 循序 · 个人英语学习系统

React / TypeScript 前端，FastAPI / SQLite 后端。支持单词、搭配、短语、句子和中文情境训练、词典、学习计划、学习档案及单人密码保护。

## 本地运行

需要 Python 3.11+ 和 Node.js 20.19+。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm.cmd ci --prefix frontend
.\start.ps1
```

浏览器访问 http://127.0.0.1:5173/ 。本地默认关闭登录保护。

## GitHub 与服务器部署

本项目放在 `kannao-2378/ether` 仓库的 `eng-app/` 目录中，不替换原网站。正式入口为 **https://kannao.top/eng/**。

前端在本地构建后随源代码一同提交，服务器拉取后不需要安装 Node。服务器操作见 [GitHub 部署教程](deploy/GITHUB.md)。密码、学习数据和音频缓存不提交。

## 学习与复习

每项内容独立记录学习证据与 FSRS 状态。当天按题数穿插巩固（2 / 4 / 8），跨天由 FSRS-6 默认模型结合教学规则安排。每日新学和复习量分别设限，待巩固并发上限 12 项。熟悉程度与阶段解锁不等同于长期记住。

个人曲线目前是默认模型结合个人知识项状态的预测，并未自动训练个人模型参数。详见 [算法说明](docs/fsrs-scheduling.md)。

## 课程与数据

课程包包含 3000 个来源表达、6538 个双语例句和 3885 项词汇材料，去重后共 13452 项知识，12 条路线、229 个单元。自动整理内容未逐条人工审核，详见 [课程说明](docs/full-course-pack.md) 和 [来源说明](backend/resources/THIRD_PARTY_NOTICES.md)。

真实学习数据默认在 `backend/data/learning.db`，测试数据独立。线上使用 `/var/lib/pels`；私有数据库、密码配置、录音缓存均保留在 Git 以外。更新代码不覆盖学习数据。
