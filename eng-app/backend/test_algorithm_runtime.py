"""Runtime evidence: isolated databases, FSRS oracle, restart and overdue scenarios."""
import unittest,tempfile,uuid,json,random
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from sqlalchemy import create_engine,text
from fsrs import Card,Rating
import app
from scheduler import rebuild,select_next,FSRS

class AlgorithmRuntimeTests(unittest.TestCase):
 def setUp(self):
  self.folder=tempfile.TemporaryDirectory();self.path=Path(self.folder.name)/'audit.db'
  self.db=create_engine('sqlite:///'+str(self.path));app.initialize(self.db)
  self.old=app.real_engine;app.real_engine=self.db;self.token=app.testing.set(False)
  self.start=datetime(2026,1,1,8,tzinfo=timezone.utc)
 def tearDown(self):
  app.real_engine=self.old;app.testing.reset(self.token);self.db.dispose();self.folder.cleanup()
 def answer(self,at,rating='clear',hint=False,wrong=False):
  q=str(uuid.uuid4())
  with patch('app.now',return_value=at):
   with self.db.begin() as c:
    c.execute(text("INSERT INTO questions VALUES(:q,'want-to',:t,0)"),dict(q=q,t=at.isoformat()))
    c.execute(text("UPDATE progress SET introduced=1 WHERE knowledge_id='want-to'"))
   if hint:app.reveal(q)
   if wrong:app.check_spelling(app.SpellingCheck(id=str(uuid.uuid4()),question_id=q,answer='want too'))
   result=app.submit(app.Submission(question_id=q,answer='want to',confidence=rating))
  return q,result
 def test_sixty_day_actual_workflow_restart_and_due_selection(self):
  for _ in range(3):q,result=self.answer(self.start)
  self.assertEqual(result['due_at'],(self.start+timedelta(days=1)).isoformat())
  intervals=[]
  for _ in range(8):
   at=datetime.fromisoformat(result['due_at'])
   q,result=self.answer(at)
   with self.db.connect() as c:
    p=c.execute(text("SELECT * FROM progress WHERE knowledge_id='want-to'")).mappings().one()
    a=c.execute(text('SELECT due_at FROM answers WHERE question_id=:q'),dict(q=q)).scalar()
   self.assertEqual(a,result['due_at']);self.assertGreater(datetime.fromisoformat(a),at)
   self.assertLessEqual(p['interval_days'],180);intervals.append(p['interval_days'])
  self.assertGreater(max(intervals),7)
  due=datetime.fromisoformat(result['due_at']);self.db.dispose()
  with self.db.begin() as c:
   self.assertEqual(select_next(c,due-timedelta(seconds=1),50,0)[0],'done')
   kind,item=select_next(c,due+timedelta(days=20),50,0)
   self.assertEqual(kind,'recall');self.assertEqual(item['id'],'want-to')
  with self.db.connect() as c:
   before=c.execute(text("SELECT card_json FROM memory_states WHERE knowledge_id='want-to'")).scalar()
  q,result=self.answer(due+timedelta(days=20),rating='forgot')
  self.assertIsNone(result['due_at'])
  with self.db.connect() as c:
   self.assertEqual(c.execute(text("SELECT gap FROM review_queue WHERE knowledge_id='want-to'")).scalar(),2)
   after=c.execute(text("SELECT card_json FROM memory_states WHERE knowledge_id='want-to'")).scalar()
  self.assertLess(json.loads(after)['stability'],json.loads(before)['stability'])
 def test_fsrs_states_match_library_oracle_and_full_replay(self):
  rng=random.Random(309);card=Card(card_id=1);at=self.start
  for n in range(35):
   at+=timedelta(hours=rng.choice([0,2,25,72,240]))
   confidence=rng.choice(['clear','clear','hard','forgot']);hint=n%11==0;wrong=n%13==0
   q,result=self.answer(at,confidence,hint,wrong)
   rating=Rating.Again if hint or wrong or confidence=='forgot' else Rating.Hard if confidence=='hard' else Rating.Good
   card,_=FSRS.review_card(card,rating,review_datetime=at)
   with self.db.begin() as c:
    raw=c.execute(text("SELECT card_json FROM memory_states WHERE knowledge_id='want-to'")).scalar()
    self.assertEqual(json.loads(raw),card.to_dict())
    before=dict(c.execute(text("SELECT * FROM review_queue WHERE knowledge_id='want-to'")).mappings().one())
    rebuild(c,'want-to');app.apply_retention_limit(c,'want-to')
    self.assertEqual(before,dict(c.execute(text("SELECT * FROM review_queue WHERE knowledge_id='want-to'")).mappings().one()))
 def test_skips_do_not_train_memory_even_after_later_real_answer(self):
  self.answer(self.start)
  q,_=self.answer(self.start+timedelta(hours=1))
  with self.db.begin() as c:
   c.execute(text('INSERT INTO test_skips VALUES(:q,:t)'),dict(q=q,t=self.start.isoformat()));rebuild(c,'want-to')
  q,_=self.answer(self.start+timedelta(days=2))
  card=Card(card_id=1)
  for at in [self.start,self.start+timedelta(days=2)]:card,_=FSRS.review_card(card,Rating.Good,review_datetime=at)
  with self.db.connect() as c:
   raw=c.execute(text("SELECT card_json FROM memory_states WHERE knowledge_id='want-to'")).scalar()
  self.assertEqual(json.loads(raw),card.to_dict())
