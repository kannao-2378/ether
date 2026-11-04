"""Opt-in authored starter slice in the independent test database.

Reuses normal questions, answers, mastery and review instead of inventing progress.
No code path activates this course automatically in a real learner database.
"""
import hashlib
import json
from pathlib import Path
from sqlalchemy import text
import curriculum_engine as ce
import transfer_evidence as evidence
import selection_cache

RESOURCE=Path(__file__).parent/'resources/starter_course.json'
PACKS={'starter':RESOURCE,'mainline':RESOURCE.with_name('mainline_course.json')}
FLAG='starter-course-preview'
COURSE='starter-preview'

def state(c):
    raw=c.execute(text('SELECT value FROM app_settings WHERE key=:k'),dict(k=FLAG)).scalar()
    return json.loads(raw) if raw else None

def enabled(c):return state(c) is not None

def load(pack='starter'):
    if pack not in PACKS:raise ValueError('未知课程包')
    spec=json.loads(PACKS[pack].read_text(encoding='utf-8'))
    validate(spec)
    return spec

def validate(spec):
    keys={g['key'] for g in spec['goals']}
    if len(keys)!=len(spec['goals']) or spec['course_id']!=COURSE:raise ValueError('起步课程身份无效')
    graph={g['key']:g.get('requires',[]) for g in spec['goals']}
    checked=set()
    def visit(k,chain):
        if k in checked:return
        if k in chain or k not in graph:raise ValueError('起步课程先修无效')
        for dep in graph[k]:visit(dep,chain|{k})
        checked.add(k)
    for key in keys:visit(key,set())
    taught=[]; tests=[]
    for g in spec['goals']:
        taught += [g['english'],g['usage'],g['sentence'],g.get('phrase','')]
        taught += [m['en'] for m in g['materials']]
        for v in g.get('variants',[]):
            if not v['requires'] or any(x not in keys for x in v['requires']):raise ValueError('迁移材料缺少明确先修')
            if v['en'] not in v['accepted_answers']:raise ValueError('规范答案未列入接受范围')
            tests.append(v['en'])
    # Static guard against preparing materials with the future full answer.
    if spec['review']['status']=='reviewed_original_starter':
        for answer in tests:
            if any(evidence.key(answer) in evidence.key(part) for part in taught if part):raise ValueError('教学内容泄漏迁移答案')
        if len(set(tests))!=len(tests):raise ValueError('迁移题重复')
    elif spec['review']['status']=='authored_mainline_core':
        # The same sentence may legitimately appear in multiple topics. Actual
        # exposure determines recall vs transfer; never claim all are unseen.
        for g in spec['goals']:
            for v in g.get('variants',[]):
                if evidence.key(v['en']) in {evidence.key(g['english']),evidence.key(g['sentence'])}:
                    raise ValueError('情境题不能复制本课示范')
    else:raise ValueError('缺少课程内容审核标记')

def clean_cards(c,spec):
    """Strip inherited examples/extensions that may disclose the future answers."""
    saved=state(c);mapping=saved['ids']
    # Other opt-in pilots restore their rows at initialization. Their cards must
    # not silently become this starter course's extra lessons after reopening.
    for gid,allowed in saved.get('member_ids',{}).items():
        for (kid,) in c.execute(text('SELECT knowledge_id FROM curriculum_lessons WHERE goal_id=:g'),dict(g=gid)).all():
            if kid not in allowed:c.execute(text('DELETE FROM curriculum_lessons WHERE goal_id=:g AND knowledge_id=:k'),dict(g=gid,k=kid))
    rows=c.execute(text('''SELECT DISTINCT k.id,k.answer,k.prompt,k.explanation FROM curriculum_lessons l
        JOIN knowledge k ON k.id=l.knowledge_id JOIN curriculum_paths p ON p.goal_id=l.goal_id
        WHERE p.course_id=:c'''),dict(c=COURSE)).mappings().all()
    by_en={evidence.key(g['english']):g for g in spec['goals']}
    variant={evidence.key(v['en']):v for g in spec['goals'] for v in g.get('variants',[])}
    notes={evidence.key(k):v for k,v in spec['word_notes'].items()}
    for r in rows:
        old=c.execute(text('SELECT payload FROM knowledge_details WHERE knowledge_id=:k'),dict(k=r['id'])).scalar()
        previous=json.loads(old) if old else {}
        # Pronunciation can be retained. Teaching examples, derived grammar and
        # source labels are rebuilt from this reviewed slice, not inherited.
        details={k:previous[k] for k in ['ipa_us','syllables','stress','pronunciation_parts'] if previous.get(k)}
        en=r['answer'];key=evidence.key(en);note=notes.get(key);g=by_en.get(key);v=variant.get(key)
        usage=g['usage'] if g else note['usage'] if note else ('用已经学过的结构表达当前情境。' if v else r['explanation'])
        examples=[dict(en=g['sentence'],zh=g['sentence_zh'])] if g else [dict(en=en,zh=r['prompt'])]
        details.update(entry_type='word' if note else 'sentence' if en.endswith('.') else 'phrase',
            pos=note['pos'] if note else '句子' if en.endswith('.') else '固定搭配／短语',
            usage=usage,examples=examples,speech_text=en,knowledge_points=[],forms=[],roots=None,
            extensions=[],variations=[],review_status=spec['review']['method'],
            sources=spec['references'],starter_version=spec['version'])
        if v:details['accepted_answers']=v['accepted_answers']
        c.execute(text('UPDATE knowledge_details SET payload=:p,version=101 WHERE knowledge_id=:k'),dict(k=r['id'],p=json.dumps(details,ensure_ascii=False)))
    # step() also considers legacy members for variations: keep only this slice's
    # registered members in its scope. Old questions/answers are never deleted.
    for gid in mapping.values():
        c.execute(text('DELETE FROM group_members WHERE group_id=:g AND knowledge_id NOT IN (SELECT knowledge_id FROM curriculum_lessons WHERE goal_id=:g)'),dict(g=gid))
    selection_cache.invalidate()

