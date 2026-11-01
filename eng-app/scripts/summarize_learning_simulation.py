"""Create a compact reviewable report from saved simulation evidence."""
import argparse,json,csv,sqlite3
from pathlib import Path
from collections import Counter

p=argparse.ArgumentParser();p.add_argument('--root',required=True);args=p.parse_args()
root=Path(args.root).resolve();runs=[];examples={};gaps={r:Counter() for r in ('clear','hard','forgot')}
for seed in (117,409,20261101):
 folder=root/f'final-{seed}'/str(seed)
 summary=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
 days=[json.loads(s) for s in (folder/'days.jsonl').read_text(encoding='utf-8').splitlines()]
 with sqlite3.connect('file:'+str(folder/'simulation.db')+'?mode=ro',uri=True) as connection:
  bank={r[0]:dict(english=r[1],chinese=r[2]) for r in connection.execute('SELECT id,answer,prompt FROM knowledge')}
 with (folder/'events.jsonl').open(encoding='utf-8') as source,(folder/'events-with-content.jsonl').open('w',encoding='utf-8') as target:
  for line in source:
   e=json.loads(line)
   if e.get('id') in bank:e.update(bank[e['id']])
   target.write(json.dumps(e,ensure_ascii=False)+'\n')
 events=Counter();short=0;zero=0;graduations=0;delayed=0;sample=[];last={};max_pool=0
 for line in (folder/'events.jsonl').open(encoding='utf-8'):
  e=json.loads(line);events[e['event']]+=1
  if e['event']=='shortened_gap':short+=1;zero+=e['actual']==0
  if e['event']=='answer':
   max_pool=max(max_pool,e['pool'])
   previous=last.get(e['id'])
   if previous and e['gap'] is not None:gaps[previous['rating']][e['gap']]+=1
   last[e['id']]=e
   if e['after']['due_at']:
    graduations+=1;delayed+=bool(e['days_since'] and e['days_since']>=1)
   for name,condition in [('forgot',e['rating']=='forgot'),('hard',e['rating']=='hard'),('three_clear',e['after']['streak']==3 and e['after']['due_at'] and not (e['days_since'] and e['days_since']>=1)),('delayed',e['days_since'] and e['days_since']>=7),('hint',e['hint']),('wrong',e['wrong'])]:
    if condition and name not in examples:examples[name]=dict(seed=seed,**e,**bank.get(e['id'],{}))
 active=[d for d in days if not d['absent']]
 record=dict(seed=seed,days=len(days),active_days=len(active),missed_days=len(days)-len(active),answers=summary['totals']['answers'],introduced=summary['totals']['introduced'],assertions=summary['statistics']['assertions'],faults=len(summary['faults']),stages=summary['totals']['stages'],max_pool=max_pool,max_new=max(d['plan']['new_admitted'] for d in active),max_review=max(d['plan']['review_admitted'] for d in active),feedback_edits=sum(d.get('feedback_edits',0) for d in days),hints=sum(d.get('hints',0) for d in days),wrong=sum(d.get('misspellings',0) for d in days),reopens=sum(d.get('reopens',0) for d in days),duplicate_retries=sum(d.get('duplicate_retries',0) for d in days),shortened_gaps=short,immediate_repeats=zero,graduations=graduations,delayed_passes=delayed,curve_variants=len({round(d['curve']['points'][28]['personal'],8) for d in active}),last_curve=active[-1]['curve']['points'][28]['personal'],delayed_samples=active[-1]['curve']['delayed_samples'],outcomes={r:sum(d.get(r,0) for d in days) for r in ('clear','hard','forgot')},missed_dates=[d['date'] for d in days if d['absent']],backlog_peak=max(d.get('backlog_start',0) for d in active),waiting_peak=max(d.get('waiting_end',0) for d in active))
 runs.append(record)
(root/'audit-summary.json').write_text(json.dumps(dict(runs=runs,examples=examples,gaps={r:dict(c) for r,c in gaps.items()}),ensure_ascii=False,indent=2),encoding='utf-8')
with (root/'daily-overview.csv').open('w',newline='',encoding='utf-8-sig') as f:
 fields=['seed','day','date','absent','answers','new','review','pending','clear','hard','forgot','hints','misspellings','backlog','curve_day7']
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for seed in (117,409,20261101):
  folder=root/f'final-{seed}'/str(seed)
  for line in (folder/'days.jsonl').open(encoding='utf-8'):
   d=json.loads(line);w.writerow(dict(seed=seed,day=d['day'],date=d['date'],absent=d['absent'],answers=d['answers'],new=d.get('plan',{}).get('new_admitted',''),review=d.get('plan',{}).get('review_admitted',''),pending=d.get('pool_end',''),clear=d.get('clear',''),hard=d.get('hard',''),forgot=d.get('forgot',''),hints=d.get('hints',''),misspellings=d.get('misspellings',''),backlog=d.get('backlog_start',''),curve_day7=round(d['curve']['points'][28]['personal'],5) if 'curve'in d else ''))
