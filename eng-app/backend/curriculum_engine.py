from selection_cache import memoized
"""One prerequisite-aware teaching registry for every course; learner evidence stays separate."""
import json,hashlib,re
import pronunciation_metadata
from pathlib import Path
from datetime import datetime,timezone
from sqlalchemy import text,bindparam
def gloss(value):return re.sub(r'\W+','',re.sub(r'[（(].*?[）)]','',value or '')).casefold()

MANIFEST=Path(__file__).parent/'resources/teaching_routes.json'
TRANSFER_PACK=Path(__file__).parent/'resources/transfer_practice.psv'
TABLES=('curriculum_goals','curriculum_paths','curriculum_prerequisites','curriculum_lessons','curriculum_aliases','curriculum_versions')

def install(c):
 for sql in [
  "CREATE TABLE IF NOT EXISTS curriculum_goals(id TEXT PRIMARY KEY,objective TEXT NOT NULL,difficulty INTEGER NOT NULL DEFAULT 1,status TEXT NOT NULL DEFAULT 'draft',revision TEXT)",
  "CREATE TABLE IF NOT EXISTS curriculum_paths(course_id TEXT,unit_id TEXT,unit_title TEXT,unit_goal TEXT,unit_position INTEGER,goal_id TEXT,position INTEGER,authored INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(course_id,unit_id,goal_id))",
  "CREATE TABLE IF NOT EXISTS curriculum_prerequisites(goal_id TEXT,prerequisite_id TEXT,PRIMARY KEY(goal_id,prerequisite_id))",
  "CREATE TABLE IF NOT EXISTS curriculum_lessons(goal_id TEXT,knowledge_id TEXT,role TEXT,position INTEGER,required INTEGER NOT NULL DEFAULT 1,PRIMARY KEY(goal_id,knowledge_id))",
  "CREATE TABLE IF NOT EXISTS curriculum_aliases(knowledge_id TEXT,alias_id TEXT,PRIMARY KEY(knowledge_id,alias_id))",
  "CREATE TABLE IF NOT EXISTS curriculum_versions(id TEXT PRIMARY KEY)",
  "CREATE INDEX IF NOT EXISTS curriculum_path_order ON curriculum_paths(course_id,unit_position,position)"]:
  c.execute(text(sql))
 if 'authored' not in [r[1] for r in c.execute(text('PRAGMA table_info(curriculum_paths)'))]:c.execute(text('ALTER TABLE curriculum_paths ADD COLUMN authored INTEGER NOT NULL DEFAULT 0'))
 c.execute(text("INSERT OR IGNORE INTO curriculum_goals(id,objective,status) SELECT id,title,'draft' FROM learning_groups WHERE id NOT LIKE 'focus-%'"))
 c.execute(text("""INSERT OR IGNORE INTO curriculum_paths(course_id,unit_id,unit_title,unit_goal,unit_position,goal_id,position) SELECT DISTINCT u.course_id,u.id,u.title,u.goal,u.position,g.group_id,MIN(i.position)
 FROM course_items i JOIN course_units u ON u.id=i.unit_id JOIN group_primary g ON g.knowledge_id=i.knowledge_id JOIN curriculum_goals t ON t.id=g.group_id AND t.status='draft' GROUP BY u.id,g.group_id"""))
 raw=MANIFEST.read_bytes();extra=TRANSFER_PACK.read_bytes();revision='registry-v4:'+hashlib.sha256(raw+extra).hexdigest()
 if c.execute(text('SELECT 1 FROM curriculum_versions WHERE id=:v'),dict(v=revision)).first():return
 spec=json.loads(raw);goals={g['key']:g for g in spec['goals']}
 for line in extra.decode('utf-8-sig').splitlines():
  if not line.strip() or line.startswith('#'):continue
  target,en,zh,deps=[s.strip() for s in line.split('|')]
  if target not in goals:raise ValueError('unknown transfer target '+target)
  variants=goals[target].setdefault('variants',[])
  if not any(v['en'].strip().casefold().rstrip('.!?')==en.casefold().rstrip('.!?') for v in variants):variants.append(dict(en=en,zh=zh,requires=deps.split(',') if deps else []))
 publish(c,spec,revision)
 c.execute(text('INSERT INTO curriculum_versions VALUES(:v)'),dict(v=revision))

