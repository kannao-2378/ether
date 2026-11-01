"""Reproducible real-service simulation; only writes under --output, never real data."""
import argparse, csv, json, math, os, random, sqlite3, sys, time
from collections import Counter
from datetime import datetime,timedelta,timezone
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--output',required=True)
parser.add_argument('--seeds',default='117,409,20261101')
parser.add_argument('--days',type=int,default=60)
parser.add_argument('--max-answers',type=int,default=240)
args=parser.parse_args()
OUT=Path(args.output).resolve();OUT.mkdir(parents=True,exist_ok=True)
ROOT=Path(__file__).resolve().parents[1]
os.environ['PELS_DATA_DIR']=str(OUT/'bootstrap');Path(os.environ['PELS_DATA_DIR']).mkdir(exist_ok=True)
os.environ['PELS_SKIP_BULK']='1'
sys.path.insert(0,str(ROOT/'backend'))
import app, bulk_courses, assessment, memory_curve
from sqlalchemy import create_engine,text,event
from scheduler import consolidation_count,consolidation_pending,FSRS,rebuild
from fsrs import Card,Rating

ZONE=timezone(timedelta(hours=8))
BASE=datetime(2026,1,1,9,tzinfo=ZONE)

def emit(file,value):
    file.write(json.dumps(value,ensure_ascii=False,default=str)+'\n');file.flush()

def state(c,kid):
    r=c.execute(text('SELECT p.*,r.due_sequence,r.gap FROM progress p LEFT JOIN review_queue r ON r.knowledge_id=p.knowledge_id WHERE p.knowledge_id=:k'),dict(k=kid)).mappings().one()
    return dict(r)

