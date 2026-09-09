import unittest
from game.player import Player
from game.song import Song
from game.studio_production_engineering import StudioEngineeringSystem


class TestStudioToneEngineering(unittest.TestCase):
    def setUp(self):
        self.player = Player("AudioEngineer")
        self.player.money = 10000
        self.song = Song("Tape Dream", "AudioEngineer", "Rock", song_quality=0.85)
        self.song.recording_quality = 0.50

    def test_analog_tape_tracking_and_mix(self):
        res = StudioEngineeringSystem.engineer_master_track(
            self.player,
            self.song,
            tracking_medium="ANALOG_2INCH_TAPE",
            vocal_chain="DOUBLE_TRACKED_HARMONIES",
            mix_philosophy="WALL_OF_SOUND",
        )
        self.assertTrue(res["ok"])
        self.assertTrue(self.song.is_recorded)
        self.assertGreater(self.song.recording_quality, 0.70)
        self.assertEqual(self.player.money, 8800)


if __name__ == "__main__":
    unittest.main()
