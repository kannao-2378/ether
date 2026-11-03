"""Bounded, typed composition from reviewed rules and currently learned facts.

This is not an LLM or arbitrary word concatenation. New reviewed material facts
extend the same rules without authoring another list of complete sentences.
"""
import hashlib,itertools,json
from pathlib import Path
from datetime import timezone,timedelta
from sqlalchemy import text
import curriculum_engine as ce,transfer_evidence as evidence

RULES=Path(__file__).parent/'resources/composition_rules.json'
TABLES=('composition_items','composition_cursors')

def install(c):
 c.execute(text('CREATE TABLE IF NOT EXISTS composition_items(knowledge_id TEXT PRIMARY KEY,goal_id TEXT,rule_id TEXT,material_id TEXT,signature TEXT)'))
 c.execute(text('CREATE TABLE IF NOT EXISTS composition_cursors(goal_id TEXT PRIMARY KEY,signature TEXT,cursor INTEGER,last_at TEXT)'))
 # A later authored-course revision rebuilds lesson membership, not these saved cards.
 c.execute(text("INSERT OR IGNORE INTO curriculum_lessons SELECT goal_id,knowledge_id,'transfer',45,1 FROM composition_items"))

class Catalog:
 def __init__(self,c,spec):
  self.c=c;self.spec=spec;self.cache={}
  authored=json.loads(ce.MANIFEST.read_text(encoding='utf-8'))['goals']
  rows=c.execute(text("SELECT g.id,k.answer FROM curriculum_goals g JOIN knowledge k ON k.id=g.id WHERE g.status='ready'")).all()
  by_en={en.casefold():kid for kid,en in rows}
  self.goals={g['key']:dict(g,id=by_en[g['english'].casefold()]) for g in authored if g['english'].casefold() in by_en}
  self.materials={}
  for kid,en in c.execute(text("SELECT k.id,k.answer FROM curriculum_lessons l JOIN knowledge k ON k.id=l.knowledge_id WHERE l.role IN ('word','sentence_word') ORDER BY k.rowid")):
   self.materials.setdefault(en.casefold(),[]).append(kid)
 def resolve(self,ref):
  if ref in self.cache:return self.cache[ref]
  kind,_,name=ref.partition(':')
  candidates=[self.goals[name]['id']] if kind=='goal' and name in self.goals else self.materials.get(name.casefold(),[]) if kind=='material' else [name] if kind=='id' else []
  found=next((kid for kid in candidates if ce.known(self.c,kid)),None)
  self.cache[ref]=found;return found
 def facts(self,kind):
  facts=list(self.spec[kind])
  for kid,payload in self.c.execute(text("SELECT d.knowledge_id,d.payload FROM knowledge_details d JOIN progress p ON p.knowledge_id=d.knowledge_id WHERE p.introduced=1 AND p.level>=3 AND json_extract(d.payload,'$.composition.reviewed')=1")):
   fact=json.loads(payload)['composition']
   if fact.get('type')==kind[:-1] and fact.get('zh') and (fact.get('base') if kind=='actions' else fact.get('en')):
    facts.append(dict(fact,ref='id:'+kid))
  result=[]
  for fact in facts:
   refs=[fact['ref']]+fact.get('requires',[]);deps=[self.resolve(r) for r in refs]
   if all(deps):result.append(dict(fact,deps=list(dict.fromkeys(deps))))
  return result

