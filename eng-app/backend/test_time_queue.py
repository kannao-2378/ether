from unittest.mock import patch
from datetime import timedelta
from fsrs import Card
from sqlalchemy import text
from test_scheduler import ScheduleTests
from scheduler import item_due,install_memory
class TimeQueueTests(ScheduleTests):
 def setUp(self):
  super().setUp();install_memory(self.c);self.flag=patch.dict('os.environ',{'PELS_FSRS_TIME_QUEUE':'1'});self.flag.start()
 def tearDown(self):self.flag.stop();super().tearDown()
 def test_fsrs_time_due(self):
  self.answer('forgot');q=self.queue();self.assertEqual(q['version'],6);self.assertEqual(q['gap'],0);self.assertEqual(q['due_sequence'],0)
  card=Card.from_json(self.c.execute(text("SELECT card_json FROM memory_states WHERE knowledge_id='a'")).scalar());self.assertEqual(q['due_at'],card.due.isoformat());self.assertEqual(item_due(self.c,'a',self.t),card.due);self.assertGreater(card.due,self.t)
 def test_good_and_hard_are_real_fsrs_dates(self):
  for rating in ('clear','hard','forgot'):
   self.answer(rating,self.t+timedelta(days=1));self.assertEqual(self.queue()['gap'],0);self.assertIsNotNone(self.queue()['due_at'])
 def test_unseen_has_no_artificial_delay(self):self.assertEqual(item_due(self.c,'unseen',self.t),self.t)