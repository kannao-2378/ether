"""Explicit learning families, daily group budgets and early registered transfer.

Individual answers/FSRS cards are never rewritten to manufacture mastery.
"""
from datetime import datetime,timedelta,timezone
import json,re
from sqlalchemy import text
ZONE=timezone(timedelta(hours=8));VERSION='families-v6'
TABLES=('focus_requests','learning_groups','group_members','group_primary','group_requirements','group_questions','daily_group_tasks','group_progress','group_usage','group_active_slots','group_install','group_migrations')
CORE={'want-to':['want'],'enjoy-doing':['enjoy'],'decide-to':['decide'],'like-doing':['like'],
      'listen-to':['listen','music'],'look-at':['look','picture'],'wait-for':['wait','bus'],
      'talk-to':['talk','friend'],'ask-for':['ask','help']}
def day_of(stamp):return stamp.astimezone(ZONE).date().isoformat()
def exists(c):return bool(c.execute(text("SELECT 1 FROM sqlite_master WHERE name='group_primary'")).first())
def install(c):
 for sql in [
  'CREATE TABLE IF NOT EXISTS learning_groups(id TEXT PRIMARY KEY,root_id TEXT NOT NULL,title TEXT NOT NULL,kind TEXT NOT NULL)',
  'CREATE TABLE IF NOT EXISTS group_members(group_id TEXT,knowledge_id TEXT,role TEXT,position INTEGER,PRIMARY KEY(group_id,knowledge_id))',
  'CREATE TABLE IF NOT EXISTS group_primary(knowledge_id TEXT PRIMARY KEY,group_id TEXT NOT NULL)',
  'CREATE TABLE IF NOT EXISTS group_requirements(knowledge_id TEXT,material_id TEXT,PRIMARY KEY(knowledge_id,material_id))',
  'CREATE TABLE IF NOT EXISTS group_questions(question_id TEXT PRIMARY KEY,group_id TEXT NOT NULL,role TEXT NOT NULL)',
  'CREATE TABLE IF NOT EXISTS daily_group_tasks(day TEXT,group_id TEXT,kind TEXT,first_item TEXT,PRIMARY KEY(day,group_id))',
  'CREATE TABLE IF NOT EXISTS group_progress(group_id TEXT PRIMARY KEY,due_at TEXT,last_at TEXT,transfer_pending INTEGER DEFAULT 0)',
  'CREATE TABLE IF NOT EXISTS group_usage(question_id TEXT,target_id TEXT,kind TEXT,PRIMARY KEY(question_id,target_id))',
  'CREATE TABLE IF NOT EXISTS group_active_slots(group_id TEXT PRIMARY KEY,entered_at TEXT NOT NULL)',
  'CREATE TABLE IF NOT EXISTS group_migrations(name TEXT PRIMARY KEY)',
  'CREATE TABLE IF NOT EXISTS group_install(id INTEGER PRIMARY KEY,version TEXT,knowledge_count INTEGER)',
  'CREATE INDEX IF NOT EXISTS group_members_item ON group_members(knowledge_id,group_id)',
  'CREATE INDEX IF NOT EXISTS group_primary_group ON group_primary(group_id,knowledge_id)',
  'CREATE INDEX IF NOT EXISTS group_questions_family ON group_questions(group_id,question_id)',
  'CREATE INDEX IF NOT EXISTS group_usage_target ON group_usage(target_id,question_id)']:
  c.execute(text(sql))
 # Minimal, reviewed starter sentence/variants, not arbitrary generated language.
 if c.execute(text("SELECT 1 FROM knowledge WHERE id='listen-to'")).first():
  for kid,prompt,answer,role,material in [
   ('group-listen-basic','我听音乐。','I listen to music.','sentence','music'),
   ('group-listen-radio','我听广播。','I listen to the radio.','transfer','the radio'),
   ('group-listen-friend','我听我的朋友说话。','I listen to my friend.','transfer','my friend'),
   ('group-listen-teacher','我听老师说话（使用 my teacher）。','I listen to my teacher.','transfer','my teacher')]:
   c.execute(text('INSERT OR IGNORE INTO knowledge VALUES(:k,:p,:a,:e,:a)'),dict(k=kid,p=prompt,a=answer,e='listen to 后面接听的对象；句子中先说谁，再说听什么。'))
   c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES(:k)'),dict(k=kid))
   payload=dict(entry_type='sentence',pos='句子',speech_text=answer,usage='先说 I（我），再说 listen to（听），最后说听的对象。',structure='I + listen to + 对象',examples=[dict(en=answer,zh=prompt)],common_errors=['listen 后接对象时不要漏掉 to。'],forms=[],roots=None,extensions=[])
   c.execute(text('INSERT OR IGNORE INTO knowledge_details VALUES(:k,:p,1,:t)'),dict(k=kid,p=json.dumps(payload,ensure_ascii=False),t=datetime.now(timezone.utc).isoformat()))

   c.execute(text("INSERT OR IGNORE INTO course_links VALUES(:k,'listen-to',:s,'已审核的组内句子与迁移题')"),dict(k=kid,s=3 if role=='sentence' else 4))
   for phrase in ('I',material):
    mid=c.execute(text('SELECT id FROM knowledge WHERE lower(answer)=lower(:a) ORDER BY rowid LIMIT 1'),dict(a=phrase)).scalar()
    if mid:c.execute(text('INSERT OR IGNORE INTO group_requirements VALUES(:k,:m)'),dict(k=kid,m=mid))
    if mid and phrase==material:c.execute(text("INSERT OR IGNORE INTO sentence_combinations VALUES(:k,'listen-to',:m,1)"),dict(k=kid,m=mid))
 count=c.execute(text('SELECT COUNT(*) FROM knowledge')).scalar()
 version=c.execute(text('SELECT version,knowledge_count FROM group_install WHERE id=1')).first()
 if not version or tuple(version)!=(VERSION,count):
  rows=[dict(r) for r in c.execute(text('SELECT k.*,COALESCE(d.payload,\'{}\') AS details FROM knowledge k LEFT JOIN knowledge_details d ON d.knowledge_id=k.id ORDER BY k.rowid')).mappings()]
  byid={r['id']:r for r in rows};byanswer={}
  for r in rows:byanswer.setdefault(r['answer'].strip().casefold(),r['id'])
  links={r[0]:(r[1],r[2]) for r in c.execute(text('SELECT knowledge_id,parent_id,stage FROM course_links'))}
  def root(k):
   seen=set()
   while k in links and links[k][0] in byid and k not in seen:
    seen.add(k);k=links[k][0]
   return k
  primary={k:root(k) for k in byid}
  for action in ('drink-water','read-books','learn-english'):
   form=action+'-ing-form'
   if form in byid and action in byid:primary[form]=primary[action]
  for base,words in CORE.items():
   if base in byid:
    for word in words:
     atom=byanswer.get(word)
     if atom and root(atom)==atom:primary[atom]=base
  groups=[];members=[]
  for r in rows:
   k=r['id'];base=primary[k];d=json.loads(byid[base]['details']);kind='word' if d.get('entry_type')=='word' or re.fullmatch(r'[A-Za-z]+',byid[base]['answer']) else 'expression'
   if k==base:groups.append(dict(g=base,k=base,t=byid[base]['answer'],kind=kind))
   stage=2 if k.endswith('-ing-form') else links.get(k,(None,1))[1]
   role='word' if re.fullmatch(r'[A-Za-z]+',r['answer']) and (k!=base or kind=='word') else {2:'phrase',3:'sentence',4:'transfer'}.get(stage,'base')
   members.append(dict(g=base,k=k,r=role,p={'word':0,'base':10,'phrase':20,'sentence':30,'transfer':40}[role]))
  c.execute(text('INSERT OR IGNORE INTO learning_groups VALUES(:g,:k,:t,:kind)'),groups)
  c.execute(text('INSERT OR IGNORE INTO group_primary VALUES(:k,:g)'),[dict(k=k,g=g) for k,g in primary.items()])
  c.execute(text('INSERT OR IGNORE INTO group_members VALUES(:g,:k,:r,:p)'),members)
  # Explicit phrase members provide a finite teaching set; never expand transfer words.
  for m in members:
   if m['r']!='phrase':continue
   for token in re.findall(r'[A-Za-z]+',byid[m['k']]['answer']):
    atom=byanswer.get(token.casefold())
    if atom and token.casefold() not in ('to','at','for','the','my','this','a','an'):
     c.execute(text("INSERT OR IGNORE INTO group_members VALUES(:g,:k,'word',0)"),dict(g=m['g'],k=atom))
  # Register the first sentence's lexical prerequisites as a finite core set.
  first={}
  for m in members:
   if m['r']=='sentence':first.setdefault(m['g'],m['k'])
  for gid,kid in first.items():
   if gid in CORE:continue
   for (atom,) in c.execute(text('SELECT material_id FROM transfer_materials WHERE knowledge_id=:k'),dict(k=kid)):
    if atom in byid and re.fullmatch(r'[A-Za-z]+',byid[atom]['answer']):
     c.execute(text("INSERT OR IGNORE INTO group_members VALUES(:g,:k,'word',0)"),dict(g=gid,k=atom))
  atom_i=byanswer.get('i')
  if atom_i:
   for m in members:
    if m['r']=='sentence' and re.search(r'\bI\b',byid[m['k']]['answer']):
     c.execute(text("INSERT OR IGNORE INTO group_members VALUES(:g,:k,'sentence_word',25)"),dict(g=m['g'],k=atom_i))
  # Starter sentences must also respect registered unknown words/chunks.
  for m in members:
   if m['r'] not in ('sentence','transfer'):continue
   for (atom,) in c.execute(text('SELECT material_id FROM transfer_materials WHERE knowledge_id=:k'),dict(k=m['k'])):
    c.execute(text('INSERT OR IGNORE INTO group_requirements VALUES(:k,:m)'),dict(k=m['k'],m=atom))
   if m['g'] in CORE:
    covered_tokens=set()
    for phrase in ('every day','this picture','the bus','my friend','my teacher','the radio'):
     atom=byanswer.get(phrase)
     if atom and re.search(r'\b'+re.escape(phrase)+r'\b',byid[m['k']]['answer'],re.I) and primary[atom]!=m['g']:
      covered_tokens.update(phrase.split())
      c.execute(text('INSERT OR IGNORE INTO group_requirements VALUES(:k,:m)'),dict(k=m['k'],m=atom))
    for token in re.findall(r'[A-Za-z]+',byid[m['k']]['answer']):
     atom=byanswer.get(token.casefold())
     if atom and token.casefold() not in covered_tokens and primary[atom]!=m['g']:
      c.execute(text('INSERT OR IGNORE INTO group_requirements VALUES(:k,:m)'),dict(k=m['k'],m=atom))
  # Register exact component use for transfer assessment only; this does not
  # grant independent success, change a component card, or merge whole groups.
  for m in members:
   if m['r'] not in ('sentence','transfer'):continue
   tokens=set(re.findall(r'[a-z]+',byid[m['k']]['answer'].casefold()))
   for r in c.execute(text("SELECT k.id,k.answer FROM group_members g JOIN knowledge k ON k.id=g.knowledge_id WHERE g.group_id=:g AND g.role='word'"),dict(g=m['g'])).mappings():
    if r['answer'].casefold() in tokens:
     c.execute(text('INSERT OR IGNORE INTO transfer_materials VALUES(:k,:m)'),dict(k=m['k'],m=r['id']))
  c.execute(text('INSERT OR REPLACE INTO group_install VALUES(1,:v,:n)'),dict(v=VERSION,n=count))
 # Preserve unfinished questions and their original item identities.
 c.execute(text('''INSERT OR IGNORE INTO group_questions
  SELECT q.id,p.group_id,m.role FROM questions q JOIN group_primary p ON p.knowledge_id=q.knowledge_id
  JOIN group_members m ON m.group_id=p.group_id AND m.knowledge_id=q.knowledge_id'''))
 # Additive one-time migration: raw tasks remain an audit ledger, not live quota.
 if not c.execute(text("SELECT 1 FROM group_migrations WHERE name='legacy-tasks-v1'")).first():
  c.execute(text("""INSERT OR IGNORE INTO daily_group_tasks
  SELECT dt.day,p.group_id,CASE WHEN MAX(dt.kind='new') THEN 'new' ELSE 'review' END,MIN(dt.knowledge_id)
  FROM daily_tasks dt JOIN group_primary p ON p.knowledge_id=dt.knowledge_id
  GROUP BY dt.day,p.group_id"""))
  c.execute(text("INSERT INTO group_migrations VALUES('legacy-tasks-v1')"))