def activate(c,*,test_only=False,pack='starter'):
    if not test_only:raise ValueError('起步试学只能在独立测试模式启用')
    if enabled(c):
        if state(c).get('pack','starter')!=pack:raise ValueError('请先退出当前课程试学，再选择其他课程包')
        return report(c)
    if c.execute(text('SELECT 1 FROM answers LIMIT 1')).first() or c.execute(text('SELECT 1 FROM questions LIMIT 1')).first() or c.execute(text('SELECT 1 FROM progress WHERE introduced=1 OR level>0 LIMIT 1')).first():
        raise ValueError('请先清空测试进度，再启用起步试学；真实学习数据不受影响')
    spec=load(pack)
    prior=dict(c.execute(text("SELECT id,status FROM curriculum_goals WHERE status!='draft'")).all())
    prior_prerequisites=[list(row) for row in c.execute(text('SELECT goal_id,prerequisite_id FROM curriculum_prerequisites'))]
    prior_owners={}
    # The old foundation grouped I under drink-water. In a fresh test preview it
    # is a genuine shared prerequisite, using the same knowledge ID and records.
    old_owner=c.execute(text("SELECT group_id FROM group_primary WHERE knowledge_id='word-i'")).scalar()
    if old_owner and old_owner!='word-i':
        prior_owners['word-i']=old_owner
        c.execute(text("INSERT OR IGNORE INTO learning_groups VALUES('word-i','word-i','I','word')"))
        c.execute(text("UPDATE group_primary SET group_id='word-i' WHERE knowledge_id='word-i'"))
        ce.member(c,'word-i','word-i','word',0)
    previous=c.execute(text("SELECT value FROM app_settings WHERE key='active-course'")).scalar() or json.dumps('all')
    c.execute(text('INSERT OR IGNORE INTO learning_courses VALUES(:i,:t,:g,:l)'),dict(i=COURSE,t=spec['title'],g=spec['scope'],l='入门试学'))
    c.execute(text('UPDATE learning_courses SET title=:t,goal=:g WHERE id=:i'),dict(i=COURSE,t=spec['title'],g=spec['scope']))
    ce.publish(c,spec,'preview:'+hashlib.sha256(PACKS[pack].read_bytes()).hexdigest())
    ids={g['key']:c.execute(text('SELECT p.goal_id FROM curriculum_paths p JOIN knowledge k ON k.id=p.goal_id WHERE p.course_id=:c AND lower(k.answer)=lower(:a)'),dict(c=COURSE,a=g['english'])).scalar() for g in spec['goals']}
    # Validate/publish while the old graph is intact, then scope the test course.
    c.execute(text("UPDATE curriculum_goals SET status='draft'"))
    for gid in ids.values():c.execute(text("UPDATE curriculum_goals SET status='ready' WHERE id=:g"),dict(g=gid))
    member_ids={gid:list(c.execute(text('SELECT knowledge_id FROM curriculum_lessons WHERE goal_id=:g'),dict(g=gid)).scalars()) for gid in ids.values()}
    payload=dict(pack=pack,version=spec['version'],ids=ids,member_ids=member_ids,prior_status=prior,previous_course=previous,prior_owners=prior_owners,prior_prerequisites=prior_prerequisites)
    c.execute(text('INSERT INTO app_settings VALUES(:k,:v)'),dict(k=FLAG,v=json.dumps(payload)))
    c.execute(text("DELETE FROM app_settings WHERE key='sourced-transfer-pilot'"))
    c.execute(text("INSERT INTO app_settings VALUES('active-course',:v) ON CONFLICT(key) DO UPDATE SET value=excluded.value"),dict(v=json.dumps(COURSE)))
    c.execute(text('UPDATE test_clock SET stage=NULL WHERE id=1'))
    clean_cards(c,spec)
    return report(c)

