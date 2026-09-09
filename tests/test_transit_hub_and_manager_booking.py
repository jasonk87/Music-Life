import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.player import Player
from game.transit_hub import TransitHubSystem


class TestTransitHubAndManagerBooking(unittest.TestCase):
    def setUp(self):
        self.game = Game(None)
        self.game.setup_world()
        self.game.player = Player("TouringMusician")

    def test_transit_hub_poi_registration(self):
        hometown = self.game.WORLD_MAP.get("Asbury Park, NJ")
        self.assertIsNotNone(hometown)
        poi_ids = [poi.poi_id for poi in hometown.points_of_interest]
        self.assertIn("asbury_transit_hub", poi_ids)

    def test_vehicle_rental_and_manager_discount(self):
        hub = TransitHubSystem()

        # Regular rental
        self.game.player.money = 200
        res = hub.rent_vehicle(self.game.player, "van_rental", days=2)
        self.assertTrue(res["ok"])
        self.assertEqual(self.game.player.money, 80)
        self.assertIsNotNone(self.game.player.vehicle)

        # Manager discount rental
        self.game.player.money = 200
        self.game.delegation_system.add_or_update_role(self.game.player, "manager", active=True)
        res_mgr = hub.rent_vehicle(self.game.player, "van_rental", days=2)
        self.assertTrue(res_mgr["ok"])
        self.assertEqual(self.game.player.money, 104) # 200 - (120 * 0.8) = 104
        self.assertIn("Manager", res_mgr["explanation"])

    def test_hail_taxi(self):
        hub = TransitHubSystem()
        self.game.player.money = 50

        res = hub.hail_taxi(self.game, "asbury_music_shop_oldtimers")
        self.assertTrue(res["ok"])
        self.assertEqual(self.game.player.money, 35)
        self.assertEqual(self.game.player.current_poi.poi_id, "asbury_music_shop_oldtimers")

    def test_manager_prebook_tour_fleet(self):
        hub = TransitHubSystem()
        self.game.player.money = 500
        self.game.delegation_system.add_or_update_role(self.game.player, "manager", active=True)

        res = hub.manager_prebook_tour_fleet(self.game)
        self.assertTrue(res["ok"])
        self.assertIsNotNone(self.game.player.vehicle)
        self.assertIn("Touring Van", self.game.player.vehicle.name)


if __name__ == "__main__":
    unittest.main()