def family(c,kid):
 return c.execute(text('SELECT group_id FROM group_primary WHERE knowledge_id=:k'),dict(k=kid)).scalar() or kid

def counts(c,stamp):
 return dict(c.execute(text('SELECT kind,COUNT(*) FROM daily_group_tasks WHERE day=:d GROUP BY kind'),dict(d=day_of(stamp))).all())

def breakdown(c,stamp):
 rows=c.execute(text("""SELECT g.kind,COUNT(*) FROM daily_group_tasks t JOIN learning_groups g ON g.id=t.group_id
 WHERE t.day=:d AND t.kind='new' GROUP BY g.kind"""),dict(d=day_of(stamp))).all()
 return dict(rows)

def admit(c,gid,kid,stamp,new_limit,review_limit):
 day=day_of(stamp)
 existing=c.execute(text('SELECT kind FROM daily_group_tasks WHERE day=:d AND group_id=:g'),dict(d=day,g=gid)).scalar()
 if existing:return acquire(c,gid,stamp)
 root=c.execute(text('SELECT root_id FROM learning_groups WHERE id=:g'),dict(g=gid)).scalar()
 introduced=c.execute(text('SELECT introduced FROM progress WHERE knowledge_id=:k'),dict(k=root)).scalar()
 seen_before=c.execute(text('SELECT 1 FROM daily_group_tasks WHERE group_id=:g AND day<:d LIMIT 1'),dict(g=gid,d=day)).first()
 kind='review' if introduced or seen_before else 'new'
 if counts(c,stamp).get(kind,0)>=(new_limit if kind=='new' else review_limit):return False
 if not acquire(c,gid,stamp):return False
 c.execute(text('INSERT INTO daily_group_tasks VALUES(:d,:g,:v,:k)'),dict(d=day,g=gid,v=kind,k=kid))
 return True

