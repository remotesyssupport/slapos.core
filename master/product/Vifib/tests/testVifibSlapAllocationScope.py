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

  def stepComputerSetAllocationScopeEmpty(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    request = self.app.REQUEST
    self.getPortal().portal_skins.changeSkin("Hosting")
    request.set('portal_skin', "Hosting")

    computer.Computer_updateAllocationScope(allocation_scope='',
      subject_list=[])

    self.getPortal().portal_skins.changeSkin("View")
    request.set('portal_skin', "View")

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

  def stepComputerSetAllocationScopeClose(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    request = self.app.REQUEST
    self.getPortal().portal_skins.changeSkin("Hosting")
    request.set('portal_skin', "Hosting")

    computer.Computer_updateAllocationScope(allocation_scope='close',
      subject_list=[])

    self.getPortal().portal_skins.changeSkin("View")
    request.set('portal_skin', "View")

  def stepComputerSetAllocationScopeOpenPublic(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    request = self.app.REQUEST
    self.getPortal().portal_skins.changeSkin("Hosting")
    request.set('portal_skin', "Hosting")

    computer.Computer_updateAllocationScope(allocation_scope='open/public',
      subject_list=[])

    self.getPortal().portal_skins.changeSkin("View")
    request.set('portal_skin', "View")

  def stepCheckComputerAllocationScopeEmpty(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    self.assertEqual(computer.getAllocationScope(), None)

  def stepCheckComputerAllocationScopeOpenFriend(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    self.assertEqual(computer.getAllocationScope(), 'open/friend')

  def stepCheckComputerAllocationScopeClose(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    self.assertEqual(computer.getAllocationScope(), 'close')

  def stepCheckComputerAllocationScopeOpenPersonal(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    self.assertEqual(computer.getAllocationScope(), 'open/personal')

  def stepCheckComputerAllocationScopeOpenPublic(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    self.assertEqual(computer.getAllocationScope(), 'open/public')

  def stepCheckComputerTradeConditionSubjectListEmpty(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    trade_condition = computer.getAggregateRelatedValue(
      portal_type='Sale Supply Line').getParentValue()
    self.assertEqual(trade_condition.getSubjectList(), [''])

  def stepCheckComputerTradeConditionSubjectListTestVifibAdmin(self, sequence,
      **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    trade_condition = computer.getAggregateRelatedValue(
      portal_type='Sale Supply Line').getParentValue()
    self.assertEqual(trade_condition.getSubjectList(),
      ['test_computer_vifib_admin@example.org'])

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
    sequence['requested_filter_dict'] = dict(
      computer_guid=sequence['computer_reference'])

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
      CheckComputerTradeConditionSubjectListEmpty
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

      # fail to instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      CheckNoRelatedSalePackingListLineForSoftwareInstance
      Logout

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

    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepComputerSetAllocationScopeOpenFriendTestVifibAdmin(self, sequence, **kw):
    computer = self.portal.portal_catalog.getResultValue(
      uid=sequence['computer_uid'])
    request = self.app.REQUEST
    self.getPortal().portal_skins.changeSkin("Hosting")
    request.set('portal_skin', "Hosting")

    computer.Computer_updateAllocationScope(allocation_scope='open/friend',
      subject_list=['test_computer_vifib_admin@example.org'])

    self.getPortal().portal_skins.changeSkin("View")
    request.set('portal_skin', "View")
    
  def test_allocation_scope_open_friend(self):
    """Check that computer is open/friend it is only available
    to owner and its friends"""
    self.computer_partition_amount = 3
    sequence_list = SequenceList()
    sequence_string = """
      LoginTestVifibCustomer
      CustomerRegisterNewComputer
      Tic
      Logout

      LoginDefaultUser
      SetComputerCoordinatesFromComputerTitle
      Logout

      LoginTestVifibCustomer
      ComputerSetAllocationScopeOpenFriendTestVifibAdmin
      Tic
      Logout
      SetSequenceSlaXmlCurrentComputer

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerAllocationScopeOpenFriend
      CheckComputerTradeConditionSubjectListTestVifibAdmin
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

      # request as friend
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for friend
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
      LoginTestVifibCustomerA
      PersonRequestSoftwareInstance
      Tic
      Logout

      # fail to instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      CheckNoRelatedSalePackingListLineForSoftwareInstance
      Logout

      # request as friend
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for friend
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_allocation_scope_open_public(self):
    """Check that computer is open/public it is only available
    to anybody"""
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

      LoginTestVifibCustomer
      ComputerSetAllocationScopeOpenPublic
      Tic
      Logout
      SetSequenceSlaXmlCurrentComputer

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerAllocationScopeOpenPublic
      CheckComputerTradeConditionSubjectListEmpty
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

      # instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_allocation_scope_close(self):
    """Check that computer is close it is not only available
    to anybody"""
    sequence_list = SequenceList()
    sequence_string = """
      LoginTestVifibCustomer
      CustomerRegisterNewComputer
      Tic
      Logout

      LoginDefaultUser
      SetComputerCoordinatesFromComputerTitle
      Logout

      LoginTestVifibCustomer
      ComputerSetAllocationScopeClose
      Tic
      Logout
      SetSequenceSlaXmlCurrentComputer

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerAllocationScopeClose
      CheckComputerTradeConditionSubjectListEmpty
      Logout
    """ + self.prepare_published_software_release + \
      self.request_and_install_software + """
      # request as owner
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout

      # fail to instantiate for owner
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      CheckNoRelatedSalePackingListLineForSoftwareInstance
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_allocation_scope_empty(self):
    """Check that computer's allocation scope is not set it is unavailable"""
    sequence_list = SequenceList()
    sequence_string = """
      LoginTestVifibCustomer
      CustomerRegisterNewComputer
      Tic
      Logout

      LoginDefaultUser
      SetComputerCoordinatesFromComputerTitle
      Logout

      LoginTestVifibCustomer
      ComputerSetAllocationScopeEmpty
      Tic
      Logout
      SetSequenceSlaXmlCurrentComputer

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerAllocationScopeEmpty
      CheckComputerTradeConditionSubjectListEmpty
      Logout
    """ + self.prepare_published_software_release + \
      self.request_and_install_software + """
      # request as owner
      LoginTestVifibCustomer
      PersonRequestSoftwareInstance
      Tic
      Logout

      # fail to instantiate for owner
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      CheckNoRelatedSalePackingListLineForSoftwareInstance
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  prepare_open_public_computer = """
      LoginTestVifibCustomer
      CustomerRegisterNewComputer
      Tic
      Logout

      LoginDefaultUser
      SetComputerCoordinatesFromComputerTitle
      Logout

      LoginTestVifibCustomer
      ComputerSetAllocationScopeOpenPublic
      Tic
      Logout
      SetSequenceSlaXmlCurrentComputer

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerAllocationScopeOpenPublic
      CheckComputerTradeConditionSubjectListEmpty
      Logout
    """ + TestVifibSlapWebServiceMixin.prepare_published_software_release \
      + request_and_install_software

  def test_allocation_scope_public_software_instance_request(self):
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string =  self.prepare_open_public_computer + """
      # request as someone else
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # now this computer patrition request new one
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartition
      Tic
      SlapLogout

      LoginDefaultUser
      CheckSoftwareInstanceAndRelatedComputerPartition
      CheckRequestedSoftwareInstanceAndRelatedComputerPartition
      Logout

      SlapLoginCurrentSoftwareInstance
      CheckRequestedComputerPartitionCleanParameterList
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_allocation_scope_personal_software_instance_request(self):
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string =  self.prepare_open_public_computer + """
      # request as someone else
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # change allocation to personal
      LoginTestVifibCustomer
      ComputerSetAllocationScopeOpenPersonal
      Tic
      Logout

      LoginDefaultUser
      CheckComputerAllocationScopeOpenPersonal
      CheckComputerTradeConditionSubjectListEmpty
      Logout

      # now this computer patrition request new one
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNotFoundResponse
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_allocation_scope_friend_software_instance_request(self):
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string =  self.prepare_open_public_computer + """
      # request as friend
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for friend
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
      LoginTestVifibCustomerA
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # change allocation to personal
      LoginTestVifibCustomer
      ComputerSetAllocationScopeOpenFriendTestVifibAdmin
      Tic
      Logout

      LoginDefaultUser
      CheckComputerAllocationScopeOpenFriend
      CheckComputerTradeConditionSubjectListTestVifibAdmin
      Logout

      # now this computer patrition request new one
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNotFoundResponse
      SlapLogout
      
      # now vifib_admin computer partition request new one and suceeds
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)
    raise NotImplementedError

  def test_allocation_scope_close_software_instance_request(self):
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string =  self.prepare_open_public_computer + """
      # request as someone else
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # change allocation to close
      LoginTestVifibCustomer
      ComputerSetAllocationScopeClose
      Tic
      Logout

      LoginDefaultUser
      CheckComputerAllocationScopeClose
      CheckComputerTradeConditionSubjectListEmpty
      Logout

      # now this computer patrition request new one
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNotFoundResponse
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def test_allocation_scope_empty_software_instance_request(self):
    self.computer_partition_amount = 2
    sequence_list = SequenceList()
    sequence_string =  self.prepare_open_public_computer + """
      # request as someone else
      LoginTestVifibAdmin
      PersonRequestSoftwareInstance
      Tic
      Logout

      # instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # change allocation to empty
      LoginTestVifibCustomer
      ComputerSetAllocationScopeEmpty
      Tic
      Logout

      LoginDefaultUser
      CheckComputerAllocationScopeEmpty
      CheckComputerTradeConditionSubjectListEmpty
      Logout

      # now this computer patrition request new one
      SlapLoginCurrentSoftwareInstance
      RequestComputerPartitionNotFoundResponse
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def stepSetSequenceSoftwareInstanceStateStopped(self, sequence, **kw):
    sequence['software_instance_state'] = 'stopped'

  def test_start_computer_partition_allocation_scope_close(self):
    """Check that it is possible to request stop of computer partition even
    if computer is close"""
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

      LoginTestVifibCustomer
      ComputerSetAllocationScopeOpenPublic
      Tic
      Logout

      SetSequenceSlaXmlCurrentComputer
      SetSequenceSoftwareInstanceStateStopped

      SlapLoginCurrentComputer
      FormatComputer
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerAllocationScopeOpenPublic
      CheckComputerTradeConditionSubjectListEmpty
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

      # instantiate for someone else
      LoginDefaultUser
      ConfirmOrderedSaleOrderActiveSense
      Tic
      SetSelectedComputerPartition
      SelectCurrentlyUsedSalePackingListUid
      Logout
      LoginDefaultUser
      CheckComputerPartitionInstanceSetupSalePackingListConfirmed
      Logout

      # confirm instantiation
      SlapLoginCurrentComputer
      SoftwareInstanceAvailable
      Tic
      SlapLogout

      LoginDefaultUser
      SetSelectedComputerPartition
      CheckComputerPartitionInstanceSetupSalePackingListStopped
      CheckComputerPartitionNoInstanceHostingSalePackingList
      Logout

      # close allocation scope of computer
      LoginTestVifibCustomer
      ComputerSetAllocationScopeClose
      Tic
      Logout

      LoginDefaultUser
      CheckComputerAllocationScopeClose
      CheckComputerTradeConditionSubjectListEmpty
      Logout

      # request start and check that it worked
      LoginTestVifibAdmin
      RequestSoftwareInstanceStart
      Tic
      Logout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListConfirmed
      Logout

      SlapLoginCurrentComputer
      SoftwareInstanceStarted
      Tic
      SlapLogout

      LoginDefaultUser
      CheckComputerPartitionInstanceHostingSalePackingListStarted
      Logout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapAllocationScope))
  return suite
