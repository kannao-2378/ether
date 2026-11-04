"""Check coverage export integrity against its actual packaged input snapshot.

Does not import the app, connect to databases, or run the learning algorithm.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'reports/curriculum-coverage'
coverage=json.loads((out/'覆盖清单.json').read_text(encoding='utf-8'))
resources=json.loads((out/'资源引用目录.json').read_text(encoding='utf-8'))
summary=json.loads((out/'汇总.json').read_text(encoding='utf-8'))
design=json.loads((ROOT/'项目说明/课程设计/通用主线目标清单.json').read_text(encoding='utf-8'))
pack=json.loads((ROOT/'backend/resources/compiled_courses.json').read_text(encoding='utf-8'))
original_sentences={x['id']:x for x in pack['sentences']}
rows={r['objective_id']:r for r in coverage['objectives']}
assets={x['id']:x for x in resources['resources']}
assert len(rows)==len(coverage['objectives'])==729
assert set(rows)=={g['id'] for t in design['topics'] for g in t['goals']}
assert len(assets)==len(resources['resources'])
for source in coverage['inputs']:
    raw=(ROOT/source['path']).read_bytes()
    if source.get('normalization')=='CRLF_to_LF':raw=raw.replace(b'\r\n',b'\n')
    assert hashlib.sha256(raw).hexdigest()==source['sha256'],source['path']
for row in rows.values():
    refs=[]
    for m in row['materials']:refs.extend(m['candidate_asset_ids'])
    for role,values in row['existing_components'].items():
        if role not in ['legacy_goal','support_reason']:refs.extend(values)
    refs+=row['corpus_candidates']+row['practice_plan']['existing_nonchoice_question_refs']
    assert set(refs)<=set(assets),row['objective_id']
    assert not row['runtime_binding']['published_for_this_objective']
    assert not row['materials_manifest_complete']
    assert row['content_review']=='pending_for_new_objective'
    for aid in row['practice_plan']['existing_nonchoice_question_refs']:
        assert assets[aid]['payload'].get('kind')!='choice',aid
for resource in assets.values():
    if resource['kind']=='corpus_phrase_hit_only':
        p=resource['payload'];s=original_sentences[p['source_record_id']]
        assert p['english']==s['answer'] and p['chinese']==s['prompt']
        assert p['source'] in s['details']['examples']
        assert all(p['source'].get(k) for k in ['source_url','translation_url','license'])
    if resource['kind']=='source_backed_pilot_question':
        assert resource['payload']['english']==resource['payload']['source']['en']
        assert resource['review_for_new_course']=='pending'
# Critical boundary cases: old data must not silently become new teaching evidence.
assert not rows['U09.2-G04']['practice_plan']['existing_nonchoice_question_refs'] # no wants card in that old family
assert 'lesson:meaning' not in rows['U09.2-G02']['practice_plan']['existing_nonchoice_question_refs']
assert all(rows[x]['prerequisites']['status']=='not_mapped' for x in rows if not rows[x]['prerequisites']['capability_components'])
assert summary['new_objectives_ready']==summary['new_objectives_published']==0
mainline=json.loads((ROOT/'backend/resources/mainline_course.json').read_text(encoding='utf-8'))
assert summary['mainline_core_topics']==len(mainline['goals'])==148
assert summary['mainline_context_questions']==sum(len(g['variants']) for g in mainline['goals'])==294
assert summary['objectives_linked_to_topic_core']==729
assert all(r['existing_components'].get('mainline_core_component') for r in rows.values())
assert not mainline['assessment_policy']['automatic_full_objective_certification']
assert sum(summary['route_windows'].values())==729
assert summary['objectives_with_scoped_legacy_teaching_components']==sum(bool(r['existing_components'].get('teaching')) for r in rows.values())
print(json.dumps({'coverage_rows':len(rows),'referenced_resources':len(assets),
                  'input_hashes':'matched','source_provenance':'matched','choice_and_person_boundaries':'passed',
                  'real_data_accessed':False,'runtime_tests_run':False},ensure_ascii=False))