def candidates(cat,target,facts):
 actions,objects,times,places=(facts[k] for k in ('actions','objects','times','places'))
 def emit(en,zh,slots,rule):
  deps=list(dict.fromkeys(kid for slot in slots for kid in slot['deps']))
  return dict(en=en.rstrip('.')+'.',zh=zh.rstrip('。')+'。',deps=deps,rule=rule)
 def timed(en,zh,slots,rule,allow=True):
  yield emit(en,zh,slots,rule)
  if allow:
   for time in times:yield emit(en+' '+time['en'],'我'+time['zh']+zh.removeprefix('我'),slots+[time],rule+'+time')
 for frame in cat.spec['frames']:
  if frame['target']!=target:continue
  for action in actions:
   form=frame.get('form','base')
   if frame['tag'] not in action.get('tags',[]) or not action.get(form):continue
   if form=='gerund' and any(not cat.resolve(r) for r in action.get('gerund_requires',[])):continue
   meaning=action.get(frame.get('meaning_form','zh'))
   if not meaning:continue
   clause='I '+frame['head']+' '+action[form];suffix=frame.get('suffix_zh','')
   yield emit(clause,'我'+frame['zh']+meaning+suffix,[action],target)
   if 'routine' in action.get('tags',[]):
    for time in times:
     yield emit(clause+' '+time['en'],'我'+frame.get('time_zh',frame['zh'])+time['zh']+meaning+suffix,[action,time],target+'+time')
 for relation in cat.spec['relations']:
  if relation['target']!=target:continue
  for obj in objects:
   if not set(relation['tags'])&set(obj.get('tags',[])):continue
   en='I '+relation['head']+' '+obj['en'];zh='我'+relation['zh']+obj['zh']+relation.get('suffix_zh','')
   yield from timed(en,zh,[obj],target,target not in ('agree-with','depend-on'))
 if target in cat.spec['action_targets']:
  goal=cat.goals[target];clause=goal['sentence'].rstrip('.');meaning=goal['sentence_zh'].rstrip('。')
  for time in times:yield emit(clause+' '+time['en'],'我'+time['zh']+meaning.removeprefix('我'),[time],target+'+time')
  if target not in ('go-home','go-to-school','get-up','cook-at-home'):
   for place in places:yield emit(clause+' '+place['en'],'我'+place['zh']+meaning.removeprefix('我'),[place],target+'+place')
 if target in ('every-day','route-in-the-morning','route-at-night','route-after-work','route-before-dinner','route-on-weekends'):
  modifier=next((t for t in times if t['ref']=='goal:'+target),None)
  if modifier:
   for action in actions:
    if 'routine' in action.get('tags',[]):yield emit('I '+action['base']+' '+modifier['en'],'我'+modifier['zh']+action['zh'],[action,modifier],target)
 if target=='route-at-home':
  place=next((p for p in places if p['ref']=='goal:route-at-home'),None)
  if place:
   for action in actions:
    if 'home' in action.get('tags',[]):yield from timed('I '+action['base']+' at home','我在家'+action['zh'],[action,place],target)
 if target=='route-i-am':
  for place,time in itertools.product(places,times):yield emit('I am '+place['en']+' '+time['en'],'我'+time['zh']+place['zh'],[place,time],target)
 if target in ('route-in-front-of','route-next-to'):
  en='in front of' if target=='route-in-front-of' else 'next to'
  for obj in objects:
   if 'spatial' not in obj.get('tags',[]):continue
   meaning='我在'+obj['zh']+('前面' if target=='route-in-front-of' else '旁边')
   yield from timed('I am '+en+' '+obj['en'],meaning,[obj],target)
 if target=='route-a-lot-of':
  for obj in objects:
   verb,meaning=('drink','喝') if 'beverage' in obj.get('tags',[]) else ('read','读') if 'reading_plural' in obj.get('tags',[]) else (None,None)
   if verb:
    dependency=cat.resolve('goal:drink-water' if verb=='drink' else 'goal:read-books')
    if dependency:yield from timed('I '+verb+' a lot of '+obj['en'],'我'+meaning+'很多'+obj['zh'],[dict(obj,deps=obj['deps']+[dependency])],target)
 if target=='route-because-of':
  rain=cat.resolve('material:the rain')
  if rain:
   for action in actions:
    if 'rain' in action.get('tags',[]):
     yield emit('I '+action['base']+' because of the rain','因为下雨，我'+action['zh'],[action,dict(deps=[rain])],target)
     for time in times:yield emit('I '+action['base']+' '+time['en']+' because of the rain','因为下雨，我'+time['zh']+action['zh'],[action,time,dict(deps=[rain])],target+'+time')
 if target=='belong-to':
  group=cat.resolve('material:this group')
  if group:
   for ref,head,meaning in [('want-to','want to','想'),('hope-to','hope to','希望'),('route-would-like-to','would like to','想'),('route-used-to','used to','过去')]:
    dep=cat.resolve('goal:'+ref)
    if dep:yield emit('I '+head+' belong to this group','我'+meaning+'属于这个群体',[dict(deps=[group,dep])],target+'+outer')

