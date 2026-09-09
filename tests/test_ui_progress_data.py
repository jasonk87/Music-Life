import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.event import Event
from game.game import Game
from game.game_time import current_game_time
from game.location import Location
from game.player import Player
from game.song import Song


class DummyUI:
    def add_log_message(self, message):
        pass

    def add_message(self, message):
        pass


class TestUiProgressData(unittest.TestCase):
    def test_career_overview_data_reflects_player_progress(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        game.player.current_location = Location("Philadelphia, PA", "Scene hub")
        game.player.contacts = ["npc_a", "npc_b"]
        game.player.active_opportunities = {
            "radio_interview_local": {"status": "available"},
            "music_blog_feature": {"status": "completed"},
        }

        song = Song("Signal", "Tester", "Pop", song_quality=0.8)
        song.mark_as_recorded(0.85)
        song.mark_as_released(current_game_time)
        song.buzz_score = 42
        game.player.songs_written = [song]
        game.player.fame = 28

        event = Event("Club Gig", "CLUB_GIG", None)
        start = current_game_time.copy()
        end = start.copy()
        end.add_hours(2)
        game.player.schedule.add_event(start, end, event.name, "Gig", {"event_id": event.event_id, "venue_id": "club_poi"})

        data = game._get_career_overview_data()

        self.assertEqual(data["summary_rows"][2], ("Songs Written", 1))
        self.assertEqual(data["summary_rows"][5], ("Top Buzz", 42))
        self.assertEqual(data["opportunities"][0], {"label": "Contacts", "value": "2"})
        self.assertEqual(data["opportunities"][1], {"label": "Open opportunities", "value": "1"})
        self.assertEqual(data["milestones"], [])
        self.assertIn("Contacts in phone: 2", data["focus_items"])


if __name__ == "__main__":
    unittest.main()
