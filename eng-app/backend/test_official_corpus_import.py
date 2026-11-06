from contextlib import closing
import bz2,importlib.util,sqlite3,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('corpus_import',Path(__file__).resolve().parents[1]/'scripts/import_official_corpus.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class OfficialImportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);(self.base/'raw').mkdir();self.old=module.BASE;module.BASE=self.base
  for filename,contents in [('eng_sentences_detailed.tsv.bz2','1\teng\tI read books.\tAlice\t2026-01-01\t2026-01-01\n'),('cmn_sentences_detailed.tsv.bz2','2\tcmn\t我读书。\tBob\t2026-01-01\t2026-01-01\n'),('eng-cmn_links.tsv.bz2','1\t2\n1\t999\n')]:
   (self.base/'raw'/filename).write_bytes(bz2.compress(contents.encode()))
 def tearDown(self):module.BASE=self.old;self.tmp.cleanup()
 def test_exact_ids_authors_and_missing_links(self):
  module.build()
  with closing(sqlite3.connect(self.base/'shared-sentences.sqlite3')) as c:
   self.assertEqual(c.execute('SELECT * FROM pairs').fetchall(),[(1,2)])
   self.assertEqual(c.execute('SELECT author FROM sentences ORDER BY id').fetchall(),[('Alice',),('Bob',)])
 def test_corrupt_download_never_replaces_previous_bank(self):
  path=self.base/'shared-sentences.sqlite3';path.write_bytes(b'previous-bank')
  (self.base/'raw/cmn_sentences_detailed.tsv.bz2').write_bytes(b'corrupt')
  with self.assertRaises(OSError):module.build()
  self.assertEqual(path.read_bytes(),b'previous-bank')
if __name__=='__main__':unittest.main()