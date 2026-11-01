import unittest,tempfile,uuid
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from sqlalchemy import create_engine,text
import app
class DailyActivityTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.tmp.name)/'test.db'));app.initialize(self.db)
  self.clock=datetime(2026,11,1,16,30,tzinfo=timezone.utc)
  self.ep=patch.object(app,'real_engine',self.db);self.ep.start();self.tp=patch('app.now',side_effect=lambda:self.clock);self.tp.start()
 def tearDown(self):self.tp.stop();self.ep.stop();self.db.dispose();self.tmp.cleanup()
 def test_preview_is_read_only_and_matches_next_group(self):
  with self.db.connect() as c:before=c.execute(text('SELECT COUNT(*) FROM daily_group_tasks')).scalar()
  report=app.daily_activity_report(planning=True);self.assertTrue(report['preview_new'])
  with self.db.connect() as c:self.assertEqual(before,c.execute(text('SELECT COUNT(*) FROM daily_group_tasks')).scalar())
  q=app.next_question();self.assertEqual(report['preview_new'][0]['id'],q['group_id'])
 def test_daily_results_timezone_feedback_and_history(self):
  q=app.next_question()
  if q['kind']=='learn':app.introduce(q['id']);q=app.next_question()
  answer=app.knowledge_content(q['id'])['answer']
  app.submit(app.Submission(question_id=q['question_id'],answer=answer,confidence='hard'))
  report=app.daily_activity_report();self.assertEqual(report['date'],'2026-11-02');self.assertEqual(report['attempts'],1);self.assertEqual(report['feedback']['hard'],1);self.assertEqual(report['items'][0]['english'],answer);self.assertEqual(sum(report['type_counts'].values()),1);self.assertEqual(report['studied_groups'],1)
  q2=app.next_question()
  if q2['kind']=='recall' and q2['id']==q['id']:
   app.submit(app.Submission(question_id=q2['question_id'],answer=answer,confidence='hard'));again=app.daily_activity_report();self.assertEqual(sum(again['type_counts'].values()),1)
  self.assertEqual(app.daily_activity_report(day='2026-11-01')['attempts'],0)
  self.clock+=timedelta(days=1);self.assertEqual(app.daily_activity_report(day='2026-11-02')['attempts'],1)
 def test_invalid_dates(self):
  for day in ['bad','2026-11-03','2026-1-1']:
   with self.assertRaises(app.HTTPException):app.daily_activity_report(day=day)
