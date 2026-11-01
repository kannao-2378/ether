"""Public reference lookup, optional official APIs, explicit preview before import."""
from contextlib import closing
import gzip,hashlib,json,re,sqlite3,threading,uuid,os,shutil
from pathlib import Path
from datetime import datetime,timedelta,timezone
from urllib.request import Request,urlopen
from urllib.parse import urlencode,quote
from urllib.error import HTTPError,URLError
from sqlalchemy import text
LOCK=threading.Lock();RES=Path(__file__).parent/'resources';WORD=re.compile("[a-zA-Z][a-zA-Z '-]{0,79}")
ECDICT='https://github.com/skywind3000/ECDICT'
def install(c):c.execute(text('CREATE TABLE IF NOT EXISTS lookup_previews(word TEXT PRIMARY KEY,id TEXT UNIQUE,payload TEXT,created_at TEXT)'))
def clean_word(word):
 word=' '.join(word.strip().casefold().split())
 if not WORD.fullmatch(word) or len(word.split())>6:raise ValueError('请输入英文单词或短语，最多80个字符')
 return word

def reference(data):
 archive=RES/'lookup-reference.sqlite3.gz'
 if not archive.exists():raise RuntimeError('补充词典资料尚未安装')
 version=hashlib.sha256(archive.read_bytes()).hexdigest()[:12];path=Path(data)/('reference-'+version+'.sqlite3')
 with LOCK:
  if not path.exists():
   path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.part')
   try:
    with gzip.open(archive,'rb') as src,tmp.open('wb') as dst:shutil.copyfileobj(src,dst)
    with closing(sqlite3.connect(tmp)) as c:
     if c.execute('pragma quick_check').fetchone()[0]!='ok':raise RuntimeError('补充词典资料损坏')
    os.replace(tmp,path)
   finally:
    if tmp.exists():tmp.unlink()
 return sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)

def fetch_json(url):
 # URLs originate only from fixed providers, never from user-supplied hosts.
 with urlopen(Request(url,headers={'User-Agent':'PersonalEnglishLearning/1.0 (personal study)','Accept':'application/json'}),timeout=6) as response:
  raw=response.read(1024*1024+1)
  if len(raw)>1024*1024:raise ValueError('来源返回内容过大')
  return json.loads(raw)

def parse_sentences(payload,word):
 if not isinstance(payload,dict):return []
 pattern=re.compile(r'(?<![a-z])'+re.escape(word)+r'(?![a-z])',re.I);out=[]
 for r in payload.get('data',[]):
  if not isinstance(r,dict):continue
  en=r.get('text','')
  if not isinstance(en,str):continue
  if r.get('lang')!='eng' or r.get('is_unapproved') or not pattern.search(en) or not 2<=len(en.split())<=12:continue
  for tr in sorted([t for t in r.get('translations',[]) if isinstance(t,dict)],key=lambda t:t.get('script')!='Hans'):
   if tr.get('lang')!='cmn' or not tr.get('is_direct') or tr.get('is_unapproved') or not re.search('[\u4e00-\u9fff]',tr.get('text','')):continue
   out.append(dict(en=en,zh=tr['text'],kind='sentence',source='Tatoeba',url='https://tatoeba.org/en/sentences/show/'+str(r['id']),translation_url='https://tatoeba.org/en/sentences/show/'+str(tr['id']),license=' / '.join(dict.fromkeys([r.get('license','CC BY 2.0 FR'),tr.get('license','CC BY 2.0 FR')])),attribution=str(r.get('owner') or 'Tatoeba contributors')+' / '+str(tr.get('owner') or 'Tatoeba contributors')));break
 return out

