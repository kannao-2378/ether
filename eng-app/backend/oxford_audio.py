"""On-demand Oxford US word audio; no guessing media URLs or bulk crawling."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import quote,urlparse
import re,json,threading

HOST='www.oxfordlearnersdictionaries.com'
_lock=threading.Lock()
class AccessRestricted(ValueError):
 """Stop automated requests instead of retrying access restrictions."""
class PronunciationParser(HTMLParser):
 def __init__(self):super().__init__();self.head=False;self.headword='';self.urls=[];self.word_urls=[];self.stack=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  context=a.get('wd') or (self.stack[-1][1] if self.stack else '')
  if tag not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):self.stack.append((tag,context))
  if tag=='h1':self.head=True
  if 'pron-us' in a.get('class','').split() and a.get('data-src-mp3'):
   self.urls.append(a['data-src-mp3']);self.word_urls.append((context.strip().casefold(),a['data-src-mp3']))
 def handle_endtag(self,tag):
  if tag=='h1':self.head=False
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i][0]==tag:del self.stack[i:];break
 def handle_data(self,data):
  if self.head:self.headword+=data

def download(url,limit):
 if urlparse(url).scheme!='https' or urlparse(url).hostname!=HOST:raise ValueError('音频来源无效')
 with urlopen(Request(url,headers={'User-Agent':'PersonalEnglishLearningSystem/1.0 (local pronunciation cache)'}),timeout=12) as r:
  if urlparse(r.geturl()).hostname!=HOST:raise ValueError('来源跳转无效')
  value=r.read(limit+1)
  if len(value)>limit:raise ValueError('文件过大')
  return value

def candidate_bases(word):
 irregular={'went':'go','gone':'go','drank':'drink','drunk':'drink','ate':'eat','eaten':'eat','bought':'buy','thought':'think','taught':'teach','children':'child','men':'man','women':'woman','feet':'foot','teeth':'tooth','mice':'mouse'}
 candidates=[word]
 if word in irregular:candidates.append(irregular[word])
 if word.endswith('ies'):candidates.append(word[:-3]+'y')
 if word.endswith('s') and not word.endswith('ss'):candidates.append(word[:-1])
 if word.endswith('es'):candidates.append(word[:-2])
 for ending in ('ing','ed'):
  if word.endswith(ending) and len(word)>len(ending)+2:
   stem=word[:-len(ending)];candidates.extend([stem,stem+'e'])
   if len(stem)>1 and stem[-1]==stem[-2]:candidates.append(stem[:-1])
 return list(dict.fromkeys(candidates))[:4]

def get_audio(word,folder):
 word=word.strip().casefold()
 if not re.fullmatch(r"[a-z]+(?:[-'][a-z]+)*",word) or len(word)>64:raise ValueError('牛津音源用于单个英文单词')
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);path=folder/(word+'.mp3')
 with _lock:
  if path.is_file() and path.stat().st_size>0:return path
  last=None
  for base,suffix in ((base,suffix) for base in candidate_bases(word) for suffix in ('','_1','_2')):
   entry='https://'+HOST+'/us/definition/english/'+quote(base+suffix,safe='')
   try:
    parser=PronunciationParser();parser.feed(download(entry,3_000_000).decode('utf-8'))
    urls=[u for label,u in parser.word_urls if '/us_pron/' in u and (label==word or not label and parser.headword.strip().casefold()==word)]
    if not urls:raise ValueError('未找到该词的美式录音')
    audio=download(urls[0],2_000_000)
    if not (audio.startswith(b'ID3') or len(audio)>1 and audio[0]==255 and audio[1]&224==224):raise ValueError('返回内容不是 MP3 音频')
    tmp=path.with_suffix('.tmp');tmp.write_bytes(audio);tmp.replace(path)
    path.with_suffix('.json').write_text(json.dumps(dict(word=word,source='Oxford Learner\'s Dictionaries',accent='en-US',entry_url=entry,audio_url=urls[0]),ensure_ascii=False),encoding='utf-8')
    return path
   except AccessRestricted:raise
   except Exception as e:last=e
  raise ValueError('牛津美式发音暂不可用，请检查网络或稍后重试') from last
