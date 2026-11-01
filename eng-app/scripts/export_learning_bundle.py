"""Explicit private transfer bundle: consistent SQLite snapshot plus optional audio cache."""
import argparse,sqlite3,tempfile,zipfile
from contextlib import closing
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def export(target,data,with_audio=False):
 data=Path(data);target=Path(target)
 if not (data/'learning.db').is_file():raise ValueError('Learning database not found')
 target.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory() as folder:
  snapshot=Path(folder)/'learning.db'
  with closing(sqlite3.connect((data/'learning.db').resolve().as_uri()+'?mode=ro',uri=True)) as source:
   destination=sqlite3.connect(snapshot)
   try:source.backup(destination)
   finally:destination.close()
  with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
   archive.write(snapshot,'learning.db')
   if with_audio:
    for p in (data/'audio/oxford-us').glob('*'):
     if p.is_file() and p.suffix in ('.mp3','.json'):archive.write(p,'audio/oxford-us/'+p.name)
    for p in (data/'audio/device-us').glob('*.wav'):
     if p.is_file():archive.write(p,'audio/device-us/'+p.name)
 return target
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--data',default=str(ROOT/'backend/data'));p.add_argument('--with-audio',action='store_true');a=p.parse_args();print('PRIVATE learning bundle:',export(a.output,a.data,a.with_audio))
