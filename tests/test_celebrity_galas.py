import unittest
from game.player import Player
from game.celebrity_events import CelebrityEventSystem, check_for_celebrity_event


class TestCelebrityGalas(unittest.TestCase):
    def setUp(self):
        self.player = Player("Celebrity")
        self.player.money = 100000
        self.player.fame = 600
        self.player.street_cred = 70
        self.player.stress = 50

    def test_attend_met_gala(self):
        res = CelebrityEventSystem.attend_gala(self.player, "met_gala")
        self.assertTrue(res["ok"])
        self.assertEqual(self.player.fame, 780)
        self.assertEqual(self.player.street_cred, 100)
        self.assertEqual(self.player.stress, 30)

    def test_backward_compatible_invitation(self):
        evt = check_for_celebrity_event(self.player)
        self.assertIsNotNone(evt)
        self.assertIn("name", evt)


if __name__ == "__main__":
    unittest.main()
