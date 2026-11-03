"""Opt-in sourced-sentence pilot with bounded, budgeted material preparation."""
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
from sqlalchemy import text
import curriculum_engine as ce,transfer_evidence as evidence
RESOURCE=Path(__file__).parent/'resources/sourced_transfer_pilot.json'
PACK=Path(__file__).parent/'resources/compiled_courses.json'
FLAG='sourced-transfer-pilot'
TABLES=('source_sentence_bank','source_sentence_targets','source_preparation_items')
ZONE=timezone(timedelta(hours=8))
GAP=3

def install(c):
 c.execute(text('CREATE TABLE IF NOT EXISTS source_sentence_bank(id TEXT PRIMARY KEY,english TEXT,chinese TEXT,provenance TEXT,review TEXT)'))
 c.execute(text('CREATE TABLE IF NOT EXISTS source_sentence_targets(knowledge_id TEXT PRIMARY KEY,bank_id TEXT,goal_id TEXT,material_id TEXT)'))
 c.execute(text('CREATE TABLE IF NOT EXISTS source_preparation_items(knowledge_id TEXT PRIMARY KEY)'))
 # Preserve generated lesson ownership after a curriculum revision.
 c.execute(text("INSERT OR IGNORE INTO curriculum_lessons SELECT goal_id,knowledge_id,'transfer',50,1 FROM source_sentence_targets"))

def enabled(c,gid=None):
 value=c.execute(text('SELECT value FROM app_settings WHERE key=:k'),dict(k=FLAG)).scalar()
 return value=='1' and (gid is None or bool(c.execute(text('SELECT 1 FROM source_sentence_targets WHERE goal_id=:g'),dict(g=gid)).first()))

def activate(c):
 originals={r['id']:r for r in json.loads(PACK.read_text(encoding='utf-8'))['sentences']}
 rows=json.loads(RESOURCE.read_text(encoding='utf-8'))['rows']
 for row in rows:
  original=originals.get(row['source_id'])
  if not original or original['answer']!=row['english'] or row['source'] not in original['details']['examples'] or row['review']['status']!='approved':raise ValueError('Source verification failed')
  if row['english']!='I want to '+row['material']['english']+'.':raise ValueError('Unreviewed construction')
 for row in rows:
  bank='source-'+hashlib.sha256(evidence.key(row['english']).encode()).hexdigest()[:20]
  material=row['material'];mid='source-material-'+hashlib.sha256(evidence.key(material['english']).encode()).hexdigest()[:20]
  kid=bank+'-'+row['goal'];gid=row['goal']
  c.execute(text('INSERT OR IGNORE INTO source_sentence_bank VALUES(:i,:e,:z,:p,:r)'),dict(i=bank,e=row['english'],z=row['chinese'],p=json.dumps(row['source'],ensure_ascii=False),r=json.dumps(row['review'],ensure_ascii=False)))
  ce.card(c,mid,material['english'],material['chinese'],material['usage'],material['english'],material['chinese'],'phrase')
  # Only the material itself is shown while preparing, never the future full answer.
  c.execute(text('INSERT OR IGNORE INTO learning_groups VALUES(:g,:g,:t,\'word\')'),dict(g=mid,t=material['english']))
  c.execute(text('INSERT OR IGNORE INTO group_primary VALUES(:k,:k)'),dict(k=mid));ce.member(c,mid,mid,'base',0)
  c.execute(text('INSERT OR IGNORE INTO source_preparation_items VALUES(:k)'),dict(k=mid))
  for alias in c.execute(text('SELECT id FROM knowledge WHERE lower(answer)=:a AND id!=:k'),dict(a=material['english'].lower(),k=mid)).scalars():
   c.execute(text('INSERT OR IGNORE INTO curriculum_aliases VALUES(:k,:a)'),dict(k=mid,a=alias))
  ce.card(c,kid,row['english'],row['chinese'],'把已学的 want to 和动作表达用于新情境。',row['english'],row['chinese'],'sentence')
  detail=json.loads(c.execute(text('SELECT payload FROM knowledge_details WHERE knowledge_id=:k'),dict(k=kid)).scalar());detail.update(examples=[dict(en=row['english'],zh=row['chinese'],**{k:v for k,v in row['source'].items() if k not in ('en','zh')})],sources=[dict(title='Tatoeba 原句',url=row['source']['source_url'])],review_status=row['review']['method'])
  c.execute(text('UPDATE knowledge_details SET payload=:p WHERE knowledge_id=:k'),dict(k=kid,p=json.dumps(detail,ensure_ascii=False)))
  ce.member(c,gid,kid,'transfer',50);c.execute(text('INSERT OR IGNORE INTO group_primary VALUES(:k,:g)'),dict(k=kid,g=gid))
  c.execute(text('INSERT OR IGNORE INTO source_sentence_targets VALUES(:k,:b,:g,:m)'),dict(k=kid,b=bank,g=gid,m=mid))
  c.execute(text("INSERT OR IGNORE INTO course_links VALUES(:k,:g,4,'有来源的迁移试点')"),dict(k=kid,g=gid))
  for dep in [gid,mid]+c.execute(text("SELECT knowledge_id FROM curriculum_lessons WHERE goal_id=:g AND role IN ('phrase','sentence')"),dict(g=gid)).scalars().all():
   c.execute(text('INSERT OR IGNORE INTO group_requirements VALUES(:k,:m)'),dict(k=kid,m=dep))
  c.execute(text('INSERT OR IGNORE INTO transfer_materials VALUES(:k,:m)'),dict(k=kid,m=mid))
  c.execute(text('INSERT OR IGNORE INTO sentence_combinations VALUES(:k,:g,:m,1)'),dict(k=kid,g=gid,m=mid))
 c.execute(text('INSERT INTO app_settings VALUES(:k,\'1\') ON CONFLICT(key) DO UPDATE SET value=excluded.value'),dict(k=FLAG))

