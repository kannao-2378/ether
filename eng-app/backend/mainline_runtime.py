"""Production course installation; never reset answers, memory or prior progress."""
import copy
import hashlib
import json
from pathlib import Path
from sqlalchemy import text
import curriculum_engine as ce
import starter_course
import selection_cache
import re

COURSE='general-mainline'
FLAG='mainline-production-version'
PHONETIC_FLAG='mainline-pronunciation-version'

def install(c):
    # Isolated previews own their own teaching graph and must not mix packages.
    if starter_course.enabled(c):return
    resource=starter_course.PACKS['mainline']
    revision=hashlib.sha256(resource.read_bytes()).hexdigest()
    previous_version=c.execute(text('SELECT value FROM app_settings WHERE key=:k'),{'k':FLAG}).scalar()
    prior=json.loads(previous_version) if previous_version else None
    spec=copy.deepcopy(starter_course.load('mainline'))
    spec.update(course_id=COURSE,reuse_existing_roots=False,preserve_existing_ownership=True,automatic_aliases=False)
    for g in spec['goals']:g['id']=g['key']
    c.execute(text('INSERT OR IGNORE INTO learning_courses VALUES(:c,:t,:g,:l)'),dict(c=COURSE,t='通用英语主线',g=spec['scope'],l='基础至进阶核心书写'))
    if prior!=revision:
        ce.publish(c,spec,'production-mainline:'+revision)
        for u in spec['units']:
            c.execute(text('INSERT OR IGNORE INTO course_units VALUES(:u,:c,:t,:g,:p)'),dict(u=COURSE+'-'+u['id'],c=COURSE,t=u['title'],g=u['goal'],p=u['position']))
        for position,g in enumerate(spec['goals']):
            c.execute(text('INSERT OR IGNORE INTO course_items VALUES(:k,:u,:p)'),dict(k=g['id'],u=COURSE+'-'+g['unit'],p=position))
        # Transfer no scores: known() reads only latest direct evidence through
        # explicitly equivalent identities. English AND sense must agree.
        rows=c.execute(text('''SELECT DISTINCT k.id,k.answer,k.prompt FROM curriculum_lessons l
            JOIN curriculum_paths p ON p.goal_id=l.goal_id JOIN knowledge k ON k.id=l.knowledge_id
            WHERE p.course_id=:c'''),{'c':COURSE}).all()
        for kid,en,zh in rows:
            if not kid.startswith('mainline-'):continue
            aliases=c.execute(text('SELECT id,prompt FROM knowledge WHERE lower(trim(answer))=lower(trim(:a)) AND id!=:k'),dict(a=en,k=kid)).all()
            for alias,prompt in aliases:
                if ce.gloss(zh)==ce.gloss(prompt):
                    c.execute(text('INSERT OR IGNORE INTO curriculum_aliases VALUES(:k,:a)'),dict(k=kid,a=alias))
        decorate(c,spec)
        c.execute(text('INSERT INTO app_settings VALUES(:k,:v) ON CONFLICT(key) DO UPDATE SET value=excluded.value'),dict(k=FLAG,v=json.dumps(revision)))
        if prior is None:
            old=c.execute(text("SELECT value FROM app_settings WHERE key='active-course'")).scalar()
            c.execute(text("INSERT OR IGNORE INTO app_settings VALUES('mainline-previous-course',:v)"),dict(v=old or json.dumps('all')))
            c.execute(text("INSERT INTO app_settings VALUES('active-course',:v) ON CONFLICT(key) DO UPDATE SET value=excluded.value"),dict(v=json.dumps(COURSE)))
    # Legacy grouping may discover incidental members after a new knowledge
    # count. Restrict only the new groups to the published lesson membership.
    c.execute(text('''DELETE FROM group_members WHERE group_id IN
        (SELECT goal_id FROM curriculum_paths WHERE course_id=:c)
        AND NOT EXISTS(SELECT 1 FROM curriculum_lessons l WHERE l.goal_id=group_members.group_id AND l.knowledge_id=group_members.knowledge_id)'''),{'c':COURSE})
    phonetic_version=c.execute(text('SELECT value FROM app_settings WHERE key=:k'),{'k':PHONETIC_FLAG}).scalar()
    if prior!=revision or phonetic_version!='2':
        backfill_pronunciation(c)
        c.execute(text('INSERT INTO app_settings VALUES(:k,\'2\') ON CONFLICT(key) DO UPDATE SET value=excluded.value'),{'k':PHONETIC_FLAG})
    selection_cache.invalidate()

