"""Inventory existing bilingual examples by goal. Never imports learner data or approves candidates."""
import argparse,csv,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def key(s):return ' '.join(s.casefold().replace('’',"'").rstrip('.!?。！？ ').split())
def patterns(goals):
 frames={'like-doing':r'like [a-z]+ing\b','enjoy-doing':r'enjoy [a-z]+ing\b','practice-doing':r'practice [a-z]+ing\b','keep-doing':r'keep [a-z]+ing\b','finish-doing':r'finish [a-z]+ing\b','route-going-to':r"(?:am |'m )going to (?:go|do|be|have|eat|drink|read|learn|work|make|buy|take|see|visit|leave|stay|get|help|try|study|play|watch|meet|ask|tell|give|call|use|bring|find|write|start|cook|talk|listen|wait|look|sleep|travel|send|come)\b",'route-i-am':r"(?:am |'m )(?![a-z]+ing\b)", 'route-good-at':r"(?:am |'m )good at\b",'route-afraid-of':r"(?:am |'m )afraid of\b"}
 gerunds={'morning','evening','spring','thing','something','anything','nothing','everything','king','ceiling','wedding'}
 result={}
 for g in goals:
  gid=g['key'];literal=re.escape(g['english'].casefold())
  broad=frames.get(gid,literal)
  if gid in ('like-doing','enjoy-doing','practice-doing','keep-doing','finish-doing'):broad=frames[gid]
  # I-frame recommendation; modifiers can occur anywhere within a simple I-clause.
  prefix=frames.get(gid,literal)
  if gid in ('every-day','route-in-the-morning','route-at-night','route-after-work','route-before-dinner','route-on-weekends','route-at-home','route-in-front-of','route-next-to','route-a-lot-of','route-because-of'):
   simple=r"^i(?: |'m ).*\b"+literal+r'\b'
  elif gid in ('route-i-am','route-good-at','route-afraid-of','route-going-to'):simple=r'^i(?: |(?=\'))'+prefix
  else:simple=r'^i '+prefix+r'\b'
  stems={'want-to':'want(?:s|ed|ing)? to','need-to':'need(?:s|ed|ing)? to','hope-to':'(?:hope|hopes|hoped|hoping) to','plan-to':'(?:plan|plans|planned|planning) to','decide-to':'(?:decide|decides|decided|deciding) to','learn-to':'(?:learn|learns|learned|learnt|learning) to','try-to':'(?:try|tries|tried|trying) to','like-doing':'(?:like|likes|liked|liking) [a-z]+ing','enjoy-doing':'enjoy(?:s|ed|ing)? [a-z]+ing','practice-doing':'(?:practice|practices|practiced|practicing|practise|practises|practised|practising) [a-z]+ing','keep-doing':'(?:keep|keeps|kept|keeping) [a-z]+ing','finish-doing':'finish(?:es|ed|ing)? [a-z]+ing','drink-water':'(?:drink|drinks|drank|drunk|drinking) water','read-books':'(?:read|reads|reading) books','learn-english':'(?:learn|learns|learned|learnt|learning) english','eat-a-meal':'(?:eat|eats|ate|eaten|eating)','get-up':'(?:get|gets|got|getting) up','go-home':'(?:go|goes|went|going) home','go-to-school':'(?:go|goes|went|going) to school','cook-at-home':'cook(?:s|ed|ing)? at home'}
  for base,forms in [('listen','listen(?:s|ed|ing)?'),('look','look(?:s|ed|ing)?'),('wait','wait(?:s|ed|ing)?'),('talk','talk(?:s|ed|ing)?'),('ask','ask(?:s|ed|ing)?'),('pay','(?:pay|pays|paid|paying)'),('worry','(?:worry|worries|worried|worrying)'),('agree','(?:agree|agrees|agreed|agreeing)'),('think','(?:think|thinks|thought|thinking)'),('depend','depend(?:s|ed|ing)?'),('belong','belong(?:s|ed|ing)?')]:
   if goal_en:=re.match('^'+base+' (.+)$',g['english'].casefold()):stems[gid]=forms+' '+re.escape(goal_en[1])
  broad=stems.get(gid,broad)
  if gid=='route-i-am':broad=r'i am';simple=r'^i am (?![a-z]+ing\b)'
  elif gid=='route-good-at':broad='good at';simple=r'^i am good at\b'
  elif gid=='route-afraid-of':broad='afraid of';simple=r'^i am afraid of\b'
  elif gid=='route-going-to':broad='going to';simple=r'^i '+frames[gid]
  result[gid]=(re.compile(r'(?<![a-z])'+broad+r'(?![a-z])',re.I),re.compile(simple,re.I))
 return result

