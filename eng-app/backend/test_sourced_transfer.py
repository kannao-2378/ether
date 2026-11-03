import tempfile,unittest,json
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from sqlalchemy import create_engine,text
import app,sourced_transfer as st,curriculum_engine as ce,group_learning as gl,composition_engine as comp

class SourcedPilotTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.tmp.name)/'pilot.db'));app.initialize(self.db,with_bulk=False)
  self.stamp=datetime(2026,11,5,8,tzinfo=timezone.utc);self.ep=patch.object(app,'real_engine',self.db);self.ep.start();self.tp=patch('app.now',return_value=self.stamp);self.tp.start()
 def tearDown(self):self.tp.stop();self.ep.stop();self.db.dispose();self.tmp.cleanup()
 def prepared(self,c):
  # Already learned ordinary foundation; sourced material remains unlearned.
  c.execute(text("UPDATE progress SET introduced=1,level=3,last_at=:t,due_at=:d WHERE knowledge_id NOT IN (SELECT knowledge_id FROM course_links WHERE stage=4) AND knowledge_id NOT IN (SELECT knowledge_id FROM source_preparation_items)"),dict(t=(self.stamp-timedelta(days=1)).isoformat(),d=(self.stamp+timedelta(days=10)).isoformat()))
 def material_answer(self,confidence='clear'):
  with self.db.begin() as c:
   result=st.select_preparation(c,self.stamp,50,50);self.assertIsNotNone(result);kind,item=result
  self.assertEqual(kind,'learn');app.introduce(item['id'])
  with patch.object(gl,'select',return_value=('recall',item)):q=app.next_question()
  app.submit(app.Submission(question_id=q['question_id'],answer=item['answer'],confidence=confidence))
  return item
 def test_default_off_and_resource_sources(self):
  with self.db.begin() as c:
   self.assertFalse(st.enabled(c));self.assertEqual(st.report(c,self.stamp),[])
   self.assertEqual(c.execute(text('SELECT count(*) FROM source_sentence_targets')).scalar(),0)
   st.activate(c);self.assertEqual(len(st.targets(c,'want-to')),5)
   for row in c.execute(text('SELECT english,provenance FROM source_sentence_bank')):
    source=json.loads(row[1]);self.assertEqual(row[0],source['en']);self.assertIn('tatoeba.org',source['source_url']);self.assertTrue(source['license'])
 def test_activation_idempotent_and_history_untouched(self):
  with self.db.begin() as c:
   before={t:set(c.execute(text('SELECT * FROM '+t))) for t in ('answers','feedback_events','progress','memory_states')}
   st.activate(c);st.activate(c)
   self.assertEqual(c.execute(text('SELECT count(*) FROM source_sentence_bank')).scalar(),5)
   for t,rows in before.items():self.assertTrue(rows<=set(c.execute(text('SELECT * FROM '+t))))
 def test_missing_materials_and_basics_not_assumed_or_leaked(self):
  with self.db.begin() as c:
   st.activate(c);self.assertIsNone(st.select_preparation(c,self.stamp,50,50));self.prepared(c)
   report=st.report(c,self.stamp)[0];self.assertEqual(report['missing_total'],5);self.assertEqual(report['ready'],0)
   self.assertNotIn('I want to',json.dumps(report));self.assertIsNone(st.select_preparation(c,self.stamp,0,50))
 def test_preparation_uses_new_quota_and_two_per_day_cap(self):
  with self.db.begin() as c:
   st.activate(c);self.prepared(c)
   for _ in range(2):
    kind,item=st.select_preparation(c,self.stamp,50,50);self.assertEqual(kind,'learn')
    c.execute(text('UPDATE progress SET introduced=1,level=3,last_at=:t WHERE knowledge_id=:k'),dict(k=item['id'],t=self.stamp.isoformat()))
   self.assertEqual(gl.counts(c,self.stamp),{'new':2});self.assertIsNone(st.select_preparation(c,self.stamp,50,50))
 def test_material_learning_spacing_then_real_chinese_transfer(self):
  with self.db.begin() as c:st.activate(c);self.prepared(c)
  item=self.material_answer()
  with self.db.connect() as c:
   target=c.execute(text('SELECT knowledge_id FROM source_sentence_targets WHERE material_id=:m'),dict(m=item['id'])).scalar()
   self.assertFalse(c.execute(text('SELECT 1 FROM group_active_slots WHERE group_id=:g'),dict(g=item['id'])).first())
   self.assertTrue(ce.known(c,item['id']));self.assertEqual(st.spacing(c,item['id'],self.stamp),3);self.assertFalse(st.allowed(c,target,self.stamp))
   self.assertEqual(app.transfer_evidence.classify(c,target,'transfer')[0],'transfer')
  for kid in ('word-i','word-water','word-read'):
   q=app.challenge(kid);answer=app.knowledge_content(kid)['answer'];app.submit(app.Submission(question_id=q['question_id'],answer=answer,confidence='clear'))
  with self.db.begin() as c:
   self.assertTrue(st.allowed(c,target,self.stamp));chosen,_=gl.step(c,'want-to',self.stamp);self.assertEqual(chosen['id'],target)
   gl.admit(c,'want-to',target,self.stamp,50,50)
  with patch.object(gl,'select',return_value=('recall',dict(chosen,group_id='want-to',group_title='want to'))):q=app.next_question()
  self.assertEqual(q['exercise_mode'],'transfer');self.assertNotIn('answer',q)
  app.submit(app.Submission(question_id=q['question_id'],answer=chosen['answer'],confidence='hard'))
  with self.db.connect() as c:self.assertEqual(st.report(c,self.stamp)[0]['successful_materials'],0)
 def test_no_other_tasks_spacing_releases_on_next_day(self):
  with self.db.begin() as c:st.activate(c);self.prepared(c)
  item=self.material_answer()
  with self.db.connect() as c:
   target=c.execute(text('SELECT knowledge_id FROM source_sentence_targets WHERE material_id=:m'),dict(m=item['id'])).scalar()
   self.assertFalse(st.allowed(c,target,self.stamp));self.assertTrue(st.allowed(c,target,self.stamp+timedelta(days=1)))
 def test_shown_answers_flagged_gap_not_invented(self):
  with self.db.begin() as c:
   st.activate(c);self.prepared(c)
   for row in st.targets(c,'want-to'):app.transfer_evidence.expose(c,row['knowledge_id'],self.stamp)
   report=st.report(c,self.stamp)[0];self.assertEqual(report['state'],'需要补充新例句');self.assertEqual(report['seen'],5)
   self.assertIsNone(st.select_preparation(c,self.stamp,50,50));comp.prepare(c,self.stamp)
   self.assertFalse(c.execute(text("SELECT 1 FROM composition_items WHERE goal_id='want-to'")).first())
 def test_tables_export_and_real_mode_cannot_enable(self):
  from fastapi import HTTPException
  with self.assertRaises(HTTPException):app.test_action('transfer-pilot',{})
  with self.db.begin() as c:st.activate(c)
  self.assertTrue(set(st.TABLES)<=set(app.export()['tables']))

 def test_fuzzy_preparation_does_not_immediately_repeat(self):
  with self.db.begin() as c:st.activate(c);self.prepared(c)
  item=self.material_answer(confidence='hard')
  with self.db.begin() as c:
   next_item=st.select_preparation(c,self.stamp,50,50)
   self.assertIsNotNone(next_item);self.assertNotEqual(next_item[1]['id'],item['id'])

 def test_budget_has_explicit_done_reason_and_direct_challenge_cannot_bypass(self):
  from fastapi import HTTPException
  with self.db.begin() as c:
   st.activate(c);self.prepared(c);target=st.targets(c,'want-to')[0]['knowledge_id']
  with self.assertRaises(HTTPException):app.challenge(target)
  app.save_settings({'daily-new-limit':0,'daily-review-limit':50})
  with patch.object(gl,'select',return_value=('done',None)):
   result=app.next_question();self.assertEqual(result['reason'],'transfer-preparation-budget')
 def test_daily_two_successes_explain_retained_candidates(self):
  with self.db.begin() as c:
   st.activate(c);self.prepared(c);targets=st.targets(c,'want-to')[:2]
   for row in targets:c.execute(text('UPDATE progress SET introduced=1,level=3 WHERE knowledge_id=:m'),dict(m=row['material_id']))
  for row in targets:
   q=app.challenge(row['knowledge_id']);en=app.knowledge_content(row['knowledge_id'])['answer'];app.submit(app.Submission(question_id=q['question_id'],answer=en,confidence='clear'))
  with self.db.connect() as c:self.assertEqual(st.report(c,self.stamp)[0]['state'],'今日迁移练习已完成')
  with patch.object(gl,'select',return_value=('done',None)):
   self.assertEqual(app.next_question()['reason'],'transfer-daily-limit')

 def test_forgotten_material_does_not_block_other_preparation(self):
  with self.db.begin() as c:st.activate(c);self.prepared(c)
  item=self.material_answer(confidence='forgot')
  with self.db.begin() as c:
   choice=st.select_preparation(c,self.stamp,50,50)
   self.assertIsNotNone(choice);self.assertNotEqual(choice[1]['id'],item['id'])
 def test_preparation_runs_before_continuously_due_other_reviews(self):
  with self.db.begin() as c:
   st.activate(c);self.prepared(c)
   c.execute(text("UPDATE progress SET due_at=:t WHERE knowledge_id='word-read'"),dict(t=self.stamp.isoformat()))
  q=app.next_question();self.assertEqual(q['group_title'],'迁移材料准备');self.assertEqual(q['kind'],'learn')

 def test_forgotten_preparation_requires_two_other_completed_exercises(self):
  with self.db.begin() as c:st.activate(c);self.prepared(c)
  item=self.material_answer(confidence='forgot')
  for index,kid in enumerate(('word-i','word-water')):
   q=app.challenge(kid);en=app.knowledge_content(kid)['answer'];app.submit(app.Submission(question_id=q['question_id'],answer=en,confidence='clear'))
   with self.db.connect() as c:self.assertEqual(st.retry_ready(c,item['id'],self.stamp),index==1)

 def test_only_difficult_material_has_explicit_spacing_reason(self):
  with self.db.begin() as c:
   st.activate(c);self.prepared(c)
   items=c.execute(text('SELECT knowledge_id FROM source_preparation_items ORDER BY rowid')).scalars().all()
   for kid in items[1:]:c.execute(text('UPDATE progress SET introduced=1,level=3 WHERE knowledge_id=:k'),dict(k=kid))
   for row in st.targets(c,'want-to')[1:]:app.transfer_evidence.expose(c,row['knowledge_id'],self.stamp)
  self.material_answer(confidence='forgot')
  with self.db.connect() as c:
   report=st.report(c,self.stamp)[0]
   self.assertEqual(report['waiting_reason'],'难记材料等待穿插或隔天再练')