def events(c,gid,day):
 return [dict(r) for r in c.execute(text("""SELECT a.*,a.rowid AS seq,COALESCE(q.role,m.role,'base') AS role,
 COALESCE((SELECT confidence FROM feedback_events f WHERE f.question_id=a.question_id ORDER BY f.rowid DESC LIMIT 1),a.confidence) AS rating,
 EXISTS(SELECT 1 FROM spelling_checks s WHERE s.question_id=a.question_id AND s.correct=0 AND julianday(s.created_at)<=julianday(a.created_at)) AS failed
 FROM group_questions q JOIN answers a ON a.question_id=q.question_id
 LEFT JOIN group_members m ON m.knowledge_id=a.knowledge_id AND m.group_id=q.group_id
 WHERE q.group_id=:g AND date(a.created_at,'+8 hours')=:d
 AND NOT EXISTS(SELECT 1 FROM test_skips ts WHERE ts.question_id=a.question_id) ORDER BY a.rowid"""),dict(g=gid,d=day)).mappings()]

def independent(e):return bool(e['correct'] and not e['revealed'] and not e['failed'] and e['rating']=='clear')

def members(c,gid):
 return [dict(r) for r in c.execute(text('SELECT k.*,p.*,m.role,m.position FROM group_members m JOIN knowledge k ON k.id=m.knowledge_id JOIN progress p ON p.knowledge_id=k.id WHERE m.group_id=:g ORDER BY m.position,k.rowid'),dict(g=gid)).mappings()]

