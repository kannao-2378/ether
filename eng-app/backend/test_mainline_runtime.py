import json,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,text
import app,content,curriculum_engine as ce,mainline_runtime as mainline,selection_cache

TABLES=('answers','feedback_events','progress','memory_states','questions','spelling_checks','review_queue')

def snapshot(c):return {t:[tuple(r) for r in c.execute(text('SELECT * FROM '+t))] for t in TABLES}

class ProductionMainlineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.tmp.name)/'learning.db'))
  app.initialize(self.db,with_bulk=False)
  self.ep=patch.object(app,'real_engine',self.db);self.ep.start();self.client=TestClient(app.app)
 def tearDown(self):self.client.close();self.ep.stop();self.db.dispose();self.tmp.cleanup()
 def seed(self):
  q=self.client.post('/api/challenge/word-i',json={}).json()
  r=self.client.post('/api/check',json=dict(id=str(uuid.uuid4()),question_id=q['question_id'],answer='I'));self.assertTrue(r.json()['correct'])
  r=self.client.post('/api/answers',json=dict(question_id=q['question_id'],answer='I',confidence='hard'));self.assertEqual(r.status_code,200,r.text)
  with self.db.connect() as c:return snapshot(c),dict(c.execute(text('SELECT * FROM group_primary')).all())
 def assert_preserved(self,c,before,owners):
  after=snapshot(c)
  for t,rows in before.items():self.assertTrue(set(rows)<=set(after[t]),t)
  current=dict(c.execute(text('SELECT * FROM group_primary')).all())
  self.assertTrue(all(current[k]==v for k,v in owners.items()))
 def test_real_history_ownership_pending_and_memory_preserved(self):
  before,owners=self.seed()
  with self.db.begin() as c:
   mainline.install(c);self.assert_preserved(c,before,owners)
   self.assertEqual(ce.report(c,mainline.COURSE)['ready_total'],148)
   self.assertEqual(mainline.status(c)['topics'],148)
   self.assertEqual(json.loads(c.execute(text("SELECT value FROM app_settings WHERE key='active-course'")).scalar()),mainline.COURSE)
   self.assertEqual(next(x for x in content.curriculum(c,False) if x['id']==mainline.COURSE)['total'],148)
   self.assertEqual(c.execute(text("SELECT count(*) FROM progress WHERE knowledge_id LIKE 'mainline-%' AND (introduced=1 OR attempts>0 OR level>0)")).scalar(),0)
 def test_restart_is_idempotent_and_respects_later_course_choice(self):
  before,owners=self.seed()
  with self.db.begin() as c:
   mainline.install(c);count=c.execute(text('SELECT count(*) FROM knowledge')).scalar()
   c.execute(text("UPDATE app_settings SET value='\"foundation\"' WHERE key='active-course'"))
  with patch.dict('os.environ',{'PELS_MAINLINE_ENABLED':'1'}):app.initialize(self.db,with_bulk=False)
  with self.db.connect() as c:
   self.assert_preserved(c,before,owners)
   self.assertEqual(c.execute(text('SELECT count(*) FROM knowledge')).scalar(),count)
   self.assertEqual(json.loads(c.execute(text("SELECT value FROM app_settings WHERE key='active-course'")).scalar()),'foundation')
 def test_wrong_sense_cannot_borrow_old_mastery(self):
  with self.db.begin() as c:
   ce.card(c,'wrong-sense','I am','并非此课程含义','独立测试','I am','独立测试','phrase')
   c.execute(text("UPDATE progress SET introduced=1,level=3 WHERE knowledge_id='wrong-sense'"))
   mainline.install(c)
   self.assertFalse(c.execute(text("SELECT 1 FROM curriculum_aliases WHERE knowledge_id='mainline-U01-2' AND alias_id='wrong-sense'")).first())
 def test_selected_course_really_reaches_today_learning(self):
  with self.db.begin() as c:mainline.install(c)
  selection_cache.invalidate()
  plan=self.client.get('/api/plan').json();self.assertEqual(plan['route']['ready_total'],148)
  q=self.client.post('/api/next',json={});self.assertEqual(q.status_code,200,q.text)
  item=q.json();self.assertNotEqual(item['kind'],'done')
  with self.db.connect() as c:
   self.assertTrue(c.execute(text('SELECT 1 FROM curriculum_lessons l JOIN curriculum_paths p ON p.goal_id=l.goal_id WHERE l.knowledge_id=:k AND p.course_id=:c'),dict(k=item['id'],c=mainline.COURSE)).first())
 def test_new_cards_reuse_syllables_without_touching_progress(self):
  with self.db.begin() as c:
   mainline.install(c)
   rows=c.execute(text("SELECT k.answer,d.payload FROM curriculum_lessons l JOIN knowledge k ON k.id=l.knowledge_id JOIN knowledge_details d ON d.knowledge_id=k.id WHERE l.goal_id='mainline-U02-1'")).all()
   phonetic={en:json.loads(raw) for en,raw in rows}
   self.assertTrue(phonetic['water']['ipa_us']);self.assertTrue(phonetic['water']['syllables'])
   self.assertTrue(phonetic['drink water']['pronunciation_parts'])
   before=snapshot(c);mainline.install(c)
   self.assertEqual(before,snapshot(c))

if __name__=='__main__':unittest.main()
