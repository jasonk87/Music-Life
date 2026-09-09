import os
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.event import Event
from game.game import Game
from game.song import Song
from game.venue import Venue


class DummyUI:
    def __init__(self, choices):
        self.choices = list(choices)
        self.messages = []

    def present_choices(self, options, title):
        return self.choices.pop(0)

    def add_log_message(self, message):
        self.messages.append(message)

    def add_message(self, message):
        self.messages.append(message)


class TestPerformanceFlow(unittest.TestCase):
    def test_event_entry_is_blocked_when_requirements_fail(self):
        ui = DummyUI(["0"])
        game = Game(ui)
        venue = Venue("venue_1", "Test Venue")
        event = Event(
            "Club Gig",
            venue,
            event_type="CLUB_GIG",
            required_skills={"guitar": 50},
            required_gear_types=["INSTRUMENT_ELECTRIC"],
        )
        venue.add_event(event)

        game.player = type("PlayerStub", (), {})()
        game.player.skills = {"guitar": 1}
        game.player.fame = 0
        game.player.songs_written = []
        game.player.gear_inventory = []
        game.player.active_opportunities = {}
        game.selected_poi = venue
        game.explore_menu_state = "view_events"

        game.handle_explore_menu()

        self.assertNotEqual(game.game_state, "performance")
        self.assertIn("does not meet skill requirement", " ".join(ui.messages))

    def test_choose_song_builds_setlist_for_multi_song_event(self):
        ui = DummyUI(["0"])
        game = Game(ui)
        venue = Venue("venue_1", "Test Venue")
        event = Event("Open Mic", venue, event_type="OPEN_MIC")
        game.active_performance = event
        game.performance_stage = "choose_song"
        game.player = type("PlayerStub", (), {})()
        game.player.songs_written = [
            Song("Opener", "Tester", "Rock", song_quality=0.6),
            Song("Closer", "Tester", "Rock", song_quality=0.9),
        ]

        game.handle_performance_scene()

        self.assertEqual(game.performance_stage, "playing")
        self.assertEqual(game.performance_setlist[0].title, "Opener")
        self.assertEqual(len(game.performance_setlist), 1)

    def test_gig_rewards_use_contextual_roll(self):
        ui = DummyUI(["0"])
        game = Game(ui)
        venue = Venue("venue_1", "Test Venue")
        event = Event("Open Mic", venue, event_type="OPEN_MIC")
        event.payout = 50
        event.fame_reward = 5
        game.active_performance = event
        game.performance_stage = "finish"
        game.player = type("PlayerStub", (), {})()
        game.player.name = "Tester"
        game.player.money = 0
        game.player.fame = 0
        game.player.skills = {"stage_presence": 10}
        game.player.stress = 10
        game.player.energy = 90
        game.player.merch_stock = []
        game.player.contacts = []
        game.player.gear_inventory = []
        game.player.vocal_strain = 0
        game.player.wrist_strain = 0
        song = Song("Closer", "Tester", "Rock", song_quality=0.9)
        song.mark_as_recorded(0.8)
        game.performance_setlist = [song]

        class PerfStub:
            crowd_hype = 75

        game.performance_manager = PerfStub()

        with patch("game.game.random.randint", return_value=70), patch("game.game.random.random", return_value=1.0):
            game.handle_performance_scene()

        self.assertGreater(game.player.money, 50)
        self.assertGreater(game.player.fame, 5)


if __name__ == "__main__":
    unittest.main()
