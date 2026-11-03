"""Long, seeded sourced-transfer regression. Only writes to a fresh --output directory."""
import argparse,os,sys,json,random,time
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from collections import Counter
from sqlalchemy import create_engine,text
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--days',type=int,default=120);p.add_argument('--turns',type=int,default=100);p.add_argument('--focused',action='store_true');a=p.parse_args()
ROOT=Path(__file__).resolve().parents[1];out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
os.environ['PELS_DATA_DIR']=str(out/'bootstrap');os.environ['PELS_SKIP_BULK']='1';sys.path.insert(0,str(ROOT/'backend'))
import app,sourced_transfer as st,group_learning as gl,curriculum_engine as ce,assessment
BASE=datetime(2026,1,1,8,tzinfo=timezone.utc)
for profile,seed in [('fresh_stubborn_word',82711),('prepared_stubborn_material',82712)]:
 rng=random.Random(seed);folder=out/profile;folder.mkdir();db=create_engine('sqlite:///'+str(folder/'simulation.db'));app.initialize(db,with_bulk=False)
 with db.begin() as c:
  st.activate(c)
  if a.focused:c.execute(text("UPDATE curriculum_goals SET status='draft' WHERE id NOT IN ('drink-water','want-to','read-books','learn-english','eat-a-meal')"))
  if profile.startswith('prepared'):
   scope="knowledge_id IN (SELECT knowledge_id FROM curriculum_lessons WHERE goal_id IN ('drink-water','want-to','read-books','learn-english','eat-a-meal') AND role!='transfer')" if a.focused else "knowledge_id NOT IN (SELECT knowledge_id FROM course_links WHERE stage=4) AND knowledge_id NOT IN (SELECT knowledge_id FROM source_preparation_items)"
   c.execute(text('UPDATE progress SET introduced=1,level=3,last_at=:t,due_at=:d WHERE '+scope),dict(t=(BASE-timedelta(days=2)).isoformat(),d=(BASE+timedelta(days=10)).isoformat()))
  stubborn='word-water' if profile.startswith('fresh') else c.execute(text('SELECT knowledge_id FROM source_preparation_items ORDER BY rowid LIMIT 1')).scalar()
  c.execute(text('UPDATE progress SET introduced=0,level=0,last_at=NULL,due_at=NULL WHERE knowledge_id=:k'),dict(k=stubborn))
 clock=[BASE];daily=[];totals=Counter();seq=[];repeat=0;max_repeat=0;stubborn_days=[]
 with patch.object(app,'real_engine',db),patch('app.now',side_effect=lambda:clock[0]),(folder/'events.jsonl').open('w',encoding='utf-8') as f:
  app.save_settings({'daily-new-limit':50,'daily-review-limit':50})
  for day in range(a.days):
   clock[0]=BASE+timedelta(days=day);today=Counter();stop=None
   skipped=day in (5,6,23,24,25) or rng.random()<.17
   if not skipped:
    for turn in range(a.turns):
     clock[0]+=timedelta(seconds=rng.randint(20,85));t0=time.perf_counter();q=app.next_question();latency=time.perf_counter()-t0
     if q['kind']=='done':stop=q.get('reason','done');f.write(json.dumps(dict(day=day+1,event='done',response=q,seconds=round(latency,4)),ensure_ascii=False)+'\n');break
     if q['kind']=='learn':app.introduce(q['id']);today['lessons']+=1;continue
     with db.connect() as c:
      expected=c.execute(text('SELECT answer FROM knowledge WHERE id=:k'),dict(k=q['id'])).scalar()
      if q.get('group_role')=='transfer':assert gl.requirements_met(c,q['id'],stamp=clock[0]),q
      if q.get('exercise_mode')=='transfer':assert 'answer' not in q and 'explanation' not in q,q
     rating='forgot' if q['id']==stubborn else rng.choices(['clear','hard','forgot'],[.72,.18,.10])[0]
     wrong=rng.random()<.12;hint=rng.random()<.07
     if wrong:app.check_spelling(app.SpellingCheck(id=f'{profile}-{day}-{turn}',question_id=q['question_id'],answer='__wrong__'));today['spelling_errors']+=1
     if hint:app.reveal(q['question_id']);today['hints']+=1
     saved=app.submit(app.Submission(question_id=q['question_id'],answer=expected,confidence=rating));today['answers']+=1;today[rating]+=1
     if q.get('exercise_mode')=='transfer':today['new_transfer_attempts']+=1
     if q['id']==stubborn:today['stubborn_attempts']+=1
     repeat=repeat+1 if seq and seq[-1]==q['id'] else 1;seq.append(q['id']);max_repeat=max(max_repeat,repeat)
     with db.connect() as c:
      counts=gl.counts(c,clock[0]);pool=c.execute(text('SELECT count(*) FROM group_active_slots')).scalar()
      assert counts.get('new',0)<=50 and counts.get('review',0)<=50 and pool<=12,(profile,day,counts,pool)
      prog=dict(c.execute(text('SELECT * FROM progress WHERE knowledge_id=:k'),dict(k=q['id'])).mappings().one())
      if q['id']==stubborn:assert not ce.known(c,stubborn),(day,prog)
      memory=c.execute(text('SELECT * FROM memory_states WHERE knowledge_id=:k'),dict(k=q['id'])).mappings().first()
     f.write(json.dumps(dict(day=day+1,event='answer',id=q['id'],group=q.get('group_id'),mode=q.get('exercise_mode'),rating=rating,wrong=wrong,hint=hint,counts=counts,pool=pool,progress=prog,memory=dict(memory) if memory else None,seconds=round(latency,4)),ensure_ascii=False,default=str)+'\n')
   with db.connect() as c:
    plan=st.report(c,clock[0],app.study_settings())[0];counts=gl.counts(c,clock[0]);pool=c.execute(text('SELECT count(*) FROM group_active_slots')).scalar()
    stubborn_state=dict(c.execute(text('SELECT * FROM progress WHERE knowledge_id=:k'),dict(k=stubborn)).mappings().one());known=ce.known(c,stubborn)
    assert not known,(profile,day,stubborn_state)
    learned=c.execute(text('SELECT count(*) FROM progress WHERE introduced=1')).scalar()
    n_answers=c.execute(text('SELECT count(*) FROM answers')).scalar()
    if skipped:assert today['answers']==0
   record=dict(day=day+1,skipped=skipped,activity=dict(today),stop=stop,counts=counts,pool=pool,plan=plan,stubborn=stubborn_state,introduced=learned,total_answers=n_answers)
   daily.append(record);totals.update(today);f.flush();(folder/'days.json').write_text(json.dumps(daily,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
   if (day+1)%20==0:
    with db.connect() as c:before={t:set(c.execute(text('SELECT * FROM '+t))) for t in ('answers','feedback_events','progress','memory_states')}
    app.initialize(db,with_bulk=False)
    with db.connect() as c:
     for t,rows in before.items():assert rows<=set(c.execute(text('SELECT * FROM '+t))),(day,t)
    print(profile,'day',day+1,'answers',n_answers,'state',plan['state'],flush=True)
 summary=dict(profile=profile,seed=seed,days=a.days,skipped=sum(r['skipped'] for r in daily),totals=dict(totals),max_consecutive_answers_same_item=max_repeat,final_plan=daily[-1]['plan'],final_stubborn=daily[-1]['stubborn'],limits=[50,50],focused=a.focused,verified_ever=any(r['plan']['state'].startswith('本轮迁移已验证') for r in daily),integrity=None)
 with db.connect() as c:summary['integrity']=c.execute(text('PRAGMA integrity_check')).scalar();assert summary['integrity']=='ok'
 (folder/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str),encoding='utf-8');db.dispose();print(json.dumps(summary,ensure_ascii=False,default=str),flush=True)
