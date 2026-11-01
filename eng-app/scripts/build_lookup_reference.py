"""Build a public reference index; contains no user progress or credentials."""
from pathlib import Path
import csv,json,re,sqlite3,gzip,shutil,tempfile
ROOT=Path(__file__).resolve().parents[1];RES=ROOT/'backend/resources'
def build():
 with tempfile.TemporaryDirectory() as folder:
  path=Path(folder)/'reference.sqlite3';c=sqlite3.connect(path)
  c.executescript('CREATE TABLE entries(word TEXT PRIMARY KEY,display TEXT,zh TEXT,ipa TEXT,pos TEXT,forms TEXT);CREATE VIRTUAL TABLE entry_search USING fts5(word,content=entries,content_rowid=rowid);CREATE TABLE sentences(id TEXT PRIMARY KEY,en TEXT,zh TEXT,zh_id TEXT);CREATE VIRTUAL TABLE sentence_search USING fts5(en,content=sentences,content_rowid=rowid);')
  for r in csv.DictReader((RES/'ecdict/ecdict.csv').open(encoding='utf-8')):
   en=r['word'].strip();zh=r['translation'].replace('\\n','；').strip();tokens=re.findall("[a-z]+(?:[-'][a-z]+)*",en.casefold())
   if not re.fullmatch("[a-zA-Z][a-zA-Z '-]{0,79}",en) or not re.search('[\u4e00-\u9fff]',zh) or len(tokens)>6:continue
   c.execute('INSERT OR IGNORE INTO entries VALUES(?,?,?,?,?,?)',(en.casefold(),en,zh,r['phonetic'],r['pos'],r['exchange']))
  for line in (RES/'tatoeba/train.jsonl').open(encoding='utf-8'):
   r=json.loads(line);en=r.get('eng-txt','');zh=r.get('cmn-txt','');tokens=re.findall("[a-z]+(?:[-'][a-z]+)*",en.casefold())
   if not 2<=len(tokens)<=12 or len(en)>200 or not re.search('[\u4e00-\u9fff]',zh):continue
   c.execute('INSERT OR IGNORE INTO sentences VALUES(?,?,?,?)',(r['eng-id'],en,zh,r['cmn-id']))
  c.execute("INSERT INTO entry_search(entry_search) VALUES('rebuild')");c.execute("INSERT INTO sentence_search(sentence_search) VALUES('rebuild')");c.commit();print('Reference:',c.execute('select count(*) from entries').fetchone()[0],'entries,',c.execute('select count(*) from sentences').fetchone()[0],'sentences');c.execute('vacuum');c.close()
  target=RES/'lookup-reference.sqlite3.gz'
  with path.open('rb') as source,target.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as out:shutil.copyfileobj(source,out)
  print(target,target.stat().st_size)
if __name__=='__main__':build()
