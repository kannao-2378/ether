"""Build a shared target index from exact token sequences, not guessed translations."""
import json,sqlite3,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def words(s):return tuple(re.findall(r"[a-z]+(?:'[a-z]+)?",s.casefold().replace('’',"'")))
def run():
 p=ROOT/'.tools/shared-corpus/shared-sentences.sqlite3';c=sqlite3.connect(p)
 c.executescript('CREATE TABLE IF NOT EXISTS targets(id TEXT PRIMARY KEY,english TEXT,chinese TEXT,stage TEXT,source_kind TEXT);CREATE TABLE IF NOT EXISTS matches(target_id TEXT,en_id INTEGER,PRIMARY KEY(target_id,en_id));CREATE INDEX IF NOT EXISTS matches_sentence ON matches(en_id);')
 b=json.loads((ROOT/'backend/resources/compiled_courses.json').read_text(encoding='utf-8'))
 m=json.loads((ROOT/'backend/resources/mainline_course.json').read_text(encoding='utf-8'))
 targets=[(g['key'],g['english'],g['chinese'],g['unit'],'authored-mainline') for g in m['goals']]+[(e['id'],e['answer'],e['prompt'],None,'existing-dictionary') for e in b['expressions']]
 trie={}
 for target,en,zh,stage,kind in targets:
  c.execute('INSERT OR REPLACE INTO targets VALUES(?,?,?,?,?)',(target,en,zh,stage,kind))
  seq=words(en)
  if not seq:continue
  node=trie
  for w in seq:node=node.setdefault(w,{})
  node.setdefault('',[]).append(target)
 for sid,en in c.execute("SELECT s.id,s.text FROM sentences s WHERE s.lang='eng' AND EXISTS(SELECT 1 FROM pairs p WHERE p.en_id=s.id)").fetchall():
  seq=words(en)
  if not 3<=len(seq)<=18 or '\n' in en:continue
  found=set()
  for i in range(len(seq)):
   node=trie
   for w in seq[i:]:
    if w not in node:break
    node=node[w];found.update(node.get('',[]))
  c.executemany('INSERT OR IGNORE INTO matches VALUES(?,?)',[(t,sid) for t in found])
 c.commit()
 stats=dict(targets=len(targets),targets_with_examples=c.execute('SELECT COUNT(DISTINCT target_id) FROM matches').fetchone()[0],target_sentence_links=c.execute('SELECT COUNT(*) FROM matches').fetchone()[0],mainline_with_examples=c.execute("SELECT COUNT(DISTINCT m.target_id) FROM matches m JOIN targets t ON t.id=m.target_id WHERE t.source_kind='authored-mainline'").fetchone()[0])
 (ROOT/'.tools/shared-corpus/matching-report.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats));c.close()
if __name__=='__main__':run()