def supported(c,kid,stamp):
 return bool(c.execute(text("SELECT 1 FROM group_usage u JOIN answers a ON a.question_id=u.question_id WHERE u.target_id=:k AND date(a.created_at,'+8 hours')=:d LIMIT 1"),dict(k=kid,d=day_of(stamp))).first())

def requirements_met(c,kid):
 return not c.execute(text('''SELECT 1 FROM group_requirements r JOIN progress p ON p.knowledge_id=r.material_id
 WHERE r.knowledge_id=:k AND p.level<3 LIMIT 1'''),dict(k=kid)).first()

def step(c,gid,stamp,history=None):
 """One active step per group; no stable gate for early transfer."""
 if gid.startswith('focus-'):
  import focus_training
  return focus_training.step(c,gid,stamp)
 rows=members(c,gid);history=events(c,gid,day_of(stamp)) if history is None else history
 kind=c.execute(text('SELECT kind FROM daily_group_tasks WHERE day=:d AND group_id=:g'),dict(d=day_of(stamp),g=gid)).scalar()
 if kind is None:
  introduced=c.execute(text('SELECT p.introduced FROM learning_groups g JOIN progress p ON p.knowledge_id=g.root_id WHERE g.id=:g'),dict(g=gid)).scalar()
  seen_before=c.execute(text('SELECT 1 FROM daily_group_tasks WHERE group_id=:g AND day<:d LIMIT 1'),dict(g=gid,d=day_of(stamp))).first()
  kind='review' if introduced or seen_before else 'new'
 if kind=='review' and not history:
  due=[r for r in rows if r['introduced'] and (not r['due_at'] or datetime.fromisoformat(r['due_at'])<=stamp) and (r['role'] not in ('sentence','transfer') or requirements_met(c,r['id']))]
  if due:return sorted(due,key=lambda r:(r['level']>=3,r['attempts'],r['role'] not in ('base','phrase'),r['last_at'] or ''))[0],False

 if not rows:return None,False
 streak=0
 for e in history:streak=streak+1 if independent(e) else 0
 successful={e['knowledge_id'] for e in history if independent(e)}
 def known(r):return r['level']>=3 or r['id'] in successful or supported(c,r['id'],stamp)
 # A concrete failure takes priority over advancing to another component.
 if history and not independent(history[-1]):
  repair=next((r for r in rows if r['id']==history[-1]['knowledge_id']),rows[0])
  if repair['role'] not in ('sentence','transfer') or requirements_met(c,repair['id']):return repair,False
 roots=[r for r in rows if r['role']=='base']
 bases=roots or [r for r in rows if r['id']==gid]
 for r in rows:
  if r['role']=='word' and not known(r):return r,False
 for r in bases:
  if not known(r):return r,False
 phrases=[r for r in rows if r['role']=='phrase' and requirements_met(c,r['id'])]
 for r in phrases:
  if not known(r):return r,False
 for word in [r for r in rows if r['role']=='sentence_word' and not known(r)]:
  ready=c.execute(text('''SELECT 1 FROM group_members m WHERE m.group_id=:g AND m.role='sentence'
   AND NOT EXISTS(SELECT 1 FROM group_requirements r JOIN progress p ON p.knowledge_id=r.material_id
    WHERE r.knowledge_id=m.knowledge_id AND r.material_id!=:w AND p.level<3) LIMIT 1'''),dict(g=gid,w=word['id'])).first()
  if ready:return word,False
 sentences=[r for r in rows if r['role']=='sentence' and requirements_met(c,r['id'])]
 for r in sentences[:1]:
  if not known(r):return r,False
 variants=sorted([r for r in rows if r['role']=='transfer' and requirements_met(c,r['id'])],key=lambda r:(r['attempts'],r['last_at'] or ''))
 # Different registered source materials, not repeat spellings of one question.
 def material(r):return c.execute(text('SELECT material_id FROM sentence_combinations WHERE knowledge_id=:k'),dict(k=r['id'])).scalar() or r['id']
 unique=[];seen=set()
 for r in variants:
  tag=material(r)
  if tag not in seen:unique.append(r);seen.add(tag)
 passed={material(r) for r in rows if r['role']=='transfer' and r['id'] in successful}
 if sentences or not any(r['role']=='sentence' for r in rows):
  if len(passed)<min(2,len(unique)):
   for r in unique:
    if material(r) not in passed:return r,len(unique)<2
 kind=c.execute(text('SELECT kind FROM daily_group_tasks WHERE day=:d AND group_id=:g'),dict(d=day_of(stamp),g=gid)).scalar()
 needed=3 if kind=='new' else 1
 # Three interleaved successes across the group, never three per component.
 if streak<needed:
  candidates=sentences[:1] or phrases or bases or rows[:1]
  # Revisit an independently unverified due component on later days.
  if kind=='review':
   due=[r for r in rows if r['introduced'] and (not r['due_at'] or datetime.fromisoformat(r['due_at'])<=stamp) and (r['role'] not in ('sentence','transfer') or requirements_met(c,r['id']))]
   if due:candidates=sorted(due,key=lambda r:(r['level']>=3,r['attempts']))
  return candidates[0],len(unique)<2
 return None,len(unique)<2

