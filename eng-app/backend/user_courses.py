"""User authored course import and its isolated, click-driven review state."""
import json, uuid, re
from datetime import datetime, timedelta, timezone
from sqlalchemy import text

ZONE=timezone(timedelta(hours=8))
MEMORY_GAPS=(2,5,10,30,90,120)
TRANSFER_GAPS=(10,30,60,90,120)

def install(c):
 c.execute(text('CREATE TABLE IF NOT EXISTS user_courses(id TEXT PRIMARY KEY,title TEXT NOT NULL,created_at TEXT NOT NULL,source_json TEXT NOT NULL)'))
 c.execute(text('CREATE TABLE IF NOT EXISTS user_course_groups(id TEXT PRIMARY KEY,course_id TEXT NOT NULL,position INTEGER NOT NULL,payload TEXT NOT NULL,UNIQUE(course_id,position))'))
 c.execute(text('CREATE TABLE IF NOT EXISTS user_course_items(id TEXT PRIMARY KEY,course_id TEXT NOT NULL,group_id TEXT NOT NULL,group_position INTEGER NOT NULL,item_position INTEGER NOT NULL,item_type TEXT NOT NULL,prompt TEXT NOT NULL,answer TEXT NOT NULL,accepted_answers TEXT NOT NULL,payload TEXT NOT NULL,UNIQUE(group_id,item_position))'))
 c.execute(text('CREATE TABLE IF NOT EXISTS user_learning_state(item_id TEXT PRIMARY KEY,status TEXT NOT NULL DEFAULT \'new\',due_day TEXT,seen_day TEXT,seen_count INTEGER NOT NULL DEFAULT 0,remember_today INTEGER NOT NULL DEFAULT 0,fuzzy_today INTEGER NOT NULL DEFAULT 0,last_confidence TEXT,updated_at TEXT)'))
 c.execute(text('CREATE TABLE IF NOT EXISTS user_learning_events(id TEXT PRIMARY KEY,item_id TEXT NOT NULL,day TEXT NOT NULL,confidence TEXT NOT NULL,created_at TEXT NOT NULL)'))
 c.execute(text('CREATE TABLE IF NOT EXISTS user_learning_meta(key TEXT PRIMARY KEY,value INTEGER NOT NULL)'))
 c.execute(text("INSERT OR IGNORE INTO user_learning_meta VALUES('event_no',0)"))
 columns={r[1] for r in c.execute(text('PRAGMA table_info(user_learning_state)'))}
 if 'repeat_after_no' not in columns:c.execute(text('ALTER TABLE user_learning_state ADD COLUMN repeat_after_no INTEGER NOT NULL DEFAULT 0'))
 if 'interval_index' not in columns:c.execute(text('ALTER TABLE user_learning_state ADD COLUMN interval_index INTEGER NOT NULL DEFAULT 0'))
 c.execute(text('CREATE INDEX IF NOT EXISTS user_items_order ON user_course_items(course_id,group_position,item_position)') )
 c.execute(text('CREATE INDEX IF NOT EXISTS user_state_due ON user_learning_state(due_day,status)'))

def _str(v): return isinstance(v,str) and bool(v.strip())
def _used(items,vocab):
 if not isinstance(items,list) or not all(_str(x) for x in items):return False
 known={x['en'].strip().casefold() for x in vocab if isinstance(x,dict) and _str(x.get('en'))} if isinstance(vocab,list) else set()
 return all(x.strip().casefold() in known for x in items)
