"""Inventory packaged curriculum components against design goals, without DB access.

Candidates are not lesson-completion claims. This script only reads public resource
files and Python literal constants through a small AST evaluator; it never imports
the application or executes its install functions.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

# Representative teaching anchors, not exhaustive prerequisites or a word-frequency list.
ANCHORS_TEXT='''
U01.1|I;you;he;she;it;we;they
U01.2|I am;you are;he is;she is;am;is;are;busy;student
U01.3|this;that;a;an;book;This is a book.
U01.4|Is this;is not;Yes, it is.;No, it isn't.
U01.5|it;It is hot.;It is seven.;hot;Monday
U02.1|drink;eat;water;rice;drink water;eat rice
U02.2|read;learn;book;books;English;read books;learn English
U02.3|go;home;school;go home;go to school
U02.4|I;you;we;they;drink water;read books;learn English
U02.5|sleep;read a book;give;give you a book;to
U02.6|keep;make;door;open;happy;keep the door open
U03.1|have;I have;book;water
U03.2|my;your;his;her;our;their;my book
U03.3|help;me;you;him;her;us;them;help me
U03.4|I;my;me;her;help me;my book
U03.5|mine;yours;his;hers;ours;theirs;of
U03.6|myself;yourself;himself;herself;ourselves;themselves;by myself;each other
U04.1|do not;don't;am not;I don't;I am not
U04.2|Do you;Yes, I do.;No, I don't.
U04.3|what;who;where;What is this;Where is
U04.4|hello;name;sorry;please;Please say that again.;How do you spell
U04.5|who;which;whose;how;what kind of;Who called;Who did you call
U05.1|one;two;three;book;books;child;children
U05.2|a;an;the;some
U05.3|water;a glass of water;a cup of;two glasses of
U05.4|how many;how much;price
U05.5|some;any;no;someone;anyone;something;anything;each;every;all;both;other;another;the other;a lot of;lots of
U06.1|big;room;useful;book;a big room;a useful book
U06.2|tired;busy;useful;am;is;are;It is important to
U06.3|very;and;but
U06.4|my;book;room;big;useful;busy
U06.5|quick;quickly;good;well;look;feel;sound
U07.1|in;on;under;book;table
U07.2|next to;in front of;behind
U07.3|there is;there are;any
U07.4|at school;go to school;go home;at home;in
U07.5|to;from;into;out of;across;through;between;among;by;with
U08.1|at seven;on Monday;in May;in the morning;at night
U08.2|every day;always;usually;sometimes;everyday
U08.3|he works;she reads;has;does;doesn't
U08.4|when;what time;how often
U09.1|want;want water;water;book
U09.2|want to;want water;drink water;learn English;read books;wants
U09.3|need;need to;want;water;rest
U09.4|Do you want to;Do you need to;I don't want to;I don't need to
U09.5|want someone to;ask someone to;tell someone to;let;make
U10.1|like;likes;don't like;doesn't like
U10.2|like doing;like to;reading;read books;Reading is fun.
U10.3|enjoy;enjoy reading;enjoy learning English;reading
U10.4|love;don't like;prefer;prefer A to B
U10.5|good at;interested in;afraid of;doing
U11.1|plan to;hope to;read books;learn English
U11.2|decide to;decided to;learn English
U11.3|try to;learn to;learn English;learn to cook
U11.4|practice doing;keep doing;finish doing;reading;learning
U11.5|stop doing;stop to;remember doing;remember to;try doing;try to
U12.1|listen to;look at;music;listen to music;this picture
U12.2|wait for;look for;the bus;my keys
U12.3|talk to;ask for;ask someone;my friend;help
U12.4|look at;look for;look after
U12.5|turn on;turn off;pick up;look after;it
U12.6|do homework;make a decision;take a break;have breakfast;get ready
U13.1|can;can't;cannot;Can you
U13.2|Can I;You can;can't
U13.3|should;must;have to;has to
U13.4|don't have to;mustn't;don't need to
U14.1|please;don't;look at;help
U14.2|Can you;Could you;help me
U14.3|I'd like;I'd like to;would like;would like to;Would you like
U14.4|Let's;How about;reading
U15.1|bigger;better;worse;more useful;than
U15.2|the best;the most useful
U15.3|too;enough;many;much;a little;a few;little;few
U15.4|price;useful;better;prefer
U15.5|as;not as;less;fewer
U16.1|price;How much;I'd like;pay for;lunch
U16.2|Where is;go straight;turn left;turn right;by bus
U16.3|meet;time;at seven;on Monday
U16.4|feel;tired;help;should;problem
U17.1|am;is;are;drinking;reading;learning
U17.2|What are you doing;are not;am not
U17.3|I read;I'm reading;know;like;now;every day
U17.4|reading;drinking;in;on;under
U18.1|was;were;yesterday
U18.2|worked;read;drank;went;yesterday
U18.3|didn't;did;Did you;was;were
U18.4|used to;be used to;read books;now
U19.1|first;then;after that;finally
U19.2|was;were;reading;was reading
U19.3|when;while;was reading
U19.4|yesterday;first;then;finally
U20.1|be going to;going to;am going to
U20.2|will;won't;Will you
U20.3|I'm meeting;tomorrow;next week
U20.4|plan to;going to;will
U20.5|when;as soon as;until;will
U21.1|have;has;done;been;read
U21.2|already;yet;just
U21.3|Have you ever;ever;never
U21.4|have done;did;yesterday
U22.1|for;for two years;have lived
U22.2|since;since Monday;since 2020
U22.3|How long;for;since;ago
U22.4|have been doing;have been learning
U23.1|because;because of;why
U23.2|to;in order to
U23.3|so;because
U23.4|although;however;but
U24.1|if;will
U24.2|may;might;could
U24.3|unless;as long as;if not
U24.4|might;if;may
U24.5|must;might;cannot;might have;should have
U25.1|I think;I know;that
U25.2|whether;if;I don't know
U25.3|where;how;what;I know where
U25.4|I wonder;I wonder if
U26.1|who;that
U26.2|which;that
U26.3|where;whose
U26.4|who;which;that
U27.1|is made;by;make
U27.2|is made;was designed;by
U27.3|can be;should be;must be
U27.4|is made;was made;first;then
U28.1|had done;had left;before
U28.2|said;told;that
U28.3|asked if;asked what
U28.4|said;heard;before;after
U29.1|agree;agree with;disagree;partly agree
U29.2|reason;example;because;for example
U29.3|It seems;evidence suggests;evidence
U29.4|however;although;advantage;limit
U29.5|is it;did you;isn't it
U30.1|remember;recall;realize;remember doing;remember to
U30.2|if;would;were
U30.3|if;had done;would have;could have;might have
U30.4|Why do I;What matters to me;value
U31.1|point;reason;example
U31.2|this;it;they;however
U31.3|please;Could you;formal
U31.4|problem;plan;because;limit
U31.5|practical;practice;useful;useless;informal
U32.1|Please say that again.;Could you speak more slowly;Do you mean
U32.2|kind of;used for;for example
U32.3|Do you mean;What about;agree
U32.4|problem;plan;because;however
U32.5|main point;according to;in other words
'''
ANCHORS={line.split('|')[0]:line.split('|')[1].split(';') for line in ANCHORS_TEXT.strip().splitlines()}

# A manually scoped relationship: never treat a whole legacy group as full coverage.
LEGACY_BINDINGS='''
drink-water|U02.1-G01 U02.1-G02 U02.1-G03 U02.1-G04
eat-a-meal|U02.1-G01 U02.1-G02 U02.1-G03 U02.1-G04
read-books|U02.2-G01 U02.2-G02 U02.2-G03 U02.2-G04
learn-english|U02.2-G01 U02.2-G02 U02.2-G04
go-home|U02.3-G01 U02.3-G02 U02.3-G04 U07.4-G04
go-to-school|U02.3-G01 U02.3-G03 U02.3-G04 U07.4-G03
route-i-am|U01.2-G01 U01.2-G02 U01.2-G03 U01.2-G04 U06.2-G03 U06.2-G04
want-to|U09.2-G01 U09.2-G02 U09.2-G03 U09.2-G04 U09.2-G05
need-to|U09.3-G02 U09.3-G03 U09.3-G04 U09.3-G05 U09.4-G01 U09.4-G03
hope-to|U11.1-G02 U11.1-G03 U11.1-G04
plan-to|U11.1-G01 U11.1-G03 U11.1-G04 U11.1-G05
decide-to|U11.2-G01 U11.2-G02 U11.2-G03 U11.2-G04 U11.2-G05
route-would-like-to|U14.3-G01 U14.3-G02 U14.3-G03 U14.3-G04 U14.3-G05
like-doing|U10.2-G01 U10.2-G02 U10.2-G03 U10.2-G04 U10.2-G05
enjoy-doing|U10.3-G01 U10.3-G02 U10.3-G03 U10.3-G04 U10.3-G05
learn-to|U11.3-G02 U11.3-G03 U11.3-G04 U11.3-G05
try-to|U11.3-G01 U11.3-G05
practice-doing|U11.4-G01 U11.4-G04 U11.4-G05
keep-doing|U11.4-G02 U11.4-G04 U11.4-G05
finish-doing|U11.4-G03 U11.4-G04 U11.4-G05
listen-to|U12.1-G01 U12.1-G04 U12.1-G05
look-at|U12.1-G02 U12.1-G04 U12.1-G05 U12.4-G02
wait-for|U12.2-G01 U12.2-G03 U12.2-G04 U12.2-G05
talk-to|U12.3-G01 U12.3-G04 U12.3-G05
ask-for|U12.3-G02 U12.3-G03 U12.3-G04 U12.3-G05
look-for|U12.2-G02 U12.2-G03 U12.2-G04 U12.2-G05 U12.4-G02
look-after|U12.4-G01 U12.4-G02 U12.4-G03 U12.4-G04
route-good-at|U10.5-G01 U10.5-G04 U10.5-G05
route-afraid-of|U10.5-G03 U10.5-G04 U10.5-G05
agree-with|U29.1-G01 U29.1-G03 U29.1-G04
every-day|U08.2-G01 U08.2-G05
route-in-the-morning|U08.1-G04 U08.1-G05
route-at-night|U08.1-G04 U08.1-G05
route-on-weekends|U08.2-G01
route-at-home|U07.4-G01 U07.4-G03 U07.4-G05
route-in-front-of|U07.2-G02 U07.2-G04
route-next-to|U07.2-G01 U07.2-G04 U07.2-G05
route-a-lot-of|U05.5-G06
route-because-of|U23.1-G02 U23.1-G03 U23.1-G05
route-going-to|U20.1-G01 U20.1-G02 U20.1-G03 U20.1-G04 U20.1-G05
route-used-to|U18.4-G01 U18.4-G02 U18.4-G03 U18.4-G04 U18.4-G05
'''
SUPPORT_BINDINGS={
 'get-up':(['U02.4-G03','U08.2-G01'],'日常动作示例，不直接覆盖频率规则'),
 'cook-at-home':(['U02.4-G03','U07.4-G01'],'动作与地点材料，不代表已教完整位置规则'),
 'pay-for':(['U16.1-G01','U16.1-G05'],'购买/付款情境材料，不代表完整购物对话'),
 'belong-to':(['U03.5-G01'],'归属表达对照，不等于mine/yours已教'),
 'route-after-work':(['U08.1-G05'],'时段材料，不代表完整时间规则'),
 'route-before-dinner':(['U08.1-G05'],'时段材料，不代表完整时间规则'),
}

LESSON_BINDINGS={
 'meaning':['U09.2-G02'], 'object':['U09.1-G01','U09.1-G02','U09.1-G03'],
 'collocation':['U09.2-G01'], 'phrase':['U09.2-G01','U09.2-G02'],
 'sentence':['U02.4-G01','U09.2-G02'], 'transfer':['U09.2-G03']}

def norm(value):
    return ' '.join(value.casefold().replace('’',"'").strip().rstrip('.!?。！？').split())

def static_value(node):
    """Only literal containers and dict(keyword=literal); never eval/exec/import."""
    if isinstance(node,ast.Constant):return node.value
    if isinstance(node,(ast.List,ast.Tuple,ast.Set)):
        values=[static_value(x) for x in node.elts]
        return tuple(values) if isinstance(node,ast.Tuple) else values
    if isinstance(node,ast.Dict):return {static_value(k):static_value(v) for k,v in zip(node.keys,node.values)}
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='dict' and not node.args:
        if any(k.arg is None for k in node.keywords):raise ValueError('dict unpack not permitted')
        return {k.arg:static_value(k.value) for k in node.keywords}
    raise ValueError(f'Nonliteral node {type(node).__name__}')

def constants(path,names,function=None):
    found={}; tree=ast.parse(path.read_text(encoding='utf-8'))
    body=tree.body if function is None else next(n.body for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==function)
    for node in body:
        if isinstance(node,ast.Assign):
            for t in node.targets:
                if isinstance(t,ast.Name) and t.id in names:
                    found[t.id]={'value':static_value(node.value),'line':node.lineno}
    return found

def inventory(output):
    inputs=[
      '项目说明/课程设计/通用主线目标清单.json','项目说明/课程设计/课程路线v4.json',
      'backend/resources/compiled_courses.json','backend/resources/teaching_routes.json',
      'backend/resources/transfer_practice.psv','backend/resources/sourced_transfer_pilot.json',
      'backend/resources/composition_rules.json','backend/content.py','backend/beginner_notes.py','backend/lesson.py','backend/transfer.py','backend/curriculum_engine.py',
      'backend/resources/starter_course.json','backend/starter_course.py',
      'backend/resources/mainline_course.json','backend/resources/mainline_lessons.psv',
      'backend/resources/mainline_word_notes.json','scripts/build_mainline_course.py']
    snapshots=[{'path':s,'sha256':hashlib.sha256((ROOT/s).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
                'normalization':'CRLF_to_LF'} for s in inputs]
    design=json.loads((ROOT/inputs[0]).read_text(encoding='utf-8'))
    route=json.loads((ROOT/inputs[1]).read_text(encoding='utf-8'))
    assert design['version']=='design-v4'
    topic_map={t['id']:t for t in design['topics']}
    goal_map={g['id']:(t,g) for t in design['topics'] for g in t['goals']}
    assert len(topic_map)==148 and len(goal_map)==729 and set(topic_map)==set(ANCHORS)
    placements={r['objective_id']:r for r in route['objective_placement']}
    assert set(placements)==set(goal_map)
    pack=json.loads((ROOT/inputs[2]).read_text(encoding='utf-8'))
    old_manifest=json.loads((ROOT/inputs[3]).read_text(encoding='utf-8'))
    legacy={g['key']:g for g in old_manifest['goals']}
    composition=json.loads((ROOT/inputs[6]).read_text(encoding='utf-8'))
    pilot=json.loads((ROOT/inputs[5]).read_text(encoding='utf-8'))
    content=constants(ROOT/'backend/content.py',{'WORDS','STRUCTURES'})
    beginner=constants(ROOT/'backend/beginner_notes.py',{'MATERIALS','FAMILIES'})
    lesson=constants(ROOT/'backend/lesson.py',{'STEPS','RULES'})
    starter=json.loads((ROOT/'backend/resources/starter_course.json').read_text(encoding='utf-8'))
    transfer_materials=constants(ROOT/'backend/transfer.py',{'materials'},function='install')['materials']
    assets={}; term_index=defaultdict(list); obj_refs=defaultdict(lambda:defaultdict(list))

    def asset(aid,kind,path,payload,**extra):
        record={'id':aid,'kind':kind,'source_path':path,'payload':payload,
                'review_for_new_course':'pending','not_proof_of_user_mastery':True,**extra}
        if aid in assets:assert assets[aid]==record,aid
        assets[aid]=record
        return aid

    # Packaged lexical and expression resources only. No real/live knowledge DB query.
    for kind,key in [('word','words'),('collocation','expressions')]:
        for x in pack[key]:
            aid='pack:'+x['id']
            # Keep only a lookup catalogue in memory; export referenced records later.
            asset(aid,kind,'backend/resources/compiled_courses.json',
                {'source_record_id':x['id'],'english':x['answer'],'chinese':x['prompt'],
                 'explanation':x['explanation'],'details':{k:x['details'].get(k) for k in
                    ['pos','ipa_us','syllables','structure','knowledge_points','usage','sources','review_status']}})
            term_index[norm(x['answer'])].append(aid)
    words=content['WORDS']['value']
    for kid,x in words.items():
        en={'word-i':'I','word-english':'English','eat-a-meal':'eat'}.get(kid,kid.removeprefix('word-'))
        aid=asset('content:word:'+kid,'original_word_note','backend/content.py',
                  {'candidate_knowledge_id':kid,'english':en,**x},source_line=content['WORDS']['line'])
        term_index[norm(en)].insert(0,aid)
    for kid,(zh,en,usage) in transfer_materials['value'].items():
        aid=asset('seedmaterial:'+kid,'original_material_note','backend/transfer.py',
                  {'candidate_knowledge_id':kid,'english':en,'chinese':zh,'usage':usage},source_line=transfer_materials['line'])
        term_index[norm(en)].insert(0,aid)

    bindings={k:v.split() for k,v in (line.split('|') for line in LEGACY_BINDINGS.strip().splitlines())}
    assert all(k in legacy for k in bindings)
    assert all(gid in goal_map for xs in bindings.values() for gid in xs)
    assert all(k in legacy and all(gid in goal_map for gid in v[0]) for k,v in SUPPORT_BINDINGS.items())
    group_assets=defaultdict(lambda:defaultdict(list))
    for key,g in legacy.items():
        aid=asset('legacy:'+key,'legacy_teaching_group','backend/resources/teaching_routes.json',g,
                  scope='Existing authored group, not a completed new-design objective')
        group_assets[key]['teaching'].append(aid)
        term_index[norm(g['english'])].insert(0,aid)
        for i,m in enumerate(g.get('materials',[])):
            mid=asset(f'legacy:{key}:material:{i}','legacy_material_declaration','backend/resources/teaching_routes.json',m)
            term_index[norm(m['en'])].append(mid)
        example=asset('legacy:'+key+':example','authored_demonstration','backend/resources/teaching_routes.json',
            {'english':g['sentence'],'chinese':g['sentence_zh'],'original_goal':key,
             'exposure_role':'demonstration_not_independent_transfer'})
        group_assets[key]['demonstration'].append(example)
        pairs=[('core',g['english'],g['chinese']),('phrase',g.get('phrase'),g.get('phrase_zh')),
               ('sentence',g['sentence'],g['sentence_zh'])]
        for role,en,zh in pairs:
            if not en or not zh:continue
            aid=asset(f'legacy:{key}:recall:{role}','declared_recall_card_pair','backend/resources/teaching_routes.json',
                {'original_goal':key,'role':role,'english':en,'chinese':zh,
                 'implementation_reference':'backend/curriculum_engine.py:publish/card/member',
                 'warning':'从原课程卡片字段提取的回忆素材，不代表新目标完整题目已经编写或审核'})
            group_assets[key]['controlled_question'].append(aid)
        for symbol,source in [('STRUCTURES',content),('FAMILIES',beginner),('MATERIALS',beginner)]:
            value=source.get(symbol,{}).get('value',{})
            if key in value:
                path='backend/content.py' if source is content else 'backend/beginner_notes.py'
                a=asset(f'note:{symbol}:{key}','original_usage_note',path,value[key],source_line=source[symbol]['line'])
                group_assets[key]['teaching'].append(a)

    psv_rows=[]
    for n,line in enumerate((ROOT/'backend/resources/transfer_practice.psv').read_text(encoding='utf-8').splitlines(),1):
        if not line.strip() or line.startswith('#'):continue
        fields=line.split('|');assert len(fields)==4,(n,line)
        key,en,zh,required=fields;assert key in legacy
        req=[v.strip() for v in required.split(',') if v.strip()]
        assert all(v in legacy or v in transfer_materials['value'] or (v.startswith('material:') and len(v)>9) for v in req),req
        a=asset(f'psv:{n}','legacy_context_exercise','backend/resources/transfer_practice.psv',
            {'original_goal':key,'english':en,'chinese':zh,'declared_requirements':req,
             'requirements_note':'旧目标级依赖不是完整词义/语法依赖；新目标适配、曝光与答案变体待核对'},source_line=n)
        group_assets[key]['context'].append(a);psv_rows.append(a)
    for i,row in enumerate(pilot['rows']):
        assert row['source']['en']==row['english'] and row['review']['status']=='approved'
        a=asset('pilot:'+row['source_id'],'source_backed_pilot_question','backend/resources/sourced_transfer_pilot.json',row,
            review_scope='已有want-to试点的AI辅助核对；未验证适配新729目标，非教师/官方审定')
        group_assets[row['goal']]['context'].append(a)
    for step in lesson['STEPS']['value']:
        aid=asset('lesson:'+step['id'],'legacy_choice_or_write_question','backend/lesson.py',step,
            source_line=lesson['STEPS']['line'],exposure_check_required=True)
        for gid in LESSON_BINDINGS[step['id']]:obj_refs[gid]['controlled_question'].append(aid)
        if step['kind']=='choice':
            for gid in LESSON_BINDINGS[step['id']]:obj_refs[gid]['choice_only_not_recall'].append(aid)
    asset('lesson:RULES','original_lesson_explanation','backend/lesson.py',lesson['RULES']['value'],
          source_line=lesson['RULES']['line'])
    for gid in ['U09.1-G01','U09.2-G01','U09.2-G02']:
        obj_refs[gid]['teaching'].append('lesson:RULES')
    for key,gids in bindings.items():
        for gid in gids:
            for role,refs in group_assets[key].items():obj_refs[gid][role].extend(refs)
            obj_refs[gid]['legacy_goal'].append(key)
    for key,(gids,reason) in SUPPORT_BINDINGS.items():
        for gid in gids:
            obj_refs[gid]['support_only'].extend(group_assets[key]['teaching'])
            obj_refs[gid]['support_reason'].append(reason)
    for g in starter['goals']:
        aid=asset('starter:'+g['key'],'authored_test_preview_slice','backend/resources/starter_course.json',g,
            execution_status='implemented_in_independent_test_mode',
            coverage_scope='起步片段，非所关联完整学生目标全部完成',
            review_method=starter['review']['method'])
        for gid in starter['mapped_objectives'][g['key']]:
            assert gid in goal_map
            obj_refs[gid]['starter_preview_component'].append(aid)

    mainline=json.loads((ROOT/'backend/resources/mainline_course.json').read_text(encoding='utf-8'))
    for g in mainline['goals']:
        aid=asset('mainline:'+g['key'],'authored_topic_core_test_course','backend/resources/mainline_course.json',g,
            execution_status='implemented_in_independent_test_mode',
            coverage_scope='课题核心文字训练；不代表所关联目标所有听说、开放表达标准已完成',
            review_method=mainline['review']['method'])
        for gid in mainline['mapped_objectives'][g['key']]:
            assert gid in goal_map
            obj_refs[gid]['mainline_core_component'].append(aid)

    # Exact phrase retrieval is just corpus discovery, not semantic/teaching approval.
    # Deliberately avoid claiming that a generic 'I', 'to', or 'that' hit covers grammar.
    sentence_index={s['id']:s for s in pack['sentences']}
    searchable=[(s,norm(s['answer'])) for s in pack['sentences']]
    phrase_cache={}
    def phrase_candidates(term):
        nk=norm(term)
        if nk in phrase_cache:return phrase_cache[nk]
        if len(nk.split())<2 or len(nk)<6:
            phrase_cache[nk]=[];return []
        pat=re.compile(r'(?<![a-z])'+re.escape(nk)+r'(?![a-z])')
        hits=[]
        for x,english in searchable:
            if not pat.search(english):continue
            examples=x['details'].get('examples',[])
            source=next((e for e in examples if e.get('en')==x['answer'] and e.get('source_url') and e.get('translation_url') and e.get('license')),None)
            if source:hits.append((len(x['answer'].split()),len(x['answer']),x,source))
        hits.sort(key=lambda h:(h[0],h[1],h[2]['id']))
        result=[]
        for _,__,x,source in hits[:3]:
            result.append(asset('sentence:'+x['id'],'corpus_phrase_hit_only','backend/resources/compiled_courses.json',
                 {'source_record_id':x['id'],'english':x['answer'],'chinese':x['prompt'],'source':source,
                  'lexical_dependency_ids':x['word_keys'],'match_warning':'仅文字包含，不代表用法、难度或新情境适合'}))
        phrase_cache[nk]=result;return result

    graph_by_goal=defaultdict(list)
    capabilities={n['id']:n for n in route['critical_starter_capabilities']}
    for n in capabilities.values():
        for gid in n['objective_ids']:graph_by_goal[gid].append(n['id'])

    def task_design(t,g):
        text=g['objective'];tid=t['id'];unit=t['unit_id']
        if any(s in text for s in ['听懂','听辨','听到','听问题','语调']):
            return ('listening_or_sound','先提供适合当前水平的音频刺激；不把播放能力当作已配置听力题',
                    '不看英文，听后辨认含义或作对应回应；目标与答案需另外编写','skill_task_not_bound')
        if tid in ['U31.1','U31.3','U31.4','U29.2','U29.3','U29.4','U30.4','U28.4','U32.5']:
            return ('open_expression','先用短材料说明信息组织，再给新任务，不预设只有唯一措辞',
                    '按内容要点、结构和表达分别评估；不能直接套定长拼写','open_assessment_not_implemented')
        if unit=='U16' or tid in ['U04.4','U14.2','U14.4','U32.1','U32.3','U32.4']:
            return ('interaction','给明确角色与交际目的，先教必要材料，再安排有回应的交流',
                    '区分写出一句话与真正接住对方回应；对话脚本和接受范围待编','interaction_task_not_bound')
        if tid=='U31.5':
            return ('lexical_reference','先核对当前词的意义、词性、词族和依据，不从字形自动编词源',
                    '用新语境检验选义和适用性，不把记住词根当掌握该词','reference_task_not_bound')
        if any(s in text for s in ['区分','区别','对照','比较','避免']):
            return ('meaning_or_form_contrast','以同一情境比较具体用法，先用白话说明意义或结构差别',
                    '撤去对照答案后独立组织或判断理由，再用新情境验证；选择题不单独证明掌握','controlled_blocks_exist_new_binding_pending')
        return ('controlled_expression','先教本目标必要材料和一个清楚用法；示范与测试分开',
                '无提示书写后在材料已会且整句未曝光的新语境运用；具体题目及合理变体待配置','controlled_blocks_exist_new_binding_pending')

    rows=[];used_assets=set();anchor_terms=set()
    for t in design['topics']:
        for g in t['goals']:
            gid=g['id'];refs={k:list(dict.fromkeys(v)) for k,v in obj_refs[gid].items()}
            exact=[term for term in ANCHORS[t['id']] if re.search(r'(?<![a-z])'+re.escape(norm(term))+r'(?![a-z])',norm(g['objective']))]
            anchors=exact if exact else ANCHORS[t['id']]
            # A he/wants goal must not get an I/want card merely because it is in
            # the same old family. This filter is lexical only, never a suitability approval.
            if exact:
                refs['controlled_question']=[aid for aid in refs.get('controlled_question',[])
                    if assets[aid]['kind']!='declared_recall_card_pair' or any(
                        re.search(r'(?<![a-z])'+re.escape(norm(term))+r'(?![a-z])',norm(assets[aid]['payload']['english']))
                        for term in exact)]
            materials=[]
            for term in anchors:
                anchor_terms.add(norm(term));candidates=list(dict.fromkeys(term_index.get(norm(term),[])))[:8]
                materials.append({'term':term,'scope':'explicit_objective_anchor' if exact else 'topic_context_seed_not_exhaustive',
                                  'candidate_asset_ids':candidates,'sense_and_role_binding':'pending'})
                used_assets.update(candidates)
            for role,values in refs.items():
                if role not in ['legacy_goal','support_reason']:used_assets.update(values)
            corpus=[]
            for term in anchors:
                corpus.extend(phrase_candidates(term))
                if len(set(corpus))>=3:break
            corpus=list(dict.fromkeys(corpus))[:3];used_assets.update(corpus)
            node_ids=graph_by_goal[gid]
            prereq=[]
            for nid in node_ids:
                prereq.append({'capability_id':nid,'capability_name':capabilities[nid]['name'],
                               'requires_capability_ids':capabilities[nid]['requires'],
                               'lexical_and_question_bindings':'pending'})
            kind,teach,practice,runtime=task_design(t,g)
            question_refs=[a for a in refs.get('controlled_question',[]) if a not in refs.get('choice_only_not_recall',[])]
            teaching_refs=refs.get('teaching',[])
            gaps=['K02','P02' if prereq else 'P01','Q02' if question_refs else 'Q01','V01','B01']
            if not teaching_refs:gaps.append('E01')
            else:gaps.append('E02')
            if not any(m['candidate_asset_ids'] for m in materials):gaps.append('K01')
            if refs.get('context') or corpus:gaps.append('T02')
            else:gaps.append('T01')
            if kind in ['listening_or_sound','interaction','open_expression','lexical_reference']:gaps.append('S01')
            row={'objective_id':gid,'topic_id':t['id'],'topic_title':t['title'],'objective':g['objective'],
                'route_window':placements[gid]['first_window'],'route_note':placements[gid]['note'],
                'coverage_status':'topic_core_test_course_partial_objective' if refs.get('mainline_core_component') else 'partial_test_preview_slice' if refs.get('starter_preview_component') else 'draft_components_only_not_ready',
                'materials':materials,'materials_manifest_complete':False,
                'existing_components':refs,'corpus_candidates':corpus,
                'prerequisites':{'status':'critical_graph_partial' if prereq else 'not_mapped',
                    'capability_components':prereq,
                    'support_topics':t.get('recommended_support_topics',[]),
                    'support_units':design['recommended_support_units'].get(t['unit_id'],[]),
                    'warning':'导航不是整章硬先修；关键图也未完成全部词义及任务依赖'},
                'teaching_plan':{'status':'authoring_blueprint_only','suggested_action':teach,
                    'existing_explanation_refs':teaching_refs},
                'practice_plan':{'recommended_type':kind,'status':'not_assembled_or_audited',
                    'suggested_verification':practice,'existing_nonchoice_question_refs':question_refs},
                'transfer_plan':{'status':'candidate_or_gap_not_published',
                    'legacy_candidate_refs':refs.get('context',[]),'corpus_hit_refs':corpus,
                    'required_checks':['目标用法与具体词义','自然度与中文','学习者已会的材料',
                                       '整句曝光与示范去重','接受答案及题型能力'],
                    'note':'不是每条目标都必须五句；听力/对话/段落需相应任务，不能一律用翻译题替代'},
                'review_plan':{'status':'legacy_references_only_new_binding_pending',
                    'legacy_group_refs':refs.get('legacy_goal',[]),
                    'policy':'回忆表现与反馈进入既有复习；不凭本表生成新FSRS状态或假掌握记录'},
                'runtime_binding':{'status':'topic_core_available_in_test_mode' if refs.get('mainline_core_component') else 'partial_slice_available_in_test_mode' if refs.get('starter_preview_component') else runtime,
                    'preview_slice_refs':refs.get('starter_preview_component',[])+refs.get('mainline_core_component',[]),'published_for_this_objective':False},
                'content_review':'pending_for_new_objective','answer_variants_status':'not_bound',
                'gaps':list(dict.fromkeys(gaps))}
            rows.append(row)

    gap_legend={
      'K01':'当前代表材料词未找到精确词条候选；不是证明整个词典不存在此词',
      'K02':'完整必要材料/词义清单尚未绑定；词条有命中也不消除此缺口',
      'P01':'目标级硬先修尚未映射','P02':'有关键能力图组件，但词义/材料及内部依赖仍待补',
      'E01':'未建立对应的旧教学讲解关联','E02':'有讲解组件，但未组装审校成此目标的教学内容',
      'Q01':'未关联到明确可复用的非选择题练习','Q02':'有旧非选择题候选，目标适配与曝光等待审',
      'T01':'本轮未找到新情境候选，须设计相应任务或调整检索',
      'T02':'有旧情境或文字匹配候选，尚未确认适合当前目标及学习者',
      'V01':'此目标合理答案变体或开放评价标准未配置',
      'S01':'相应听力/互动/开放表达/查词任务未绑定；通用拼写不能替代',
      'B01':'新目录目标未导入运行课程，不可直接标ready'}
    assert len(rows)==729 and len({r['objective_id'] for r in rows})==729
    assert used_assets<=set(assets),used_assets-set(assets)
    assert all(r['coverage_status'] in ('draft_components_only_not_ready','partial_test_preview_slice','topic_core_test_course_partial_objective') for r in rows)
    assert len(POLICY_SET:={x['origin_goal_id'] for x in design['quality_constraints']})==6
    assert not (POLICY_SET & {r['objective_id'] for r in rows})
    assert set(capabilities)=={ref for r in rows for comp in r['prerequisites']['capability_components'] for ref in [comp['capability_id']]}
    phase=Counter(r['route_window'] for r in rows)
    mapped=set(bindings)|set(SUPPORT_BINDINGS)
    remaining=[{'key':k,'english':g['english'],'reason':'未强行关联；需要在对应词义/领域材料中明确安置'}
               for k,g in legacy.items() if k not in mapped]
    summary={
      'scope':'packaged_static_resources_only_no_live_or_private_DB', 'design_version':design['version'],
      'objectives':len(rows),'topics':len(topic_map),'route_windows':dict(sorted(phase.items())),
      'lexical_resources':len(pack['words']),'expression_resources':len(pack['expressions']),
      'source_sentences':len(pack['sentences']),'legacy_groups':len(legacy),'legacy_psv_questions':len(psv_rows),
      'intro_lesson_steps':len(lesson['STEPS']['value']),'pilot_reviewed_sentences':len(pilot['rows']),
      'dynamic_rule_frames':len(composition['frames']),
      'dynamic_rule_warning':'只清点规则数量，不展开生成句子，也不把组合数当已审核课程',
      'objectives_with_scoped_legacy_teaching_components':sum(bool(r['existing_components'].get('teaching')) for r in rows),
      'objectives_with_nonchoice_question_candidates':sum(bool(r['practice_plan']['existing_nonchoice_question_refs']) for r in rows),
      'objectives_with_critical_capability_graph_components':sum(bool(r['prerequisites']['capability_components']) for r in rows),
      'objectives_with_lexical_anchor_hits':sum(any(m['candidate_asset_ids'] for m in r['materials']) for r in rows),
      'objectives_with_context_or_corpus_candidates':sum(bool(r['existing_components'].get('context') or r['corpus_candidates']) for r in rows),
      'exact_material_terms_checked':len(anchor_terms),'exported_referenced_assets':len(used_assets),
      'new_objectives_ready':0,'new_objectives_published':0,'legacy_unplaced':remaining,
      'test_preview_groups':len(starter['goals']),
      'test_preview_transfer_questions':sum(len(g.get('variants',[])) for g in starter['goals']),
      'objectives_with_partial_test_preview_slice':sum(bool(r['existing_components'].get('starter_preview_component')) for r in rows),
      'mainline_core_topics':len(mainline['goals']),
      'mainline_context_questions':sum(len(g.get('variants',[])) for g in mainline['goals']),
      'objectives_linked_to_topic_core':sum(bool(r['existing_components'].get('mainline_core_component')) for r in rows),
      'gaps':dict(Counter(code for r in rows for code in r['gaps'])),
      'warning':'有组件/有词条/有例句均不等于目标已经具备完整教学与评估；未评价实际学习效果',
      'writes':'reports_only_no_runtime_or_real_data_mutations'}
    assert 0<summary['objectives_with_scoped_legacy_teaching_components']<len(rows)

    # Observations are locatable static evidence, not a claim to have audited every source item.
    issues=[
      {'id':'SRC01','source':'backend/resources/compiled_courses.json','record_id':'expr-1d03bdc1e001f187',
       'finding':'going to条目混合将来意图和实际去向例句，自动知识点包含进行体解释，不能直接作为going-to将来课程讲解',
       'action':'拆分语义/用法并审校，不能仅凭文字命中发布'},
      {'id':'SRC02','source':'backend/resources/compiled_courses.json','record_id':'lex-b9776d7ddf459c9a',
       'finding':'the的中文为“art. 那”，英文定义混入Thee旧义及其他用法，不能当初学者定冠词完整讲解',
       'action':'使用有语境的定冠词讲解；原词典条目只作待核对资料'},
      {'id':'SRC03','source':'backend/resources/teaching_routes.json','record_id':'route-used-to',
       'finding':'旧先修只有every-day与plan-to，不能替代新课程对过去习惯及相应用法的能力准备',
       'action':'旧依赖保留作历史信息，不自动复制为新目标硬先修'},
      {'id':'SRC04','source':'backend/resources/teaching_routes.json','record_id':'decide-to',
       'finding':'旧示范I decide to learn English需要具体自然语境；不能把它当过去决定的替代',
       'action':'按v4路线在过去动作具备后编自然的决定情境'}]
    for issue in issues[:2]:
        records=pack['expressions'] if issue['record_id'].startswith('expr') else pack['words']
        assert any(x['id']==issue['record_id'] for x in records)
    expression=next(x for x in pack['expressions'] if x['id']==issues[0]['record_id'])
    article=next(x for x in pack['words'] if x['id']==issues[1]['record_id'])
    issue_conditions={
      'SRC01':expression['answer']=='going to' and any('进行体' in x for x in expression['details'].get('knowledge_points',[])),
      'SRC02':article['prompt']=='art. 那' and 'Thee' in article['details'].get('definition_en',''),
      'SRC03':legacy['route-used-to']['requires']==['every-day','plan-to'],
      'SRC04':legacy['decide-to']['sentence']=='I decide to learn English.'}
    issues=[x for x in issues if issue_conditions[x['id']]]

    output.mkdir(parents=True,exist_ok=True)
    (output/'覆盖清单.json').write_text(json.dumps({'version':'coverage-v1','scope':summary['scope'],
        'inputs':snapshots,'gap_legend':gap_legend,'objectives':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'资源引用目录.json').write_text(json.dumps({'version':'coverage-v1','resources':[assets[k] for k in sorted(used_assets)]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'汇总.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'资料质量与映射问题.json').write_text(json.dumps(issues,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    def esc(text):return str(text).replace('|','／').replace('\n',' ')
    lines=['# 课程覆盖总表','',
      '**仅静态资料盘点，不是课程发布清单。** 候选材料不等于词义已绑定、题目合适或学习者已会。',
      '','| 指标 | 数量 |','|---|---:|']
    for name,key in [('目标','objectives'),('课题','topics'),('有旧讲解组件关联的目标','objectives_with_scoped_legacy_teaching_components'),
                     ('已实现核心书写训练的主线课题（独立试学）','mainline_core_topics'),
                     ('主线情境题（不保证每条均为首次新组合）','mainline_context_questions'),
                     ('有明确非选择题候选的目标','objectives_with_nonchoice_question_candidates'),
                     ('有关键能力图组件的目标','objectives_with_critical_capability_graph_components'),
                     ('本轮确认可发布的新目标','new_objectives_ready')]:lines.append(f'| {name} | {summary[key]} |')
    lines+=['',f"完整主线试学：{summary['mainline_core_topics']}课题、{summary['mainline_context_questions']}情境题，关联全部{summary['objectives_linked_to_topic_core']}条目标的课题核心训练。听说和开放任务仍需各自证据，不据此认证完整729条能力。入口：设置→独立测试模式→清空测试进度→启用完整主线试学。",'',
      f"原起步试学仍保留{summary['test_preview_groups']}组、{summary['test_preview_transfer_questions']}道题的较小测试范围。",'',
      '词条和语料命中不计“完成覆盖率”。本轮输入含旧50组、基础讲解、6个入门题步骤、固定情境题和5条有来源试点；未展开动态组合，也未读取本地/线上真实学习数据库。',
      '', '## 重要资料问题','']
    for issue in issues:lines.append(f"- **{issue['id']} {issue['record_id']}**：{issue['finding']}。{issue['action']}。")
    lines+=['','## 缺口代码','']+[f'- **{code}**：{description}。' for code,description in gap_legend.items()]
    lines+=['','## 729条逐目标清单','',
      '每行的“材料”只是代表性种子，不是完整先修。讲解/语境表示来源组件数，0表示本轮未建立关联，不等于世界上没有资料。具体原文、来源及角色见JSON。','']
    for rid in sorted(phase):
        lines+=['',f'### {rid}（{phase[rid]}条目标）','',
          '| 目标ID | 要学会什么 | 代表材料 | 讲解组件 | 非选择题候选 | 旧语境/原句候选 | 先修 | 缺口 |',
          '|---|---|---|---:|---:|---:|---|---|']
        for row in (x for x in rows if x['route_window']==rid):
            refs=row['existing_components'];preview='、'.join(m['term'] for m in row['materials'][:4])
            lines.append('| '+' | '.join(map(esc,[row['objective_id'],row['objective'],preview,
              len(refs.get('teaching',[])),len(row['practice_plan']['existing_nonchoice_question_refs']),
              len(refs.get('context',[]))+len(row['corpus_candidates']),
              '关键图部分已有' if row['prerequisites']['capability_components'] else '待映射',' '.join(row['gaps'])]))+' |')
    lines+=['','## 尚未安置的旧目标','']
    for x in remaining:lines.append(f"- `{x['key']}` {x['english']}：{x['reason']}。")
    lines+=['','## 使用方式','',
      '1. 先看R01待办与目标关联的原始资源；逐条挑选可复用片段，不能把整组内容复制后标ready。',
      '2. 为准备发布的目标补完整词义/材料、硬先修、讲解和实际题目；不能用本表代表词代替完整材料清单。',
      '3. 合理答案、曝光、迁移、听说等按题型分别验证；原先5条试点审核不等于新目标也已通过。',
      '4. 覆盖JSON引用的所有资产均在资源引用目录，保留源路径与原ID；源ID不是本轮新建的运行知识ID。',
      '5. 本表全部是草稿组件盘点，0个新目标可发布；原来的运行课程没有被禁用或清空。']
    (output/'覆盖总表.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

    first=[x for x in rows if x['route_window']=='R01']
    todo=['# R01编课待办','',f'共有{len(first)}条目标处于R01引入窗口。这不是要求一次学完；按关键能力小段推进。',
          '','## 先做的关键路径','']
    for nid in route['capability_topological_order']:
        n=capabilities[nid]
        if all(placements[gid]['first_window']=='R01' for gid in n['objective_ids']):
            todo.append(f"- **{nid} {n['name']}**：目标 {'、'.join(n['objective_ids'])}；前置能力 {'、'.join(n['requires']) or '起步材料待确认'}。")
    todo+=['','## 逐目标的组件与待办','']
    for row in first:
        refs=row['existing_components'];gid=row['objective_id']
        todo.extend([f"### {gid} {row['objective']}",'',
          '- 代表材料：'+'、'.join(m['term'] for m in row['materials'])+'（仍需补全词义和范围）。',
          '- 已有关联讲解：'+('、'.join(refs.get('teaching',[])) or '本轮未建立对应关联')+'。',
          '- 已有非选择题候选：'+('、'.join(row['practice_plan']['existing_nonchoice_question_refs']) or '待编写或继续查找')+'。',
          '- 已实现的独立试学片段：'+('、'.join(refs.get('starter_preview_component',[])) or '尚无')+'；不等于本目标所有能力均已完成。',
          '- 主线课题核心训练：'+('、'.join(refs.get('mainline_core_component',[])) or '尚无')+'；完整目标仍需对应能力证据。',
          '- 关键能力：'+('、'.join(x['capability_id'] for x in row['prerequisites']['capability_components']) or '尚未映射')+'。',
          '- 教学草案：'+row['teaching_plan']['suggested_action']+'。',
          '- 验证草案：'+row['practice_plan']['suggested_verification']+'。',
          '- 待办：'+'；'.join(gap_legend[c] for c in row['gaps'])+'。',''])
    (output/'R01-编课待办.md').write_text('\n'.join(todo)+'\n',encoding='utf-8')
    validation={'objective_rows':len(rows),'unique_objective_ids':len({r['objective_id'] for r in rows}),
      'all_design_goals_present':set(goal_map)=={r['objective_id'] for r in rows},
      'valid_exported_asset_refs':used_assets<=set(assets),'policy_requirements_excluded':not(POLICY_SET&{r['objective_id'] for r in rows}),
      'source_sentence_provenance_checked':True,'all_new_objectives_remain_draft':True,
      'runtime_or_learner_data_tested':False,'real_data_written':False}
    (output/'盘点校验结果.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/curriculum-coverage')
    args=parser.parse_args();inventory(args.output)
