import spelling_practice
import time
import queue
import threading
import curriculum_engine
import composition_engine
import sourced_transfer
import starter_course
import user_courses
import mainline_runtime
import selection_cache
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import hashlib
import random
import re
import uuid
import os
from contextvars import ContextVar
from scheduler import rebuild, choose, select_next, update_coverage, install_memory, consolidation_count, CONSOLIDATION_LIMIT
from courses import install
import lesson
import transfer
import combinations
import context_engine
import word_lookup
import focus_training
import daily_activity
import group_learning
from learning_profile import familiarity,RULES
import assessment
import transfer_evidence
import content
import bulk_courses
import oxford_audio
import device_audio
from private_auth import PrivateAuth
import learning_stats as learning_profile_stats

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text, event
import response_cache

DATA = Path(os.environ.get('PELS_DATA_DIR',str(Path(__file__).parent / 'data')))
DATA.mkdir(parents=True,exist_ok=True)
AUTH=PrivateAuth.from_env(DATA)
def _sqlite_engine(path):
 e=create_engine(f'sqlite:///{path}')
 @event.listens_for(e,'connect')
 def _tune(dbapi_con,con_record):
  # Random index probes over a ~300MB db dominate every request; mmap and a
  # larger page cache turn 1s scans into ~0.2s without changing semantics.
  dbapi_con.execute('PRAGMA cache_size=-131072')
  dbapi_con.execute('PRAGMA mmap_size=536870912')
  dbapi_con.execute('PRAGMA temp_store=MEMORY')
 return e
real_engine=_sqlite_engine(DATA / 'learning.db')
test_engine=_sqlite_engine(DATA / 'testing.db')
testing=ContextVar('testing',default=False)
class EngineRouter:
    def __getattr__(self,name):return getattr(test_engine if testing.get() else real_engine,name)
engine=EngineRouter()
app = FastAPI(title='Personal English Learning System',docs_url=None if AUTH.enabled else '/docs',openapi_url=None if AUTH.enabled else '/openapi.json')
app.add_middleware(CORSMiddleware, allow_origins=[AUTH.origin] if AUTH.enabled else ['http://localhost:5173', 'http://127.0.0.1:5173'], allow_credentials=AUTH.enabled,allow_methods=['*'], allow_headers=['*'])

class _SwrScopeMiddleware:
    """Mark HTTP tasks so read routes may serve stale-while-revalidate entries.

    Runs inside database_mode, so testing mode is already routed here; test-mode
    requests skip SWR entirely because a background refresh thread would compute
    against the real database. Pure ASGI middleware keeps the contextvar visible
    to sync endpoints.
    """
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        _mark_foreground()
        if testing.get():return await self.app(scope,receive,send)
        token=response_cache.begin_http()
        try:await self.app(scope,receive,send)
        finally:
            response_cache.end_http(token)
            _mark_foreground()
app.add_middleware(_SwrScopeMiddleware)

_foreground_until=0.0
_foreground_lock=threading.Lock()

def _mark_foreground():
    """Reserve the moments around user-facing requests for the user."""
    global _foreground_until
    with _foreground_lock:_foreground_until=max(_foreground_until,time.monotonic()+0.3)

def _wait_foreground_gap():
    """Block until no user-facing request finished recently (rehearsals only)."""
    while True:
        with _foreground_lock:until=_foreground_until
        remaining=until-time.monotonic()
        if remaining<=0:return
        time.sleep(min(0.05,max(0.01,remaining)))

@app.get('/api/health')
def health():return dict(status='ok')

@app.get('/api/auth/status')
def auth_status(request:Request):return AUTH.status(request)

class LoginRequest(BaseModel):
    password:str=Field(min_length=1,max_length=1024)

@app.post('/api/auth/login')
def auth_login(body:LoginRequest,request:Request):return AUTH.login(request,body.password)

@app.post('/api/auth/logout')
def auth_logout(request:Request):return AUTH.logout(request)

@app.get('/api/pronunciation/oxford-us')
def oxford_pronunciation(word: str):
    try:path=oxford_audio.get_audio(word,DATA/'audio'/'oxford-us')
    except ValueError as e:raise HTTPException(503,str(e))
    return FileResponse(path,media_type='audio/mpeg',headers={'Cache-Control':'public,max-age=31536000'})

@app.get('/api/pronunciation/device-us')
def device_pronunciation(text_value: str):
    if not text_value.strip() or len(text_value)>300:raise HTTPException(400,'发音内容长度无效')
    # Do not expose an arbitrary public text-to-speech service.
    with engine.connect() as c:
        known=c.execute(text('SELECT 1 FROM knowledge WHERE answer=:value OR example=:value LIMIT 1'),dict(value=text_value)).first()
    if not known:raise HTTPException(400,'只能播放课程中已有的英文内容')
    try:path=device_audio.get_audio(text_value,DATA/'audio/device-us')
    except ValueError as e:raise HTTPException(503,str(e))
    return FileResponse(path,media_type='audio/wav',headers={'Cache-Control':'private,max-age=86400'})

SEEDS = [
 ('want-to', '想要做某事', 'want to', '后接动词原形', 'I want to drink water.'),
 ('enjoy-doing', '喜欢做某事（享受这个过程）', 'enjoy doing', 'enjoy 后接 doing', 'I enjoy reading.'),
 ('decide-to', '决定做某事', 'decide to', '后接动词原形', 'I decide to study.'),
 ('like-doing', '喜欢做某事（用 doing 形式）', 'like doing', 'like 也可以接 to do；这一题练习 doing', 'I like reading.'),
 ('listen-to', '听……', 'listen to', 'listen 后面接对象时使用 to', 'I listen to music.'),
 ('look-at', '看……', 'look at', '表示把目光转向某个对象', 'I look at the picture.'),
 ('wait-for', '等待……', 'wait for', '等待某人或某物时使用 for', 'I wait for the bus.'),
 ('talk-to', '与……交谈（使用 to）', 'talk to', '这一题练习 talk to；talk with 也可以表达交谈', 'I talk to my friend.'),
 ('ask-for', '请求得到……', 'ask for', '请求某物或帮助', 'I ask for help.'),
]

def now():
    stamp=datetime.now(timezone.utc)
    if testing.get():
        with test_engine.connect() as c:
            offset=c.execute(text('SELECT days FROM test_clock WHERE id=1')).scalar() or 0
        stamp+=timedelta(days=offset)
    return stamp

def initialize(target,with_bulk=False):
    if not getattr(target,'_pels_configured',False):
        def connection_options(dbapi,record):
            dbapi.execute('PRAGMA busy_timeout=5000')
            dbapi.execute('PRAGMA synchronous=NORMAL')
        event.listen(target,'connect',connection_options)
        target._pels_configured=True
    with target.connect() as setup:setup.exec_driver_sql('PRAGMA journal_mode=WAL')
    with target.begin() as c:
        c.execute(text('CREATE TABLE IF NOT EXISTS knowledge (id TEXT PRIMARY KEY, prompt TEXT, answer TEXT, explanation TEXT, example TEXT)'))
        c.execute(text('CREATE TABLE IF NOT EXISTS progress (knowledge_id TEXT PRIMARY KEY, introduced INTEGER DEFAULT 0, attempts INTEGER DEFAULT 0, correct INTEGER DEFAULT 0, streak INTEGER DEFAULT 0, level INTEGER DEFAULT 0, interval_days REAL DEFAULT 0, due_at TEXT, last_at TEXT)'))
        c.execute(text('CREATE TABLE IF NOT EXISTS questions (id TEXT PRIMARY KEY, knowledge_id TEXT, created_at TEXT, revealed INTEGER DEFAULT 0)'))
        c.execute(text('CREATE TABLE IF NOT EXISTS answers (id TEXT PRIMARY KEY, question_id TEXT UNIQUE, knowledge_id TEXT, raw_answer TEXT, correct INTEGER, revealed INTEGER, confidence TEXT, created_at TEXT, due_at TEXT, feedback TEXT)'))
        c.execute(text('CREATE TABLE IF NOT EXISTS spelling_checks (id TEXT PRIMARY KEY, question_id TEXT, raw_answer TEXT, correct INTEGER, created_at TEXT)'))
        c.execute(text('CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)'))
        courses_cleared = c.execute(text("SELECT value FROM app_settings WHERE key='courses-cleared-v1'")).scalar() == '1'
        c.execute(text('CREATE TABLE IF NOT EXISTS feedback_events (id TEXT PRIMARY KEY, question_id TEXT, confidence TEXT, created_at TEXT)'))
        c.execute(text('CREATE TABLE IF NOT EXISTS daily_coverage(day TEXT,knowledge_id TEXT,source_question_id TEXT,PRIMARY KEY(day,knowledge_id,source_question_id))'))
        c.execute(text('CREATE TABLE IF NOT EXISTS daily_tasks (day TEXT,knowledge_id TEXT,kind TEXT,PRIMARY KEY(day,knowledge_id))'))
        c.execute(text('CREATE TABLE IF NOT EXISTS review_queue (knowledge_id TEXT PRIMARY KEY, due_sequence INTEGER, due_at TEXT, gap INTEGER, version INTEGER)'))
        c.execute(text('CREATE INDEX IF NOT EXISTS progress_attempts ON progress(attempts)'))
        c.execute(text('CREATE INDEX IF NOT EXISTS progress_due ON progress(introduced,due_at)'))
        c.execute(text('CREATE INDEX IF NOT EXISTS queue_due ON review_queue(due_at,due_sequence)'))
        c.execute(text('CREATE INDEX IF NOT EXISTS answers_time ON answers(created_at)'))
        c.execute(text('CREATE INDEX IF NOT EXISTS answers_knowledge ON answers(knowledge_id)'))
        c.execute(text('CREATE INDEX IF NOT EXISTS checks_question ON spelling_checks(question_id)'))
        spelling_practice.install(c)
        import shared_examples
        shared_examples.install(c)
        c.execute(text('CREATE TABLE IF NOT EXISTS input_corrections(question_id TEXT PRIMARY KEY, correction_count INTEGER NOT NULL, last_at TEXT NOT NULL)'))
        c.execute(text('CREATE INDEX IF NOT EXISTS feedback_question ON feedback_events(question_id)'))
        if not courses_cleared:
            for kid, prompt, answer, explanation, example in SEEDS:
                c.execute(text('INSERT OR IGNORE INTO knowledge VALUES (:id,:p,:a,:e,:x)'), dict(id=kid,p=prompt,a=answer,e=explanation,x=example))
                c.execute(text('INSERT OR IGNORE INTO progress (knowledge_id) VALUES (:id)'),dict(id=kid))
            install(c,text)
        lesson.install(c,text)
        if not courses_cleared:
            transfer.install(c,text)
            combinations.install(c,text)
            context_engine.install(c,text)
        c.execute(text('CREATE TABLE IF NOT EXISTS rule_readings(rule_id TEXT PRIMARY KEY,read_at TEXT)'))
        c.execute(text('CREATE TABLE IF NOT EXISTS test_skips(question_id TEXT PRIMARY KEY,created_at TEXT)'))
        c.execute(text('CREATE TABLE IF NOT EXISTS daily_new_pacing(day TEXT PRIMARY KEY,last_sequence INTEGER NOT NULL)'))
        c.execute(text('CREATE TABLE IF NOT EXISTS daily_extensions(id TEXT PRIMARY KEY,day TEXT NOT NULL,requested_amount INTEGER NOT NULL,extra INTEGER NOT NULL,created_at TEXT NOT NULL)'))
        c.execute(text('CREATE INDEX IF NOT EXISTS extensions_day ON daily_extensions(day)'))
        install_memory(c)
        assessment.install(c)
        transfer_evidence.install(c)
        user_courses.install(c)
        for old in c.execute(text('SELECT DISTINCT a.knowledge_id FROM answers a LEFT JOIN review_queue r ON r.knowledge_id=a.knowledge_id WHERE r.version IS NULL OR r.version<5')).scalars().all():
            rebuild(c,old)
            if not assessment.get(c,old)['stable']:
                item=c.execute(text('SELECT interval_days,last_at FROM progress WHERE knowledge_id=:k'),dict(k=old)).mappings().one()
                if item['interval_days']>7:
                    due=(datetime.fromisoformat(item['last_at'])+timedelta(days=7)).isoformat()
                    c.execute(text('UPDATE progress SET interval_days=7,due_at=:d WHERE knowledge_id=:k'),dict(k=old,d=due))
                    c.execute(text('UPDATE review_queue SET due_at=:d WHERE knowledge_id=:k'),dict(k=old,d=due))
        if not courses_cleared:
            content.install(c)
            if with_bulk:bulk_courses.install(c)
            word_lookup.install(c)
            focus_training.install(c)
            group_learning.install(c)
            composition_engine.install(c)
            sourced_transfer.install(c)
            starter_course.restore(c)
            if os.environ.get('PELS_MAINLINE_ENABLED')=='1':
                mainline_runtime.install(c)
                if os.environ.get('PELS_COURSE_EXPANSION')=='1':
                    import course_expansion
                    course_expansion.install(c)
        # Only derived assessment caches are refreshed; raw answers and FSRS cards stay intact.
        for cached in c.execute(text('SELECT knowledge_id,payload FROM knowledge_assessments')).all():
            if json.loads(cached[1]).get('evidence_version')!=transfer_evidence.VERSION:
                payload=assessment.calculate(c,cached[0])
                c.execute(text('UPDATE knowledge_assessments SET payload=:p WHERE knowledge_id=:k'),dict(k=cached[0],p=json.dumps(payload,ensure_ascii=False)))

