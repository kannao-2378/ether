"""Course order and minimal core materials, independent of review timing."""
import re
import curriculum_engine
from sqlalchemy import text,bindparam
from datetime import timedelta
STRUCTURE_WORDS=set("to at for a an the of on in with by doing do something someone about after before into up down off out over under through from as without upon".split())

def core_members(c,gid,rows):
 lesson={r[0]:r for r in c.execute(text('SELECT knowledge_id,role,position FROM curriculum_lessons WHERE goal_id=:g'),dict(g=gid))}
 if lesson:
  root=c.execute(text('SELECT root_id FROM learning_groups WHERE id=:g'),dict(g=gid)).scalar()
  selected=[dict(r,role=lesson[r['id']][1],position=lesson[r['id']][2]) for r in rows if r['id'] in lesson]
  return sorted([r for r in selected if r['id']==root or r['role']!='word' or not curriculum_engine.material_covered(c,gid,r['id'])],key=lambda r:r['position'])
 root=c.execute(text('SELECT root_id FROM learning_groups WHERE id=:g'),dict(g=gid)).scalar()
 anchors=[r for r in rows if r['id']==root or r['role'] in ('base','phrase')]
 tokens=set(re.findall('[a-z]+',' '.join(r['answer'] for r in anchors).casefold()))
 result=[]
 for r in rows:
  if r['role']=='word' and r['id']!=root:
   if r['answer'].casefold() in STRUCTURE_WORDS:continue
   if any(a['id']==root and a['level']>=3 for a in rows):continue
   if r['answer'].casefold() not in tokens:continue
   known_form=c.execute(text("SELECT 1 FROM progress p JOIN knowledge_details d ON d.knowledge_id=p.knowledge_id JOIN json_each(d.payload,'$.forms') f WHERE p.level>=3 AND lower(f.value)=:word AND p.knowledge_id!=:k LIMIT 1"),dict(word=r['answer'].casefold(),k=r['id'])).first()
   if known_form:continue
  result.append(r)
 return result

def owns_review(c,gid,r):
 if r['role'] not in ('word','sentence_word'):return True
 owner=c.execute(text('SELECT group_id FROM group_primary WHERE knowledge_id=:k'),dict(k=r['id'])).scalar()
 return owner==gid

def unseen(c,course='all',limit=1):
 return curriculum_engine.candidates(c,course,limit)



def ordered(c,gids):
 if not gids:return []
 rows=c.execute(text("SELECT g.id,CASE WHEN u.course_id='foundation' THEN 0 WHEN u.course_id IS NOT NULL THEN (SELECT rowid FROM learning_courses WHERE id=u.course_id) ELSE 999999 END AS course_order,COALESCE(u.position,999999) AS unit_order,COALESCE(i.position,999999) AS item_order FROM learning_groups g LEFT JOIN course_items i ON i.knowledge_id=g.root_id LEFT JOIN course_units u ON u.id=i.unit_id WHERE g.id IN :ids ORDER BY COALESCE((SELECT MIN(p.unit_position*1000000+t.difficulty*10000+p.position) FROM curriculum_paths p JOIN curriculum_goals t ON t.id=p.goal_id WHERE t.status='ready' AND p.goal_id=g.id AND p.course_id='foundation'),999999999),course_order,unit_order,item_order,g.rowid").bindparams(bindparam('ids',expanding=True)),dict(ids=list(dict.fromkeys(gids)))).all()
 return [r[0] for r in rows]

def allowed(c,gids,course,include_new=True):
 prospective=[r['id'] for r in unseen(c,course,3)] if include_new else []
 roots=ordered(c,list(gids)+prospective);new=[];result=set()
 for gid in roots:
  if not c.execute(text('SELECT 1 FROM learning_groups g JOIN group_primary own ON own.knowledge_id=g.root_id AND own.group_id=g.id JOIN group_members m ON m.group_id=g.id WHERE g.id=:g LIMIT 1'),dict(g=gid)).first():continue
  introduced=c.execute(text('SELECT p.introduced FROM learning_groups g JOIN progress p ON p.knowledge_id=g.root_id WHERE g.id=:g'),dict(g=gid)).scalar()
  if introduced:result.add(gid)
  elif len(new)<3 and c.execute(text("SELECT 1 FROM curriculum_goals WHERE id=:g AND status='ready'"),dict(g=gid)).first() and not curriculum_engine.blockers(c,gid):new.append(gid);result.add(gid)
 return result

def finish(c,gid,stamp,pending):
 dates=c.execute(text('SELECT p.due_at FROM group_members m JOIN group_primary own ON own.knowledge_id=m.knowledge_id AND own.group_id=m.group_id JOIN progress p ON p.knowledge_id=m.knowledge_id WHERE m.group_id=:g AND p.introduced=1 AND julianday(p.due_at)>julianday(:t)'),dict(g=gid,t=stamp.isoformat())).scalars().all()
 due=min(dates) if dates else (stamp+timedelta(days=1)).isoformat()
 c.execute(text('INSERT INTO group_progress VALUES(:g,:d,:t,:p) ON CONFLICT(group_id) DO UPDATE SET due_at=excluded.due_at,last_at=excluded.last_at,transfer_pending=excluded.transfer_pending'),dict(g=gid,d=due,t=stamp.isoformat(),p=int(pending)))
 c.execute(text('DELETE FROM group_active_slots WHERE group_id=:g'),dict(g=gid))


def pause_lower(c,gid):
 waiting=c.execute(text("SELECT s.group_id FROM group_active_slots s JOIN learning_groups g ON g.id=s.group_id JOIN progress p ON p.knowledge_id=g.root_id WHERE p.introduced=0 AND s.group_id NOT LIKE 'focus-%'")).scalars().all()
 ranked=ordered(c,waiting+[gid])
 if len(ranked)>1 and ranked[-1]!=gid:c.execute(text('DELETE FROM group_active_slots WHERE group_id=:g'),dict(g=ranked[-1]))


def register_core(c):
 roots=c.execute(text("SELECT g.id,k.answer FROM learning_groups g JOIN knowledge k ON k.id=g.root_id JOIN course_items i ON i.knowledge_id=g.root_id JOIN course_units u ON u.id=i.unit_id WHERE g.kind='expression' AND u.course_id='foundation'")).all()
 grammar=STRUCTURE_WORDS
 for gid,en in roots:
  for token in set(re.findall('[a-z]+',en.casefold()))-grammar:
   kid=c.execute(text("SELECT id FROM knowledge WHERE lower(answer)=:a ORDER BY CASE WHEN id LIKE 'word-%' THEN 0 ELSE 1 END,rowid LIMIT 1"),dict(a=token)).scalar()
   if kid:c.execute(text("INSERT OR IGNORE INTO group_members VALUES(:g,:k,'word',0)"),dict(g=gid,k=kid))


def covered_function(c,kid,material):
 word=c.execute(text('SELECT answer FROM knowledge WHERE id=:k'),dict(k=material)).scalar()
 if not word or (word.casefold() not in STRUCTURE_WORDS|{'my','your','his','her','our','their'} and ' ' not in word):return False
 phrases=c.execute(text("SELECT k.answer FROM group_members target JOIN group_members m ON m.group_id=target.group_id JOIN progress p ON p.knowledge_id=m.knowledge_id JOIN knowledge k ON k.id=m.knowledge_id WHERE target.knowledge_id=:k AND m.role IN ('base','phrase') AND p.level>=3"),dict(k=kid)).scalars().all()
 return any(re.search(r'(?<![a-z])'+re.escape(word)+r'(?![a-z])',phrase,re.I) for phrase in phrases)
