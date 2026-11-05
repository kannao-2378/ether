"""Word-level spelling evidence; never a whole-sentence memory failure."""
from sqlalchemy import text

TABLES=('word_check_requests','word_spelling_difficulties')

def install(c):
 c.execute(text('CREATE TABLE IF NOT EXISTS word_check_requests(id TEXT PRIMARY KEY,question_id TEXT NOT NULL,word_index INTEGER NOT NULL)'))
 c.execute(text('''CREATE TABLE IF NOT EXISTS word_spelling_difficulties(
 question_id TEXT,word_index INTEGER,expected_word TEXT NOT NULL,error_count INTEGER NOT NULL,
 last_at TEXT NOT NULL,practice_id TEXT,PRIMARY KEY(question_id,word_index))'''))

def record(c,request,options,given,stamp):
 # Count only a full-length word with a valid preceding prefix. Partial
 # non-prefix input and invalid preceding words must not accumulate errors.
 i=request.word_index
 candidates=[w for w in options if len(w)>i and w[:i]==given[:i]]
 if not candidates or len(given[i]) not in {len(w[i]) for w in candidates}:return
 inserted=c.execute(text('INSERT OR IGNORE INTO word_check_requests VALUES(:id,:q,:i)'),dict(id=request.id,q=request.question_id,i=i))
 if not inserted.rowcount:return
 expected=candidates[0][i]
 c.execute(text('''INSERT INTO word_spelling_difficulties VALUES(:q,:i,:w,1,:t,NULL)
 ON CONFLICT(question_id,word_index) DO UPDATE SET error_count=error_count+1,last_at=excluded.last_at'''),dict(q=request.question_id,i=i,w=expected,t=stamp.isoformat()))

def enqueue(c,qid,stamp):
 import focus_training
 for row in c.execute(text('SELECT * FROM word_spelling_difficulties WHERE question_id=:q AND error_count>=3 AND practice_id IS NULL'),dict(q=qid)).mappings().all():
  # Reuse an actual dictionary word; never fabricate its meaning or split a phrase.
  kid=c.execute(text("""SELECT k.id FROM knowledge k JOIN knowledge_details d ON d.knowledge_id=k.id
  WHERE lower(k.answer)=:w AND json_extract(d.payload,'$.entry_type')='word' ORDER BY k.rowid LIMIT 1"""),dict(w=row['expected_word'])).scalar()
  if not kid:continue
  gid=focus_training.add(c,kid,stamp,member_ids=[kid])['id']
  c.execute(text('UPDATE word_spelling_difficulties SET practice_id=:g WHERE question_id=:q AND word_index=:i'),dict(g=gid,q=qid,i=row['word_index']))
