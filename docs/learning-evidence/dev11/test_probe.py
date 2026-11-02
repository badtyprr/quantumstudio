"""A crash or unrelated diagnostic must never satisfy a rejection fixture."""
import unittest
from probe import REJECTIONS, expected_rejection

class RejectionTests(unittest.TestCase):
 def test_expected_errors(self):
  for fixture,message in REJECTIONS.items():
   with self.subTest(fixture=fixture):
    self.assertTrue(expected_rejection(fixture,2,message+'\r\n'))
    for code in (0,1,-11,3221225477):
     self.assertFalse(expected_rejection(fixture,code,message))
    self.assertFalse(expected_rejection(fixture,2,'Unrelated failure'))
    self.assertFalse(expected_rejection(fixture,2,message+'\nAdditional error'))
 def test_unknown_fixture(self):
  self.assertFalse(expected_rejection('unknown',2,'error'))

if __name__=='__main__':unittest.main()
