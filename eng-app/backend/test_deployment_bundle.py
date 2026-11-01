import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from scripts.export_learning_bundle import export


class TransferBundleTests(unittest.TestCase):
 def test_consistent_snapshot_excludes_sessions_and_test_data(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);data=root/'data';data.mkdir()
   source=sqlite3.connect(data/'learning.db')
   try:
    source.execute('PRAGMA journal_mode=WAL')
    source.execute('CREATE TABLE retention(id TEXT PRIMARY KEY,stability REAL,next_review TEXT)')
    source.execute("INSERT INTO retention VALUES('word',12.5,'2026-11-20')")
    source.commit()
    (data/'auth.db').write_bytes(b'private sessions')
    (data/'learning-test.db').write_bytes(b'test data')
    audio=data/'audio/oxford-us';audio.mkdir(parents=True)
    (audio/'word.mp3').write_bytes(b'audio')
    (audio/'word.json').write_text('{}')
    (audio/'incomplete.tmp').write_bytes(b'incomplete')
    device=data/'audio/device-us';device.mkdir()
    (device/'phrase.wav').write_bytes(b'recorded speech')
    archive=export(root/'private.zip',data,True)
    with zipfile.ZipFile(archive) as z:
     self.assertEqual(set(z.namelist()),{'learning.db','audio/oxford-us/word.mp3','audio/oxford-us/word.json','audio/device-us/phrase.wav'})
     z.extract('learning.db',root/'restored')
    restored=sqlite3.connect(root/'restored/learning.db')
    try:
     self.assertEqual(restored.execute('PRAGMA integrity_check').fetchone()[0],'ok')
     self.assertEqual(restored.execute('SELECT * FROM retention').fetchone(),('word',12.5,'2026-11-20'))
    finally:restored.close()
    with zipfile.ZipFile(export(root/'database-only.zip',data)) as z:
     self.assertEqual(z.namelist(),['learning.db'])
    self.assertEqual(source.execute('SELECT COUNT(*) FROM retention').fetchone()[0],1)
   finally:source.close()

 def test_missing_database_does_not_create_empty_backup(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   with self.assertRaises(ValueError):export(root/'private.zip',root)
   self.assertFalse((root/'private.zip').exists())
