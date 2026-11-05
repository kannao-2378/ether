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

 def test_three_full_errors_enqueue_only_the_word_after_submission(self):
  q=self.question()
  with self.db.begin() as c:
   c.execute(text("INSERT INTO knowledge VALUES('test-want','想要','want','','')"))
   c.execute(text("INSERT INTO progress(knowledge_id) VALUES('test-want')"))
   c.execute(text('INSERT INTO knowledge_details VALUES(:k,:p,1,:t)'),dict(k='test-want',p='{"entry_type":"word"}',t=app.now().isoformat()))
  for _ in range(3):self.check(q,'wont',0)
  with self.db.connect() as c:
   self.assertEqual(c.execute(text('SELECT error_count FROM word_spelling_difficulties WHERE question_id=:q'),dict(q=q)).scalar(),3)
   self.assertEqual(c.execute(text('SELECT COUNT(*) FROM focus_requests')).scalar(),0)
  app.submit(app.Submission(question_id=q,answer='want to',confidence='clear'))
  with self.db.connect() as c:
   self.assertEqual(app.assessment.calculate(c,'want-to')['independent_successes'],1)
   gid=c.execute(text('SELECT practice_id FROM word_spelling_difficulties WHERE question_id=:q'),dict(q=q)).scalar()
   self.assertTrue(gid)
   self.assertEqual(c.execute(text('SELECT k.answer FROM group_members m JOIN knowledge k ON k.id=m.knowledge_id WHERE m.group_id=:g'),dict(g=gid)).scalars().all(),['want'])

 def test_duplicate_request_and_incomplete_nonprefix_do_not_count(self):
  q=self.question()
  for _ in range(3):app.check_word(app.WordCheck(id='same-request',question_id=q,answer='wont',word_index=0))
  self.check(q,'wo',0)
  with self.db.connect() as c:
   self.assertEqual(c.execute(text('SELECT error_count FROM word_spelling_difficulties WHERE question_id=:q'),dict(q=q)).scalar(),1)

 def test_errors_in_different_word_slots_do_not_add_together(self):
  q=self.question()
  self.check(q,'wont',0);self.check(q,'wont',0);self.check(q,'want tx',1)
  with self.db.connect() as c:
   self.assertEqual(c.execute(text('SELECT error_count FROM word_spelling_difficulties WHERE question_id=:q ORDER BY word_index'),dict(q=q)).scalars().all(),[2,1])
 def test_dictionary_reuses_only_registered_equivalent_evidence(self):
  q=self.question();app.submit(app.Submission(question_id=q,answer='want to',confidence='clear'))
  with self.db.begin() as c:
   c.execute(text("UPDATE progress SET introduced=1 WHERE knowledge_id='want-to'"))
   c.execute(text("INSERT INTO knowledge VALUES('test-equivalent','想要做某事','want to','','')"))
   c.execute(text("INSERT INTO progress(knowledge_id) VALUES('test-equivalent')"))
   c.execute(text("INSERT INTO curriculum_aliases VALUES('test-equivalent','want-to')"))
  rows=app.dictionary(q='want to',status='learned')['items']
  item=next(r for r in rows if r['id']=='test-equivalent')
  self.assertTrue(item['introduced']);self.assertEqual(item['evidence_id'],'want-to')
  self.assertFalse(any(r['id']=='test-equivalent' for r in app.dictionary(q='want to',status='unseen')['items']))
  with self.db.connect() as c:self.assertEqual(c.execute(text("SELECT attempts FROM progress WHERE knowledge_id='test-equivalent'")).scalar(),0)
