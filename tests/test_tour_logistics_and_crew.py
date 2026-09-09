import unittest
from game.player import Player
from game.tour_logistics import TourLogisticsSystem


class TestTourLogisticsAndCrew(unittest.TestCase):
    def setUp(self):
        self.player = Player("TourHead")
        self.player.money = 150000

    def test_lease_and_buy_sleeper_tour_bus(self):
        sys = TourLogisticsSystem()

        lease_res = sys.lease_tour_bus(self.player)
        self.assertTrue(lease_res["ok"])
        self.assertTrue(sys.tour_bus.is_leased)
        self.assertEqual(self.player.comfort, 80)

        # Clear and test buy
        sys.tour_bus = None
        buy_res = sys.buy_tour_bus(self.player)
        self.assertTrue(buy_res["ok"])
        self.assertTrue(sys.tour_bus.is_owned)

    def test_hire_touring_crew_and_payroll(self):
        sys = TourLogisticsSystem()

        hire_foh = sys.hire_crew_member(self.player, "foh_engineer")
        self.assertTrue(hire_foh["ok"])
        hire_ld = sys.hire_crew_member(self.player, "lighting_tech")
        self.assertTrue(hire_ld["ok"])

        self.assertEqual(len(sys.hired_crew), 2)

        # Payroll test
        payroll_logs = sys.process_weekly_crew_and_bus_payroll(self.player)
        self.assertTrue(len(payroll_logs) > 0)


if __name__ == "__main__":
    unittest.main()