def publish(c,spec,revision='custom'):
 """Validate before mutating. May be used by future course manifests without engine changes."""
 if not c.execute(text('SELECT 1 FROM learning_courses WHERE id=:c'),dict(c=spec['course_id'])).first():raise ValueError('unknown course')
 goals=spec['goals'];keys={g['key'] for g in goals}
 if len(keys)!=len(goals):raise ValueError('duplicate teaching goal')
 ids={}
 for g in goals:
  preferred=g.get('id',g['key'])
  existing=c.execute(text('SELECT answer FROM knowledge WHERE id=:p'),dict(p=preferred)).scalar()
  if existing and existing.casefold()!=g['english'].casefold():raise ValueError('knowledge identity cannot change English')
  rows=c.execute(text("SELECT k.id,k.prompt,p.introduced FROM knowledge k JOIN progress p ON p.knowledge_id=k.id JOIN group_primary own ON own.knowledge_id=k.id JOIN learning_groups lg ON lg.id=own.group_id AND lg.root_id=k.id WHERE lower(k.answer)=lower(:a) ORDER BY k.id=:p DESC,k.rowid"),dict(a=g['english'],p=preferred)).all()
  row=next((r for r in rows if r[0]==preferred or not r[2] or gloss(r[1])==gloss(g['chinese'])),None)
  if existing and not row:raise ValueError('existing material must be reused through its teaching group')
  ids[g['key']]=row[0] if row and spec.get('reuse_existing_roots',True) else preferred
 if len(set(ids.values()))!=len(ids):raise ValueError('duplicate goal identity; reuse one goal instead')
 graph={r[0]:[] for r in c.execute(text("SELECT id FROM curriculum_goals WHERE status='ready'"))}
 for a,b in c.execute(text('SELECT goal_id,prerequisite_id FROM curriculum_prerequisites')):graph.setdefault(a,[]).append(b)
 removed=[]
 if spec.get('replace_course'):
  old=c.execute(text('SELECT goal_id FROM curriculum_paths WHERE course_id=:c AND authored=1'),dict(c=spec['course_id'])).scalars().all()
  removed=[g for g in old if g not in ids.values()]
  for g in removed:
   if not c.execute(text('SELECT 1 FROM curriculum_paths WHERE goal_id=:g AND course_id!=:c AND authored=1'),dict(g=g,c=spec['course_id'])).first():graph.pop(g,None)
 for g in goals:graph[ids[g['key']]]=[ids.get(dep,dep) for dep in g.get('requires',[])]
 checked=set()
 def visit(k,chain):
  if k in checked:return
  if k in chain:raise ValueError('cyclic course prerequisites')
  if k not in graph:raise ValueError('missing course prerequisite '+k)
  for dep in graph[k]:visit(dep,chain|{k})
  checked.add(k)
 for k in graph:visit(k,set())
 if any(type(g.get('difficulty',1)) is not int or not 1<=g.get('difficulty',1)<=6 for g in goals):raise ValueError('invalid goal difficulty')
 if any(not g.get('objective') or not g.get('usage') or not g.get('sentence') or not g.get('chinese') for g in goals):raise ValueError('incomplete teaching content')
 material_ids={}
 for g in goals:
  for m in g.get('materials',[]):
   choices=c.execute(text('SELECT id,prompt FROM knowledge WHERE lower(answer)=lower(:a) ORDER BY rowid'),dict(a=m['en'])).all()
   row=next((r for r in choices if r[0]==m.get('id') or gloss(r[1])==gloss(m['zh'])),None)
   mid=row[0] if row else ids[g['key']]+'-material-'+hashlib.sha256((m['en'].casefold()+'|'+gloss(m['zh'])).encode()).hexdigest()[:12]
   material_ids.setdefault(m['en'].casefold(),mid)
 for g in goals:
  for v in g.get('variants',[]):
   for dep in v.get('requires',[]):
    if dep.startswith('material:'):
     if dep[9:].casefold() not in material_ids:raise ValueError('missing authored material '+dep)
     continue
    if dep not in ids and not c.execute(text('SELECT 1 FROM knowledge WHERE id=:k'),dict(k=dep)).first():raise ValueError('missing transfer material '+dep)
 units={u['id']:u for u in spec['units']}
 if any(g['unit'] not in units for g in goals):raise ValueError('unknown teaching unit')
 for gid in removed:
  c.execute(text('DELETE FROM curriculum_paths WHERE course_id=:c AND goal_id=:g AND authored=1'),dict(c=spec['course_id'],g=gid))
  c.execute(text("UPDATE curriculum_goals SET status='retired' WHERE id=:g AND NOT EXISTS(SELECT 1 FROM curriculum_paths WHERE goal_id=:g AND authored=1)"),dict(g=gid))
 variant_links=[]
 for g in goals:
  kid=ids[g['key']]
  card(c,kid,g['english'],g['chinese'],g['usage'],g['sentence'],g['sentence_zh'],'word' if ' ' not in g['english'] else 'collocation')
  c.execute(text("INSERT OR IGNORE INTO learning_groups VALUES(:k,:k,:a,:kind)"),dict(k=kid,a=g['english'],kind='word' if ' ' not in g['english'] else 'expression'))
  c.execute(text('INSERT OR IGNORE INTO group_primary VALUES(:k,:k)'),dict(k=kid))
 for pos,g in enumerate(goals):
  gid=ids[g['key']];u=units[g['unit']]
  c.execute(text("INSERT INTO curriculum_goals VALUES(:g,:o,:d,'ready',:v) ON CONFLICT(id) DO UPDATE SET objective=excluded.objective,difficulty=excluded.difficulty,status='ready',revision=excluded.revision"),dict(g=gid,o=g['objective'],d=g.get('difficulty',1),v=revision))
  # Replace source locations in this course only; other courses can reuse this goal.
  c.execute(text('DELETE FROM curriculum_paths WHERE goal_id=:g AND (course_id=:c OR authored=0)'),dict(c=spec['course_id'],g=gid))
  c.execute(text('INSERT INTO curriculum_paths VALUES(:c,:u,:t,:o,:up,:g,:p,1)'),dict(c=spec['course_id'],u=u['id'],t=u['title'],o=u['goal'],up=u['position'],g=gid,p=pos))
  c.execute(text('DELETE FROM curriculum_prerequisites WHERE goal_id=:g'),dict(g=gid))
  for dep in g.get('requires',[]):c.execute(text('INSERT INTO curriculum_prerequisites VALUES(:g,:d)'),dict(g=gid,d=ids.get(dep,dep)))
  c.execute(text('DELETE FROM curriculum_lessons WHERE goal_id=:g'),dict(g=gid))
  root_role='word' if ' ' not in g['english'] else 'base'
  member(c,gid,gid,root_role,10)
  mats=[]
  for m in g.get('materials',[]):
   choices=c.execute(text('SELECT id,prompt FROM knowledge WHERE lower(answer)=lower(:a) ORDER BY rowid'),dict(a=m['en'])).all()
   row=next((r for r in choices if r[0]==m.get('id') or gloss(r[1])==gloss(m['zh'])),None)
   mid=row[0] if row else gid+'-material-'+hashlib.sha256((m['en'].casefold()+'|'+gloss(m['zh'])).encode()).hexdigest()[:12]
   card(c,mid,m['en'],m['zh'],m.get('usage',m['en']+' 表示“'+m['zh']+'”。'),m['en'],m['zh'],'word' if ' ' not in m['en'] else 'phrase',replace=False)
   
   if mid not in ids.values() and not spec.get('preserve_existing_ownership',False):
    old=c.execute(text('SELECT group_id FROM group_primary WHERE knowledge_id=:k'),dict(k=mid)).scalar()
    if old==mid:c.execute(text('UPDATE group_primary SET group_id=:g WHERE knowledge_id=:k'),dict(g=gid,k=mid))
   c.execute(text('INSERT OR IGNORE INTO group_primary VALUES(:k,:g)'),dict(k=mid,g=gid))
   member(c,gid,mid,'sentence_word' if m['en']=='I' else 'word',0 if m['en']!='I' else 25);mats.append(mid)
  lesson_ids=[gid]
  for role,en,zh in [('phrase',g.get('phrase'),g.get('phrase_zh')),('sentence',g['sentence'],g['sentence_zh'])]+[('transfer',v['en'],v['zh']) for v in g.get('variants',[])]:
   if not en or en==g['english']:continue
   kid=gid+'-lesson-'+role+'-'+hashlib.sha256(en.strip().casefold().rstrip('.!?').encode()).hexdigest()[:12];lesson_ids.append(kid)
   card(c,kid,en,zh,g['usage'],en,zh,'sentence' if role in ('sentence','transfer') else 'phrase')
   c.execute(text('INSERT OR IGNORE INTO course_links VALUES(:k,:p,:s,:src)'),dict(k=kid,p=gid,s={'phrase':2,'sentence':3,'transfer':4}[role],src='自编课程，统一先修编排'))
   c.execute(text('INSERT OR IGNORE INTO group_primary VALUES(:k,:g)'),dict(k=kid,g=gid))
   member(c,gid,kid,role,{'phrase':20,'sentence':30,'transfer':40}[role])
   c.execute(text('DELETE FROM group_requirements WHERE knowledge_id=:k'),dict(k=kid))
   for mid in mats+[gid]:
    if mid!=kid:c.execute(text('INSERT OR IGNORE INTO group_requirements VALUES(:k,:m)'),dict(k=kid,m=mid))
  for v in g.get('variants',[]):
   kid=gid+'-lesson-transfer-'+hashlib.sha256(v['en'].strip().casefold().rstrip('.!?').encode()).hexdigest()[:12]
   variant_links.append((gid,kid,v.get('requires',[])))
  # Exact, explicitly authored equivalent forms reuse latest evidence, never copy grades.
  for kid in lesson_ids:
   if not spec.get('automatic_aliases',True):continue
   for (alias,) in c.execute(text('SELECT b.id FROM knowledge a JOIN knowledge b ON lower(trim(a.answer))=lower(trim(b.answer)) WHERE a.id=:k AND a.id!=b.id'),dict(k=kid,family=gid+'-%')):
    c.execute(text('INSERT OR IGNORE INTO curriculum_aliases VALUES(:k,:a)'),dict(k=kid,a=alias))

 for gid,kid,deps in variant_links:
  resolved=[material_ids[d[9:].casefold()] if d.startswith('material:') else ids.get(d,d) for d in deps]
  for material in resolved:
   c.execute(text('INSERT OR IGNORE INTO group_requirements VALUES(:k,:m)'),dict(k=kid,m=material))
   c.execute(text('INSERT OR IGNORE INTO transfer_materials VALUES(:k,:m)'),dict(k=kid,m=material))
  if resolved:c.execute(text('INSERT OR IGNORE INTO sentence_combinations VALUES(:k,:g,:m,1)'),dict(k=kid,g=gid,m=resolved[0]))
 c.execute(text('DELETE FROM group_active_slots WHERE NOT EXISTS(SELECT 1 FROM learning_groups g JOIN group_primary p ON p.knowledge_id=g.root_id AND p.group_id=g.id WHERE g.id=group_active_slots.group_id)'))

