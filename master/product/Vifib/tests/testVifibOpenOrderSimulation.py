from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

from DateTime.DateTime import DateTime

class TestVifibOpenOrderSimulation(TestVifibSlapWebServiceMixin):

  def stepCheckSimulationMovement(self, sequence, **kw):
    person = self.portal.ERP5Site_getAuthenticatedMemberPersonValue()
    open_order = person.getDestinationDecisionRelatedValue(
        portal_type="Open Sale Order")
    open_order_line_list = open_order.contentValues(
        portal_type="Open Sale Order Line")
    self.assertEquals(1, len(open_order_line_list))

    open_order_line = open_order_line_list[0]
    hosting_subscription = open_order_line.getAggregateValue(
      portal_type="Hosting Subscription")

    applied_rule = hosting_subscription.getCausalityRelatedValue(
        portal_type="Applied Rule")
    self.assertEquals(
        "portal_rules/default_subscription_item_rule",
        applied_rule.getSpecialise())

    self.assertEquals(None, hosting_subscription.getPeriodicityMinuteFrequency())
    self.assertEquals([0], hosting_subscription.getPeriodicityMinuteList())
    self.assertEquals(None, hosting_subscription.getPeriodicityHourFrequency())
    self.assertEquals([0], hosting_subscription.getPeriodicityHourList())
    self.assertEquals(None, hosting_subscription.getPeriodicityDayFrequency())
    self.assertEquals(None, hosting_subscription.getPeriodicityMonthFrequency())
    self.assertEquals([1], hosting_subscription.getPeriodicityMonthDayList())
    self.assertEquals(None, hosting_subscription.getPeriodicityWeekFrequency())

    today = DateTime()
    year = today.year()
    month = today.month()
    day = today.day()
    self.assertEquals(year, open_order_line.getStartDate().year())
    self.assertEquals(month, open_order_line.getStartDate().month())
    self.assertEquals(day, open_order_line.getStartDate().day())
    to_year = year + 1
    to_month = month + 1
    if to_month > 12:
      to_year += 1
      to_month -=12
    to_day = 1
    self.assertEquals(to_year, open_order_line.getStopDate().year())
    self.assertEquals(to_month, open_order_line.getStopDate().month())
    self.assertEquals(to_day, open_order_line.getStopDate().day())

    # Calculate the list of time frames
    expected_time_frame_list = []
    current_year = year
    current_month = month + 1
    if current_month > 12:
      current_year += 1
      current_month -= 12
    current_day = 1
    current = DateTime(current_year, current_month, current_day)
    while current <= DateTime(to_year, to_month, to_day):
      expected_time_frame_list.append(current)
      current_month += 1
      if current_month > 12:
        current_year += 1
        current_month -= 12
      current = DateTime(current_year, current_month, current_day)

    # Check that simulation is created by the periodicity
    self.assertEquals(len(expected_time_frame_list),
                      len(applied_rule.contentValues()) + 1)

    # Check the list of expected simulation
    idx = 0
    while idx + 1 < len(expected_time_frame_list):
      simulation_movement = self.portal.portal_catalog.getResultValue(
          parent_uid=applied_rule.getUid(),
          portal_type="Simulation Movement",
          **{
            'movement.start_date':expected_time_frame_list[idx],
            'movement.stop_date':expected_time_frame_list[idx + 1]
          })
      import pdb; pdb.set_trace()
      self.assertNotEquals(None, simulation_movement)

      # Check simulation movement property
      self.assertNotEquals(1, simulation_movement.getQuantity())
      self.assertNotEquals("XXX", simulation_movement.getQuantityUnit())
      self.assertNotEquals(1, simulation_movement.getPrice())
      self.assertNotEquals("EUR", simulation_movement.getPriceCurrency())
      # XXX supplier
      self.assertNotEquals("XXX", simulation_movement.getSource())
      self.assertNotEquals("XXX", simulation_movement.getSourceSection())
      # XXX customer
      self.assertNotEquals("XXX", simulation_movement.getDestination())
      self.assertNotEquals("XXX", simulation_movement.getDestinationSection())

      self.assertNotEquals("XXX", simulation_movement.getSpecialise())

      self.assertNotEquals("XXX", simulation_movement.getResource())

      self.assertNotEquals("XXX",
                           simulation_movement.getAggregate(
                             portal_type="Computer Partition"))
      self.assertNotEquals("XXX",
                           simulation_movement.getAggregate(
                             portal_type="Software Instance"))
      self.assertNotEquals("XXX",
                           simulation_movement.getAggregate(
                             portal_type="Hosting Subscription"))
      self.assertNotEquals("XXX",
                           simulation_movement.getAggregate(
                             portal_type="Software Release"))

  def test_OpenOrder_request_changeSoftwareType(self):
    """
    Check that requesting the same instance with a different software type
    does not create a new instance
    """
    self.computer_partition_amount = 1
    sequence_list = SequenceList()
    sequence_string = self.prepare_person_requested_software_instance + """
      LoginTestVifibCustomer
      CheckSimulationMovement
      Tic
      SlapLogout
    """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibOpenOrderSimulation))
  return suite
