import unittest
from game.player import Player
from game.community_charity import CommunityCharitySystem


class TestCommunityCharity(unittest.TestCase):
    def setUp(self):
        self.player = Player("Philanthropist")
        self.player.money = 20000
        self.player.street_cred = 60
        self.player.fame = 40
        self.player.stress = 50

    def test_donate_to_youth_instrument_fund(self):
        sys = CommunityCharitySystem()

        res = sys.donate_to_initiative(self.player, "youth_instrument_fund")
        self.assertTrue(res["ok"])
        self.assertEqual(len(sys.completed_donations), 1)
        self.assertEqual(sys.total_donated, 5000)
        self.assertEqual(self.player.street_cred, 80)
        self.assertEqual(self.player.fame, 55)
        self.assertEqual(self.player.stress, 30)


if __name__ == "__main__":
    unittest.main()
