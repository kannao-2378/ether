import unittest,tempfile
from pathlib import Path
from sqlalchemy import create_engine,text
import app,content
from scheduler import select_next

class ContentTests(unittest.TestCase):
 def setUp(self):
  self.folder=tempfile.TemporaryDirectory();self.engine=create_engine('sqlite:///'+str(Path(self.folder.name)/'content.db'));app.initialize(self.engine)
 def tearDown(self):self.engine.dispose();self.folder.cleanup()
 def test_all_entries_have_structured_metadata(self):
  with self.engine.connect() as c:
   ids=c.execute(text('SELECT id FROM knowledge')).scalars().all()
   for kid in ids:
    d=content.details(c,kid)
    self.assertTrue(d['usage']);self.assertTrue(d['speech_text']);self.assertTrue(d['entry_type']);self.assertTrue(d['examples'])
 def test_words_have_pronunciation_pos_and_no_fabricated_roots(self):
  with self.engine.connect() as c:
   for kid in content.WORDS:
    d=content.details(c,kid)
    for key in ('ipa_us','syllables','stress','pos','definition_en'):self.assertTrue(d[key],(kid,key))
    self.assertTrue(d['examples'][0]['zh'])
   self.assertIsNone(content.details(c,'word-water')['roots'])
   self.assertIn('古法语',content.details(c,'word-enjoy')['roots'])
 def test_six_units_real_items_and_bilingual_examples(self):
  with self.engine.connect() as c:
   course=content.curriculum(c)[0];self.assertEqual(len(course['units']),6)
   for unit in course['units']:
    self.assertEqual(unit['total'],len(next(u[3] for u in content.UNITS if u[0]==unit['id'])))
    for item in unit['items']:
     self.assertTrue(content.details(c,item['id'])['examples'][0]['zh'],item['id'])
 def test_reinstall_preserves_history_and_canonical_answers(self):
  with self.engine.begin() as c:
   c.execute(text("UPDATE progress SET attempts=12,level=3 WHERE knowledge_id='want-to'"))
   before=c.execute(text('SELECT * FROM knowledge ORDER BY id')).all()
   content.install(c);content.install(c)
   self.assertEqual(before,c.execute(text('SELECT * FROM knowledge ORDER BY id')).all())
   self.assertEqual(c.execute(text("SELECT attempts FROM progress WHERE knowledge_id='want-to'")).scalar(),12)
 def test_new_content_uses_curriculum_order(self):
  with self.engine.begin() as c:
   kind,item=select_next(c,app.now(),5,5)
   self.assertEqual((kind,item['id']),('learn','word-drink'))
 def test_lookup_and_export_share_metadata(self):
  previous=app.real_engine;app.real_engine=self.engine;token=app.testing.set(False)
  try:
   self.assertEqual(app.knowledge_content('word-water')['details']['pos'],'n. 名词；本义不可数')
   self.assertEqual(len(app.learning_plan()['curriculum'][0]['units']),6)
   self.assertIn('knowledge_details',app.export()['tables'])
  finally:app.testing.reset(token);app.real_engine=previous
 def test_dictionary_totals_pagination_and_empty_filter(self):
  previous=app.real_engine;app.real_engine=self.engine;token=app.testing.set(False)
  try:
   first=app.dictionary();self.assertEqual(first['total_all'],first['total'])
   self.assertEqual(first['total_pages'],(first['total']+29)//30)
   last=app.dictionary(page=first['total_pages']);self.assertEqual(len(last['items']),first['total']-30*(first['total_pages']-1))
   empty=app.dictionary(q='zzzz-no-result');self.assertEqual(empty['total_pages'],0);self.assertEqual(empty['total'],0);self.assertEqual(empty['total_all'],first['total_all'])
  finally:app.testing.reset(token);app.real_engine=previous

 def test_beginner_notes_are_concrete_and_workflow_is_not_a_definition(self):
  with self.engine.connect() as c:
   for kid,parts in [('drink-water',['drink','water']),('read-books',['read','books']),('learn-english',['learn','English'])]:
    d=content.details(c,kid)
    self.assertNotIn('动作对象',d['structure'])
    self.assertTrue(all(part in d['structure'] for part in parts))
    self.assertEqual(d['sentence_parts'],[])
    self.assertNotIn('use_when',d)
    self.assertFalse(d['variations'])
    self.assertFalse(d['knowledge_points'])
   for kid in ['go-to-school','learn-english','eat-a-meal']:
    d=content.details(c,kid)
    self.assertNotIn('先掌握表达材料',d['usage'])
    self.assertNotIn('先掌握表达材料',str(d['knowledge_points']))
   d=content.details(c,'want-to')
   self.assertIn('want to drink water',d['usage'])
   self.assertNotIn('动词原形',d['usage'])

 def test_expression_phrase_and_sentence_have_concrete_usage_context(self):
  with self.engine.connect() as c:
   for kid in ['want-to','want-to-action','want-to-sentence','enjoy-reading']:
    d=content.details(c,kid)
    self.assertTrue(d['use_when'],kid)
    self.assertTrue(d['variations'],kid)
    self.assertTrue(all(v['en'] and v['zh'] for v in d['variations']))
   d=content.details(c,'want-to-sentence')
   self.assertEqual([p['en'] for p in d['sentence_parts']],['I','want to','drink water'])
   self.assertNotIn('请写出',str(d['sentence_parts']))

if __name__=='__main__':unittest.main()
