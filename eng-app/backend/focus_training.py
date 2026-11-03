"""User-selected, bounded practice batches using registered knowledge only."""
import re,json,uuid
from datetime import timedelta,datetime,timezone
from sqlalchemy import text
import group_learning as groups
TABLES=('focus_requests',)

def install(c):
 c.execute(text("CREATE TABLE IF NOT EXISTS focus_requests(id TEXT PRIMARY KEY,knowledge_id TEXT NOT NULL,created_at TEXT NOT NULL,status TEXT NOT NULL,completed_at TEXT)"))
 c.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS focus_one_open ON focus_requests(knowledge_id) WHERE status IN ('pending','active')"))
 # Original, fixed mini lesson; not generated on demand or presented as external material.
 cards=[('word-practical','practical','实用的；切合实际的','word','practical 用来说明东西有用、适合实际情况。practical advice 是实用的建议；practical solution 是切实可行的解决办法。'),
 ('practical-advice','practical advice','实用的建议','collocation','practical 放在 advice 前面，说明建议实际有用。advice 通常不可数，不写 a practical advice。'),
 ('practical-solution','practical solution','切实可行的解决办法','collocation','practical 修饰 solution，说明这个办法能实际执行。单数 solution 在完整句子里通常需要 a 或 the。'),
 ('practical-find','find a practical solution','找到一个切实可行的解决办法','phrase','find 是找到；a practical solution 是一个切实可行的解决办法。先说 find，再说找到什么。'),
 ('practical-sentence','This is a practical solution.','这是一个切实可行的解决办法。','sentence','This 是这件事或这个东西，is 是，a practical solution 是一个可行的解决办法。'),
 ('practical-advice-sentence','I need practical advice.','我需要实用的建议。','sentence','I 是我；need 是需要；practical advice 是实用的建议。advice 不可数，这里不加 a。')]
 for kid,en,zh,kind,usage in cards:
  existing=c.execute(text('SELECT id FROM knowledge WHERE lower(answer)=lower(:a) LIMIT 1'),dict(a=en)).scalar()
  if existing:
   c.execute(text("UPDATE knowledge_details SET payload=json_set(payload,'$.speech_text',:a) WHERE knowledge_id=:k AND json_extract(payload,'$.speech_text') IS NULL"),dict(k=existing,a=en))
   continue
  details=dict(speech_text=en,entry_type=kind,pos='adj. 形容词' if kind=='word' else '',usage=usage,examples=[dict(en='I need practical advice.',zh='我需要实用的建议。')],extensions=[dict(en='practical solution',zh='切实可行的解决办法')],common_errors=['practical 是形容词；practice 是练习，不能随意互换。'],source_note='项目自编专项示范')
  if kind=='word':details.update(ipa_us='/ˈpræktɪkəl/',syllables='prac·ti·cal',stress='第一音节重读')
  c.execute(text('INSERT OR IGNORE INTO knowledge VALUES(:k,:zh,:en,:u,:e)'),dict(k=kid,zh=zh,en=en,u=usage,e='I need practical advice.'))
  c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES(:k)'),dict(k=kid))
  if kid!='word-practical':c.execute(text('INSERT OR IGNORE INTO course_links(knowledge_id,parent_id,stage) VALUES(:k,:p,:s)'),dict(k=kid,p='word-practical',s=3 if kind=='sentence' else 2 if kind=='phrase' else 1))
  c.execute(text('INSERT OR IGNORE INTO knowledge_details VALUES(:k,:p,1,:t)'),dict(k=kid,p=json.dumps(details,ensure_ascii=False),t=datetime.now(timezone.utc).isoformat()))

def candidates(c,kid):
 target=c.execute(text('SELECT * FROM knowledge WHERE id=:k'),dict(k=kid)).mappings().first()
 if not target:raise ValueError('词条不存在')
 pattern=re.compile(r'(?<![a-z])'+re.escape(target['answer'].strip().rstrip('.!?').casefold())+r'(?![a-z])')
 rows=c.execute(text("SELECT k.*,COALESCE(json_extract(d.payload,'$.entry_type'),'collocation') AS entry_type FROM knowledge k LEFT JOIN knowledge_details d ON d.knowledge_id=k.id ORDER BY k.rowid")).mappings()
 selected=[];limits=dict(word=1,collocation=3,phrase=3,sentence=3);counts={}
 for r in rows:
  if r['id']==kid or pattern.search(r['answer'].casefold()):
   kind=r['entry_type']
   if kind not in limits or (r['id']!=kid and counts.get(kind,0)>=limits[kind]):continue
   selected.append(dict(r));counts[kind]=counts.get(kind,0)+1
 selected.sort(key=lambda r:(r['id']!=kid,{'word':0,'collocation':1,'phrase':2,'sentence':3}.get(r['entry_type'],4)))
 return dict(target=dict(target),items=selected,counts=counts)