initialize(real_engine,with_bulk=os.environ.get('PELS_SKIP_BULK')!='1')
initialize(test_engine,with_bulk=not AUTH.enabled and os.environ.get('PELS_SKIP_BULK')!='1')
with test_engine.begin() as c:
    c.execute(text('CREATE TABLE IF NOT EXISTS test_clock(id INTEGER PRIMARY KEY,days INTEGER)'))
    if 'stage' not in [row[1] for row in c.execute(text('PRAGMA table_info(test_clock)'))]:
        c.execute(text('ALTER TABLE test_clock ADD COLUMN stage INTEGER DEFAULT 1'))
    c.execute(text('INSERT OR IGNORE INTO test_clock(id,days,stage) VALUES(1,0,1)'))
    c.execute(text('UPDATE progress SET level=0,introduced=0 WHERE attempts=0 AND level>=5 AND knowledge_id IN (SELECT material_id FROM transfer_materials)'))

@app.middleware('http')
async def database_mode(request,call_next):
    blocked=AUTH.guard(request)
    if blocked is not None:return blocked
    token=testing.set(request.headers.get('X-Learning-Test')=='1')
    try:
        response=await call_next(request)
        if AUTH.enabled:
            response.headers['Cache-Control']='private, max-age=86400' if request.url.path.startswith('/api/pronunciation/') else 'no-store'
        return response
    finally:testing.reset(token)

@app.get('/api/test/status')
def test_status():
    with engine.connect() as c:starter=starter_course.report(c) if testing.get() else None
    return dict(testing=testing.get(),time=now().isoformat(),starter_course=starter)

@app.post('/api/test/{action}')
def test_action(action: str, data: dict):
    if not testing.get():raise HTTPException(403,'仅允许在独立测试模式使用')
    response_cache.bump()
    if action in ('starter-course','mainline-course'):
        try:
            with test_engine.begin() as c:result=starter_course.activate(c,test_only=True,pack='mainline' if action=='mainline-course' else 'starter')
        except ValueError as error:raise HTTPException(409,str(error))
        return dict(enabled=True,starter_course=result)
    if action=='starter-exit':
        with test_engine.begin() as c:starter_course.exit_preview(c)
        return test_status()
    if action in ('transfer-pilot','unlock','prepare'):
        with test_engine.connect() as c:preview=starter_course.enabled(c)
        if preview:raise HTTPException(409,'请先退出起步试学，再使用其他测试预览')
    if action=='transfer-pilot':
        with test_engine.begin() as c:
            sourced_transfer.activate(c)
            c.execute(text('UPDATE test_clock SET stage=NULL WHERE id=1'))
        return dict(enabled=True,scope='want-to')
    if action=='advance':
        days=data.get('days')
        if type(days) is not int or days not in (1,3,7):raise HTTPException(422,'请选择1、3或7天')
        with test_engine.begin() as c:c.execute(text('UPDATE test_clock SET days=days+:d WHERE id=1'),dict(d=days))
    elif action=='unlock':
        with test_engine.begin() as c:
            current=c.execute(text('SELECT stage FROM test_clock WHERE id=1')).scalar() or 1
            target=data.get('stage',min(4,current+1))
            if type(target) is not int or target not in (1,2,3,4):
                raise HTTPException(422,'请选择搭配、短语、句子或中文情境阶段')
            c.execute(text('UPDATE test_clock SET stage=:s WHERE id=1'),dict(s=target))
            c.execute(text("UPDATE progress SET level=5 WHERE knowledge_id IN (SELECT p.knowledge_id FROM progress p LEFT JOIN course_links l ON l.knowledge_id=p.knowledge_id WHERE COALESCE(l.stage,1)<:s AND p.knowledge_id NOT IN (SELECT material_id FROM transfer_materials))"),dict(s=target))

            # Stage test needs its own fresh daily slots; learning records stay intact.
            c.execute(text('DELETE FROM daily_tasks'))
    elif action in ('reset','prepare'):
        with test_engine.begin() as c:
            for table in ('shared_example_links','word_check_requests','word_spelling_difficulties','input_corrections','answers','questions','spelling_checks','feedback_events','review_queue','memory_states','consolidation_slots','daily_new_pacing','daily_tasks','daily_coverage','lesson_attempts','context_round_items','context_rounds','composition_evidence','knowledge_assessments','test_skips','daily_extensions','teaching_exposures','question_trials','composition_items','composition_cursors','user_courses','user_course_groups','user_course_items','user_learning_state','user_learning_events','user_learning_meta'):
                c.execute(text('DELETE FROM '+table))
            c.execute(text("INSERT OR IGNORE INTO user_learning_meta VALUES('event_no',0)"))
            c.execute(text("DELETE FROM app_settings WHERE key='sourced-transfer-pilot'"))
            for table in ('focus_requests','group_questions','daily_group_tasks','group_progress','group_usage','group_active_slots'):c.execute(text('DELETE FROM '+table))
            c.execute(text('UPDATE test_clock SET days=0,stage=1 WHERE id=1'))
            c.execute(text('UPDATE progress SET introduced=0,attempts=0,correct=0,streak=0,level=0,interval_days=0,due_at=NULL,last_at=NULL'))
            if starter_course.enabled(c):
                c.execute(text('UPDATE test_clock SET stage=NULL WHERE id=1'))
                starter_course.restore(c)
        if action=='prepare':
            stamp=now()
            with test_engine.begin() as c:
                c.execute(text('UPDATE progress SET introduced=1,due_at=:d WHERE knowledge_id NOT IN (SELECT knowledge_id FROM course_links)'),dict(d=(stamp+timedelta(days=365)).isoformat()))
                for n in range(3):
                    qid=str(uuid.uuid4());at=(stamp-timedelta(seconds=120-n*30)).isoformat()
                    c.execute(text('INSERT INTO questions VALUES(:q,:k,:t,0)'),dict(q=qid,k='want-to',t=at))
                    c.execute(text("INSERT INTO answers VALUES(:id,:q,'want-to','want to',1,0,'clear',:t,NULL,'测试夹具：独立通过')"),dict(id=str(uuid.uuid4()),q=qid,t=at))
                rebuild(c,'want-to')
    else:raise HTTPException(404,'未知测试操作')
    return test_status()

def group_mode(c,qid):
    if not testing.get():return True
    if c.execute(text("SELECT 1 FROM group_questions WHERE question_id=:q AND group_id LIKE 'focus-%'"),dict(q=qid)).first():return True
    return bool(c.execute(text("SELECT 1 FROM sqlite_master WHERE name='test_clock'")).first() and c.execute(text('SELECT stage FROM test_clock WHERE id=1')).scalar() is None)


def answer_hint(c,item,local_checks=True):
    options=transfer.answer_options(item['id'],item['answer'],(content.details(c,item['id']) or {}).get('accepted_answers'))
    normalized=[transfer.normalize(a) for a in options]
    shapes=[list(map(len,a.split())) for a in normalized]
    result=dict(answer_length=len(normalize(item['answer'])),word_lengths=list(map(len,normalize(item['answer']).split())),answer_shapes=shapes)
    if local_checks and sum(map(len,normalized))<=600 and all(a.isascii() for a in normalized):
        salt='word-check-v1:'+item['id']+':'
        digest=lambda value:hashlib.sha256((salt+value).encode()).hexdigest()
        variants=[]
        for a in normalized:
            words=a.split()
            variants.append(dict(shape=list(map(len,words)),hashes=[digest(' '.join(words[:i+1])) for i in range(len(words))],pending=[[digest(' '.join(words[:i]+[word[:n]])) for n in range(1,len(word))] for i,word in enumerate(words)]))
        result['word_validation']=dict(salt=salt,variants=variants)
    return result


def normalize(value):
    return transfer.normalize(value)