def targets(c,gid):return c.execute(text('SELECT * FROM source_sentence_targets WHERE goal_id=:g ORDER BY rowid'),dict(g=gid)).mappings().all()
def basics_ready(c,gid):
 basics=c.execute(text("SELECT knowledge_id FROM curriculum_lessons WHERE goal_id=:g AND role IN ('phrase','sentence')"),dict(g=gid)).scalars().all()
 return ce.known(c,gid) and not ce.blockers(c,gid) and bool(basics) and all(ce.known(c,k) for k in basics)

def spacing(c,mid,stamp):
 row=c.execute(text('''SELECT a.rowid,a.created_at FROM answers a WHERE (a.knowledge_id=:m OR a.knowledge_id IN (SELECT alias_id FROM curriculum_aliases WHERE knowledge_id=:m)) ORDER BY a.rowid DESC LIMIT 1'''),dict(m=mid)).first()
 if not row or datetime.fromisoformat(row[1]).astimezone(ZONE).date()!=stamp.astimezone(ZONE).date():return 0
 completed=c.execute(text('''SELECT count(*) FROM answers a WHERE a.rowid>:s AND a.knowledge_id!=:m AND a.knowledge_id NOT IN (SELECT alias_id FROM curriculum_aliases WHERE knowledge_id=:m) AND a.correct=1 AND NOT EXISTS(SELECT 1 FROM test_skips x WHERE x.question_id=a.question_id)'''),dict(s=row[0],m=mid)).scalar()
 return max(0,GAP-completed)

def allowed(c,kid,stamp):
 row=c.execute(text('SELECT goal_id,material_id FROM source_sentence_targets WHERE knowledge_id=:k'),dict(k=kid)).first()
 if not row:return not c.execute(text('SELECT 1 FROM source_preparation_items WHERE knowledge_id=:k'),dict(k=kid)).first() or enabled(c)
 return enabled(c,row[0]) and ce.known(c,row[1]) and not spacing(c,row[1],stamp)

def filter_variants(c,gid,rows,stamp):
 if enabled(c,gid):
  ids={r['knowledge_id'] for r in targets(c,gid)}
  return [r for r in rows if r['id'] in ids and allowed(c,r['id'],stamp)]
 excluded={r[0] for r in c.execute(text('SELECT knowledge_id FROM source_sentence_targets'))}
 return [r for r in rows if r['id'] not in excluded]

