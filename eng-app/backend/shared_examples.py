"""Read-only matching of official source examples against actual learner evidence."""
import os,re,sqlite3
from pathlib import Path
from sqlalchemy import text

def words(s):return set(re.findall(r"[a-z]+(?:'[a-z]+)?",s.casefold().replace('’',"'")))
def bank_path():return Path(os.environ.get('PELS_SENTENCE_BANK',str(Path(os.environ.get('PELS_DATA_DIR',str(Path(__file__).parent/'data')))/'shared-sentences.sqlite3')))
def normalize(s):return re.sub(r'\s+',' ',s.strip().casefold()).rstrip('.!?。！？ ')
def plan(c,limit=20):
 p=bank_path()
 if not p.exists():return dict(available=False,items=[],reason='共享例句库尚未安装')
 bank=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True);bank.row_factory=sqlite3.Row
 try:
  known=set()
  for en, in c.execute(text('SELECT k.answer FROM knowledge k JOIN progress p ON p.knowledge_id=k.id WHERE p.introduced=1 AND p.level>=3')):
   term=words(en)
   if len(term)==1:known.update(term)
  exposed={r[0] for r in c.execute(text('SELECT answer_key FROM teaching_exposures'))}
  exposed.update(normalize(r[0]) for r in c.execute(text('SELECT k.answer FROM answers a JOIN knowledge k ON k.id=a.knowledge_id')))
  goals=c.execute(text("""SELECT t.id,k.answer,k.prompt,p.unit_id,p.position FROM curriculum_goals t JOIN curriculum_paths p ON p.goal_id=t.id JOIN learning_groups g ON g.id=t.id JOIN knowledge k ON k.id=g.root_id WHERE p.course_id='general-mainline' AND t.status='ready' AND t.id LIKE 'mainline-%' ORDER BY p.unit_position,p.position""")).mappings().all()
  import curriculum_engine as ce
  items=[];gaps=[];waiting=[]
  for g in goals:
   if len(words(g['answer']))<2:continue
   candidates=bank.execute('''SELECT m.en_id,e.text AS english,z.text AS chinese,e.author AS en_author,z.author AS zh_author,z.id AS zh_id
   FROM matches m JOIN sentences e ON e.id=m.en_id JOIN pairs p ON p.en_id=e.id JOIN sentences z ON z.id=p.zh_id
   WHERE m.target_id=? ORDER BY length(e.text),e.id,z.id LIMIT 120''',(g['id'],)).fetchall()
   if not candidates:gaps.append(dict(id=g['id'],english=g['answer'],reason='官方语料中未找到精确连续表达'));continue
   if not ce.known(c,g['id']):continue
   seen=set();prepared=[]
   for r in candidates:
    if re.search(r'\d',r['english']):continue  # Numeric prerequisites are not inferred.
    if not 4<=len(re.findall(r"[a-z]+(?:'[a-z]+)?",r['english'].casefold()))<=18:continue
    key=normalize(r['english'])
    if key in exposed or key in seen:continue
    seen.add(key);missing=sorted(words(r['english'])-known)
    row=dict(r);row.update(goal_id=g['id'],goal=g['answer'],stage=g['unit_id'],missing_words=missing,mode='source_context_candidate',source_url=f"https://tatoeba.org/en/sentences/show/{r['en_id']}",translation_url=f"https://tatoeba.org/en/sentences/show/{r['zh_id']}",license='CC BY 2.0 FR',publisher_reviewed=False)
    if missing:prepared.append(row);continue
    if sum(i['goal_id']==g['id'] for i in items)<2:items.append(row)
   if prepared:waiting.append(min(prepared,key=lambda r:(len(r['missing_words']),len(r['english']))))
  return dict(available=True,known_single_word_forms=len(known),eligible_total=len(items),items=items[:limit],waiting=waiting[:limit],coverage_gaps=gaps,policy='只读备课预览：已学目标、精确表达、其余词已具备独立回忆证据、排除已曝光整句；不自动认证目标义项或迁移。',source='Tatoeba官方直接翻译语料；社区内容，不是出版社审定教材')
 finally:bank.close()
def install(c):
 c.execute(text('CREATE TABLE IF NOT EXISTS shared_example_links(knowledge_id TEXT PRIMARY KEY,goal_id TEXT,en_id INTEGER,zh_id INTEGER,created_at TEXT)'))

