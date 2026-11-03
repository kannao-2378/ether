"""Record teaching exposure separately from verified transfer trials.

Legacy answers remain untouched: absence of trial metadata is not proof of transfer.
"""
import re
from sqlalchemy import text

VERSION=3
TABLES=('teaching_exposures','question_trials')

def key(value):
 return re.sub(r'\s+',' ',value.strip().casefold()).rstrip('.!?。！？ ')

def install(c):
 c.execute(text('CREATE TABLE IF NOT EXISTS teaching_exposures(answer_key TEXT PRIMARY KEY,knowledge_id TEXT,created_at TEXT,source TEXT)'))
 c.execute(text('CREATE TABLE IF NOT EXISTS question_trials(question_id TEXT PRIMARY KEY,mode TEXT NOT NULL,reason TEXT NOT NULL,version INTEGER NOT NULL)'))

def expose(c,kid,stamp,details=None,source='teaching'):
 answer=c.execute(text('SELECT answer FROM knowledge WHERE id=:k'),dict(k=kid)).scalar()
 values=[answer] if answer else []
 for field in ('examples','extensions'):
  for item in (details or {}).get(field,[]) or []:
   if isinstance(item,dict) and item.get('en'):values.append(item['en'])
 for value in values:
  c.execute(text('INSERT OR IGNORE INTO teaching_exposures VALUES(:a,:k,:t,:s)'),dict(a=key(value),k=kid,t=stamp.isoformat(),s=source))

def classify(c,kid,role=None):
 stage=c.execute(text('SELECT stage FROM course_links WHERE knowledge_id=:k'),dict(k=kid)).scalar()
 mode='recall';reason='ordinary practice'
 if role=='transfer' or stage==4:
  answer=c.execute(text('SELECT answer FROM knowledge WHERE id=:k'),dict(k=kid)).scalar() or ''
  exposed=c.execute(text('SELECT 1 FROM teaching_exposures WHERE answer_key=:a'),dict(a=key(answer))).first()
  # A successful genuine trial may later be reviewed; an assisted first attempt cannot.
  proven=c.execute(text("""SELECT 1 FROM answers a JOIN question_trials t ON t.question_id=a.question_id
   WHERE a.knowledge_id=:k AND t.mode IN ('transfer','transfer-review') AND a.correct=1 AND a.revealed=0
   AND COALESCE((SELECT confidence FROM feedback_events f WHERE f.question_id=a.question_id ORDER BY rowid DESC LIMIT 1),a.confidence)='clear'
   AND NOT EXISTS(SELECT 1 FROM spelling_checks s WHERE s.question_id=a.question_id AND s.correct=0)
   AND NOT EXISTS(SELECT 1 FROM test_skips s WHERE s.question_id=a.question_id) LIMIT 1"""),dict(k=kid)).first()
  seen=c.execute(text("""SELECT 1 FROM knowledge k JOIN progress p ON p.knowledge_id=k.id
   WHERE p.introduced=1 AND lower(rtrim(trim(k.answer),'.!?。！？ '))=:a LIMIT 1"""),dict(a=key(answer))).first()
  examples=c.execute(text("""SELECT 1 FROM knowledge k JOIN progress p ON p.knowledge_id=k.id
   LEFT JOIN knowledge_details d ON d.knowledge_id=k.id WHERE p.introduced=1 AND
   (lower(rtrim(trim(k.example),'.!?。！？ '))=:a OR EXISTS(SELECT 1 FROM json_each(d.payload,'$.examples') e
   WHERE lower(rtrim(trim(json_extract(e.value,'$.en')),'.!?。！？ '))=:a)) LIMIT 1"""),dict(a=key(answer))).first()
  exposed=exposed or examples
  mode='transfer-review' if proven else 'recall' if exposed or seen else 'transfer'
  reason='verified variation review' if proven else 'answer previously taught or legacy exposure unknown' if exposed or seen else 'new combination, no recorded teaching exposure'
 return mode,reason

def register(c,qid,kid,role=None):
 old=c.execute(text('SELECT mode FROM question_trials WHERE question_id=:q'),dict(q=qid)).scalar()
 if old:return old
 mode,reason=classify(c,kid,role)
 c.execute(text('INSERT OR IGNORE INTO question_trials VALUES(:q,:m,:r,:v)'),dict(q=qid,m=mode,r=reason,v=VERSION))
 return mode
