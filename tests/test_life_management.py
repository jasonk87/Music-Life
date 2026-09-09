import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.player import Player
from game.lodging import LodgingSystem
from game.food_system import FoodSystem
from game.vehicle_system import VehicleMarket, PlayerVehicle


class TestLifeManagement(unittest.TestCase):
    def setUp(self):
        self.game = Game(None)
        self.game.setup_world()
        self.game.player = Player("Traveler")

    def test_lodging_system_motel_booking(self):
        lodging = LodgingSystem()
        self.game.player.money = 100
        self.game.player.energy = 20
        self.game.player.stress = 50.0

        res = lodging.book_lodging(self.game, "motel_roadside")
        self.assertTrue(res["ok"])
        self.assertEqual(self.game.player.money, 50)
        self.assertGreater(self.game.player.energy, 90)
        self.assertLess(self.game.player.stress, 50.0)

    def test_food_system_dining_and_inventory(self):
        food_sys = FoodSystem()
        self.game.player.money = 50
        self.game.player.hunger = 80.0

        # Meal dining
        meal_res = food_sys.buy_and_eat_meal(self.game.player, "greasy_diner")
        self.assertTrue(meal_res["ok"])
        self.assertEqual(self.game.player.money, 36)
        self.assertLess(self.game.player.hunger, 50.0)

        # Portable food
        pack_res = food_sys.buy_portable_food(self.game.player, "energy_bar")
        self.assertTrue(pack_res["ok"])
        self.assertEqual(self.game.player.money, 32)
        self.assertTrue(any(g.gear_type == "FOOD" for g in self.game.player.gear_inventory))

        # Eat from inventory
        food_idx = next(i for i, g in enumerate(self.game.player.gear_inventory) if g.gear_type == "FOOD")
        eat_res = food_sys.eat_from_inventory(self.game.player, food_idx)
        self.assertTrue(eat_res["ok"])

    def test_vehicle_purchasing_driving_and_refuel(self):
        self.game.player.money = 3000
        buy_res = VehicleMarket.buy_vehicle(self.game.player, "van_touring")
        self.assertTrue(buy_res["ok"])
        self.assertEqual(self.game.player.money, 500)
        self.assertIsNotNone(self.game.player.vehicle)

        veh = self.game.player.vehicle
        drive_res = veh.drive_distance(150.0)
        self.assertGreater(drive_res["distance_driven"], 0)
        self.assertLess(veh.fuel_current, veh.fuel_capacity)

        # Refuel
        refuel_res = veh.refuel(self.game.player, liters=15.0)
        self.assertTrue(refuel_res["ok"])

        # Mechanics repair
        repair_res = veh.repair_engine(self.game.player, cost=100)
        self.assertTrue(repair_res["ok"])
        self.assertEqual(veh.engine_condition, 100.0)

    def test_save_load_vehicle_persistence(self):
        from game.save_manager import JSONSaveManager
        self.game.player.money = 5000
        buy_res = VehicleMarket.buy_vehicle(self.game.player, "van_touring")
        self.assertTrue(buy_res["ok"])
        self.game.player.vehicle.fuel_current = 42.0

        save_path = "test_veh_save.json"
        saved = JSONSaveManager.save_game(self.game, filepath=save_path)
        self.assertTrue(saved)

        self.game.player.vehicle = None
        loaded = JSONSaveManager.load_game(self.game, filepath=save_path)
        self.assertTrue(loaded)
        self.assertIsNotNone(self.game.player.vehicle)
        self.assertEqual(self.game.player.vehicle.model_key, "van_touring")
        self.assertEqual(self.game.player.vehicle.fuel_current, 42.0)

        if os.path.exists(save_path):
            os.remove(save_path)


if __name__ == "__main__":
    unittest.main()