def restore(c):
    if enabled(c):clean_cards(c,load(state(c).get('pack','starter')))

def can_challenge(c,kid,stamp):
    if not enabled(c):return True
    entry=c.execute(text('''SELECT l.goal_id,l.role FROM curriculum_lessons l JOIN curriculum_paths p ON p.goal_id=l.goal_id
        WHERE p.course_id=:c AND l.knowledge_id=:k LIMIT 1'''),dict(c=COURSE,k=kid)).first()
    if not entry:return True
    gid,role=entry
    if ce.blockers(c,gid):return False
    if role in ('phrase','sentence','transfer'):
        import group_learning
        if not ce.known(c,gid) or not group_learning.requirements_met(c,kid,stamp=stamp):return False
        if role=='transfer':
            basics=c.execute(text("SELECT knowledge_id FROM curriculum_lessons WHERE goal_id=:g AND role IN ('phrase','sentence')"),dict(g=gid)).scalars().all()
            return bool(basics) and all(ce.known(c,k) for k in basics)
    return True

def exit_preview(c):
    saved=state(c)
    if not saved:return
    c.execute(text("UPDATE curriculum_goals SET status='draft'"))
    for gid,status in saved['prior_status'].items():
        c.execute(text('UPDATE curriculum_goals SET status=:s WHERE id=:g'),dict(g=gid,s=status))
    c.execute(text('DELETE FROM curriculum_prerequisites'))
    for gid,dep in saved['prior_prerequisites']:
        c.execute(text('INSERT INTO curriculum_prerequisites VALUES(:g,:p)'),dict(g=gid,p=dep))
    spec=json.loads(ce.MANIFEST.read_text(encoding='utf-8'))
    goals={g['key']:g for g in spec['goals']}
    for line in ce.TRANSFER_PACK.read_text(encoding='utf-8-sig').splitlines():
        if not line.strip() or line.startswith('#'):continue
        key,en,zh,deps=[x.strip() for x in line.split('|')]
        goals[key].setdefault('variants',[]).append(dict(en=en,zh=zh,requires=deps.split(',') if deps else []))
    ce.publish(c,spec,'restore-original-after-starter')
    for gid,status in saved['prior_status'].items():
        c.execute(text('UPDATE curriculum_goals SET status=:s WHERE id=:g'),dict(g=gid,s=status))
    for gid in saved['ids'].values():
        if gid not in saved['prior_status']:
            c.execute(text("UPDATE curriculum_goals SET status='draft' WHERE id=:g"),dict(g=gid))
        c.execute(text('DELETE FROM group_members WHERE group_id=:g AND knowledge_id NOT IN (SELECT knowledge_id FROM curriculum_lessons WHERE goal_id=:g)'),dict(g=gid))
    c.execute(text('DELETE FROM curriculum_paths WHERE course_id=:c'),dict(c=COURSE))
    c.execute(text('DELETE FROM app_settings WHERE key=:k'),dict(k=FLAG))
    for kid,owner in saved.get('prior_owners',{}).items():
        c.execute(text('UPDATE group_primary SET group_id=:g WHERE knowledge_id=:k'),dict(g=owner,k=kid))
    c.execute(text("UPDATE app_settings SET value=:v WHERE key='active-course'"),dict(v=saved['previous_course']))
    c.execute(text('UPDATE test_clock SET stage=NULL WHERE id=1'))
    selection_cache.invalidate()

def report(c):
    saved=state(c)
    if not saved:return None
    rows=[]
    spec=load(saved.get('pack','starter'))
    for g in spec['goals']:
        gid=saved['ids'][g['key']]
        scope=c.execute(text("SELECT l.knowledge_id,l.role FROM curriculum_lessons l WHERE l.goal_id=:g AND l.role!='transfer'"),dict(g=gid)).all()
        passed=bool(scope) and all(ce.known(c,k) for k,_ in scope)
        rows.append(dict(id=gid,title=g['chinese'],objective=g['objective'],topic_id=g.get('topic_id'),unit=g['unit'],passed=passed,
                         blockers=len(ce.blockers(c,gid))))
    candidates=c.execute(text("SELECT l.knowledge_id FROM curriculum_lessons l JOIN curriculum_paths p ON p.goal_id=l.goal_id WHERE p.course_id=:c AND l.role='transfer'"),dict(c=COURSE)).scalars().all()
    return dict(version=saved['version'],pack=saved.get('pack','starter'),title=spec['title'],groups=rows,
                transfer_questions=len(candidates),unseen_transfer=sum(evidence.classify(c,k,'transfer')[0]=='transfer' for k in candidates),
                scope=spec['scope'],objective_count=len(spec.get('objective_tasks',[])),real_records_changed=False)