def card(c,kid,en,zh,usage,example,example_zh,kind,replace=True):
 c.execute(text('INSERT OR IGNORE INTO knowledge VALUES(:k,:z,:a,:e,:x)'),dict(k=kid,z=zh,a=en,e=usage,x=example))
 c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES(:k)'),dict(k=kid))
 if replace:c.execute(text('UPDATE knowledge SET prompt=:z,explanation=:e,example=:x WHERE id=:k'),dict(k=kid,z=zh,e=usage,x=example))
 raw=c.execute(text('SELECT payload FROM knowledge_details WHERE knowledge_id=:k'),dict(k=kid)).scalar();d=json.loads(raw) if raw else {}
 if replace or not raw:
  d.update(entry_type=d.get('entry_type',kind),usage=usage,structure=d.get('structure') or '',examples=[dict(en=example,zh=example_zh)],speech_text=en,knowledge_points=[],review_status='自编教学内容；已校验课程依赖与结构，非官方教材')
  pronunciation_metadata.enrich(d,en)
  c.execute(text('INSERT INTO knowledge_details VALUES(:k,:p,100,:t) ON CONFLICT(knowledge_id) DO UPDATE SET payload=excluded.payload,version=100,updated_at=excluded.updated_at'),dict(k=kid,p=json.dumps(d,ensure_ascii=False),t=datetime.now(timezone.utc).isoformat()))

