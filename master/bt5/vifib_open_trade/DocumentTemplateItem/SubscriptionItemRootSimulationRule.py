# -- coding: utf-8 --
##############################################################################
#
# Copyright (c) 2011 Nexedi SA and Contributors. All Rights Reserved.
#                    Yingjie Xu <yxu@nexedi.com>
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

"""
This file is experimental.
"""

import zope.interface
from AccessControl import ClassSecurityInfo
from Products.ERP5Type import Permissions, PropertySheet, interfaces
from Products.ERP5.mixin.rule import RuleMixin

from DateTime.DateTime import DateTime

class SubscriptionItemRootSimulationRule(RuleMixin):

  # CMF Type Definition
  meta_type = 'ERP5 Subscription Item Root Simulation Rule'
  portal_type = 'Subscription Item Root Simulation Rule'

  # Declarative security
  security = ClassSecurityInfo()
  security.declareObjectProtected(Permissions.AccessContentsInformation)

  # Declarative interfaces
  zope.interface.implements(interfaces.IRule,)

  # Default Properties
  property_sheet = (
    PropertySheet.Base,
    PropertySheet.XMLObject,
    PropertySheet.CategoryCore,
    PropertySheet.DublinCore,
    PropertySheet.Task,
    PropertySheet.Predicate,
    PropertySheet.Reference,
    PropertySheet.Version,
    PropertySheet.Rule
    )

  def getNextPeriodicalDate(self, date):
    """
    Returns the first day of next month in this implementation.
    This method should be moved to Periodicity and carefully designed in the future.
    """
    year = date.year()
    month = date.month() + 1
    if month > 12:
      month -= 12
      year += 1
    return DateTime(year, month, 1)

  def expand(self, applied_rule, **kw):
    subscription_item = applied_rule.getCausalityValue()
    open_order_movement_list = subscription_item.getAggregateRelatedValueList(
                                   portal_type = 'Open Sale Order Line')
    for movement in open_order_movement_list:
      start_date = movement.getStartDate()
      stop_date = movement.getStopDate()
      current_date = start_date
      while current_date < stop_date:
        next_date = self.getNextPeriodicalDate(current_date)
        applied_rule.newContent(
            portal_type = 'Simulation Movement',
            aggregate_value = self,
            resource = movement.getResource(),
            start_date = current_date,
            stop_date = next_date,
            source = movement.getSource(),
            source_section = movement.getSourceSection(),
            destination = movement.getDestination(),
            destination_section = movement.getDestinationSection(),
            price = movement.getPrice(),
            quantity = movement.getQuantity(),
            )
