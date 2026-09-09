import unittest
from types import SimpleNamespace
from game.player import Player
from game.song import Song
from game.sync_licensing import SyncLicensingSystem
from game.streaming_dsp import StreamingPlatformSystem


class TestSyncLicensing(unittest.TestCase):
    def setUp(self):
        self.player = Player("Composer")
        self.player.money = 5000
        self.player.fame = 90
        self.player.street_cred = 70
        self.player.current_location = SimpleNamespace(name="Los Angeles, CA")

        self.song = Song("Cinematic Anthem", "Composer", "Rock", song_quality=0.85)
        self.song.is_recorded = True
        self.song.recording_quality = 0.88

    def test_pitch_and_secure_hollywood_blockbuster_sync(self):
        sys = SyncLicensingSystem()
        opps = sys.scout_sync_opportunities_in_city(self.player)
        self.assertGreaterEqual(len(opps), 2)

        res = sys.pitch_song_for_sync(self.player, self.song, "hollywood_blockbuster")
        self.assertTrue(res["ok"])
        self.assertEqual(len(sys.active_placements), 1)
        self.assertGreaterEqual(self.player.money, 50000)

        # Process daily sync streaming boost
        dsp = StreamingPlatformSystem()
        dsp.register_song_for_streaming(self.song, initial_fame=90)
        logs = sys.process_daily_sync_streams(dsp)
        self.assertGreater(dsp.catalog[self.song.song_id].daily_streams, 10000)


if __name__ == "__main__":
    unittest.main()
