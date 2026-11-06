import json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone
from sqlalchemy import create_engine,text
import app,mainline_runtime,shared_examples,curriculum_engine as ce
class SharedCorpusTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name);self.db=create_engine('sqlite:///'+str(self.path/'learner.db'));app.initialize(self.db,with_bulk=False)
  self.bank=self.path/'bank.db';b=sqlite3.connect(self.bank)
  b.executescript('CREATE TABLE sentences(id INTEGER PRIMARY KEY,lang TEXT,text TEXT,author TEXT);CREATE TABLE pairs(en_id INTEGER,zh_id INTEGER);CREATE TABLE matches(target_id TEXT,en_id INTEGER);')
  for i,(en,zh) in enumerate([('I want to drink water.','我想喝水。'),('I want to drink tea.','我想喝茶。'),('I want to drink coffee.','我想喝咖啡。')],1):
   b.execute('INSERT INTO sentences VALUES(?,?,?,?)',(i,'eng',en,'author-en'));b.execute('INSERT INTO sentences VALUES(?,?,?,?)',(i+10,'cmn',zh,'author-zh'));b.execute('INSERT INTO pairs VALUES(?,?)',(i,i+10));b.execute('INSERT INTO matches VALUES(?,?)',('mainline-U09-2',i))
  b.commit();b.close();self.env=patch.dict('os.environ',{'PELS_SENTENCE_BANK':str(self.bank)});self.env.start();self.stamp=datetime(2026,11,6,9,tzinfo=timezone.utc)
  with self.db.begin() as c:
   mainline_runtime.install(c)
   for w in ('I','want','to','drink','water','tea'):
    kid='fixture-'+w;ce.card(c,kid,w,w,'','','','word');c.execute(text('UPDATE progress SET introduced=1,level=3 WHERE knowledge_id=:k'),dict(k=kid))
   c.execute(text("UPDATE progress SET introduced=1,level=3 WHERE knowledge_id='mainline-U09-2'"))
   c.execute(text("INSERT INTO daily_group_tasks VALUES('2026-11-06','mainline-U09-2','review','mainline-U09-2')"))
 def tearDown(self):self.env.stop();self.db.dispose();self.tmp.cleanup()
 def test_plan_is_read_only_and_hides_unknown_vocabulary(self):
  with self.db.connect() as c:
   before=c.execute(text('SELECT COUNT(*) FROM knowledge')).scalar();r=shared_examples.plan(c)
   self.assertEqual(len(r['items']),2);self.assertTrue(all('coffee' not in x['english'] for x in r['items']));self.assertTrue(any('coffee' in x['missing_words'] for x in r['waiting']));self.assertEqual(before,c.execute(text('SELECT COUNT(*) FROM knowledge')).scalar())
 def test_exposure_excluded_and_original_pair_retained(self):
  with self.db.begin() as c:
   c.execute(text("INSERT INTO teaching_exposures VALUES('i want to drink water','fixture','2026-11-06','test')"));r=shared_examples.plan(c)
   self.assertEqual(len(r['items']),1);self.assertEqual(r['items'][0]['zh_id'],12);self.assertEqual(r['items'][0]['en_author'],'author-en')
 def test_preparation_bounded_idempotent_and_keeps_grades(self):
  with self.db.begin() as c:
   before=c.execute(text('SELECT COUNT(*) FROM answers')).scalar();self.assertEqual(shared_examples.prepare(c,self.stamp),2);self.assertEqual(shared_examples.prepare(c,self.stamp),0)
   self.assertEqual(before,c.execute(text('SELECT COUNT(*) FROM answers')).scalar());self.assertEqual(c.execute(text('SELECT COUNT(*) FROM shared_example_links')).scalar(),2)
   self.assertEqual(c.execute(text("SELECT COUNT(*) FROM sentence_combinations WHERE knowledge_id LIKE 'shared-example-%'")).scalar(),2)
 def test_sourced_answer_uses_normal_grading_and_transfer_evidence(self):
  import transfer_evidence
  with self.db.begin() as c:
   shared_examples.prepare(c,self.stamp)
   kid=c.execute(text('SELECT knowledge_id FROM shared_example_links ORDER BY en_id LIMIT 1')).scalar()
   answer=c.execute(text('SELECT answer FROM knowledge WHERE id=:k'),dict(k=kid)).scalar()
   c.execute(text('INSERT INTO questions VALUES(:q,:k,:t,0)'),dict(q='source-proof',k=kid,t=self.stamp.isoformat()))
   c.execute(text("INSERT INTO group_questions VALUES('source-proof','mainline-U09-2','transfer')"))
   transfer_evidence.register(c,'source-proof',kid,'transfer')
  with patch.object(app,'real_engine',self.db),patch.object(app,'now',return_value=self.stamp):
   checked=app.check_spelling(app.SpellingCheck(id='source-check',question_id='source-proof',answer=answer));self.assertTrue(checked['correct'])
   result=app.submit(app.Submission(question_id='source-proof',answer=answer,confidence='clear'));self.assertTrue(result['correct'])
  with self.db.connect() as c:
   mode=c.execute(text("SELECT mode FROM question_trials WHERE question_id='source-proof'")).scalar()
   self.assertEqual(c.execute(text("SELECT independent FROM composition_evidence WHERE question_id='source-proof'")).scalar(),int(mode in ('transfer','transfer-review')))
if __name__=='__main__':unittest.main()
