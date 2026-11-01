"""Offline compiler: dictionary-attested expressions + independently translated examples.

Source snapshots and licenses are in backend/resources. No runtime AI or network is used.
Selection rank is this corpus's coverage, NOT an official general-English frequency list.
"""
from pathlib import Path
import csv,json,re,hashlib,collections,math
import spacy

ROOT=Path(__file__).resolve().parents[1];RES=ROOT/'backend/resources'
POS={'NOUN':'n. 名词','VERB':'v. 动词','ADJ':'adj. 形容词','ADV':'adv. 副词','ADP':'prep. 介词','PRON':'pron. 代词','DET':'限定词','AUX':'助动词','CCONJ':'连词','SCONJ':'从属连词','PART':'小品词','NUM':'数词','INTJ':'感叹词','PROPN':'专有名词'}
BAD=re.compile(r'\b(fuck|shit|bitch|porn|suicide|nazi|rape|murder|cocaine|heroin)\w*\b',re.I)
TECH=re.compile(r'\[[^]]+\]|<[^>]+>|古语|古义|骂人|粗俗|脏话|俚语|罕用')
FUNCTION_END=set('a an the my your his her our their is was are been be do did has have he she it we they'.split())
FRAGMENTS={'a good','a great','a nice','a bad','a new','a young','a big','a long','a short','lot of','such good','as good','very own'}
CATEGORIES=[
 ('self','自我、情绪与思考','表达感受、回忆、意愿、判断和自我认识。','feel mind think remember forget believe hope afraid happy sad worry wish dream idea thought life truth meaning purpose myself yourself himself herself'),
 ('society','社会、观点与公共议题','理解规则、权利、社会关系及表达不同意见。','law rule right government public society country nation vote political politics freedom free agree disagree opinion peace war power social history'),
 ('finance','金钱、商业与金融基础','谈论价格、收入、交易、储蓄、风险与商业。','money pay cost price buy sell bank business market trade rich poor debt stock investment invest profit interest financial tax income cash credit dollar save savings'),
 ('design','设计、创作与品牌表达','描述外观、风格、构思、创作及信息呈现。','design art color colour style brand image picture photo shape draw paint creative create model pattern light dark beautiful beauty music song film'),
 ('learning','学习、语言与沟通','组织学习活动，提出问题并理解交流。','learn study school book read write english language word lesson question answer understand explain speak say talk tell know teacher student university college listen'),
 ('work','工作、计划与解决问题','表达任务、进度、方法、决定、能力和合作。','work job office meeting plan decide try help need must should can able task problem solve result success fail finish start begin end project effort team important possible chance opportunity'),
 ('relationships','人际关系与交往','问候、礼貌表达、家庭朋友及相处。','friend family mother father parent sister brother child baby wife husband marry love together meet visit welcome thank sorry please excuse respect person people man woman boy girl'),
 ('travel','出行、地点与方向','表达交通、距离、路线、位置与旅行经历。','go come walk run drive ride travel trip car bus train plane flight road street station airport hotel town city village home house room door outside inside away near far left north south east west'),
 ('daily','生活、饮食与健康','日常活动、生活用品、身体与健康。','eat drink water food tea coffee milk dinner lunch breakfast meal sleep bed tired sick ill health doctor hospital body hand eye face head heart hair clothes wear cold hot weather rain snow sun'),
 ('time','时间、数量与关系','表达频率、时间顺序、程度、比较和逻辑联系。','day night morning evening week month year time hour minute today tomorrow yesterday now then before after always never often sometimes much many little few more less most least same different only once twice'),
]
def stable(prefix,value):return prefix+hashlib.sha256(value.casefold().encode()).hexdigest()[:16]
def clean(s):return s.replace('\\n','\n').strip()
def meaning(row):
 s=clean(row['translation']);lines=[x.strip() for x in s.splitlines() if re.search('[\u4e00-\u9fff]',x) and not TECH.search(x)]
 return (lines[0] if lines else '').strip()
