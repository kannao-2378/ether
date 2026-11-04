"""Extract attested syllable counts/stress from the bundled CMU dictionary.

Does not infer spelling divisions or fabricate missing IPA. No learner DB/network.
"""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RES=ROOT/'backend/resources'
spec=json.loads((RES/'mainline_course.json').read_text(encoding='utf-8'))
terms={t.casefold() for g in spec['goals'] for s in [g['english'],g['sentence']]+[v['en'] for v in g['variants']] for t in re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?",s)}
phones={}
for line in (RES/'cmudict/cmudict.dict').read_text(encoding='utf-8').splitlines():
    parts=line.split()
    if not parts or line.startswith(';;;'):continue
    key=re.sub(r'\(\d+\)$','',parts[0]).casefold()
    if key in terms:phones.setdefault(key,[p for p in parts[1:] if re.fullmatch('[A-Z]+[012]?',p)])
result={}
for term,values in sorted(phones.items()):
    vowels=[p for p in values if p[-1:].isdigit()]
    if not vowels:continue
    stress=next((i+1 for i,v in enumerate(vowels) if v.endswith('1')),None)
    result[term]=dict(syllables=f'{len(vowels)} 个音节',stress='单音节' if len(vowels)==1 else f'第 {stress} 音节重读' if stress else '',source='CMU Pronouncing Dictionary',phones=values)
(RES/'mainline_pronunciation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(words=len(result),unavailable=sorted(terms-set(result)),fabricated_ipa=False)))