def validate(data):
 errors=[]
 if not isinstance(data,dict): return ['根字段：必须是JSON对象']
 if not _str(data.get('title')): errors.append('title：必填文本')
 groups=data.get('groups')
 if not isinstance(groups,list) or len(groups)!=30: return errors+['groups：必须恰好包含30组']
 for gi,g in enumerate(groups,1):
  p=f'第{gi}组'
  if not isinstance(g,dict): errors.append(f'{p}：必须是对象');continue
  vocab=g.get('vocabulary')
  if not isinstance(vocab,list) or not vocab: errors.append(f'{p}.vocabulary：必须是非空数组')
  else:
   for vi,w in enumerate(vocab,1):
    if not isinstance(w,dict): errors.append(f'{p}.vocabulary[{vi}]：必须是对象');continue
    fields=('en','zh','part_of_speech','ipa_us','ipa_uk','syllables','stress','root_affixes','word_forms','collocations','examples','mnemonic','spelling','needs_review','accepted_answers_en','vocabulary_used')
    for k in fields:
     if k not in w:errors.append(f'{p}.vocabulary[{vi}].{k}：缺少字段；不适用请填null或空数组');continue
     if k in ('en','zh') and not _str(w.get(k)):errors.append(f'{p}.vocabulary[{vi}].{k}：必填文本')
     if k=='needs_review' and not isinstance(w[k],bool):errors.append(f'{p}.vocabulary[{vi}].needs_review：必须是布尔值')
     if k in ('ipa_us','ipa_uk','mnemonic','spelling','part_of_speech') and w[k] is not None and not _str(w[k]):errors.append(f'{p}.vocabulary[{vi}].{k}：请填文本或null')
     if k in ('syllables','root_affixes','word_forms','collocations') and w[k] is not None and not isinstance(w[k],list):errors.append(f'{p}.vocabulary[{vi}].{k}：请填数组或null')
     if k=='stress' and w[k] is not None and not isinstance(w[k],(int,str)):errors.append(f'{p}.vocabulary[{vi}].stress：请填重读音节序号/文本或null')
     if k=='examples' and w[k] is not None:
      if not isinstance(w[k],list):errors.append(f'{p}.vocabulary[{vi}].examples：请填数组或null')
      else:
       for ei,ex in enumerate(w[k],1):
        if not isinstance(ex,dict) or not _str(ex.get('en')) or not _str(ex.get('zh')):errors.append(f'{p}.vocabulary[{vi}].examples[{ei}]：需要en和zh文本')
     if k=='accepted_answers_en' and (not isinstance(w[k],list) or not w[k] or not all(_str(x) for x in w[k])):errors.append(f'{p}.vocabulary[{vi}].accepted_answers_en：必须是非空英文答案数组')
     if k=='vocabulary_used' and not _used(w[k],vocab):errors.append(f'{p}.vocabulary[{vi}].vocabulary_used：必须是本组词汇英文的数组')
  target=g.get('target')
  if not isinstance(target,dict): errors.append(f'{p}.target：必须是对象')
  else:
   for k in ('type','en','zh'):
    if not _str(target.get(k)): errors.append(f'{p}.target.{k}：必填文本')
   if target.get('type') not in ('rule','collocation','grammar'): errors.append(f'{p}.target.type：只能是rule/collocation/grammar')
   if not isinstance(target.get('accepted_answers_en'),list) or not target.get('accepted_answers_en') or not all(_str(x) for x in target['accepted_answers_en']):errors.append(f'{p}.target.accepted_answers_en：必须是非空英文答案数组')
   if not _used(target.get('vocabulary_used'),vocab):errors.append(f'{p}.target.vocabulary_used：必须是本组词汇英文的数组')
   if not isinstance(target.get('needs_review'),bool):errors.append(f'{p}.target.needs_review：必须是布尔值')
  for field,n in (('required_sentences',2),('transfer_cases',10)):
   arr=g.get(field)
   if not isinstance(arr,list) or len(arr)!=n: errors.append(f'{p}.{field}：必须恰好包含{n}项');continue
   for ix,item in enumerate(arr,1):
    label=f'{p}.{field}[{ix}]'
    if not isinstance(item,dict): errors.append(f'{label}：必须是对象');continue
    for k in ('prompt_zh','accepted_answers_en','vocabulary_used','needs_review'):
     if k not in item: errors.append(f'{label}.{k}：缺少字段')
    if not _str(item.get('prompt_zh')): errors.append(f'{label}.prompt_zh：必填文本')
    a=item.get('accepted_answers_en')
    if not isinstance(a,list) or not a or not all(_str(x) for x in a): errors.append(f'{label}.accepted_answers_en：必须是非空英文答案数组')
    if not _used(item.get('vocabulary_used'),vocab): errors.append(f'{label}.vocabulary_used：必须是本组词汇英文的数组')
    if not isinstance(item.get('needs_review'),bool):errors.append(f'{label}.needs_review：必须是布尔值')
 return errors

def _items(g):
 out=[]
 for i,w in enumerate(g['vocabulary']):
  details={k:v for k,v in w.items() if k not in ('en','zh')}
  out.append(('word',w['zh'],w['accepted_answers_en'][0],w['accepted_answers_en'],{'word':w,'content':details}))
 t=g['target'];out.append(('focus',t['zh'],t['en'],t['accepted_answers_en'],{'target':t}))
 for i,s in enumerate(g['required_sentences']):out.append(('sentence',s['prompt_zh'],s['accepted_answers_en'][0],s['accepted_answers_en'],s))
 for i,s in enumerate(g['transfer_cases']):out.append(('transfer',s['prompt_zh'],s['accepted_answers_en'][0],s['accepted_answers_en'],s))
 return out

def import_course(c,data,stamp):
 errors=validate(data)
 if errors: raise ValueError('\n'.join(errors[:100]))
 cid=str(uuid.uuid4());title=data['title'].strip()
 c.execute(text('INSERT INTO user_courses VALUES(:id,:title,:t,:j)'),dict(id=cid,title=title,t=stamp.isoformat(),j=json.dumps(data,ensure_ascii=False)))
 for gi,g in enumerate(data['groups']):
  gid=str(uuid.uuid4());c.execute(text('INSERT INTO user_course_groups VALUES(:id,:c,:p,:j)'),dict(id=gid,c=cid,p=gi,j=json.dumps(g,ensure_ascii=False)))
  for ii,(kind,prompt,answer,accepted,payload) in enumerate(_items(g)):
   iid=str(uuid.uuid4());c.execute(text('INSERT INTO user_course_items VALUES(:id,:c,:g,:gp,:ip,:kind,:p,:a,:aa,:j)'),dict(id=iid,c=cid,g=gid,gp=gi,ip=ii,kind=kind,prompt=prompt,answer=answer,aa=json.dumps(accepted,ensure_ascii=False),j=json.dumps(payload,ensure_ascii=False)))
   c.execute(text('INSERT INTO user_learning_state(item_id) VALUES(:id)'),dict(id=iid))
 return {'id':cid,'title':title,'groups':30,'items':sum(len(_items(g)) for g in data['groups'])}