_prepare_state={'fingerprint':None}
def prepare(c,stamp):
 """Add at most two eligible references/day to already admitted mainline groups."""
 if not bank_path().exists():return 0
 install(c)
 day=stamp.astimezone(__import__('datetime').timezone(__import__('datetime').timedelta(hours=8))).date().isoformat()
 used=c.execute(text("SELECT COUNT(*) FROM shared_example_links WHERE date(created_at,'+8 hours')=:d"),dict(d=day)).scalar()
 if used>=2:return 0
 admitted=set(c.execute(text('SELECT group_id FROM daily_group_tasks WHERE day=:d'),dict(d=day)).scalars())
 if not admitted:return 0
 # Scanning the sentence bank is wasted work unless answers, progress, quota or today's groups changed.
 db=getattr(getattr(c,'engine',None),'url',None)
 import response_cache
 progress=response_cache.version('progress')
 fingerprint=(day,str(getattr(db,'database',None)),used,len(admitted),
  c.execute(text('SELECT COALESCE(MAX(rowid),0) FROM answers')).scalar(),progress)
 if _prepare_state['fingerprint']==fingerprint:return 0
 import hashlib,json,curriculum_engine as ce
 report=plan(c,1000);added=0
 for row in report['items']:
  gid=row['goal_id']
  if gid not in admitted:continue
  if c.execute(text('SELECT COUNT(*) FROM shared_example_links WHERE goal_id=:g'),dict(g=gid)).scalar()>=6:continue
  kid='shared-example-'+hashlib.sha256((gid+':'+str(row['en_id'])).encode()).hexdigest()[:20]
  if c.execute(text('SELECT 1 FROM knowledge WHERE id=:k'),dict(k=kid)).first():continue
  ce.card(c,kid,row['english'],row['chinese'],'原始双语情境练习，复用已学材料。',row['english'],row['chinese'],'sentence')
  raw=json.loads(c.execute(text('SELECT payload FROM knowledge_details WHERE knowledge_id=:k'),dict(k=kid)).scalar())
  raw.update(examples=[dict(en=row['english'],zh=row['chinese'],source_url=row['source_url'],translation_url=row['translation_url'],attribution=f"Tatoeba: {row['en_author'] or 'unowned'} / {row['zh_author'] or 'unowned'}",license=row['license'])],source_note=report['source'],review_status='官方导出原文直接关联，机器校验；非出版社审定',accepted_answers=[row['english']])
  c.execute(text('UPDATE knowledge_details SET payload=:p WHERE knowledge_id=:k'),dict(k=kid,p=json.dumps(raw,ensure_ascii=False)))
  c.execute(text("INSERT INTO course_links VALUES(:k,:g,4,'Tatoeba official bulk direct pair')"),dict(k=kid,g=gid))
  c.execute(text('INSERT OR IGNORE INTO group_primary VALUES(:k,:g)'),dict(k=kid,g=gid));ce.member(c,gid,kid,'transfer',60)
  c.execute(text('INSERT INTO group_requirements VALUES(:k,:g)'),dict(k=kid,g=gid))
  # Existing transfer attribution uses a concrete known material, not the whole sentence.
  for word in sorted(words(row['english'])):
   mid=c.execute(text('SELECT k.id FROM knowledge k JOIN progress p ON p.knowledge_id=k.id WHERE lower(k.answer)=:w AND p.introduced=1 AND p.level>=3 ORDER BY p.last_at DESC LIMIT 1'),dict(w=word)).scalar()
   if mid:
    c.execute(text('INSERT OR IGNORE INTO transfer_materials VALUES(:k,:m)'),dict(k=kid,m=mid))
    c.execute(text('INSERT OR IGNORE INTO group_requirements VALUES(:k,:m)'),dict(k=kid,m=mid))
  # Attribute only to an actual, already learned content expression in this
  # sentence. Do not create fictional material identities from arbitrary words.
  frame=words(row['goal']);stop={'i','you','we','they','he','she','it','a','an','the','to','am','is','are','do','does','and','or','my','your','our','their','his','her'}
  materials=[]
  for mid,en in c.execute(text('SELECT k.id,k.answer FROM knowledge k JOIN progress p ON p.knowledge_id=k.id WHERE p.introduced=1 AND p.level>=3')):
   terms=words(en)
   if not terms-frame-stop:continue
   if re.search(r'(?<![a-z])'+re.escape(en.casefold())+r'(?![a-z])',row['english'].casefold()):materials.append((len(terms),len(en),mid))
  if materials:
   material=max(materials)[2]
   c.execute(text('INSERT OR IGNORE INTO sentence_combinations VALUES(:k,:g,:m,1)'),dict(k=kid,g=gid,m=material))
  c.execute(text('INSERT INTO shared_example_links VALUES(:k,:g,:e,:z,:t)'),dict(k=kid,g=gid,e=row['en_id'],z=row['zh_id'],t=stamp.isoformat()))
  added+=1
  if used+added>=2:break
 _prepare_state['fingerprint']=fingerprint
 return added