def backfill_pronunciation(c):
    """Reuse attested pronunciation only; never guess syllabification from spelling."""
    fields=('ipa_us','syllables','stress','pronunciation_parts')
    catalog={};quality={}
    for kid,en,raw in c.execute(text('SELECT k.id,k.answer,d.payload FROM knowledge k JOIN knowledge_details d ON d.knowledge_id=k.id')):
        d=json.loads(raw);key=en.strip().casefold()
        if not d.get('ipa_us') and not d.get('syllables'):continue
        score=int(bool(d.get('ipa_us')))+int(bool(d.get('syllables')))+int('·' in str(d.get('syllables','')))+3*int(kid.startswith('word-'))
        if score>quality.get(key,-1):catalog[key]={f:d[f] for f in fields if d.get(f)};quality[key]=score
    bundled=Path(__file__).parent/'resources/mainline_pronunciation.json'
    if bundled.exists():
        for key,reference in json.loads(bundled.read_text(encoding='utf-8')).items():
            entry=catalog.setdefault(key,{})
            for field in ('syllables','stress'):
                if not entry.get(field) and reference.get(field):entry[field]=reference[field]
    rows=c.execute(text('''SELECT DISTINCT k.id,k.answer,d.payload FROM curriculum_lessons l
        JOIN curriculum_paths p ON p.goal_id=l.goal_id JOIN knowledge k ON k.id=l.knowledge_id
        JOIN knowledge_details d ON d.knowledge_id=k.id WHERE p.course_id=:c'''),{'c':COURSE}).all()
    ignored={'i','you','we','they','he','she','it','a','an','the','to','of','am','is','are','be','do','does','did'}
    for kid,en,raw in rows:
        if not kid.startswith(('mainline-','auto-transfer-')):continue
        d=json.loads(raw);before=json.dumps(d,sort_keys=True)
        reference=catalog.get(en.strip().casefold())
        if reference:
            for field,value in reference.items():
                if not d.get(field):d[field]=value
        elif not d.get('ipa_us') and not any(part.get('ipa') for part in d.get('pronunciation_parts',[])):
            tokens=re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?",en)
            candidates=[w for w in tokens if w.casefold() not in ignored and w.casefold() in catalog]
            candidates=candidates or [w for w in tokens if w.casefold() in catalog]
            if candidates:
                word=candidates[0];ref=catalog[word.casefold()]
                d['pronunciation_parts']=[dict(en=word,ipa=ref.get('ipa_us',''),syllables=ref.get('syllables',''),stress=ref.get('stress',''))]
        if json.dumps(d,sort_keys=True)!=before:
            c.execute(text('UPDATE knowledge_details SET payload=:p WHERE knowledge_id=:k'),dict(k=kid,p=json.dumps(d,ensure_ascii=False)))

def decorate(c,spec):
    by_en={g['english'].casefold().rstrip('.!?'):g for g in spec['goals']}
    variants={v['en'].casefold().rstrip('.!?'):v for g in spec['goals'] for v in g['variants']}
    for r in c.execute(text('''SELECT DISTINCT k.id,k.answer,k.prompt,d.payload FROM curriculum_lessons l
        JOIN curriculum_paths p ON p.goal_id=l.goal_id JOIN knowledge k ON k.id=l.knowledge_id
        LEFT JOIN knowledge_details d ON d.knowledge_id=k.id WHERE p.course_id=:c'''),{'c':COURSE}).all():
        kid,en,zh,raw=r
        # Existing shared dictionary entries and their metadata remain intact.
        if not kid.startswith('mainline-'):continue
        old=json.loads(raw or '{}');key=en.casefold().rstrip('.!?')
        g=by_en.get(key);v=variants.get(key);note=spec['word_notes'].get(key)
        d={k:old[k] for k in ['ipa_us','syllables','stress','pronunciation_parts'] if old.get(k)}
        usage=g['usage'] if g else note['usage'] if note else old.get('usage','')
        example=dict(en=g['sentence'],zh=g['sentence_zh']) if g else dict(en=en,zh=zh)
        d.update(entry_type='word' if note else 'sentence' if en.endswith(('.','?','!')) else 'phrase',
                 pos=note['pos'] if note else '句子' if en.endswith(('.','?','!')) else '固定搭配／短语',
                 usage=usage,examples=[example],speech_text=en,knowledge_points=[],extensions=[],variations=[],
                 review_status=spec['review']['method'],sources=spec['references'],mainline_version=spec['version'])
        if v:d['accepted_answers']=v['accepted_answers']
        c.execute(text('UPDATE knowledge_details SET payload=:p,version=102 WHERE knowledge_id=:k'),dict(k=kid,p=json.dumps(d,ensure_ascii=False)))

def status(c):
    version=c.execute(text('SELECT value FROM app_settings WHERE key=:k'),{'k':FLAG}).scalar()
    if not version:return None
    count=c.execute(text('SELECT count(DISTINCT goal_id) FROM curriculum_paths WHERE course_id=:c'),{'c':COURSE}).scalar()
    return dict(course_id=COURSE,topics=count,version=json.loads(version),assessment='核心书写训练；完整听说与开放能力另行验证')
