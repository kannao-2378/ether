import unittest,tempfile
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
from sqlalchemy import create_engine,text
from urllib.error import URLError
import app,word_lookup as lookup,focus_training
class LookupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=create_engine('sqlite:///'+str(Path(self.tmp.name)/'test.db'));app.initialize(self.db)
  self.clock=datetime(2026,11,1,8,tzinfo=timezone.utc);self.ep=patch.object(app,'real_engine',self.db);self.ep.start();self.tp=patch('app.now',return_value=self.clock);self.tp.start()
 def tearDown(self):self.tp.stop();self.ep.stop();self.db.dispose();self.tmp.cleanup()
 def preview(self):
  data=dict(word='testword',items=[dict(id='root',en='testword',zh='测试词',kind='word',source='ECDICT',url=lookup.ECDICT,license='MIT'),dict(id='sentence',en='This is a testword.',zh='这是一个测试词。',kind='sentence',source='Tatoeba',url='https://tatoeba.org/en/sentences/show/1',license='CC BY 2.0 FR')],forms=[],phonetic_reference='',warnings=[])
  with self.db.begin() as c:return lookup.save_preview(c,data,self.clock)
 def test_import_is_explicit_idempotent_and_does_not_fake_mastery(self):
  p=self.preview()
  with self.db.connect() as c:self.assertEqual(c.execute(text("SELECT COUNT(*) FROM knowledge WHERE answer='testword'")).scalar(),0)
  body=app.LookupImport(preview_id=p['id'],selected=['root','sentence'],train=True);first=app.import_lookup(body);second=app.import_lookup(body);self.assertEqual(first['id'],second['id']);self.assertEqual(first['focus']['id'],second['focus']['id'])
  with self.db.connect() as c:
   self.assertEqual(c.execute(text('SELECT COUNT(*) FROM answers')).scalar(),0)
   self.assertEqual(c.execute(text('SELECT attempts FROM progress WHERE knowledge_id=:k'),dict(k=first['id'])).scalar(),0)
   self.assertEqual(c.execute(text('SELECT COUNT(*) FROM group_members WHERE group_id=:g'),dict(g=first['focus']['id'])).scalar(),2)
 def test_reject_forged_selection_or_missing_root(self):
  p=self.preview()
  for ids in [['not-in-preview'],['sentence']]:
   with self.assertRaises(app.HTTPException):app.import_lookup(app.LookupImport(preview_id=p['id'],selected=ids))
 def test_cache_avoids_repeated_network(self):
  self.preview()
  with patch.object(lookup,'search',side_effect=AssertionError('Network should not run')):self.assertTrue(app.lookup_word(app.LookupQuery(word='testword'))['cached'])
 def test_exact_word_and_direct_translation_filter(self):
  def sentence(en,number,direct=True):return dict(id=number,text=en,lang='eng',translations=[dict(id=10+number,text='这是例句',lang='cmn',is_direct=direct)])
  rows=lookup.parse_sentences(dict(data=[sentence('Practice makes perfect.',1),sentence('It is practical.',2),sentence('A practical idea works.',3,False)]),'practical');self.assertEqual(len(rows),1);self.assertEqual(rows[0]['en'],'It is practical.')
 def test_input_validation(self):
  for word in ['https://evil.test','../test','中文','a'*81]:
   with self.assertRaises(ValueError):lookup.clean_word(word)
 def test_offline_reference_and_provider_failure_return_real_chinese(self):
  with patch.object(lookup,'fetch_json',side_effect=URLError('offline')):
   result=lookup.search(Path(app.DATA)/'test-reference','resilient')
  self.assertTrue(any(i['en']=='resilient' and '弹' in i['zh'] for i in result['items']));self.assertTrue(result['warnings'])
