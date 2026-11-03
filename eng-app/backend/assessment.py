"""Evidence-based assessment: subjective feedback, retention and transfer stay separate."""
import json
import transfer_evidence
from datetime import datetime,timedelta,timezone
from sqlalchemy import text

def transferable(e):
 return bool(e.get('transfer_contexts',0)>=2 and e.get('last_transfer_ok',False))

def install(c):
 c.execute(text('CREATE TABLE IF NOT EXISTS knowledge_assessments(knowledge_id TEXT PRIMARY KEY,payload TEXT NOT NULL)'))

def calculate(c,kid):
 rows=[dict(r) for r in c.execute(text('''SELECT a.*,COALESCE((SELECT f.confidence FROM feedback_events f WHERE f.question_id=a.question_id ORDER BY f.rowid DESC LIMIT 1),a.confidence) AS rating,
 EXISTS(SELECT 1 FROM spelling_checks s WHERE s.question_id=a.question_id AND s.correct=0 AND julianday(s.created_at)<=julianday(a.created_at)) AS failed
 FROM answers a WHERE a.knowledge_id=:k AND NOT EXISTS(SELECT 1 FROM test_skips ts WHERE ts.question_id=a.question_id) ORDER BY a.rowid'''),dict(k=kid)).mappings()]
 history=[];previous=None;max_gap=0;delayed=0;days=set()
 for row in rows:
  stamp=datetime.fromisoformat(row['created_at'])
  independent=bool(row['correct'] and not row['revealed'] and not row['failed'] and row['rating']=='clear')
  gap=(stamp-previous).total_seconds()/86400 if previous else 0
  if independent:
   days.add(stamp.astimezone(timezone(timedelta(hours=8))).date().isoformat())
   if gap>=1:delayed+=1;max_gap=max(max_gap,gap)
  history.append(independent);previous=stamp
 recent=history[-10:];rate=sum(recent)/len(recent) if recent else None
 stable=len(days)>=3 and delayed>=2 and max_gap>=7 and rate is not None and rate>=.8 and bool(history[-1])
 if not rows:retention='尚无独立测试记录'
 elif not history[-1]:retention='当前待巩固'
 elif stable:retention='跨时段记忆较稳固'
 elif delayed:retention='已有延迟记忆证据'
 else:retention='当天能回忆，长期记忆待验证'
 # Use structural/material links as explicit evidence scope; never grant component mastery.
 uses=[dict(r) for r in c.execute(text('''SELECT a.created_at,sc.material_id,sc.knowledge_id,
 a.correct,a.revealed,COALESCE((SELECT f.confidence FROM feedback_events f WHERE f.question_id=a.question_id ORDER BY f.rowid DESC LIMIT 1),a.confidence) AS rating,
 EXISTS(SELECT 1 FROM spelling_checks s WHERE s.question_id=a.question_id AND s.correct=0 AND julianday(s.created_at)<=julianday(a.created_at)) AS failed
 FROM sentence_combinations sc JOIN answers a ON a.knowledge_id=sc.knowledge_id
 JOIN question_trials qt ON qt.question_id=a.question_id AND qt.mode IN ('transfer','transfer-review')
 WHERE (sc.structure_id=:k OR sc.material_id=:k OR sc.knowledge_id=:k OR EXISTS(SELECT 1 FROM transfer_materials tm WHERE tm.knowledge_id=sc.knowledge_id AND tm.material_id=:k))
 AND NOT EXISTS(SELECT 1 FROM test_skips ts WHERE ts.question_id=a.question_id) ORDER BY a.rowid'''),dict(k=kid)).mappings()]
 successful=[r for r in uses if r['correct'] and not r['revealed'] and not r['failed'] and r['rating']=='clear']
 contexts=len({r['material_id'] for r in successful})
 transfer_days=len({datetime.fromisoformat(r['created_at']).astimezone(timezone(timedelta(hours=8))).date().isoformat() for r in successful})
 last_transfer_ok=bool(uses and uses[-1]['correct'] and not uses[-1]['revealed'] and not uses[-1]['failed'] and uses[-1]['rating']=='clear')
 transfer='尚无迁移验证' if not uses else '近期迁移表现待练习' if not last_transfer_ok else '多情境、跨日使用有证据' if contexts>=3 and transfer_days>=2 else '已有不同情境使用证据' if contexts>=2 else '仅在一种材料中验证'
 result=dict(transferable=contexts>=2 and last_transfer_ok,last_transfer_ok=last_transfer_ok,transfer_label='未验证' if not uses else '待练习' if not last_transfer_ok else '可迁移' if contexts>=2 else '初步会用',evidence_version=transfer_evidence.VERSION,latest_feedback=rows[-1]['rating'] if rows else None,last_at=rows[-1]['created_at'] if rows else None,retention=retention,stable=stable,independent_successes=sum(history),independent_days=len(days),delayed_successes=delayed,longest_gap_days=round(max_gap,1),recent_independent_rate=round(rate,2) if rate is not None else None,transfer=transfer,transfer_contexts=contexts,transfer_successes=len(successful),transfer_days=transfer_days,criteria='稳固：至少3个独立成功日、2次间隔≥24小时成功，其中一次间隔≥7天；最近10次独立通过率≥80%，最近一次通过。此为初始可调规则。')
 return result

def refresh(c,kid):
 install(c)
 affected={kid}
 current=kid
 while current:
  current=c.execute(text('SELECT parent_id FROM course_links WHERE knowledge_id=:k'),dict(k=current)).scalar()
  if current:affected.add(current)
 for row in c.execute(text('SELECT structure_id,material_id FROM sentence_combinations WHERE knowledge_id=:k'),dict(k=kid)):affected.update(row)
 affected.update(c.execute(text('SELECT material_id FROM transfer_materials WHERE knowledge_id=:k'),dict(k=kid)).scalars())
 if c.execute(text("SELECT 1 FROM sqlite_master WHERE name='knowledge_components'")).first():affected.update(c.execute(text("SELECT component_id FROM knowledge_components WHERE knowledge_id=:k AND relation='contains_expression'"),dict(k=kid)).scalars())
 for key in affected:
  payload=calculate(c,key)
  c.execute(text('INSERT INTO knowledge_assessments VALUES(:k,:p) ON CONFLICT(knowledge_id) DO UPDATE SET payload=excluded.payload'),dict(k=key,p=json.dumps(payload,ensure_ascii=False)))

def get(c,kid):
 raw=c.execute(text('SELECT payload FROM knowledge_assessments WHERE knowledge_id=:k'),dict(k=kid)).scalar()
 cached=json.loads(raw) if raw else None
 return cached if cached and cached.get('evidence_version')==transfer_evidence.VERSION else calculate(c,kid)
