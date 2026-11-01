import tempfile,unittest,wave,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from fastapi.testclient import TestClient
import device_audio,app

def wav(path):
 with wave.open(str(path),'wb') as f:
  f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\x01\x00'*1600)

class DeviceAudioTests(unittest.TestCase):
 def test_concurrent_requests_generate_once_and_repair_corruption(self):
  with tempfile.TemporaryDirectory() as folder:
   def generate(text,path):time.sleep(.02);wav(path)
   with patch.object(device_audio,'synthesize',side_effect=generate) as synth:
    with ThreadPoolExecutor(max_workers=6) as workers:paths=list(workers.map(lambda _:device_audio.get_audio('want to',folder),range(6)))
    self.assertEqual(synth.call_count,1);self.assertEqual(len(set(paths)),1)
    paths[0].write_bytes(b'broken')
    device_audio.get_audio('want to',folder);self.assertEqual(synth.call_count,2)
    self.assertTrue(device_audio.valid(paths[0]))

 def test_failure_leaves_no_incomplete_recording(self):
  with tempfile.TemporaryDirectory() as folder:
   with patch.object(device_audio,'synthesize',side_effect=OSError('unavailable')):
    with self.assertRaises(ValueError):device_audio.get_audio('want to',folder)
   self.assertEqual(list(Path(folder).glob('*')),[])
   for text in ('',' ', 'a'*301):
    with self.assertRaises(ValueError):device_audio.get_audio(text,folder)

 def test_api_only_plays_existing_course_content(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(app,'DATA',Path(folder)),TestClient(app.app) as client:
   target=device_audio.cache_path('want to',Path(folder)/'audio/device-us');target.parent.mkdir(parents=True);wav(target)
   r=client.get('/api/pronunciation/device-us',params={'text_value':'want to'})
   self.assertEqual(r.status_code,200);self.assertTrue(r.content.startswith(b'RIFF'));self.assertIn('audio/wav',r.headers['content-type'])
   with patch.object(device_audio,'get_audio') as generate:
    self.assertEqual(client.get('/api/pronunciation/device-us',params={'text_value':'arbitrary text not in the course'}).status_code,400)
    self.assertEqual(client.get('/api/pronunciation/device-us',params={'text_value':''}).status_code,400)
    generate.assert_not_called()
   with patch.object(device_audio,'get_audio',side_effect=ValueError('engine unavailable')):
    self.assertEqual(client.get('/api/pronunciation/device-us',params={'text_value':'want to'}).status_code,503)