@app.get('/api/rules/{rule_id}')
def rule_profile(rule_id: str):
    if rule_id not in RULES:raise HTTPException(404,'该规则尚未制作')
    with engine.connect() as c:
        reading=c.execute(text('SELECT read_at FROM rule_readings WHERE rule_id=:r'),dict(r=rule_id)).scalar()
        used=c.execute(text('''SELECT COUNT(*) FROM composition_evidence e JOIN answers a ON a.question_id=e.question_id WHERE e.structure_id=:r AND e.independent=1 AND EXISTS(SELECT 1 FROM question_trials t WHERE t.question_id=e.question_id AND t.mode IN ('transfer','transfer-review'))
          AND COALESCE((SELECT f.confidence FROM feedback_events f WHERE f.question_id=e.question_id ORDER BY f.rowid DESC LIMIT 1),a.confidence)='clear' '''),dict(r=rule_id)).scalar()
        level=c.execute(text('SELECT level FROM progress WHERE knowledge_id=:r'),dict(r=rule_id)).scalar() or 0
    return dict(id=rule_id,**RULES[rule_id],read_at=reading,independent_uses=used,state='已在组合题中独立使用' if used else '搭配回忆通过，待验证规则运用' if level>=3 else '已看讲解，待练习验证' if reading else '尚未学习')

@app.post('/api/rules/{rule_id}/read')
def read_rule(rule_id: str):
    if rule_id not in RULES:raise HTTPException(404,'规则不存在')
    with engine.begin() as c:c.execute(text('INSERT INTO rule_readings VALUES(:r,:t) ON CONFLICT(rule_id) DO UPDATE SET read_at=excluded.read_at'),dict(r=rule_id,t=now().isoformat()))
    return rule_profile(rule_id)

@app.get('/api/plan')
def learning_plan(compact: bool=False):
    # The report walks ~200 goals with prerequisite lookups; cache the serialized
    # body so plan pages render from cache between study writes.
    mode=(str(engine.url.database),compact,bool(testing.get()))
    def compute():return json.dumps(_learning_plan_payload(compact),ensure_ascii=False,separators=(',',':'))
    # swr: answer bumps serve the previous snapshot instantly while a background
    # thread recomputes; rare structural writes (settings, imports) hard-invalidate.
    return json.loads(response_cache.cached('plan',mode,120,compute,swr=True))

def _learning_plan_payload(compact: bool=False):
    if compact:
        s=study_settings()
        with engine.connect() as c,selection_cache.scope():
            route=curriculum_engine.report(c,s['active-course'])
            if os.environ.get('PELS_COURSE_EXPANSION')=='1':
                import course_expansion
                route['expansion']=course_expansion.summary()
        return dict(date=group_learning.day_of(now()),route=route,curriculum=[dict(id=s['active-course'],title='通用英语')],new_limit=s['daily-new-limit'],review_limit=s['daily-review-limit'])
    d=_dashboard_payload(summary_only=True);s=study_settings();zone=timezone(timedelta(hours=8));day=now().astimezone(zone).date().isoformat()
    with engine.connect() as c:
        admitted=group_learning.counts(c,now())
    with engine.connect() as c:curriculum=content.curriculum(c,include_items=False);packages=bulk_courses.summary(c)
    with engine.connect() as c,selection_cache.scope():
        route=curriculum_engine.report(c,s['active-course'])
        preparation=sourced_transfer.report(c,now(),s)
        if os.environ.get('PELS_COURSE_EXPANSION')=='1':
            import course_expansion
            route['expansion']=course_expansion.summary()
        starter=starter_course.report(c) if testing.get() else None
    return dict(date=day,route=route,starter_course=starter,transfer_preparation=preparation,curriculum=curriculum,packages=packages,new_limit=s['daily-new-limit'],review_limit=s['daily-review-limit'],new_admitted=admitted.get('new',0),review_admitted=admitted.get('review',0),new_breakdown=d.get('new_breakdown',{}),cross_day_due=d['cross_day_due'],same_day_practice=d['same_day_practice'],today_count=d['today_count'],rules=[],weak=[])

@app.get('/api/shared-examples/plan')
def shared_examples_plan():
    import shared_examples
    with engine.connect() as c,selection_cache.scope():return shared_examples.plan(c)

@app.get('/api/daily-activity')
def daily_activity_report(day: str | None=None,planning: bool=False,summary: bool=False):
    stamp=now();day=day or group_learning.day_of(stamp)
    try:
        parsed=datetime.strptime(day,'%Y-%m-%d').date()
        if parsed.isoformat()!=day:raise ValueError()
    except ValueError:raise HTTPException(400,'日期格式错误')
    if day>group_learning.day_of(stamp):raise HTTPException(400,'不能查询未来记录')
    settings=study_settings()
    # Planning previews recompute group scheduling; short TTL keeps plan pages instant.
    # summary=True serves the study-page quota badge without the planning block.
    effective_planning=planning and not summary
    def compute():
        with engine.connect() as c,selection_cache.scope():return daily_activity.build(c,stamp,day,settings['daily-new-limit'],settings['daily-review-limit'],settings['active-course'],effective_planning)
    return response_cache.cached('daily-activity',(str(engine.url.database),day,effective_planning,settings['daily-new-limit'],settings['daily-review-limit'],settings['active-course']),30,compute,swr=True)

@app.get('/api/profile')
def learning_profile_summary():
    # Stats tolerate ~1 minute of staleness; answers refresh via TTL, imports via bump.
    def compute():
        with engine.connect() as c:return learning_profile_stats.build(c,now())
    return response_cache.cached('profile',str(engine.url.database),60,compute,swr=True)