def active_groups(c,stamp):
 today=day_of(stamp)
 return c.execute(text("""SELECT DISTINCT p.group_id FROM progress s JOIN group_primary p ON p.knowledge_id=s.knowledge_id
 LEFT JOIN group_progress gp ON gp.group_id=p.group_id
 WHERE p.group_id NOT LIKE 'focus-%' AND s.introduced=1 AND (gp.due_at IS NULL OR julianday(gp.due_at)<=julianday(:t))
 AND (s.due_at IS NULL OR julianday(s.due_at)<=julianday(:t))
 UNION SELECT d.group_id FROM daily_group_tasks d LEFT JOIN group_progress gp ON gp.group_id=d.group_id
 WHERE d.group_id NOT LIKE 'focus-%' AND d.day<:day AND (gp.due_at IS NULL OR julianday(gp.due_at)<=julianday(:t))
 ORDER BY 1"""),dict(t=stamp.isoformat(),day=today)).scalars().all()

def pool_count(c,stamp):
 c.execute(text("""DELETE FROM group_active_slots WHERE group_id IN (SELECT group_id FROM group_progress WHERE due_at IS NOT NULL AND julianday(due_at)>julianday(:t))"""),dict(t=stamp.isoformat()))
 return c.execute(text('SELECT COUNT(*) FROM group_active_slots')).scalar()

