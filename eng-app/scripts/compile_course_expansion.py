"""Compile source-backed expression lessons without generating English or translations."""
import json,re,sqlite3,hashlib
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
def tokens(s):return re.findall(r"[a-z]+(?:'[a-z]+)?",s.casefold().replace('’',"'"))
def key(s):return ' '.join(tokens(s))
def build():
 b=json.loads((ROOT/'backend/resources/compiled_courses.json').read_text(encoding='utf-8'))
 bank=sqlite3.connect((ROOT/'backend/data/shared-sentences.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
 lex={w['answer'].casefold():w for w in b['words']}
 main=json.loads((ROOT/'backend/resources/mainline_course.json').read_text(encoding='utf-8'))
 for term,note in main['word_notes'].items():
  lex.setdefault(term.casefold(),dict(id='course-word-'+hashlib.sha256(term.casefold().encode()).hexdigest()[:16],answer=term,prompt=note['zh'],details=dict(pos=note['pos'],usage=note['usage'],entry_type='word')))
 rows=[];gaps=[];used=set();stage_counts=Counter();contexts=0
 core={key(g['english']) for g in main['goals']};reused=[]
 band_total=Counter(e['band'] for e in b['expressions']);band_index=Counter()
 for e in b['expressions']:
  band_index[e['band']]+=1
  if key(e['answer']) in core:reused.append(e['id']);continue
  candidates=bank.execute("SELECT DISTINCT e.id,z.id,e.text,z.text,e.author,z.author FROM matches m JOIN pairs p ON p.en_id=m.en_id JOIN sentences e ON e.id=p.en_id JOIN sentences z ON z.id=p.zh_id WHERE m.target_id=? ORDER BY length(e.text),e.id,z.id LIMIT 160",(e['id'],)).fetchall()
  selected=[];missing=set();seen=set()
  for eid,zid,en,zh,ea,za in candidates:
   seq=tokens(en);norm=key(en)
   if not 3<=len(seq)<=16 or re.search(r'\d',en) or not re.search('[\u4e00-\u9fff]',zh) or norm in seen:continue
   if key(e['answer']) not in norm:continue
   unknown=set(seq)-lex.keys()
   if unknown:missing.update(unknown);continue
   seen.add(norm)
   selected.append(dict(en_id=eid,zh_id=zid,en=en,zh=zh,en_author=ea,zh_author=za,words=list(dict.fromkeys(seq))))
   if len(selected)>=4:break
  if not selected:
   gaps.append(dict(id=e['id'],english=e['answer'],reason='缺少词汇资料齐备的双语句',missing_words=sorted(missing)[:20]));continue
  span=4 if e['band']=='building' else 3
  stage={'basic':1,'building':3,'advanced':6}[e['band']]+min(span-1,(band_index[e['band']]-1)*span//band_total[e['band']])
  n=max(len(tokens(r['en'])) for r in selected)
  stage=max(stage,2 if n>7 else 1,3 if n>11 else 1)
  if any(w in tokens(e['answer']) for w in ('although','unless','whether','despite','instead')):stage=max(stage,5)
  stage=min(8,stage)
  terms=set(tokens(e['answer']))|set(w for r in selected for w in r['words'])
  if terms-lex.keys():gaps.append(dict(id=e['id'],english=e['answer'],reason='核心表达缺少词汇资料',missing_words=sorted(terms-lex.keys())));continue
  stage_counts['R%02d'%stage]+=1;contexts+=len(selected)-1;used.update(terms)
  rows.append(dict(id=e['id'],english=e['answer'],chinese=e['prompt'],stage='R%02d'%stage,domain=e['category'],rank=e['rank'],materials=sorted(terms),sentences=selected))
 bank.close()
 out=dict(version='source-expansion-v1',source='Tatoeba official direct pairs; community content, not publisher-reviewed',stage_policy='项目规则：原资料难度带、句长和结构词；非CEFR认证，领域为原资料标签',lessons=rows,words={w:lex[w] for w in sorted(used)},gaps=gaps,counts=dict(input_expressions=len(b['expressions']),lessons=len(rows),word_forms=len(used),demonstrations=len(rows),context_questions=contexts,gaps=len(gaps),reused_core_expressions=len(reused),stages=dict(stage_counts),domains=dict(Counter(r['domain'] for r in rows))))
 path=ROOT/'backend/resources/course_expansion.json';path.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 (ROOT/'docs/course-expansion-report.json').write_text(json.dumps(dict(counts=out['counts'],gaps=gaps,policy=out['stage_policy']),ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(out['counts'],ensure_ascii=False));return out
if __name__=='__main__':build()
