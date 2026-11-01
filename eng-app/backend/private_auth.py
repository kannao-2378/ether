"""Independent single-owner login. Opaque revocable sessions; no shared portfolio login."""
import hashlib,hmac,os,secrets,sqlite3,threading,time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse
from fastapi.responses import JSONResponse

ITERATIONS=600_000
COOKIE='pels_session'

def password_hash(password):
 salt=secrets.token_bytes(16)
 digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,ITERATIONS)
 return f'pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}'

class PrivateAuth:
 def __init__(self,data,enabled=False,encoded='',origin='',cookie_path='/',secure=True):
  self.enabled=enabled;self.encoded=encoded;self.origin=origin.rstrip('/');self.path=cookie_path
  self.secure=secure;self.db=Path(data)/'auth.db';self.failures={};self.lock=threading.Lock();self.lifetime=14*86400
  if not enabled:return
  try:
   scheme,iterations,salt,digest=encoded.split('$')
   if not (scheme=='pbkdf2_sha256' and 200000<=int(iterations)<=2000000 and len(bytes.fromhex(salt))>=16 and len(bytes.fromhex(digest))==32):raise ValueError('Invalid password hash')
   parsed=urlparse(self.origin)
   if not (parsed.scheme=='https' and parsed.hostname and not parsed.path and not parsed.username and not parsed.query and not parsed.fragment):raise ValueError('Invalid public origin')
   if not (cookie_path.startswith('/') and cookie_path.endswith('/')):raise ValueError('Invalid cookie path')
  except Exception:raise RuntimeError('Login configuration invalid: set a PBKDF2 password hash, HTTPS public origin and cookie path') from None
  self.db.parent.mkdir(parents=True,exist_ok=True)
  with self.connection() as c:
   c.execute('CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,csrf TEXT NOT NULL,expires REAL NOT NULL,credential TEXT NOT NULL)')
 @contextmanager
 def connection(self):
  c=sqlite3.connect(self.db,timeout=10)
  try:
   with c:yield c
  finally:c.close()
 @classmethod
 def from_env(cls,data):
  return cls(data,os.environ.get('PELS_AUTH_ENABLED')=='1',os.environ.get('PELS_AUTH_PASSWORD_HASH',''),os.environ.get('PELS_PUBLIC_ORIGIN',''),os.environ.get('PELS_COOKIE_PATH','/'),True)
 def session(self,request):
  token=request.cookies.get(COOKIE,'')
  if not token or len(token)>200:return None
  with self.connection() as c:
   row=c.execute('SELECT csrf,expires,credential FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
  if not row or row[1]<=time.time() or not hmac.compare_digest(row[2],hashlib.sha256(self.encoded.encode()).hexdigest()):return None
  return dict(csrf=row[0],expires=row[1])
 def guard(self,request):
  if not self.enabled:return None
  path=request.url.path
  if path.startswith('/api/test') or request.headers.get('X-Learning-Test')=='1':
   return JSONResponse({'detail':'线上环境不开放测试模式'},403)
  if path=='/api/health' or path in ('/api/auth/status','/api/auth/login'):
   if path.endswith('/login') and request.method=='POST' and request.headers.get('origin','').rstrip('/')!=self.origin:
    return JSONResponse({'detail':'登录来源无效'},403)
   return None
  if not path.startswith('/api/'):
   return JSONResponse({'detail':'Not found'},404)
  session=self.session(request)
  if not session:return JSONResponse({'detail':'请先登录'},401)
  if request.method not in ('GET','HEAD','OPTIONS'):
   if request.headers.get('origin','').rstrip('/')!=self.origin or not hmac.compare_digest(request.headers.get('X-CSRF-Token','').encode(),session['csrf'].encode()):
    return JSONResponse({'detail':'请求验证失败，请刷新后重试'},403)
  return None
 def status(self,request):
  if not self.enabled:return dict(enabled=False,authenticated=True)
  session=self.session(request)
  return dict(enabled=True,authenticated=bool(session),csrf=session['csrf'] if session else None)
 def login(self,request,password):
  if not self.enabled:return JSONResponse(dict(enabled=False,authenticated=True))
  address=request.client.host if request.client else 'unknown';now=time.time()
  with self.lock:
   self.failures={k:[t for t in v if now-t<900] for k,v in self.failures.items() if any(now-t<900 for t in v)}
   recent=self.failures.get(address,[])
   if len(recent)>=5:return JSONResponse({'detail':'尝试过多，请15分钟后再试'},429,headers={'Retry-After':'900'})
   # Reserve an attempt before hashing so parallel requests cannot bypass the limit.
   if len(self.failures)>=2048 and address not in self.failures:return JSONResponse({'detail':'请稍后重试'},429)
   self.failures[address]=recent+[now]
  _,iterations,salt,expected=self.encoded.split('$')
  actual=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),int(iterations)).hex()
  if not hmac.compare_digest(actual,expected):return JSONResponse({'detail':'密码不正确'},401)
  with self.lock:self.failures.pop(address,None)
  token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
  with self.connection() as c:
   c.execute('DELETE FROM sessions WHERE expires<=?',(now,))
   c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),csrf,now+self.lifetime,hashlib.sha256(self.encoded.encode()).hexdigest()))
  response=JSONResponse(dict(enabled=True,authenticated=True,csrf=csrf))
  response.set_cookie(COOKIE,token,max_age=self.lifetime,secure=self.secure,httponly=True,samesite='lax',path=self.path)
  return response
 def logout(self,request):
  if self.enabled:
   with self.connection() as c:c.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(request.cookies.get(COOKIE,'').encode()).hexdigest(),))
  response=JSONResponse(dict(saved=True));response.delete_cookie(COOKIE,path=self.path,secure=self.secure,httponly=True,samesite='lax');return response