def acquire(c,gid,stamp):
 if c.execute(text('SELECT 1 FROM group_active_slots WHERE group_id=:g'),dict(g=gid)).first():return True
 if pool_count(c,stamp)>=12:return False
 c.execute(text('INSERT OR IGNORE INTO group_active_slots VALUES(:g,:t)'),dict(g=gid,t=stamp.isoformat()))
 return True

def refresh(c,kid,stamp,question_id=None):
 gid=c.execute(text('SELECT group_id FROM group_questions WHERE question_id=COALESCE(:q,(SELECT question_id FROM answers WHERE knowledge_id=:k ORDER BY rowid DESC LIMIT 1))'),dict(q=question_id,k=kid)).scalar() or family(c,kid)
 if gid.startswith('focus-'):
  import focus_training
  focus_training.refresh(c,gid,stamp);return
 # Usage evidence is derived from qualified source answers; never updates target FSRS.
 c.execute(text('DELETE FROM group_usage WHERE question_id IN (SELECT a.question_id FROM answers a JOIN group_questions q ON q.question_id=a.question_id WHERE a.knowledge_id=:k AND q.group_id=:g)'),dict(k=kid,g=gid))
 for e in events(c,gid,day_of(stamp)):
  if e['knowledge_id']!=kid or not independent(e):continue
  tokens=set(re.findall(r'[a-z]+',e['raw_answer'].casefold()))
  for r in members(c,gid):
   if r['id']==kid:continue
   if (r['role']=='word' and r['answer'].casefold() in tokens) or (r['role'] in ('base','phrase') and e['role'] in ('phrase','sentence','transfer')):
    c.execute(text("INSERT OR IGNORE INTO group_usage VALUES(:q,:k,'contextual_use')"),dict(q=e['question_id'],k=r['id']))
 chosen,pending=step(c,gid,stamp)
 due=None
 if chosen is None:
  # The weakest introduced component determines the next group visit.
  # Contextual use cannot postpone an unverified word indefinitely.
  dates=[]
  for member in members(c,gid):
   if not member['introduced']:continue
   own=datetime.fromisoformat(member['due_at']) if member['due_at'] else None
   dates.append(own if own and own>stamp else stamp+timedelta(days=1))
  due=min(dates or [stamp+timedelta(days=1)]).isoformat()
 c.execute(text('INSERT INTO group_progress VALUES(:g,:d,:t,:p) ON CONFLICT(group_id) DO UPDATE SET due_at=excluded.due_at,last_at=excluded.last_at,transfer_pending=excluded.transfer_pending'),dict(g=gid,d=due,t=stamp.isoformat(),p=int(pending)))

