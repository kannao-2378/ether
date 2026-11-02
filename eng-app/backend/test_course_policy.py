import unittest,tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from sqlalchemy import create_engine,text
import app,group_learning as groups,course_policy
class CoursePolicyTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.tmp.name)/'test.db'));app.initialize(self.db)
  self.clock=datetime(2026,11,2,1,tzinfo=timezone.utc);self.ep=patch.object(app,'real_engine',self.db);self.ep.start();self.tp=patch('app.now',side_effect=lambda:self.clock);self.tp.start()
 def tearDown(self):self.tp.stop();self.ep.stop();self.db.dispose();self.tmp.cleanup()
 def test_sentence_incidental_word_not_forced_before_core(self):
  with self.db.begin() as c:
   c.execute(text("INSERT INTO knowledge VALUES('extra-bathe','洗澡','bathe','洗澡','I bathe every day.')"));c.execute(text("INSERT INTO progress(knowledge_id) VALUES('extra-bathe')"));c.execute(text("INSERT INTO group_members VALUES('every-day','extra-bathe','word',0)"))
   groups.admit(c,'every-day','every-day',self.clock,1,0)
  app.save_settings({'daily-new-limit':1,'daily-review-limit':0})
  self.assertNotEqual(app.next_question().get('id'),'extra-bathe')
 def test_known_root_form_not_taught_as_separate_new_word(self):
  with self.db.begin() as c:
   c.execute(text("UPDATE progress SET introduced=1,level=3 WHERE knowledge_id='word-learn'"))
   c.execute(text("INSERT INTO knowledge VALUES('form-learning','学习','learning','学习','learning English')"));c.execute(text("INSERT INTO progress(knowledge_id) VALUES('form-learning')"));c.execute(text("INSERT INTO group_members VALUES('learn-english','form-learning','word',0)"))
   ids=[r['id'] for r in course_policy.core_members(c,'learn-english',groups.members(c,'learn-english'))]
   self.assertNotIn('form-learning',ids)
 def test_future_known_group_not_retested_for_shared_words(self):
  with self.db.begin() as c:
   c.execute(text('UPDATE progress SET introduced=1,level=3,due_at=:d'),dict(d=(self.clock+timedelta(days=7)).isoformat()))
   item,_=groups.step(c,'listen-to',self.clock)
   self.assertIsNone(item)
 def test_initial_course_starts_with_materials_not_unrelated_example_words(self):
  app.save_settings({'daily-new-limit':50})
  q=app.next_question();self.assertEqual(q['group_id'],'drink-water');self.assertIn(q['id'],['word-drink','word-water','drink-water'])
 def test_three_new_goals_concurrently_not_three_per_day(self):
  app.save_settings({'daily-new-limit':50,'daily-review-limit':0})
  for i in range(12):
   q=app.next_question()
   while q['kind']=='learn':app.introduce(q['id']);q=app.next_question()
   self.assertNotEqual(q['kind'],'done');answer=app.knowledge_content(q['id'])['answer'];app.submit(app.Submission(question_id=q['question_id'],answer=answer,confidence='hard'))
  with self.db.connect() as c:
   self.assertEqual(groups.counts(c,self.clock).get('new'),3);self.assertLessEqual(c.execute(text('SELECT COUNT(*) FROM group_active_slots')).scalar(),12)
 def test_shared_word_review_only_in_primary_owner(self):
  with self.db.connect() as c:
   owner=groups.family(c,'word-i');row=dict(c.execute(text("SELECT * FROM progress WHERE knowledge_id='word-i'")).mappings().one(),id='word-i',role='word')
   self.assertFalse(course_policy.owns_review(c,'some-other-group',row));self.assertTrue(course_policy.owns_review(c,owner,row))

 def test_known_want_to_covers_to_without_fake_single_word_mastery(self):
  with self.db.begin() as c:
   c.execute(text('UPDATE progress SET introduced=1,level=3'))
   c.execute(text("INSERT INTO knowledge VALUES('function-to','to','to','to','to')"));c.execute(text("INSERT INTO progress(knowledge_id) VALUES('function-to')"))
   c.execute(text("INSERT INTO group_requirements VALUES('want-to-sentence','function-to')"))
   self.assertTrue(groups.requirements_met(c,'want-to-sentence'));self.assertEqual(c.execute(text("SELECT level FROM progress WHERE knowledge_id='function-to'")).scalar(),0)

 def test_known_phrase_covers_contained_chunk_not_unrelated_material(self):
  with self.db.begin() as c:
   c.execute(text("UPDATE progress SET level=3,introduced=1 WHERE knowledge_id='look-at-action'"))
   for kid,en in [('known-contained','this picture'),('unknown-unrelated','the radio')]:
    c.execute(text('INSERT INTO knowledge VALUES(:k,:a,:a,:a,:a)'),dict(k=kid,a=en));c.execute(text('INSERT INTO progress(knowledge_id) VALUES(:k)'),dict(k=kid))
   self.assertTrue(course_policy.covered_function(c,'look-at-sentence','known-contained'));self.assertFalse(course_policy.covered_function(c,'look-at-sentence','unknown-unrelated'))
