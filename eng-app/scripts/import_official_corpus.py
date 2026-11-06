"""Import linked, attributed sentence records into an independent shared corpus."""
import bz2,csv,json,sqlite3,re,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'.tools/shared-corpus'
def tokens(s):return re.findall(r"[a-z]+(?:'[a-z]+)?",s.lower().replace('’',"'"))
def build():
 links=[]
 with bz2.open(BASE/'raw/eng-cmn_links.tsv.bz2','rt',encoding='utf-8') as f:
  for line in f:
   p=line.rstrip('\n').split('\t')
   if len(p)!=2:raise ValueError('Invalid link row')
   links.append(tuple(map(int,p)))
 needed={'eng':{a for a,b in links},'cmn':{b for a,b in links}}
 out=BASE/'shared-sentences.sqlite3';part=BASE/'shared-sentences.build.sqlite3'
 if part.exists():part.unlink()
 c=sqlite3.connect(part)
 try:
  c.executescript('CREATE TABLE sentences(id INTEGER PRIMARY KEY,lang TEXT NOT NULL,text TEXT NOT NULL,author TEXT,created TEXT,modified TEXT);CREATE TABLE pairs(en_id INTEGER,zh_id INTEGER,PRIMARY KEY(en_id,zh_id));CREATE TABLE terms(term TEXT,en_id INTEGER,PRIMARY KEY(term,en_id));CREATE INDEX term_sentence ON terms(en_id);CREATE TABLE manifest(payload TEXT);')
  stats={};ids=set()
  for lang in ('eng','cmn'):
   count=0;malformed=0
   with bz2.open(BASE/f'raw/{lang}_sentences_detailed.tsv.bz2','rt',encoding='utf-8') as f:
    for row in csv.reader(f,delimiter='\t',quoting=csv.QUOTE_NONE):
     if len(row)!=6:malformed+=1;continue
     sid=int(row[0])
     if sid not in needed[lang]:continue
     if row[1]!=lang or not row[2].strip():raise ValueError('Mismatched language or empty text')
     c.execute('INSERT INTO sentences VALUES(?,?,?,?,?,?)',(sid,lang,*row[2:]));ids.add(sid);count+=1
   if malformed:raise ValueError(f'{lang}: {malformed} malformed rows; old corpus not replaced')
   stats[lang]=count;stats[lang+'_malformed']=malformed
  rejected=0
  for a,b in links:
   if a not in ids or b not in ids:rejected+=1;continue
   c.execute('INSERT OR IGNORE INTO pairs VALUES(?,?)',(a,b))
  for sid,value in c.execute("SELECT id,text FROM sentences WHERE lang='eng'").fetchall():
   c.executemany('INSERT OR IGNORE INTO terms VALUES(?,?)',[(t,sid) for t in set(tokens(value))])
  stats.update(direct_pairs=c.execute('SELECT COUNT(*) FROM pairs').fetchone()[0],unresolved_links=rejected,source='https://downloads.tatoeba.org/exports/per_language/',license='CC BY 2.0 FR',publisher_reviewed=False)
  c.execute('INSERT INTO manifest VALUES(?)',(json.dumps(stats),));c.commit()
  assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  assert c.execute("SELECT COUNT(*) FROM pairs p JOIN sentences e ON e.id=p.en_id JOIN sentences z ON z.id=p.zh_id WHERE e.lang!='eng' OR z.lang!='cmn'").fetchone()[0]==0
 finally:c.close()
 os.replace(part,out);(BASE/'import-report.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats))
if __name__=='__main__':build()
