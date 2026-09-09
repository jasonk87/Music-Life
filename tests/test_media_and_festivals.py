import unittest
from types import SimpleNamespace
from game.player import Player
from game.media_and_festivals import MediaAndFestivalsSystem


class TestMediaAndFestivals(unittest.TestCase):
    def setUp(self):
        self.player = Player("Superstar")
        self.player.money = 10000
        self.player.fame = 160
        self.player.street_cred = 85

    def test_tonight_show_at_30_rock(self):
        self.player.current_location = SimpleNamespace(name="New York City, NY")
        sys = MediaAndFestivalsSystem()

        res = sys.perform_late_night_tv(self.player, "tonight_30rock", "Breakthrough Anthem")
        self.assertTrue(res["ok"])
        self.assertEqual(len(sys.tv_performances_logged), 1)
        self.assertGreater(self.player.fame, 160)

    def test_glastonbury_pyramid_stage_headliner(self):
        self.player.current_location = SimpleNamespace(name="London, UK")
        sys = MediaAndFestivalsSystem()

        res = sys.headline_festival_mainstage(self.player, "glastonbury", ["Track 1", "Track 2", "Encore"])
        self.assertTrue(res["ok"])
        self.assertEqual(len(sys.festival_sets_logged), 1)
        self.assertGreaterEqual(self.player.money, 160000)


if __name__ == "__main__":
    unittest.main()
