"""Bounded checks against an explicitly isolated installed database."""
import json,re,sqlite3,argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from sqlalchemy import create_engine,text
import course_expansion,curriculum_engine as ce,group_learning,selection_cache
from datetime import datetime,timezone
def verify(data):
 p=Path(data).resolve()
 if p== (ROOT/'backend/data').resolve() or '.tools' not in p.parts:raise ValueError('Use an isolated .tools data directory')
 e=create_engine('sqlite:///'+str(p/'learning.db'));s=course_expansion.load();checked=0
 with e.connect() as c:
  for g in s['lessons']:
   gid=('expansion-'+g['id']) if c.execute(text('SELECT 1 FROM curriculum_paths WHERE goal_id=:g AND course_id=\'general-mainline\''),dict(g='expansion-'+g['id'])).first() else g['id'];root=c.execute(text('SELECT group_id FROM group_primary WHERE knowledge_id=:g'),dict(g=gid)).scalar();assert root==gid,('ownership',gid,root)
   actual=c.execute(text('SELECT knowledge_id,role FROM curriculum_lessons WHERE goal_id=:g'),dict(g=gid)).all()
   assert sum(role=='transfer' for _,role in actual)>=len(g['sentences'])-1,('contexts',gid)
   expected={row['en'] for row in g['sentences'][1:]}
   actual_en=set(c.execute(text("SELECT k.answer FROM curriculum_lessons l JOIN knowledge k ON k.id=l.knowledge_id WHERE l.goal_id=:g AND l.role='transfer'"),dict(g=gid)).scalars());assert expected<=actual_en,('missing source contexts',gid)
   assert c.execute(text('SELECT COUNT(*) FROM curriculum_prerequisites WHERE goal_id=:g'),dict(g=gid)).scalar()>0
   for row in g['sentences']:
    assert row['en'] and row['zh'] and set(row['words'])<=s['words'].keys()
   checked+=1
  # An unseen prerequisite prevents admission; all required words gate a test.
  probe=next(g for g in s['lessons'] if len(g['sentences'])>1);gid=probe['id']
  transaction=c.begin_nested()
  try:
   deps=c.execute(text('SELECT prerequisite_id FROM curriculum_prerequisites WHERE goal_id=:g'),dict(g=gid)).scalars().all()
   for dep in deps:
    c.execute(text('UPDATE progress SET introduced=0,level=0 WHERE knowledge_id=:k OR knowledge_id IN (SELECT alias_id FROM curriculum_aliases WHERE knowledge_id=:k)'),dict(k=dep))
   with selection_cache.scope():assert ce.blockers(c,gid)
   kid=c.execute(text("SELECT knowledge_id FROM curriculum_lessons WHERE goal_id=:g AND role='transfer' LIMIT 1"),dict(g=gid)).scalar()
   req=c.execute(text('SELECT material_id FROM group_requirements WHERE knowledge_id=:k'),dict(k=kid)).scalars().all()
   for mid in req:
    c.execute(text('UPDATE progress SET introduced=0,level=0 WHERE knowledge_id=:k OR knowledge_id IN (SELECT alias_id FROM curriculum_aliases WHERE knowledge_id=:k)'),dict(k=mid))
   with selection_cache.scope():assert not group_learning.requirements_met(c,kid,stamp=datetime.now(timezone.utc))
   for mid in req:c.execute(text('UPDATE progress SET introduced=1,level=5 WHERE knowledge_id=:k'),dict(k=mid))
   with selection_cache.scope():assert group_learning.requirements_met(c,kid,stamp=datetime.now(timezone.utc))
   for x in json.loads((ROOT/'backend/resources/mainline_course.json').read_text(encoding='utf-8'))['goals'][:2]:c.execute(text('UPDATE progress SET introduced=1,level=5 WHERE knowledge_id=:k'),dict(k=x['key']))
   first=json.loads((ROOT/'backend/resources/mainline_course.json').read_text(encoding='utf-8'))['goals'][:4]
   for x in first:c.execute(text("INSERT OR REPLACE INTO daily_group_tasks VALUES('2099-01-01',:g,'new',0)"),dict(g=x['key']))
   with selection_cache.scope():
    next_rows=ce.candidates(c,'general-mainline',1);assert next_rows and not next_rows[0]['id'].startswith('mainline-'), 'breadth lane should follow four structure admissions'
  finally:transaction.rollback()
  assert c.execute(text('PRAGMA quick_check')).scalar()=='ok'
 e.dispose();return dict(lessons_checked=checked,ownership=True,source_words=True,prerequisite_gate=True,transfer_material_gate=True,integrity=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',required=True);print(json.dumps(verify(p.parse_args().data)))
