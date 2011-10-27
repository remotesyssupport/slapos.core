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

  def stepCheckComputerAllocationScopeOpenPersonal(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    self.assertEqual(computer.getAllocationScope(), 'open/personal')

  def stepCheckComputerTradeConditionSujectListEmpty(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    trade_condition = computer.getAggregateRelatedValue(
      portal_type='Sale Supply Line').getParentValue()
    self.assertEqual(trade_condition.getSubjectList(), [])

  request_and_install_software = """
      LoginTestVifibCustomer
      RequestSoftwareInstallation
      Tic
      Logout

      SlapLoginCurrentComputer
      ComputerSoftwareReleaseAvailable
      Tic
      SlapLogout
  """

  def stepCheckNoRelatedSalePackingListLineForSoftwareInstance(self, sequence,
    **kw):
    software_instance = self.portal.portal_catalog.getResultValue(
        uid=sequence['software_instance_uid'])
    self.assertEqual(0, len(software_instance.getAggregateRelatedValueList(
          portal_type=self.sale_packing_list_line_portal_type)))

  def stepSetSequenceSlaXmlCurrentComputer(self, sequence, **kw):
    sequence['sla_xml'] = """<?xml version='1.0' encoding='utf-8'?>
<instance>
<parameter id="computer_guid">%s</parameter>
</instance>""" % sequence['computer_reference']

  def test_allocation_scope_open_personal(self):
    """Check that computer is open/personal it is only available
    to owner"""
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string = """
      LoginTestVifibCustomer
      CustomerRegisterNewComputer
      Tic
      Logout

      LoginDefaultUser
      SetComputerCoordinatesFromComputerTitle
      Logout

      SetSequenceSlaXmlCurrentComputer

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerAllocationScopeOpenPersonal
      CheckComputerTradeConditionSujectListEmpty
      Logout
    """ + self.prepare_published_software_release + \
      self.request_and_install_software + """
      # request as owner
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for owner
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # request as someone else
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for owner
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      CheckNoRelatedSalePackingListLineForSoftwareInstance
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

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