def preparation_step(c,gid,stamp):
 import group_learning as gl
 row=c.execute(text('SELECT k.*,p.* FROM knowledge k JOIN progress p ON p.knowledge_id=k.id WHERE k.id=:g'),dict(g=gid)).mappings().first()
 if not enabled(c):return None,False
 history=gl.events(c,gid,gl.day_of(stamp))
 if history and gl.independent(history[-1]):return None,False
 if ce.known(c,gid) and row['due_at'] and datetime.fromisoformat(row['due_at'])>stamp:return None,False
 return dict(row,role='base',position=0),False

def select_preparation(c,stamp,new_limit,review_limit,allow_repeat=False):
 import group_learning as gl
 if not enabled(c):return None
 day=gl.day_of(stamp)
 used=c.execute(text("SELECT count(*) FROM daily_group_tasks d JOIN source_preparation_items p ON p.knowledge_id=d.group_id WHERE d.day=:d AND d.kind='new'"),dict(d=day)).scalar()
 new_active=c.execute(text("SELECT count(*) FROM group_active_slots s JOIN daily_group_tasks d ON d.group_id=s.group_id WHERE d.day=:d AND d.kind='new'"),dict(d=day)).scalar()
 for gid in c.execute(text('SELECT DISTINCT goal_id FROM source_sentence_targets')).scalars().all():
  if not basics_ready(c,gid):continue
  choices=[]
  for row in targets(c,gid):
   if evidence.classify(c,row['knowledge_id'],'transfer')[0]!='transfer':continue
   if ce.known(c,row['material_id']):continue
   item=c.execute(text('SELECT k.*,p.* FROM knowledge k JOIN progress p ON p.knowledge_id=k.id WHERE k.id=:k'),dict(k=row['material_id'])).mappings().first()
   choices.append(item)
  last=None if allow_repeat else gl.recent_fuzzy(c,stamp)
  choices=[item for item in choices if not gl.repeats_fuzzy(item,last)]
  if not choices:continue
  item=choices[0];mid=item['id'];existing=c.execute(text('SELECT 1 FROM daily_group_tasks WHERE day=:d AND group_id=:g'),dict(d=day,g=mid)).first()
  if not item['introduced'] and not existing and (used>=2 or new_active>=3):continue
  if not gl.admit(c,mid,mid,stamp,new_limit,review_limit):continue
  kind=c.execute(text('SELECT kind FROM daily_group_tasks WHERE day=:d AND group_id=:g'),dict(d=day,g=mid)).scalar()
  c.execute(text('INSERT OR IGNORE INTO daily_tasks VALUES(:d,:k,:v)'),dict(d=day,k=mid,v=kind))
  return ('recall' if item['introduced'] else 'learn'),dict(item,role='base',group_id=mid,group_title='迁移材料准备')
 return None

