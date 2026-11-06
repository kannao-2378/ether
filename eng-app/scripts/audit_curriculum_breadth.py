"""Audit course breadth without touching any learning database."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=json.loads((ROOT/'backend/resources/mainline_course.json').read_text(encoding='utf-8'))
word_targets=[300,400,500,600,600,600,500,500]
chunk_targets=[150,250,400,450,500,500,400,350]
seen=set();stages=[]
for i,u in enumerate(spec['units']):
 goals=[g for g in spec['goals'] if g['unit']==u['id']]
 words={m['en'].casefold() for g in goals for m in g['materials']}
 new=words-seen;seen|=words
 stages.append(dict(id=u['id'],title=u['title'],target_new_lexemes=word_targets[i],target_new_collocation_senses=chunk_targets[i],actual_material_word_forms_new=len(new),actual_topics=len(goals),actual_authored_contexts=sum(len(g['variants']) for g in goals),target_contexts_per_structure=6,structures_below_context_target=[g['id'] for g in goals if len(g['variants'])<6]))
domains=[dict(id=k,title=t,start_stage=r,target_collocation_senses=n,status='planned_unmapped') for k,t,r,n in [('general','通用生活与交流','R01',1800),('reflection','自我、情绪与反思','R03',300),('design','设计、创作与品牌','R03',300),('finance','金钱、商业与金融','R03',250),('philosophy','哲学、价值与理念','R05',200),('public','社会、政治与公共议题','R05',150)]]
result=dict(version='breadth-plan-v1',status='design_and_audit_only_not_runtime',counting=dict(words='词元目标；现有只核对词形，不能直接相减宣称精确缺口',collocations='英文+义项；句型框架不自动计作高频搭配',domains='每项唯一主领域，跨领域标签不重复计数'),stages=stages,domains=domains,transfer=dict(min_authored_contexts=6,distinct_materials=3,distinct_situations=2,pass_different_contexts=3,delayed_check_required=True,stable_not_prerequisite=True,exposure_excluded=True,maximum_new_contexts_per_session=2),sources=['https://englishprofile.org/?menu=english-vocabulary-profile'],actual_total_word_forms=len(seen),actual_total_authored_contexts=sum(len(g['variants']) for g in spec['goals']))
out=ROOT/'docs/curriculum-breadth-audit.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
assert sum(word_targets)==4000 and sum(chunk_targets)==3000
assert sum(d['target_collocation_senses'] for d in domains)==3000
print('8 stages; targets: 4000 lexemes / 3000 collocation senses; actual:',len(seen),'word forms;',result['actual_total_authored_contexts'],'contexts')
print('topics below 6 contexts:',sum(len(s['structures_below_context_target']) for s in stages))