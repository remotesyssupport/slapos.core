from Products.ERP5Type.tests.Sequence import SequenceList
import random
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

class TestVifibSlapAllocationScope(TestVifibSlapWebServiceMixin):
  def stepCustomerRegisterNewComputer(self, sequence, **kw):
    sequence['computer_title'] = str(random.random())
    request = self.app.REQUEST
    self.getPortal().portal_skins.changeSkin("Hosting")
    request.set('portal_skin', "Hosting")
    self.portal.web_site_module.hosting.WebSection_registerNewComputer(
      title=sequence['computer_title'])
    self.getPortal().portal_skins.changeSkin("View")
    request.set('portal_skin', "View")

  def stepSetComputerCoordinatesFromComputerTitle(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      title=sequence['computer_title'], portal_type='Computer')

    sequence.edit(
      computer_uid=computer.getUid(),
      computer_reference=computer.getReference(),
    )

  def stepComputerSetAllocationScopeOpenPersonal(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    request = self.app.REQUEST
    self.getPortal().portal_skins.changeSkin("Hosting")
    request.set('portal_skin', "Hosting")

    computer.Computer_updateAllocationScope(allocation_scope='open/personal',
      subject_list=[])

    self.getPortal().portal_skins.changeSkin("View")
    request.set('portal_skin', "View")

  def test_allocation_scope_open_personal(self):
    """Check that computer is open/personal it is only available
    to owner"""
    sequence_list = SequenceList()
    sequence_string = """
      LoginTestVifibCustomer
      CustomerRegisterNewComputer
      Tic
      Logout

      LoginDefaultUser
      SetComputerCoordinatesFromComputerTitle
      Logout

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginTestVifibCustomer
      ComputerSetAllocationScopeOpenPersonal
      Tic
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)
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
