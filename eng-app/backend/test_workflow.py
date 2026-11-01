import unittest,tempfile,uuid
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from sqlalchemy import create_engine,text
from fastapi import HTTPException
import app

class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.folder=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.folder.name)/'flow.db'));app.initialize(self.db)
  self.old=app.real_engine;app.real_engine=self.db;self.token=app.testing.set(False)
  self.clock=patch('app.now',return_value=datetime(2026,10,31,8,tzinfo=timezone.utc));self.clock.start()
 def tearDown(self):
  self.clock.stop();app.testing.reset(self.token);app.real_engine=self.old;self.db.dispose();self.folder.cleanup()
 def question(self,kid='want-to'):
  q=str(uuid.uuid4())
  with self.db.begin() as c:
   c.execute(text('INSERT INTO questions VALUES(:q,:k,:t,0)'),dict(q=q,k=kid,t=app.now().isoformat()))
   c.execute(text('UPDATE progress SET introduced=1 WHERE knowledge_id=:k'),dict(k=kid))
  return q
 def submit(self,q,answer='want to',rating='clear'):
  return app.submit(app.Submission(question_id=q,answer=answer,confidence=rating))
 def test_wrong_spelling_cannot_finalize_or_unlock(self):
  q=self.question()
  with self.assertRaises(HTTPException):self.submit(q,'want too')
  with self.db.connect() as c:self.assertEqual(c.execute(text('SELECT COUNT(*) FROM answers')).scalar(),0)
 def test_duplicate_submit_and_prompted_success(self):
  q=self.question();app.reveal(q);self.submit(q);self.submit(q)
  with self.db.connect() as c:
   self.assertEqual(c.execute(text('SELECT COUNT(*) FROM answers')).scalar(),1)
   self.assertLess(c.execute(text("SELECT level FROM progress WHERE knowledge_id='want-to'")).scalar(),3)
 def test_check_failure_then_correction_not_independent(self):
  q=self.question()
  app.check_spelling(app.SpellingCheck(id=str(uuid.uuid4()),question_id=q,answer='want too'))
  self.submit(q)
  with self.db.connect() as c:self.assertEqual(c.execute(text("SELECT streak FROM progress WHERE knowledge_id='want-to'")).scalar(),0)
 def test_feedback_correction_preserves_count_and_changes_gap(self):
  q=self.question();self.submit(q)
  app.feedback(app.Feedback(question_id=q,confidence='forgot'))
  with self.db.connect() as c:
   self.assertEqual(c.execute(text("SELECT gap FROM review_queue WHERE knowledge_id='want-to'")).scalar(),2)
   self.assertEqual(c.execute(text("SELECT attempts FROM progress WHERE knowledge_id='want-to'")).scalar(),1)
  self.assertEqual(app.recent_history('want-to')[0]['confidence'],'forgot')
 def test_pending_unfinished_not_editable_as_completed(self):
  with self.assertRaises(HTTPException):app.feedback(app.Feedback(question_id=self.question(),confidence='clear'))
 def test_composition_feedback_updates_rule_evidence_both_ways(self):
  q=self.question('compose-want-to-drink-water');self.submit(q,'I want to drink water.','forgot')
  self.assertEqual(app.rule_profile('want-to')['independent_uses'],0)
  app.feedback(app.Feedback(question_id=q,confidence='clear'))
  self.assertEqual(app.rule_profile('want-to')['independent_uses'],1)
  app.feedback(app.Feedback(question_id=q,confidence='hard'))
  self.assertEqual(app.rule_profile('want-to')['independent_uses'],0)
 def test_missed_days_keep_due_items_without_fabricated_answers(self):
  q=self.question();self.submit(q)
  with self.db.begin() as c:
   due=(app.now()+timedelta(days=1)).isoformat()
   c.execute(text("UPDATE review_queue SET due_at=:t WHERE knowledge_id='want-to'"),dict(t=due))
   c.execute(text("UPDATE progress SET due_at=:t WHERE knowledge_id='want-to'"),dict(t=due))
  with patch('app.now',return_value=app.now()+timedelta(days=4)):
   self.assertEqual(app.next_question()['id'],'want-to')
   with self.db.connect() as c:self.assertEqual(c.execute(text('SELECT COUNT(*) FROM answers')).scalar(),1)
 def test_composition_admission_only_counts_actual_question(self):
  future=(app.now()+timedelta(days=100)).isoformat()
  with self.db.begin() as c:
   c.execute(text('UPDATE progress SET introduced=1,level=5,due_at=:d'),dict(d=future))
   c.execute(text("UPDATE progress SET introduced=0,level=0,due_at=NULL WHERE knowledge_id LIKE 'compose-%'"))
  app.save_settings({'daily-new-limit':1,'daily-review-limit':0})
  q=app.next_question();self.assertTrue(q['id'].startswith('compose-'))
  with self.db.connect() as c:
   slots=c.execute(text('SELECT knowledge_id FROM daily_tasks')).scalars().all()
   self.assertEqual(slots,[q['id']])
   answer=c.execute(text('SELECT answer FROM knowledge WHERE id=:k'),dict(k=q['id'])).scalar()
  self.submit(q['question_id'],answer)
  next_q=app.next_question();self.assertEqual(next_q['kind'],'done')
 def test_skip_test_does_not_create_coverage_or_rule_mastery(self):
  previous=app.test_engine;app.test_engine=self.db;token=app.testing.set(True)
  try:
   q=self.question('compose-want-to-drink-water');app.skip_test_question(q)
   with self.db.connect() as c:
    self.assertEqual(c.execute(text('SELECT COUNT(*) FROM daily_coverage')).scalar(),0)
    self.assertEqual(c.execute(text('SELECT SUM(independent) FROM composition_evidence')).scalar(),0)
   self.assertEqual(app.rule_profile('want-to')['independent_uses'],0)
  finally:app.testing.reset(token);app.test_engine=previous
 def test_export_contains_more_than_100_records(self):
  with self.db.begin() as c:
   for n in range(105):c.execute(text("INSERT INTO answers VALUES(:q,:q,'want-to','want to',1,0,'clear',:t,NULL,'')"),dict(q=str(n),t=app.now().isoformat()))
  self.assertEqual(len(app.export()['tables']['answers']),105)
 def test_data_restores_after_engine_reconnect(self):
  q=self.question();self.submit(q)
  self.db.dispose()
  self.assertEqual(app.recent_history('want-to')[0]['question_id'],q)
 def test_concurrent_duplicate_submit_only_counts_once(self):
  from concurrent.futures import ThreadPoolExecutor
  q=self.question()
  with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(lambda _:self.submit(q),range(12)))
  with self.db.connect() as c:
   self.assertEqual(c.execute(text('SELECT COUNT(*) FROM answers')).scalar(),1)
   self.assertEqual(c.execute(text("SELECT attempts FROM progress WHERE knowledge_id='want-to'")).scalar(),1)
 def test_feedback_replay_keeps_unstable_interval_capped(self):
  start=app.now()
  for day in (0,1,3,5):
   with patch('app.now',return_value=start+timedelta(days=day)):
    q=self.question();self.submit(q)
  with patch('app.now',return_value=start+timedelta(days=6)):
   app.feedback(app.Feedback(question_id=q,confidence='clear'))
  with self.db.connect() as c:
   row=c.execute(text("SELECT interval_days,due_at FROM progress WHERE knowledge_id='want-to'")).mappings().one()
   self.assertEqual(row['interval_days'],7)
   self.assertEqual(row['due_at'],(start+timedelta(days=12)).isoformat())


 def test_memory_history_last_feedback_per_learning_day(self):
  from datetime import datetime,timezone
  times=['2026-10-30T15:00:00+00:00','2026-10-30T16:01:00+00:00','2026-10-30T17:00:00+00:00','2026-11-02T08:00:00+00:00','2026-11-06T08:00:00+00:00']
  with self.db.begin() as c:
   for i,t in enumerate(times):
    c.execute(text("INSERT INTO answers(id,question_id,knowledge_id,correct,revealed,confidence,created_at) VALUES(:i,:i,'want-to',1,0,:r,:t)"),dict(i=str(i),r='forgot' if i==1 else 'clear',t=t))
   c.execute(text("INSERT INTO feedback_events VALUES('f','2','hard','2026-11-07T08:00:00+00:00')"))
  result=app.memory_history('want-to')
  self.assertEqual(result['count'],5)
  self.assertEqual([x['day'] for x in result['tags']],[2,4,8])
  self.assertEqual([x['confidence'] for x in result['tags']],['hard','clear','clear'])

 def test_history_explains_question_gap_and_actual_calendar_schedule(self):
  q=self.question();self.submit(q,rating='hard')
  history=app.memory_history('want-to')
  self.assertIsNone(history['due_at'])
  self.assertEqual(history['remaining_questions'],4)
  self.assertTrue(history['schedule_note'])
  for _ in range(3):q=self.question();self.submit(q)
  history=app.memory_history('want-to')
  self.assertIsNotNone(history['due_at'])
  self.assertIn('2026-11-01 16:00',history['plan'])
  self.assertEqual(history['schedule_note'],'')

 def test_normal_context_round_rotates_without_blocking_daily_learning(self):
  import context_engine
  with self.db.begin() as c:
   c.execute(text('INSERT INTO context_rounds(created_at) VALUES(:t)'),dict(t=app.now().isoformat()))
   round_id=c.execute(text('SELECT MAX(id) FROM context_rounds')).scalar()
   ids=c.execute(text("SELECT id FROM knowledge WHERE id LIKE 'compose-%' LIMIT 5")).scalars().all()
   for k in ids:c.execute(text('INSERT INTO context_round_items VALUES(:r,:k)'),dict(r=round_id,k=k))
   context_engine.pick(c,app.now())
   self.assertEqual(c.execute(text('SELECT COUNT(*) FROM context_rounds')).scalar(),2)

 def test_resumed_yesterday_question_occupies_today_review_slot(self):
  q=self.question()
  with patch('app.now',return_value=app.now()+timedelta(days=1)):
   result=app.next_question();self.assertEqual(result['question_id'],q)
   with self.db.connect() as c:
    rows=c.execute(text("SELECT kind FROM daily_tasks WHERE day='2026-11-01' AND knowledge_id='want-to'")).scalars().all()
    self.assertEqual(rows,['review'])