lines=['# 两个月随机学习模拟审计','', '使用完整课程库、真实后端服务函数和独立 SQLite 数据库。每组 60 个自然日；新学/复习上限始终为 50/50，待巩固池限制 12。模拟时间为 2026-01-01 至 2026-03-01，未修改操作系统时间。','', '| 随机种子 | 学习/缺席天数 | 答题次数 | 接触内容 | 校验次数 | 失败 | 新学峰值 | 复习峰值 | 待巩固峰值 |','|---|---|---|---|---|---|---|---|---|']
for r in runs:lines.append(f"| {r['seed']} | {r['active_days']}/{r['missed_days']} | {r['answers']} | {r['introduced']} | {r['assertions']} | {r['faults']} | {r['max_new']} | {r['max_review']} | {r['max_pool']} |")
lines+=['','## 校验范围','','- 每次答题对比 FSRS 官方库的记忆状态；核对连续独立通过、2/4/8 题目标间隔、是否应退出当天巩固、下一次日期。','- 核对重复提交、返回修改反馈、重开恢复、课程阶段、保存的答题/进度/队列、每日上限、12 项限制和 SQLite 完整性。','- 每个实际学习日保存完整学习计划、各阶段题量、30 天预测曲线 121 个点和真实延迟验证统计。缺席日不出题、不写答题记录，记录缺席，回来后继续处理积压。','- 随机用户模型独立于 FSRS：每项难度不同，练习会增强，间隔会遗忘；另有疲劳、拼错、看答案、重试、修改反馈、关闭重开和多日缺席。','', '## 本次发现并修复','','1. 情境轮结束可能遮挡今日其他任务。正常学习自动衔接轮次；某轮无可用题时继续其他内容。','2. 原限制只拦新学：到期旧词遗忘和跨日覆盖变化也会扩大待巩固池。现在满池时先处理池内内容，不再额外引入到期复习项；当天覆盖不再虚假释放尚未巩固的名额；未答题目也占位。修改旧反馈导致退回的额外内容进入等待队列，不丢记录；活动训练池始终最多 12 项。','', '## 必须知道的边界','','- 50/50 是每日不同内容上限，不是每天必做 100 项；同一项反复练习会产生多条答题。缺席、时间预算和 12 项限制都会降低实际数量。','- 2/4/8 是目标间隔。当其他可练题不足时，现有兜底规则会提前重复，甚至连续出现。日志单独记录 shortened_gap，这不等于严格隔题保证。','- 个人曲线是默认 FSRS 参数下的逐项记忆状态平均预测；本次未训练个人参数，也没有证明真实学习收益或最佳遗忘预测精度。','- 模拟直接调用真实后端业务函数，未逐题驱动浏览器/音频。孤立测试库使用 WAL/NORMAL 加速；不能据此推断正式库运行速度或突然断电的数据安全。','', '## 日志位置','','- daily-overview.csv：全部 180 天汇总，可用 Excel 打开。','- final-种子/种子/days.jsonl：逐日完整计划、曲线与统计。','- final-种子/种子/events.jsonl：逐题输入行为、反馈、间隔、前后记忆状态和异常。','- final-种子/种子/simulation.db：每组独立数据库，可复核。','- audit-summary.json：汇总和忘记/模糊/三次成功/长延迟的实例。','- preflight*、run-*：预跑和修复前的日志（中断的预跑不算通过）。','']
lines+=['## 额度与接口补充验证','','- 已发生的新学/复习名额不因整句覆盖而退还，避免设置 50 项却引入超过 50 项。当天免重复练习仍然生效。','- 恢复前一天未答完的问题，计入当天复习名额。','- quota-stress/117：独立的随机额度压力测试，确实达到新学 50 项边界。','- 另有随机 HTTP 流程测试，覆盖 POST 出题/检查/提交、重复请求、恢复、档案和导出。','- events-with-content.jsonl 补全逐题英文与中文，方便直接查看当天学了什么。','- 修复前的预跑日志保存在上一级目录；它们不计入最终通过的 180 天。','']
for r in runs:lines+= [f"### 种子 {r['seed']}",'',f"认识/模糊/忘记：{r['outcomes']}。看答案 {r['hints']} 次，拼错 {r['wrong']} 次，修改反馈 {r['feedback_edits']} 次，重开 {r['reopens']} 次，重复请求 {r['duplicate_retries']} 次。",f"缩短间隔 {r['shortened_gaps']} 次，其中连续重复 {r['immediate_repeats']} 次；第 7 天个人预测在 {r['curve_variants']} 个学习日快照中发生变化；延迟验证 {r['delayed_samples']} 次。",f"等待巩固队列峰值 {r['waiting_peak']} 项。实际题目阶段分布：{r['stages']}。缺席日期：{', '.join(r['missed_dates'])}。",'']
(root/'审计报告.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(runs,ensure_ascii=False,indent=2))