def prepare(c,stamp):
 """Materialize a small unseen reservoir; never update grades or mastered facts."""
 spec=json.loads(RULES.read_text(encoding='utf-8'));cat=Catalog(c,spec)
 facts={kind:cat.facts(kind) for kind in ('actions','objects','times','places')}
 signature=hashlib.sha256((RULES.read_text(encoding='utf-8')+json.dumps(facts,sort_keys=True)).encode()).hexdigest()
 states={row[0]:row[1:] for row in c.execute(text('SELECT goal_id,signature,cursor,last_at FROM composition_cursors'))}
 checked=0;created=0
 ordered=sorted(cat.goals.items(),key=lambda item:states.get(item[1]['id'],('','', ''))[2])
 for target,goal in ordered:
  gid=goal['id']
  state=states.get(gid)
  if state and state[0]==signature and state[1]<0:continue
  if not ce.known(c,gid) or ce.blockers(c,gid):continue
  basics=c.execute(text("SELECT knowledge_id FROM curriculum_lessons WHERE goal_id=:g AND role IN ('phrase','sentence')"),dict(g=gid)).scalars().all()
  if not basics or not all(ce.known(c,kid) for kid in basics):continue
  # The normal group scheduler enforces today's successful-variation budget.
  passed=c.execute(text("""SELECT count(DISTINCT sc.material_id) FROM answers a JOIN group_questions g ON g.question_id=a.question_id
   JOIN question_trials t ON t.question_id=a.question_id JOIN sentence_combinations sc ON sc.knowledge_id=a.knowledge_id
   WHERE g.group_id=:g AND date(a.created_at,'+8 hours')=:d AND t.mode IN ('transfer','transfer-review') AND a.correct=1 AND a.revealed=0
   AND COALESCE((SELECT confidence FROM feedback_events f WHERE f.question_id=a.question_id ORDER BY rowid DESC LIMIT 1),a.confidence)='clear'
   AND NOT EXISTS(SELECT 1 FROM spelling_checks s WHERE s.question_id=a.question_id AND s.correct=0)
   AND NOT EXISTS(SELECT 1 FROM test_skips s WHERE s.question_id=a.question_id)"""),dict(g=gid,d=stamp.astimezone(timezone(timedelta(hours=8))).date().isoformat())).scalar()
  if passed>=2:continue
  existing=c.execute(text('SELECT i.knowledge_id,i.material_id FROM composition_items i JOIN progress p ON p.knowledge_id=i.knowledge_id WHERE i.goal_id=:g AND p.introduced=0'),dict(g=gid)).all()
  reservoir=set()
  for kid,material in existing:
   dependencies=c.execute(text('SELECT material_id FROM group_requirements WHERE knowledge_id=:k'),dict(k=kid)).scalars().all()
   if all(ce.known(c,dep) for dep in dependencies) and evidence.classify(c,kid,'transfer')[0]=='transfer':reservoir.add(material)
  if len(reservoir)>=spec['batch_per_goal']:
   c.execute(text('UPDATE composition_cursors SET last_at=:t WHERE goal_id=:g'),dict(g=gid,t=stamp.isoformat()))
   checked+=1
   if checked>=spec['groups_per_request']:break
   continue
  cursor=state[1] if state and state[0]==signature else 0
  stream=iter(candidates(cat,target,facts));position=0
  for _ in range(cursor):
   if next(stream,None) is None:break
   position+=1
  for candidate in stream:
   position+=1
   if not candidate['deps'] or candidate['deps'][0] in reservoir:continue
   answer_key=evidence.key(candidate['en'])
   if c.execute(text("SELECT 1 FROM group_members m JOIN knowledge k ON k.id=m.knowledge_id WHERE m.group_id=:g AND lower(rtrim(trim(k.answer),'.!?。！？ '))=:a LIMIT 1"),dict(g=gid,a=answer_key)).first():continue
   kid='auto-transfer-'+hashlib.sha256((gid+'|'+answer_key).encode()).hexdigest()[:24]
   if evidence.classify(c,kid,'transfer',answer=candidate['en'])[0]!='transfer':continue
   ce.card(c,kid,candidate['en'],candidate['zh'],goal['usage'],candidate['en'],candidate['zh'],'sentence')
   c.execute(text('INSERT OR IGNORE INTO group_primary VALUES(:k,:g)'),dict(k=kid,g=gid));ce.member(c,gid,kid,'transfer',45)
   c.execute(text("INSERT OR IGNORE INTO course_links VALUES(:k,:g,4,'已审核规则与已学材料自动组合')"),dict(k=kid,g=gid))
   for dep in dict.fromkeys([gid]+basics+candidate['deps']):c.execute(text('INSERT OR IGNORE INTO group_requirements VALUES(:k,:m)'),dict(k=kid,m=dep))
   for dep in candidate['deps']:c.execute(text('INSERT OR IGNORE INTO transfer_materials VALUES(:k,:m)'),dict(k=kid,m=dep))
   c.execute(text('INSERT OR IGNORE INTO sentence_combinations VALUES(:k,:g,:m,1)'),dict(k=kid,g=gid,m=candidate['deps'][0]))
   c.execute(text('INSERT OR IGNORE INTO composition_items VALUES(:k,:g,:r,:m,:s)'),dict(k=kid,g=gid,r=candidate['rule'],m=candidate['deps'][0],s=signature))
   reservoir.add(candidate['deps'][0]);created+=1
   if len(reservoir)>=spec['batch_per_goal']:break
  else:position=-1
  c.execute(text('INSERT INTO composition_cursors VALUES(:g,:s,:p,:t) ON CONFLICT(goal_id) DO UPDATE SET signature=excluded.signature,cursor=excluded.cursor,last_at=excluded.last_at'),dict(g=gid,s=signature,p=position,t=stamp.isoformat()))
  checked+=1
  if checked>=spec['groups_per_request']:break
 return created
