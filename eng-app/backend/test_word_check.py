import tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import create_engine,text
import app

class WordCheckTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.tmp.name)/'word.db'));app.initialize(self.db,with_bulk=False)
  self.ep=patch.object(app,'real_engine',self.db);self.ep.start()
 def tearDown(self):self.ep.stop();self.db.dispose();self.tmp.cleanup()
 def question(self,kid='want-to'):
  q=str(uuid.uuid4())
  with self.db.begin() as c:c.execute(text('INSERT INTO questions VALUES(:q,:k,:t,0)'),dict(q=q,k=kid,t=app.now().isoformat()))
  return q
 def check(self,q,answer,index):return app.check_word(app.WordCheck(id=str(uuid.uuid4()),question_id=q,answer=answer,word_index=index))
 def test_correct_word_does_not_reveal_answer_or_finish_question(self):
  q=self.question();r=self.check(q,'WANT',0)
  self.assertTrue(r['correct']);self.assertFalse(r['complete']);self.assertNotIn('answer',r)
  self.assertEqual(r['answer_shapes'],[[4,2]])
  with self.db.connect() as c:self.assertEqual(c.execute(text('SELECT COUNT(*) FROM answers')).scalar(),0)
 def test_incomplete_word_is_not_an_error(self):
  q=self.question();r=self.check(q,'wan',0);self.assertTrue(r['pending']);self.assertFalse(r['correct'])
  with self.db.connect() as c:self.assertEqual(c.execute(text('SELECT COUNT(*) FROM spelling_checks')).scalar(),0)
 def test_self_correction_is_independent_without_hint(self):
  q=self.question();self.assertFalse(self.check(q,'wont',0)['correct']);self.assertTrue(self.check(q,'want to',1)['complete'])
  app.submit(app.Submission(question_id=q,answer='want to',confidence='clear'))
  with self.db.connect() as c:self.assertEqual(app.assessment.calculate(c,'want-to')['independent_successes'],1)
  with self.db.connect() as c:
   self.assertEqual(c.execute(text('SELECT COUNT(*) FROM spelling_checks WHERE correct=0')).scalar(),0)
   self.assertEqual(c.execute(text('SELECT correction_count FROM input_corrections WHERE question_id=:q'),dict(q=q)).scalar(),1)
 def test_hint_still_blocks_independent_success(self):
  q=self.question();self.check(q,'wont',0)
  with self.db.begin() as c:c.execute(text('UPDATE questions SET revealed=1 WHERE id=:q'),dict(q=q))
  app.submit(app.Submission(question_id=q,answer='want to',confidence='clear'))
  with self.db.connect() as c:self.assertEqual(app.assessment.calculate(c,'want-to')['independent_successes'],0)
 def test_cannot_skip_an_incorrect_previous_word(self):
  self.assertFalse(self.check(self.question(),'wrong to',1)['correct'])
 def test_alternative_word_lengths_and_complete_sentence(self):
  q=self.question('want-to-transfer-eat');self.assertTrue(self.check(q,'I want to hav',3)['pending'])
  r=self.check(q,'I want to have',3);self.assertTrue(r['correct']);self.assertFalse(r['complete'])
  self.assertEqual(r['answer_shapes'],[[1,4,2,4,1,4]])
  self.assertTrue(self.check(q,'i want to have a meal.',5)['complete'])
