import unittest
from types import SimpleNamespace
from game.player import Player
from game.song import Song
from game.producers_and_sessions import ProducersAndSessionsSystem


class TestProducersAndSessions(unittest.TestCase):
    def setUp(self):
        self.player = Player("Auteur")
        self.player.money = 25000
        self.player.fame = 50
        self.player.street_cred = 60
        self.song = Song("Analog Masterpiece", "Auteur", "Rock", song_quality=0.75)

    def test_record_with_chicago_tape_purist(self):
        self.player.current_location = SimpleNamespace(name="Chicago, IL")
        sys = ProducersAndSessionsSystem()

        res = sys.produce_track_with_legend(self.player, self.song, "chicago_tape_purist")
        self.assertTrue(res["ok"])
        self.assertTrue(self.song.is_recorded)
        self.assertGreaterEqual(self.song.recording_quality, 0.90)

    def test_hire_london_philharmonia_strings(self):
        self.player.current_location = SimpleNamespace(name="London, UK")
        sys = ProducersAndSessionsSystem()

        res = sys.hire_session_section(self.player, self.song, "london_philharmonia_strings")
        self.assertTrue(res["ok"])
        self.assertGreater(getattr(self.song, "music_complexity", 0.5), 0.65)


if __name__ == "__main__":
    unittest.main()
