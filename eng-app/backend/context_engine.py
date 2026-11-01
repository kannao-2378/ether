"""Typed action forms + construction templates, with persisted five-question rounds."""
from sqlalchemy import text
from datetime import datetime,timedelta,timezone
from scheduler import consolidation_count, CONSOLIDATION_LIMIT

ACTIONS=[
 ('drink-water','喝水','drink water','drinking water',['drink','water']),
 ('read-books','读书','read books','reading books',['read','books']),
 ('learn-english','学英语','learn English','learning English',['learn','english']),
]
WORDS={'drink':('喝','drink'),'water':('水','water'),'read':('阅读','read'),'books':('书（复数）','books'),'learn':('学习','learn'),'english':('英语','English')}

def install(c,text):
 c.execute(text('CREATE TABLE IF NOT EXISTS context_rounds(id INTEGER PRIMARY KEY,created_at TEXT)'))
 c.execute(text('CREATE TABLE IF NOT EXISTS context_round_items(round_id INTEGER,knowledge_id TEXT,PRIMARY KEY(round_id,knowledge_id))'))
 c.execute(text('CREATE TABLE IF NOT EXISTS composition_evidence(question_id TEXT PRIMARY KEY,structure_id TEXT,material_id TEXT,independent INTEGER,created_at TEXT)'))
 for kid,(prompt,answer) in WORDS.items():
  c.execute(text('INSERT OR IGNORE INTO knowledge VALUES(:k,:p,:a,:e,:a)'),dict(k='word-'+kid,p=prompt,a=answer,e='单词独立回忆训练；整句写对不自动将此单词标为掌握。'))
  c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES(:k)'),dict(k='word-'+kid))
 for material,meaning,base,gerund,words in ACTIONS:
  form=material+'-ing-form'
  c.execute(text('INSERT OR IGNORE INTO knowledge VALUES(:k,:p,:a,:e,:a)'),dict(k=form,p=meaning+'（使用 doing 形式）',a=gerund,e='在 enjoy 后使用 doing 形式；不能把这一形式直接接在 want to 后。'))
  c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES(:k)'),dict(k=form))
  for structure,construction,prompt,verb in [('want-to','I want to ','我想'+meaning+'。',base),('enjoy-doing','I enjoy ','我享受'+meaning+'的过程（使用 enjoy）。',gerund)]:
   kid='compose-'+structure+'-'+material;answer=construction+verb+'.'
   c.execute(text('INSERT OR IGNORE INTO knowledge VALUES(:k,:p,:a,:e,:a)'),dict(k=kid,p=prompt,a=answer,e='组合训练：'+('want to 后接动词原形。' if structure=='want-to' else 'enjoy 后接 doing。')))
   c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES(:k)'),dict(k=kid))
   c.execute(text("INSERT OR IGNORE INTO course_links VALUES(:k,:parent,4,'结构模板与动作形式组合')"),dict(k=kid,parent=structure+'-sentence'))
   c.execute(text('INSERT OR IGNORE INTO sentence_combinations VALUES(:k,:s,:m,1)'),dict(k=kid,s=structure,m=material))
   required=[material]+['word-'+w for w in words]+([form] if structure=='enjoy-doing' else [])
   for dependency in required:c.execute(text('INSERT OR IGNORE INTO transfer_materials VALUES(:k,:m)'),dict(k=kid,m=dependency))

def pick(c,stamp,test=False,new_limit=5,review_limit=5):
 current=c.execute(text('SELECT MAX(id) FROM context_rounds')).scalar()
 if current is None:
  c.execute(text('INSERT INTO context_rounds(created_at) VALUES(:t)'),dict(t=stamp.isoformat()))
  current=c.execute(text('SELECT MAX(id) FROM context_rounds')).scalar()
 used=c.execute(text('SELECT COUNT(*) FROM context_round_items WHERE round_id=:r'),dict(r=current)).scalar()
 if used>=5:
  if test:return None,'这一轮 5 道情境题已完成，可以开始下一轮。'
  # Normal daily learning continues without a manual round-reset button.
  c.execute(text('INSERT INTO context_rounds(created_at) VALUES(:t)'),dict(t=stamp.isoformat()))
  current=c.execute(text('SELECT MAX(id) FROM context_rounds')).scalar()
 candidates=c.execute(text('''SELECT k.*,p.* FROM sentence_combinations sc JOIN knowledge k ON k.id=sc.knowledge_id JOIN progress p ON p.knowledge_id=k.id
 WHERE k.id LIKE 'compose-%' AND NOT EXISTS(SELECT 1 FROM context_round_items ri WHERE ri.round_id=:r AND ri.knowledge_id=k.id)
 AND (:test OR (EXISTS(SELECT 1 FROM course_links l JOIN progress parent ON parent.knowledge_id=l.parent_id WHERE l.knowledge_id=k.id AND parent.level>=3)
 AND NOT EXISTS(SELECT 1 FROM transfer_materials tm JOIN progress mp ON mp.knowledge_id=tm.material_id WHERE tm.knowledge_id=k.id AND mp.level<3)))
 ORDER BY (SELECT COUNT(*) FROM answers a WHERE a.knowledge_id=k.id),COALESCE(p.last_at,''),k.rowid'''),dict(r=current,test=test)).mappings().all()
 day=stamp.astimezone(timezone(timedelta(hours=8))).date().isoformat()
 counts=dict(c.execute(text('SELECT kind,COUNT(*) FROM daily_tasks dt WHERE day=:d GROUP BY kind'),dict(d=day)).all())
 sequence=c.execute(text('SELECT COALESCE(MAX(rowid),0)+1 FROM answers')).scalar()
 for row in candidates:
  kind='review' if row['introduced'] else 'new'
  if not test:
   if kind=='new' and consolidation_count(c,stamp)>=CONSOLIDATION_LIMIT:continue
   if c.execute(text('SELECT 1 FROM daily_coverage WHERE day=:d AND knowledge_id=:k'),dict(d=day,k=row['id'])).first():continue
   queued=c.execute(text('SELECT due_at,due_sequence FROM review_queue WHERE knowledge_id=:k'),dict(k=row['id'])).mappings().first()
   if kind=='review' and consolidation_count(c,stamp)>=CONSOLIDATION_LIMIT and not c.execute(text('SELECT 1 FROM consolidation_slots WHERE knowledge_id=:k'),dict(k=row['id'])).first():continue
   if queued and ((queued['due_at'] and datetime.fromisoformat(queued['due_at'])>stamp) or (not queued['due_at'] and queued['due_sequence']>sequence)):continue
   if row['due_at'] and datetime.fromisoformat(row['due_at'])>stamp:continue
   exists=c.execute(text('SELECT 1 FROM daily_tasks WHERE day=:d AND knowledge_id=:k'),dict(d=day,k=row['id'])).first()
   if not exists and counts.get(kind,0)>=(review_limit if kind=='review' else new_limit):continue
   c.execute(text('INSERT OR IGNORE INTO daily_tasks VALUES(:d,:k,:v)'),dict(d=day,k=row['id'],v=kind))
  c.execute(text('INSERT INTO context_round_items VALUES(:r,:k)'),dict(r=current,k=row['id']))
  return dict(row),None
 return None,'当前可用且未重复的组合已练完，或已达到每日上限。本轮不强凑五题。'
