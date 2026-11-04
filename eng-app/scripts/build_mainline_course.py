"""Build the whole authored topic spine from static resources; never open learner DBs."""
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'backend/resources/mainline_lessons.psv'
OUT=ROOT/'backend/resources/mainline_course.json'

def words(s):
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?",s)

def build():
    design=json.loads((ROOT/'项目说明/课程设计/通用主线目标清单.json').read_text(encoding='utf-8'))
    route=json.loads((ROOT/'项目说明/课程设计/课程路线v4.json').read_text(encoding='utf-8'))
    bank=json.loads((ROOT/'backend/resources/compiled_courses.json').read_text(encoding='utf-8'))
    lex={w['answer'].casefold():w for w in bank['words']}
    overrides=ROOT/'backend/resources/mainline_word_notes.json'
    notes=json.loads(overrides.read_text(encoding='utf-8')) if overrides.exists() else {}
    topics={t['id']:t for t in design['topics']}
    placement={t['topic_id']:t['main_window'] for t in route['topic_placement']}
    stages={s['id']:s for s in route['stages']}
    records={}
    for line in SOURCE.read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):continue
        fields=line.split('|')
        if len(fields)!=11:raise ValueError('invalid authored row '+fields[0])
        tid,en,zh,usage,demo,dzh,a,az,b,bz,deps=fields
        if tid in records:raise ValueError('duplicate topic '+tid)
        records[tid]=dict(id=tid,en=en,zh=zh,usage=usage,demo=demo,dzh=dzh,tests=[(a,az),(b,bz)],deps=deps.split(',') if deps else [])
    if set(records)!=set(topics):raise ValueError('topic coverage mismatch')
    ordered=[];visiting=set()
    def visit(tid):
        if tid in visiting:raise ValueError('cyclic authored prerequisites '+tid)
        if tid not in records:raise ValueError('unknown prerequisite '+tid)
        if tid in ordered:return
        visiting.add(tid)
        for dep in records[tid]['deps']:visit(dep)
        visiting.remove(tid);ordered.append(tid)
    for tid in sorted(records,key=lambda t:(placement[t],int(t[1:3]),int(t.split('.')[1]))):visit(tid)
    missing=set();goals=[];mapping={};objective_tasks=[]
    for tid in ordered:
        r=records[tid];topic=topics[tid];key='mainline-'+tid.replace('.','-')
        terms={t.casefold():t for text in [r['en'],r['demo']]+[s for s,_ in r['tests']] for t in words(text)}
        if tid=='U01.1':terms.update(he='he',we='we',they='they')
        mats=[]
        for norm,term in sorted(terms.items()):
            if norm==r['en'].casefold():continue
            note=notes.get(norm)
            if note is None:
                entry=lex.get(norm)
                if entry:
                    meaning=entry['prompt'].replace('\\n','；').replace('\n','；').strip()
                    note=dict(zh=meaning,pos=entry.get('details',{}).get('pos') or '词汇',usage=meaning,source_asset_id=entry['id'],source='ECDICT / packaged lexical resource (MIT)')
                    notes[norm]=note
            if not note:missing.add(norm);continue
            mats.append(dict(en='I' if norm=='i' else term.lower() if norm!='english' else 'English',zh=note['zh'],usage=note['usage']))
        variants=[]
        # Pronoun recognition is material training, not sentence transfer.
        if tid!='U01.1':
            for en,zh in r['tests']:
                variants.append(dict(en=en,zh=zh,requires=[key],accepted_answers=[en]))
        g=dict(key=key,id='word-i' if tid=='U01.1' else key,unit=placement[tid],english=r['en'],chinese=r['zh'],
               objective=topic['title'],usage=r['usage'],sentence=r['demo'],sentence_zh=r['dzh'],materials=mats,
               requires=['mainline-'+d.replace('.','-') for d in r['deps']],difficulty=min(6,max(1,int(placement[tid][1:]))),
               variants=variants,topic_id=tid,objective_ids=[o['id'] for o in topic['goals']])
        goals.append(g);mapping[key]=g['objective_ids']
        for o in topic['goals']:
            text=o['objective']
            mode='listening_speaking' if any(w in text for w in ['听','发音','口头','口语','跟读']) else 'open_task' if any(w in text for w in ['交流','协商','语气','段落','转述','讨论','回应','阅读理解']) else 'guided_written'
            objective_tasks.append(dict(id=o['id'],topic_id=tid,objective=text,mode=mode,
                lesson=key,assessment_status='requires_separate_evidence',
                note='核心例题只覆盖本目标的部分用法；不从同课拼写成绩推导整项目标掌握'))
    if missing:raise ValueError('Untranslated material words: '+', '.join(sorted(missing)))
    pack=dict(version='mainline-v1',course_id='starter-preview',title='通用英语主线 · 148课题',
        scope='148课题核心书写课程；729目标目录均关联，听说与开放任务不由拼写认证',
        review=dict(status='authored_mainline_core',method='本项目原创课题讲解和有限答案练习；AI辅助语言核对、依赖和曝光检查；非官方教材、非全能力认证'),
        references=[dict(title='ECDICT · 部分词汇中文释义',url='https://github.com/skywind3000/ECDICT',license='MIT')],units=[dict(id=s['id'],title=s['name'],goal=s['description'],position=i+1) for i,s in enumerate(route['stages'])],
        goals=goals,word_notes=notes,mapped_objectives=mapping,objective_tasks=objective_tasks,
        source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        assessment_policy=dict(fixed_answers_only=True,automatic_full_objective_certification=False,
            unseen_context_only_after_materials=True,fsrs_unchanged=True),
        counts=dict(topics=len(goals),objectives=len(objective_tasks),context_questions=sum(len(g['variants']) for g in goals),
            reusable_words=len({m['en'].casefold() for g in goals for m in g['materials']})))
    OUT.write_text(json.dumps(pack,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return pack

if __name__=='__main__':print(json.dumps(build()['counts'],ensure_ascii=False))
