import os
import sys
import unittest
from unittest.mock import patch


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


class TestSurvivalLoop(unittest.TestCase):
    def test_weekly_survival_costs_penalize_missed_bills(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        game.player.money = 20
        game.player.stress = 10
        game.player.comfort = 50
        game.player.health = 90

        game._apply_weekly_survival_costs()

        self.assertEqual(game.player.money, 0)
        self.assertEqual(game.player.unpaid_survival_weeks, 1)
        self.assertGreater(game.player.stress, 10)
        self.assertLess(game.player.comfort, 50)
        self.assertLess(game.player.health, 90)

    def test_survival_state_can_end_run(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        game.player.health = 0
        game.player.alive = True
        game.running = True

        game._check_player_survival_state()

        self.assertFalse(game.player.alive)
        self.assertFalse(game.running)
        self.assertIn("gave out", game.player.cause_of_death)

    def test_missing_bills_can_cause_eviction(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        game.player.money = 0
        game.player.has_home = True

        game._apply_weekly_survival_costs()
        game._apply_weekly_survival_costs()

        self.assertFalse(game.player.has_home)
        self.assertEqual(game.player.unpaid_survival_weeks, 2)

    def test_bad_conditions_can_trigger_sickness_event(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        game.player.health = 30
        game.player.energy = 80
        game.player.stress = 10

        with patch("game.game.random.randint", side_effect=[100, 8]):
            game._apply_weekly_life_event()

        self.assertEqual(game.player.health, 22)
        self.assertEqual(game.player.energy, 60)
        self.assertEqual(game.player.stress, 20)

    def test_weekly_life_event_can_trigger_viral_break(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        game.player.money = 0
        game.player.has_bodyguard = True
        game.player.fame = 40
        game.player.contacts = ["a", "b", "c", "d", "e", "f", "g", "h"]

        from game.song import Song

        song = Song("Flashpoint", "Tester", "Rock", song_quality=0.8)
        song.mark_as_recorded(0.8)
        song.is_released = True
        song.buzz_score = 40
        game.player.songs_written = [song]

        with patch("game.game.random.randint", side_effect=[45, 30, 20]):
            game._apply_weekly_life_event()

        self.assertEqual(game.player.fame, 60)
        self.assertEqual(song.buzz_score, 70)


if __name__ == "__main__":
    unittest.main()
