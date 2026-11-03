import tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from sqlalchemy import create_engine,text
import app,curriculum_engine as ce,group_learning as groups,transfer_evidence

class TransferPackTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.tmp.name)/'pack.db'));app.initialize(self.db,with_bulk=False)
  self.stamp=datetime(2026,11,4,8,tzinfo=timezone.utc)
  self.ep=patch.object(app,'real_engine',self.db);self.ep.start();self.tp=patch('app.now',return_value=self.stamp);self.tp.start()
 def tearDown(self):self.tp.stop();self.ep.stop();self.db.dispose();self.tmp.cleanup()
 def prepared(self):
  with self.db.begin() as c:
   c.execute(text("UPDATE progress SET introduced=1,level=3,due_at=:d WHERE knowledge_id NOT IN (SELECT knowledge_id FROM course_links WHERE stage=4)"),dict(d=(self.stamp+timedelta(days=10)).isoformat()))
   c.execute(text("INSERT INTO group_progress VALUES('want-to',:d,:d,1)"),dict(d=(self.stamp+timedelta(days=10)).isoformat()))
  app.save_settings({'daily-new-limit':0,'daily-review-limit':50})
 def test_all_fifty_goals_have_at_least_three_variants_and_links(self):
  with self.db.connect() as c:
   counts=c.execute(text("SELECT goal_id,count(*) FROM curriculum_lessons WHERE role='transfer' GROUP BY goal_id")).all()
   self.assertEqual(len(counts),50);self.assertTrue(all(n>=3 for _,n in counts));self.assertEqual(sum(n for _,n in counts),165)
   self.assertEqual(c.execute(text("SELECT count(*) FROM curriculum_lessons l WHERE role='transfer' AND NOT EXISTS(SELECT 1 FROM sentence_combinations sc WHERE sc.knowledge_id=l.knowledge_id)")).scalar(),0)
 def test_missing_registered_object_blocks_transfer(self):
  self.prepared()
  with self.db.begin() as c:
   kid=c.execute(text("SELECT l.knowledge_id FROM curriculum_lessons l JOIN knowledge k ON k.id=l.knowledge_id WHERE l.goal_id='look-at' AND k.answer='I look at my cat.'")).scalar()
   mat=c.execute(text("SELECT r.material_id FROM group_requirements r JOIN knowledge k ON k.id=r.material_id WHERE r.knowledge_id=:k AND k.answer='my cat'"),dict(k=kid)).scalar()
   self.assertIsNotNone(mat);c.execute(text('UPDATE progress SET introduced=0,level=0 WHERE knowledge_id=:m'),dict(m=mat))
   self.assertFalse(groups.requirements_met(c,kid,stamp=self.stamp))
 def test_known_materials_allow_chinese_transfer_before_stable(self):
  self.prepared();q=app.next_question()
  self.assertEqual(q['kind'],'recall');self.assertEqual(q['exercise_mode'],'transfer');self.assertNotIn('answer',q)
  with self.db.connect() as c:self.assertFalse(app.assessment.calculate(c,q['group_id'])['stable'])
 def test_old_completed_goal_can_reopen_for_new_transfer_without_new_quota(self):
  self.prepared()
  with self.db.connect() as c:
   self.assertIn('want-to',ce.upgrades(c,self.stamp))
   item,_=groups.step(c,'want-to',self.stamp);self.assertEqual(item['role'],'transfer')
   self.assertEqual(transfer_evidence.classify(c,item['id'],'transfer')[0],'transfer')
  q=app.next_question()
  with self.db.connect() as c:self.assertEqual(groups.counts(c,self.stamp).get('new',0),0)
 def test_install_is_idempotent_and_preserves_original_rows(self):
  self.prepared();q=app.next_question();answer=app.knowledge_content(q['id'])['answer'];app.submit(app.Submission(question_id=q['question_id'],answer=answer,confidence='clear'))
  tables=('answers','feedback_events','progress','memory_states')
  with self.db.connect() as c:before={t:set(c.execute(text('SELECT * FROM '+t)).all()) for t in tables};count=c.execute(text('SELECT count(*) FROM knowledge')).scalar()
  app.initialize(self.db,with_bulk=False)
  with self.db.connect() as c:
   self.assertEqual(count,c.execute(text('SELECT count(*) FROM knowledge')).scalar())
   for t in tables:self.assertTrue(before[t]<=set(c.execute(text('SELECT * FROM '+t)).all()),t)

 def test_shown_variants_do_not_hide_new_combinations(self):
  self.prepared()
  with self.db.begin() as c:
   kids=c.execute(text("SELECT knowledge_id FROM curriculum_lessons WHERE goal_id='want-to' AND role='transfer' ORDER BY rowid LIMIT 2")).scalars().all()
   for kid in kids:transfer_evidence.expose(c,kid,self.stamp)
   item,_=groups.step(c,'want-to',self.stamp)
   self.assertNotIn(item['id'],kids);self.assertEqual(transfer_evidence.classify(c,item['id'],'transfer')[0],'transfer')
 def test_daily_two_variation_limit_and_group_quota_are_preserved(self):
  self.prepared()
  with self.db.begin() as c:self.assertTrue(groups.admit(c,'want-to','want-to',self.stamp,0,50))
  for _ in range(2):
   with self.db.connect() as c:item,_=groups.step(c,'want-to',self.stamp)
   self.assertEqual(item['role'],'transfer');q=app.challenge(item['id'])
   app.submit(app.Submission(question_id=q['question_id'],answer=item['answer'],confidence='clear'))
  with self.db.connect() as c:
   item,_=groups.step(c,'want-to',self.stamp);self.assertIsNone(item)
   self.assertEqual(groups.counts(c,self.stamp),{'review':1})