def search(data,word,online=True):
 word=clean_word(word);items=[];warnings=[];ipa='';forms=[]
 try:
  with closing(reference(data)) as c:
   c.row_factory=sqlite3.Row
   row=c.execute('SELECT * FROM entries WHERE word=?',(word,)).fetchone()
   if row:
    ipa=row['ipa'];forms=[p.split(':',1)[1] for p in row['forms'].split('/') if ':' in p and p.split(':',1)[0] in ('p','d','i','3','r','t','s')]
    items.append(dict(en=row['display'],zh=row['zh'],pos=row['pos'],kind='word' if ' ' not in word else 'phrase',source='ECDICT',url=ECDICT,license='MIT'))
   token=word.split()[0]
   for r in c.execute("SELECT e.* FROM entry_search x JOIN entries e ON e.rowid=x.rowid WHERE entry_search MATCH ? AND instr(e.word,' ')>0 ORDER BY length(e.word),e.word LIMIT 30",('\"'+token+'\"',)):
    if r['word']!=word and re.search(r'(?<![a-z])'+re.escape(word)+r'(?![a-z])',r['word'],re.I):items.append(dict(en=r['display'],zh=r['zh'],kind='phrase',source='ECDICT',url=ECDICT,license='MIT'))
   for r in c.execute('SELECT s.* FROM sentence_search t JOIN sentences s ON s.rowid=t.rowid WHERE sentence_search MATCH ? ORDER BY length(s.en),s.id LIMIT 30',('\"'+token+'\"',)):
    if re.search(r'(?<![a-z])'+re.escape(word)+r'(?![a-z])',r['en'],re.I):items.append(dict(en=r['en'],zh=r['zh'],kind='sentence',source='Tatoeba',url='https://tatoeba.org/en/sentences/show/'+r['id'],translation_url='https://tatoeba.org/en/sentences/show/'+r['zh_id'],license='CC BY 2.0 FR',attribution='Tatoeba contributors'))
 except (OSError,sqlite3.Error,RuntimeError) as e:warnings.append(str(e))
 if online:
  try:
   remote=fetch_json('https://api.dictionaryapi.dev/api/v2/entries/en/'+quote(word,safe=''))
   if isinstance(remote,list) and remote:
    for p in remote[0].get('phonetics',[]):
     if '-us.' in p.get('audio','') and p.get('text'):ipa=p['text'];break
    if not any(i['en']==word for i in items):warnings.append('在线词典找到了该词，但中文释义暂缺；本次不能导入缺少中文释义的词条')
  except (OSError,ValueError,HTTPError,URLError):warnings.append('在线词典暂不可用，已保留本地资料')
  try:
   params=dict(lang='eng',q='"'+word+'"',sort='words',limit=20,word_count='2-12',is_orphan='no',is_unapproved='no',showtrans='matching')
   params.update({'trans:lang':'cmn','trans:is_direct':'yes','trans:is_unapproved':'no'})
   items+=parse_sentences(fetch_json('https://api.tatoeba.org/v1/sentences?'+urlencode(params)),word)
  except (OSError,ValueError,HTTPError,URLError):warnings.append('在线例句暂不可用，已保留本地例句')
 seen=set();result=[];counts={}
 for item in items:
  key=item['en'].strip().casefold().rstrip('.!?')
  if key in seen or counts.get(item['kind'],0)>=(1 if item['kind']=='word' else 8):continue
  if not re.search('[\u4e00-\u9fff]',item['zh']):continue
  item['id']=hashlib.sha256((item['kind']+'|'+item['en']+'|'+item['zh']).encode()).hexdigest()[:24]
  seen.add(key);result.append(item);counts[item['kind']]=counts.get(item['kind'],0)+1
 return dict(word=word,items=result,warnings=warnings,phonetic_reference=ipa,forms=forms,looked_up_at=datetime.now(timezone.utc).isoformat())

def save_preview(c,payload,stamp):
 cached=c.execute(text('SELECT id,payload,created_at FROM lookup_previews WHERE word=:w'),dict(w=payload['word'])).mappings().first()
 pid=str(uuid.uuid4());payload=dict(payload,id=pid)
 c.execute(text('INSERT INTO lookup_previews VALUES(:w,:i,:p,:t) ON CONFLICT(word) DO UPDATE SET id=excluded.id,payload=excluded.payload,created_at=excluded.created_at'),dict(w=payload['word'],i=pid,p=json.dumps(payload,ensure_ascii=False),t=stamp.isoformat()))
 c.execute(text('DELETE FROM lookup_previews WHERE julianday(created_at)<julianday(:t)'),dict(t=(stamp-timedelta(days=7)).isoformat()))
 return payload

def import_items(c,preview_id,selected,stamp):
 row=c.execute(text('SELECT payload,created_at FROM lookup_previews WHERE id=:i'),dict(i=preview_id)).mappings().first()
 if not row or stamp-datetime.fromisoformat(row['created_at'])>timedelta(days=7):raise ValueError('查询预览已过期，请重新查询')
 payload=json.loads(row['payload']);chosen=[i for i in payload['items'] if i['id'] in selected]
 if not chosen or len(chosen)!=len(set(selected)):raise ValueError('请选择预览中有效的内容')
 root=next((i for i in chosen if i['en'].casefold()==payload['word']),None)
 if root is None:raise ValueError('请同时选中查询的词条')
 examples=[dict(en=i['en'],zh=i['zh'],source_url=i['url'],translation_url=i.get('translation_url'),license=i['license']) for i in chosen if i['kind']=='sentence']
 ids=[];root_id=None
 for item in sorted(chosen,key=lambda i:i is not root):
  existing=c.execute(text('SELECT id FROM knowledge WHERE lower(answer)=lower(:a) LIMIT 1'),dict(a=item['en'])).scalar()
  kid=existing or 'lookup-'+hashlib.sha256((item['kind']+'|'+item['en'].casefold()).encode()).hexdigest()[:20]
  if not existing:
   details=dict(entry_type=item['kind'],pos=item.get('pos',''),speech_text=item['en'],usage=item['zh'],examples=examples,forms=payload['forms'] if item is root else [],roots=None,phonetic_reference=payload['phonetic_reference'] if item is root else '',sources=[dict(title=item['source'],url=item['url'],license=item['license'],attribution=item.get('attribution',''))],extensions=[])
   c.execute(text('INSERT INTO knowledge VALUES(:k,:p,:a,:e,:ex)'),dict(k=kid,p=item['zh'],a=item['en'],e=item['zh'],ex=examples[0]['en'] if examples else item['en']))
   c.execute(text('INSERT INTO progress(knowledge_id) VALUES(:k)'),dict(k=kid))
   c.execute(text('INSERT INTO knowledge_details VALUES(:k,:p,1,:t)'),dict(k=kid,p=json.dumps(details,ensure_ascii=False),t=stamp.isoformat()))
  if item is root:root_id=kid
  elif not existing:c.execute(text("INSERT OR IGNORE INTO course_links VALUES(:k,:r,:s,'用户选择的词典和双语语料')"),dict(k=kid,r=root_id,s=3 if item['kind']=='sentence' else 2))
  ids.append(kid)
 return dict(id=root_id,imported_ids=ids)
