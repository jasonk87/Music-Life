import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.game_time import current_game_time
from game.player import Player
from game.band import Band, BandMember
from game.band_drama import check_creative_friction, check_for_band_drama
from game.merch_system import MerchSystem, MerchItem


class TestRealAndRawMechanics(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 10
        current_game_time.minute = 0

        self.game = Game(None)
        self.game.player = Player("Tester")

    def test_street_cred_field_initialization(self):
        self.assertEqual(self.game.player.street_cred, 50)
        self.game.player.street_cred = min(100, self.game.player.street_cred + 10)
        self.assertEqual(self.game.player.street_cred, 60)

    def test_merch_production_and_booth_sales(self):
        merch_sys = MerchSystem()
        self.game.player.money = 500

        res = merch_sys.produce_merch(self.game.player, "screenprint_tshirts")
        self.assertTrue(res["ok"])
        self.assertEqual(len(self.game.player.merch_stock), 1)
        self.assertEqual(self.game.player.merch_stock[0].unit_count, 15)

        # Simulate post-gig merch booth
        sales_res = merch_sys.resolve_gig_merch_booth(self.game.player, gig_turnout=60, performance_score=15.0)
        self.assertGreater(sales_res["units_sold"], 0)
        self.assertGreater(sales_res["total_revenue"], 0)
        self.assertLess(self.game.player.merch_stock[0].unit_count, 15)

    def test_band_creative_friction(self):
        band = Band("The Test Project", self.game.player)
        member1 = BandMember("Alex", "Guitar")
        member1.indie_authenticity_preference = 0.8
        member1.satisfaction = 80

        band.members = [self.game.player, member1]

        report = check_creative_friction(self.game.player, band, "signed_major_label")
        self.assertIn("sold out", report.lower())
        self.assertEqual(member1.satisfaction, 65)

    def test_band_drama_checks(self):
        band = Band("The Test Project", self.game.player)
        member1 = BandMember("Jordan", "Drums")
        member1.satisfaction = 20
        member1.ego = 85
        band.members = [self.game.player, member1]

        result = check_for_band_drama(self.game.player, band)
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
