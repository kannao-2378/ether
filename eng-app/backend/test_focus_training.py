import unittest,tempfile,uuid
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from sqlalchemy import create_engine,text
import app,focus_training as focus
class FocusTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.tmp.name)/'test.db'));app.initialize(self.db)
  self.clock=datetime(2026,11,1,8,tzinfo=timezone.utc);self.ep=patch.object(app,'real_engine',self.db);self.ep.start();self.tp=patch('app.now',side_effect=lambda:self.clock);self.tp.start()
  app.save_settings({'daily-new-limit':0,'daily-review-limit':0})
 def tearDown(self):self.tp.stop();self.ep.stop();self.db.dispose();self.tmp.cleanup()
 def question(self):
  q=app.next_question()
  if q['kind']=='learn':app.introduce(q['id']);q=app.next_question()
  return q
 def answer(self,q,rating='clear'):
  return app.submit(app.Submission(question_id=q['question_id'],answer=app.knowledge_content(q['id'])['answer'],confidence=rating))
 def test_practical_full_batch_works_above_daily_cap_without_faking_records(self):
  info=app.focus_info('word-practical');self.assertEqual(len(info['items']),6)
  first=app.add_focus('word-practical');again=app.add_focus('word-practical');self.assertEqual(first['id'],again['id'])
  with self.db.connect() as c:self.assertEqual(c.execute(text("SELECT attempts FROM progress WHERE knowledge_id='word-practical'")).scalar(),0)
  seen=[]
  for _ in range(12):
   q=self.question()
   if q['kind']=='done':break
   self.assertTrue(q['group_id'].startswith('focus-'));seen.append(q['id']);self.answer(q)
  self.assertEqual(len(seen),6);self.assertEqual(len(set(seen)),6)
  with self.db.connect() as c:
   self.assertEqual(c.execute(text('SELECT status FROM focus_requests')).scalar(),'completed')
   self.assertEqual(c.execute(text("SELECT COUNT(*) FROM daily_group_tasks WHERE kind IN ('new','review')")).scalar(),0)
   self.assertEqual(c.execute(text('SELECT COUNT(*) FROM answers')).scalar(),6)
  self.assertEqual(app.daily_activity_report()['special'],1)
 def test_known_word_is_still_tested_and_errors_dont_advance(self):
  with self.db.begin() as c:c.execute(text("UPDATE progress SET introduced=1,level=5 WHERE knowledge_id='word-practical'"))
  app.add_focus('word-practical');q=self.question();self.assertEqual(q['id'],'word-practical');self.answer(q,'forgot')
  q=self.question();self.assertEqual(q['id'],'word-practical');self.answer(q,'clear');self.assertNotEqual(self.question()['id'],'word-practical')
 def test_cancel_never_resumes_abandoned_focus_question(self):
  job=app.add_focus('word-practical');q=self.question();app.cancel_focus(job['id']);self.assertEqual(app.next_question()['kind'],'done')
  with self.db.connect() as c:self.assertEqual(c.execute(text('SELECT COUNT(*) FROM answers')).scalar(),0)
 def test_restart_and_cross_day_preserve_batch_progress(self):
  job=app.add_focus('word-practical');q=self.question();self.answer(q);self.clock+=timedelta(days=1);app.initialize(self.db)
  q=self.question();self.assertNotEqual(q['id'],'word-practical');self.assertEqual(q['group_id'],job['id'])
 def test_hint_and_spelling_failure_need_fresh_independent_attempt(self):
  app.add_focus('word-practical');q=self.question();app.reveal(q['question_id']);self.answer(q);self.assertEqual(self.question()['id'],'word-practical')
 def test_regular_pending_question_is_preserved_and_single_entry_fallback(self):
  app.save_settings({'daily-new-limit':1,'daily-review-limit':0});normal=self.question();app.add_focus('word-practical');self.assertTrue(self.question()['group_id'].startswith('focus-'))
  with self.db.connect() as c:self.assertEqual(c.execute(text('SELECT COUNT(*) FROM questions WHERE id=:q'),dict(q=normal['question_id'])).scalar(),1)
  with self.assertRaises(app.HTTPException):app.add_focus('not-a-real-word')
 def test_pool_limit_queues_without_exceeding_twelve(self):
  with self.db.begin() as c:
   for i in range(12):c.execute(text('INSERT INTO group_active_slots VALUES(:g,:t)'),dict(g='occupied'+str(i),t=self.clock.isoformat()))
  job=app.add_focus('word-practical');self.assertEqual(app.next_question()['kind'],'done')
  with self.db.connect() as c:self.assertEqual(c.execute(text('SELECT COUNT(*) FROM group_active_slots')).scalar(),12)

 def test_completed_batch_reopens_after_feedback_correction(self):
  app.add_focus('word-practical');questions=[]
  for _ in range(6):q=self.question();questions.append(q);self.answer(q)
  app.feedback(app.Feedback(question_id=questions[-1]['question_id'],confidence='forgot'))
  self.assertEqual(self.question()['id'],questions[-1]['id'])
 def test_test_database_can_use_focus_queue(self):
  token=app.testing.set(True)
  try:
   with self.db.begin() as c:
    c.execute(text('CREATE TABLE IF NOT EXISTS test_clock(id INTEGER PRIMARY KEY,days INTEGER,stage INTEGER)'));c.execute(text('INSERT OR IGNORE INTO test_clock VALUES(1,0,NULL)'))
   with patch.object(app,'test_engine',self.db):
    app.add_focus('word-practical');q=self.question();self.answer(q);self.assertNotEqual(self.question()['id'],'word-practical')
  finally:app.testing.reset(token)

 def test_single_entry_fallback_and_ordinary_records_survive(self):
  with self.db.begin() as c:
   c.execute(text("INSERT INTO knowledge VALUES('lonely','罕见测试词','uniquetesttoken','仅测试','uniquetesttoken')"));c.execute(text("INSERT INTO progress(knowledge_id) VALUES('lonely')"))
  info=app.focus_info('lonely');self.assertEqual(len(info['items']),1);app.add_focus('lonely');q=self.question();self.assertEqual(q['id'],'lonely');self.answer(q);self.assertEqual(app.next_question()['kind'],'done')