def member(c,gid,kid,role,pos):
 c.execute(text('INSERT OR IGNORE INTO group_members VALUES(:g,:k,:r,:p)'),dict(g=gid,k=kid,r=role,p=pos))
 c.execute(text('INSERT OR REPLACE INTO curriculum_lessons VALUES(:g,:k,:r,:p,1)'),dict(g=gid,k=kid,r=role,p=pos))

@memoized
def known(c,kid):
 # Most recent direct result across an authored equivalent set wins, including forgetting.
 row=c.execute(text("SELECT p.level FROM progress p WHERE p.introduced=1 AND (p.knowledge_id=:k OR p.knowledge_id IN (SELECT alias_id FROM curriculum_aliases WHERE knowledge_id=:k)) ORDER BY julianday(p.last_at) DESC,p.knowledge_id=:k DESC LIMIT 1"),dict(k=kid)).first()
 return bool(row and row[0]>=3)

@memoized
def blocker_map(c):
 rows=c.execute(text("""WITH sources AS (
 SELECT knowledge_id AS target,knowledge_id AS source,level,last_at FROM progress WHERE introduced=1
 UNION ALL SELECT a.knowledge_id,p.knowledge_id,p.level,p.last_at FROM curriculum_aliases a JOIN progress p ON p.knowledge_id=a.alias_id WHERE p.introduced=1
 ), ranked AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY target ORDER BY julianday(last_at) DESC,target=source DESC) rn FROM sources)
 SELECT d.goal_id,d.prerequisite_id,k.answer FROM curriculum_prerequisites d JOIN learning_groups g ON g.id=d.prerequisite_id JOIN knowledge k ON k.id=g.root_id
 LEFT JOIN ranked p ON p.target=d.prerequisite_id AND p.rn=1 WHERE COALESCE(p.level,0)<3""")).all()
 result={}
 for gid,kid,en in rows:result.setdefault(gid,[]).append(dict(id=kid,english=en,reason='先掌握：'+en))
 return result

