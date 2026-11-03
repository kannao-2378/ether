"""Per-question read caches never survive feedback or teaching exposure."""
import unittest,tempfile
from pathlib import Path
from sqlalchemy import create_engine,text,event
import app,curriculum_engine as ce,transfer_evidence as te,selection_cache as cache
class SelectionCacheTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.tmp.name)/'cache.db'));app.initialize(self.db,with_bulk=False)
 def tearDown(self):self.db.dispose();self.tmp.cleanup()
 def test_repeated_reads_cached_and_new_question_rereads_changed_progress(self):
  with self.db.begin() as c:
   calls=[]
   def track(*args):calls.append(1)
   event.listen(self.db,'before_cursor_execute',track)
   with cache.scope():
    self.assertFalse(ce.known(c,'want-to'));self.assertFalse(ce.known(c,'want-to'))
   self.assertEqual(len(calls),1);event.remove(self.db,'before_cursor_execute',track)
   c.execute(text("UPDATE progress SET introduced=1,level=3 WHERE knowledge_id='want-to'"))
   with cache.scope():self.assertTrue(ce.known(c,'want-to'))
   c.execute(text("UPDATE progress SET level=1 WHERE knowledge_id='want-to'"))
   with cache.scope():self.assertFalse(ce.known(c,'want-to'))
 def test_teaching_invalidates_cached_transfer_classification(self):
  from datetime import datetime,timezone
  with self.db.begin() as c:
   kid=c.execute(text("SELECT knowledge_id FROM curriculum_lessons WHERE goal_id='want-to' AND role='transfer' ORDER BY rowid LIMIT 1")).scalar()
   with cache.scope():
    self.assertEqual(te.classify(c,kid,'transfer')[0],'transfer')
    te.expose(c,kid,datetime.now(timezone.utc))
    self.assertEqual(te.classify(c,kid,'transfer')[0],'recall')
