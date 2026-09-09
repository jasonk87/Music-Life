import unittest
from game.player import Player
from game.fan_club_and_pr import FanClubAndPRSystem


class TestFanClubAndPR(unittest.TestCase):
    def setUp(self):
        self.player = Player("PopIcon")
        self.player.money = 20000
        self.player.fame = 100
        self.player.street_cred = 80

    def test_vip_fan_club_launch_and_monthly_payout(self):
        sys = FanClubAndPRSystem()

        launch_res = sys.launch_vip_fan_club(self.player)
        self.assertTrue(launch_res["ok"])
        self.assertTrue(sys.is_club_launched)
        self.assertGreater(launch_res["total_subscribers"], 50)

        # Monthly payout
        initial_money = self.player.money
        logs = sys.process_monthly_fan_club_payout(self.player)
        self.assertTrue(len(logs) > 0)
        self.assertGreater(self.player.money, initial_money)

    def test_hire_pr_crisis_firm(self):
        sys = FanClubAndPRSystem()
        self.player.stress = 80

        res = sys.hire_pr_crisis_firm(self.player, "Leaked Backstage Audio Scandal")
        self.assertTrue(res["ok"])
        self.assertEqual(len(sys.pr_crises_resolved), 1)
        self.assertEqual(self.player.stress, 50)


if __name__ == "__main__":
    unittest.main()
