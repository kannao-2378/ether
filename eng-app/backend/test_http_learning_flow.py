"""HTTP request boundary smoke test, including random failures and clock advance."""
import random,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,text
import app

class HttpLearningTests(unittest.TestCase):
 def test_random_http_learning_restart_and_profile(self):
  rng=random.Random(6071)
  with tempfile.TemporaryDirectory() as folder:
   db=create_engine('sqlite:///'+str(Path(folder)/'http.db'));app.initialize(db)
   old=app.real_engine;app.real_engine=db
   clock=[datetime(2026,1,1,8,tzinfo=timezone.utc)]
   try:
    with patch('app.now',side_effect=lambda:clock[0]),TestClient(app.app) as client:
     self.assertEqual(client.post('/api/settings',json={'daily-new-limit':50,'daily-review-limit':50}).status_code,200)
     answers=0
     for _ in range(100):
      clock[0]+=timedelta(seconds=rng.randint(10,60))
      response=client.post('/api/next');self.assertEqual(response.status_code,200)
      q=response.json()
      if q['kind']=='done':break
      if q['kind']=='learn':
       self.assertEqual(client.post('/api/introduce/'+q['id']).status_code,200);continue
      self.assertEqual(client.post('/api/next').json()['question_id'],q['question_id'])
      k=client.get('/api/knowledge/'+q['id']).json()
      if rng.random()<.25:
       bad=client.post('/api/check',json={'id':str(_),'question_id':q['question_id'],'answer':'__wrong__'})
       self.assertFalse(bad.json()['correct'])
      if rng.random()<.15:self.assertEqual(client.post('/api/reveal/'+q['question_id']).status_code,200)
      body=dict(question_id=q['question_id'],answer=k['answer'],confidence=rng.choice(['clear','clear','hard','forgot']))
      result=client.post('/api/answers',json=body);self.assertEqual(result.status_code,200)
      self.assertEqual(client.post('/api/answers',json=body).json()['id'],result.json()['id']);answers+=1
     db.dispose();clock[0]+=timedelta(days=5)
     plan=client.get('/api/plan').json();self.assertEqual(plan['new_limit'],50);self.assertEqual(plan['review_limit'],50)
     profile=client.get('/api/profile').json();self.assertEqual(profile['summary']['completed'],answers)
     self.assertEqual(len(profile['memory_curve']['points']),121)
     self.assertEqual(client.post('/api/next').status_code,200)
     self.assertIn('consolidation_slots',client.get('/api/export').json()['tables'])
   finally:app.real_engine=old;db.dispose()
