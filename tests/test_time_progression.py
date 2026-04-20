import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.game_time import current_game_time
from game.player import Player


class DummyUI:
    def __init__(self):
        self.messages = []

    def add_log_message(self, message):
        self.messages.append(message)

    def add_message(self, message):
        self.messages.append(message)


class TestTimeProgression(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 8
        current_game_time.minute = 0

        self.game = Game(DummyUI())
        self.game.player = Player("Tester")

    def test_menu_transition_interaction_does_not_advance_time(self):
        self.game.handle_interaction("Write a new song")

        self.assertEqual(self.game.explore_menu_state, "write_song_menu")
        self.assertEqual(current_game_time.hour, 8)
        self.assertEqual(current_game_time.minute, 0)

    def test_rest_advances_only_requested_hours(self):
        # We need a home location for rest to work properly now
        from game.poi import PointOfInterest
        self.game.player.current_poi = PointOfInterest("home_poi", "Home", "Home", category="HOME")
        self.game.rest(8)

        self.assertEqual(current_game_time.hour, 16)
        self.assertEqual(current_game_time.minute, 0)


if __name__ == "__main__":
    unittest.main()
