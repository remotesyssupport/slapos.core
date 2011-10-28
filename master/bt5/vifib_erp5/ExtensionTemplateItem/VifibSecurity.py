##############################################################################
#
# Copyright (c) 2002-2011 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
##############################################################################

from Products.ERP5Security.ERP5GroupManager import ConsistencyError
from AccessControl.SecurityManagement import getSecurityManager, \
             setSecurityManager, newSecurityManager
from AccessControl import Unauthorized

def restrictMethodAsShadowUser(self, callable_object, *args, **kw):
  """
  Restrict the security access of a method to the unaccessible shadow user
  associated to the current user.
  """
  relative_url = self.getRelativeUrl()
  if self.getPortalType() != 'Open Sale Order':
    raise Unauthorized("%s is not an Open Sale Order" % relative_url)
  else:
    # Check that open order is the validated one for the current user
    if self.getValidationState() != 'validated':
      raise Unauthorized('Open Sale Order %s is not validated.' % relative_url)
    person = self.ERP5Site_getAuthenticatedMemberPersonValue()
    if person is None:
      software_instance = self.portal_catalog.getResultValue(
        portal_type='Software Instance',
        reference=getSecurityManager().getUser().getId())
      if software_instance is not None:
        raise Unauthorized('No Person nor Software Instance document found')
    if person is not None:
      person_uid = person.getUid()
      if self.getDestinationSectionUid() != person_uid:
        raise Unauthorized('This Open Sale Order does not belongs to %s'%
          person.getReference())
    else:
      delivery_line = software_instance.getAggregateRelatedValue(
        portal_type='Sale Packing List Line')
      if delivery_line is None:
        raise Unauthorized('No delivery line found')
      hosting_subscription = delivery_line.getAggregateValue(
        portal_type='Hosting Subscription')
      if hosting_subscription is None:
        raise Unauthorized('No Hosting Subscription')
      open_order_line = hosting_subscription.getAggergateRelatedValue(
          portal_type='Open Sale Order Line')
      if open_order_line is None:
        raise Unauthorized('No Open Sale Order')
      if open_order_line.getParentValue().getUid() != self.getUid():
        raise Unauthorized('This Open Sale Order does not belongs to %s'%
          software_instance.getReference())

    portal_membership = self.getPortalObject().portal_membership
    # Switch to the shadow user temporarily, so that the behavior would not
    # change even if this method is invoked by random users.
    sm = getSecurityManager()
    newSecurityManager(None, portal_membership.getMemberById(
      self.getReference()))
    try:
      return callable_object(*args, **kw)
    finally:
      # Restore the original user.
      setSecurityManager(sm)

def getComputerSecurityCategory(self, base_category_list, user_name, 
                                object, portal_type):
  """
  This script returns a list of dictionaries which represent
  the security groups which a computer is member of.
  """
  category_list = []

  computer_list = self.portal_catalog.unrestrictedSearchResults(
    portal_type='Computer', 
    reference=user_name,
    validation_state="validated",
    limit=2,
  )

  if len(computer_list) == 1:
    for base_category in base_category_list:
      if base_category == "role":
        category_list.append(
         {base_category: ['role', 'role/computer']})
  elif len(computer_list) > 1:
    raise ConsistencyError, "Error: There is more than one Computer " \
                            "with reference '%s'" % user_name

  return category_list

def getSoftwareInstanceSecurityCategory(self, base_category_list, user_name, 
                                object, portal_type):
  """
  This script returns a list of dictionaries which represent
  the security groups which a Software Instance is member of.
  """
  category_list = []

  software_instance_list = self.portal_catalog.unrestrictedSearchResults(
    portal_type='Software Instance', 
    reference=user_name,
    validation_state="validated",
    limit=2,
  )

  if len(software_instance_list) == 1:
    category_dict = {}
    for base_category in base_category_list:
      if base_category == "role":
        category_dict.setdefault(base_category, []).extend(['role', 'role/instance'])
      if base_category == "aggregate":
        software_instance = software_instance_list[0]
        current_delivery_line = self.portal_catalog.unrestrictedGetResultValue(
          portal_type='Sale Packing List Line',
          aggregate_uid=software_instance.getUid(),
          simulation_state=self.getPortalCurrentInventoryStateList() + \
              self.getPortalFutureInventoryStateList() + \
              self.getPortalReservedInventoryStateList() + \
              self.getPortalTransitInventoryStateList(),
          sort_on=(('movement.start_date', 'DESC'),)
        )
        if current_delivery_line is not None:
          hosting_item = current_delivery_line.getAggregateValue(portal_type='Hosting Subscription')
          if hosting_item is not None:
            category_dict.setdefault(base_category, []).append(hosting_item.getRelativeUrl())
    category_list.append(category_dict)
  elif len(software_instance_list) > 1:
    raise ConsistencyError, "Error: There is more than one Software Instance " \
                            "with reference %r" % user_name

  return category_list