def add(c,kid,stamp,member_ids=None):
 existing=c.execute(text("SELECT id FROM focus_requests WHERE knowledge_id=:k AND status IN ('pending','active')"),dict(k=kid)).scalar()
 if existing:
  if member_ids:
   position=c.execute(text('SELECT COALESCE(MAX(position),0)+1 FROM group_members WHERE group_id=:g'),dict(g=existing)).scalar()
   for i,mid in enumerate(member_ids):
    kind=c.execute(text("SELECT COALESCE(json_extract(payload,'$.entry_type'),'word') FROM knowledge_details WHERE knowledge_id=:k"),dict(k=mid)).scalar()
    c.execute(text('INSERT OR IGNORE INTO group_members VALUES(:g,:k,:r,:p)'),dict(g=existing,k=mid,r={'word':'word','collocation':'base','phrase':'phrase','sentence':'sentence'}.get(kind,'base'),p=position+i))
  return dict(id=existing,saved=True,duplicate=True)
 info=candidates(c,kid)
 if member_ids:
  info['items']=[]
  for mid in member_ids:
   row=c.execute(text("SELECT k.*,COALESCE(json_extract(d.payload,'$.entry_type'),'word') AS entry_type FROM knowledge k LEFT JOIN knowledge_details d ON d.knowledge_id=k.id WHERE k.id=:k"),dict(k=mid)).mappings().first()
   if row:info['items'].append(dict(row))
 gid='focus-'+str(uuid.uuid4())
 inserted=c.execute(text("INSERT OR IGNORE INTO focus_requests VALUES(:g,:k,:t,'pending',NULL)"),dict(g=gid,k=kid,t=stamp.isoformat()))
 if not inserted.rowcount:
  existing=c.execute(text("SELECT id FROM focus_requests WHERE knowledge_id=:k AND status IN ('pending','active')"),dict(k=kid)).scalar()
  return dict(id=existing,saved=True,duplicate=True)
 c.execute(text("INSERT INTO learning_groups VALUES(:g,:k,:title,'expression')"),dict(g=gid,k=kid,title='专项 · '+info['target']['answer']))
 for i,r in enumerate(info['items']):
  role={'word':'word','collocation':'base','phrase':'phrase','sentence':'sentence'}[r['entry_type']]
  c.execute(text('INSERT INTO group_members VALUES(:g,:k,:r,:p)'),dict(g=gid,k=r['id'],r=role,p=i))
 return dict(id=gid,saved=True,duplicate=False)

def step(c,gid,stamp):
 request=c.execute(text('SELECT * FROM focus_requests WHERE id=:g'),dict(g=gid)).mappings().first()
 if not request or request['status'] in ('completed','cancelled'):return None,False
 # Only fresh independent evidence from this batch advances it; old mastery is preserved.
 days=c.execute(text("SELECT DISTINCT date(a.created_at,'+8 hours') FROM answers a JOIN group_questions q ON q.question_id=a.question_id WHERE q.group_id=:g AND julianday(a.created_at)>=julianday(:t)"),dict(g=gid,t=request['created_at'])).scalars().all()
 history=sorted([e for day in days for e in groups.events(c,gid,day) if e['created_at']>=request['created_at']],key=lambda e:e['seq'])
 last={e['knowledge_id']:e for e in history}
 passed={kid for kid,e in last.items() if groups.independent(e)}
 for r in groups.members(c,gid):
  if r['id'] not in passed:return r,False
 return None,False

def refresh(c,gid,stamp):
 state=c.execute(text('SELECT status FROM focus_requests WHERE id=:g'),dict(g=gid)).scalar()
 if not state or state=='cancelled':return
 if state=='completed':c.execute(text("UPDATE focus_requests SET status='active',completed_at=NULL WHERE id=:g"),dict(g=gid))
 item,_=step(c,gid,stamp)
 if item is None:
  c.execute(text("UPDATE focus_requests SET status='completed',completed_at=:t WHERE id=:g AND status!='cancelled'"),dict(g=gid,t=stamp.isoformat()))
  c.execute(text('INSERT INTO group_progress VALUES(:g,:d,:t,0) ON CONFLICT(group_id) DO UPDATE SET due_at=excluded.due_at,last_at=excluded.last_at'),dict(g=gid,d=(stamp+timedelta(days=1)).isoformat(),t=stamp.isoformat()))
  c.execute(text('DELETE FROM group_active_slots WHERE group_id=:g'),dict(g=gid))

def select(c,stamp,allow_repeat=False):
 last_fuzzy=None if allow_repeat else groups.recent_fuzzy(c,stamp)
 requests=c.execute(text("SELECT id FROM focus_requests WHERE status IN ('pending','active') ORDER BY rowid")).scalars().all()
 for gid in requests:
  item,_=step(c,gid,stamp)
  if item is None:refresh(c,gid,stamp);continue
  pending=c.execute(text('SELECT q.id FROM questions q JOIN group_questions g ON g.question_id=q.id LEFT JOIN answers a ON a.question_id=q.id WHERE g.group_id=:g AND q.knowledge_id=:k AND a.id IS NULL ORDER BY q.rowid LIMIT 1'),dict(g=gid,k=item['id'])).scalar()
  if not pending and groups.repeats_fuzzy(item,last_fuzzy):continue
  if not groups.acquire(c,gid,stamp):return None
  c.execute(text("UPDATE focus_requests SET status='active' WHERE id=:g"),dict(g=gid))
  c.execute(text("INSERT OR IGNORE INTO daily_group_tasks VALUES(:d,:g,'special',:k)"),dict(d=groups.day_of(stamp),g=gid,k=item['id']))
  item=dict(item);item['group_id']=gid;item['group_title']='专项 · '+c.execute(text('SELECT answer FROM knowledge WHERE id=(SELECT knowledge_id FROM focus_requests WHERE id=:g)'),dict(g=gid)).scalar()
  if pending:item['question_id']=pending
  return ('recall' if item['introduced'] else 'learn'),item
 return None

def listing(c,day):
 return [dict(r) for r in c.execute(text("SELECT f.id,k.answer AS title,f.status FROM focus_requests f JOIN knowledge k ON k.id=f.knowledge_id WHERE f.status IN ('pending','active') OR date(f.completed_at,'+8 hours')=:d ORDER BY f.rowid"),dict(d=day)).mappings()]

def cancel(c,gid):
 result=c.execute(text("UPDATE focus_requests SET status='cancelled' WHERE id=:g AND status IN ('pending','active')"),dict(g=gid))
 c.execute(text('DELETE FROM group_active_slots WHERE group_id=:g'),dict(g=gid))
 return bool(result.rowcount)
