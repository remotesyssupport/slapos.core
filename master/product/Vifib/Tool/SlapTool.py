# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010-2011 Nexedi SA and Contributors. All Rights Reserved.
#                    Łukasz Nowak <luke@nexedi.com>
#                    Romain Courteaud <romain@nexedi.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from AccessControl import ClassSecurityInfo
from AccessControl import Unauthorized
from Products.ERP5Type.UnrestrictedMethod import UnrestrictedMethod
from Products.ERP5Security.ERP5UserManager import SUPER_USER
from OFS.Traversable import NotFound
from Products.DCWorkflow.DCWorkflow import ValidationFailed
from Products.ERP5Type.Globals import InitializeClass
from Products.ERP5Type.Tool.BaseTool import BaseTool
from Products.ZSQLCatalog.SQLCatalog import Query, ComplexQuery
from Products.ERP5Type import Permissions
from lxml import etree
try:
  from slapos.slap.slap import Computer
  from slapos.slap.slap import ComputerPartition as SlapComputerPartition
  from slapos.slap.slap import SoftwareInstance
  from slapos.slap.slap import SoftwareRelease
except ImportError:
  # Do no prevent instance from starting
  # if libs are not installed
  class Computer:
    def __init__(self):
      raise ImportError
  class SlapComputerPartition:
    def __init__(self):
      raise ImportError
  class SoftwareInstance:
    def __init__(self):
      raise ImportError
  class SoftwareRelease:
    def __init__(self):
      raise ImportError

from zLOG import LOG, INFO
import xml_marshaller
import StringIO
import pkg_resources
from Products.Vifib.Conduit import VifibConduit
class SoftwareInstanceNotReady(Exception):
  pass

def convertToREST(function):
  """
  Wrap the method to create a log entry for each invocation to the zope logger
  """
  def wrapper(self, *args, **kwd):
    """
    Log the call, and the result of the call
    """
    try:
      retval = function(self, *args, **kwd)
    except (ValueError, AttributeError), log:
      LOG('SlapTool', INFO, 'Converting ValueError to NotFound, real error:',
          error=True)
      raise NotFound(log)
    except SoftwareInstanceNotReady, log:
      self.REQUEST.response.setStatus(408)
      return self.REQUEST.response
    except ValidationFailed:
      LOG('SlapTool', INFO, 'Converting ValidationFailed to ValidationFailed,'\
        ' real error:',
          error=True)
      raise ValidationFailed

    self.REQUEST.response.setHeader('Content-Type', 'text/xml')
    return '%s' % retval
  wrapper.__doc__ = function.__doc__
  return wrapper

_MARKER = []

