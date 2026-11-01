"""Summary requests must omit the full knowledge list and history queries."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import create_engine,event
from fastapi.testclient import TestClient
import app
class DashboardSummaryTests(unittest.TestCase):
 def test_small_response_same_counts_without_full_list_queries(self):
  with tempfile.TemporaryDirectory() as folder:
   engine=create_engine('sqlite:///'+str(Path(folder)/'summary.db'));app.initialize(engine)
   statements=[]
   def capture(conn,cursor,statement,parameters,context,executemany):statements.append(statement)
   try:
    with patch.object(app,'real_engine',engine),TestClient(app.app) as client:
     client.post('/api/next')
     full=client.get('/api/dashboard');self.assertEqual(full.status_code,200)
     event.listen(engine,'before_cursor_execute',capture)
     light=client.get('/api/dashboard?summary_only=true');self.assertEqual(light.status_code,200)
     self.assertEqual(light.json(),{k:v for k,v in full.json().items() if k not in ('items','history')})
     self.assertNotIn('items',light.json());self.assertNotIn('history',light.json())
     self.assertLess(len(light.content),1000)
     self.assertLess(len(light.content)*10,len(full.content))
     self.assertFalse(any('SELECT k.*,p.*' in sql or 'ORDER BY a.created_at DESC LIMIT 100' in sql for sql in statements))
   finally:engine.dispose()
if __name__=='__main__':unittest.main()
