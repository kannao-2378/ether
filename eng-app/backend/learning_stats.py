"""Learning profile derived from persisted evidence, never from fabricated session time."""
from datetime import datetime,timedelta,timezone
from sqlalchemy import text
import assessment
import memory_curve

ZONE=timezone(timedelta(hours=8))
def rank(p,e):
 if e.get('stable'):return 3
 if e.get('independent_successes',0)>0 and e.get('latest_feedback')=='clear':return 2
 return 1 if p['introduced'] or p['attempts'] or e.get('last_at') else 0

def build(c,stamp):
 today=stamp.astimezone(ZONE).date();start=today-timedelta(days=29)
 rows=c.execute(text('''SELECT a.knowledge_id,a.created_at,a.correct,a.revealed,
 COALESCE((SELECT confidence FROM feedback_events f WHERE f.question_id=a.question_id ORDER BY f.rowid DESC LIMIT 1),a.confidence) AS rating,
 EXISTS(SELECT 1 FROM spelling_checks s WHERE s.question_id=a.question_id AND s.correct=0 AND julianday(s.created_at)<=julianday(a.created_at)) AS failed
 FROM answers a WHERE NOT EXISTS(SELECT 1 FROM test_skips ts WHERE ts.question_id=a.question_id) ORDER BY a.rowid''')).mappings().all()
 buckets={str(start+timedelta(days=i)):dict(date=str(start+timedelta(days=i)),attempts=0,independent=0,items=set()) for i in range(30)}
 days=set();independent=0;hints=0;failed=0;feedback=dict(clear=0,hard=0,forgot=0);latest=None;first=None
 for row in rows:
  at=datetime.fromisoformat(row['created_at']);day=at.astimezone(ZONE).date()
  if day>today:continue
  days.add(day);first=min(first,at) if first else at;latest=max(latest,at) if latest else at
  ok=bool(row['correct'] and not row['revealed'] and not row['failed'] and row['rating']=='clear')
  independent+=ok;hints+=bool(row['revealed']);failed+=bool(row['failed']);feedback[row['rating']]+=1
  if str(day) in buckets:
   b=buckets[str(day)];b['attempts']+=1;b['independent']+=ok;b['items'].add(row['knowledge_id'])
 history={}
 for row in rows:
  if datetime.fromisoformat(row['created_at']).astimezone(ZONE).date()<=today:history.setdefault(row['knowledge_id'],[]).append(row)
 long_weak=[]
 total=c.execute(text('SELECT COUNT(*) FROM knowledge')).scalar()
 counts=[total,0,0,0];types={k:dict(total=0,touched=0,familiar=0,stable=0,transferable=0) for k in ('word','collocation','phrase','sentence','rule')};weak=[]
 entries=c.execute(text('''SELECT k.id,k.answer,k.prompt,p.*,COALESCE(json_extract(d.payload,'$.entry_type'),'collocation') AS kind
 FROM knowledge k JOIN progress p ON p.knowledge_id=k.id LEFT JOIN knowledge_details d ON d.knowledge_id=k.id''')).mappings()
 touched=0
 for p in entries:
  kind=p['kind'] if p['kind'] in types else 'collocation';types[kind]['total']+=1
  if not p['introduced'] and not p['attempts']:continue
  touched+=1;types[kind]['touched']+=1;e=assessment.get(c,p['id']);level=rank(p,e);counts[0]-=1;counts[level]+=1
  types[kind]['familiar']+=level>=2;types[kind]['stable']+=level>=3;types[kind]['transferable']+=assessment.transferable(e)
  evidence=history.get(p['id'],[])
  bad=[r for r in evidence if r['rating'] in ('hard','forgot') or r['revealed']]
  bad_days={datetime.fromisoformat(r['created_at']).astimezone(ZONE).date() for r in bad}
  recovered=len(evidence)>=3 and all(r['correct'] and not r['revealed'] and r['rating']=='clear' for r in evidence[-3:])
  if len(bad_days)>=2 and not recovered:
   long_weak.append(dict(id=p['id'],answer=p['answer'],prompt=p['prompt'],reason='跨天反复模糊或忘记' if any(r['rating'] in ('hard','forgot') for r in bad) else '跨天依赖答案提示',days=len(bad_days),last_at=p['last_at']))
  if p['attempts'] and (e.get('latest_feedback') in ('hard','forgot') or e.get('recent_independent_rate') is not None and e['recent_independent_rate']<.8):
   weak.append(dict(id=p['id'],answer=p['answer'],prompt=p['prompt'],kind=kind,feedback=e['latest_feedback'],rate=e['recent_independent_rate'],attempts=p['attempts'],last_at=p['last_at']))
 weak.sort(key=lambda w:(0 if w['feedback']=='forgot' else 1,w['rate'] if w['rate'] is not None else 1,w['last_at'] or ''))
 streak=0;cursor=today if today in days else today-timedelta(days=1)
 while cursor in days:streak+=1;cursor-=timedelta(days=1)
 longest=0;run=0;previous=None
 for day in sorted(days):
  run=run+1 if previous and day-previous==timedelta(days=1) else 1;longest=max(longest,run);previous=day
 for b in buckets.values():b['items']=len(b['items'])
 completed=sum(feedback.values())
 return dict(memory_curve=memory_curve.build(c,stamp,rows),date=str(today),summary=dict(total=total,touched=touched,completed=completed,independent=independent,independent_rate=independent/completed if completed else None,active_days=len(days),streak=streak,longest_streak=longest,hinted=hints,spelling_failed=failed,first_at=first.isoformat() if first else None,last_at=latest.isoformat() if latest else None),transfer_summary=dict(transferable=sum(t['transferable'] for t in types.values())),mastery=[dict(label=label,count=n) for label,n in zip(('未学','初识','熟悉','稳固'),counts)],types=[dict(kind=k,**v) for k,v in types.items() if v['total']],trend=list(buckets.values()),feedback=feedback,weak=weak[:10],weak_total=len(weak),long_weak=long_weak,long_weak_total=len(long_weak))