def blockers(c,gid):return blocker_map(c).get(gid,[])

def candidates(c,course='all',limit=1):
 rows=c.execute(text("""SELECT DISTINCT g.id,g.title,g.kind AS unit_type,t.difficulty,p.course_id,p.unit_position,p.position FROM curriculum_goals t
 JOIN learning_groups g ON g.id=t.id JOIN group_primary own ON own.knowledge_id=g.root_id AND own.group_id=g.id
 JOIN progress s ON s.knowledge_id=g.root_id JOIN curriculum_paths p ON p.goal_id=g.id
 WHERE t.status='ready' AND s.introduced=0
 AND NOT EXISTS(SELECT 1 FROM daily_group_tasks d WHERE d.group_id=g.id)
 ORDER BY p.course_id!='foundation',p.course_id,p.unit_position,t.difficulty,p.position,g.id"""),dict(c=course)).mappings().all()
 # Breadth practice must not force hundreds of phrases before the next structure.
 import os
 if os.environ.get('PELS_COURSE_EXPANSION')=='1':
  recent=c.execute(text("SELECT group_id FROM daily_group_tasks WHERE kind='new' ORDER BY rowid DESC LIMIT 4")).scalars().all()
  breadth_first=len(recent)==4 and all(g.startswith('mainline-') for g in recent)
  rows.sort(key=lambda r:(r['id'].startswith('mainline-') if breadth_first else not r['id'].startswith('mainline-')))
 result=[];seen=set()
 def add(gid):
  if gid in seen:return
  seen.add(gid)
  for b in blockers(c,gid):
   dep=next((r for r in rows if r['id']==b['id']),None)
   if dep:add(dep['id'])
  r=next((r for r in rows if r['id']==gid and r['course_id']==course),None) or next((r for r in rows if r['id']==gid),None)
  if r and not blockers(c,gid):result.append(dict(r))
 for r in rows:
  if course!='all' and r['course_id']!=course:continue
  add(r['id'])
  if len(result)>=limit:break
 return result[:limit]

