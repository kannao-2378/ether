import unittest
from datetime import datetime,timedelta,timezone
from sqlalchemy import create_engine,text
from scheduler import rebuild,choose,select_next,update_coverage

class ScheduleTests(unittest.TestCase):
 def setUp(self):
  self.engine=create_engine('sqlite://')
  self.c=self.engine.connect();self.tx=self.c.begin()
  for sql in [
   'CREATE TABLE answers(id TEXT,question_id TEXT,knowledge_id TEXT,correct INTEGER,revealed INTEGER,confidence TEXT,created_at TEXT)',
   'CREATE TABLE spelling_checks(question_id TEXT,correct INTEGER,created_at TEXT)',
   'CREATE TABLE feedback_events(question_id TEXT,confidence TEXT)',
   'CREATE TABLE progress(knowledge_id TEXT,attempts INTEGER,correct INTEGER,streak INTEGER,level INTEGER,interval_days REAL,due_at TEXT,last_at TEXT)',
   'CREATE TABLE review_queue(knowledge_id TEXT PRIMARY KEY,due_sequence INTEGER,due_at TEXT,gap INTEGER,version INTEGER)']:
   self.c.execute(text(sql))
  self.c.execute(text('CREATE TABLE transfer_materials(knowledge_id TEXT,material_id TEXT)'))
  self.c.execute(text('CREATE TABLE test_skips(question_id TEXT PRIMARY KEY,created_at TEXT)'))
  self.c.execute(text('CREATE TABLE course_links(knowledge_id TEXT PRIMARY KEY,parent_id TEXT,stage INTEGER,source TEXT)'))
  self.c.execute(text("INSERT INTO progress(knowledge_id) VALUES ('a')"))
  self.t=datetime(2026,10,31,tzinfo=timezone.utc)
 def tearDown(self):self.tx.rollback();self.c.close();self.engine.dispose()
 def answer(self,rating='clear',stamp=None,kid='a'):
  n=self.c.execute(text('SELECT COUNT(*) FROM answers')).scalar()+1
  self.c.execute(text('INSERT INTO answers VALUES (:id,:q,:k,1,0,:r,:t)'),dict(id=str(n),q=str(n),k=kid,r=rating,t=(stamp or self.t).isoformat()))
  rebuild(self.c,kid)
  return str(n)
 def queue(self):return self.c.execute(text("SELECT * FROM review_queue WHERE knowledge_id='a'")).mappings().one()
 def test_feedback_gaps(self):
  for rating,gap in [('clear',8),('hard',4),('forgot',2)]:
   q=self.answer(rating);self.assertEqual(self.queue()['gap'],gap)
   self.assertEqual(self.queue()['due_sequence'],int(q)+gap+1)
 def test_exact_other_question_count(self):
  self.answer('forgot');rows=[dict(id='a',introduced=1,due_at=None)]
  self.assertFalse(choose(self.c,rows,self.t)[0])
  self.answer(kid='b');self.assertFalse(choose(self.c,rows,self.t)[0])
  self.answer(kid='b');self.assertTrue(choose(self.c,rows,self.t)[0])
 def test_correction_replays_without_extra_attempt(self):
  q=self.answer('clear')
  self.c.execute(text("INSERT INTO feedback_events VALUES (:q,'forgot')"),dict(q=q));rebuild(self.c,'a')
  self.assertEqual(self.queue()['gap'],2)
  self.assertEqual(self.c.execute(text("SELECT attempts FROM progress WHERE knowledge_id='a'")).scalar(),1)
 def test_next_day_verification(self):
  for _ in range(3):self.answer()
  due=self.queue()['due_at'];self.assertGreaterEqual(datetime.fromisoformat(due),self.t+timedelta(days=1))
  rows=[dict(id='a',introduced=1,due_at=due)]
  self.assertFalse(choose(self.c,rows,self.t)[1])
  self.answer(stamp=self.t+timedelta(days=1))
  self.assertEqual(self.c.execute(text("SELECT level FROM progress WHERE knowledge_id='a'")).scalar(),5)
 def test_prompted_success_not_mastered(self):
  q=self.answer();self.c.execute(text("UPDATE answers SET revealed=1 WHERE question_id=:q"),dict(q=q));rebuild(self.c,'a')
  self.assertEqual(self.queue()['gap'],4);self.assertIsNone(self.queue()['due_at'])
 def test_no_repeat_from_refresh(self):
  self.answer('hard');before=dict(self.queue());rebuild(self.c,'a');self.assertEqual(before,dict(self.queue()))
 def test_incremental_matches_full_replay(self):
  self.answer()
  for n,rating in enumerate(['hard','clear','clear','clear','forgot'],start=2):
   self.c.execute(text('INSERT INTO answers VALUES (:q,:q,\'a\',1,0,:r,:t)'),dict(q=str(n),r=rating,t=self.t.isoformat()))
   rebuild(self.c,'a',incremental=True)
   incremental=dict(self.queue())
   progress=dict(self.c.execute(text("SELECT * FROM progress WHERE knowledge_id='a'")).mappings().one())
   rebuild(self.c,'a')
   self.assertEqual(incremental,dict(self.queue()))
   self.assertEqual(progress,dict(self.c.execute(text("SELECT * FROM progress WHERE knowledge_id='a'")).mappings().one()))
 def prepare_selection(self):
  self.c.execute(text('ALTER TABLE progress ADD COLUMN introduced INTEGER DEFAULT 1'))
  self.c.execute(text('CREATE TABLE knowledge(id TEXT PRIMARY KEY)'))
  for kid in ['a','b','c']:
   self.c.execute(text('INSERT INTO knowledge VALUES (:k)'),dict(k=kid))
   if kid!='a':self.c.execute(text('INSERT INTO progress(knowledge_id,introduced) VALUES (:k,1)'),dict(k=kid))
 def test_daily_review_cap_and_next_day_reset(self):
  self.prepare_selection()
  kind,item=select_next(self.c,self.t,1,0);self.assertEqual(item['id'],'a')
  # Repeat does not consume a second slot.
  select_next(self.c,self.t,1,0)
  self.assertEqual(self.c.execute(text('SELECT COUNT(*) FROM daily_tasks')).scalar(),1)
  self.c.execute(text("UPDATE progress SET due_at=:d WHERE knowledge_id='a'"),dict(d=(self.t+timedelta(days=3)).isoformat()))
  self.assertEqual(select_next(self.c,self.t,1,0)[0],'done')
  self.assertEqual(select_next(self.c,self.t+timedelta(days=1),1,0)[1]['id'],'b')
 def test_new_content_cap(self):
  self.prepare_selection();self.c.execute(text('UPDATE progress SET introduced=0'))
  self.assertEqual(select_next(self.c,self.t,0,1)[0],'learn')
  self.c.execute(text("UPDATE progress SET introduced=1,due_at=:d WHERE knowledge_id='a'"),dict(d=(self.t+timedelta(days=3)).isoformat()))
  self.assertEqual(select_next(self.c,self.t,0,1)[0],'done')
 def test_sentence_unlocks_after_independent_recall(self):
  self.prepare_selection()
  self.c.execute(text("UPDATE progress SET introduced=0 WHERE knowledge_id='b'"))
  self.c.execute(text("UPDATE progress SET due_at=:t WHERE knowledge_id IN ('a','c')"),dict(t=(self.t+timedelta(days=3)).isoformat()))
  self.c.execute(text("INSERT INTO course_links VALUES ('b','a',2,'test')"))
  self.c.execute(text("UPDATE progress SET level=2 WHERE knowledge_id='a'"))
  self.assertEqual(select_next(self.c,self.t,5,5)[0],'done')
  self.c.execute(text("UPDATE progress SET level=3 WHERE knowledge_id='a'"))
  self.assertEqual(select_next(self.c,self.t,5,5)[1]['id'],'b')
 def test_sentence_covers_parent_and_correction_restores(self):
  self.prepare_selection()
  self.c.execute(text("INSERT INTO course_links VALUES('b','a',2,'test')"))
  self.c.execute(text("INSERT INTO course_links VALUES('c','b',3,'test')"))
  q=self.answer(kid='c')
  update_coverage(self.c,'c',self.t)
  self.assertEqual(self.c.execute(text('SELECT COUNT(*) FROM daily_coverage')).scalar(),2)
  self.c.execute(text("UPDATE progress SET due_at=:d WHERE knowledge_id='c'"),dict(d=(self.t+timedelta(days=3)).isoformat()))
  self.c.execute(text("DELETE FROM review_queue WHERE knowledge_id='c'"))
  self.assertEqual(select_next(self.c,self.t,5,5)[0],'done')
  self.c.execute(text("INSERT INTO feedback_events VALUES(:q,'hard')"),dict(q=q))
  update_coverage(self.c,'c',self.t)
  self.assertEqual(self.c.execute(text('SELECT COUNT(*) FROM daily_coverage')).scalar(),0)
  self.assertEqual(select_next(self.c,self.t,5,5)[0],'recall')
 def test_prompted_sentence_does_not_cover(self):
  self.c.execute(text("INSERT INTO course_links VALUES('b','a',2,'test')"))
  q=self.answer(kid='b')
  self.c.execute(text('UPDATE answers SET revealed=1 WHERE question_id=:q'),dict(q=q))
  update_coverage(self.c,'b',self.t)
  self.assertEqual(self.c.execute(text('SELECT COUNT(*) FROM daily_coverage')).scalar(),0)


 def test_fsrs_persisted_and_delayed_replay(self):
  for _ in range(3):self.answer()
  self.answer(stamp=self.t+timedelta(days=1))
  before=dict(self.queue())
  memory=self.c.execute(text("SELECT * FROM memory_states WHERE knowledge_id='a'")).mappings().one()
  self.assertEqual(memory['algorithm'],'FSRS-6')
  import json
  self.assertGreater(json.loads(memory['card_json'])['stability'],0)
  rebuild(self.c,'a',incremental=True)
  self.assertEqual(before,dict(self.queue()))
  rebuild(self.c,'a')
  self.assertEqual(before,dict(self.queue()))
  self.c.execute(text("INSERT INTO feedback_events VALUES ('4','forgot')"))
  rebuild(self.c,'a')
  self.assertIsNone(self.queue()['due_at'])
  self.assertEqual(self.queue()['gap'],2)

 def test_due_times_compare_actual_instants_across_offsets(self):
  self.prepare_selection()
  self.c.execute(text("UPDATE progress SET due_at='2026-10-31T09:00:00+08:00'"))
  # At 02:00 UTC, 09:00 China time has already passed by one hour.
  kind,item=select_next(self.c,self.t+timedelta(hours=2),5,0)
  self.assertEqual(kind,'recall')
  self.assertIsNotNone(item)

 def test_incremental_catches_all_unprocessed_answers(self):
  self.answer()
  for n in (2,3):
   self.c.execute(text("INSERT INTO answers VALUES(:q,:q,'a',1,0,'clear',:t)"),dict(q=str(n),t=self.t.isoformat()))
  rebuild(self.c,'a',incremental=True)
  before=dict(self.queue())
  p=dict(self.c.execute(text("SELECT * FROM progress WHERE knowledge_id='a'")).mappings().one())
  rebuild(self.c,'a')
  self.assertEqual(before,dict(self.queue()))
  self.assertEqual(p,dict(self.c.execute(text("SELECT * FROM progress WHERE knowledge_id='a'")).mappings().one()))

 def test_independent_new_words_are_not_starved_by_ready_reviews(self):
  self.prepare_selection()
  self.c.execute(text("INSERT INTO knowledge VALUES('d')"))
  self.c.execute(text("INSERT INTO progress(knowledge_id,introduced,due_at) VALUES('d',1,:t)"),dict(t=(self.t+timedelta(days=1)).isoformat()))
  self.c.execute(text("UPDATE progress SET introduced=0 WHERE knowledge_id IN ('b','c')"))
  self.c.execute(text("UPDATE progress SET due_at=:t WHERE knowledge_id='a'"),dict(t=(self.t-timedelta(days=1)).isoformat()))
  # Cross-day due reviews still take priority. Clear it into today's practice.
  self.c.execute(text("UPDATE progress SET due_at=NULL WHERE knowledge_id='a'"))
  first=select_next(self.c,self.t,10,10)
  self.assertEqual((first[0],first[1]['id']),('learn','b'))
  self.c.execute(text("UPDATE progress SET introduced=1,due_at=:t WHERE knowledge_id='b'"),dict(t=(self.t+timedelta(days=1)).isoformat()))
  self.assertEqual(select_next(self.c,self.t,10,10)[0],'recall')
  for n in ('one','two'):
   self.c.execute(text("INSERT INTO answers VALUES(:q,:q,'a',1,0,'clear',:t)"),dict(q=n,t=self.t.isoformat()))
  self.assertEqual(select_next(self.c,self.t,10,10)[1]['id'],'c')

 def test_twelve_consolidation_items_pause_new_and_release_slot(self):
  self.prepare_selection()
  self.c.execute(text('CREATE TABLE daily_coverage(day TEXT,knowledge_id TEXT,source_question_id TEXT)'))
  self.c.execute(text('UPDATE progress SET attempts=1,introduced=1'))
  for i in range(9):
   self.c.execute(text('INSERT INTO knowledge VALUES(:k)'),dict(k='old'+str(i)))
   self.c.execute(text('INSERT INTO progress(knowledge_id,introduced,attempts) VALUES(:k,1,1)'),dict(k='old'+str(i)))
  self.c.execute(text("INSERT INTO knowledge VALUES('fresh')"))
  self.c.execute(text("INSERT INTO progress(knowledge_id,introduced,attempts) VALUES('fresh',0,0)"))
  from scheduler import consolidation_count
  self.assertEqual(consolidation_count(self.c,self.t),12)
  self.assertEqual(select_next(self.c,self.t,50,50)[0],'recall')
  # A scheduled item no longer occupies a consolidation slot.
  self.c.execute(text("INSERT INTO review_queue VALUES('a',0,:t,8,5)"),dict(t=(self.t+timedelta(days=1)).isoformat()))
  self.assertEqual(consolidation_count(self.c,self.t),11)
  result=select_next(self.c,self.t,50,50)
  self.assertEqual((result[0],result[1]['id']),('learn','fresh'))
  # Refresh/reconnect must derive the same count from persisted progress.
  self.assertEqual(consolidation_count(self.c,self.t+timedelta(days=1)),11)

 def test_coverage_does_not_erase_unfinished_consolidation_slots(self):
  self.prepare_selection()
  self.c.execute(text('CREATE TABLE daily_coverage(day TEXT,knowledge_id TEXT,source_question_id TEXT)'))
  self.c.execute(text("INSERT INTO daily_coverage VALUES('2026-10-31','a','source')"))
  from scheduler import consolidation_count
  self.assertEqual(consolidation_count(self.c,self.t),3)
  self.assertEqual(consolidation_count(self.c,self.t+timedelta(days=1)),3)

 def test_full_pool_does_not_admit_another_delayed_review(self):
  self.prepare_selection()
  self.c.execute(text('UPDATE progress SET introduced=1,attempts=1'))
  for i in range(9):
   k='pending'+str(i)
   self.c.execute(text('INSERT INTO knowledge VALUES(:k)'),dict(k=k))
   self.c.execute(text('INSERT INTO progress(knowledge_id,introduced,attempts) VALUES(:k,1,1)'),dict(k=k))
  self.c.execute(text("INSERT INTO knowledge VALUES('delayed')"))
  self.c.execute(text("INSERT INTO progress(knowledge_id,introduced,attempts,due_at) VALUES('delayed',1,4,:t)"),dict(t=(self.t-timedelta(days=1)).isoformat()))
  self.c.execute(text("INSERT INTO review_queue VALUES('delayed',0,:t,8,5)"),dict(t=(self.t-timedelta(days=1)).isoformat()))
  kind,item=select_next(self.c,self.t,50,50)
  self.assertEqual(kind,'recall');self.assertNotEqual(item['id'],'delayed')

 def test_feedback_return_waits_without_creating_thirteenth_active_slot(self):
  self.prepare_selection()
  self.c.execute(text('UPDATE progress SET introduced=1,attempts=1'))
  for i in range(10):
   k='pending'+str(i)
   self.c.execute(text('INSERT INTO knowledge VALUES(:k)'),dict(k=k))
   self.c.execute(text('INSERT INTO progress(knowledge_id,introduced,attempts) VALUES(:k,1,1)'),dict(k=k))
  from scheduler import consolidation_count,consolidation_pending
  self.assertEqual(len(consolidation_pending(self.c,self.t)),13)
  self.assertEqual(consolidation_count(self.c,self.t),12)
  self.assertEqual(self.c.execute(text('SELECT COUNT(*) FROM consolidation_slots')).scalar(),12)
  waiting=self.c.execute(text('SELECT knowledge_id FROM progress WHERE knowledge_id NOT IN (SELECT knowledge_id FROM consolidation_slots)')).scalar()
  self.assertNotEqual(select_next(self.c,self.t,50,50)[1]['id'],waiting)
  occupied=self.c.execute(text('SELECT knowledge_id FROM consolidation_slots LIMIT 1')).scalar()
  self.c.execute(text('INSERT INTO review_queue VALUES(:k,0,:t,8,5)'),dict(k=occupied,t=(self.t+timedelta(days=1)).isoformat()))
  self.assertEqual(consolidation_count(self.c,self.t),12)
  self.assertTrue(self.c.execute(text('SELECT 1 FROM consolidation_slots WHERE knowledge_id=:k'),dict(k=waiting)).first())
  self.assertEqual(len(consolidation_pending(self.c,self.t)),12)

 def test_covered_tasks_do_not_refund_daily_fifty_slot_quota(self):
  self.prepare_selection()
  self.c.execute(text('CREATE TABLE daily_tasks(day TEXT,knowledge_id TEXT,kind TEXT,PRIMARY KEY(day,knowledge_id))'))
  self.c.execute(text('CREATE TABLE daily_coverage(day TEXT,knowledge_id TEXT,source_question_id TEXT)'))
  self.c.execute(text('UPDATE progress SET introduced=0'))
  for i in range(50):
   self.c.execute(text("INSERT INTO daily_tasks VALUES('2026-10-31',:k,'new')"),dict(k='seen'+str(i)))
   self.c.execute(text("INSERT INTO daily_coverage VALUES('2026-10-31',:k,'sentence')"),dict(k='seen'+str(i)))
  self.assertEqual(select_next(self.c,self.t,50,50)[0],'done')
