"""Exhaustive static corpus audit. No learner data or online publication."""
import json,re,hashlib
from pathlib import Path
from collections import Counter
r=Path(__file__).resolve().parents[1]
b=json.loads((r/'backend/resources/compiled_courses.json').read_text(encoding='utf-8'))
by_parent={}
for s in b['sentences']:by_parent.setdefault(s['parent'],[]).append(s)
counts=Counter();courses=[];missing=0
for e in b['expressions']:
 examples=[];seen=set()
 for s in by_parent.get(e['id'],[]):
  key=s['answer'].casefold().strip().rstrip('.!?')
  if key in seen:continue
  seen.add(key)
  sources=[x for x in s['details'].get('examples',[]) if x.get('source_url') and x.get('translation_url') and x.get('license') and x.get('zh')]
  examples.append(dict(id=s['id'],en=s['answer'],zh=s['prompt'],materials=s.get('word_keys',[]),sources=sources,provenance_complete=bool(sources)))
 usable=sum(x['provenance_complete'] for x in examples)
 missing+=max(0,6-usable)
 reasons=['stage_and_prerequisite_review_required','sense_match_review_required']
 if usable<6:reasons.append('fewer_than_six_sourced_examples')
 counts[e['category']]+=1
 courses.append(dict(id=e['id'],en=e['answer'],zh=e['prompt'],source_category=e['category'],rank=e['rank'],band=e['band'],ranking_basis='snapshot_sentence_coverage_not_official_frequency',contexts=examples,context_shortfall=max(0,6-usable),release_ready=False,blockers=reasons))
result=dict(status='fully_indexed_not_fully_authored',total_expressions=len(courses),total_source_sentences=len(b['sentences']),source_word_forms=len(b['words']),category_counts=dict(counts),minimum_additional_context_slots=missing,expressions_meeting_six_context_count=sum(len(x['contexts'])>=6 for x in courses),official_frequency_verified=False,items=courses)
output=r/'docs/full-course-material-audit.json';output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
assert len({x['id'] for x in courses})==3000
assert sum(len(x['contexts']) for x in courses)<=len(b['sentences'])
print(json.dumps({k:v for k,v in result.items() if k!='items'},ensure_ascii=False))