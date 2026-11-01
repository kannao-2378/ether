import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
import oxford_audio

class OxfordAudioTests(unittest.TestCase):
 def test_inflected_form_uses_exact_form_audio_not_lemma(self):
  html=b'<h1>book</h1><div wd="book"><div class="pron-us" data-src-mp3="https://www.oxfordlearnersdictionaries.com/media/english/us_pron/book.mp3"></div></div><div wd="books"><div class="pron-us" data-src-mp3="https://www.oxfordlearnersdictionaries.com/media/english/us_pron/books.mp3"></div></div>'
  def fetch(url,limit):
   if url.endswith('.mp3'):self.assertTrue(url.endswith('/books.mp3'));return b'ID3books'
   if '/books' in url:raise ValueError('404')
   return html
  with tempfile.TemporaryDirectory() as folder,patch('oxford_audio.download',side_effect=fetch):self.assertEqual(oxford_audio.get_audio('books',folder).read_bytes(),b'ID3books')
 def test_us_only_and_cached_playback_without_network(self):
  html=b'<h1>drink</h1><div class="pron-uk" data-src-mp3="https://www.oxfordlearnersdictionaries.com/media/english/uk_pron/test.mp3"></div><div class="sound pron-us" data-src-mp3="https://www.oxfordlearnersdictionaries.com/media/english/us_pron/test.mp3"></div>'
  with tempfile.TemporaryDirectory() as folder:
   with patch('oxford_audio.download',side_effect=[html,b'ID3test']) as request:
    p=oxford_audio.get_audio('DRINK',folder);self.assertEqual(p.read_bytes(),b'ID3test');self.assertIn('/us_pron/',request.call_args[0][0])
   with patch('oxford_audio.download',side_effect=AssertionError('offline')):self.assertEqual(oxford_audio.get_audio('drink',folder),p)
 def test_mismatched_headword_never_plays_another_word(self):
  with tempfile.TemporaryDirectory() as folder,patch('oxford_audio.download',return_value=b'<h1>other</h1><div class="pron-us" data-src-mp3="https://www.oxfordlearnersdictionaries.com/media/english/us_pron/test.mp3"></div>'):
   with self.assertRaises(ValueError):oxford_audio.get_audio('drink',folder)
   self.assertFalse(list(Path(folder).glob('*.mp3')))
 def test_rejects_non_audio_and_unsafe_inputs(self):
  with tempfile.TemporaryDirectory() as folder:
   for word in ('../secret','https://example.com','two words',''):
    with self.assertRaises(ValueError):oxford_audio.get_audio(word,folder)
   with patch('oxford_audio.download',side_effect=[b'<h1>drink</h1><div class="pron-us" data-src-mp3="https://www.oxfordlearnersdictionaries.com/media/english/us_pron/test.mp3"></div>',b'<html>denied</html>']*3):
    with self.assertRaises(ValueError):oxford_audio.get_audio('drink',folder)
   self.assertFalse(list(Path(folder).glob('*.mp3')))

if __name__=='__main__':unittest.main()
