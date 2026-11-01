import unittest,tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
from sqlalchemy import create_engine,text
import app,learning_stats

class LearningStatsTests(unittest.TestCase):
 def setUp(self):
  self.folder=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.folder.name)/'stats.db'));app.initialize(self.db);self.n=0;self.now=datetime(2026,10,9,8,tzinfo=timezone.utc)
 def tearDown(self):self.db.dispose();self.folder.cleanup()
 def answer(self,c,kid='want-to',rating='clear',day=0,hint=0,failed=False,skip=False,at=None):
  self.n+=1;q=str(self.n);stamp=(at or self.now+timedelta(days=day)).isoformat()
  c.execute(text('INSERT INTO questions VALUES(:q,:k,:t,:h)'),dict(q=q,k=kid,t=stamp,h=hint))
  c.execute(text("INSERT INTO answers VALUES(:q,:q,:k,'answer',1,:h,:r,:t,NULL,'')"),dict(q=q,k=kid,t=stamp,h=hint,r=rating))
  c.execute(text('UPDATE progress SET introduced=1,attempts=attempts+1,last_at=:t WHERE knowledge_id=:k'),dict(k=kid,t=stamp))
  if failed:c.execute(text("INSERT INTO spelling_checks VALUES(:q,:q,'wrong',0,:t)"),dict(q=q,t=stamp))
  if skip:c.execute(text('INSERT INTO test_skips VALUES(:q,:t)'),dict(q=q,t=stamp))
  return q
 def test_empty_profile_no_invented_rate_or_days(self):
  with self.db.connect() as c:r=learning_stats.build(c,self.now)
  self.assertEqual(r['summary']['completed'],0);self.assertIsNone(r['summary']['independent_rate']);self.assertEqual(r['summary']['active_days'],0);self.assertEqual(len(r['trend']),30)
  self.assertEqual(sum(m['count'] for m in r['mastery']),r['summary']['total'])
 def test_hints_failures_and_skips_not_independent(self):
  with self.db.begin() as c:
   self.answer(c);self.answer(c,hint=1);self.answer(c,failed=True);self.answer(c,rating='hard');self.answer(c,skip=True)
   r=learning_stats.build(c,self.now)
  self.assertEqual(r['summary']['completed'],4);self.assertEqual(r['summary']['independent'],1);self.assertEqual(r['summary']['independent_rate'],.25);self.assertEqual(r['summary']['hinted'],1);self.assertEqual(r['summary']['spelling_failed'],1)
 def test_feedback_correction_updates_stats_without_extra_attempt(self):
  with self.db.begin() as c:
   q=self.answer(c);before=learning_stats.build(c,self.now)
   c.execute(text("INSERT INTO feedback_events VALUES('f',:q,'forgot',:t)"),dict(q=q,t=self.now.isoformat()))
   after=learning_stats.build(c,self.now)
  self.assertEqual(before['summary']['independent'],1);self.assertEqual(after['summary']['completed'],1);self.assertEqual(after['summary']['independent'],0);self.assertEqual(after['feedback']['forgot'],1);self.assertEqual(after['weak_total'],1)
 def test_china_midnight_and_streak(self):
  self.now=datetime(2026,11,1,8,tzinfo=timezone.utc)
  with self.db.begin() as c:
   self.answer(c,at=datetime(2026,10,31,15,30,tzinfo=timezone.utc));self.answer(c,at=datetime(2026,10,31,16,30,tzinfo=timezone.utc))
   r=learning_stats.build(c,self.now)
  self.assertEqual(r['summary']['active_days'],2);self.assertEqual(r['summary']['streak'],2);self.assertEqual(r['trend'][-1]['attempts'],1);self.assertEqual(r['trend'][-2]['attempts'],1)
 def test_stable_needs_evidence_and_types_share_records(self):
  with self.db.begin() as c:
   for day in (-8,-7,0):self.answer(c,kid='word-drink',day=day)
   c.execute(text("UPDATE progress SET introduced=1,level=5 WHERE knowledge_id='want-to'"))
   r=learning_stats.build(c,self.now)
  self.assertEqual(next(m['count'] for m in r['mastery'] if m['label']=='稳固'),1)
  word=next(t for t in r['types'] if t['kind']=='word');self.assertEqual(word['stable'],1)
  self.assertEqual(r['summary']['touched'],2)

 def test_memory_curve_defaults_and_real_state_updates(self):
  from scheduler import rebuild
  with self.db.begin() as c:
   initial=learning_stats.build(c,self.now)['memory_curve']
   self.assertEqual(initial['mode'],'default_prediction')
   self.assertEqual(initial['delayed_samples'],0)
   self.assertEqual(initial['items'],0)
   self.assertTrue(all(p['personal']==p['default'] for p in initial['points']))
   self.answer(c,day=-2);rebuild(c,'want-to')
   first=learning_stats.build(c,self.now)['memory_curve']
   self.answer(c);rebuild(c,'want-to')
   second=learning_stats.build(c,self.now)['memory_curve']
   self.assertEqual(second['items'],1)
   self.assertEqual(second['delayed_samples'],1)
   self.assertEqual(second['observations'][0]['rate'],1)
   self.assertGreater(second['points'][28]['personal'],first['points'][28]['personal'])
   c.execute(text("INSERT INTO feedback_events VALUES('curve-f','2','forgot',:t)"),dict(t=self.now.isoformat()))
   rebuild(c,'want-to')
   corrected=learning_stats.build(c,self.now)['memory_curve']
   self.assertEqual(corrected['delayed_samples'],1)
   self.assertEqual(corrected['observations'][0]['rate'],0)
   self.assertLess(corrected['points'][28]['personal'],second['points'][28]['personal'])
   self.assertTrue(all(0<=p['personal']<=1 for p in corrected['points']))
   self.assertTrue(all(corrected['points'][i]['personal']>=corrected['points'][i+1]['personal'] for i in range(120)))

 def test_curve_excludes_skips_same_day_and_future(self):
  from scheduler import rebuild
  with self.db.begin() as c:
   self.answer(c,day=-2,skip=True);rebuild(c,'want-to')
   self.assertEqual(learning_stats.build(c,self.now)['memory_curve']['items'],0)
   self.answer(c);self.answer(c);self.answer(c,day=1)
   rebuild(c,'want-to')
   curve=learning_stats.build(c,self.now)['memory_curve']
   self.assertEqual(curve['items'],0)
   self.assertEqual(curve['delayed_samples'],0)

if __name__=='__main__':unittest.main()