def report(c,course='all'):
 rows=c.execute(text("""SELECT t.id,t.objective,t.difficulty,t.status,p.course_id,p.unit_id,p.unit_title,p.unit_goal,p.unit_position,p.position,k.answer,k.prompt,s.level,s.introduced
 FROM curriculum_goals t JOIN curriculum_paths p ON p.goal_id=t.id JOIN learning_groups g ON g.id=t.id JOIN knowledge k ON k.id=g.root_id JOIN progress s ON s.knowledge_id=k.id
 WHERE t.status='ready' AND (:c='all' OR p.course_id=:c) ORDER BY p.course_id!='foundation',p.course_id,p.unit_position,t.difficulty,p.position LIMIT 200"""),dict(c=course)).mappings().all()
 units={};seen=set();current=None
 for r in rows:
  if r['id'] in seen:continue
  seen.add(r['id']);u=units.setdefault(r['unit_id'],dict(id=r['unit_id'],title=r['unit_title'],goal=r['unit_goal'],items=[]))
  missing=blockers(c,r['id'])
  required=c.execute(text("SELECT knowledge_id FROM curriculum_lessons WHERE goal_id=:g AND (knowledge_id=:g OR role IN ('phrase','sentence')) AND required=1"),dict(g=r['id'])).scalars().all()
  passed=bool(required) and all(known(c,k) for k in required)
  introduced=r['introduced'] or c.execute(text('SELECT 1 FROM curriculum_aliases a JOIN progress p ON p.knowledge_id=a.alias_id WHERE a.knowledge_id=:k AND p.introduced=1 LIMIT 1'),dict(k=r['id'])).first() is not None
  state='recalled' if passed else 'blocked' if missing else 'learning' if introduced else 'ready'
  item=dict(id=r['id'],english=r['answer'],chinese=r['prompt'],objective=r['objective'],state=state,blockers=missing);u['items'].append(item)
  if not current and state in ('learning','ready'):current=u['id']
 for u in units.values():u['recalled']=sum(i['state']=='recalled' for i in u['items']);u['total']=len(u['items'])
 draft=c.execute(text("SELECT COUNT(DISTINCT g.id) FROM curriculum_goals g JOIN curriculum_paths p ON p.goal_id=g.id WHERE g.status='draft' AND (:c='all' OR p.course_id=:c)"),dict(c=course)).scalar()
 stats=c.execute(text("SELECT COUNT(DISTINCT t.id),COUNT(DISTINCT CASE WHEN s.introduced=0 THEN t.id END) FROM curriculum_goals t JOIN curriculum_paths p ON p.goal_id=t.id JOIN learning_groups g ON g.id=t.id JOIN progress s ON s.knowledge_id=g.root_id WHERE t.status='ready' AND (:c='all' OR p.course_id=:c)"),dict(c=course)).one()
 return dict(units=list(units.values()),current_unit=current,ready_total=stats[0],draft_total=draft,unintroduced=stats[1],truncated=stats[0]>len(seen),recalled=sum(u['recalled'] for u in units.values()),note='回忆通过不等于长期稳固；未编排资料仍可在词典查看或加入专项。')


