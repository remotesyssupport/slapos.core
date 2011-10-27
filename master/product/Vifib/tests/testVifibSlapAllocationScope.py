from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapAllocationScope(TestVifibSlapWebServiceMixin):
  def test_allocation_scope_open_personal(self):
    """Check that computer is open/personal it is only available
    to owner"""
    raise NotImplementedError

  def test_allocation_scope_open_friend(self):
    """Check that computer is open/friend it is only available
    to owner and its friends"""
    raise NotImplementedError

  def test_allocation_scope_open_public(self):
    """Check that computer is open/public it is only available
    to anybody"""
    raise NotImplementedError

  def test_allocation_scope_close(self):
    """Check that computer is close it is not only available
    to anybody"""
    raise NotImplementedError

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapAllocationScope))
  return suite