def collect(output):
 pack=json.loads((ROOT/'backend/resources/compiled_courses.json').read_text(encoding='utf-8'));route=json.loads((ROOT/'backend/resources/teaching_routes.json').read_text(encoding='utf-8'));rules=patterns(route['goals']);words={r['id']:r for r in pack['words']}
 approved=json.loads((ROOT/'backend/resources/sourced_transfer_pilot.json').read_text(encoding='utf-8'))['rows'];approved={(r['goal'],r['source_id']):r for r in approved if r['review']['status']=='approved'}
 banned=re.compile(r'\b(?:fuck\w*|shit|sex|rape|naked|porn\w*|suicide|kill\w*)\b|sleep with your wife',re.I)
 flags={'unsupported_source':0,'empty_translation':0,'duplicate_input':0};candidates=[];coverage=[];by_english={};goals=route['goals']
 for goal in goals:
  gid=goal['key'];broad,simple=rules[gid];seen=set();matched=[];short=[]
  taught={key(goal.get('sentence',''))}|{key(e['en']) for e in goal.get('examples',[]) if isinstance(e,dict) and e.get('en')}
  for row in pack['sentences']:
   en=row['answer'];normal=key(en).replace("i'm",'i am')
   if not broad.search(normal):continue
   if normal in seen:continue
   seen.add(normal)
   sources=[e for e in row['details'].get('examples',[]) if e.get('en')==en and e.get('source_url') and e.get('translation_url') and e.get('license')]
   if not sources:flags['unsupported_source']+=1;continue
   if not row['prompt'].strip():flags['empty_translation']+=1;continue
   tokens=re.findall(r"[a-z]+(?:'[a-z]+)?",normal);reasons=[]
   if not simple.search(normal):reasons.append('主语或结构超出当前简单I句型')
   if len(tokens)>12:reasons.append('句子偏长')
   if any(mark in en for mark in [';',':','\n','?','!']):reasons.append('句式或标点需额外确认')
   if re.search(r'\b(?:if|unless|although|whether|whose|whom|when|while|where|who|which|because|but|and|that)\b',normal) and gid!='route-because-of':reasons.append('可能包含额外分句或连接结构')
   if en.rstrip('.').count('.') or '"' in en:reasons.append('可能需要上下文或含多个句子')
   if banned.search(en):reasons.append('不选为本批基础训练情境')
   if normal in taught:reasons.append('本目标已有示范句，不能作新迁移储备')
   if gid=='route-next-to' and 'next to nothing' in normal:reasons.append('next to nothing是另一习语，不是位置关系')
   if 'do fishing' in normal:reasons.append('表达自然度需核对，不入本批')
   if '我试试思想' in row['prompt']:reasons.append('中文原译不适合直接教学，待修订')
   if gid=='route-i-am' and re.search(r'\b(?:all ears|done up)\b',normal):reasons.append('需先学习额外习语')
   if re.search(r'\b(?:what|how|when|while|where|who|which)\b',normal):
    if '可能包含额外分句或连接结构' not in reasons:reasons.append('可能包含额外分句或连接结构')
   if gid.startswith('route-') or gid=='every-day':
    if not re.search(r'^i (?:am|drink|eat|read|learn|go|cook|want|need|hope|plan|decide|like|enjoy|practice|keep|finish|listen|look|wait|talk|ask|pay|worry|agree|think|depend|belong|have|run|bathe|work|live|sleep|stay|study|speak|walk|play|try|used|would)\b',normal):reasons.append('需先准备额外时态或句式')
   if gid.endswith('doing') and re.search(r'\b(?:like|enjoy|practice|keep|finish) (?:morning|evening|spring|thing|something|anything|nothing|everything|king|ceiling|wedding)\b',normal):reasons.append('ing词不等于动作，需词义确认')
   deps=[dict(dictionary_id=k,english=words[k]['answer'],chinese=words[k]['prompt']) for k in row['word_keys'] if k in words]
   old=approved.get((gid,row['id']))
   entry=dict(goal_id=gid,goal=goal['english'],source_id=row['id'],english=en,chinese=old['chinese'] if old else row['prompt'],original_chinese=row['prompt'],source=sources[0],lexical_dependencies=deps,dependency_status='已有试点前置材料标注' if old else '词汇已关联；具体词义、词块、语法依赖待标注',review_status='已有试点AI辅助逐条核对' if (gid,row['id']) in approved else '待内容与依赖复核',screening='建议优先复核' if not reasons else '待筛选',screening_reasons=reasons,word_count=len(tokens))
   matched.append(entry)
   if not reasons:short.append(entry)
  blocked=['不选为本批基础训练情境','本目标已有示范句，不能作新迁移储备','next to nothing是另一习语，不是位置关系','表达自然度需核对，不入本批','中文原译不适合直接教学，待修订']
  eligible=[r for r in matched if not any(x in blocked for x in r['screening_reasons'])]
  eligible.sort(key=lambda r:((gid,r['source_id']) not in approved,len(r['screening_reasons']),r['word_count'],len(r['english']),r['source_id']))
  selected=[];translations=set()
  for row in eligible:
   zh=re.sub(r'[。！？，、,.!?\s]','',row['chinese'])
   if zh in translations:continue
   translations.add(zh);selected.append(row)
   if len(selected)==5:break
  for row in matched:
   row['shortlisted']=any(r['source_id']==row['source_id'] for r in selected)
   row['excluded']=any(x in blocked for x in row['screening_reasons'])
   candidates.append(row)
   if row['excluded']:continue
   by_english.setdefault(key(row['english']),dict(english=row['english'],chinese=row['chinese'],source=row['source'],status='待内容与教学依赖复核',goals=[]))['goals'].append(gid)
  coverage.append(dict(goal_id=gid,goal=goal['english'],matched=len(matched),simple_candidates=len(short),shortlisted=len(selected),basic_shortlisted=sum(not r['screening_reasons'] for r in selected),target=5,gap=max(0,5-len(selected)),reviewed=sum((gid,r['source_id']) in approved for r in selected),status='候选已找到，待复核与依赖标注' if len(selected)>=5 else '当前初筛不足5条；需调整匹配或补来源'))
 output.mkdir(parents=True,exist_ok=True)
 with (output/'coverage.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(coverage[0]));w.writeheader();w.writerows(coverage)
 with (output/'candidates.jsonl').open('w',encoding='utf-8') as f:
  for row in candidates:f.write(json.dumps(row,ensure_ascii=False)+'\n')
 shortlisted=[r for r in candidates if r['shortlisted']]
 with (output/'shortlist.csv').open('w',encoding='utf-8-sig',newline='') as f:
  names=['goal_id','goal','source_id','english','chinese','review_status','dependency_status','screening_reasons','source_url'];w=csv.DictWriter(f,fieldnames=names);w.writeheader()
  for r in shortlisted:w.writerow({**{k:r[k] for k in names if k!='source_url'},'source_url':r['source']['source_url']})
 (output/'shared_examples.json').write_text(json.dumps(dict(version=1,status='inventory_only_not_active_curriculum',sentences=list(by_english.values())),ensure_ascii=False,indent=2),encoding='utf-8')
 summary=dict(input_sentences=len(pack['sentences']),goals=len(goals),matched_associations=len(candidates),unique_source_sentences=len(by_english),goals_with_matches=sum(r['matched']>0 for r in coverage),shortlisted_associations=len(shortlisted),shortlisted_unique=len({key(r['english']) for r in shortlisted}),goals_with_five=sum(r['shortlisted']>=5 for r in coverage),basic_shortlisted=sum(r['basic_shortlisted'] for r in coverage),gap=sum(r['gap'] for r in coverage),previously_reviewed=sum(r['reviewed'] for r in coverage),note='储备含需要额外语法准备的句子，不等于正式可用题；未新增英文，未改学习记录，未装入运行课程。')
 (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
 lines=['# 现有例句批量匹配结果','',summary['note'],'',
 f"已检查 {summary['input_sentences']} 条双语例句，覆盖 {summary['goals_with_matches']} 个目标。去除明显不对应内容后，整理 {summary['unique_source_sentences']} 条不同来源句。按每目标最多5条，选出 {summary['shortlisted_associations']} 条储备，{summary['goals_with_five']} 个目标达到5条，储备缺口 {summary['gap']} 条。",'',
 f"储备中 {summary['basic_shortlisted']} 条符合简单I句式初筛，另外 {summary['shortlisted_associations']-summary['basic_shortlisted']} 条需要额外句式或其他准备。初筛通过不等于审核合格；只有既有 {summary['previously_reviewed']} 条保留试点审核标记。其余都需要内容及词义、词块、语法依赖复核。",'',
 f"若只要求简单I句式，形式候选缺口为 {250-summary['basic_shortlisted']} 条。上述储备缺口不能当成当前可直接学习的缺口。缺口只是当前资料和匹配条件的结果，不能直接认定必须新编同等数量句子。",'',
 '文件：coverage.csv 是逐组数量，shortlist.csv 是优先候选清单，candidates.jsonl 是全部匹配审计，shared_examples.json 是按原句去重的共享目录。保留来源、译文来源与许可证。仅目录整理，未启用课程或修改真实数据。','',
 '| 学习目标 | 文字命中 | 简单I句候选 | 本批储备 | 其中简单I句 | 距5条缺口 |','|---|---:|---:|---:|---:|---:|' ]
 lines += [f"| {r['goal']} | {r['matched']} | {r['simple_candidates']} | {r['shortlisted']} | {r['basic_shortlisted']} | {r['gap']} |" for r in coverage]
 (output/'结果.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',default=str(ROOT/'reports/shared-examples'));a=p.parse_args();collect(Path(a.output))
