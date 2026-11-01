"""Read-only daily learning evidence and tentative group plan."""
from datetime import datetime
from sqlalchemy import text
import group_learning as groups
import focus_training

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
  for gid in groups.active_groups(c,stamp):
   if gid in seen:continue
   r=c.execute(text('SELECT id,title,kind AS unit_type FROM learning_groups WHERE id=:g'),dict(g=gid)).mappings().first()
   if r:result['preview_review'].append(dict(r))
  result['review_waiting']=len(result['preview_review'])
  result['preview_review']=result['preview_review'][:max(0,review_limit-result['review'])]
  course_filter='' if course=='all' else "AND EXISTS(SELECT 1 FROM group_members m JOIN course_items i ON i.knowledge_id=m.knowledge_id JOIN course_units u ON u.id=i.unit_id WHERE m.group_id=g.id AND u.course_id=:course)"
  result['preview_new']=[dict(r) for r in c.execute(text("""SELECT g.id,g.title,g.kind AS unit_type FROM learning_groups g
 JOIN progress p ON p.knowledge_id=g.root_id JOIN group_primary own ON own.knowledge_id=g.root_id AND own.group_id=g.id
 WHERE p.introduced=0 AND NOT EXISTS(SELECT 1 FROM daily_group_tasks t WHERE t.group_id=g.id) """+course_filter+"""
 ORDER BY CASE WHEN g.kind='expression' THEN 0 ELSE 1 END,COALESCE((SELECT MIN(i.position) FROM group_members m JOIN course_items i ON i.knowledge_id=m.knowledge_id WHERE m.group_id=g.id),999999),g.rowid LIMIT :n"""),dict(course=course,n=max(0,new_limit-result['new']))).mappings()]
 return result