def run(seed,template):
    rng=random.Random(seed);folder=OUT/str(seed);folder.mkdir(exist_ok=True)
    path=folder/'simulation.db'
    if path.exists() or (folder/'events.jsonl').exists():raise RuntimeError('Output exists; choose a fresh directory: '+str(path))
    src=sqlite3.connect(template);dst=sqlite3.connect(path);src.backup(dst);src.close();dst.close()
    db=create_engine('sqlite:///'+str(path))
    # Isolated accelerated simulation only; power-loss durability/performance is NOT under test.
    @event.listens_for(db,'connect')
    def configure(connection,record):
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA synchronous=NORMAL')
    app.real_engine=db;app.testing.set(False)
    clock=[BASE];app.now=lambda:clock[0]
    app.save_settings({'daily-new-limit':50,'daily-review-limit':50,'active-course':'all'})
    events=(folder/'events.jsonl').open('w',encoding='utf-8');days=(folder/'days.jsonl').open('w',encoding='utf-8')
    faults=[];stats=Counter();daily=[];skill={};last_seq={};last_at={};cards={};last_questions=[]
    def check(ok,code,**context):
        stats['assertions']+=1
        if not ok:
            fault=dict(code=code,time=clock[0].isoformat(),**context);faults.append(fault);emit(events,dict(event='FAIL',**fault))
    # Deterministic random absences include multi-day breaks, without learning on those days.
    missed=set(rng.sample(range(2,args.days),min(max(0,args.days-2),max(3,args.days//7))))
    if args.days>=30:missed.update([17,18,19,42,43])
    recent_feedback=[]
    for day in range(args.days):
        clock[0]=BASE+timedelta(days=day,hours=rng.choice([0,3,10]))
        began=time.perf_counter();date=clock[0].date().isoformat();daystats=Counter();stages=Counter();latencies=[]
        if day in missed:
            with db.connect() as c:before=c.execute(text('SELECT COUNT(*) FROM answers')).scalar()
            # Reopen only; never execute an answer or advance any review state.
            db.dispose()
            with db.connect() as c:after=c.execute(text('SELECT COUNT(*) FROM answers')).scalar()
            check(before==after,'absence_changed_history')
            record=dict(day=day+1,date=date,absent=True,answers=0,elapsed_seconds=time.perf_counter()-began)
            emit(days,record);daily.append(record);stats['missed_days']+=1
            continue
        fatigue=rng.uniform(.05,.25);budget=rng.randint(args.max_answers//2,args.max_answers)
        # Every tenth active-day candidate allows enough time to exhaust a daily plan.
        if day%10==0:budget=args.max_answers*2
        with db.connect() as c:daystats['backlog_start']=c.execute(text('SELECT COUNT(*) FROM review_queue WHERE due_at IS NOT NULL AND julianday(due_at)<=julianday(:t)'),dict(t=clock[0].isoformat())).scalar()
        for step in range(budget*2+80):
            if daystats['answers']>=budget:daystats['stopped_for_time']=1;break
            next_time=clock[0]+timedelta(seconds=rng.randint(12,65))
            if next_time.date().isoformat()!=date:daystats['stopped_at_midnight']=1;break
            clock[0]=next_time
            with db.connect() as c:pool_before=consolidation_count(c,clock[0]);sequence=c.execute(text('SELECT COALESCE(MAX(rowid),0) FROM answers')).scalar()
            started=time.perf_counter();q=app.next_question();latencies.append((time.perf_counter()-started)*1000)
            if q['kind']=='done':
                daystats['done']=1;emit(events,dict(event='done',day=day+1,question=q,pool=pool_before));break
            kid=q['id']
            if q['kind']=='learn':
                check(pool_before<12,'new_admitted_with_full_pool',id=kid,pool=pool_before)
                app.introduce(kid);daystats['introduced']+=1;stats['introductions']+=1
                with db.connect() as c:pool_after=consolidation_count(c,clock[0])
                check(pool_after<=12,'new_introduction_exceeds_pool',id=kid,pool=pool_after)
                emit(events,dict(event='introduce',day=day+1,id=kid,answer=q['answer'],pool_before=pool_before,pool_after=pool_after))
                continue
            with db.connect() as c:
                k=dict(c.execute(text('SELECT k.*,COALESCE(l.stage,1) AS stage FROM knowledge k LEFT JOIN course_links l ON l.knowledge_id=k.id WHERE k.id=:k'),dict(k=kid)).mappings().one())
                before=state(c,kid)
                stored=c.execute(text('SELECT card_json FROM memory_states WHERE knowledge_id=:k'),dict(k=kid)).scalar()
            stages[str(k['stage'])]+=1
            gap=sequence-last_seq[kid] if kid in last_seq else None
            days_since=(clock[0]-last_at[kid]).total_seconds()/86400 if kid in last_at else None
            if before['due_at']:
                check(datetime.fromisoformat(before['due_at'])<=clock[0],'review_before_due',id=kid,due=before['due_at'])
            elif gap is not None and gap<before['gap']:
                daystats['shortened_gaps']+=1
                emit(events,dict(event='shortened_gap',day=day+1,id=kid,expected=before['gap'],actual=gap))
            # Simulated human memory is independent of FSRS, not derived from its predictions.
            ability=skill.setdefault(kid,dict(strength=rng.uniform(.2,1.5),difficulty=rng.uniform(.05,.5)))
            probability=max(.08,min(.96,(.65+.30*(1-math.exp(-ability['strength'])))*math.exp(-(days_since or 0)/(4+ability['strength']*7))-ability['difficulty']*.15-fatigue*.35))
            remembered=rng.random()<probability
            rating=rng.choices(['clear','hard','forgot'],[.83,.15,.02] if remembered else [.05,.40,.55])[0]
            hint=not remembered and rng.random()<.45
            wrong=rng.random()<(0.05 if remembered else .38)
            if wrong:
                bad=app.check_spelling(app.SpellingCheck(id=str(__import__('uuid').uuid4()),question_id=q['question_id'],answer='__WRONG__'))
                check(not bad['correct'],'invalid_answer_accepted',id=kid)
            if hint:app.reveal(q['question_id'])
            correct=app.check_spelling(app.SpellingCheck(id=str(__import__('uuid').uuid4()),question_id=q['question_id'],answer=k['answer']))
            check(correct['correct'],'canonical_answer_rejected',id=kid)
            body=app.Submission(question_id=q['question_id'],answer=k['answer'],confidence=rating)
            result=app.submit(body)
            if rng.random()<.06:
                duplicate=app.submit(body);check(duplicate['id']==result['id'],'duplicate_created_new_answer',id=kid);daystats['duplicate_retries']+=1
            independent=not hint and not wrong and rating=='clear'
            expected_rating=Rating.Again if hint or wrong or rating=='forgot' else Rating.Hard if rating=='hard' else Rating.Good
            card=Card.from_json(stored) if stored else Card(card_id=1)
            expected_card,_=FSRS.review_card(card,expected_rating,review_datetime=clock[0].astimezone(timezone.utc))
            expected_streak=(before['streak'] or 0)+1 if independent else 0
            delayed=bool(before['last_at'] and clock[0]-datetime.fromisoformat(before['last_at'])>=timedelta(hours=24))
            with db.connect() as c:
                after=state(c,kid)
                actual_card=json.loads(c.execute(text('SELECT card_json FROM memory_states WHERE knowledge_id=:k'),dict(k=kid)).scalar())
                answer_due=c.execute(text('SELECT due_at FROM answers WHERE question_id=:q'),dict(q=q['question_id'])).scalar()
            check(actual_card==expected_card.to_dict(),'fsrs_state_differs_from_library',id=kid)
            check(after['attempts']==(before['attempts'] or 0)+1,'answer_count_mismatch',id=kid)
            check(after['streak']==expected_streak,'streak_wrong',id=kid)
            check(after['gap']==(2 if rating=='forgot' else 4 if rating=='hard' or not independent else 8),'feedback_gap_wrong',id=kid)
            check(bool(after['due_at'])==bool(independent and (delayed or expected_streak>=3)),'graduation_rule_wrong',id=kid)
            check(answer_due==result['due_at']==after['due_at'],'saved_due_mismatch',id=kid)
            if after['due_at']:
                check(datetime.fromisoformat(after['due_at'])>clock[0],'next_due_not_future',id=kid)
                daystats['scheduled']+=1
            daystats['answers']+=1;daystats[rating]+=1;daystats['hints']+=hint;daystats['misspellings']+=wrong;stats['answers']+=1
            emit(events,dict(event='answer',day=day+1,time=clock[0],id=kid,stage=k['stage'],question_id=q['question_id'],rating=rating,hint=hint,wrong=wrong,independent=independent,gap=gap,days_since=days_since,pool=pool_before,before=before,after=after,fsrs=actual_card))
            ability['strength']+=.6 if independent else .18
            last_seq[kid]=sequence+1;last_at[kid]=clock[0];last_questions.append(q['question_id'])
            if rng.random()<.035 and last_questions:
                # Correct a recent subjective rating; use actual endpoint and replay path.
                qid=rng.choice(last_questions[-8:]);new_rating=rng.choice(['clear','hard','forgot'])
                app.feedback(app.Feedback(question_id=qid,confidence=new_rating));daystats['feedback_edits']+=1
                emit(events,dict(event='feedback_edit',day=day+1,question_id=qid,rating=new_rating,time=clock[0]))
            if rng.random()<.035:
                db.dispose();restored=app.next_question()
                if restored['kind']=='recall':
                    again=app.next_question();check(restored.get('question_id')==again.get('question_id'),'pending_not_restored')
                daystats['reopens']+=1
        # Real daily plan, all curve points, recent daily histories, and database invariants.
        plan=app.learning_plan();profile=app.learning_profile_stats.build
        with db.connect() as c:
            counts=dict(c.execute(text('SELECT kind,COUNT(*) FROM daily_tasks WHERE day=:d GROUP BY kind'),dict(d=date)).all())
            check(plan['new_limit']==50 and plan['review_limit']==50,'settings_changed')
            check(plan['new_admitted']<=50,'daily_new_limit_exceeded',actual=plan['new_admitted'])
            check(plan['review_admitted']<=50,'daily_review_limit_exceeded',actual=plan['review_admitted'])
            check(counts.get('new',0)<=50 and counts.get('review',0)<=50,'raw_daily_admission_limit_exceeded',actual=counts)
            check(not c.execute(text('SELECT 1 FROM progress p WHERE p.attempts!=(SELECT COUNT(*) FROM answers a WHERE a.knowledge_id=p.knowledge_id) LIMIT 1')).first(),'progress_history_count_differs')
            check(not c.execute(text('SELECT 1 FROM review_queue r JOIN progress p ON p.knowledge_id=r.knowledge_id WHERE r.due_at IS NOT p.due_at LIMIT 1')).first(),'queue_progress_due_differs')
            check(c.execute(text('PRAGMA quick_check')).scalar()=='ok','sqlite_integrity')
            data=profile(c,clock[0]);curve=data['memory_curve']
            check(all(0<=p['personal']<=1 and 0<=p['default']<=1 for p in curve['points']),'curve_out_of_range')
            check(all(curve['points'][i]['personal']>=curve['points'][i+1]['personal'] for i in range(120)),'curve_not_monotonic')
            pool=consolidation_count(c,clock[0])
            check(pool<=12,'pool_exceeds_twelve',actual=pool)
            waiting=max(0,len(consolidation_pending(c,clock[0]))-pool)
            # Full vs incremental replay must be identical, including corrected feedback.
        record=dict(day=day+1,date=date,absent=False,**dict(daystats),stages=dict(stages),pool_end=pool,waiting_end=waiting,plan=plan,curve=curve,profile_summary=data['summary'],raw_slots=counts,p95_next_ms=sorted(latencies)[int(len(latencies)*.95)] if latencies else 0,elapsed_seconds=time.perf_counter()-began)
        emit(days,record);daily.append(record);stats['active_days']+=1
        print(json.dumps(dict(seed=seed,day=day+1,answers=daystats['answers'],new=plan['new_admitted'],review=plan['review_admitted'],pool=pool,faults=len(faults))),flush=True)
    with db.connect() as c:
        totals=dict(answers=c.execute(text('SELECT COUNT(*) FROM answers')).scalar(),introduced=c.execute(text('SELECT COUNT(*) FROM progress WHERE introduced=1')).scalar(),stages=[list(r) for r in c.execute(text('SELECT COALESCE(l.stage,1),COUNT(*) FROM answers a LEFT JOIN course_links l ON l.knowledge_id=a.knowledge_id GROUP BY COALESCE(l.stage,1)'))])
    events.close();days.close();db.dispose()
    summary=dict(seed=seed,days=args.days,statistics=dict(stats),totals=totals,faults=faults,missed_days=[d+1 for d in sorted(missed) if d<args.days])
    (folder/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    with (folder/'daily.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=['day','date','absent','answers','introduced','clear','hard','forgot','hints','misspellings','pool_end','scheduled','stopped_for_time','p95_next_ms','elapsed_seconds'],extrasaction='ignore');writer.writeheader();writer.writerows(daily)
    return summary

if __name__=='__main__':
    template=OUT/'template.db'
    if not template.exists():
        engine=create_engine('sqlite:///'+str(template));app.initialize(engine,with_bulk=True);engine.dispose()
    summaries=[]
    for seed in map(int,args.seeds.split(',')):summaries.append(run(seed,template))
    (OUT/'summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding='utf-8')
    print('COMPLETE '+str(OUT),flush=True)
