import json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from sqlalchemy import create_engine,text
import app,composition_engine as comp,curriculum_engine as ce,group_learning as groups,transfer_evidence as evidence

class CompositionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.tmp.name)/'test.db'));app.initialize(self.db,with_bulk=False)
  self.stamp=datetime(2026,11,4,8,tzinfo=timezone.utc)
  self.ep=patch.object(app,'real_engine',self.db);self.ep.start();self.tp=patch('app.now',return_value=self.stamp);self.tp.start()
 def tearDown(self):self.tp.stop();self.ep.stop();self.db.dispose();self.tmp.cleanup()
 def learned(self,c):
  c.execute(text("UPDATE progress SET introduced=1,level=3,last_at=:t,due_at=:d WHERE knowledge_id NOT IN (SELECT knowledge_id FROM course_links WHERE stage=4)"),dict(t=self.stamp.isoformat(),d=(self.stamp+timedelta(days=10)).isoformat()))
 def catalog(self,c):
  spec=json.loads(comp.RULES.read_text(encoding='utf-8'));cat=comp.Catalog(c,spec);facts={k:cat.facts(k) for k in ('actions','objects','times','places')};return cat,facts
 def small_rules(self):
  spec=json.loads(comp.RULES.read_text(encoding='utf-8'));spec['actions']=[a for a in spec['actions'] if a['ref']=='material:rest'];spec['objects']=[];spec['times']=[];spec['places']=[]
  path=Path(self.tmp.name)/'rules.json';path.write_text(json.dumps(spec),encoding='utf-8');return path
 def fill(self,c):
  for i in range(25):self.assertLessEqual(comp.prepare(c,self.stamp+timedelta(seconds=i)),6)
 def test_all_current_goals_have_a_rule_and_typed_candidates(self):
  with self.db.begin() as c:
   self.learned(c);cat,facts=self.catalog(c)
   covered={r['target'] for r in cat.spec['frames']+cat.spec['relations']}|set(cat.spec['action_targets'])|set(cat.spec['special_targets'])
   self.assertEqual(set(cat.goals),covered)
   missing=[g for g in cat.goals if not list(comp.candidates(cat,g,facts))];self.assertEqual(missing,[])
   want=list(comp.candidates(cat,'want-to',facts));enjoy=list(comp.candidates(cat,'enjoy-doing',facts))
   self.assertEqual(next(r['zh'] for r in want if r['en']=='I want to drink water every day.'),'我想每天喝水。');self.assertIn('I want to rest.',[r['en'] for r in want]);self.assertIn('I enjoy resting.',[r['en'] for r in enjoy])
   self.assertFalse(any('enjoy rest.' in r['en'] or 'enjoy to ' in r['en'] or 'enjoy getting up' in r['en'] for r in enjoy))
   self.assertFalse(any('water' in r['en'] for r in comp.candidates(cat,'talk-to',facts)))
   self.assertFalse(any('my keys' in r['en'] for r in comp.candidates(cat,'route-next-to',facts)))
   self.assertFalse(any('every day' in r['en'] for r in comp.candidates(cat,'route-afraid-of',facts)))
   self.assertFalse(any('get up' in r['en'] for r in comp.candidates(cat,'route-used-to',facts)))
 def test_unknown_material_and_unknown_basics_are_not_used(self):
  with self.db.begin() as c:
   cat,facts=self.catalog(c);self.assertEqual(comp.prepare(c,self.stamp),0);self.assertEqual(facts['actions'],[])
   self.learned(c);rest=cat.materials['rest'];c.execute(text('UPDATE progress SET level=2 WHERE knowledge_id IN ('+','.join(':k'+str(i) for i in range(len(rest)))+')'),{f'k{i}':k for i,k in enumerate(rest)})
   cat,facts=self.catalog(c);self.assertFalse(any(a['base']=='rest' for a in facts['actions']))
   c.execute(text("UPDATE progress SET level=2 WHERE knowledge_id IN (SELECT knowledge_id FROM curriculum_lessons WHERE role='sentence')"));self.assertEqual(comp.prepare(c,self.stamp),0)
 def test_lazy_reservoir_persists_and_preserves_grades(self):
  path=self.small_rules()
  with patch.object(comp,'RULES',path),self.db.begin() as c:
   self.learned(c);before={t:set(c.execute(text('SELECT * FROM '+t))) for t in ('answers','feedback_events','progress','memory_states')}
   self.fill(c)
   count=c.execute(text('SELECT count(*) FROM composition_items')).scalar();self.assertGreater(count,0)
   self.fill(c);self.assertEqual(count,c.execute(text('SELECT count(*) FROM composition_items')).scalar())
   self.assertTrue(c.execute(text("SELECT 1 FROM composition_items i JOIN knowledge k ON k.id=i.knowledge_id WHERE i.goal_id='want-to' AND k.answer='I want to rest.'")).first())
   for t,rows in before.items():self.assertTrue(rows<=set(c.execute(text('SELECT * FROM '+t))),t)
   self.assertEqual(c.execute(text('SELECT count(*) FROM composition_items i JOIN progress p ON p.knowledge_id=i.knowledge_id WHERE p.introduced!=0 OR p.level!=0')).scalar(),0)
  with self.db.begin() as c:c.execute(text('DELETE FROM curriculum_lessons WHERE knowledge_id IN (SELECT knowledge_id FROM composition_items)'))
  app.initialize(self.db,with_bulk=False)
  with self.db.connect() as c:
   self.assertEqual(count,c.execute(text('SELECT count(*) FROM composition_items')).scalar())
   self.assertEqual(count,c.execute(text('SELECT count(*) FROM composition_items i JOIN curriculum_lessons l ON l.knowledge_id=i.knowledge_id')).scalar())
 def test_new_reviewed_learned_material_extends_existing_rules_without_sentence_pack(self):
  with patch.object(comp,'RULES',self.small_rules()),self.db.begin() as c:
   self.learned(c);self.fill(c)
   ce.card(c,'custom-write-emails','write emails','写邮件','','','','phrase')
   raw=c.execute(text("SELECT payload FROM knowledge_details WHERE knowledge_id='custom-write-emails'")).scalar();d=json.loads(raw);d['composition']=dict(reviewed=True,type='action',base='write emails',gerund='writing emails',zh='写邮件',tags=['intent','preference'])
   c.execute(text("UPDATE knowledge_details SET payload=:p WHERE knowledge_id='custom-write-emails'"),dict(p=json.dumps(d)))
   self.fill(c);self.assertFalse(c.execute(text("SELECT 1 FROM knowledge WHERE answer='I want to write emails.'")).first())
   c.execute(text("UPDATE progress SET introduced=1,level=3 WHERE knowledge_id='custom-write-emails'"));self.fill(c)
   self.assertTrue(c.execute(text("SELECT 1 FROM knowledge WHERE answer='I want to write emails.'")).first())
   self.assertTrue(c.execute(text("SELECT 1 FROM knowledge WHERE answer='I enjoy writing emails.'")).first())
 def test_exposed_complete_answer_is_not_regenerated_as_transfer(self):
  with patch.object(comp,'RULES',self.small_rules()),self.db.begin() as c:
   self.learned(c);c.execute(text("INSERT INTO teaching_exposures VALUES('i want to rest','some-old-example',:t,'test')"),dict(t=self.stamp.isoformat()));self.fill(c)
   self.assertFalse(c.execute(text("SELECT 1 FROM composition_items i JOIN knowledge k ON k.id=i.knowledge_id WHERE i.goal_id='want-to' AND k.answer='I want to rest.'")).first())
 def test_generated_question_enters_normal_scheduler_without_answer_or_extra_quota(self):
  with patch.object(comp,'RULES',self.small_rules()):
   with self.db.begin() as c:
    self.learned(c);self.fill(c)
    c.execute(text("UPDATE progress SET introduced=1,level=3,due_at=:d WHERE knowledge_id IN (SELECT knowledge_id FROM curriculum_lessons WHERE goal_id='want-to' AND role='transfer' AND knowledge_id NOT IN (SELECT knowledge_id FROM composition_items))"),dict(d=(self.stamp+timedelta(days=10)).isoformat()))
    item,_=groups.step(c,'want-to',self.stamp);self.assertTrue(item['id'].startswith('auto-transfer-'));self.assertTrue(groups.requirements_met(c,item['id'],stamp=self.stamp))
    self.assertTrue(groups.admit(c,'want-to','want-to',self.stamp,0,50))
   q=app.next_question();self.assertEqual(q.get('id'),item['id']);self.assertEqual(q['exercise_mode'],'transfer');self.assertNotIn('answer',q)
   app.submit(app.Submission(question_id=q['question_id'],answer=item['answer'],confidence='clear'))
   exported=app.export()['tables'];self.assertIn('composition_items',exported);self.assertIn('composition_cursors',exported)
   with self.db.connect() as c:self.assertEqual(groups.counts(c,self.stamp),{'review':1})
