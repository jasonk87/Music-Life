import os
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.poi import PointOfInterest
from game.player import Player
from game.song import Song


class DummyUI:
    def __init__(self, choices=None, text_inputs=None):
        self.choices = list(choices or [])
        self.text_inputs = list(text_inputs or [])
        self.messages = []

    def present_choices(self, options, title, context=None):
        return self.choices.pop(0)

    def get_text_input(self, prompt):
        return self.text_inputs.pop(0)

    def add_log_message(self, message):
        self.messages.append(message)

    def add_message(self, message):
        self.messages.append(message)


class TestEconomyProgression(unittest.TestCase):
    def test_recording_quality_uses_best_relevant_skill(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        game.player.skills["guitar"] = 1
        game.player.skills["vocals"] = 20
        game.player.skills["electronic"] = 5
        game.player.skills["songwriting"] = 10

        song = Song("Test Song", "Tester", "Pop", song_quality=0.5)
        quality = game._calculate_recording_quality(song, studio_quality=0.6, producer_bonus=0.1)

        self.assertAlmostEqual(quality, 0.84, places=2)

    def test_single_release_cost_is_applied(self):
        ui = DummyUI(choices=["0"])
        game = Game(ui)
        game.player = Player("Tester")
        game.player.money = 100
        song = Song("Single", "Tester", "Rock", song_quality=0.5)
        song.mark_as_recorded(0.6)
        game.player.songs_written = [song]
        game.music_menu_state = "release_song"

        game.handle_music_menu()

        self.assertEqual(game.player.money, 85)
        self.assertTrue(song.is_released)

    def test_marketing_outcome_uses_contextual_roll(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        game.player.fame = 20
        game.player.contacts = ["a", "b", "c", "d"]
        song = Song("Push", "Tester", "Rock", song_quality=0.8)
        song.mark_as_recorded(0.85)
        song.is_released = True
        song.buzz_score = 20

        with patch("game.game.random.randint", return_value=70):
            outcome = game._resolve_marketing_outcome("social_media", song)

        self.assertEqual(outcome["band"], "strong")

    def test_demo_submission_stores_resolved_outcome_on_schedule(self):
        ui = DummyUI(choices=["0"])
        game = Game(ui)
        game.player = Player("Tester")
        game.player.money = 100
        game.player.fame = 45
        game.selected_poi = PointOfInterest(
            "label",
            "Label",
            "Indie label",
            category="OFFICE_RECORD_LABEL",
            min_fame_to_submit=40,
            genres_preferred=["Rock"],
        )
        song = Song("Demo", "Tester", "Rock", song_quality=0.8)
        song.mark_as_recorded(0.85)
        game.player.songs_written = [song]
        game.explore_menu_state = "submit_demo"

        with patch.object(game, "_resolve_demo_submission_outcome", return_value={
            "band": "strong_interest",
            "data": {"advance_mult": 1.1, "marketing_mult": 1.1, "message": "The office pays attention."},
        }):
            game.handle_explore_menu()

        scheduled = game.player.schedule.scheduled_items[0]
        self.assertEqual(scheduled.details["submission_outcome"], "strong_interest")
        self.assertEqual(scheduled.details["advance_mult"], 1.1)


if __name__ == "__main__":
    unittest.main()
