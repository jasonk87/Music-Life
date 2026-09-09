import unittest
from types import SimpleNamespace
from game.player import Player
from game.song import Song
from game.vintage_gear_network import VintageGearNetworkSystem
from game.billboard_charts import BillboardChartSystem


class TestVintageGearAndCharts(unittest.TestCase):
    def setUp(self):
        self.player = Player("GuitarHero")
        self.player.money = 200000
        self.player.fame = 100
        self.player.street_cred = 85
        self.player.current_location = SimpleNamespace(name="Nashville, TN")

    def test_scout_and_buy_59_burst_les_paul(self):
        sys = VintageGearNetworkSystem()
        found = sys.scout_city_shops_for_vintage(self.player)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].gear_id, "burst_59_les_paul")

        buy_res = sys.purchase_vintage_grail(self.player, "burst_59_les_paul")
        self.assertTrue(buy_res["ok"])
        self.assertEqual(len(sys.owned_grails), 1)
        self.assertEqual(self.player.money, 75000)

    def test_billboard_hot_100_ranking(self):
        charts = BillboardChartSystem()
        s = Song("Summer Smash", "GuitarHero", "Rock", song_quality=0.9)
        s.is_recorded = True
        s.recording_quality = 0.95
        s.is_released = True

        logs = charts.update_weekly_billboard_hot_100(self.player, [s])
        self.assertTrue(len(logs) > 0)
        self.assertIn(s.song_id, charts.chart_entries)
        self.assertLessEqual(charts.chart_entries[s.song_id].current_position, 10)


if __name__ == "__main__":
    unittest.main()
