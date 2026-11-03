import unittest,tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
from sqlalchemy import create_engine,text
import app,assessment

class AssessmentTests(unittest.TestCase):
 def setUp(self):
  self.folder=tempfile.TemporaryDirectory();self.engine=create_engine('sqlite:///'+str(Path(self.folder.name)/'test.db'));app.initialize(self.engine)
  self.c=self.engine.connect();self.tx=self.c.begin();self.seq=0;self.start=datetime(2026,1,1,tzinfo=timezone.utc)
 def tearDown(self):self.tx.rollback();self.c.close();self.engine.dispose();self.folder.cleanup()
 def answer(self,day=0,kid='want-to',rating='clear',hint=0,skip=False):
  self.seq+=1;q=str(self.seq)
  self.c.execute(text("INSERT INTO answers VALUES(:q,:q,:k,'answer',1,:h,:r,:t,NULL,'')"),dict(q=q,k=kid,h=hint,r=rating,t=(self.start+timedelta(days=day,seconds=self.seq)).isoformat()))
  if kid.startswith('compose-'):self.c.execute(text("INSERT INTO question_trials VALUES(:q,'transfer','isolated genuine trial',2)"),dict(q=q))
  if skip:self.c.execute(text('INSERT INTO test_skips VALUES(:q,:t)'),dict(q=q,t=self.start.isoformat()))
  return q
 def test_same_day_successes_not_stable(self):
  for _ in range(10):self.answer()
  p=assessment.calculate(self.c,'want-to');self.assertFalse(p['stable']);self.assertEqual(p['independent_days'],1)
 def test_transfer_days_use_local_midnight(self):
  self.start=datetime(2026,1,1,15,30,tzinfo=timezone.utc)
  self.answer(kid='compose-want-to-drink-water')
  self.answer(day=1/24,kid='compose-want-to-read-books')
  self.assertEqual(assessment.calculate(self.c,'want-to')['transfer_days'],2)
 def test_spaced_success_and_later_forgotten(self):
  for day in (0,1,8):self.answer(day)
  self.assertTrue(assessment.calculate(self.c,'want-to')['stable'])
  self.answer(9,rating='forgot');p=assessment.calculate(self.c,'want-to');self.assertFalse(p['stable']);self.assertEqual(p['latest_feedback'],'forgot');self.assertEqual(p['independent_successes'],3)
 def test_hints_and_test_skips_do_not_prove_mastery(self):
  self.answer(hint=1);self.answer(1,skip=True)
  self.assertEqual(assessment.calculate(self.c,'want-to')['independent_successes'],0)
 def test_transfer_is_distinct_and_corrections_apply(self):
  q=self.answer(kid='compose-want-to-drink-water')
  self.answer(kid='compose-want-to-learn-english')
  p=assessment.calculate(self.c,'want-to');self.assertEqual(p['transfer_contexts'],2);self.assertFalse(p['stable'])
  self.c.execute(text("INSERT INTO feedback_events VALUES('correction',:q,'hard',:t)"),dict(q=q,t=self.start.isoformat()))
  p=assessment.calculate(self.c,'want-to');self.assertEqual(p['transfer_contexts'],1)
 def test_cached_profile_matches_evidence(self):
  self.answer();assessment.refresh(self.c,'want-to')
  self.assertEqual(assessment.get(self.c,'want-to'),assessment.calculate(self.c,'want-to'))

 def test_transfer_can_be_demonstrated_before_memory_is_stable(self):
  self.answer(kid='compose-want-to-learn-english');self.answer(kid='compose-want-to-read-books')
  e=assessment.calculate(self.c,'want-to')
  self.assertFalse(e['stable']);self.assertTrue(e['transferable']);self.assertEqual(e['transfer_label'],'可迁移')
 def test_stable_memory_does_not_imply_transfer(self):
  for day in (0,1,8):self.answer(day)
  e=assessment.calculate(self.c,'want-to')
  self.assertTrue(e['stable']);self.assertFalse(e['transferable']);self.assertEqual(e['transfer_label'],'未验证')
 def test_one_context_is_only_initial_use_and_hard_can_lower_transfer(self):
  q=self.answer(kid='compose-want-to-learn-english');e=assessment.calculate(self.c,'want-to')
  self.assertEqual(e['transfer_label'],'初步会用');self.assertFalse(e['transferable'])
  self.c.execute(text("INSERT INTO feedback_events VALUES('lower-transfer',:q,'hard',:t)"),dict(q=q,t=self.start.isoformat()))
  self.assertFalse(assessment.calculate(self.c,'want-to')['transferable'])

if __name__=='__main__':unittest.main()
