import unittest
from unittest.mock import patch
import app,transfer
class SentenceShapeTests(unittest.TestCase):
 def test_options_keep_supported_alternatives(self):
  self.assertTrue(transfer.grade('want-to-transfer-eat','i want to have a meal','I want to eat.')['correct'])
  self.assertFalse(transfer.grade('x','I go school','I go to school.')['correct'])
 def test_shape_exposes_lengths_only(self):
  with patch('app.content.details',return_value={}):
   hint=app.answer_hint(None,dict(id='want-to-transfer-eat',answer='I want to eat.'))
  self.assertEqual(hint['word_lengths'],[1,4,2,3]);self.assertIn([1,4,2,4,1,4],hint['answer_shapes'])
  self.assertNotIn('answer',hint)
 def test_custom_options_and_punctuation(self):
  with patch('app.content.details',return_value={'accepted_answers':["I'm ready!",'I am ready.']}):
   hint=app.answer_hint(None,dict(id='custom',answer="I'm ready!"))
  self.assertEqual(hint['answer_shapes'],[[3,5],[1,2,5]])
