"""Integration tests for family counting, transfer, migration and concrete repair."""
import tempfile,unittest,uuid,json
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from sqlalchemy import create_engine,text
import app,group_learning as groups
class GroupLearningTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.temp.name)/'groups.db'));app.initialize(self.db)
  self.clock=datetime(2026,11,1,8,tzinfo=timezone.utc)
  self.engine=patch.object(app,'real_engine',self.db);self.engine.start();self.time=patch('app.now',side_effect=lambda:self.clock);self.time.start()
  with self.db.begin() as c:
   for kid,answer in [('test-listen','listen'),('test-music','music')]:
    c.execute(text('INSERT INTO knowledge VALUES(:k,:a,:a,:a,:a)'),dict(k=kid,a=answer));c.execute(text('INSERT INTO progress(knowledge_id) VALUES(:k)'),dict(k=kid))
   groups.install(c)
   c.execute(text("UPDATE progress SET introduced=1,level=3,due_at=:t WHERE knowledge_id='drink-water' OR knowledge_id=(SELECT id FROM knowledge WHERE answer='music' ORDER BY rowid LIMIT 1)"),dict(t=(self.clock+timedelta(days=10)).isoformat()))
   c.execute(text("UPDATE group_primary SET group_id='listen-to' WHERE knowledge_id='word-i'"))
   c.execute(text("UPDATE progress SET introduced=1,level=3,due_at=:t WHERE knowledge_id IN (SELECT knowledge_id FROM curriculum_lessons WHERE goal_id='drink-water' AND role IN ('phrase','sentence'))"),dict(t=(self.clock+timedelta(days=10)).isoformat()))
   # Explicit legacy lesson fixture tests scheduler invariants independently of the new authored route.
   c.execute(text("DELETE FROM curriculum_prerequisites WHERE goal_id='listen-to'"))
   c.execute(text("DELETE FROM curriculum_lessons WHERE goal_id='listen-to'"))
   c.execute(text("UPDATE group_primary SET group_id='listen-to' WHERE knowledge_id='test-music'"))
   c.execute(text("INSERT OR IGNORE INTO group_members VALUES('listen-to','test-music','word',0)"))
   self.assertTrue(groups.admit(c,'listen-to','test-listen',self.clock,1,0))
  app.save_settings({'daily-new-limit':1,'daily-review-limit':0})
 def tearDown(self):self.time.stop();self.engine.stop();self.db.dispose();self.temp.cleanup()
 def correct(self,q,rating='clear',wrong=False):
  answer=app.knowledge_content(q['id'])['answer']
  if wrong:app.check_spelling(app.SpellingCheck(id=str(uuid.uuid4()),question_id=q['question_id'],answer='__wrong__'))
  return app.submit(app.Submission(question_id=q['question_id'],answer=answer,confidence=rating))
 def finish(self,max_steps=40):
  seen=[]
  for _ in range(max_steps):
   q=app.next_question()
   if q['kind']=='done':return seen
   seen.append((q['kind'],q['id']))
   if q['kind']=='learn':app.introduce(q['id'])
   else:self.correct(q)
  self.fail('Group never finishes: '+str(seen))
 def test_listen_words_and_expression_share_one_slot_and_do_not_loop(self):
  seen=self.finish()
  for kid in ['test-listen','test-music','listen-to','listen-to-action','group-listen-basic']:
   self.assertEqual(sum(1 for kind,k in seen if kind=='recall' and k==kid),1,(kid,seen))
  with self.db.connect() as c:
   self.assertEqual(groups.counts(c,self.clock),{'new':1})
   self.assertEqual(c.execute(text("SELECT transfer_pending FROM group_progress WHERE group_id='listen-to'")).scalar(),1)
   self.assertEqual(c.execute(text("SELECT COUNT(*) FROM answers WHERE knowledge_id='group-listen-radio'")).scalar(),0)
 def test_early_transfer_uses_known_material_without_stable_gate(self):
  with self.db.begin() as c:c.execute(text("UPDATE progress SET level=3,introduced=1,due_at=:t WHERE knowledge_id IN ('the-radio','my-friend')"),dict(t=(self.clock+timedelta(days=10)).isoformat()))
  seen=self.finish()
  self.assertIn(('recall','group-listen-radio'),seen);self.assertIn(('recall','group-listen-friend'),seen)
  self.assertNotIn(('recall','group-listen-teacher'),seen)
  with self.db.connect() as c:
   self.assertEqual(groups.counts(c,self.clock),{'new':1})
   self.assertFalse(app.assessment.get(c,'listen-to')['stable'])
   self.assertEqual(c.execute(text("SELECT transfer_pending FROM group_progress WHERE group_id='listen-to'")).scalar(),0)
 def test_error_repairs_the_actual_word_without_restarting_family(self):
  q=app.next_question();app.introduce(q['id']);q=app.next_question();self.correct(q,'hard',wrong=True)
  q2=app.next_question();self.assertEqual(q2['id'],q['id'])
  self.assertEqual(q2['kind'],'recall')
  with self.db.connect() as c:self.assertEqual(groups.counts(c,self.clock),{'new':1})
 def test_support_never_changes_target_card_or_fakes_attempts(self):
  self.finish()
  with self.db.connect() as c:
   before=c.execute(text("SELECT attempts FROM progress WHERE knowledge_id='test-listen'")).scalar()
   self.assertEqual(before,1)
   self.assertTrue(c.execute(text("SELECT 1 FROM group_usage WHERE target_id='test-listen'")).first())
 def test_cross_day_returns_review_and_keeps_raw_answers(self):
  self.finish()
  with self.db.connect() as c:before=c.execute(text('SELECT COUNT(*) FROM answers')).scalar()
  self.clock+=timedelta(days=2);app.save_settings({'daily-new-limit':0,'daily-review-limit':1})
  q=app.next_question();self.assertEqual(q['kind'],'recall')
  with self.db.connect() as c:
   self.assertEqual(groups.counts(c,self.clock),{'review':1});self.assertEqual(c.execute(text('SELECT COUNT(*) FROM answers')).scalar(),before)
 def test_correction_reopens_completed_group_without_extra_budget(self):
  self.finish()
  with self.db.connect() as c:q=c.execute(text("SELECT question_id FROM answers WHERE knowledge_id='group-listen-basic' ORDER BY rowid DESC LIMIT 1")).scalar()
  app.feedback(app.Feedback(question_id=q,confidence='forgot'))
  resumed=app.next_question();self.assertEqual(resumed['id'],'group-listen-basic')
  with self.db.connect() as c:self.assertEqual(groups.counts(c,self.clock),{'new':1})
 def test_pool_holds_twelve_families_and_releases_completed_slot(self):
  with self.db.begin() as c:
   c.execute(text('DELETE FROM group_active_slots'));c.execute(text('DELETE FROM daily_group_tasks'))
   ids=c.execute(text('SELECT id FROM learning_groups LIMIT 13')).scalars().all()
   for gid in ids[:12]:self.assertTrue(groups.acquire(c,gid,self.clock))
   self.assertFalse(groups.acquire(c,ids[12],self.clock));self.assertEqual(groups.pool_count(c,self.clock),12)
   c.execute(text('INSERT INTO group_progress VALUES(:g,:d,:t,0)'),dict(g=ids[0],d=(self.clock+timedelta(days=1)).isoformat(),t=self.clock.isoformat()))
   self.assertTrue(groups.acquire(c,ids[12],self.clock));self.assertEqual(groups.pool_count(c,self.clock),12)
 def test_same_spelling_root_different_usage_is_not_merged(self):
  with self.db.connect() as c:
   self.assertNotEqual(groups.family(c,'look-at'),groups.family(c,'look-for'))
   self.assertEqual(groups.family(c,'listen-to'),groups.family(c,'test-listen'))
 def test_migration_preserves_answers_and_fsrs_and_budget(self):
  self.finish()
  with self.db.begin() as c:
   before=c.execute(text('SELECT * FROM answers ORDER BY id')).all();cards=c.execute(text('SELECT * FROM memory_states ORDER BY knowledge_id')).all()
   slots=groups.counts(c,self.clock);groups.install(c);groups.install(c)
   self.assertEqual(before,c.execute(text('SELECT * FROM answers ORDER BY id')).all())
   self.assertEqual(cards,c.execute(text('SELECT * FROM memory_states ORDER BY knowledge_id')).all())
   self.assertEqual(slots,groups.counts(c,self.clock))
 def test_pending_transfer_is_deferred_if_material_lapses(self):
  with self.db.begin() as c:
   c.execute(text("UPDATE progress SET level=3,introduced=1 WHERE knowledge_id IN ('listen-to','the-radio','word-i')"))
   q='pending-transfer-test'
   c.execute(text("INSERT INTO questions VALUES(:q,'group-listen-radio',:t,0)"),dict(q=q,t=self.clock.isoformat()))
   c.execute(text("INSERT INTO group_questions VALUES(:q,'listen-to','transfer')"),dict(q=q))
   c.execute(text("UPDATE progress SET level=2 WHERE knowledge_id='the-radio'"))
  self.clock+=timedelta(days=1);app.save_settings({'daily-new-limit':1,'daily-review-limit':1})
  nxt=app.next_question();self.assertNotEqual(nxt.get('question_id'),q)
  with self.db.connect() as c:
   self.assertTrue(c.execute(text('SELECT 1 FROM questions WHERE id=:q'),dict(q=q)).first())
   self.assertFalse(c.execute(text('SELECT 1 FROM answers WHERE question_id=:q'),dict(q=q)).first())
 def test_transfer_returns_same_day_when_materials_become_known(self):
  self.finish()
  with self.db.begin() as c:c.execute(text("UPDATE progress SET level=3,introduced=1,due_at=:t WHERE knowledge_id IN ('the-radio','my-friend')"),dict(t=(self.clock+timedelta(days=10)).isoformat()))
  nxt=app.next_question();self.assertEqual(nxt['id'],'group-listen-radio')
  if nxt['kind']=='learn':app.introduce(nxt['id'])
  else:self.correct(nxt)
  self.finish()
  with self.db.connect() as c:self.assertEqual(groups.counts(c,self.clock),{'new':1})
 def test_two_variants_maximum_then_rotate_material_on_later_day(self):
  with self.db.begin() as c:c.execute(text("UPDATE progress SET level=3,introduced=1,due_at=:t WHERE knowledge_id IN ('the-radio','my-friend','my-teacher')"),dict(t=(self.clock+timedelta(days=10)).isoformat()))
  first=self.finish();variants={k for kind,k in first if kind=='recall' and k.startswith('group-listen-') and k!='group-listen-basic'}
  self.assertEqual(len(variants),2)
  self.clock+=timedelta(days=2);app.save_settings({'daily-new-limit':0,'daily-review-limit':1})
  second=self.finish();self.assertIn(('recall','group-listen-teacher'),second)
  with self.db.connect() as c:
   self.assertEqual(c.execute(text("SELECT COUNT(*) FROM answers a JOIN group_questions q ON q.question_id=a.question_id WHERE q.role='transfer' AND date(a.created_at,'+8 hours')=:d"),dict(d=groups.day_of(self.clock))).scalar(),2)
 def test_first_context_word_owner_survives_restart_without_new_slot(self):
  with self.db.begin() as c:
   c.execute(text("INSERT INTO knowledge VALUES('shared-audio','音频','audio','音频','audio')"));c.execute(text("INSERT INTO progress(knowledge_id) VALUES('shared-audio')"))
   app.content.install(c);groups.install(c)
   c.execute(text("INSERT OR IGNORE INTO group_members VALUES('listen-to','shared-audio','word',0)"))
  with self.db.begin() as c:c.execute(text("UPDATE knowledge SET answer='listen to audio' WHERE id='listen-to-action'"))
  self.finish()
  with self.db.begin() as c:
   self.assertEqual(groups.family(c,'shared-audio'),'listen-to');groups.install(c)
   self.assertEqual(groups.family(c,'shared-audio'),'listen-to');self.assertEqual(groups.counts(c,self.clock),{'new':1})
 def test_unfinished_family_is_review_next_day_even_before_root_introduction(self):
  q=app.next_question();app.introduce(q['id']);self.correct(app.next_question())
  self.clock+=timedelta(days=1);app.save_settings({'daily-new-limit':0,'daily-review-limit':1})
  nxt=app.next_question();self.assertNotEqual(nxt['kind'],'done')
  with self.db.connect() as c:self.assertEqual(groups.counts(c,self.clock),{'review':1})
 def test_history_uses_current_group_schedule_for_shared_word(self):
  self.finish()
  future=(self.clock+timedelta(days=4)).isoformat()
  with self.db.begin() as c:c.execute(text("INSERT INTO group_progress VALUES('want-to',:d,:t,0)"),dict(d=future,t=self.clock.isoformat()))
  own=app.memory_history('word-i');other=app.memory_history('word-i',group_id='want-to')
  self.assertNotEqual(own['group_due_at'],other['group_due_at']);self.assertEqual(other['group_due_at'],future)
 def test_completed_legacy_bookings_do_not_hide_active_group_after_twelfth_row(self):
  q=app.next_question();app.introduce(q['id']);q=app.next_question();self.correct(q,'hard')
  with self.db.begin() as c:
   for i in range(11):
    gid='old-empty-'+str(i)
    c.execute(text("INSERT INTO learning_groups VALUES(:g,'word-i',:g,'word')"),dict(g=gid))
    c.execute(text("INSERT INTO daily_group_tasks VALUES('2026-11-01',:g,'review','word-i')"),dict(g=gid))
   c.execute(text("INSERT INTO daily_group_tasks VALUES('2026-11-01','look-at','new','look-at')"))
   c.execute(text("INSERT OR IGNORE INTO group_active_slots VALUES('look-at',:t)"),dict(t=self.clock.isoformat()))
   for i in range(10):c.execute(text('INSERT INTO group_active_slots VALUES(:g,:t)'),dict(g='other-active-'+str(i),t=self.clock.isoformat()))
  app.save_settings({'daily-new-limit':2})
  nxt=app.next_question();self.assertEqual(nxt['group_id'],'look-at');self.assertNotEqual(nxt['id'],q['id'])
  with self.db.connect() as c:self.assertEqual(c.execute(text('SELECT COUNT(*) FROM group_active_slots')).scalar(),12)
 def test_dashboard_history_keeps_original_question_group(self):
  q=app.next_question();app.introduce(q['id']);q=app.next_question();self.correct(q)
  row=next(h for h in app.dashboard()['history'] if h['question_id']==q['question_id'])
  self.assertEqual(row['group_id'],q['group_id']);self.assertEqual(row['group_title'],q['group_title'])
if __name__=='__main__':unittest.main()