def category(phrase,en):
 if phrase in ('interest in','interested in','take an interest in'):return 'learning'
 words=set(re.findall('[a-z]+',phrase));full=set(re.findall('[a-z]+',en.lower()))
 scores=[(len(words&set(keys.split()))*8+len(full&set(keys.split())),index,key) for index,(key,*_,keys) in enumerate(CATEGORIES)]
 return max(scores,key=lambda t:(t[0],-t[1]))[2]
ARP={'AA':'ɑː','AE':'æ','AH':'ʌ','AO':'ɔː','AW':'aʊ','AY':'aɪ','B':'b','CH':'tʃ','D':'d','DH':'ð','EH':'ɛ','ER':'ɝ','EY':'eɪ','F':'f','G':'ɡ','HH':'h','IH':'ɪ','IY':'iː','JH':'dʒ','K':'k','L':'l','M':'m','N':'n','NG':'ŋ','OW':'oʊ','OY':'ɔɪ','P':'p','R':'r','S':'s','SH':'ʃ','T':'t','TH':'θ','UH':'ʊ','UW':'uː','V':'v','W':'w','Y':'j','Z':'z','ZH':'ʒ'}
def pronunciation(phones):
 if not phones:return None,None,None
 vowels=[p for p in phones if p[-1:].isdigit()];count=len(vowels);stress=next((i+1 for i,p in enumerate(vowels) if p.endswith('1')),1)
 # Segment readings are intentional: do not invent syllable boundaries in spelling.
 values=[]
 for p in phones:
  base=p.rstrip('012');values.append('ə' if p=='AH0' else 'ɚ' if p=='ER0' else ARP.get(base,''))
 return '/'+''.join(values)+'/',f'{count} 个音节',('单音节' if count==1 else f'第 {stress} 音节重读')

def grammar(doc):
 notes=[]
 if any(t.dep_ in ('nsubj','nsubjpass') for t in doc):
  subjects=[t.text for t in doc if t.dep_ in ('nsubj','nsubjpass')];notes.append('句中主语：'+ ' / '.join(subjects)+'；先找出“谁或什么”在做事。')
 roots=[t for t in doc if t.dep_=='ROOT'];root=roots[0] if roots else None
 if root:notes.append('核心谓语：'+root.text+'；用它判断句子主要在说什么。')
 if any(t.dep_=='neg' for t in doc):notes.append('否定表达：注意 not / n\'t 的位置，不能只把中文“不”插进句子。')
 if any(t.tag_=='MD' for t in doc):notes.append('情态动词后使用动词原形；对照例句检查 can、should、must 等词后面的动作。')
 if any(t.dep_=='aux' and t.lemma_=='have' for t in doc):notes.append('have / has / had 与过去分词可以构成完成体；不要把每个 have 都理解成“拥有”。')
 elif any(t.dep_=='aux' and t.lemma_=='be' for t in doc) and any(t.tag_=='VBG' for t in doc):notes.append('be 与动词-ing 可以构成进行体，表示某时正在进行的动作。')
 elif root and 'Past' in root.morph.get('Tense'):notes.append('例句包含过去形式；回忆时要保留相应词形，不只是记住原形。')
 if doc.text.endswith('?'):notes.append('这是疑问句；请观察助动词、主语和主要动作的顺序。')
 return notes or ['把表达放回例句中理解它的作用，不按中文逐字替换。']

