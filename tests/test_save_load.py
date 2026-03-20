import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.player import Player


class DummyUI:
    def __init__(self):
        self.messages = []

    def add_log_message(self, message):
        self.messages.append(message)

    def add_message(self, message):
        self.messages.append(message)


class TestSaveLoad(unittest.TestCase):
    def test_load_restores_player_state_and_resets_transient_state(self):
        ui = DummyUI()
        game = Game(ui)
        game.player = Player("Tester")
        game.player.money = 1234
        game.player.fame = 77
        game.player.active_opportunities = {"tour_offer_x": "available"}
        game.active_performance = object()
        game.performance_setlist = ["stale"]
        game.travel_manager = object()
        game.selected_poi = object()
        game.game_state = "performance"

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "savegame.dat")
            game.save_game(save_path)

            game.player.money = 1
            game.player.fame = 2
            game.performance_setlist = ["mutated"]
            game.game_state = "travel_active"

            game.load_game(save_path)

        self.assertEqual(game.player.money, 1234)
        self.assertEqual(game.player.fame, 77)
        self.assertEqual(game.player.active_opportunities["tour_offer_x"]["status"], "available")
        self.assertIsNone(game.active_performance)
        self.assertEqual(game.performance_setlist, [])
        self.assertIsNone(game.travel_manager)
        self.assertIsNone(game.selected_poi)
        self.assertEqual(game.game_state, "main_menu")


if __name__ == "__main__":
    unittest.main()
