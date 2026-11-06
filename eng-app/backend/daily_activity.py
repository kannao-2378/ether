"""Read-only daily learning evidence and tentative group plan."""
from datetime import datetime
from sqlalchemy import text
import group_learning as groups
import focus_training
import course_policy

def build(c,stamp,day,new_limit,review_limit,course='all',planning=False):
 today=groups.day_of(stamp)
 rows=c.execute(text("""SELECT a.question_id,a.knowledge_id,k.answer,k.prompt,a.correct,a.revealed,a.created_at,COALESCE(json_extract(d.payload,'$.entry_type'),'collocation') AS entry_type,
 COALESCE((SELECT confidence FROM feedback_events f WHERE f.question_id=a.question_id ORDER BY f.rowid DESC LIMIT 1),a.confidence) AS rating,
 EXISTS(SELECT 1 FROM spelling_checks s WHERE s.question_id=a.question_id AND s.correct=0 AND julianday(s.created_at)<=julianday(a.created_at)) AS failed,
 COALESCE(g.group_id,p.group_id) AS group_id
 FROM answers a JOIN knowledge k ON k.id=a.knowledge_id LEFT JOIN knowledge_details d ON d.knowledge_id=k.id LEFT JOIN group_questions g ON g.question_id=a.question_id
 LEFT JOIN group_primary p ON p.knowledge_id=a.knowledge_id
 WHERE date(a.created_at,'+8 hours')=:d AND NOT EXISTS(SELECT 1 FROM test_skips t WHERE t.question_id=a.question_id) ORDER BY a.rowid"""),dict(d=day)).mappings().all()
 items={};feedback=dict(clear=0,hard=0,forgot=0);independent=0
 for r in rows:
  ok=bool(r['correct'] and not r['revealed'] and not r['failed'] and r['rating']=='clear')
  independent+=ok;feedback[r['rating']]+=1
  item=items.setdefault(r['knowledge_id'],dict(id=r['knowledge_id'],english=r['answer'],chinese=r['prompt'],entry_type=r['entry_type'],attempts=0,independent=0,feedback=r['rating'],last_at=r['created_at']))
  item['attempts']+=1;item['independent']+=ok;item['feedback']=r['rating'];item['last_at']=r['created_at']
 booked=[dict(r) for r in c.execute(text("""SELECT t.group_id AS id,g.title,g.kind AS unit_type,t.kind,p.due_at FROM daily_group_tasks t
 JOIN learning_groups g ON g.id=t.group_id LEFT JOIN group_progress p ON p.group_id=g.id WHERE t.day=:d ORDER BY t.rowid"""),dict(d=day)).mappings()]
 practiced={r['group_id'] for r in rows}
 for b in booked:b['status']='completed' if day==today and b['due_at'] and datetime.fromisoformat(b['due_at'])>stamp else ('practiced' if b['id'] in practiced else 'started')
 result=dict(date=day,attempts=len(rows),items=list(items.values()),independent=independent,feedback=feedback,groups=booked,new=sum(b['kind']=='new' for b in booked),review=sum(b['kind']=='review' for b in booked),preview_new=[],preview_review=[])
 type_counts={kind:sum(i['entry_type']==kind for i in items.values()) for kind in ('word','collocation','phrase','sentence','rule')}
 result.update(type_counts=type_counts,studied_groups=len(practiced-{None}),studied_new=sum(b['kind']=='new' and b['id'] in practiced for b in booked),studied_review=sum(b['kind']=='review' and b['id'] in practiced for b in booked))
 result['focus']=focus_training.listing(c,day) if planning and day==today else []
 result['special']=sum(b['kind']=='special' and b['id'] in practiced for b in booked)
 if planning and day==today:
  seen={b['id'] for b in booked}
  active=groups.active_groups(c,stamp);permitted=course_policy.allowed(c,active+[b['id'] for b in booked],course,result['new']<new_limit)
  for b in booked:
   if b['id'] not in permitted and b['kind']!='special' and b['status']!='completed':b['status']='waiting'
  for gid in course_policy.ordered(c,active):
   if gid not in permitted:continue
   if gid in seen:continue
   r=c.execute(text('SELECT id,title,kind AS unit_type FROM learning_groups WHERE id=:g'),dict(g=gid)).mappings().first()
   if r:result['preview_review'].append(dict(r))
  result['review_waiting']=len(result['preview_review'])
  result['preview_review']=result['preview_review'][:max(0,review_limit-result['review'])]
  remaining=max(0,new_limit-result['new'])
  ready={r['id'] for r in course_policy.unseen(c,course,remaining)}
  planned=c.execute(text("SELECT g.id,g.title,g.kind AS unit_type FROM curriculum_paths cp JOIN curriculum_goals cg ON cg.id=cp.goal_id JOIN learning_groups g ON g.id=cg.id JOIN progress p ON p.knowledge_id=g.root_id WHERE (:c='all' OR cp.course_id=:c) AND cg.status='ready' AND p.introduced=0 AND NOT EXISTS(SELECT 1 FROM daily_group_tasks d WHERE d.group_id=g.id) ORDER BY cp.unit_position,cg.difficulty,cp.position LIMIT :n"),dict(c=course,n=remaining)).mappings().all()
  result['preview_new']=[dict(r,status='planned' if r['id'] in ready else 'waiting',prerequisites_ready=r['id'] in ready) for r in planned]
  result['new_planned']=result['new']+len(planned)
  result['review_planned']=result['review']+len(result['preview_review'])
  result['new_wait_reason']='后续内容须先完成基础，按顺序逐步开始' if any(r['id'] not in ready for r in planned) else ''

 return result
