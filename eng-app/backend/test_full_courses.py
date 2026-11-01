import unittest,tempfile,shutil,json
from pathlib import Path
from datetime import timedelta
from sqlalchemy import create_engine,text
import app,bulk_courses,content,transfer

class FullCourseTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=tempfile.TemporaryDirectory();cls.base=Path(cls.folder.name)/'base.db';engine=create_engine('sqlite:///'+str(cls.base));app.initialize(engine,with_bulk=True);engine.dispose()
 @classmethod
 def tearDownClass(cls):cls.folder.cleanup()
 def setUp(self):
  self.case=tempfile.TemporaryDirectory();self.path=Path(self.case.name)/'case.db';shutil.copyfile(self.base,self.path);self.engine=create_engine('sqlite:///'+str(self.path));self.old=app.real_engine;app.real_engine=self.engine;self.token=app.testing.set(False)
 def tearDown(self):app.testing.reset(self.token);app.real_engine=self.old;self.engine.dispose();self.case.cleanup()
 def test_3000_distinct_attested_expressions(self):
  data=json.loads(bulk_courses.PACK.read_text(encoding='utf-8'))
  self.assertEqual(len({r['answer'].casefold() for r in data['expressions']}),3000)
  for r in data['expressions']:
   self.assertTrue(r['details']['examples'])
   for e in r['details']['examples']:self.assertIn(r['answer'],e['en'].lower());self.assertTrue(e['zh']);self.assertTrue(e['source_url']);self.assertTrue(e['translation_url'])
  with self.engine.connect() as c:self.assertEqual(c.execute(text("SELECT COUNT(*) FROM package_members WHERE kind='expression'")).scalar(),3000)
 def test_metadata_types_and_pronunciation_are_not_faked(self):
  result=app.dictionary(kind='word');self.assertGreater(result['total'],3000);self.assertTrue(all(r['entry_type']=='word' for r in result['items']))
  with self.engine.connect() as c:
   raw=c.execute(text("SELECT payload FROM knowledge_details WHERE knowledge_id LIKE 'lex-%' LIMIT 1")).scalar();d=json.loads(raw)
   self.assertTrue(d['pos']);self.assertTrue(d['examples'][0]['zh']);self.assertIn('词性取本课例句',d['review_status'])
 def test_curriculum_is_summary_only_and_units_paginate(self):
  plan=app.learning_plan();self.assertEqual(len(plan['curriculum']),12)
  self.assertEqual(sum(len(c['units']) for c in plan['curriculum']),229)
  for c in plan['curriculum']:
   for u in c['units']:self.assertNotIn('items',u)
  unit=max((u for c in plan['curriculum'] for u in c['units']),key=lambda u:u['total'])
  page=app.curriculum_unit(unit['id']);self.assertEqual(len(page['items']),min(100,unit['total']));self.assertLessEqual(len(page['items']),100)
  self.assertEqual(app.curriculum_unit(unit['id'],page=999)['items'],[])
 def test_course_choice_includes_required_base_without_reset(self):
  app.save_settings({'active-course':'course-finance'})
  q=app.next_question()
  with self.engine.connect() as c:
   self.assertTrue(c.execute(text("SELECT 1 FROM course_items ci JOIN course_units cu ON cu.id=ci.unit_id JOIN group_members gm ON gm.knowledge_id=ci.knowledge_id WHERE cu.course_id='course-finance' AND gm.group_id=:g"),dict(g=q['group_id'])).first())
 def test_reimport_preserves_answers_and_progress(self):
  with self.engine.begin() as c:c.execute(text("UPDATE progress SET attempts=12,level=3 WHERE knowledge_id='want-to'"))
  with self.engine.begin() as c:
   count=c.execute(text('SELECT COUNT(*) FROM knowledge')).scalar();bulk_courses.install(c);content.install(c)
   self.assertEqual(c.execute(text('SELECT COUNT(*) FROM knowledge')).scalar(),count)
   self.assertEqual(c.execute(text("SELECT attempts FROM progress WHERE knowledge_id='want-to'")).scalar(),12)
 def test_source_answer_sets_still_require_target_structure(self):
  data=json.loads(bulk_courses.PACK.read_text(encoding='utf-8'))
  row=next(r for r in data['sentences'] if len(r['details'].get('accepted_answers',[]))>1)
  for answer in row['details']['accepted_answers']:self.assertIn(row['details']['structure'],answer.lower());self.assertTrue(transfer.grade(row['id'],answer.lower(),row['answer'],row['details']['accepted_answers'])['correct'])
  self.assertFalse(transfer.grade(row['id'],'unrelated answer',row['answer'],row['details']['accepted_answers'])['correct'])

if __name__=='__main__':unittest.main()
