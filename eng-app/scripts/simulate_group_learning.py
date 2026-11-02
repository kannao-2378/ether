"""Seeded 60-day grouped-learning runtime audit; isolated data only."""
import os,sys,json,random,tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from sqlalchemy import create_engine,text
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
os.environ['PELS_SKIP_BULK']='1';os.environ['PELS_DATA_DIR']=str(ROOT/'.tools/group-simulation-import')
import app,group_learning as groups
rng=random.Random(611012);output=ROOT/'.tools/group-simulation-final';output.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
 db=create_engine('sqlite://');app.initialize(db,with_bulk=True)
 old=app.real_engine;app.real_engine=db;clock=[datetime(2026,11,1,8,tzinfo=timezone.utc)]
 report=[]
 try:
  with patch('app.now',side_effect=lambda:clock[0]):
   app.save_settings({'daily-new-limit':50,'daily-review-limit':50})
   for day in range(60):
    clock[0]=datetime(2026,11,1,8,tzinfo=timezone.utc)+timedelta(days=day)
    if rng.random()<.17:
     report.append(dict(day=day+1,skipped=True));continue
    answers=0;bad=0;transfers=0;learned=0
    for turn in range(rng.randint(80,140)):
     clock[0]+=timedelta(seconds=rng.randint(15,75))
     q=app.next_question()
     if q['kind']=='done':break
     if q['kind']=='learn':app.introduce(q['id']);learned+=1;continue
     with db.connect() as c:
      expected=c.execute(text('SELECT answer FROM knowledge WHERE id=:k'),dict(k=q['id'])).scalar()
      if q.get('group_role')=='transfer':
       assert groups.requirements_met(c,q['id'],stamp=clock[0]),(day,q);transfers+=1
     rating=rng.choices(['clear','hard','forgot'],[.70,.18,.12])[0]
     if rng.random()<.12:
      app.check_spelling(app.SpellingCheck(id=f'{day}-{turn}',question_id=q['question_id'],answer='__wrong__'));bad+=1
     if rng.random()<.08:app.reveal(q['question_id'])
     body=app.Submission(question_id=q['question_id'],answer=expected,confidence=rating)
     saved=app.submit(body);answers+=1
     if turn%17==0:assert app.submit(body)['id']==saved['id']
     if turn%23==0:app.feedback(app.Feedback(question_id=q['question_id'],confidence=rng.choice(['clear','hard','forgot'])))
     with db.begin() as c:
      counts=groups.counts(c,clock[0]);pool=groups.pool_count(c,clock[0])
      assert counts.get('new',0)<=50 and counts.get('review',0)<=50 and pool<=12,(day,counts,pool)
    with db.begin() as c:
     counts=groups.counts(c,clock[0]);pool=groups.pool_count(c,clock[0]);rows=c.execute(text('SELECT COUNT(*) FROM answers')).scalar()
     assert rows>=answers
    report.append(dict(day=day+1,answers=answers,lessons=learned,spelling_failures=bad,transfers=transfers,groups=counts,active=pool,total_answers=rows))
    if day%10==9:app.initialize(db,with_bulk=True)
    (output/'days.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if day%10==9:print('simulated day',day+1,flush=True)
 finally:app.real_engine=old;db.dispose()
summary=dict(days=len(report),skipped=sum(bool(r.get('skipped')) for r in report),answers=sum(r.get('answers',0) for r in report),transfers=sum(r.get('transfers',0) for r in report),seed=611012,limits=[50,50],pool_limit=12)
(output/'summary.json').write_text(json.dumps(summary,indent=2));print(summary)