def main():
 lex={}
 for r in csv.DictReader((RES/'ecdict/ecdict.csv').open(encoding='utf-8')):
  if re.fullmatch(r"[a-z]+(?:[ '-][a-z]+)*",r['word']) and meaning(r):lex[r['word']]=r
 phrases={p:r for p,r in lex.items() if re.fullmatch('[a-z]+(?: [a-z]+){1,4}',p) and p.split()[-1] not in FUNCTION_END and p not in FRAGMENTS and not BAD.search(p)}
 matches=collections.defaultdict(dict);counts=collections.Counter();seen=set()
 for line in (RES/'tatoeba/train.jsonl').open(encoding='utf-8'):
  r=json.loads(line);en=r.get('eng-txt','').strip();zh=r.get('cmn-txt','').strip();sid=r.get('eng-id','')
  tokens=re.findall(r"[a-z]+(?:'[a-z]+)?",en.lower())
  if not 3<=len(tokens)<=18 or not re.search('[\u4e00-\u9fff]',zh) or BAD.search(en) or '\n' in en or len(zh)>130:continue
  if not re.fullmatch(r"[A-Za-z0-9 ,.!?;:'’\-\"()]+",en):continue
  if sid not in seen:counts.update(tokens);seen.add(sid)
  for n in range(2,6):
   for i in range(len(tokens)-n+1):
    phrase=' '.join(tokens[i:i+n])
    if phrase in phrases and re.search(r'(?<![a-z])'+re.escape(phrase)+r'(?![a-z])',en.lower()):matches[phrase].setdefault(sid,r)
 print('attested candidates',len(matches),flush=True)
 nlp=spacy.load('en_core_web_sm')
 surface_docs=dict(zip(matches,nlp.pipe(matches,batch_size=128)))
 families=collections.defaultdict(list)
 for phrase,doc in surface_docs.items():
  canonical=' '.join(t.lemma_.lower() for t in doc)
  if phrase in ('going to','be going to'):canonical='future:'+canonical
  families[canonical].append(phrase)
 representatives=[]
 for canonical,forms in families.items():
  # Prefer an attested base form; don't count came/come or had/have as new groups.
  base=canonical.removeprefix('future:')
  representative=base if base in forms else max(forms,key=lambda p:(len(matches[p]),-len(p)))
  representatives.append((representative,sum(len(matches[p]) for p in forms)))
 ranked=sorted(representatives,key=lambda pair:(-pair[1],sum(1/math.sqrt(counts[w]+1) for w in pair[0].split()),pair[0]))
 selected=[p for p,_ in ranked[:3000]]
 print('distinct lemma families',len(families),flush=True)
 if len(selected)!=3000:raise RuntimeError('Insufficient attested expressions; do not pad the pack.')
 cmu={}
 for line in (RES/'cmudict/cmudict.dict').read_text(encoding='utf-8').splitlines():
  if line.startswith(';;;') or not line.strip():continue
  word,*phones=line.split();cmu.setdefault(re.sub(r'\(\d+\)$','',word),phones)
 roots=json.loads((RES/'ecdict/wordroot.txt').read_text(encoding='utf-8'));root_examples=collections.defaultdict(list)
 for key,r in roots.items():
  for example in r.get('example',[]):
   if isinstance(example,str):root_examples[example.lower()].append(dict(part=key,meaning=r.get('meaning',''),origin=r.get('origin','')))
 examples={}
 for p in selected:
  rows=sorted(matches[p].values(),key=lambda r:(len(r['eng-txt'].split()),r['eng-id']))[:3]
  for r in rows:examples[r['eng-id']]=r
 print('analysing real examples',len(examples),flush=True)
 docs=dict(zip(examples,nlp.pipe((r['eng-txt'] for r in examples.values()),batch_size=128)))
 lexeme_usage={};records=[];all_sentences={};grouped=collections.defaultdict(list)
 for rank,p in enumerate(selected):
  evidence=sorted(matches[p].values(),key=lambda r:(len(r['eng-txt'].split()),r['eng-id']))[:3];first=evidence[0];cat=category(p,first['eng-txt'])
  group='basic' if rank<1000 else 'building' if rank<2000 else 'advanced';difficulty=['基础表达','组合表达','扩展表达'][rank//1000]
  kid=stable('expr-',p);row=phrases[p];phrase_doc=nlp(p);pos=POS.get(phrase_doc.root.pos_,'表达') if hasattr(phrase_doc,'root') else None
  token_pos=next((t.pos_ for t in phrase_doc if t.dep_=='ROOT'),'');kind='phrase' if token_pos in ('NOUN','PROPN') else 'collocation'
  ipa,syll,stress=pronunciation(cmu.get(p))
  parts=[]
  for word in p.split():
   ip,sy,st=pronunciation(cmu.get(word))
   if ip:parts.append(dict(en=word,ipa=ip,syllables=sy,stress=st))
  records.append(dict(id=kid,answer=p,prompt=meaning(row),explanation='本条是词典收录并在独立双语例句中出现的表达；结合例句判断本次含义。',example=first['eng-txt'],details=dict(entry_type=kind,level=difficulty,topics=[next(c[1] for c in CATEGORIES if c[0]==cat)],pos='名词短语' if kind=='phrase' else '词典表达／搭配',ipa_us=ipa,syllables=syll,stress=stress,pronunciation_parts=parts,definition_en=clean(row['definition']) or None,usage=meaning(row),structure=p,knowledge_points=grammar(docs[first['eng-id']]),common_errors=['拼写时保留完整表达；复述例句时还要注意主语、时态和前后搭配。'],forms=[],roots=None,root_note='多词表达不强行拆词根；下方词汇材料分别保留可用的构词资料。',extensions=[],examples=[dict(en=r['eng-txt'],zh=r['cmn-txt'],scene='真实双语语料',source_url='https://tatoeba.org/en/sentences/show/'+r['eng-id'],translation_url='https://tatoeba.org/en/sentences/show/'+r['cmn-id'],attribution='Tatoeba contributors; sentence IDs '+r['eng-id']+' / '+r['cmn-id'],license='CC BY 2.0 FR') for r in evidence],sources=[dict(title='ECDICT · 双语表达词条（MIT）',url='https://github.com/skywind3000/ECDICT'),dict(title='Tatoeba · 例句与译文',url='https://tatoeba.org/en/sentences/show/'+first['eng-id']),dict(title='CMU · 美式分词读音',url='https://github.com/cmusphinx/cmudict')],speech_text=p,audio_path=None,version=1,review_status='词典与双语语料交叉匹配；句法为离线自动分析，未逐条人工审核',corpus_occurrences=len(matches[p]),source_phonetic=clean(row['phonetic']) or None),category=cat,band=group,rank=rank))
  grouped[(cat,group)].append(kid)
  for r in evidence:
   doc=docs[r['eng-id']];sid=stable('sent-',r['eng-txt']);word_keys=[]
   for t in doc:
    w=t.text.lower()
    if t.pos_ in ('PUNCT','SPACE','PROPN') or not re.fullmatch('[a-z]+',w) or w not in lex:continue
    wid=stable('lex-',w);word_keys.append(wid);lexeme_usage.setdefault(w,(r,t.pos_,t.lemma_))
   all_sentences.setdefault(sid,dict(id=sid,answer=r['eng-txt'],prompt=r['cmn-txt'],explanation='在真实句子中回忆已学表达，注意句型和词形。',example=r['eng-txt'],parent=kid,word_keys=list(dict.fromkeys(word_keys)),details=dict(entry_type='sentence',level=difficulty,topics=[cat],ipa_us=None,syllables=None,stress=None,pos=None,usage='先确认中文情境，再用本课表达组织完整句子。',structure=p,knowledge_points=grammar(doc),common_errors=['本题使用语料中的参考表达；合理的其他译法需要另行加入答案集合，不能一概当作语法错误。'],forms=[],roots=None,extensions=[],examples=[dict(en=r['eng-txt'],zh=r['cmn-txt'],scene='Tatoeba 双语例句',source_url='https://tatoeba.org/en/sentences/show/'+r['eng-id'],translation_url='https://tatoeba.org/en/sentences/show/'+r['cmn-id'],attribution='Tatoeba sentence IDs '+r['eng-id']+' / '+r['cmn-id'],license='CC BY 2.0 FR')],sources=[dict(title='Tatoeba · 原句及作者',url='https://tatoeba.org/en/sentences/show/'+r['eng-id'])],speech_text=r['eng-txt'],version=1,review_status='独立双语语料；句法分析未经逐条人工审核'),category=cat,band=group,rank=rank))
   records[-1]['details']['extensions'].append(dict(en=r['eng-txt'],note='对应中文：'+r['cmn-txt'],knowledge_id=sid))
 words=[]
 for w,(r,pos,lemma) in sorted(lexeme_usage.items(),key=lambda item:(-counts[item[0]],item[0])):
  row=lex[w];ip,sy,st=pronunciation(cmu.get(w));forms=[]
  names={'p':'过去式','d':'过去分词','i':'-ing 形式','3':'第三人称单数','s':'复数','r':'比较级','t':'最高级','0':'原形'}
  for pair in row['exchange'].split('/'):
   if ':' in pair:
    k,v=pair.split(':',1)
    if k in names:forms.append(names[k]+'：'+v)
  words.append(dict(id=stable('lex-',w),answer=w,prompt=meaning(row),explanation='词汇材料：本课例句中使用的 '+POS.get(pos,pos)+'。',example=r['eng-txt'],details=dict(entry_type='word',level='词汇材料',topics=['课程词汇'],ipa_us=ip,syllables=sy,stress=st,pos=POS.get(pos,pos),definition_en=clean(row['definition']) or None,usage=meaning(row),structure=None,knowledge_points=['本课词性：'+POS.get(pos,pos)+'；具体意思需要结合下方例句。'],common_errors=[],forms=forms,roots='；'.join(x['part']+' = '+x['meaning']+'（'+x['origin']+'）' for x in root_examples[w]) or None,root_note='只保留构词资料中明确列举此词的说明；没有资料时不强行拆解。',extensions=[],examples=[dict(en=r['eng-txt'],zh=r['cmn-txt'],source_url='https://tatoeba.org/en/sentences/show/'+r['eng-id'],translation_url='https://tatoeba.org/en/sentences/show/'+r['cmn-id'],attribution='Tatoeba sentence IDs '+r['eng-id']+' / '+r['cmn-id'],license='CC BY 2.0 FR')],sources=[dict(title='ECDICT · 词条与构词资料',url='https://github.com/skywind3000/ECDICT'),dict(title='CMU · 美式发音',url='https://github.com/cmusphinx/cmudict')],speech_text=w,version=1,review_status='开放词典材料；词性取本课例句，不代表此词只有一种词性',lemma=lemma,source_phonetic=clean(row['phonetic']) or None)))
 translations=collections.defaultdict(set)
 for r in examples.values():translations[r['cmn-txt']].add(r['eng-txt'])
 for sentence in all_sentences.values():
  target=sentence['details']['structure']
  sentence['details']['accepted_answers']=sorted({sentence['answer']}|{en for en in translations[sentence['prompt']] if re.search(r'(?<![a-z])'+re.escape(target)+r'(?![a-z])',en.lower())})
 data=dict(version='attested-3000-v1',expression_count=len(records),sentence_count=len(all_sentences),word_count=len(words),categories=[dict(id=c[0],title=c[1],goal=c[2]) for c in CATEGORIES],expressions=records,sentences=list(all_sentences.values()),words=words,selection='ECDICT exact entries appearing in independently translated Tatoeba sentences; ordered by unique sentence coverage in this snapshot, not an official frequency ranking.',source_files={str(p.relative_to(RES)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (RES/'ecdict/ecdict.csv',RES/'tatoeba/train.jsonl',RES/'cmudict/cmudict.dict')})
 path=RES/'compiled_courses.json';path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 print(json.dumps({k:data[k] for k in ('version','expression_count','sentence_count','word_count')})+' bytes='+str(path.stat().st_size),flush=True)

if __name__=='__main__':main()
