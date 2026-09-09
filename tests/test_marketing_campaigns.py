import unittest
from game.player import Player
from game.song import Song
from game.marketing import MarketingSystem, run_marketing_campaign


class TestMarketingCampaigns(unittest.TestCase):
    def setUp(self):
        self.player = Player("Marketer")
        self.player.money = 50000
        self.player.fame = 80
        self.player.street_cred = 60
        self.song = Song("Hit Anthem", "Marketer", "Pop", song_quality=0.85)

    def test_times_square_billboard_campaign(self):
        res = MarketingSystem.launch_campaign(self.player, self.song, "times_square_billboard")
        self.assertTrue(res["ok"])
        self.assertGreaterEqual(self.song.buzz_score, 350)
        self.assertEqual(self.player.fame, 180)
        self.assertEqual(self.player.street_cred, 85)

    def test_backward_compatible_function(self):
        buzz, msg = run_marketing_campaign("tiktok_viral_push", self.song)
        self.assertGreater(buzz, 0)
        self.assertIn("Complete", msg.title())


if __name__ == "__main__":
    unittest.main()
