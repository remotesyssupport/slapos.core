import unittest
from Products.ERP5Type.tests.Sequence import SequenceList
from Products.ERP5Type.DateUtils import getClosestDate, addToDate
from testVifibSlapWebService import TestVifibSlapWebServiceMixin

from DateTime.DateTime import DateTime

class TestVifibOpenOrderSimulation(TestVifibSlapWebServiceMixin):

  def stepCheckSimulationMovement(self, sequence, **kw):
    person = self.portal.person_module['test_vifib_customer']
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

    # Should check timezone information here?
    today = getClosestDate(target_date=DateTime(), precision='day', before=1)
    self.assertEquals(today.year(), open_order_line.getStartDate().year())
    self.assertEquals(today.month(), open_order_line.getStartDate().month())
    self.assertEquals(today.day(), open_order_line.getStartDate().day())
    self.assertEquals(0, open_order_line.getStartDate().hour())
    self.assertEquals(0, open_order_line.getStartDate().minute())
    self.assertEquals(0.0, open_order_line.getStartDate().second())
    stop_date = addToDate(getClosestDate(target_date=today, precision='month', before=0), year=1)
    self.assertEquals(stop_date.year(), open_order_line.getStopDate().year())
    self.assertEquals(stop_date.month(), open_order_line.getStopDate().month())
    self.assertEquals(stop_date.day(), open_order_line.getStopDate().day())
    self.assertEquals(0, open_order_line.getStopDate().hour())
    self.assertEquals(0, open_order_line.getStopDate().minute())
    self.assertEquals(0.0, open_order_line.getStopDate().second())

    # Calculate the list of time frames
    expected_time_frame_list = []
    current = getClosestDate(target_date=today, precision='month', before=0)
    while current <= stop_date:
      expected_time_frame_list.append(current)
      current = addToDate(getClosestDate(target_date=current, precision='month', before=0), month=1)

    # Check that simulation is created by the periodicity
    self.assertEquals(len(expected_time_frame_list),
                      len(applied_rule.contentValues()) + 1)

    # Check the list of expected simulation
    idx = 0
    while idx + 1 < len(expected_time_frame_list):
      simulation_movement_list = \
        self.portal.portal_catalog.unrestrictedSearchResults(
          parent_uid=applied_rule.getUid(),
          portal_type="Simulation Movement",
          **{
            'movement.start_date':expected_time_frame_list[idx],
            'movement.stop_date':expected_time_frame_list[idx + 1],
          })
      self.assertEquals(1, len(simulation_movement_list))
      simulation_movement = simulation_movement_list[0].getObject()
      self.assertNotEquals(None, simulation_movement)

      # Check simulation movement property
      self.assertEquals(1.0, simulation_movement.getQuantity())
      self.assertEquals(None, simulation_movement.getQuantityUnit())
      self.assertEquals(1.0, simulation_movement.getPrice())
      self.assertEquals(None, simulation_movement.getPriceCurrency())
      # XXX supplier
      self.assertEquals(None, simulation_movement.getSource())
      self.assertEquals(None, simulation_movement.getSourceSection())
      # XXX customer
      self.assertEquals(None, simulation_movement.getDestination())
      self.assertEquals("person_module/test_vifib_customer", simulation_movement.getDestinationSection())

      self.assertEquals(None, simulation_movement.getSpecialise())

      self.assertEquals(None, simulation_movement.getResource())
      self.assertEquals("default/delivery", simulation_movement.getTradePhase())

      # self.assertEquals("XXX",
      #                      simulation_movement.getAggregate(
      #                        portal_type="Computer Partition"))
      # self.assertEquals("XXX",
      #                      simulation_movement.getAggregate(
      #                        portal_type="Software Instance"))
      # self.assertEquals("XXX",
      #                      simulation_movement.getAggregate(
      #                        portal_type="Hosting Subscription"))
      # self.assertEquals("XXX",
      #                      simulation_movement.getAggregate(
      #                        portal_type="Software Release"))

      idx += 1

  def test_OpenOrder_request_changeSoftwareType(self):
    """
    Check that requesting the same instance with a different software type
    does not create a new instance
    """
    self.computer_partition_amount = 1
    sequence_list = SequenceList()
    sequence_string = \
        self.prepare_installed_computer_partition_sequence_string + """
      LoginDefaultUser
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