def local_day(stamp):return stamp.astimezone(ZONE).date()
def next_item(c,stamp):
 day=local_day(stamp).isoformat()
 event_no=c.execute(text("SELECT value FROM user_learning_meta WHERE key='event_no'")).scalar() or 0
 row=c.execute(text("SELECT i.*,s.status,s.due_day,s.seen_day,s.seen_count,s.remember_today,s.fuzzy_today FROM user_course_items i JOIN user_learning_state s ON s.item_id=i.id JOIN user_courses u ON u.id=i.course_id WHERE s.status!='done' AND (s.due_day IS NULL OR s.due_day<=:d) AND (s.seen_day IS NULL OR s.seen_day<>:d OR s.due_day IS NULL OR s.due_day<>:d OR s.repeat_after_no<=:n) ORDER BY CASE WHEN s.due_day<=:d AND s.status IN ('remember','familiar','transfer') AND (s.seen_day IS NULL OR s.seen_day<:d) THEN 0 WHEN s.seen_day<:d AND s.status!='new' THEN 1 WHEN s.seen_day=:d AND s.repeat_after_no<=:n THEN 2 ELSE 3 END,u.created_at,i.group_position,i.item_position LIMIT 1"),dict(d=day,n=event_no)).mappings().first()
 return dict(row) if row else None
def due_string(day,gap):return (datetime.fromisoformat(day).date()+timedelta(days=gap)).isoformat()
def submit(c,item_id,answer,confidence,stamp):
 row=c.execute(text('SELECT i.*,s.* FROM user_course_items i JOIN user_learning_state s ON s.item_id=i.id WHERE i.id=:id'),dict(id=item_id)).mappings().first()
 if not row:raise ValueError('学习内容不存在')
 kind=row['item_type'];allowed=('fuzzy','remember','familiar') if kind=='word' else ('fuzzy','remember','transfer')
 if confidence not in allowed:raise ValueError('自评选项无效')
 norm=lambda x:re.sub(r'\s+',' ',x.strip()).casefold()
 accepted=json.loads(row['accepted_answers']);correct=norm(answer) in {norm(x) for x in accepted}
 if not correct:raise ValueError('答案与列出的标准答案不匹配，请先修正拼写')
 day=local_day(stamp);d=day.isoformat();status=row['status'];seen_count=row['seen_count'];remember=row['remember_today'] if row['seen_day']==d else 0;fuzzy=row['fuzzy_today'] if row['seen_day']==d else 0;due=None;idx=row['interval_index']
 if confidence=='fuzzy':
  if status in ('familiar','transfer'):
   status='relearning';fuzzy=0;due=(day+timedelta(days=1)).isoformat()
  else:
   status='fuzzy';fuzzy+=1;due=d
  idx=0;remember=0
 elif confidence=='remember':
  remember+=1
  if status in ('familiar','transfer','relearning'):
   status='remember';idx=0;due=due_string(d,2)
  elif remember>=2:
   if status=='remember':idx=min(idx+1,len(MEMORY_GAPS)-1)
   else:idx=0
   status='remember';due=due_string(d,MEMORY_GAPS[idx])
  else:
   status='learning';due=d
 elif confidence in ('familiar','transfer'):
  status='familiar' if confidence=='familiar' else 'transfer'
  idx=min(idx+1,len(TRANSFER_GAPS)-1) if row['status'] in ('familiar','transfer') else 0
  due=due_string(d,TRANSFER_GAPS[idx])
 seen_count+=1
 c.execute(text("UPDATE user_learning_meta SET value=value+1 WHERE key='event_no'"))
 event_no=c.execute(text("SELECT value FROM user_learning_meta WHERE key='event_no'")).scalar()
 repeat_gap=2+(sum(item_id.encode('utf-8'))%3)
 repeat_after=(event_no+repeat_gap) if confidence in ('fuzzy','remember') and due==d else 0
 c.execute(text('UPDATE user_learning_state SET status=:s,due_day=:due,seen_day=:d,seen_count=:n,remember_today=:r,fuzzy_today=:f,last_confidence=:cf,updated_at=:t,repeat_after_no=:rep,interval_index=:idx WHERE item_id=:id'),dict(s=status,due=due,d=d,n=seen_count,r=remember,f=fuzzy,cf=confidence,t=stamp.isoformat(),id=item_id,rep=repeat_after,idx=idx))
 c.execute(text('INSERT INTO user_learning_events VALUES(:id,:item,:day,:cf,:t)'),dict(id=str(uuid.uuid4()),item=item_id,day=d,cf=confidence,t=stamp.isoformat()))
 return {'correct':True,'status':status,'due_day':due,'answer':row['answer']}
