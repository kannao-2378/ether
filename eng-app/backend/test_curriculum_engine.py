import copy,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from sqlalchemy import create_engine,text
import app,curriculum_engine as ce,course_policy,group_learning as groups
class TeachingRegistryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.tmp.name)/'test.db'));app.initialize(self.db,with_bulk=False)
  self.ep=patch.object(app,'real_engine',self.db);self.ep.start();self.clock=datetime(2026,11,2,8,tzinfo=timezone.utc);self.tp=patch.object(app,'now',return_value=self.clock);self.tp.start()
 def tearDown(self):self.tp.stop();self.ep.stop();self.db.dispose();self.tmp.cleanup()
 def test_fifty_authored_goals_and_draft_quarantine(self):
  with self.db.connect() as c:
   report=ce.report(c);self.assertEqual(report['ready_total'],50);self.assertGreater(report['draft_total'],0)
   self.assertTrue(all(c.execute(text("SELECT status FROM curriculum_goals WHERE id=:g"),dict(g=g['id'])).scalar()=='ready' for g in ce.candidates(c,limit=50)))
 def test_actual_dependencies_filter_new_candidates(self):
  with self.db.begin() as c:
   self.assertNotIn('need-to',[r['id'] for r in ce.candidates(c,limit=50)])
   c.execute(text("UPDATE progress SET introduced=1,level=3 WHERE knowledge_id='want-to'"))
   self.assertIn('need-to',[r['id'] for r in ce.candidates(c,limit=50)])
 def test_generic_other_course_can_request_foundation_support(self):
  with self.db.begin() as c:
   c.execute(text("INSERT INTO learning_courses VALUES('new-domain','new domain','goal','beginner')"))
   spec=dict(course_id='new-domain',units=[dict(id='other-unit',title='other',goal='express',position=0)],goals=[dict(key='other-goal',unit='other-unit',english='save money',chinese='存钱',objective='表达存钱',usage='save money 表示存钱。',sentence='I save money.',sentence_zh='我存钱。',requires=['drink-water'])])
   ce.publish(c,spec)
   self.assertEqual(ce.candidates(c,'new-domain')[0]['id'],'drink-water')
   self.assertEqual(ce.report(c,'new-domain')['units'][0]['items'][0]['state'],'blocked')
   c.execute(text("UPDATE progress SET introduced=1,level=3 WHERE knowledge_id='drink-water'"))
   self.assertEqual(ce.candidates(c,'new-domain')[0]['id'],'other-goal')
 def test_cycle_is_rejected_without_partial_write(self):
  spec=json.loads(ce.MANIFEST.read_text(encoding='utf-8'));spec['goals'][0]['requires']=['drink-water']
  with self.db.begin() as c:
   before=c.execute(text('SELECT COUNT(*) FROM knowledge')).scalar()
   with self.assertRaises(ValueError):ce.publish(c,spec)
   self.assertEqual(c.execute(text('SELECT COUNT(*) FROM knowledge')).scalar(),before)
 def test_shared_goal_has_one_identity_across_courses(self):
  spec=json.loads(ce.MANIFEST.read_text(encoding='utf-8'));spec['goals']=spec['goals'][:1];spec['course_id']='shared-course'
  with self.db.begin() as c:
   c.execute(text("INSERT INTO learning_courses VALUES('shared-course','shared','shared','1')"));before=c.execute(text('SELECT COUNT(*) FROM knowledge')).scalar();ce.publish(c,spec)
   self.assertEqual(c.execute(text('SELECT COUNT(*) FROM knowledge')).scalar(),before)
   self.assertEqual(c.execute(text("SELECT COUNT(DISTINCT goal_id) FROM curriculum_paths WHERE goal_id='drink-water' AND authored=1")).scalar(),1)
   self.assertEqual(c.execute(text("SELECT COUNT(DISTINCT course_id) FROM curriculum_paths WHERE goal_id='drink-water' AND authored=1")).scalar(),2)
 def test_required_materials_are_not_duplicated_as_new_goals(self):
  with self.db.connect() as c:
   self.assertEqual(groups.family(c,'word-read'),'read-books')
   self.assertNotIn('word-read',[r['id'] for r in ce.candidates(c,limit=100)])
 def test_compiled_lesson_excludes_incidental_legacy_sentence_words(self):
  with self.db.connect() as c:
   ids={r['id'] for r in course_policy.core_members(c,'every-day',groups.members(c,'every-day'))}
   self.assertNotIn('every-day-sentence',ids)
   self.assertTrue(any('lesson-sentence' in k for k in ids))
 def test_latest_forgetting_beats_old_equivalent_success(self):
  with self.db.begin() as c:
   target=c.execute(text("SELECT knowledge_id FROM curriculum_lessons WHERE goal_id='want-to' AND role='sentence'")).scalar()
   c.execute(text('INSERT OR IGNORE INTO curriculum_aliases VALUES(:k,:a)'),dict(k=target,a='want-to-sentence'))
   c.execute(text("UPDATE progress SET introduced=1,level=3,last_at='2026-11-01T00:00:00+00:00' WHERE knowledge_id='want-to-sentence'"))
   self.assertTrue(ce.known(c,target))
   c.execute(text("UPDATE progress SET introduced=1,level=2,last_at='2026-11-02T00:00:00+00:00' WHERE knowledge_id=:k"),dict(k=target));self.assertFalse(ce.known(c,target))
 def test_existing_records_survive_reinstall(self):
  q=app.next_question();app.introduce(q['id']);q=app.next_question();app.submit(app.Submission(question_id=q['question_id'],answer=app.knowledge_content(q['id'])['answer'],confidence='hard'))
  with self.db.begin() as c:
   before={t:c.execute(text('SELECT * FROM '+t)).all() for t in ('answers','feedback_events','progress','memory_states')};groups.install(c)
   for t,rows in before.items():self.assertEqual(rows,c.execute(text('SELECT * FROM '+t)).all())
 def test_draft_keeps_due_reviews_but_does_not_add_new_lessons(self):
  with self.db.begin() as c:
   c.execute(text("UPDATE curriculum_goals SET status='draft' WHERE id='want-to'"));c.execute(text("UPDATE progress SET introduced=1,level=3,due_at=:t WHERE knowledge_id='want-to'"),dict(t=self.clock.isoformat()))
   item,_=groups.step(c,'want-to',self.clock);self.assertEqual(item['id'],'want-to')
   c.execute(text("UPDATE progress SET due_at=:t WHERE knowledge_id='want-to'"),dict(t=(self.clock+timedelta(days=10)).isoformat()))
   item,_=groups.step(c,'want-to',self.clock);self.assertIsNone(item)

 def test_retire_unused_goal_without_erasing_knowledge(self):
  spec=json.loads(ce.MANIFEST.read_text(encoding='utf-8'));spec['goals']=spec['goals'][:-1]
  with self.db.begin() as c:
   old=c.execute(text("SELECT id FROM curriculum_goals WHERE objective LIKE '过去常常%' AND status='ready'")).scalar();ce.publish(c,spec)
   self.assertEqual(ce.report(c)['ready_total'],49)
   self.assertEqual(c.execute(text('SELECT status FROM curriculum_goals WHERE id=:k'),dict(k=old)).scalar(),'retired')
   self.assertTrue(c.execute(text('SELECT 1 FROM knowledge WHERE id=:k'),dict(k=old)).first())
 def test_material_identity_survives_insertion_and_distinguishes_senses(self):
  spec=json.loads(ce.MANIFEST.read_text(encoding='utf-8'));spec['replace_course']=False;spec['goals']=spec['goals'][:1]
  with self.db.begin() as c:
   before=c.execute(text("SELECT knowledge_id FROM curriculum_lessons WHERE goal_id='drink-water' AND role='sentence'")).scalar()
   spec['goals'][0]['materials'].insert(0,dict(en='right',zh='右边'));spec['goals'][0]['materials'].insert(0,dict(en='right',zh='正确的'));ce.publish(c,spec)
   self.assertEqual(c.execute(text("SELECT knowledge_id FROM curriculum_lessons WHERE goal_id='drink-water' AND role='sentence'")).scalar(),before)
   meanings=c.execute(text("SELECT DISTINCT k.prompt FROM curriculum_lessons l JOIN knowledge k ON k.id=l.knowledge_id WHERE l.goal_id='drink-water' AND k.answer='right'")).scalars().all();self.assertEqual(set(meanings),{'正确的','右边'})

 def test_default_sandbox_uses_same_registry(self):
  with self.db.begin() as c:
   c.execute(text('CREATE TABLE IF NOT EXISTS test_clock(id INTEGER PRIMARY KEY,days INTEGER,stage INTEGER)'));c.execute(text('INSERT OR REPLACE INTO test_clock VALUES(1,0,NULL)'))
  token=app.testing.set(True)
  try:
   with patch.object(app,'test_engine',self.db):self.assertEqual(app.next_question()['group_id'],'drink-water')
  finally:app.testing.reset(token)
 def test_transfer_reuses_known_actions_and_blocks_unknown_radio(self):
  with self.db.begin() as c:
   target=c.execute(text("SELECT knowledge_id FROM curriculum_lessons WHERE goal_id='listen-to' AND role='transfer'")).scalar()
   c.execute(text("UPDATE progress SET introduced=1,level=3 WHERE knowledge_id IN (SELECT knowledge_id FROM group_members WHERE group_id='listen-to')"))
   c.execute(text("UPDATE progress SET level=0,introduced=0 WHERE knowledge_id='the-radio'"));self.assertFalse(groups.requirements_met(c,target))
   c.execute(text("UPDATE progress SET level=3,introduced=1 WHERE knowledge_id='the-radio'"));self.assertTrue(groups.requirements_met(c,target))

 def test_sandbox_skip_advances_without_independent_evidence(self):
  with self.db.begin() as c:c.execute(text('CREATE TABLE IF NOT EXISTS test_clock(id INTEGER PRIMARY KEY,days INTEGER,stage INTEGER)'));c.execute(text('INSERT OR REPLACE INTO test_clock VALUES(1,0,NULL)'))
  token=app.testing.set(True)
  try:
   with patch.object(app,'test_engine',self.db):
    q=app.next_question();app.introduce(q['id']);q=app.next_question();app.skip_test_question(q['question_id']);nxt=app.next_question();self.assertNotEqual(q['id'],nxt['id'])
    with self.db.connect() as c:self.assertEqual(c.execute(text('SELECT COUNT(*) FROM group_usage WHERE question_id=:q'),dict(q=q['question_id'])).scalar(),0)
  finally:app.testing.reset(token)

 def test_known_whole_chunk_reuses_words_without_forging_word_scores(self):
  with self.db.begin() as c:
   c.execute(text("UPDATE progress SET introduced=1,level=3 WHERE knowledge_id='drink-water'"))
   chosen={r['id'] for r in course_policy.core_members(c,'drink-water',groups.members(c,'drink-water'))};self.assertNotIn('word-drink',chosen)
   target=c.execute(text("SELECT knowledge_id FROM curriculum_lessons WHERE goal_id='drink-water' AND role='sentence'")).scalar();self.assertTrue(ce.chunk_covers(c,target,'word-drink'))
   self.assertEqual(c.execute(text("SELECT level FROM progress WHERE knowledge_id='word-drink'")).scalar(),0)

 def test_difficulty_orders_available_goals_within_a_unit(self):
  with self.db.begin() as c:
   c.execute(text("INSERT INTO learning_courses VALUES('level-course','level','level','1')"))
   spec=dict(course_id='level-course',units=[dict(id='level-unit',title='level',goal='level',position=0)],goals=[dict(key='level-hard',unit='level-unit',english='assess risk',chinese='评估风险',objective='表达评估风险',usage='assess risk 表示评估风险。',sentence='I assess risk.',sentence_zh='我评估风险。',difficulty=3),dict(key='level-easy',unit='level-unit',english='save money',chinese='存钱',objective='表达存钱',usage='save money 表示存钱。',sentence='I save money.',sentence_zh='我存钱。',difficulty=1)])
   ce.publish(c,spec);self.assertEqual(ce.candidates(c,'level-course')[0]['id'],'level-easy')

 def test_existing_word_phrase_sentence_classification_is_preserved(self):
  with self.db.connect() as c:self.assertEqual(app.content.details(c,'drink-water')['entry_type'],'phrase')