def report(c,stamp,limits=None):
 if not enabled(c):return []
 result=[]
 for gid in c.execute(text('SELECT DISTINCT goal_id FROM source_sentence_targets')).scalars().all():
  pending=[];ready=0;waiting=0;seen=0
  for row in targets(c,gid):
   mode=evidence.classify(c,row['knowledge_id'],'transfer')[0]
   if mode=='recall':seen+=1;continue
   if mode=='transfer-review':continue
   if not ce.known(c,row['material_id']):
    prompt=c.execute(text('SELECT prompt FROM knowledge WHERE id=:m'),dict(m=row['material_id'])).scalar();pending.append(dict(id=row['material_id'],prompt=prompt));continue
   if spacing(c,row['material_id'],stamp):waiting+=1
   else:ready+=1
  proofs=c.execute(text("""SELECT DISTINCT s.material_id,a.created_at,date(a.created_at,'+8 hours') AS day FROM source_sentence_targets s JOIN answers a ON a.knowledge_id=s.knowledge_id JOIN question_trials t ON t.question_id=a.question_id WHERE s.goal_id=:g AND t.mode IN ('transfer','transfer-review') AND a.correct=1 AND a.revealed=0 AND COALESCE((SELECT confidence FROM feedback_events f WHERE f.question_id=a.question_id ORDER BY f.rowid DESC LIMIT 1),a.confidence)='clear' AND NOT EXISTS(SELECT 1 FROM spelling_checks x WHERE x.question_id=a.question_id AND x.correct=0) AND NOT EXISTS(SELECT 1 FROM test_skips x WHERE x.question_id=a.question_id)"""),dict(g=gid)).all()
  today_count=len({r[0] for r in proofs if r[2]==stamp.astimezone(ZONE).date().isoformat()})
  proofs=[r for r in proofs if ce.known(c,r[0])]
  materials=len({r[0] for r in proofs});days=len({r[2] for r in proofs})
  times=[datetime.fromisoformat(r[1]) for r in proofs]
  delayed=bool(times and max(times)-min(times)>=timedelta(hours=24))
  latest=c.execute(text("""SELECT a.correct,a.revealed,COALESCE((SELECT confidence FROM feedback_events f WHERE f.question_id=a.question_id ORDER BY f.rowid DESC LIMIT 1),a.confidence),EXISTS(SELECT 1 FROM spelling_checks x WHERE x.question_id=a.question_id AND x.correct=0) FROM answers a JOIN source_sentence_targets s ON s.knowledge_id=a.knowledge_id WHERE s.goal_id=:g ORDER BY a.rowid DESC LIMIT 1"""),dict(g=gid)).first()
  latest_ok=bool(latest and latest[0] and not latest[1] and latest[2]=='clear' and not latest[3])
  state='基础学习中' if not basics_ready(c,gid) else '可尝试迁移' if ready else '等待穿插练习' if waiting else '需要准备材料' if pending else '需要补充新例句'
  if basics_ready(c,gid) and today_count>=2:state='今日迁移练习已完成'
  elif basics_ready(c,gid) and latest and not latest_ok:state='需巩固上一条表达'
  if basics_ready(c,gid) and materials>=3 and days>=2 and delayed and latest_ok:state='本轮迁移已验证，继续复习'
  reason=None
  if limits and state=='需要准备材料':
   import group_learning as gl
   counts=gl.counts(c,stamp);day=gl.day_of(stamp)
   used=c.execute(text("SELECT count(*) FROM daily_group_tasks d JOIN source_preparation_items p ON p.knowledge_id=d.group_id WHERE d.day=:d AND d.kind='new'"),dict(d=day)).scalar()
   mid=pending[0]['id'];introduced=c.execute(text('SELECT introduced FROM progress WHERE knowledge_id=:m'),dict(m=mid)).scalar()
   kind='review' if introduced else 'new'
   existing=c.execute(text('SELECT 1 FROM daily_group_tasks WHERE day=:d AND group_id=:g'),dict(d=day,g=mid)).first()
   if not existing and counts.get(kind,0)>=limits['daily-'+kind+'-limit']:reason='今日'+('复习' if introduced else '新学')+'额度已用完'
   elif not introduced and not existing and used>=2:reason='今日已新增两项迁移材料'
   slots=c.execute(text('SELECT count(*) FROM group_active_slots a LEFT JOIN group_progress g ON g.group_id=a.group_id WHERE g.due_at IS NULL OR julianday(g.due_at)<=julianday(:t)'),dict(t=stamp.isoformat())).scalar()
   if slots>=12 and not c.execute(text('SELECT 1 FROM group_active_slots WHERE group_id=:g'),dict(g=mid)).first():reason='12项活动池已满'
  title=c.execute(text('SELECT title FROM learning_groups WHERE id=:g'),dict(g=gid)).scalar()
  result.append(dict(goal_id=gid,title=title,state=state,total=len(targets(c,gid)),ready=ready,waiting=waiting,missing=pending[:2],missing_total=len(pending),seen=seen,successful_materials=materials,successful_days=days,minimum_materials=3,minimum_days=2,delayed_validation=delayed,waiting_reason=reason,today_successful_materials=today_count))
 return result


def eligible(c,gid,kid,stamp):
 row=c.execute(text('SELECT goal_id FROM source_sentence_targets WHERE knowledge_id=:k'),dict(k=kid)).first()
 if enabled(c,gid):return bool(row and row[0]==gid and allowed(c,kid,stamp))
 return not row