class SlapTool(BaseTool):
  """SlapTool"""

  # TODO:
  #   * catch and convert exceptions to HTTP codes (be restful)

  id = 'portal_slap'
  meta_type = 'ERP5 Slap Tool'
  portal_type = 'Slap Tool'
  security = ClassSecurityInfo()
  allowed_types = ()

  security.declarePrivate('manage_afterAdd')
  def manage_afterAdd(self, item, container) :
    """Init permissions right after creation.

    Permissions in slap tool are simple:
     o Each member can access the tool.
     o Only manager can view and create.
     o Anonymous can not access
    """
    item.manage_permission(Permissions.AddPortalContent,
          ['Manager'])
    item.manage_permission(Permissions.AccessContentsInformation,
          ['Member', 'Manager'])
    item.manage_permission(Permissions.View,
          ['Manager',])
    BaseTool.inheritedAttribute('manage_afterAdd')(self, item, container)

  ####################################################
  # Public GET methods
  ####################################################

  security.declareProtected(Permissions.AccessContentsInformation,
    'getComputerInformation')
  def getComputerInformation(self, computer_id):
    """Returns marshalled XML of all needed information for computer

    Includes Software Releases, which may contain Software Instances.

    Reuses slap library for easy marshalling.
    """
    self.REQUEST.response.setHeader('Content-Type', 'text/xml')
    slap_computer = Computer(computer_id)
    parent_uid = self._getComputerUidByReference(computer_id)

    slap_computer._computer_partition_list = []
    slap_computer._software_release_list = \
         self._getSoftwareReleaseValueListForComputer(computer_id)
    for computer_partition in self.getPortalObject().portal_catalog(
                    parent_uid=parent_uid,
                    portal_type="Computer Partition"):
      slap_computer._computer_partition_list.append(
          self._getSlapPartitionByPackingList(computer_partition.getObject()))
    return xml_marshaller.xml_marshaller.dumps(slap_computer)

  security.declareProtected(Permissions.AccessContentsInformation,
    'getComputerPartitionCertificate')
  def getComputerPartitionCertificate(self, computer_id, computer_partition_id):
    """Method to fetch certificate"""
    self.REQUEST.response.setHeader('Content-Type', 'text/xml')
    software_instance = self._getSoftwareInstanceForComputerPartition(
      computer_id, computer_partition_id)
    certificate_dict = dict(
      key=software_instance.getSslKey(),
      certificate=software_instance.getSslCertificate()
    )
    return xml_marshaller.xml_marshaller.dumps(certificate_dict)

  ####################################################
  # Public POST methods
  ####################################################

  security.declareProtected(Permissions.AccessContentsInformation,
    'setComputerPartitionConnectionXml')
  def setComputerPartitionConnectionXml(self, computer_id,
                                        computer_partition_id,
                                        connection_xml, slave_reference=None):
    """
    Set instance parameter informations on the slagrid server
    """
    # When None is passed in POST, it is converted to string
    if slave_reference is not None and slave_reference.lower() == "none":
      slave_reference = None
    return self._setComputerPartitionConnectionXml(computer_id,
                                                   computer_partition_id,
                                                   connection_xml,
                                                   slave_reference)

  security.declareProtected(Permissions.AccessContentsInformation,
    'supplySupply')
  def supplySupply(self, url, computer_id):
    """
    Request Software Release installation
    """
    return self._supplySupply(url, computer_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'buildingSoftwareRelease')
  def buildingSoftwareRelease(self, url, computer_id):
    """
    Reports that Software Release is being build
    """
    return self._buildingSoftwareRelease(url, computer_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'availableSoftwareRelease')
  def availableSoftwareRelease(self, url, computer_id):
    """
    Reports that Software Release is available
    """
    return self._availableSoftwareRelease(url, computer_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'softwareReleaseError')
  def softwareReleaseError(self, url, computer_id, error_log):
    """
    Add an error for a software Release workflow
    """
    return self._softwareReleaseError(url, computer_id, error_log)

  security.declareProtected(Permissions.AccessContentsInformation,
    'buildingComputerPartition')
  def buildingComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is being build
    """
    return self._buildingComputerPartition(computer_id, computer_partition_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'availableComputerPartition')
  def availableComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is available
    """
    return self._availableComputerPartition(computer_id, computer_partition_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'softwareInstanceError')
  def softwareInstanceError(self, computer_id,
                            computer_partition_id, error_log):
    """
    Add an error for the software Instance Workflow
    """
    return self._softwareInstanceError(computer_id, computer_partition_id,
                                       error_log)

  security.declareProtected(Permissions.AccessContentsInformation,
    'softwareInstanceBang')
  def softwareInstanceBang(self, computer_id,
                            computer_partition_id, message):
    """
    Fire up bang on this Software Instance
    """
    return self._softwareInstanceBang(computer_id, computer_partition_id,
                                       message)

  security.declareProtected(Permissions.AccessContentsInformation,
    'startedComputerPartition')
  def startedComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is started
    """
    return self._startedComputerPartition(computer_id, computer_partition_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'stoppedComputerPartition')
  def stoppedComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is stopped
    """
    return self._stoppedComputerPartition(computer_id, computer_partition_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'destroyedComputerPartition')
  def destroyedComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is destroyed
    """
    return self._destroyedComputerPartition(computer_id, computer_partition_id)

  security.declareProtected(Permissions.AccessContentsInformation,
    'requestComputerPartition')
  def requestComputerPartition(self, computer_id=None,
      computer_partition_id=None, software_release=None, software_type=None,
      partition_reference=None, partition_parameter_xml=None,
      filter_xml=None, state=None, shared_xml=_MARKER):
    """
    Asynchronously requests creation of computer partition for assigned
    parameters

    Returns XML representation of partition with HTTP code 200 OK

    In case if this request is still being processed data contain
    "Computer Partition is being processed" and HTTP code is 408 Request Timeout

    In any other case returns not important data and HTTP code is 403 Forbidden
    """
    return self._requestComputerPartition(computer_id, computer_partition_id,
        software_release, software_type, partition_reference,
        shared_xml, partition_parameter_xml, filter_xml, state)

  security.declareProtected(Permissions.AccessContentsInformation,
    'useComputer')
  def useComputer(self, computer_id, use_string):
    """Entry point to reporting usage of a computer."""
    #We retrieve XSD model
    try:
      computer_consumption_model = \
        pkg_resources.resource_string(
          'slapos.slap',
          'doc/computer_consumption.xsd')
    except IOError:
      computer_consumption_model = \
        pkg_resources.resource_string(
          __name__,
          '../../../../slapos/slap/doc/computer_consumption.xsd')

    if self._validateXML(use_string, computer_consumption_model):
      vifib_conduit_instance = VifibConduit.VifibConduit()

      #We create the SPL
      vifib_conduit_instance.addNode(
        object=self, 
        xml=use_string, 
        computer_id=computer_id)
    else:
      raise NotImplementedError("XML file sent by the node is not valid !")

    return 'Content properly posted.'

  @convertToREST
  def _computerBang(self, computer_id, message):
    """
    Fire up bung on Computer
    """
    return self._getComputerDocument(computer_id).reportComputerBang(
                                     comment=message)

  security.declareProtected(Permissions.AccessContentsInformation,
    'computerBang')
  def computerBang(self, computer_id, message):
    """
    Fire up bang on this Software Instance
    """
    return self._computerBang(computer_id, message)

  security.declareProtected(Permissions.AccessContentsInformation,
    'loadComputerConfigurationFromXML')
  def loadComputerConfigurationFromXML(self, xml):
    "Load the given xml as configuration for the computer object"
    computer_dict = xml_marshaller.xml_marshaller.loads(xml)
    computer = self._getComputerDocument(computer_dict['reference'])
    computer.Computer_updateFromDict(computer_dict)
    return 'Content properly posted.'

  security.declareProtected(Permissions.AccessContentsInformation,
    'useComputerPartition')
  def useComputerPartition(self, computer_id, computer_partition_id,
    use_string):
    """Warning : deprecated method."""
    computer_document = self._getComputerDocument(computer_id)
    computer_partition_document = self._getComputerPartitionDocument(
      computer_document.getReference(), computer_partition_id)
    # easy way to start to store usage messages sent by client in related Web
    # Page text_content...
    self._reportUsage(computer_partition_document, use_string)
    return """Content properly posted.
              WARNING : this method is deprecated. Please use useComputer."""

  security.declareProtected(Permissions.AccessContentsInformation,
    'registerComputerPartition')
  def registerComputerPartition(self, computer_reference,
                                computer_partition_reference):
    """
    Registers connected representation of computer partition and
    returns Computer Partition class object
    """
    # Try to get the computer partition to raise an exception if it doesn't
    # exist
    self._getComputerPartitionDocument(
          computer_reference, computer_partition_reference)
    return xml_marshaller.xml_marshaller.dumps(
        SlapComputerPartition(computer_reference,
        computer_partition_reference))

  ####################################################
  # Internal methods
  ####################################################

  def _validateXML(self, to_be_validated, xsd_model):
    """Will validate the xml file"""
    #We parse the XSD model
    xsd_model = StringIO.StringIO(xsd_model)
    xmlschema_doc = etree.parse(xsd_model)
    xmlschema = etree.XMLSchema(xmlschema_doc)

    string_to_validate = StringIO.StringIO(to_be_validated)

    try:
      document = etree.parse(string_to_validate)
    except (etree.XMLSyntaxError, etree.DocumentInvalid) as e:
      LOG('SlapTool::_validateXML', INFO, 
        'Failed to parse this XML reports : %s\n%s' % \
          (to_be_validated, _formatXMLError(e)))
      return False

    if xmlschema.validate(document):
      return True

    return False

  def _instanceXmlToDict(self, xml):
    result_dict = {}
    if xml is not None and xml != '':
      tree = etree.fromstring(xml.encode('utf-8'))
      for element in tree.findall('parameter'):
        key = element.get('id')
        value = result_dict.get(key, None)
        if value is not None:
          value = value + ' ' + element.text
        else:
          value = element.text
        result_dict[key] = value
    return result_dict

  def _getSlapPartitionByPackingList(self, computer_partition_document):
    computer = computer_partition_document
    portal = self.getPortalObject()
    portal_preferences = portal.portal_preferences
    while computer.getPortalType() != 'Computer':
      computer = computer.getParentValue()
    computer_id = computer.getReference()
    slap_partition = SlapComputerPartition(computer_id,
                                computer_partition_document.getReference())

    slap_partition._software_release_document = None
    slap_partition._requested_state = 'destroyed'
    slap_partition._need_modification = 0

    update_movement = self._getSalePackingListLineForComputerPartition(
      computer_partition_document, service_uid_list=[portal.restrictedTraverse(portal_preferences.getPreferredInstanceUpdateResource()).getUid()])
    if update_movement is not None:
      if update_movement.getSimulationState() != 'confirmed':
        # only confirmed update movements are interesting
        update_movement = None
    movement = self._getSalePackingListLineForComputerPartition(
                                           computer_partition_document)
    if movement is not None:
      software_release_document = \
              movement.getAggregateValue(portal_type='Software Release')
      slap_partition._software_release_document =  SoftwareRelease(
            software_release=software_release_document.getUrlString(),
            computer_guid=computer_id)
      parameter_dict = self._getSalePackingListLineAsSoftwareInstance(
                                                       movement)
      # software instance has to define an xml parameter
      slap_partition._parameter_dict = self._instanceXmlToDict(
        parameter_dict.pop('xml'))
      slap_partition._connection_dict = self._instanceXmlToDict(
        parameter_dict.pop('connection_xml'))
      for slave_instance_dict in parameter_dict.get("slave_instance_list", []):
        if slave_instance_dict.has_key("connection_xml"):
          slave_instance_dict.update(self._instanceXmlToDict(
            slave_instance_dict.pop("connection_xml")))
        if slave_instance_dict.has_key("xml"):
          slave_instance_dict.update(self._instanceXmlToDict(
            slave_instance_dict.pop("xml")))
      slap_partition._parameter_dict.update(parameter_dict)

      # Apply state and buildout run conditions
      if movement.getResource() == \
              portal_preferences.getPreferredInstanceSetupResource():

        if movement.getSimulationState() in ('confirmed', 'started',):
          slap_partition._requested_state = 'stopped'
          slap_partition._need_modification = 1
        elif movement.getSimulationState() == 'stopped':
          slap_partition._requested_state = 'stopped'
          if update_movement is not None:
            slap_partition._need_modification = 1
        elif movement.getSimulationState() == 'delivered':
          slap_partition._requested_state = 'destroyed'
        else:
          raise NotImplementedError, "Unexpected state %s" % \
                                     movement.getSimulationState()

      elif movement.getResource() == \
              portal_preferences.getPreferredInstanceHostingResource():
        if movement.getSimulationState() == 'confirmed':
          slap_partition._requested_state = 'started'
          slap_partition._need_modification = 1
        elif movement.getSimulationState() == 'started':
          slap_partition._requested_state = 'started'
          slap_partition._need_modification = \
            self._hasSlaveInstanceNeedModification(computer_partition_document)
          if update_movement is not None:
            slap_partition._need_modification = 1
        elif movement.getSimulationState() == 'stopped':
          slap_partition._requested_state = 'stopped'
          slap_partition._need_modification = 1
        elif movement.getSimulationState() == 'delivered':
          slap_partition._requested_state = 'stopped'
          if update_movement is not None:
            slap_partition._need_modification = 1
        else:
          raise NotImplementedError, "Unexpected state %s" % \
                                     movement.getSimulationState()

      elif movement.getResource() == \
              portal_preferences.getPreferredInstanceCleanupResource():

        if movement.getSimulationState() in ('confirmed', 'started',
            'stopped'):
          slap_partition._need_modification = 1

      else:
        raise NotImplementedError, "Unexpected resource%s" % \
                                   movement.getResource()
    return slap_partition

  def _hasSlaveInstanceNeedModification(self, computer_partition_document):
    """
      Check if modification is needed for...
    """
    portal = self.getPortalObject()
    portal_preferences = portal.portal_preferences
       
    hosting_service = portal.restrictedTraverse(
       portal_preferences.getPreferredInstanceHostingResource())

    setup_service = portal.restrictedTraverse(
       portal_preferences.getPreferredInstanceSetupResource())

    hosting_query = ComplexQuery(Query(aggregate_portal_type="Slave Instance"),
      Query(aggregate_relative_url=computer_partition_document.getRelativeUrl()),
      # Search only for Confirmed and Stopped, the only one states that require
      # buildout be re-updated.
      Query(simulation_state=["confirmed", "stopped"]),
      Query(default_resource_uid=hosting_service.getUid()),
      operator="AND")

    setup_query = ComplexQuery(Query(aggregate_portal_type="Slave Instance"),
      Query(aggregate_relative_url=computer_partition_document.getRelativeUrl()),
      Query(simulation_state=["confirmed", "started"]),
      Query(default_resource_uid=setup_service.getUid()),
      operator="AND")

    query = ComplexQuery(hosting_query, setup_query, operator="OR")

    # Use getTrackingList
    catalog_result = portal.portal_catalog(
      portal_type='Sale Packing List Line',
      sort_on=(('movement.start_date', 'DESC'),),
      limit=1,
      query=query)

    return len(catalog_result)

  @convertToREST
  def _supplySupply(self, url, computer_id):
    """
    Request Software Release installation
    """
    computer_document = self._getComputerDocument(computer_id)
    computer_document.requestSoftwareReleaseInstallation(
      software_release_url=url)

  @convertToREST
  def _buildingSoftwareRelease(self, url, computer_id):
    """
    Reports that Software Release is being build
    """
    computer_document = self._getComputerDocument(computer_id)
    computer_document.startSoftwareReleaseInstallation(
      software_release_url=url)

  @convertToREST
  def _availableSoftwareRelease(self, url, computer_id):
    """
    Reports that Software Release is available
    """
    computer_document = self._getComputerDocument(computer_id)
    computer_document.stopSoftwareReleaseInstallation(software_release_url=url)

  @convertToREST
  def _softwareReleaseError(self, url, computer_id, error_log):
    """
    Add an error for a software Release workflow
    """
    computer_document = self._getComputerDocument(computer_id)
    computer_document.reportSoftwareReleaseInstallationError(
                                     comment=error_log,
                                     software_release_url=url)

  @convertToREST
  def _buildingComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is being build
    """
    return self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id).startComputerPartitionInstallation()

  @convertToREST
  def _availableComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is available
    """
    return self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id).stopComputerPartitionInstallation()

  @convertToREST
  def _softwareInstanceError(self, computer_id,
                            computer_partition_id, error_log):
    """
    Add an error for the software Instance Workflow
    """
    return self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id).reportComputerPartitionError(
                                     comment=error_log)

  @convertToREST
  def _softwareInstanceBang(self, computer_id,
                            computer_partition_id, message):
    """
    Fire up bang on Software Instance
    Add an error for the software Instance Workflow
    """
    return self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id).reportComputerPartitionBang(
                                     comment=message)

  @convertToREST
  def _startedComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is started
    """
    return self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id).startComputerPartition()

  @convertToREST
  def _stoppedComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is stopped
    """
    return self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id).stopComputerPartition()

  @convertToREST
  def _destroyedComputerPartition(self, computer_id, computer_partition_id):
    """
    Reports that Computer Partition is destroyed
    """
    software_instance = self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id)
    return software_instance.destroyComputerPartition()

  @convertToREST
  def _setComputerPartitionConnectionXml(self, computer_id,
                                         computer_partition_id,
                                         connection_xml,
                                         slave_reference=None):
    """
    Sets Computer Partition connection Xml
    """
    software_instance = self._getSoftwareInstanceForComputerPartition(
        computer_id,
        computer_partition_id,
        slave_reference)
    partition_parameter_kw = xml_marshaller.xml_marshaller.loads(
                                              connection_xml)
    instance = etree.Element('instance')
    for parameter_id, parameter_value in partition_parameter_kw.iteritems():
      # cast everything to string
      parameter_value = str(parameter_value)
      etree.SubElement(instance, "parameter",
                       attrib={'id':parameter_id}).text = parameter_value
    connection_xml = etree.tostring(instance, pretty_print=True,
                                  xml_declaration=True, encoding='utf-8')
    software_instance.edit(
      connection_xml=connection_xml,
    )

  @convertToREST
  def _requestComputerPartition(self, computer_id, computer_partition_id,
        software_release, software_type, partition_reference,
        shared_xml, partition_parameter_xml, filter_xml, state):
    """
    Asynchronously requests creation of computer partition for assigned
    parameters

    Returns XML representation of partition with HTTP code 200 OK

    In case if this request is still being processed data contain
    "Computer Partition is being processed" and HTTP code is 408 Request
    Timeout

    In any other case returns not important data and HTTP code is 403 Forbidden
    """
    if state:
      state = xml_marshaller.xml_marshaller.loads(state)
    if state is None:
      state = 'started'
    if shared_xml is not _MARKER:
      shared = xml_marshaller.xml_marshaller.loads(shared_xml)
    else:
      shared = False
    if partition_parameter_xml:
      partition_parameter_kw = xml_marshaller.xml_marshaller.loads(
                                              partition_parameter_xml)
    else:
      partition_parameter_kw = dict()
    if filter_xml:
      filter_kw = xml_marshaller.xml_marshaller.loads(filter_xml)
    else:
      filter_kw = dict()

    instance = etree.Element('instance')
    for parameter_id, parameter_value in partition_parameter_kw.iteritems():
      # cast everything to string
      parameter_value = str(parameter_value)
      etree.SubElement(instance, "parameter",
                       attrib={'id':parameter_id}).text = parameter_value
    instance_xml = etree.tostring(instance, pretty_print=True,
                                  xml_declaration=True, encoding='utf-8')

    instance = etree.Element('instance')
    for parameter_id, parameter_value in filter_kw.iteritems():
      # cast everything to string
      parameter_value = str(parameter_value)
      etree.SubElement(instance, "parameter",
                       attrib={'id':parameter_id}).text = parameter_value
    sla_xml = etree.tostring(instance, pretty_print=True,
                                  xml_declaration=True, encoding='utf-8')

    if shared:
      instance_portal_type = "Slave Instance"
    else:
      instance_portal_type = "Software Instance"

    if computer_id and computer_partition_id:
      # requested by Software Instance, there is already top part of tree
      software_instance_document = self.\
        _getSoftwareInstanceForComputerPartition(computer_id,
        computer_partition_id)
      software_instance_document.requestSoftwareInstance(
              software_release=software_release,
              software_type=software_type,
              partition_reference=partition_reference,
              instance_xml=instance_xml,
              shared=shared,
              sla_xml=sla_xml,
              state=state)

      # Get requested software instance
      requested_software_instance = software_instance_document.portal_catalog.\
          getResultValue(
                portal_type=instance_portal_type,
                source_reference=software_type,
                # predecessor_related_uid is inconsistent with
                # SoftwareInstancae.requestSoftwareInstance but in this case it
                # is assumed, that data are correct
                predecessor_related_uid=software_instance_document.getUid(),
                title=partition_reference,
          )
    else:
      # requested as root, so done by human
      person = self.getPortalObject()\
          .ERP5Site_getAuthenticatedMemberPersonValue()
      person.requestSoftwareInstance(software_release=software_release,
              software_type=software_type,
              software_title=partition_reference,
              shared=shared,
              instance_xml=instance_xml,
              sla_xml=sla_xml,
              state=state)
      requested_software_instance = person.portal_catalog.\
          getResultValue(
                portal_type=instance_portal_type,
                # In order be in sync with defaults of person.
                #   requestSoftwareInstance it is required to default here
                # too
                source_reference=software_type or 'RootSoftwareInstance',
                title=partition_reference,
          )

    if requested_software_instance is None:
      raise SoftwareInstanceNotReady
    else:
      query_kw = {}
      if shared:
        # Provide precise reference when search for a slave.
        query_kw['slave_reference'] = requested_software_instance.getReference()

      movement = self._getSalePackingListLineForComputerPartition(
                         requested_software_instance, **query_kw)
      if movement is None:
        raise SoftwareInstanceNotReady
      software_instance = SoftwareInstance(
        **self._getSalePackingListLineAsSoftwareInstance(movement))
      return xml_marshaller.xml_marshaller.dumps(software_instance)

  ####################################################
  # Internals methods
  ####################################################

  def _getDocument(self, **kwargs):
    # No need to get all results if an error is raised when at least 2 objects
    # are found
    l = self.getPortalObject().portal_catalog(limit=2, **kwargs)
    if len(l) != 1:
      raise NotFound, "No document found with parameters: %s" % kwargs
    else:
      return l[0].getObject()

  def _getComputerDocument(self, computer_reference):
    """
    Get the validated computer with this reference.
    """
    return self._getDocument(
        portal_type='Computer',
        # XXX Hardcoded validation state
        validation_state="validated",
        reference=computer_reference)

  @UnrestrictedMethod
  def _getComputerUidByReference(self, computer_reference):
    return self._getComputerDocument(computer_reference).getUid()

  def _getComputerPartitionDocument(self, computer_reference,
                                    computer_partition_reference):
    """
    Get the computer partition defined in an available computer
    """
    # Related key might be nice
    return self._getDocument(portal_type='Computer Partition',
                             reference=computer_partition_reference,
                             parent_uid=self._getComputerUidByReference(
                                computer_reference))

  def _getUsageReportServiceDocument(self):
    service_document = self.Base_getUsageReportServiceDocument()
    if service_document is not None:
      return service_document
    raise Unauthorized

  def _getSoftwareInstanceForComputerPartition(self, computer_id,
      computer_partition_id, slave_reference=None):
    computer_partition_document = self._getComputerPartitionDocument(
      computer_id, computer_partition_id)
    if computer_partition_document.getSlapState() != 'busy':
      LOG('SlapTool::_getSoftwareInstanceForComputerPartition', INFO,
          'Computer partition %s shall be busy, is free' %
          computer_partition_document.getRelativeUrl())
      raise NotFound, "No software instance found for: %s - %s" % (computer_id,
          computer_partition_id)
    packing_list_line = self._getSalePackingListLineForComputerPartition(
                                                computer_partition_document,
                                                slave_reference)
    if packing_list_line is None:
      raise NotFound, "No software instance found for: %s - %s" % (computer_id,
          computer_partition_id)
    else:
      portal_type_list = ["Software Instance", "Slave Instance"]
      software_instance = packing_list_line.getAggregateValue(
                                              portal_type=portal_type_list)
      if software_instance is None:
        raise NotFound, "No software instance found for: %s - %s" % (
          computer_id, computer_partition_id)
      else:
        return software_instance

  @UnrestrictedMethod
  def _getSalePackingListLineAsSoftwareInstance(self, sale_packing_list_line):
    merged_dict = sale_packing_list_line.\
        SalePackinListLine_asSoftwareInstnaceComputerPartitionMergedDict()
    if merged_dict is None:
      LOG('SlapTool._getSalePackingListLineAsSoftwareInstance', INFO,
        '%s returned no information' % sale_packing_list_line.getRelativeUrl())
      raise Unauthorized
    return merged_dict

  @UnrestrictedMethod
  def _getSoftwareReleaseValueListForComputer(self, computer_reference):
    """Returns list of Software Releases documentsfor computer"""
    computer_document = self._getComputerDocument(computer_reference)
    portal = self.getPortalObject()

    state_list = []
    state_list.extend(portal.getPortalReservedInventoryStateList())
    state_list.extend(portal.getPortalTransitInventoryStateList())

    software_release_list = []
    for software_release_url_string in computer_document\
      .Computer_getSoftwareReleaseUrlStringList(state_list):
      software_release_response = SoftwareRelease(
          software_release=software_release_url_string,
          computer_guid=computer_reference)
      software_release_list.append(software_release_response)
    return software_release_list

  def _getSalePackingListLineForComputerPartition(self,
                                                  computer_partition_document,
                                                  slave_reference=None,
                                                  service_uid_list=None):
    """
    Return latest meaningfull sale packing list related to a computer partition
    document
    """
    portal = self.getPortalObject()
    portal_preferences = portal.portal_preferences
    if service_uid_list is None:
      service_uid_list = []
      for service_relative_url in \
        (portal_preferences.getPreferredInstanceSetupResource(),
         portal_preferences.getPreferredInstanceHostingResource(),
         portal_preferences.getPreferredInstanceCleanupResource(),
         ):
        service = portal.restrictedTraverse(service_relative_url)
        service_uid_list.append(service.getUid())

    # Get associated software release
    state_list = []
    state_list.extend(portal.getPortalCurrentInventoryStateList())
    state_list.extend(portal.getPortalReservedInventoryStateList())
    state_list.extend(portal.getPortalTransitInventoryStateList())
    if slave_reference is not None:
      query = ComplexQuery(Query(aggregate_reference=slave_reference),
          Query(aggregate_relative_url=computer_partition_document.getRelativeUrl()),
          operator="AND")
    else:
      query = ComplexQuery(Query(aggregate_portal_type="Software Instance"),
          Query(aggregate_relative_url=computer_partition_document.getRelativeUrl()),
          operator="AND")

    # Use getTrackingList
    catalog_result = portal.portal_catalog(
      portal_type='Sale Packing List Line',
      simulation_state=state_list,
      default_resource_uid=service_uid_list,
      sort_on=(('movement.start_date', 'DESC'),),
      limit=1,
      query=query
    )
    if len(catalog_result):
      return catalog_result[0].getObject()
    else:
      return None

  def _reportComputerUsage(self, computer, usage):
    """Stores usage report of a computer."""
    usage_report_portal_type = 'Usage Report'
    usage_report_module = \
      self.getPortalObject().getDefaultModule(usage_report_portal_type)
    sale_packing_list_portal_type = 'Sale Packing List'
    sale_packing_list_module = \
      self.getPortalObject().getDefaultModule(sale_packing_list_portal_type)
    sale_packing_list_line_portal_type = 'Sale Packing List Line'

    software_release_portal_type = 'Software Release'
    hosting_subscription_portal_type = 'Hosting Subscription'
    software_instance_portal_type = 'Software Instance'

    # We get the whole computer usage in one time
    # We unmarshall it, then we create a single packing list,
    # each line is a computer partition
    unmarshalled_usage = xml_marshaller.xml_marshaller.loads(usage)

    # Creates the Packing List
    usage_report_sale_packing_list_document = \
      sale_packing_list_module.newContent(
        portal_type = sale_packing_list_portal_type,
      )
    usage_report_sale_packing_list_document.confirm()
    usage_report_sale_packing_list_document.start()

    # Adds a new SPL line for each Computer Partition
    for computer_partition_usage in unmarshalled_usage\
        .computer_partition_usage_list:
      #Get good packing list line for a computer_partition
      computer_partition_document = self.\
                _getComputerPartitionDocument(
                  computer.getReference(),
                  computer_partition_usage.getId()
                )
      instance_setup_sale_packing_line = \
          self._getDocument(
                    portal_type='Sale Packing List Line',
                    simulation_state='stopped',
                    aggregate_relative_url=computer_partition_document\
                      .getRelativeUrl(),
                    resource_relative_url=self.portal_preferences\
                      .getPreferredInstanceSetupResource()
          )

      # Fetching documents
      software_release_document = \
          self.getPortalObject().restrictedTraverse(
              instance_setup_sale_packing_line.getAggregateList(
                  portal_type=software_release_portal_type
              )[0]
          )
      hosting_subscription_document = \
          self.getPortalObject().restrictedTraverse(
              instance_setup_sale_packing_line.getAggregateList(
                  portal_type=hosting_subscription_portal_type
              )[0]
          )
      software_instance_document = \
          self.getPortalObject().restrictedTraverse(
              instance_setup_sale_packing_line.getAggregateList(
                  portal_type=software_instance_portal_type
              )[0]
          )
      # Creates the usage document
      usage_report_document = usage_report_module.newContent(
        portal_type = usage_report_portal_type,
        text_content = computer_partition_usage.usage,
        causality_value = computer_partition_document
      )
      usage_report_document.validate()
      # Creates the line
      usage_report_sale_packing_list_document.newContent(
        portal_type = sale_packing_list_line_portal_type,
        # We assume that "Usage Report" is an existing service document
        resource_value = self._getUsageReportServiceDocument(),
        aggregate_value_list = [usage_report_document, \
          computer_partition_document, software_release_document, \
          hosting_subscription_document, software_instance_document
        ]
      )

  def _reportUsage(self, computer_partition, usage):
    """Warning : deprecated method."""
    portal_type = 'Usage Report'
    module = self.getPortalObject().getDefaultModule(portal_type)
    usage_report = module.newContent(
      portal_type=portal_type,
      text_content=usage,
      causality_value=computer_partition
    )
    usage_report.validate()

InitializeClass(SlapTool)
