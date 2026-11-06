"""Fetch official Tatoeba bulk files, sequentially; never crawl sentence pages."""
import bz2,hashlib,json,time,urllib.request,urllib.error,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'.tools/shared-corpus/raw'
FILES=[('eng','eng_sentences_detailed.tsv.bz2'),('cmn','cmn_sentences_detailed.tsv.bz2'),('eng','eng-cmn_links.tsv.bz2')]
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def run():
 DEST.mkdir(parents=True,exist_ok=True);manifest=[]
 for lang,name in FILES:
  u=f'https://downloads.tatoeba.org/exports/per_language/{lang}/{name}';p=DEST/name
  meta=p.with_suffix(p.suffix+'.json')
  if p.exists() and meta.exists() and json.loads(meta.read_text())['sha256']==digest(p):
   manifest.append(json.loads(meta.read_text()));print('cached',name,flush=True);continue
  part=p.with_suffix(p.suffix+'.part')
  try:
   req=urllib.request.Request(u,headers={'User-Agent':'PersonalEnglishLearning/1.0 (official bulk export downloader)'})
   with urllib.request.urlopen(req,timeout=120) as response,part.open('wb') as f:
    headers=dict(response.headers)
    while True:
     b=response.read(1024*1024)
     if not b:break
     f.write(b)
   # Fully decompress, detecting truncation/CRC errors before publishing the file.
   count=0
   with bz2.open(part,'rt',encoding='utf-8') as f:
    for line in f:count+=1
   item=dict(url=u,file=name,sha256=digest(part),bytes=part.stat().st_size,rows=count,retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),last_modified=headers.get('Last-Modified'),license='Tatoeba standard sentence export: CC BY 2.0 FR; attribution via sentence author/id')
   part.replace(p);meta.write_text(json.dumps(item,indent=2));manifest.append(item);print('downloaded',name,item['bytes'],'bytes',count,'rows',flush=True)
  except urllib.error.HTTPError as e:
   if e.code in (403,429):raise SystemExit(f'Server returned {e.code}; stopped without bypass or rapid retries')
   raise
  time.sleep(1)
 (DEST.parent/'download-manifest.json').write_text(json.dumps(manifest,indent=2));return manifest
if __name__=='__main__':run()