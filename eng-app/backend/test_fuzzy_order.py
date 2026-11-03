"""Narrow regressions for interleaving; isolated data, no simulated real history."""
import tempfile,unittest,uuid
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from sqlalchemy import create_engine,text
import app,focus_training,group_learning as groups

class FuzzyOrderTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.tmp.name)/'order.db'))
  app.initialize(self.db,with_bulk=False);self.clock=datetime(2026,11,3,8,tzinfo=timezone.utc)
  self.ep=patch.object(app,'real_engine',self.db);self.ep.start();self.tp=patch('app.now',return_value=self.clock);self.tp.start()
 def tearDown(self):self.tp.stop();self.ep.stop();self.db.dispose();self.tmp.cleanup()
 def prepare(self,count):
  with self.db.begin() as c:
   for n in range(count):
    kid='order-'+str(n);answer='sample'+chr(97+n)
    c.execute(text('INSERT INTO knowledge VALUES(:k,:a,:a,:a,:a)'),dict(k=kid,a=answer))
    c.execute(text('INSERT INTO progress(knowledge_id,introduced,level,due_at) VALUES(:k,1,2,:t)'),dict(k=kid,t=self.clock.isoformat()))
    c.execute(text("INSERT INTO learning_groups VALUES(:k,:k,:k,'word')"),dict(k=kid))
    c.execute(text("INSERT INTO group_members VALUES(:k,:k,'word',0)"),dict(k=kid))
    c.execute(text('INSERT INTO group_primary VALUES(:k,:k)'),dict(k=kid))
  app.save_settings({'daily-new-limit':0,'daily-review-limit':count})
 def answer(self,q,rating='hard',wrong=False):
  if wrong:app.check_spelling(app.SpellingCheck(id=str(uuid.uuid4()),question_id=q['question_id'],answer='wrong'))
  return app.submit(app.Submission(question_id=q['question_id'],answer=app.knowledge_content(q['id'])['answer'],confidence=rating))
 def test_four_other_items_before_fuzzy_returns_when_available(self):
  self.prepare(5);first=app.next_question();self.answer(first)
  others=[]
  for _ in range(4):
   q=app.next_question();self.assertNotEqual(q['id'],first['id']);others.append(q['id']);self.answer(q,'clear')
  self.assertEqual(len(set(others)),4);self.assertEqual(app.next_question()['id'],first['id'])
  with self.db.connect() as c:self.assertEqual(groups.counts(c,self.clock),{'review':5})
 def test_small_pool_rotates_instead_of_adjacent_repeat(self):
  self.prepare(2);seen=[]
  for _ in range(6):
   q=app.next_question();seen.append(q['id']);self.answer(q)
  self.assertTrue(all(a!=b for a,b in zip(seen,seen[1:])))
  with self.db.connect() as c:
   self.assertEqual(groups.counts(c,self.clock),{'review':2})
   self.assertLess(c.execute(text("SELECT MAX(level) FROM progress WHERE knowledge_id LIKE 'order-%'")).scalar(),3)
 def test_single_item_pauses_without_finishing_and_can_resume(self):
  self.prepare(1);q=app.next_question();saved=self.answer(q)
  with self.db.connect() as c:before=c.execute(text('SELECT * FROM memory_states')).all()
  paused=app.next_question();self.assertEqual(paused['reason'],'interleaving-needed')
  with self.db.connect() as c:
   self.assertEqual(c.execute(text('SELECT * FROM memory_states')).all(),before)
   self.assertEqual(c.execute(text('SELECT due_at FROM group_progress WHERE group_id=:g'),dict(g=q['group_id'])).scalar(),None)
   self.assertEqual(c.execute(text('SELECT due_at FROM answers WHERE question_id=:q'),dict(q=q['question_id'])).scalar(),saved['due_at'])
  resumed=app.next_question(allow_repeat=True);self.assertEqual(resumed['id'],q['id'])
  self.assertEqual(app.next_question()['question_id'],resumed['question_id'])
 def test_forgotten_and_actual_spelling_error_keep_repair(self):
  self.prepare(1);q=app.next_question();self.answer(q,'forgot');q2=app.next_question();self.assertEqual(q2['id'],q['id'])
  self.answer(q2,'hard',wrong=True);self.assertEqual(app.next_question()['id'],q['id'])
 def test_focus_uses_another_request_before_repeating(self):
  self.prepare(2)
  with self.db.begin() as c:
   for n in range(2):focus_training.add(c,'order-'+str(n),self.clock,member_ids=['order-'+str(n)])
  first=app.next_question();self.answer(first);self.assertNotEqual(app.next_question()['id'],first['id'])
 def test_no_avoidance_carried_into_tomorrow(self):
  self.prepare(1);q=app.next_question();self.answer(q)
  with self.db.connect() as c:self.assertIsNone(groups.recent_fuzzy(c,self.clock+timedelta(days=1)))

 def test_duplicate_english_does_not_count_as_another_item(self):
  self.prepare(2)
  with self.db.begin() as c:c.execute(text("UPDATE knowledge SET answer='SAMPLEA.' WHERE id='order-1'"))
  q=app.next_question();self.answer(q)
  self.assertEqual(app.next_question()['reason'],'interleaving-needed')

 def test_forgotten_rotates_when_another_item_exists(self):
  self.prepare(2)
  with self.db.begin() as c:app.sourced_transfer.activate(c)
  first=app.next_question();self.answer(first,'forgot')
  self.assertNotEqual(app.next_question()['id'],first['id'])

 def test_pilot_single_forgotten_item_pauses_without_faking_mastery(self):
  self.prepare(1)
  with self.db.begin() as c:app.sourced_transfer.activate(c)
  q=app.next_question();self.answer(q,'forgot')
  self.assertEqual(app.next_question()['reason'],'interleaving-needed')
  self.assertEqual(app.next_question(allow_repeat=True)['id'],q['id'])
