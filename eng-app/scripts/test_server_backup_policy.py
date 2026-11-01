from contextlib import closing
import unittest,tempfile,sqlite3,zipfile,sys
from pathlib import Path
from datetime import datetime,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parent))
from server_backup_policy import run
class PolicyTests(unittest.TestCase):
 def test_change_interval_and_retention(self):
  with tempfile.TemporaryDirectory() as tmp:
   data=Path(tmp)/'data';data.mkdir();folder=Path(tmp)/'backups';db=data/'learning.db'
   with closing(sqlite3.connect(db,isolation_level=None)) as c:c.execute('CREATE TABLE records(value)');c.execute('INSERT INTO records VALUES(1)')
   start=datetime(2026,11,1,3)
   self.assertTrue(run(data,folder,start).startswith('OK'))
   self.assertIn('five days',run(data,folder,start+timedelta(days=4)))
   self.assertIn('no data changes',run(data,folder,start+timedelta(days=5)))
   for days in [6,11,16]:
    with closing(sqlite3.connect(db,isolation_level=None)) as c:c.execute('INSERT INTO records VALUES(?)',(days,))
    self.assertTrue(run(data,folder,start+timedelta(days=days)).startswith('OK'))
    self.assertLessEqual(len(list(folder.glob('*.zip'))),2)
   self.assertEqual(len(list(folder.glob('*.zip'))),2)
 def test_bad_previous_never_prunes(self):
  with tempfile.TemporaryDirectory() as tmp:
   data=Path(tmp)/'data';data.mkdir();folder=Path(tmp)/'backups';folder.mkdir()
   with closing(sqlite3.connect(data/'learning.db',isolation_level=None)) as c:c.execute('CREATE TABLE records(value)')
   bad=folder/'learning-20260101-030000.zip';bad.write_bytes(b'bad')
   with self.assertRaises(zipfile.BadZipFile):run(data,folder,datetime(2026,11,1,3))
   self.assertTrue(bad.exists())
if __name__=='__main__':unittest.main()