@app.get('/api/curriculum/units/{unit_id}')
def curriculum_unit(unit_id: str,page: int=1):
    page=max(1,page)
    with engine.connect() as c:
        if not c.execute(text('SELECT 1 FROM course_units WHERE id=:u'),dict(u=unit_id)).first():raise HTTPException(404,'单元不存在')
        total=c.execute(text('SELECT COUNT(*) FROM course_items WHERE unit_id=:u'),dict(u=unit_id)).scalar()
        items=[dict(r) for r in c.execute(text('SELECT k.id,k.answer,k.prompt,p.introduced,p.level,COALESCE(l.stage,1) AS stage FROM course_items ci JOIN knowledge k ON k.id=ci.knowledge_id JOIN progress p ON p.knowledge_id=k.id LEFT JOIN course_links l ON l.knowledge_id=k.id WHERE ci.unit_id=:u ORDER BY ci.position,k.id LIMIT 100 OFFSET :o'),dict(u=unit_id,o=(page-1)*100)).mappings()]
    return dict(items=items,total=total,page=page,page_size=100,total_pages=(total+99)//100)

@app.get('/api/knowledge/{kid}')
def knowledge_content(kid: str, visible: bool=False):
    with engine.begin() as c:
        row=c.execute(text('SELECT * FROM knowledge WHERE id=:k'),dict(k=kid)).mappings().first()
        if not row:raise HTTPException(404,'知识内容不存在')
        details=content.details(c,kid)
        if visible:transfer_evidence.expose(c,kid,now(),details,source='visible explanation')
        return dict(row,details=details)

@app.post('/api/challenge/{kid}')
def challenge(kid: str):
    with engine.begin() as c:
        item=c.execute(text('SELECT k.*,l.parent_id FROM knowledge k LEFT JOIN course_links l ON l.knowledge_id=k.id WHERE k.id=:k'),dict(k=kid)).mappings().first()
        if not item:raise HTTPException(404,'内容不存在')
        if testing.get() and not starter_course.can_challenge(c,kid,now()):
            raise HTTPException(409,'请先完成起步课程的必要材料和基础表达')
        source_goal=c.execute(text('SELECT goal_id FROM source_sentence_targets WHERE knowledge_id=:k'),dict(k=kid)).scalar()
        if source_goal and (not sourced_transfer.basics_ready(c,source_goal) or not sourced_transfer.allowed(c,kid,now())):raise HTTPException(409,'请先完成迁移材料准备与穿插练习')
        if item['parent_id'] and not testing.get():
            level=c.execute(text('SELECT level FROM progress WHERE knowledge_id=:k'),dict(k=item['parent_id'])).scalar() or 0
            if level<3:raise HTTPException(409,'请先验证前置内容')
        # Reuse an unanswered question so clicks do not create duplicate tasks.
        qid=c.execute(text('SELECT q.id FROM questions q LEFT JOIN answers a ON a.question_id=q.id WHERE q.knowledge_id=:k AND a.id IS NULL ORDER BY q.rowid DESC LIMIT 1'),dict(k=kid)).scalar()
        if not qid:
            qid=str(uuid.uuid4())
            c.execute(text('INSERT INTO questions VALUES(:q,:k,:t,0)'),dict(q=qid,k=kid,t=now().isoformat()))
        transfer_evidence.register(c,qid,kid)
        c.execute(text('UPDATE progress SET introduced=1 WHERE knowledge_id=:k'),dict(k=kid))
        response_cache.bump('dashboard','daily-activity','plan','progress')
        return dict(kind='recall',question_id=qid,id=kid,prompt=item['prompt'],**answer_hint(c,item),challenge=True)

class LookupQuery(BaseModel):
    word: str = Field(min_length=1,max_length=80)

class LookupImport(BaseModel):
    preview_id: str = Field(max_length=100)
    selected: list[str] = Field(min_length=1,max_length=20)
    train: bool = False

@app.post('/api/word-lookup')
def lookup_word(body: LookupQuery):
    try:word=word_lookup.clean_word(body.word)
    except ValueError as e:raise HTTPException(400,str(e))
    stamp=now()
    with engine.connect() as c:
        row=c.execute(text('SELECT payload,created_at FROM lookup_previews WHERE word=:w'),dict(w=word)).mappings().first()
        if row:
            cached=json.loads(row['payload']);ttl=timedelta(minutes=5) if cached.get('warnings') else timedelta(hours=24)
            if timedelta(0)<=stamp-datetime.fromisoformat(row['created_at'])<ttl:return dict(cached,cached=True)
    payload=word_lookup.search(DATA if not testing.get() else DATA/'lookup-test-cache',word)
    with engine.begin() as c:return word_lookup.save_preview(c,payload,stamp)

@app.post('/api/word-lookup/import')
def import_lookup(body: LookupImport):
    with engine.begin() as c:
        try:result=word_lookup.import_items(c,body.preview_id,body.selected,now())
        except ValueError as e:raise HTTPException(400,str(e))
        group_learning.install(c)
        composition_engine.install(c)
        sourced_transfer.install(c)
        # Only derived assessment caches are refreshed; raw answers and FSRS cards stay intact.
        for cached in c.execute(text('SELECT knowledge_id,payload FROM knowledge_assessments')).all():
            if json.loads(cached[1]).get('evidence_version')!=transfer_evidence.VERSION:
                payload=assessment.calculate(c,cached[0])
                c.execute(text('UPDATE knowledge_assessments SET payload=:p WHERE knowledge_id=:k'),dict(k=cached[0],p=json.dumps(payload,ensure_ascii=False)))
        if body.train:result['focus']=focus_training.add(c,result['id'],now(),member_ids=result['imported_ids'])
        result['items']=[dict(c.execute(text('SELECT k.*,p.*,COALESCE(l.stage,1) AS stage FROM knowledge k JOIN progress p ON p.knowledge_id=k.id LEFT JOIN course_links l ON l.knowledge_id=k.id WHERE k.id=:k'),dict(k=kid)).mappings().one()) for kid in result['imported_ids']]
    response_cache.bump('dictionary','dashboard','daily-activity','profile','plan','progress',hard=True)
    return dict(saved=True,**result)

@app.get('/api/focus/{kid}')
def focus_info(kid: str):
    with engine.connect() as c:
        try:info=focus_training.candidates(c,kid)
        except ValueError:raise HTTPException(404,'词条不存在')
        info['requests']=[r for r in focus_training.listing(c,group_learning.day_of(now())) if c.execute(text('SELECT knowledge_id FROM focus_requests WHERE id=:g'),dict(g=r['id'])).scalar()==kid]
        return info

@app.post('/api/focus/{kid}')
def add_focus(kid: str):
    with engine.begin() as c:
        try:result=focus_training.add(c,kid,now())
        except ValueError:raise HTTPException(404,'词条不存在')
    response_cache.bump('daily-activity','plan','progress',hard=True)
    return result

@app.post('/api/focus-cancel/{gid}')
def cancel_focus(gid: str):
    with engine.begin() as c:
        if not focus_training.cancel(c,gid):raise HTTPException(409,'任务已经结束或不存在')
    response_cache.bump('daily-activity','plan','progress',hard=True)
    return dict(saved=True)

@app.get('/api/dictionary')
def dictionary(q: str='',kind: str='all',status: str='all',page: int=1):
    page=max(1,page)
    # Content is fixed; only mastery metadata moves, so a short server cache is safe.
    def compute():
        with engine.connect() as c:
            return _dictionary_payload(c,q,kind,status,page)
    return response_cache.cached('dictionary',(str(engine.url.database),q[:100],kind,status,page),60,compute,swr=True)

def _dictionary_payload(c,q,kind,status,page):
        prefix="""WITH sources AS (
          SELECT knowledge_id AS target,knowledge_id AS source,last_at FROM progress WHERE introduced=1
          UNION ALL SELECT a.knowledge_id,p.knowledge_id,p.last_at FROM curriculum_aliases a JOIN progress p ON p.knowledge_id=a.alias_id WHERE p.introduced=1
        ), ranked AS (SELECT target,source,ROW_NUMBER() OVER(PARTITION BY target ORDER BY julianday(last_at) DESC,target=source DESC) AS rn FROM sources) """
        # Types are display metadata; mastery always comes from the shared progress row.
        base="""FROM knowledge k LEFT JOIN ranked er ON er.target=k.id AND er.rn=1 JOIN progress p ON p.knowledge_id=COALESCE(er.source,k.id) LEFT JOIN course_links l ON l.knowledge_id=k.id LEFT JOIN knowledge_details kd ON kd.knowledge_id=k.id
          WHERE 1=1 AND (k.answer LIKE :q OR k.prompt LIKE :q)
          AND (:kind='all' OR COALESCE(json_extract(kd.payload,'$.entry_type'),CASE WHEN COALESCE(l.stage,1)>=3 THEN 'sentence' WHEN k.id LIKE 'word-%' OR k.id='eat-a-meal' THEN 'word' WHEN l.stage=2 OR k.id IN (SELECT material_id FROM transfer_materials) THEN 'phrase' ELSE 'collocation' END)=:kind)
          AND (:status='all' OR (:status='learned' AND p.introduced=1) OR (:status='unseen' AND p.introduced=0) OR (:status='recall' AND p.level>=3) OR (:status='delayed' AND p.level>=5) OR (:status='transferable' AND EXISTS(SELECT 1 FROM knowledge_assessments ka WHERE ka.knowledge_id=p.knowledge_id AND json_extract(ka.payload,'$.transfer_contexts')>=2 AND json_extract(ka.payload,'$.last_transfer_ok')=1)))"""
        params=dict(q='%'+q[:100]+'%',kind=kind,status=status,offset=(page-1)*30)
        total=c.execute(text('SELECT COUNT(*) FROM knowledge')).scalar() if not q and kind=='all' and status=='all' else c.execute(text(prefix+'SELECT COUNT(*) '+base),params).scalar()
        type_counts=dict(c.execute(text("SELECT COALESCE(json_extract(payload,'$.entry_type'),'collocation'),COUNT(*) FROM knowledge_details GROUP BY 1")).all())
        type_counts['collocation']=type_counts.get('collocation',0)+total-sum(type_counts.values())
        total_all=c.execute(text('SELECT COUNT(*) FROM knowledge')).scalar()
        id_base="FROM knowledge k LEFT JOIN ranked er ON er.target=k.id AND er.rn=1 JOIN progress p ON p.knowledge_id=COALESCE(er.source,k.id)" if not q and kind=='all' and status=='all' else base
        if not q and kind=='all' and status=='all':
            ids=c.execute(text(prefix+'SELECT k.id FROM ranked er JOIN knowledge k ON k.id=er.target WHERE er.rn=1 ORDER BY k.rowid LIMIT 30 OFFSET :offset'),params).scalars().all()
            if len(ids)<30:
                learned=c.execute(text(prefix+'SELECT COUNT(*) FROM ranked er JOIN knowledge k ON k.id=er.target WHERE er.rn=1')).scalar()
                ids+=c.execute(text(prefix+"SELECT k.id FROM knowledge k JOIN progress p ON p.knowledge_id=k.id LEFT JOIN ranked er ON er.target=k.id AND er.rn=1 WHERE p.introduced=0 AND er.target IS NULL ORDER BY k.rowid LIMIT :remaining OFFSET :rest"),dict(remaining=30-len(ids),rest=max(0,params['offset']-learned))).scalars().all()
        else:ids=c.execute(text(prefix+'SELECT k.id '+id_base+' ORDER BY p.introduced DESC,k.rowid LIMIT 30 OFFSET :offset'),params).scalars().all()
        selected={f'pick{i}':kid for i,kid in enumerate(ids)}
        params.update(selected)
        page_base=base+' AND k.id IN ('+','.join(':'+key for key in selected)+')' if selected else base+' AND 0=1'
        rows=c.execute(text(prefix+"SELECT k.*,p.*,COALESCE(json_extract(kd.payload,'$.entry_type'),CASE WHEN COALESCE(l.stage,1)>=3 THEN 'sentence' WHEN k.id LIKE 'word-%' OR k.id='eat-a-meal' THEN 'word' WHEN l.stage=2 OR k.id IN (SELECT material_id FROM transfer_materials) THEN 'phrase' ELSE 'collocation' END) AS entry_type "+page_base+' ORDER BY p.introduced DESC,k.rowid'),params).mappings().all()
        items=[]
        for row in rows:
            item=dict(row);item['familiarity_level'],item['familiarity_label']=familiarity(item);item['assessment']=assessment.get(c,item['knowledge_id']);item['evidence_id']=item['knowledge_id'];items.append(item)
        return dict(items=items,total=total,total_all=total_all,type_counts=type_counts,page=page,page_size=30,total_pages=(total+29)//30)

@app.get('/api/lesson/want-01')
def lesson_state():
    with engine.connect() as c:return lesson.state(c,text)

class LessonAnswer(BaseModel):
    id: str
    step: int = Field(ge=0,lt=len(lesson.STEPS))
    answer: str = Field(max_length=500)
    hinted: bool = False

@app.post('/api/lesson/want-01/answer')
def lesson_answer(body: LessonAnswer):
    with engine.begin() as c:
        prior=c.execute(text('SELECT correct FROM lesson_attempts WHERE id=:id'),dict(id=body.id)).first()
        if prior:return dict(correct=bool(prior[0]),state=lesson.state(c,text))
        if lesson.state(c,text)['step']!=body.step:raise HTTPException(409,'课程已更新，请重新打开课程')
        question=lesson.STEPS[body.step]
        correct=lesson.normalize(body.answer) in [lesson.normalize(a) for a in question['answers']]
        c.execute(text("INSERT INTO lesson_attempts VALUES(:id,'want-01',:s,:a,:c,:h,:t)"),dict(id=body.id,s=body.step,a=body.answer,c=int(correct),h=int(body.hinted),t=now().isoformat()))
        return dict(correct=correct,explanation=question['explanation'],state=lesson.state(c,text))

@app.get('/api/settings')
def get_settings():
    import json
    values={'interface-theme':'system','speech-auto':True,'speech-rate':0.85,'speech-voice':'','speech-source':'oxford','daily-review-limit':30,'daily-new-limit':10,'active-course':'all'}
    values['keybindings']=dict(clear='1',hard='2',forgot='3',familiar='4',peek='Control',audio='Enter',submit='Enter',contextAudio='Alt+Enter')
    with engine.connect() as c:
        for key,value in c.execute(text('SELECT key,value FROM app_settings')):
            values[key]=json.loads(value)
    return values

def study_settings(connection=None):
    values=get_settings()
    day=now().astimezone(timezone(timedelta(hours=8))).date().isoformat()
    def bonus(c):return c.execute(text('SELECT COALESCE(SUM(extra),0) FROM daily_extensions WHERE day=:d'),dict(d=day)).scalar()
    if connection is not None:extra=bonus(connection)
    else:
        with engine.connect() as c:extra=bonus(c)
    values['daily-new-base']=values['daily-new-limit']
    values['daily-new-limit']+=extra
    return values

class ExtraLearning(BaseModel):
    id: str = Field(min_length=8,max_length=128)
    amount: int = Field(strict=True)

@app.post('/api/daily-extra')
def add_daily_learning(body: ExtraLearning):
    if body.amount not in (10,20,50):raise HTTPException(422,'请选择10、20或50组')
    stamp=now();day=stamp.astimezone(timezone(timedelta(hours=8))).date().isoformat()
    with engine.begin() as c:
        existing=c.execute(text('SELECT * FROM daily_extensions WHERE id=:i'),dict(i=body.id)).mappings().first()
        settings=study_settings(c)
        if existing:
            if existing['day']!=day or existing['requested_amount']!=body.amount:raise HTTPException(409,'加学请求已过期或参数不同，请重新选择')
        else:
            if group_learning.pool_count(c,stamp)>=CONSOLIDATION_LIMIT:raise HTTPException(409,'还有12组待巩固，请先完成巩固，再增加新内容')
            admitted=group_learning.counts(c,stamp).get('new',0)
            if admitted<settings['daily-new-limit']:raise HTTPException(409,'今日仍有新学额度，无需追加；请先检查课程前置条件')
            extra=body.amount+max(0,admitted-settings['daily-new-limit'])
            c.execute(text('INSERT OR IGNORE INTO daily_extensions VALUES(:i,:d,:a,:e,:t)'),dict(i=body.id,d=day,a=body.amount,e=extra,t=stamp.isoformat()))
        limit=study_settings(c)['daily-new-limit']
    response_cache.bump('dashboard','daily-activity','plan','progress',hard=True)
    return dict(amount=body.amount,date=day,new_limit=limit)

@app.post('/api/settings')
def save_settings(values: dict):
    import json
    for key,value in values.items():
        if key=='speech-source':
            if value not in ('oxford','windows'):raise HTTPException(422,'朗读音源无效')
            continue
        if key=='active-course':
            if not testing.get() and os.environ.get('PELS_MAINLINE_ENABLED')=='1' and value!='general-mainline':raise HTTPException(422,'正式学习仅使用通用英语主线')
            if not isinstance(value,str):raise HTTPException(422,'课程选择无效')
            with engine.connect() as c:valid=value=='all' or bool(c.execute(text('SELECT 1 FROM learning_courses WHERE id=:c'),dict(c=value)).first())
            if not valid:raise HTTPException(422,'课程不存在')
            continue
        if key=='keybindings':
            required={'clear','hard','forgot','familiar','peek','audio','submit','contextAudio'}
            allowed={'1','2','3','4','5','6','7','8','9','F2','F3','F4','F6','F7','F8','F9','Enter','Control','Alt+Enter'}
            if not isinstance(value,dict) or set(value)!=required or any(v not in allowed for v in value.values()):raise HTTPException(422,'快捷键配置无效')
            pairs=[(k,v) for k,v in value.items() if k not in ('submit','contextAudio')]
            for i,(a,v) in enumerate(pairs):
                for b,w in pairs[i+1:]:
                    if v==w and {a,b}!={'audio','submit'}:raise HTTPException(422,'快捷键重复')
            continue
        valid=(key in ('daily-review-limit','daily-new-limit') and type(value) is int and 0<=value<=300) or (key=='interface-theme' and value in ('system','light','dark')) or (key=='speech-auto' and isinstance(value,bool)) or (key=='speech-rate' and isinstance(value,(float,int)) and value in (0.7,0.85,1)) or (key=='speech-voice' and isinstance(value,str) and len(value)<500)
        if not valid: raise HTTPException(422,'设置值无效')
    with engine.begin() as c:
        for key,value in values.items():
            c.execute(text('INSERT INTO app_settings VALUES (:k,:v) ON CONFLICT(key) DO UPDATE SET value=excluded.value'),dict(k=key,v=json.dumps(value)))
    response_cache.bump()
    return get_settings()

def _dashboard_payload(summary_only: bool = False, lightweight: bool = False):
    with engine.connect() as c,selection_cache.scope():
        total_content=c.execute(text('SELECT COUNT(*) FROM knowledge')).scalar()
        introduced_content=c.execute(text('SELECT COUNT(*) FROM progress WHERE introduced=1')).scalar()
        if not summary_only:
            base='SELECT k.*,p.*,COALESCE(l.stage,1) AS stage,l.parent_id,CASE WHEN l.parent_id IS NULL OR pp.level>=3 THEN 1 ELSE 0 END AS unlocked FROM knowledge k JOIN progress p ON k.id=p.knowledge_id LEFT JOIN course_links l ON l.knowledge_id=k.id LEFT JOIN progress pp ON pp.knowledge_id=l.parent_id'
            if lightweight:
                # OR across 95k rows forces a full scan; UNION keeps both branches indexed.
                items = [dict(r) for r in c.execute(text(base+' WHERE p.introduced=1 UNION '+base+' WHERE k.id IN (SELECT knowledge_id FROM questions ORDER BY rowid DESC LIMIT 100)')).mappings()]
            else:
                items = [dict(r) for r in c.execute(text(base)).mappings()]
            answers = [dict(r) for r in c.execute(text('SELECT a.*,COALESCE((SELECT confidence FROM feedback_events f WHERE f.question_id=a.question_id ORDER BY f.rowid DESC LIMIT 1),a.confidence) AS effective_confidence,k.prompt,k.answer,gq.group_id,lg.title AS group_title FROM answers a JOIN knowledge k ON k.id=a.knowledge_id LEFT JOIN group_questions gq ON gq.question_id=a.question_id LEFT JOIN learning_groups lg ON lg.id=gq.group_id ORDER BY a.created_at DESC LIMIT 100')).mappings()]
            hints={}
            for answer in answers:
                answer['confidence']=answer.pop('effective_confidence')
                kid=answer['knowledge_id']
                if kid not in hints:hints[kid]=answer_hint(c,dict(id=kid,answer=answer['answer']),local_checks=False)
                answer.update(hints[kid])
        counts=group_learning.due_counts(c,now())
        day_start=now().astimezone(timezone(timedelta(hours=8))).replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc).isoformat()
        today_count=c.execute(text('SELECT COUNT(*) FROM answers WHERE julianday(created_at)>=julianday(:t)'),dict(t=day_start)).scalar()
        admitted=group_learning.counts(c,now())
        new_breakdown=group_learning.breakdown(c,now())
    today = now().date().isoformat()
    summary = dict(due=(counts['cross_day'] or 0)+(counts['practice'] or 0), cross_day_due=counts['cross_day'] or 0, same_day_practice=counts['practice'] or 0, today_count=today_count, today_new=admitted.get('new',0),today_review=admitted.get('review',0),total_content=total_content,introduced_content=introduced_content,scheduler_version=6 if os.environ.get('PELS_FSRS_TIME_QUEUE')=='1' else 5,new_breakdown=new_breakdown)
    return summary if summary_only else dict(items=items, history=answers, **summary)

def dashboard(summary_only: bool = False, lightweight: bool = False):
    return _dashboard_payload(summary_only,lightweight)

@app.get('/api/dashboard')
def dashboard_route(summary_only: bool = False, lightweight: bool = False):
    # Counts must track every answer, so writes bump this domain; the TTL only
    # absorbs repeated reads. The serialized body is cached to skip re-encoding.
    mode=str(engine.url.database)
    body=response_cache.cached('dashboard',(mode,summary_only,lightweight),10,
        lambda:json.dumps(_dashboard_payload(summary_only,lightweight),ensure_ascii=False,separators=(',',':')),swr=True)
    return Response(content=body,media_type='application/json')

def _knowledge_payload(c,item):
    # Inline /api/knowledge metadata so the study page needs no extra roundtrip.
    return dict(id=item['id'],answer=item.get('answer'),prompt=item.get('prompt'),explanation=item.get('explanation'),example=item.get('example'),details=content.details(c,item['id']))

def _select_next(c,allow_repeat=False):
        stage=c.execute(text('SELECT stage FROM test_clock WHERE id=1')).scalar() if testing.get() else None
        special=focus_training.select(c,now(),allow_repeat=allow_repeat)
        if not testing.get() or special or stage is None:
            if not starter_course.enabled(c):composition_engine.prepare(c,now())
            if not testing.get():
                import shared_examples
                shared_examples.prepare(c,now())
            settings=study_settings(c)
            kind,item=special if special else group_learning.select(c,now(),settings['daily-new-limit'],settings['daily-review-limit'],settings['active-course'],allow_repeat=allow_repeat)
            if kind=='timed-wait':return dict(kind='done',reason='fsrs-wait',message='当前内容尚未到FSRS复习时间；进度已保存，到期后继续。')
            if kind=='paused':return dict(kind='done',reason='interleaving-needed',message='模糊的内容已保留待练，暂时没有其他内容可穿插。可以休息一下，或主动再练这一项。')
            if kind=='done':
                plans=sourced_transfer.report(c,now(),settings)
                if any(p['state']=='等待穿插练习' for p in plans):return dict(kind='done',reason='transfer-spacing',message='迁移材料已备好，先穿插其他练习或隔天再验证。')
                if any(p['state']=='今日迁移练习已完成' for p in plans):return dict(kind='done',reason='transfer-daily-limit',message='本组今日迁移练习量已完成，其他候选已保留。')
                if any(p['waiting_reason'] for p in plans):return dict(kind='done',reason='transfer-preparation-budget',message=next(p['waiting_reason'] for p in plans if p['waiting_reason'])+'；迁移任务已保留。')
                if any(p['state']=='需要补充新例句' for p in plans):return dict(kind='done',reason='transfer-content-gap',message='当前缺少未展示过的新例句，已记录待补充。')
                route=curriculum_engine.report(c,settings['active-course'])
                if not route['ready_total']:return dict(kind='done',reason='uncompiled-course',message='本课程暂无已编排新课；可在学习计划选择课程，或在词典加入专项。')
                if not route['unintroduced']:return dict(kind='done',reason='no-more-new-goals',message='没有新的已编排学习组；未完成训练和到期复习仍会继续安排。')
                return dict(kind='done',message='今日可安排的学习组已完成或达到上限。')
            if kind=='learn':
                transfer_evidence.expose(c,item['id'],now(),content.details(c,item['id']))
                return dict(kind='learn',**item,knowledge=_knowledge_payload(c,item))
            qid=item.get('question_id') or str(uuid.uuid4())
            if not item.get('question_id'):
                c.execute(text('INSERT INTO questions(id,knowledge_id,created_at,revealed) VALUES(:q,:k,:t,0)'),dict(q=qid,k=item['id'],t=now().isoformat()))
                c.execute(text('INSERT INTO group_questions VALUES(:q,:g,:r)'),dict(q=qid,g=item['group_id'],r=item['role']))
                transfer_evidence.register(c,qid,item['id'],item['role'])
            mode=c.execute(text('SELECT mode FROM question_trials WHERE question_id=:q'),dict(q=qid)).scalar() or 'recall'
            if item['role']=='transfer':c.execute(text('UPDATE progress SET introduced=1 WHERE knowledge_id=:k'),dict(k=item['id']))
            return dict(kind='recall',question_id=qid,id=item['id'],prompt=item['prompt'],**answer_hint(c,item),group_id=item['group_id'],group_title=item.get('group_title',''),group_role=item['role'],exercise_mode=mode,knowledge=_knowledge_payload(c,item))

        stage_filter=(' AND COALESCE((SELECT stage FROM course_links l WHERE l.knowledge_id=k.id),1)=:stage' if stage else '')+" AND NOT EXISTS(SELECT 1 FROM daily_coverage cv WHERE cv.knowledge_id=k.id AND cv.day=:day)"
        pending=c.execute(text('SELECT q.id AS question_id,k.* FROM questions q JOIN knowledge k ON q.knowledge_id=k.id LEFT JOIN answers a ON a.question_id=q.id WHERE a.id IS NULL'+stage_filter+' ORDER BY q.created_at LIMIT 1'),dict(stage=stage,day=now().astimezone(timezone(timedelta(hours=8))).date().isoformat())).mappings().first()
        settings=study_settings(c)
        def admit_pending(kid,kind):
            day=now().astimezone(timezone(timedelta(hours=8))).date().isoformat()
            if c.execute(text('SELECT 1 FROM daily_tasks WHERE day=:d AND knowledge_id=:k'),dict(d=day,k=kid)).first():return True
            count=c.execute(text('SELECT COUNT(*) FROM daily_tasks WHERE day=:d AND kind=:v'),dict(d=day,v=kind)).scalar()
            if count>=settings['daily-new-limit' if kind=='new' else 'daily-review-limit']:return False
            c.execute(text('INSERT INTO daily_tasks VALUES(:d,:k,:v)'),dict(d=day,k=kid,v=kind))
            return True
        if pending and not testing.get():
            full=consolidation_count(c,now())>=CONSOLIDATION_LIMIT
            if full and not c.execute(text('SELECT 1 FROM consolidation_slots WHERE knowledge_id=:k'),dict(k=pending['id'])).first():pending=None
        def material_question(material):
            if not material['introduced']:
                if not testing.get() and consolidation_count(c,now())>=CONSOLIDATION_LIMIT:
                    return None
                if not testing.get() and not admit_pending(material['id'],'new'):return None
                return dict(kind='learn',**dict(material),supplement=True,knowledge=_knowledge_payload(c,material))
            if not testing.get() and not admit_pending(material['id'],'review'):return None
            existing=c.execute(text('SELECT q.id FROM questions q LEFT JOIN answers a ON a.question_id=q.id WHERE q.knowledge_id=:k AND a.id IS NULL LIMIT 1'),dict(k=material['id'])).scalar()
            qid=existing or str(uuid.uuid4())
            if not existing:c.execute(text('INSERT INTO questions(id,knowledge_id,created_at,revealed) VALUES(:q,:k,:t,0)'),dict(q=qid,k=material['id'],t=now().isoformat()))
            return dict(kind='recall',question_id=qid,id=material['id'],prompt=material['prompt'],**answer_hint(c,material),supplement=True,knowledge=_knowledge_payload(c,material))
        if pending:
            missing=None if testing.get() else transfer.missing_material(c,text,pending['id'])
            if missing:
                material=material_question(missing)
                if material:return material
            elif testing.get() or admit_pending(pending['id'],'review'):
                return dict(kind='recall',question_id=pending['question_id'],id=pending['id'],prompt=pending['prompt'],**answer_hint(c,pending),knowledge=_knowledge_payload(c,pending))
        if stage==4 and not bulk_courses.summary(c):
            item,message=context_engine.pick(c,now(),test=True)
            if item is None:return dict(kind='done',message=message,context_round_complete=True)
            kind='recall'
        else:
            kind,item=select_next(c,now(),settings['daily-review-limit'],settings['daily-new-limit'],test_stage=stage,active_course=settings['active-course'])
            if item and item['id'].startswith('compose-'):
                candidate,message=context_engine.pick(c,now(),new_limit=settings['daily-new-limit'],review_limit=settings['daily-review-limit'])
                if candidate:item=candidate;kind='recall'
                else:
                    # A context round ending must not hide the rest of today's work.
                    kind,item=select_next(c,now(),settings['daily-review-limit'],settings['daily-new-limit'],test_stage=stage,active_course=settings['active-course'],exclude_context=True)
        if item and item['id'].startswith('compose-'):c.execute(text('UPDATE progress SET introduced=1 WHERE knowledge_id=:k'),dict(k=item['id']))
        if kind=='learn':
            item_stage=c.execute(text('SELECT stage FROM course_links WHERE knowledge_id=:k'),dict(k=item['id'])).scalar()
            if item_stage!=4:
                transfer_evidence.expose(c,item['id'],now(),content.details(c,item['id']))
                return dict(kind=kind,**item,knowledge=_knowledge_payload(c,item))
            c.execute(text('UPDATE progress SET introduced=1 WHERE knowledge_id=:k'),dict(k=item['id']))
        if kind=='done':return dict(kind='done',message='今日安排已完成或已达每日组数上限，剩余任务会保留。')
        qid = str(uuid.uuid4())
        c.execute(text('INSERT INTO questions (id,knowledge_id,created_at) VALUES (:q,:k,:t)'),dict(q=qid,k=item['id'],t=now().isoformat()))
        transfer_evidence.register(c,qid,item['id'])
        return dict(kind='recall',question_id=qid,id=item['id'],prompt=item['prompt'],**answer_hint(c,item),knowledge=_knowledge_payload(c,item))

@app.post('/api/next')
def next_question(allow_repeat: bool=False):
    with engine.begin() as c,selection_cache.scope():
        result=_select_next(c,allow_repeat)
    response_cache.bump('dashboard','daily-activity','plan','progress')
    return result

class UserCourseImport(BaseModel):
    course: dict

@app.post('/api/user-courses/import')
def import_user_course(body: UserCourseImport):
    with engine.begin() as c:
        try: result=user_courses.import_course(c,body.course,now())
        except ValueError as e: raise HTTPException(422,str(e))
    response_cache.bump('dictionary','plan','dashboard',hard=True)
    return dict(saved=True,**result)

@app.get('/api/user-courses')
def list_user_courses():
    with engine.connect() as c:
        return [dict(r) for r in c.execute(text("SELECT c.id,c.title,c.created_at,COUNT(DISTINCT g.id) groups,COUNT(DISTINCT i.id) items FROM user_courses c LEFT JOIN user_course_groups g ON g.course_id=c.id LEFT JOIN user_course_items i ON i.course_id=c.id GROUP BY c.id ORDER BY c.created_at DESC")).mappings()]

@app.get('/api/user-courses/summary')
def user_course_summary():
    day=user_courses.local_day(now()).isoformat()
    with engine.connect() as c:
        states=c.execute(text('SELECT status,COUNT(*) n FROM user_learning_state GROUP BY status')).mappings().all()
        total=c.execute(text('SELECT COUNT(*) FROM user_course_items')).scalar() or 0
        due=c.execute(text('SELECT COUNT(*) FROM user_learning_state WHERE status!=\'done\' AND (due_day IS NULL OR due_day<=:d)'),dict(d=day)).scalar() or 0
        overdue=c.execute(text('SELECT COUNT(*) FROM user_learning_state WHERE due_day<:d'),dict(d=day)).scalar() or 0
        courses=c.execute(text('SELECT id,title,created_at FROM user_courses ORDER BY created_at')).mappings().all()
        today=c.execute(text('SELECT COUNT(*) FROM user_learning_events WHERE day=:d'),dict(d=day)).scalar() or 0
    return dict(day=day,total=total,due=due,overdue=overdue,today_done=today,courses=[dict(x) for x in courses],states={r['status']:r['n'] for r in states})

@app.get('/api/user-courses/next')
def user_course_next():
    with engine.connect() as c:
        row=user_courses.next_item(c,now())
        if not row:return dict(kind='done',message='今天的自定课程内容已完成；未完成项会继续保留。')
        return dict(kind=row['item_type'],item_id=row['id'],group=row['group_position']+1,position=row['item_position']+1,prompt=row['prompt'],status=row['status'])

@app.get('/api/user-courses/reveal/{item_id}')
def user_course_reveal(item_id:str):
    with engine.connect() as c:
        row=c.execute(text('SELECT answer,accepted_answers,payload FROM user_course_items WHERE id=:id'),dict(id=item_id)).mappings().first()
        if not row:raise HTTPException(404,'学习内容不存在')
        return dict(answer=row['answer'],accepted_answers=json.loads(row['accepted_answers']),details=json.loads(row['payload']))

class UserCourseAnswer(BaseModel):
    item_id:str
    answer:str
    confidence:str

@app.post('/api/user-courses/answer')
def user_course_answer(body: UserCourseAnswer):
    with engine.begin() as c:
        try:result=user_courses.submit(c,body.item_id,body.answer,body.confidence,now())
        except ValueError as e:raise HTTPException(400,str(e))
        nxt=user_courses.next_item(c,now())
    response_cache.bump('dictionary','plan','dashboard')
    return dict(saved=True,**result,next=(dict(kind=nxt['item_type'],item_id=nxt['id'],group=nxt['group_position']+1,prompt=nxt['prompt']) if nxt else None))

@app.get('/api/user-courses/{course_id}')
def get_user_course(course_id:str):
    with engine.connect() as c:
        row=c.execute(text('SELECT title,source_json FROM user_courses WHERE id=:id'),dict(id=course_id)).mappings().first()
        if not row:raise HTTPException(404,'课程不存在')
        return dict(title=row['title'],course=json.loads(row['source_json']))

# Pre-computed 认识 transitions: the client warms this while the learner reads
# the meaning card, so the real click only applies the deterministic write.
_prepared_introduce={}
_PREPARE_TTL=90

@app.post('/api/prepare-introduce/{kid}')
def prepare_introduce(kid: str):
    """Rehearse the introduce+scheduler flow in a rolled-back transaction.

    Applies the exact writes of /api/introduce plus _select_next, then rolls
    everything back; the question the learner would see after clicking 认识 is
    memoized for the real click. Reading time on the card absorbs the compute.
    """
    try:
        with engine.connect() as c:
            tx=c.begin()
            try:
                question=None
                with selection_cache.scope():
                    row=c.execute(text('SELECT 1 FROM progress WHERE knowledge_id=:k AND introduced=0'),dict(k=kid)).first()
                    if row:
                        transfer_evidence.expose(c,kid,now(),content.details(c,kid))
                        c.execute(text('UPDATE progress SET introduced=1,due_at=:t WHERE knowledge_id=:k AND introduced=0'),dict(k=kid,t=now().isoformat()))
                        question=_select_next(c)
            finally:
                tx.rollback()
        if question is not None:
            _prepared_introduce[(str(engine.url.database),kid)]=(time.monotonic(),question)
            return dict(prepared=True)
        return dict(prepared=False)
    except Exception:
        return dict(prepared=False)

@app.post('/api/introduce/{kid}')
def introduce(kid: str):
    with engine.begin() as c:
        transfer_evidence.expose(c,kid,now(),content.details(c,kid))
        result = c.execute(text('UPDATE progress SET introduced=1,due_at=:t WHERE knowledge_id=:k AND introduced=0'),dict(k=kid,t=now().isoformat()))
        if not result.rowcount:
            raise HTTPException(409,'内容不存在或已经学习')
    response_cache.bump('dashboard','daily-activity','plan','progress')
    # Inline the follow-up question so the client saves one serial round trip
    # on the meaning-screen "认识" transition; serve the rehearsal result when
    # it is fresh enough that the scheduler outcome cannot have drifted. The
    # question-exists guard keeps a rolled-back, freshly generated question id
    # from 404ing the next /api/check.
    key=(str(engine.url.database),kid)
    hit=_prepared_introduce.pop(key,None)
    if hit and time.monotonic()-hit[0]<=_PREPARE_TTL:
        nxt=hit[1]
        if nxt.get('kind')!='recall' or not nxt.get('question_id') or _question_exists(nxt['question_id']):
            return dict(saved=True,next=nxt)
    return dict(saved=True,next=next_question())

@app.post('/api/reveal/{qid}')
def reveal(qid: str):
    with engine.begin() as c:
        row=c.execute(text('SELECT k.answer,k.explanation FROM questions q JOIN knowledge k ON q.knowledge_id=k.id WHERE q.id=:q'),dict(q=qid)).mappings().first()
        if not row:
            raise HTTPException(404,'题目不存在')
        c.execute(text('UPDATE questions SET revealed=1 WHERE id=:q'),dict(q=qid))
        kid=c.execute(text('SELECT knowledge_id FROM questions WHERE id=:q'),dict(q=qid)).scalar()
        transfer_evidence.expose(c,kid,now(),source='hint')
        return dict(row)

class Submission(BaseModel):
    hint_used: bool = False
    question_id: str
    answer: str = Field(max_length=1000)
    confidence: str = Field(pattern='^(clear|hard|forgot)$')

@app.post('/api/test/skip-question/{qid}')
def skip_test_question(qid: str):
    if not testing.get():raise HTTPException(403,'仅测试模式允许跳过')
    with engine.connect() as c:
        row=c.execute(text('SELECT k.answer FROM questions q JOIN knowledge k ON k.id=q.knowledge_id WHERE q.id=:q'),dict(q=qid)).first()
    if not row:raise HTTPException(404,'题目不存在')
    result=submit(Submission(question_id=qid,answer=row[0],confidence='clear'))
    with test_engine.begin() as c:
        c.execute(text('CREATE TABLE IF NOT EXISTS test_skips(question_id TEXT PRIMARY KEY,created_at TEXT)'))
        c.execute(text('INSERT OR IGNORE INTO test_skips VALUES(:q,:t)'),dict(q=qid,t=now().isoformat()))
        c.execute(text('UPDATE composition_evidence SET independent=0 WHERE question_id=:q'),dict(q=qid))
        c.execute(text('UPDATE progress SET level=5 WHERE knowledge_id=(SELECT knowledge_id FROM questions WHERE id=:q)'),dict(q=qid))
        kid=c.execute(text('SELECT knowledge_id FROM questions WHERE id=:q'),dict(q=qid)).scalar()
        rebuild(c,kid)
        c.execute(text('UPDATE progress SET level=5 WHERE knowledge_id=:k'),dict(k=kid))
        update_coverage(c,kid,now())
        c.execute(text('DELETE FROM group_usage WHERE question_id=:q'),dict(q=qid))
        if group_mode(c,qid):group_learning.refresh(c,kid,now(),qid)
        assessment.refresh(c,kid)
    response_cache.bump('dashboard','daily-activity','plan','progress')
    return dict(saved=True,test_skip=True)

class SpellingCheck(BaseModel):
    id: str
    question_id: str
    answer: str = Field(max_length=1000)

class WordCheck(SpellingCheck):
    word_index: int = Field(ge=0,le=499)

@app.post('/api/check-word')
def check_word(body: WordCheck):
    with engine.begin() as c:
        row=c.execute(text('SELECT k.* FROM questions q JOIN knowledge k ON k.id=q.knowledge_id WHERE q.id=:q'),dict(q=body.question_id)).mappings().first()
        if not row:raise HTTPException(404,'题目不存在')
        given=transfer.normalize(body.answer).split()
        if len(given)!=body.word_index+1:raise HTTPException(422,'请按顺序填写单词')
        options=[transfer.normalize(a).split() for a in transfer.answer_options(row['id'],row['answer'],(content.details(c,row['id']) or {}).get('accepted_answers'))]
        matching=[words for words in options if len(words)>=len(given) and words[:len(given)]==given]
        pending=not matching and any(len(words)>=len(given) and words[:len(given)-1]==given[:-1] and words[len(given)-1].startswith(given[-1]) for words in options)
        # Partial word success is not a completed answer or a memory success.
        if not matching and not pending:
            spelling_practice.record(c,body,options,given,now())
            c.execute(text('INSERT INTO input_corrections VALUES(:q,1,:t) ON CONFLICT(question_id) DO UPDATE SET correction_count=correction_count+1,last_at=excluded.last_at'),dict(q=body.question_id,t=now().isoformat()))
        return dict(correct=bool(matching),pending=pending,complete=any(len(words)==len(given) for words in matching),answer_shapes=[list(map(len,words)) for words in matching] if matching else [])

class Feedback(BaseModel):
    question_id: str
    confidence: str = Field(pattern='^(clear|hard|forgot)$')

@app.post('/api/feedback')
def feedback(body: Feedback):
    with engine.begin() as c:
        if not c.execute(text('SELECT id FROM answers WHERE question_id=:q'),dict(q=body.question_id)).first():
            raise HTTPException(404,'没有可修改的已完成答题记录')
        c.execute(text('INSERT INTO feedback_events VALUES (:id,:q,:v,:t)'),dict(id=str(uuid.uuid4()),q=body.question_id,v=body.confidence,t=now().isoformat()))
        kid=c.execute(text('SELECT knowledge_id FROM questions WHERE id=:q'),dict(q=body.question_id)).scalar()
        rebuild(c,kid)
        update_coverage(c,kid,now())
        c.execute(text('''UPDATE composition_evidence SET independent=(SELECT CASE WHEN a.correct=1 AND a.revealed=0
          AND :confidence='clear' AND EXISTS(SELECT 1 FROM question_trials t WHERE t.question_id=a.question_id AND t.mode IN ('transfer','transfer-review')) AND NOT EXISTS(SELECT 1 FROM spelling_checks sc WHERE sc.question_id=a.question_id AND sc.correct=0 AND julianday(sc.created_at)<=julianday(a.created_at))
          AND NOT EXISTS(SELECT 1 FROM test_skips ts WHERE ts.question_id=a.question_id) THEN 1 ELSE 0 END
          FROM answers a WHERE a.question_id=:q) WHERE question_id=:q'''),dict(q=body.question_id,confidence=body.confidence))
        assessment.refresh(c,kid)
        apply_retention_limit(c,kid)
        if group_mode(c,body.question_id):group_learning.refresh(c,kid,now(),body.question_id)
    response_cache.bump('dashboard','daily-activity','plan','progress')
    return dict(saved=True)

@app.post('/api/check')
def check_spelling(body: SpellingCheck):
    with engine.begin() as c:
        row=c.execute(text('SELECT k.*,COALESCE(l.stage,1) AS stage FROM questions q JOIN knowledge k ON k.id=q.knowledge_id LEFT JOIN course_links l ON l.knowledge_id=k.id WHERE q.id=:q'),dict(q=body.question_id)).mappings().first()
        if not row:
            raise HTTPException(404,'题目不存在')
        assessment=transfer.grade(row['id'],body.answer,row['answer'],(content.details(c,row['id']) or {}).get('accepted_answers'))
        correct=assessment['correct']
        if correct:transfer_evidence.expose(c,row['id'],now(),content.details(c,row['id']),source='checked answer')
        if correct:
            c.execute(text('INSERT OR IGNORE INTO spelling_checks VALUES (:id,:q,:a,1,:t)'),dict(id=body.id,q=body.question_id,a=body.answer,t=now().isoformat()))
        else:
            c.execute(text('INSERT INTO input_corrections VALUES(:q,1,:t) ON CONFLICT(question_id) DO UPDATE SET correction_count=correction_count+1,last_at=excluded.last_at'),dict(q=body.question_id,t=now().isoformat()))
        response=dict(correct=correct,analysis=assessment['analysis'],notices=assessment['notices'],**(dict(answer=row['answer'],explanation=row['explanation'],example=row['example']) if correct else {}))
    # A correct check means the learner will submit a confidence next; rehearse
    # all three outcomes in the background so the real submit can inline the
    # follow-up question instead of re-running the scheduler on the hot path.
    if correct and not testing.get():
        _enqueue_submit_rehearsal(body.question_id,body.answer)
    return response

# Pre-computed submissions: /api/check warms every confidence outcome while the
# learner reads the feedback buttons, so the real /api/answers click only applies
# the deterministic write and serves the rehearsed next question.
_prepared_submit={}
_prepare_queue=queue.Queue()
_prepare_worker_started=False

def _submit_rehearsal_worker():
    while True:
        question_id,answer=_prepare_queue.get()
        try:_rehearse_submission(question_id,answer)
        except Exception:pass
        finally:_prepare_queue.task_done()

def _enqueue_submit_rehearsal(question_id,answer):
    global _prepare_worker_started
    if 'PYTEST_CURRENT_TEST' in os.environ:return
    if not _prepare_worker_started:
        _prepare_worker_started=True
        threading.Thread(target=_submit_rehearsal_worker,daemon=True,name='submit-rehearsal').start()
    _prepare_queue.put((question_id,answer))

def _question_exists(question_id):
    with engine.connect() as c:
        return bool(c.execute(text('SELECT 1 FROM questions WHERE id=:q'),dict(q=question_id)).first())

def _rehearsed_next(question_id,confidence):
    """Serve a rehearsed next question if fresh and anchored in the database.

    The rehearsal rolls back its transaction, so a freshly generated question
    row would not exist; serving its id would 404 the next /api/check. In that
    case (and after TTL) we fall back to a real scheduler run, which also
    re-applies the scheduler's admission writes.
    """
    key=(str(engine.url.database),question_id,confidence)
    hit=_prepared_submit.pop(key,None)
    if hit and time.monotonic()-hit[0]<=_PREPARE_TTL:
        nxt=hit[1]
        if nxt.get('kind')!='recall' or not nxt.get('question_id') or _question_exists(nxt['question_id']):
            return nxt
    return None

def _rehearse_submission(question_id,answer):
    """Replay submit+scheduler for each confidence in rolled-back transactions.

    hint_used mirrors the real client: assisted questions are exactly those the
    learner revealed, which is what questions.revealed stores.
    """
    db=str(engine.url.database)
    with engine.connect() as c:
        for confidence in ('clear','hard','forgot'):
            # Yield the SQLite writer lock to foreground learner requests.
            _wait_foreground_gap()
            tx=c.begin()
            try:
                with selection_cache.scope():
                    # Any earlier SELECT would autobegin and make begin() fail,
                    # so read the hint state inside the transaction.
                    revealed=c.execute(text('SELECT revealed FROM questions WHERE id=:q'),dict(q=question_id)).scalar()
                    if revealed is None:return
                    applied,result=_apply_submission(c,Submission(question_id=question_id,answer=answer,confidence=confidence,hint_used=bool(revealed)))
                    if applied:
                        _prepared_submit[(db,question_id,confidence)]=(time.monotonic(),_select_next(c))
            except Exception:
                pass
            finally:
                tx.rollback()

def _apply_submission(c,body):
    """Apply one /api/answers submission on connection c; returns (applied,result).

    Raises the same 404/422 as the route. applied=False means an answer row for
    this question already existed, so nothing was written.
    """
    existing=c.execute(text('SELECT * FROM answers WHERE question_id=:q'),dict(q=body.question_id)).mappings().first()
    if existing:
        return False,dict(existing)
    row=c.execute(text('SELECT q.*,k.answer,p.streak,p.interval_days,p.last_at,p.level FROM questions q JOIN knowledge k ON k.id=q.knowledge_id JOIN progress p ON p.knowledge_id=k.id WHERE q.id=:q'),dict(q=body.question_id)).mappings().first()
    if not row:
        raise HTTPException(404,'题目不存在')
    c.execute(text('''INSERT OR IGNORE INTO group_questions SELECT :q,p.group_id,m.role FROM group_primary p
      JOIN group_members m ON m.group_id=p.group_id AND m.knowledge_id=p.knowledge_id WHERE p.knowledge_id=:k'''),dict(q=body.question_id,k=row['knowledge_id']))
    if body.hint_used:
        c.execute(text('UPDATE questions SET revealed=1 WHERE id=:q'),dict(q=body.question_id))
        row=dict(row,revealed=1)
    correct=transfer.grade(row['knowledge_id'],body.answer,row['answer'],(content.details(c,row['knowledge_id']) or {}).get('accepted_answers'))['correct']
    if not correct:raise HTTPException(422,'请先完成正确拼写，再提交记忆反馈')
    due=now()
    feedback='拼写结果与记忆反馈已保存。'
    result=dict(id=str(uuid.uuid4()),question_id=body.question_id,knowledge_id=row['knowledge_id'],raw_answer=body.answer,correct=int(correct),revealed=row['revealed'],confidence=body.confidence,created_at=now().isoformat(),due_at=due.isoformat(),feedback=feedback)
    inserted=c.execute(text('INSERT OR IGNORE INTO answers VALUES (:id,:question_id,:knowledge_id,:raw_answer,:correct,:revealed,:confidence,:created_at,:due_at,:feedback)'),result)
    if not inserted.rowcount:
        return False,dict(c.execute(text('SELECT * FROM answers WHERE question_id=:q'),dict(q=body.question_id)).mappings().one())
    spelling_practice.enqueue(c,body.question_id,now())
    rebuild(c,row['knowledge_id'],incremental=True)
    combination=c.execute(text('SELECT structure_id,material_id FROM sentence_combinations WHERE knowledge_id=:k'),dict(k=row['knowledge_id'])).mappings().first()
    if combination:
        errors=c.execute(text('SELECT COUNT(*) FROM spelling_checks WHERE question_id=:q AND correct=0'),dict(q=body.question_id)).scalar()
        c.execute(text('INSERT OR IGNORE INTO composition_evidence VALUES(:q,:s,:m,:i,:t)'),dict(q=body.question_id,s=combination['structure_id'],m=combination['material_id'],i=int(correct and not row['revealed'] and not errors and body.confidence=='clear' and bool(c.execute(text("SELECT 1 FROM question_trials WHERE question_id=:q AND mode IN ('transfer','transfer-review')"),dict(q=body.question_id)).first())),t=now().isoformat()))
    update_coverage(c,row['knowledge_id'],now())
    assessment.refresh(c,row['knowledge_id'])
    apply_retention_limit(c,row['knowledge_id'])
    if group_mode(c,body.question_id):group_learning.refresh(c,row['knowledge_id'],now(),body.question_id)
    scheduled=c.execute(text('SELECT due_at,due_sequence,gap FROM review_queue WHERE knowledge_id=:k'),dict(k=row['knowledge_id'])).mappings().first()
    result['due_at']=scheduled['due_at']
    c.execute(text('UPDATE answers SET due_at=:d WHERE question_id=:q'),dict(d=scheduled['due_at'],q=body.question_id))
    return True,dict(**result,expected=row['answer'])

@app.post('/api/answers')
def submit(body: Submission):
    with engine.begin() as c:
        applied,result=_apply_submission(c,body)
    if not applied:
        return result
    response_cache.bump('dashboard','daily-activity','plan','progress')
    # Inline next only for real HTTP requests; direct function calls (tests,
    # skip_test_question) keep the exact pre-round-6 behavior.
    if not response_cache.http_active():
        return result
    # Inline the follow-up question so the client saves one serial round trip on
    # the confidence click; serve the rehearsal result when it is fresh enough
    # that the scheduler outcome cannot have drifted.
    rehearsed=_rehearsed_next(body.question_id,body.confidence)
    if rehearsed is not None:
        return dict(**result,next=rehearsed)
    return dict(**result,next=next_question())

@app.get('/api/export')
def export():
    tables=('knowledge','knowledge_details','learning_courses','course_units','course_items','progress','questions','answers','spelling_checks','feedback_events','review_queue','memory_states','consolidation_slots','daily_new_pacing','daily_tasks','daily_coverage','course_links','transfer_materials','sentence_combinations','composition_evidence','knowledge_assessments','rule_readings','lesson_attempts','context_rounds','context_round_items','app_settings','test_skips','daily_extensions')
    with engine.begin() as c:
        tables=tables+tuple(name for name in ('content_packages','package_members','knowledge_components') if c.execute(text("SELECT 1 FROM sqlite_master WHERE name=:n AND type='table'"),dict(n=name)).first())
        tables+=tuple(t for t in group_learning.TABLES+spelling_practice.TABLES if t not in tables)
        tables+=('shared_example_links','user_courses','user_course_groups','user_course_items','user_learning_state','user_learning_events','user_learning_meta')
        data={table:[dict(r) for r in c.execute(text('SELECT * FROM '+table)).mappings()] for table in tables}
    return dict(format_version=1,mode='test' if testing.get() else 'real',exported_at=now().isoformat(),tables=data)

def apply_retention_limit(c,kid):
    profile=assessment.get(c,kid)
    interval=c.execute(text('SELECT interval_days FROM progress WHERE knowledge_id=:k'),dict(k=kid)).scalar() or 0
    if interval>7 and not profile['stable']:
        last=c.execute(text('SELECT last_at FROM progress WHERE knowledge_id=:k'),dict(k=kid)).scalar()
        capped=(datetime.fromisoformat(last)+timedelta(days=7)).isoformat()
        c.execute(text('UPDATE progress SET interval_days=7,due_at=:t WHERE knowledge_id=:k'),dict(k=kid,t=capped))
        c.execute(text('UPDATE review_queue SET due_at=:t WHERE knowledge_id=:k'),dict(k=kid,t=capped))

@app.post('/api/context/new-round')
def new_context_round():
    with engine.begin() as c:
        pending=c.execute(text("SELECT 1 FROM questions q LEFT JOIN answers a ON a.question_id=q.id WHERE q.knowledge_id LIKE 'compose-%' AND a.id IS NULL LIMIT 1")).first()
        if pending:raise HTTPException(409,'请先完成当前情境题')
        c.execute(text('INSERT INTO context_rounds(created_at) VALUES(:t)'),dict(t=now().isoformat()))
    return dict(saved=True)

@app.get('/api/memory-history/{kid}')
def memory_history(kid: str, group_id: str | None = None):
    zone=timezone(timedelta(hours=8))
    with engine.connect() as c:
        summary=c.execute(text('SELECT MIN(created_at) AS first,MAX(created_at) AS last,COUNT(*) AS count FROM answers WHERE knowledge_id=:k'),dict(k=kid)).mappings().one()
        rows=c.execute(text("SELECT created_at,confidence FROM (SELECT a.created_at,COALESCE((SELECT confidence FROM feedback_events f WHERE f.question_id=a.question_id ORDER BY f.rowid DESC LIMIT 1),a.confidence) AS confidence, ROW_NUMBER() OVER(PARTITION BY date(a.created_at,'+8 hours') ORDER BY a.created_at DESC,a.rowid DESC) AS daily_rank FROM answers a WHERE a.knowledge_id=:k) WHERE daily_rank=1 ORDER BY created_at DESC LIMIT 3"),dict(k=kid)).mappings().all()
        queue=c.execute(text('SELECT due_at,due_sequence FROM review_queue WHERE knowledge_id=:k'),dict(k=kid)).mappings().first()
        progress=c.execute(text('SELECT due_at FROM progress WHERE knowledge_id=:k'),dict(k=kid)).mappings().first()
        seq=c.execute(text('SELECT COALESCE(MAX(rowid),0) FROM answers')).scalar()
        valid_group=group_id and c.execute(text('SELECT 1 FROM group_members WHERE group_id=:g AND knowledge_id=:k'),dict(g=group_id,k=kid)).first()
        gid=group_id if valid_group else group_learning.family(c,kid)
        group_schedule=c.execute(text('SELECT * FROM group_progress WHERE group_id=:g'),dict(g=gid)).mappings().first()
        group_plan=None
        if group_schedule:
            if group_schedule['due_at']:
                group_plan='本组下次复习：'+datetime.fromisoformat(group_schedule['due_at']).astimezone(zone).strftime('%Y-%m-%d %H:%M')
            else:group_plan='本组仍在当天巩固'
    first=datetime.fromisoformat(summary['first']).astimezone(zone).date() if summary['first'] else None
    tags=[dict(day=(datetime.fromisoformat(r['created_at']).astimezone(zone).date()-first).days+1,confidence=r['confidence'],time=r['created_at']) for r in reversed(rows)]
    due=queue['due_at'] if queue else progress['due_at'] if progress else None
    schedule_note='';remaining_questions=None
    if due:
        days=max(0,(datetime.fromisoformat(due).astimezone(zone).date()-now().astimezone(zone).date()).days)
        local_due=datetime.fromisoformat(due).astimezone(zone)
        plan=('已到期：' if datetime.fromisoformat(due)<=now() else '下次复习：')+local_due.strftime('%Y-%m-%d %H:%M')
    elif queue:
        remaining_questions=max(0,queue['due_sequence']-seq-1)
        plan=f'当天巩固：再隔 {remaining_questions} 题' if remaining_questions else '当天巩固：已可再次出题'
        schedule_note='这一轮按题数安排，没有固定时刻；完成当天巩固后，再确定跨天复习日期。'
    else:plan='尚未形成复习计划'
    return dict(first=summary['first'],last=summary['last'],count=summary['count'],tags=tags,plan=plan,due_at=due,schedule_note=schedule_note,remaining_questions=remaining_questions,group_plan=group_plan,group_due_at=group_schedule['due_at'] if group_schedule else None,transfer_pending=bool(group_schedule and group_schedule['transfer_pending']))

@app.get('/api/history/{kid}')
def recent_history(kid: str):
    with engine.connect() as c:
        rows=c.execute(text('''SELECT a.question_id,a.created_at,a.correct,a.revealed,
          COALESCE((SELECT f.confidence FROM feedback_events f WHERE f.question_id=a.question_id ORDER BY f.rowid DESC LIMIT 1),a.confidence) AS confidence,
          (SELECT COUNT(*) FROM spelling_checks s WHERE s.question_id=a.question_id AND s.correct=0 AND julianday(s.created_at)<=julianday(a.created_at)) AS errors
          FROM answers a WHERE a.knowledge_id=:k ORDER BY a.rowid DESC LIMIT 3'''),dict(k=kid)).mappings().all()
    return [dict(row) for row in rows]

@app.post('/api/backup')
def backup():
    import sqlite3
    target=DATA / ('backup-'+now().strftime('%Y%m%d-%H%M%S-%f')+'.db')
    with sqlite3.connect(DATA/('testing.db' if testing.get() else 'learning.db')) as source, sqlite3.connect(target) as dest:
        source.backup(dest)
    return dict(filename=target.name)
