import os
"""Version 5: question gaps within a day, FSRS-6 for long-term memory."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from fsrs import Scheduler, Card, Rating

FSRS = Scheduler(desired_retention=0.9, learning_steps=(), relearning_steps=(), maximum_interval=180, enable_fuzzing=False)
FSRS_TIMED = Scheduler(desired_retention=0.9, maximum_interval=180, enable_fuzzing=False)
def time_queue_enabled():return os.environ.get('PELS_FSRS_TIME_QUEUE')=='1'
def item_due(c,kid,stamp):
    row=c.execute(text('SELECT card_json FROM memory_states WHERE knowledge_id=:k'),dict(k=kid)).first()
    return Card.from_json(row[0]).due if row else stamp
CONSOLIDATION_LIMIT = 12

def consolidation_pending(c, stamp):
    has_questions=c.execute(text("SELECT 1 FROM sqlite_master WHERE name='questions'")).first()
    pending=" OR EXISTS(SELECT 1 FROM questions q WHERE q.knowledge_id=p.knowledge_id AND NOT EXISTS(SELECT 1 FROM answers a WHERE a.question_id=q.id))" if has_questions else ''
    return c.execute(text('''SELECT p.knowledge_id FROM progress p
      LEFT JOIN review_queue r ON r.knowledge_id=p.knowledge_id
      WHERE p.introduced=1 AND ((r.knowledge_id IS NOT NULL AND r.due_at IS NULL) OR (r.knowledge_id IS NULL AND (p.due_at IS NULL OR julianday(p.due_at)<=julianday(:t)))'''+pending+') ORDER BY '+("CASE WHEN EXISTS(SELECT 1 FROM questions q WHERE q.knowledge_id=p.knowledge_id AND NOT EXISTS(SELECT 1 FROM answers a WHERE a.question_id=q.id)) THEN 0 ELSE 1 END," if has_questions else '')+'p.rowid'),dict(t=stamp.isoformat())).scalars().all()

def consolidation_count(c, stamp):
    """Persistent 12-slot active pool. Corrected/lapsed extras wait without lost evidence."""
    c.execute(text('CREATE TABLE IF NOT EXISTS consolidation_slots(knowledge_id TEXT PRIMARY KEY,entered_at TEXT NOT NULL)'))
    pending=consolidation_pending(c,stamp)
    ids=set(pending)
    active=c.execute(text('SELECT knowledge_id FROM consolidation_slots ORDER BY rowid')).scalars().all()
    for kid in active:
        if kid not in ids:c.execute(text('DELETE FROM consolidation_slots WHERE knowledge_id=:k'),dict(k=kid))
    active=[k for k in active if k in ids]
    for kid in pending:
        if len(active)>=CONSOLIDATION_LIMIT:break
        if kid not in active:
            c.execute(text('INSERT INTO consolidation_slots VALUES(:k,:t)'),dict(k=kid,t=stamp.isoformat()))
            active.append(kid)
    return len(active)

def install_memory(c):
    c.execute(text("CREATE TABLE IF NOT EXISTS memory_states(knowledge_id TEXT PRIMARY KEY,card_json TEXT NOT NULL,last_answer TEXT NOT NULL,algorithm TEXT NOT NULL)"))
    c.execute(text('CREATE TABLE IF NOT EXISTS consolidation_slots(knowledge_id TEXT PRIMARY KEY,entered_at TEXT NOT NULL)'))


def update_coverage(c, kid, stamp):
    """Derived daily coverage, recalculated after feedback corrections too."""
    from datetime import timezone
    c.execute(text('CREATE TABLE IF NOT EXISTS daily_coverage(day TEXT,knowledge_id TEXT,source_question_id TEXT,PRIMARY KEY(day,knowledge_id,source_question_id))'))
    # This source's previous coverage may no longer be valid after a correction.
    c.execute(text('DELETE FROM daily_coverage WHERE source_question_id IN (SELECT question_id FROM answers WHERE knowledge_id=:k)'),dict(k=kid))
    rows=c.execute(text('''SELECT a.*,
      COALESCE((SELECT confidence FROM feedback_events f WHERE f.question_id=a.question_id ORDER BY f.rowid DESC LIMIT 1),a.confidence) AS rating
      FROM answers a WHERE a.knowledge_id=:k AND a.correct=1 AND a.revealed=0
      AND NOT EXISTS(SELECT 1 FROM test_skips ts WHERE ts.question_id=a.question_id)
      AND NOT EXISTS(SELECT 1 FROM spelling_checks s WHERE s.question_id=a.question_id AND s.correct=0 AND julianday(s.created_at)<=julianday(a.created_at))'''),dict(k=kid)).mappings()
    parents=[];current=kid
    while current:
        current=c.execute(text('SELECT parent_id FROM course_links WHERE knowledge_id=:k'),dict(k=current)).scalar()
        if current:parents.append(current)
    for row in rows:
        if row['rating']!='clear':continue
        day=datetime.fromisoformat(row['created_at']).astimezone(timezone(timedelta(hours=8))).date().isoformat()
        covered=set(parents)
        if c.execute(text("SELECT 1 FROM sqlite_master WHERE name='knowledge_components'")).first():
            covered.update(c.execute(text("SELECT component_id FROM knowledge_components WHERE knowledge_id=:k AND relation='contains_expression'"),dict(k=kid)).scalars())
        covered.discard(kid)
        for parent in covered:
            c.execute(text('INSERT OR IGNORE INTO daily_coverage VALUES (:d,:k,:q)'),dict(d=day,k=parent,q=row['question_id']))

def rebuild(c, kid, incremental=False):
    install_memory(c)
    memory=c.execute(text('SELECT * FROM memory_states WHERE knowledge_id=:k'),dict(k=kid)).mappings().first()
    state=c.execute(text('SELECT p.* FROM progress p JOIN review_queue r ON r.knowledge_id=p.knowledge_id WHERE p.knowledge_id=:k AND r.version IN (5,6)'),dict(k=kid)).mappings().first() if incremental else None
    if not memory:state=None
    after=c.execute(text('SELECT rowid FROM answers WHERE id=:a'),dict(a=memory['last_answer'])).scalar() if state else None
    if state and after is None:state=None
    rows=c.execute(text('''SELECT a.*,a.rowid AS seq,
      EXISTS(SELECT 1 FROM test_skips ts WHERE ts.question_id=a.question_id) AS skipped,
      COALESCE((SELECT confidence FROM feedback_events f WHERE f.question_id=a.question_id ORDER BY f.rowid DESC LIMIT 1),a.confidence) AS rating,
      (SELECT COUNT(*) FROM spelling_checks s WHERE s.question_id=a.question_id AND s.correct=0 AND julianday(s.created_at)<=julianday(a.created_at)) AS failed
      FROM answers a WHERE a.knowledge_id=:k AND (:after IS NULL OR a.rowid>:after) ORDER BY a.rowid ASC'''),dict(k=kid,after=after if state else None)).mappings().all()
    card=Card.from_json(memory['card_json']) if state else Card(card_id=1)
    if not rows:return
    streak=0; interval=0; last=None; due=None; target=0; level=0
    attempts=0;correct=0
    if state:
        streak=state['streak'];interval=state['interval_days'];level=state['level']
        last=datetime.fromisoformat(state['last_at']) if state['last_at'] else None
        attempts=state['attempts'];correct=state['correct']
    for a in rows:
        stamp=datetime.fromisoformat(a['created_at'])
        independent=bool(not a['skipped'] and a['correct'] and not a['revealed'] and not a['failed'] and a['rating']=='clear')
        rating=Rating.Again if not a['correct'] or a['revealed'] or a['failed'] or a['rating']=='forgot' else Rating.Hard if a['rating']=='hard' else Rating.Good
        if not a['skipped']:
            card,_=(FSRS_TIMED if time_queue_enabled() else FSRS).review_card(card,rating,review_datetime=stamp.astimezone(timezone.utc))
        delayed=bool(last and stamp-last>=timedelta(hours=24))
        if independent:
            streak+=1
            level=max(level,3)
            if delayed:
                interval=max(1,(card.due-stamp).total_seconds()/86400)
                level=5
            elif streak>=3:
                interval=1 if level<5 else max(1,(card.due-stamp).total_seconds()/86400)
            else: interval=0
        else:
            streak=0;interval=0;level=min(level,2)
        gap=2 if a['rating']=='forgot' else 4 if a['rating']=='hard' or not independent else 8
        due=(stamp+timedelta(days=interval)).isoformat() if interval else None
        target=a['seq']+gap+1
        if time_queue_enabled():
            due=card.due.isoformat();interval=max(0,(card.due-stamp).total_seconds()/86400);target=0;gap=0
        last=stamp
    if not rows:return
    c.execute(text("INSERT INTO memory_states VALUES(:k,:j,:a,'FSRS-6') ON CONFLICT(knowledge_id) DO UPDATE SET card_json=:j,last_answer=:a,algorithm='FSRS-6'"),dict(k=kid,j=card.to_json(),a=rows[-1]['id']))
    c.execute(text('''INSERT INTO review_queue (knowledge_id,due_sequence,due_at,gap,version)
      VALUES (:k,:s,:d,:g,:v) ON CONFLICT(knowledge_id) DO UPDATE SET due_sequence=:s,due_at=:d,gap=:g,version=:v'''),dict(k=kid,s=target,d=due,g=gap,v=6 if time_queue_enabled() else 5))
    c.execute(text('''UPDATE progress SET attempts=:a,correct=:c,streak=:s,level=:l,interval_days=:i,due_at=:d,last_at=:t WHERE knowledge_id=:k'''),dict(k=kid,a=attempts+len(rows),c=correct+sum(a['correct'] for a in rows),s=streak,l=level,i=interval,d=due,t=last.isoformat()))

def select_next(c, stamp, review_limit=30, new_limit=10, test_stage=None,active_course='all',exclude_context=False):
    """Retrieve one candidate in SQL, never materialize the entire curriculum."""
    if test_stage==4:
        # Preview each context before repeating one; production review rules stay intact.
        item=c.execute(text('''SELECT k.*,p.* FROM knowledge k JOIN progress p ON p.knowledge_id=k.id
          JOIN course_links l ON l.knowledge_id=k.id WHERE l.stage=4
          AND (:course='all' OR EXISTS(SELECT 1 FROM course_items ci JOIN course_units cu ON cu.id=ci.unit_id WHERE ci.knowledge_id=k.id AND cu.course_id=:course))
          ORDER BY (SELECT COUNT(*) FROM answers a WHERE a.knowledge_id=k.id),
          COALESCE(p.last_at,''),k.rowid LIMIT 1'''),dict(course=active_course)).mappings().first()
        if item:return ('recall' if item['introduced'] else 'learn'),dict(item)
        return 'done',None
    seq=c.execute(text('SELECT COALESCE(MAX(rowid),0)+1 FROM answers')).scalar()
    from datetime import timezone
    day=stamp.astimezone(timezone(timedelta(hours=8))).date().isoformat()
    c.execute(text('CREATE TABLE IF NOT EXISTS daily_tasks (day TEXT,knowledge_id TEXT,kind TEXT,PRIMARY KEY(day,knowledge_id))'))
    c.execute(text('CREATE TABLE IF NOT EXISTS daily_coverage(day TEXT,knowledge_id TEXT,source_question_id TEXT,PRIMARY KEY(day,knowledge_id,source_question_id))'))
    counts=dict(c.execute(text('SELECT kind,COUNT(*) FROM daily_tasks d WHERE day=:day GROUP BY kind'),dict(day=day)).all())
    remaining=counts.get('review',0)<review_limit
    admission=" AND (EXISTS (SELECT 1 FROM daily_tasks d WHERE d.day=:day AND d.knowledge_id=k.id) OR :remaining) "
    coverage_filter=' AND NOT EXISTS(SELECT 1 FROM daily_coverage cv WHERE cv.day=:day AND cv.knowledge_id=k.id)'
    stage_filter=(' AND COALESCE((SELECT stage FROM course_links cl WHERE cl.knowledge_id=k.id),1)=:stage' if test_stage else '')+coverage_filter
    if exclude_context:stage_filter+=" AND k.id NOT LIKE 'compose-%'"
    room=test_stage is not None or consolidation_count(c,stamp)<CONSOLIDATION_LIMIT
    params=dict(t=stamp.isoformat(),s=seq,day=day,remaining=remaining,stage=test_stage,course=active_course)
    params['room']=room
    base='''FROM knowledge k JOIN progress p ON p.knowledge_id=k.id
      LEFT JOIN review_queue r ON r.knowledge_id=k.id
      WHERE p.introduced=1 AND (CASE WHEN r.knowledge_id IS NULL THEN p.due_at ELSE r.due_at END IS NULL
      OR julianday(CASE WHEN r.knowledge_id IS NULL THEN p.due_at ELSE r.due_at END)<=julianday(:t))
      AND (:room OR k.id IN (SELECT knowledge_id FROM consolidation_slots))'''+('' if test_stage else ''' AND NOT EXISTS(SELECT 1 FROM transfer_materials tm JOIN progress mp ON mp.knowledge_id=tm.material_id WHERE tm.knowledge_id=k.id AND mp.level<3)''')+admission+stage_filter
    ready=c.execute(text('SELECT k.*,p.* '+base+''' AND (r.due_at IS NOT NULL OR COALESCE(r.due_sequence,0)<=:s)
      ORDER BY CASE WHEN COALESCE(r.due_at,p.due_at) IS NOT NULL THEN 0 ELSE 1 END,julianday(COALESCE(r.due_at,p.due_at)),COALESCE(r.due_sequence,0),k.id LIMIT 1'''),params).mappings().first()
    material_filter='' if test_stage else ' AND NOT EXISTS(SELECT 1 FROM transfer_materials tm JOIN progress mp ON mp.knowledge_id=tm.material_id WHERE tm.knowledge_id=k.id AND mp.level<3)'
    has_curriculum=not test_stage and c.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='course_items'")).first()
    course_filter=''' AND (EXISTS(SELECT 1 FROM course_items ci JOIN course_units cu ON cu.id=ci.unit_id WHERE ci.knowledge_id=k.id AND cu.course_id=:course)
      OR EXISTS(SELECT 1 FROM transfer_materials tm JOIN course_items ci ON ci.knowledge_id=tm.knowledge_id JOIN course_units cu ON cu.id=ci.unit_id JOIN course_links cl ON cl.knowledge_id=tm.knowledge_id JOIN progress pp ON pp.knowledge_id=cl.parent_id WHERE tm.material_id=k.id AND cu.course_id=:course AND pp.level>=3)
      OR EXISTS(SELECT 1 FROM course_links cl JOIN course_items ci ON ci.knowledge_id=cl.knowledge_id JOIN course_units cu ON cu.id=ci.unit_id WHERE cl.parent_id=k.id AND cu.course_id=:course))''' if active_course!='all' else ''
    material_filter+=course_filter
    course_order='CASE WHEN EXISTS(SELECT 1 FROM transfer_materials tm JOIN course_links cl ON cl.knowledge_id=tm.knowledge_id JOIN progress pp ON pp.knowledge_id=cl.parent_id WHERE tm.material_id=k.id AND pp.level>=3) THEN 0 ELSE 1 END,CASE WHEN EXISTS(SELECT 1 FROM course_items ci WHERE ci.knowledge_id=k.id) THEN 0 ELSE 1 END,(SELECT position FROM course_items ci WHERE ci.knowledge_id=k.id),' if has_curriculum else ''
    unseen=c.execute(text('SELECT k.*,p.* FROM knowledge k JOIN progress p ON p.knowledge_id=k.id WHERE p.introduced=0 AND NOT EXISTS (SELECT 1 FROM course_links l JOIN progress parent ON parent.knowledge_id=l.parent_id WHERE l.knowledge_id=k.id AND parent.level<3)'+material_filter+stage_filter+' ORDER BY '+course_order+'CASE WHEN EXISTS(SELECT 1 FROM course_links cl WHERE cl.knowledge_id=k.id) THEN 0 ELSE 1 END,k.rowid LIMIT 1'),params).mappings().first() if room and counts.get('new',0)<new_limit else None
    count=c.execute(text('SELECT COUNT(*) FROM progress WHERE introduced=1')).scalar()
    c.execute(text('CREATE TABLE IF NOT EXISTS daily_new_pacing(day TEXT PRIMARY KEY,last_sequence INTEGER NOT NULL)'))
    last_new=c.execute(text('SELECT last_sequence FROM daily_new_pacing WHERE day=:day'),dict(day=day)).scalar()
    new_turn=last_new is None or seq-1-last_new>=2
    def admit(kind,item):
        if kind=='learn':
            c.execute(text('INSERT INTO daily_new_pacing VALUES(:day,:s) ON CONFLICT(day) DO UPDATE SET last_sequence=:s'),dict(day=day,s=seq-1))
        # Composition picker admits the actual chosen variant, not this placeholder.
        if not item['id'].startswith('compose-'):
            c.execute(text('INSERT OR IGNORE INTO daily_tasks VALUES (:day,:k,:kind)'),dict(day=day,k=item['id'],kind='new' if kind=='learn' else 'review'))
        return kind,dict(item)
    if ready and ready['due_at']:return admit('recall',ready)
    if unseen and room and counts.get('new',0)<new_limit and (count<3 or not ready or new_turn):return admit('learn',unseen)
    if ready:return admit('recall',ready)
    fallback=c.execute(text('SELECT k.*,p.* '+base+''' ORDER BY CASE WHEN k.id=(SELECT knowledge_id FROM answers ORDER BY rowid DESC LIMIT 1) THEN 1 ELSE 0 END,COALESCE(r.due_sequence,0),k.id LIMIT 1'''),params).mappings().first()
    return admit('recall',fallback) if fallback else ('done',None)

def choose(c, rows, stamp):
    sequence=c.execute(text('SELECT COALESCE(MAX(rowid),0) FROM answers')).scalar()
    queues={r['knowledge_id']:dict(r) for r in c.execute(text('SELECT * FROM review_queue')).mappings()}
    available=[]
    for item in rows:
        if not item['introduced']:continue
        queue=queues.get(item['id'])
        if queue and queue['due_at'] and datetime.fromisoformat(queue['due_at'])>stamp:continue
        # Older date-based records are preserved if no v2 schedule exists yet.
        if not queue and item['due_at'] and datetime.fromisoformat(item['due_at'])>stamp:continue
        available.append((item,queue or {'due_sequence':0,'due_at':None}))
    ready=[pair for pair in available if pair[1]['due_at'] or pair[1]['due_sequence']<=sequence+1]
    ready.sort(key=lambda pair:(0 if pair[1]['due_at'] else 1,pair[1]['due_at'] or '',pair[1]['due_sequence'],pair[0]['id']))
    return ready,available
