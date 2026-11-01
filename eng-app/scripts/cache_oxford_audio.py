"""Single-worker, resumable Oxford audio queue; stops on restrictions, never bypasses them."""
import argparse,json,re,sqlite3,sys,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.error import HTTPError,URLError

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import oxford_audio

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',action='store_true');p.add_argument('--limit',type=int,default=0);a=p.parse_args()
 folder=ROOT/'backend/data/audio/oxford-us';folder.mkdir(parents=True,exist_ok=True)
 log=ROOT/'.tools/oxford-audio-download.jsonl'
 with sqlite3.connect('file:'+str(ROOT/'backend/data/learning.db')+'?mode=ro',uri=True) as c:
  words=list(dict.fromkeys(r[0].strip().casefold() for r in c.execute('SELECT k.answer FROM knowledge k JOIN progress p ON p.knowledge_id=k.id ORDER BY p.introduced DESC,k.rowid') if re.fullmatch(r"[A-Za-z]+(?:[-'][A-Za-z]+)*",r[0].strip()) and len(r[0].strip())<=64))
 pending=[w for w in words if not (folder/(w+'.mp3')).is_file()]
 print(json.dumps(dict(total=len(words),cached=len(words)-len(pending),pending=len(pending))),flush=True)
 if a.plan:return
 original=oxford_audio.download;last=[0.0]
 def download(url,limit):
  time.sleep(max(0,.2-(time.monotonic()-last[0])));last[0]=time.monotonic()
  try:data=original(url,limit)
  except HTTPError as e:
   if e.code==404:raise
   raise oxford_audio.AccessRestricted('HTTP '+str(e.code)+'; queue stopped') from e
  except URLError as e:raise oxford_audio.AccessRestricted('Network error; queue stopped: '+str(e.reason)) from e
  if any(marker in data.lower() for marker in (b'<title>just a moment',b'<title>access denied',b'<title>verify you are human')):
   raise oxford_audio.AccessRestricted('Access challenge; queue stopped')
  return data
 oxford_audio.download=download
 count=0
 with log.open('a',encoding='utf-8') as f:
  def record(**value):
   value['time']=datetime.now(timezone.utc).isoformat();f.write(json.dumps(value,ensure_ascii=False)+'\n');f.flush();print(json.dumps(value,ensure_ascii=False),flush=True)
  for word in pending[:a.limit or None]:
   try:path=oxford_audio.get_audio(word,folder)
   except oxford_audio.AccessRestricted as e:
    record(status='stopped',word=word,reason=str(e),downloaded=count);return 2
   except ValueError as e:
    record(status='missing',word=word,reason=str(e));continue
   count+=1;record(status='cached',word=word,bytes=path.stat().st_size,downloaded=count)
   if count%5==0:time.sleep(3)
  record(status='complete',downloaded=count)
 return 0

if __name__=='__main__':sys.exit(main())
