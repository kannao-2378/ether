"""Today's extra new-learning quota persists, expires by day, and is idempotent."""
import tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from sqlalchemy import create_engine,text
from fastapi.testclient import TestClient
import app
class ExtraLearningTests(unittest.TestCase):
 def setUp(self):
  self.folder=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.folder.name)/'extra.db'));app.initialize(self.db)
  self.engine_patch=patch.object(app,'real_engine',self.db);self.engine_patch.start()
  self.clock=datetime(2026,11,1,8,tzinfo=timezone.utc);self.clock_patch=patch('app.now',side_effect=lambda:self.clock);self.clock_patch.start()
  self.client=TestClient(app.app);self.client.post('/api/settings',json={'daily-new-limit':50,'daily-review-limit':0})
  with self.db.begin() as c:
   # The new budget counts families; create enough distinct units for a 50-unit case.
   for n in range(10):
    c.execute(text('INSERT INTO knowledge VALUES(:k,:a,:a,:a,:a)'),dict(k='quota-word-'+str(n),a='quotaword'+str(n)))
    c.execute(text('INSERT INTO progress(knowledge_id) VALUES(:k)'),dict(k='quota-word-'+str(n)))
   app.content.install(c);app.group_learning.install(c)
   for n in range(10):c.execute(text("INSERT OR IGNORE INTO course_items VALUES(:k,'materials',:p)"),dict(k='quota-word-'+str(n),p=1000+n))
   # Publish synthetic quota targets into the same registry; dictionary presence alone is insufficient.
   for n in range(10):
    c.execute(text("INSERT OR REPLACE INTO curriculum_goals VALUES(:k,'quota fixture',1,'ready','test')"),dict(k='quota-word-'+str(n)))
    c.execute(text("INSERT OR REPLACE INTO curriculum_paths VALUES('foundation','quota','quota','quota',999,:k,:n,1)"),dict(k='quota-word-'+str(n),n=n))
   units=c.execute(text('SELECT id,root_id FROM learning_groups LIMIT 50')).all()
   for gid,kid in units:
    c.execute(text("INSERT INTO daily_group_tasks VALUES('2026-11-01',:g,'new',:k)"),dict(g=gid,k=kid))
    c.execute(text("INSERT INTO daily_tasks VALUES('2026-11-01',:k,'new')"),dict(k=kid))
    c.execute(text('UPDATE progress SET introduced=1,level=5,due_at=:due WHERE knowledge_id=:k'),dict(k=kid,due=(self.clock+timedelta(days=10)).isoformat()))
    c.execute(text('UPDATE progress SET introduced=1,level=5,due_at=:d WHERE knowledge_id IN (SELECT knowledge_id FROM group_members WHERE group_id=:g)'),dict(g=gid,d=(self.clock+timedelta(days=10)).isoformat()))
    c.execute(text('INSERT INTO group_progress VALUES(:g,:d,:t,0)'),dict(g=gid,d=(self.clock+timedelta(days=10)).isoformat(),t=self.clock.isoformat()))

 def tearDown(self):
  self.client.close();self.clock_patch.stop();self.engine_patch.stop();self.db.dispose();self.folder.cleanup()
 def test_fifty_plus_ten_and_restart_and_tomorrow(self):
  self.assertEqual(self.client.post('/api/next').json()['kind'],'done')
  body={'id':'extension-12345','amount':10}
  self.assertEqual(self.client.post('/api/daily-extra',json=body).json()['new_limit'],60)
  self.assertEqual(self.client.post('/api/daily-extra',json=body).json()['new_limit'],60)
  self.assertEqual(self.client.get('/api/settings').json()['daily-new-limit'],50)
  self.assertEqual(self.client.get('/api/plan').json()['new_limit'],60)
  self.assertEqual(self.client.post('/api/next').json()['kind'],'learn')
  self.assertIn('daily_extensions',self.client.get('/api/export').json()['tables'])
  app.initialize(self.db)
  self.assertEqual(app.study_settings()['daily-new-limit'],60)
  self.clock+=timedelta(days=1)
  self.assertEqual(app.study_settings()['daily-new-limit'],50)
  self.assertEqual(self.client.post('/api/daily-extra',json=body).status_code,409)
 def test_twenty_and_fifty_choices(self):
  for amount in (20,50):
   with self.db.begin() as c:c.execute(text('DELETE FROM daily_extensions'))
   r=self.client.post('/api/daily-extra',json={'id':'extension-choice-'+str(amount),'amount':amount})
   self.assertEqual(r.status_code,200)
   self.assertEqual(r.json()['new_limit'],50+amount)
 def test_invalid_amount_and_conflicting_retries(self):
  for amount in [0,1,15,100,True,'10']:
   self.assertEqual(self.client.post('/api/daily-extra',json={'id':'extension-invalid','amount':amount}).status_code,422)
  self.client.post('/api/daily-extra',json={'id':'extension-valid','amount':20})
  self.assertEqual(self.client.post('/api/daily-extra',json={'id':'extension-valid','amount':50}).status_code,409)
  self.assertEqual(self.client.post('/api/daily-extra',json={'id':'extension-next','amount':10}).status_code,409)
if __name__=='__main__':unittest.main()
