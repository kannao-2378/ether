"""Import the reproducible, attested expression pack without replacing learner history."""
from pathlib import Path
import json,hashlib
from datetime import datetime,timezone
from sqlalchemy import text

PACK=Path(__file__).parent/'resources/compiled_courses.json'
def key(value):return ' '.join(value.strip().casefold().rstrip('.!?。！？').split())

def install(c):
 if not PACK.exists():return
 version='attested-3000-v1'
 c.execute(text('CREATE TABLE IF NOT EXISTS content_packages(id TEXT PRIMARY KEY,version TEXT,metadata TEXT,installed_at TEXT)'))
 c.execute(text('CREATE TABLE IF NOT EXISTS package_members(package_id TEXT,knowledge_id TEXT,kind TEXT,PRIMARY KEY(package_id,knowledge_id,kind))'))
 c.execute(text('CREATE TABLE IF NOT EXISTS knowledge_components(knowledge_id TEXT,component_id TEXT,relation TEXT,PRIMARY KEY(knowledge_id,component_id,relation))'))
 c.execute(text('CREATE INDEX IF NOT EXISTS components_component ON knowledge_components(component_id,knowledge_id)'))
 c.execute(text('CREATE INDEX IF NOT EXISTS memberships_unit ON course_items(unit_id,position)'))
 c.execute(text('CREATE INDEX IF NOT EXISTS materials_material ON transfer_materials(material_id,knowledge_id)'))
 c.execute(text('CREATE INDEX IF NOT EXISTS links_parent ON course_links(parent_id,knowledge_id)'))
 if c.execute(text("SELECT version FROM content_packages WHERE id='attested-expressions'")).scalar()==version:return
 data=json.loads(PACK.read_text(encoding='utf-8'));stamp=datetime.now(timezone.utc).isoformat()
 existing={}
 for r in c.execute(text('SELECT id,answer FROM knowledge ORDER BY rowid')).mappings():existing.setdefault(key(r['answer']),r['id'])
 aliases={};new=[];detail=[];members=[];course_rows=[];unit_rows=[];item_rows=[];link_rows=[];materials=[];components=[];combinations=[]
 for kind,rows in [('expression',data['expressions']),('word',data['words']),('sentence',data['sentences'])]:
  for row in rows:
   canonical=key(row['answer']);kid=existing.get(canonical)
   if not kid:
    kid=row['id'];existing[canonical]=kid
    new.append(dict(id=kid,prompt=row['prompt'],answer=row['answer'],explanation=row['explanation'],example=row['example']))
    detail.append(dict(k=kid,p=json.dumps(row['details'],ensure_ascii=False,separators=(',',':')),t=stamp))
   aliases[row['id']]=kid;members.append(dict(k=kid,kind=kind))
 # One shared content ID is used for an expression even if it was already in the starter course.
 c.execute(text('INSERT OR IGNORE INTO knowledge(id,prompt,answer,explanation,example) VALUES(:id,:prompt,:answer,:explanation,:example)'),new)
 c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES(:id)'),[dict(id=r['id']) for r in new])
 c.execute(text('INSERT OR IGNORE INTO knowledge_details VALUES(:k,:p,100,:t)'),detail)
 groups={}
 for expression in data['expressions']:
  groups.setdefault(expression['category'],[]).append(expression)
 positions={};unit_for={};pos=1000
 for cat in data['categories']:
  cid='course-'+cat['id'];course_rows.append(dict(id=cid,title=cat['title'],goal=cat['goal'],level='按语料覆盖与复杂度递进；非官方 CEFR 分级'))
  rows=groups.get(cat['id'],[])
  for offset in range(0,len(rows),25):
   chunk=rows[offset:offset+25];uid=cid+'-'+str(offset//25+1).zfill(3)
   unit_rows.append(dict(id=uid,c=cid,title=f'{offset//25+1:02d} · '+chunk[0]['details']['level']+' · '+cat['title'],goal='学习本组表达，再在真实句子和不同例句中回忆；新词按需要补学。',position=offset//25))
   for expression in chunk:
    kid=aliases[expression['id']];positions[kid]=pos;unit_for[kid]=uid;item_rows.append(dict(k=kid,u=uid,p=pos));pos+=10
 course_rows.append(dict(id='course-vocabulary',title='课程词汇材料',goal='本课程实际例句使用的词汇；按需补学，不要求先背完整个词库。',level='随表达课程配套'))
 for offset in range(0,len(data['words']),40):
  uid='vocabulary-'+str(offset//40+1).zfill(3);unit_rows.append(dict(id=uid,c='course-vocabulary',title=f'{offset//40+1:02d} · 课程词汇材料',goal='词汇与来源例句关联；通过独立拼写验证，不由整句成绩代替单词成绩。',position=offset//40))
  for row in data['words'][offset:offset+40]:item_rows.append(dict(k=aliases[row['id']],u=uid,p=100000+offset))
 first_sentence={}
 for row in data['sentences']:
  kid=aliases[row['id']];parent=aliases[row['parent']]
  if parent not in first_sentence:first_sentence[parent]=kid;stage=3;prereq=parent
  else:stage=4;prereq=first_sentence[parent]
  if kid!=prereq:link_rows.append(dict(k=kid,parent=prereq,stage=stage,source='Tatoeba 独立双语例句；保留原句出处'))
  item_rows.append(dict(k=kid,u=unit_for[parent],p=positions[parent]+stage))
  for word in row['word_keys']:
   atom=aliases[word]
   if atom!=kid:materials.append(dict(k=kid,m=atom));components.append(dict(k=kid,m=atom,r='contains_word'))
  combinations.append(dict(k=kid,s=parent,m=kid))
 # A successful sentence covers every selected expression it actually contains for that day.
 import re
 for expression in data['expressions']:
  for example in expression['details']['examples']:
   sid='sent-'+hashlib.sha256(example['en'].casefold().encode()).hexdigest()[:16]
   if sid in aliases and aliases[sid]!=aliases[expression['id']]:components.append(dict(k=aliases[sid],m=aliases[expression['id']],r='contains_expression'))
 c.execute(text('INSERT OR IGNORE INTO learning_courses VALUES(:id,:title,:goal,:level)'),course_rows)
 c.execute(text('INSERT OR IGNORE INTO course_units VALUES(:id,:c,:title,:goal,:position)'),unit_rows)
 c.execute(text('INSERT OR IGNORE INTO course_items VALUES(:k,:u,:p)'),item_rows)
 c.execute(text('INSERT OR IGNORE INTO course_links VALUES(:k,:parent,:stage,:source)'),link_rows)
 c.execute(text('INSERT OR IGNORE INTO transfer_materials VALUES(:k,:m)'),materials)
 c.execute(text('INSERT OR IGNORE INTO knowledge_components VALUES(:k,:m,:r)'),components)
 c.execute(text('INSERT OR IGNORE INTO sentence_combinations VALUES(:k,:s,:m,1)'),combinations)
 c.execute(text("INSERT OR IGNORE INTO package_members VALUES('attested-expressions',:k,:kind)"),members)
 metadata={k:data[k] for k in ('expression_count','sentence_count','word_count','selection','source_files')}
 metadata['canonical_counts']={kind:len({r['k'] for r in members if r['kind']==kind}) for kind in ('expression','word','sentence')}
 c.execute(text("INSERT INTO content_packages VALUES('attested-expressions',:v,:m,:t) ON CONFLICT(id) DO UPDATE SET version=excluded.version,metadata=excluded.metadata,installed_at=excluded.installed_at"),dict(v=version,m=json.dumps(metadata,ensure_ascii=False),t=stamp))

def summary(c):
 if not c.execute(text("SELECT 1 FROM sqlite_master WHERE name='content_packages'")).first():return []
 return [dict(id=r['id'],version=r['version'],**json.loads(r['metadata'])) for r in c.execute(text('SELECT * FROM content_packages')).mappings()]
