import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.game_time import current_game_time
from game.location import Location
from game.player import Player
from game.poi import PointOfInterest
from game.song import Song


class DummyUI:
    def __init__(self, choices=None):
        self.choices = list(choices or [])

    def present_choices(self, options, title, context=None):
        return self.choices.pop(0)

    def draw_ascii_art(self, art_lines, x, y, color=None):
        pass

    def add_log_message(self, message):
        pass

    def add_message(self, message):
        pass


class TestHomeDayFlow(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 8
        current_game_time.minute = 0

        self.game = Game(DummyUI())
        self.game.player = Player("Tester")
        self.game.player.current_poi = PointOfInterest(
            "home",
            "Home",
            "Apartment",
            category="HOME",
            rest_quality=0.8,
            comfort_modifier_hourly=5,
        )
        self.game.player.current_location = Location("Test City", "Test city")

    def test_practice_guitar_home_advances_time_and_skill(self):
        initial_skill = self.game.player.skills["guitar"]
        self.game.handle_interaction("Practice guitar (at home)")

        self.assertGreater(self.game.player.skills["guitar"], initial_skill)
        self.assertEqual(current_game_time.hour, 10)

    def test_food_order_applies_cost_and_effects(self):
        diner = PointOfInterest("diner", "Diner", "Food", category="FOOD_FASTFOOD")
        diner.menu_items = [
            {
                "display_text": "Order Cheap Burger ($5)",
                "cost": 5,
                "effects": {"hunger": -35, "energy": 10, "comfort": -2},
            }
        ]
        self.game.selected_poi = diner
        self.game.player.money = 20
        self.game.player.hunger = 50
        self.game.player.energy = 50
        self.game.player.comfort = 50

        self.game.handle_interaction("Order Cheap Burger ($5)")

        self.assertEqual(self.game.player.money, 15)
        self.assertEqual(self.game.player.hunger, 16)
        self.assertEqual(self.game.player.energy, 60)
        self.assertEqual(self.game.player.comfort, 50)

    def test_explore_poi_menu_uses_current_location_context(self):
        ui = DummyUI()
        game = Game(ui)
        game.player = Player("Tester")
        game.player.current_location = Location("Test City", "City")
        poi = PointOfInterest("shop", "Shop", "A shop", category="SHOP_MUSIC")
        poi.interaction_options = ["Browse items for sale"]
        game.player.current_poi = poi
        game.selected_poi = poi
        game.explore_menu_state = "location"
        game.player.active_opportunities = {}

        game.handle_explore_menu()

        self.assertEqual(game.explore_menu_state, "poi")
        self.assertIs(game.selected_poi, poi)

    def test_explore_poi_back_returns_to_main_menu(self):
        ui = DummyUI(choices=["back"])
        game = Game(ui)
        game.player = Player("Tester")
        game.player.current_location = Location("Test City", "City")
        poi = PointOfInterest("shop", "Shop", "A shop", category="SHOP_MUSIC")
        game.player.current_poi = poi
        game.selected_poi = poi
        game.explore_menu_state = "poi"
        game.game_state = "explore"

        game.handle_explore_menu()

        self.assertEqual(game.game_state, "main_menu")

    def test_home_demo_records_song_from_home(self):
        ui = DummyUI(choices=["0"])
        game = Game(ui)
        game.player = Player("Tester")
        home = PointOfInterest(
            "home",
            "Home",
            "Apartment",
            category="HOME",
            studio_quality=0.3,
        )
        game.player.current_location = Location("Test City", "City")
        game.player.current_poi = home
        game.selected_poi = home
        game.explore_menu_state = "record_song"
        game.player.songs_written.append(Song("First Draft", game.player.name, "Rock", 0.65))

        game.handle_explore_menu()

        self.assertTrue(game.player.songs_written[0].is_recorded)
        self.assertEqual(game.explore_menu_state, "poi")


if __name__ == "__main__":
    unittest.main()
