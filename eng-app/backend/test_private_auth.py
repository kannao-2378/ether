import tempfile,unittest,time
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
import app
from private_auth import PrivateAuth,password_hash,COOKIE

class PrivateAuthTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.encoded=password_hash('Test password only 8294!')
 def setUp(self):
  self.folder=tempfile.TemporaryDirectory();self.old=app.AUTH
  self.auth=PrivateAuth(self.folder.name,True,self.encoded,'https://learn.example','/')
  app.AUTH=self.auth;self.client=TestClient(app.app,base_url='https://learn.example')
 def tearDown(self):self.client.close();app.AUTH=self.old;self.folder.cleanup()
 def login(self):
  r=self.client.post('/api/auth/login',json={'password':'Test password only 8294!'},headers={'Origin':'https://learn.example'})
  self.assertEqual(r.status_code,200);return r.json()['csrf']
 def test_all_learning_endpoints_require_login(self):
  for path in ['/api/dashboard','/api/profile','/api/plan','/api/export','/api/knowledge/word-drink','/api/pronunciation/oxford-us?word=drink','/api/pronunciation/device-us?text_value=want%20to']:
   self.assertEqual(self.client.get(path).status_code,401,path)
  self.assertEqual(self.client.post('/api/next').status_code,401)
  self.assertEqual(self.client.get('/api/health').status_code,200)
  self.assertFalse(self.client.get('/api/auth/status').json()['authenticated'])
 def test_login_csrf_origin_logout_and_revocation(self):
  csrf=self.login();cookie=self.client.cookies.get(COOKIE)
  self.assertTrue(self.client.get('/api/auth/status').json()['authenticated'])
  self.assertEqual(self.client.post('/api/auth/logout').status_code,403)
  self.assertEqual(self.client.post('/api/auth/logout',headers={'Origin':'https://evil.example','X-CSRF-Token':csrf}).status_code,403)
  self.assertEqual(self.client.post('/api/auth/logout',headers={'Origin':'https://learn.example','X-CSRF-Token':csrf}).status_code,200)
  self.assertFalse(self.client.get('/api/auth/status').json()['authenticated'])
  self.assertEqual(self.client.get('/api/profile',headers={'Cookie':COOKIE+'='+cookie}).status_code,401)
 def test_cookie_flags_and_english_scope(self):
  app.AUTH=PrivateAuth(self.folder.name,True,self.encoded,'https://learn.example','/english/')
  r=self.client.post('/api/auth/login',json={'password':'Test password only 8294!'},headers={'Origin':'https://learn.example'})
  value=r.headers['set-cookie'].lower()
  for flag in ['httponly','secure','samesite=lax','path=/english/']:self.assertIn(flag,value)
 def test_failed_login_rate_limit_and_cross_origin_login(self):
  self.assertEqual(self.client.post('/api/auth/login',json={'password':'bad'},headers={'Origin':'https://evil.example'}).status_code,403)
  for _ in range(5):self.assertEqual(self.client.post('/api/auth/login',json={'password':'bad'},headers={'Origin':'https://learn.example'}).status_code,401)
  self.assertEqual(self.client.post('/api/auth/login',json={'password':'bad'},headers={'Origin':'https://learn.example'}).status_code,429)
 def test_expiry_test_mode_and_password_change(self):
  self.login()
  self.assertEqual(self.client.get('/api/test/status').status_code,403)
  self.assertEqual(self.client.get('/api/profile',headers={'X-Learning-Test':'1'}).status_code,403)
  with patch('private_auth.time.time',return_value=time.time()+15*86400):self.assertEqual(self.client.get('/api/profile').status_code,401)
  app.AUTH=PrivateAuth(self.folder.name,True,password_hash('Another test password 123!'),'https://learn.example','/')
  self.assertEqual(self.client.get('/api/profile').status_code,401)
 def test_missing_configuration_fails_closed(self):
  with self.assertRaises(RuntimeError):PrivateAuth(self.folder.name,True,'','https://learn.example','/')
