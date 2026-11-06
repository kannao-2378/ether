"""Index existing course assets as candidates, never publish unreviewed lessons."""
import json,re
from pathlib import Path
from collections import Counter
r=Path(__file__).resolve().parents[1];b=json.loads((r/'backend/resources/compiled_courses.json').read_text(encoding='utf-8'))
sent={x['id']:x for x in b['sentences']};rows=[]
for e in b['expressions']:
 d=e.get('details',{});examples=d.get('examples',[])
 rows.append(dict(id=e['id'],english=e['answer'],chinese=e['prompt'],topics=d.get('topics',[]),available_bilingual_examples=sum(bool(x.get('en') and x.get('zh')) for x in examples),status='candidate_requires_sense_stage_review',reason='已有词典与双语资料，尚未验证频率、阶段和目标义项'))
out=r/'docs/course-asset-candidates.json';out.write_text(json.dumps(dict(expressions=len(rows),sentences=len(sent),words=len(b['words']),topics=dict(Counter(t for x in rows for t in x['topics'])),items=rows),ensure_ascii=False,indent=2),encoding='utf-8')
print('indexed',len(rows),'expressions;',len(sent),'sentences;',len(b['words']),'word entries; candidates only')