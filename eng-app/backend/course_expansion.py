"""Source-backed expression breadth, attached to the same prerequisite-aware route."""
import json,hashlib
from functools import lru_cache
from pathlib import Path
from datetime import datetime,timezone
from sqlalchemy import text
import curriculum_engine as ce
RESOURCE=Path(__file__).parent/'resources/course_expansion.json'
def load():return json.loads(RESOURCE.read_text(encoding='utf-8'))
@lru_cache(maxsize=1)
def summary():
 if not RESOURCE.exists():return None
 s=load();return dict(**s['counts'],policy=s['stage_policy'],source=s['source'])
def install(c):
 if not RESOURCE.exists():return
 raw=RESOURCE.read_bytes();revision='source-expansion-v4:'+hashlib.sha256(raw).hexdigest()
 if c.execute(text('SELECT 1 FROM curriculum_versions WHERE id=:v'),dict(v=revision)).first():return
 s=json.loads(raw);main=json.loads(RESOURCE.with_name('mainline_course.json').read_text(encoding='utf-8'))
 existing=set(c.execute(text('SELECT id FROM knowledge')).scalars())
 catalog={}
 if c.execute(text("SELECT 1 FROM sqlite_master WHERE name='shared_sentence_catalog'")).first():catalog={(a,b):k for a,b,k in c.execute(text('SELECT en_id,zh_id,knowledge_id FROM shared_sentence_catalog'))}
 words=s['words'];stamp=datetime.now(timezone.utc).isoformat()
 used={w for lesson in s['lessons'] for w in lesson['materials']}
 for term in used:
  w=words[term]
  if w['id'] not in existing:
   ce.card(c,w['id'],w['answer'],w['prompt'],w.get('details',{}).get('usage') or w['prompt'],w['answer'],w['prompt'],'word',replace=False)
   existing.add(w['id'])
 goals=[];paths=[];prereqs=[];lessons=[];members=[];primary=[];links=[];reqs=[];transfer=[];combos=[];groups=[]
 for n,g in enumerate(s['lessons']):
  source_id=g['id'];gid=source_id;stage=int(g['stage'][1:]);demo=g['sentences'][0]
  owner=c.execute(text('SELECT group_id FROM group_primary WHERE knowledge_id=:k'),dict(k=source_id)).scalar()
  if owner and owner!=source_id:
   gid='expansion-'+source_id
   c.execute(text("DELETE FROM curriculum_paths WHERE course_id='general-mainline' AND goal_id=:g"),dict(g=source_id))
   c.execute(text('INSERT OR IGNORE INTO curriculum_aliases VALUES(:k,:a)'),dict(k=gid,a=source_id))
  # Original identity and original learner evidence are reused, never copied.
  if gid not in existing:ce.card(c,gid,g['english'],g['chinese'],g['chinese'],demo['en'],demo['zh'],'collocation',replace=False);existing.add(gid)
  groups.append(dict(g=gid,a=g['english']));primary.append(dict(k=gid,g=gid))
  goals.append(dict(g=gid,o='使用 '+g['english'],d=min(stage,6),v=revision))
  paths.append(dict(u='breadth-'+g['stage'],t=g['stage']+' · 表达应用',o='原始双语材料；先补必要词汇，再回忆表达与尝试新句。',up=stage,g=gid,p=10000+n))
  anchors=[x['key'] for x in main['goals'] if x['unit']==('R%02d'%(stage-1))] if stage>1 else [x['key'] for x in main['goals'][:2]]
  for dep in anchors:prereqs.append(dict(g=gid,d=dep))
  lessons.append(dict(g=gid,k=gid,r='base',p=10));members.append(dict(g=gid,k=gid,r='base',p=10))
  mids=[words[t]['id'] for t in g['materials']]
  for mid in mids:
   if mid==gid:continue
   lessons.append(dict(g=gid,k=mid,r='word',p=0));members.append(dict(g=gid,k=mid,r='word',p=0));primary.append(dict(k=mid,g=gid))
  for i,row in enumerate(g['sentences']):
   kid='course-context-'+hashlib.sha256((gid+':'+str(row['en_id'])+':'+str(row['zh_id'])).encode()).hexdigest()[:24]
   source=catalog.get((row['en_id'],row['zh_id']))
   if source:c.execute(text('INSERT OR IGNORE INTO curriculum_aliases VALUES(:k,:a)'),dict(k=kid,a=source))
   if kid not in existing:
    ce.card(c,kid,row['en'],row['zh'],'',row['en'],row['zh'],'sentence',replace=False)
    details=dict(entry_type='sentence',speech_text=row['en'],accepted_answers=[row['en']],examples=[dict(en=row['en'],zh=row['zh'],source_url='https://tatoeba.org/en/sentences/show/'+str(row['en_id']),translation_url='https://tatoeba.org/en/sentences/show/'+str(row['zh_id']),attribution='Tatoeba: '+str(row['en_author'])+' / '+str(row['zh_author']),license='CC BY 2.0 FR')],source_note=s['source'])
    c.execute(text('UPDATE knowledge_details SET payload=:p WHERE knowledge_id=:k'),dict(k=kid,p=json.dumps(details,ensure_ascii=False)));existing.add(kid)
   role='sentence' if i==0 else 'transfer';position=30 if i==0 else 40+i
   lessons.append(dict(g=gid,k=kid,r=role,p=position));members.append(dict(g=gid,k=kid,r=role,p=position));primary.append(dict(k=kid,g=gid));links.append(dict(k=kid,g=gid,s=3 if i==0 else 4))
   for mid in [gid]+[words[t]['id'] for t in row['words']]:
    if mid!=kid:reqs.append(dict(k=kid,m=mid))
   if i:
    material=[words[t]['id'] for t in row['words'] if t not in g['english'].casefold().split() and t not in {'i','you','he','she','it','we','they','a','an','the','to','is','are','am'}]
    for mid in material:transfer.append(dict(k=kid,m=mid))
    if material:combos.append(dict(k=kid,g=gid,m=material[0]))
 def batch(sql,rows):
  if rows:c.execute(text(sql),rows)
 batch('INSERT OR IGNORE INTO learning_groups VALUES(:g,:g,:a,\'expression\')',groups)
 batch('INSERT OR IGNORE INTO group_primary VALUES(:k,:g)',primary)
 batch("INSERT INTO curriculum_goals VALUES(:g,:o,:d,'ready',:v) ON CONFLICT(id) DO UPDATE SET objective=excluded.objective,difficulty=excluded.difficulty,status='ready',revision=excluded.revision",goals)
 batch("INSERT OR REPLACE INTO curriculum_paths VALUES('general-mainline',:u,:t,:o,:up,:g,:p,1)",paths)
 batch('DELETE FROM curriculum_prerequisites WHERE goal_id=:g',[dict(g=g['g']) for g in goals])
 batch('INSERT OR IGNORE INTO curriculum_prerequisites VALUES(:g,:d)',prereqs)
 batch('DELETE FROM curriculum_lessons WHERE goal_id=:g',[dict(g=g['g']) for g in goals])
 batch('INSERT OR REPLACE INTO curriculum_lessons VALUES(:g,:k,:r,:p,1)',lessons)
 batch('INSERT INTO group_members VALUES(:g,:k,:r,:p) ON CONFLICT(group_id,knowledge_id) DO UPDATE SET role=excluded.role,position=excluded.position',members)
 batch("INSERT OR IGNORE INTO course_links VALUES(:k,:g,:s,'Tatoeba official direct pair')",links)
 batch('INSERT OR IGNORE INTO group_requirements VALUES(:k,:m)',reqs)
 batch('INSERT OR IGNORE INTO transfer_materials VALUES(:k,:m)',transfer)
 batch('INSERT OR IGNORE INTO sentence_combinations VALUES(:k,:g,:m,1)',combos)
 c.execute(text('INSERT INTO curriculum_versions VALUES(:v)'),dict(v=revision))