def upgrades(c,stamp=None):
 raw=c.execute(text("SELECT value FROM app_settings WHERE key='active-course'")).scalar()
 course=json.loads(raw) if raw else 'all'
 rows=c.execute(text("""SELECT g.id,l.knowledge_id FROM curriculum_goals t JOIN learning_groups g ON g.id=t.id
 JOIN progress root ON root.knowledge_id=g.root_id JOIN curriculum_lessons l ON l.goal_id=g.id
 JOIN progress p ON p.knowledge_id=l.knowledge_id
 WHERE t.status='ready' AND root.introduced=1 AND root.level>=3 AND p.introduced=0 AND l.role IN ('phrase','sentence') AND (:course='all' OR EXISTS(SELECT 1 FROM curriculum_paths route WHERE route.goal_id=g.id AND route.course_id=:course))"""),dict(course=course)).all()
 result=list(dict.fromkeys(g for g,k in rows if not blockers(c,g) and not known(c,k)))
 if stamp is not None:
  import group_learning,transfer_evidence
  candidates=c.execute(text("""SELECT DISTINCT g.id FROM curriculum_goals t JOIN learning_groups g ON g.id=t.id
   JOIN progress p ON p.knowledge_id=g.root_id JOIN curriculum_lessons l ON l.goal_id=g.id
   WHERE t.status='ready' AND p.introduced=1 AND p.level>=3 AND l.role='transfer' AND (:course='all' OR EXISTS(SELECT 1 FROM curriculum_paths route WHERE route.goal_id=g.id AND route.course_id=:course))"""),dict(course=course)).scalars()
  for gid in candidates:
   if gid in result or blockers(c,gid):continue
   item,_=group_learning.step(c,gid,stamp)
   if item and item['role']=='transfer' and transfer_evidence.classify(c,item['id'],'transfer')[0]=='transfer':result.append(gid)
 return result


def chunk_covers(c,target,material):
 word=c.execute(text('SELECT answer FROM knowledge WHERE id=:k'),dict(k=material)).scalar()
 answer=c.execute(text('SELECT answer FROM knowledge WHERE id=:k'),dict(k=target)).scalar()
 if not word or not answer:return False
 rows=c.execute(text("SELECT k.id,k.answer FROM curriculum_lessons t JOIN curriculum_lessons l ON l.goal_id=t.goal_id JOIN knowledge k ON k.id=l.knowledge_id WHERE t.knowledge_id=:k AND l.role IN ('base','phrase')"),dict(k=target)).all()
 boundary=lambda small,big:bool(re.search(r'(?<![a-z])'+re.escape(small)+r'(?![a-z])',big,re.I))
 return any(known(c,k) and boundary(word,chunk) and boundary(chunk,answer) for k,chunk in rows)


def material_covered(c,gid,material):
 word=c.execute(text('SELECT answer FROM knowledge WHERE id=:k'),dict(k=material)).scalar()
 if not word:return False
 rows=c.execute(text("SELECT k.id,k.answer FROM curriculum_lessons l JOIN knowledge k ON k.id=l.knowledge_id WHERE l.goal_id=:g AND l.role IN ('base','phrase')"),dict(g=gid)).all()
 return any(known(c,k) and re.search(r'(?<![a-z])'+re.escape(word)+r'(?![a-z])',chunk,re.I) for k,chunk in rows)
