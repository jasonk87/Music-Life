import unittest
from game.rival_bands_and_trends import RivalBandsAndTrendsSystem


class TestRivalBandsAndTrends(unittest.TestCase):
    def setUp(self):
        self.sys = RivalBandsAndTrendsSystem()

    def test_rival_roster_and_activity(self):
        self.assertIn("silver_strays", self.sys.rivals)
        self.assertIn("static_reverie", self.sys.rivals)

        logs = self.sys.simulate_rival_band_activity()
        self.assertGreater(len(logs), 0)

    def test_cultural_trends_cycling(self):
        trend = self.sys.get_current_trend()
        self.assertEqual(trend.dominant_genre, "Rock")

        # Fast-forward trend
        self.sys.active_trend.days_remaining = 1
        shift_msg = self.sys.check_and_cycle_cultural_trends()
        self.assertIsNotNone(shift_msg)
        self.assertEqual(self.sys.active_trend.dominant_genre, "Electronic")


if __name__ == "__main__":
    unittest.main()