def select(c,stamp,new_limit,review_limit,course='all'):
 import focus_training
 special=focus_training.select(c,stamp)
 if special:return special
 day=day_of(stamp);seq=c.execute(text('SELECT COALESCE(MAX(rowid),0)+1 FROM answers')).scalar()
 # A persisted unfinished question always resumes before introducing anything else.
 pending_rows=c.execute(text('''SELECT k.*,q.id AS question_id,COALESCE(g.group_id,p.group_id) AS group_id,COALESCE(g.role,m.role,'base') AS role
 FROM questions q JOIN knowledge k ON k.id=q.knowledge_id LEFT JOIN group_questions g ON g.question_id=q.id
 JOIN group_primary p ON p.knowledge_id=k.id LEFT JOIN group_members m ON m.knowledge_id=k.id AND m.group_id=p.group_id
 LEFT JOIN answers a ON a.question_id=q.id WHERE a.id IS NULL ORDER BY q.rowid''')).mappings().all()
 for pending in pending_rows:
  if pending['group_id'].startswith('focus-'):continue
  if pending['role'] in ('sentence','transfer'):
   if not requirements_met(c,pending['id']):continue
   roots=c.execute(text("SELECT p.level,k.id FROM group_members m JOIN progress p ON p.knowledge_id=m.knowledge_id JOIN knowledge k ON k.id=m.knowledge_id WHERE m.group_id=:g AND m.role='base'"),dict(g=pending['group_id'])).all()
   if any(level<3 and not supported(c,kid,stamp) for level,kid in roots):continue
  if not admit(c,pending['group_id'],pending['id'],stamp,new_limit,review_limit):continue
  pending=dict(pending);pending['group_title']=c.execute(text('SELECT title FROM learning_groups WHERE id=:g'),dict(g=pending['group_id'])).scalar()
  c.execute(text('INSERT OR IGNORE INTO group_questions VALUES(:q,:g,:r)'),dict(q=pending['question_id'],g=pending['group_id'],r=pending['role']))
  kind=c.execute(text('SELECT kind FROM daily_group_tasks WHERE day=:d AND group_id=:g'),dict(d=day,g=pending['group_id'])).scalar()
  c.execute(text('INSERT OR IGNORE INTO daily_tasks VALUES(:d,:k,:v)'),dict(d=day,k=pending['id'],v=kind))
  return 'recall',dict(pending)
 # Revisit today's deferred transfer when newly learned materials become available.
 deferred=c.execute(text("SELECT group_id FROM group_progress WHERE transfer_pending=1 AND date(last_at,'+8 hours')=:d AND julianday(due_at)>julianday(:t)"),dict(d=day,t=stamp.isoformat())).scalars().all()
 for gid in deferred:
  resumed,_=step(c,gid,stamp)
  if resumed and acquire(c,gid,stamp):c.execute(text('UPDATE group_progress SET due_at=NULL WHERE group_id=:g'),dict(g=gid))
 current=c.execute(text("""SELECT t.group_id FROM daily_group_tasks t LEFT JOIN group_progress p ON p.group_id=t.group_id
 WHERE t.day=:d AND t.group_id NOT LIKE 'focus-%' AND (p.due_at IS NULL OR julianday(p.due_at)<=julianday(:t)) ORDER BY t.rowid"""),dict(d=day,t=stamp.isoformat())).scalars().all()
 candidates=[]
 for gid in current[:12]:
  hist=events(c,gid,day)
  item,_=step(c,gid,stamp,history=hist)
  if item:
   gap=(2 if hist[-1]['rating']=='forgot' else 4 if not independent(hist[-1]) else 8) if hist else 0
   due=hist[-1]['seq']+gap+1 if hist else 0
   candidates.append((due,gid,item))
 ready=[r for r in candidates if r[0]<=seq]
 def result(gid,item):
  item=dict(item);item['group_id']=gid
  if item['role'] in ('sentence','transfer') and not requirements_met(c,item['id']):return None
  if not admit(c,gid,item['id'],stamp,new_limit,review_limit):return None
  if item['role'] in ('word','sentence_word') and not item['introduced']:
   # Freeze first teaching ownership; shared later uses don't create new quotas.
   current=family(c,item['id'])
   owner_kind=c.execute(text('SELECT kind FROM learning_groups WHERE id=:g'),dict(g=current)).scalar()
   if owner_kind=='word':c.execute(text('UPDATE group_primary SET group_id=:g WHERE knowledge_id=:k'),dict(g=gid,k=item['id']))

  item['group_title']=c.execute(text('SELECT title FROM learning_groups WHERE id=:g'),dict(g=gid)).scalar()
  kind=c.execute(text('SELECT kind FROM daily_group_tasks WHERE day=:d AND group_id=:g'),dict(d=day,g=gid)).scalar()
  c.execute(text('INSERT OR IGNORE INTO daily_tasks VALUES(:d,:k,:v)'),dict(d=day,k=item['id'],v=kind))
  return ('recall' if item['introduced'] else 'learn'),item
 for _,gid,item in sorted(ready,key=lambda r:r[0]):
  choice=result(gid,item)
  if choice:return choice
 # Due groups already learned on previous days get priority over new groups.
 for gid in active_groups(c,stamp):
  if gid in current:continue
  item,_=step(c,gid,stamp)
  if item and admit(c,gid,item['id'],stamp,new_limit,review_limit):return result(gid,item)
 if len(candidates)<12 and pool_count(c,stamp)<12 and counts(c,stamp).get('new',0)<new_limit:
  course_filter='' if course=='all' else "AND EXISTS(SELECT 1 FROM group_members m JOIN course_items i ON i.knowledge_id=m.knowledge_id JOIN course_units u ON u.id=i.unit_id WHERE m.group_id=g.id AND u.course_id=:course)"
  unseen=c.execute(text('''SELECT g.id FROM learning_groups g JOIN progress p ON p.knowledge_id=g.root_id
   JOIN group_primary primary_group ON primary_group.knowledge_id=g.root_id AND primary_group.group_id=g.id
   WHERE p.introduced=0 AND NOT EXISTS(SELECT 1 FROM daily_group_tasks t WHERE t.group_id=g.id) '''+course_filter+'''
   ORDER BY CASE WHEN g.kind='expression' THEN 0 ELSE 1 END,
   COALESCE((SELECT MIN(i.position) FROM group_members m JOIN course_items i ON i.knowledge_id=m.knowledge_id WHERE m.group_id=g.id),999999),g.rowid LIMIT 1'''),dict(d=day,course=course)).scalar()
  if unseen:
   item,_=step(c,unseen,stamp)
   if item:
    choice=result(unseen,item)
    if choice:return choice
 # With too few groups, shorten the gap rather than inventing or pulling future reviews.
 for _,gid,item in sorted(candidates,key=lambda r:r[0]):
  choice=result(gid,item)
  if choice:return choice
 return 'done',None


def due_counts(c,stamp):
    active=active_groups(c,stamp)
    cross=0
    for gid in active:
        due=c.execute(text('SELECT due_at FROM group_progress WHERE group_id=:g'),dict(g=gid)).scalar()
        if due is None:
            due=c.execute(text('SELECT MIN(p.due_at) FROM group_primary g JOIN progress p ON p.knowledge_id=g.knowledge_id WHERE g.group_id=:g AND p.introduced=1'),dict(g=gid)).scalar()
        if due and datetime.fromisoformat(due)<=stamp:cross+=1
    return dict(cross_day=cross,practice=len(active)-cross)
