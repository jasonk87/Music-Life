import unittest
from types import SimpleNamespace
from game.player import Player
from game.song import Song
from game.live_concert_dynamics import LiveConcertDynamicsEngine, LivePerformanceState


class TestLiveConcertDynamics(unittest.TestCase):
    def setUp(self):
        self.player = Player("Rocker")
        self.player.fame = 150
        self.player.current_location = SimpleNamespace(name="Asbury Park, NJ")
        self.venue = SimpleNamespace(name="The Stone Pony", capacity=1000)
        self.s1 = Song("Boardwalk Riff", "Rocker", "Rock", song_quality=0.85)
        self.s1.recording_quality = 0.88
        self.s2 = Song("Ocean Avenue Jam", "Rocker", "Rock", song_quality=0.80)
        self.s2.recording_quality = 0.82

    def test_concert_lifecycle_and_tactics(self):
        perf = LiveConcertDynamicsEngine.start_concert(self.player, self.venue, [self.s1, self.s2], ticket_price=30)
        self.assertEqual(perf.venue_name, "The Stone Pony")
        self.assertGreater(perf.crowd_attendance, 0)
        self.assertGreater(perf.gross_revenue, 0)

        # Standard tactic
        res1 = LiveConcertDynamicsEngine.perform_song_with_tactic(self.player, perf, self.s1, tactic="STANDARD")
        self.assertTrue(res1["ok"])
        self.assertGreater(perf.hype_score, 40.0)

        # Stage Banter
        res2 = LiveConcertDynamicsEngine.perform_song_with_tactic(self.player, perf, self.s2, tactic="CITY_BANTER")
        self.assertTrue(res2["ok"])
        self.assertIn("Asbury Park, NJ", res2["explanation"])

        # Encore
        perf.hype_score = 90.0
        enc_res = LiveConcertDynamicsEngine.trigger_encore(self.player, perf, self.s1)
        self.assertTrue(enc_res["ok"])
        self.assertTrue(perf.encore_completed)
        self.assertGreater(perf.gross_revenue, 0)


if __name__ == "__main__":
    unittest.main()
