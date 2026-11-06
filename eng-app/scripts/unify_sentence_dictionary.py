"""Unify source sentence pairs with dictionary entries; never overwrite scores."""
import hashlib,json,re,sqlite3
from pathlib import Path
from contextlib import closing

def key(en,zh):return (re.sub(r'\s+',' ',en.strip()).casefold().rstrip('.!?'),zh.strip())
def unify(learning,bank):
 with closing(sqlite3.connect(learning)) as c,closing(sqlite3.connect(bank)) as b:
  existing={key(en,zh):kid for kid,en,zh in c.execute('SELECT id,answer,prompt FROM knowledge')}
  c.execute('CREATE TABLE IF NOT EXISTS shared_sentence_catalog(en_id INTEGER,zh_id INTEGER,knowledge_id TEXT NOT NULL,PRIMARY KEY(en_id,zh_id))')
  inserted=0;linked=0
  with c:
   for eid,zid,en,zh,ea,za in b.execute("SELECT p.en_id,p.zh_id,e.text,z.text,e.author,z.author FROM pairs p JOIN sentences e ON e.id=p.en_id JOIN sentences z ON z.id=p.zh_id ORDER BY p.en_id,p.zh_id"):
    norm=key(en,zh);kid=existing.get(norm)
    if kid is None:
     kid='sentence-source-'+hashlib.sha256((norm[0]+'\0'+norm[1]).encode()).hexdigest()[:24]
     c.execute('INSERT OR IGNORE INTO knowledge VALUES(?,?,?,?,?)',(kid,zh,en,'',en))
     c.execute('INSERT OR IGNORE INTO progress(knowledge_id) VALUES(?)',(kid,))
     details=dict(entry_type='sentence',speech_text=en,examples=[dict(en=en,zh=zh,source_url=f'https://tatoeba.org/en/sentences/show/{eid}',translation_url=f'https://tatoeba.org/en/sentences/show/{zid}',attribution=f'Tatoeba: {ea} / {za}',license='CC BY 2.0 FR')],source_note='Tatoeba官方社区语料；原始直接翻译关系，非出版社审定教材')
     c.execute('INSERT OR IGNORE INTO knowledge_details VALUES(?,?,1,datetime(\'now\'))',(kid,json.dumps(details,ensure_ascii=False)))
     existing[norm]=kid;inserted+=1
    if kid.startswith('sentence-source-'):
     details=dict(entry_type='sentence',speech_text=en,examples=[dict(en=en,zh=zh,source_url=f'https://tatoeba.org/en/sentences/show/{eid}',translation_url=f'https://tatoeba.org/en/sentences/show/{zid}',attribution=f'Tatoeba: {ea} / {za}',license='CC BY 2.0 FR')],source_note='Tatoeba官方社区语料；原始直接翻译关系，非出版社审定教材')
     c.execute("UPDATE knowledge_details SET payload=?,version=20 WHERE knowledge_id=?",(json.dumps(details,ensure_ascii=False),kid))
    c.execute('INSERT OR IGNORE INTO shared_sentence_catalog VALUES(?,?,?)',(eid,zid,kid));linked+=1
  assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  return dict(new_dictionary_sentences=inserted,source_pairs_linked=linked,unique_linked_sentences=c.execute('SELECT COUNT(DISTINCT knowledge_id) FROM shared_sentence_catalog').fetchone()[0])
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--learning',required=True);p.add_argument('--bank',required=True);a=p.parse_args();print(json.dumps(unify(a.learning,a.bank)))
