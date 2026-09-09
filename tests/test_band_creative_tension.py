import unittest
from types import SimpleNamespace
from game.player import Player
from game.song import Song
from game.band_creative_tension import BandCreativeTensionSystem


class TestBandCreativeTension(unittest.TestCase):
    def setUp(self):
        self.player = Player("BandLeader")
        self.player.money = 15000
        self.song = Song("Anthem", "BandLeader", "Rock", song_quality=0.75)
        self.bandmate = SimpleNamespace(member_name="Leo Bassist", satisfaction=70.0)
        self.sys = BandCreativeTensionSystem()

    def test_publishing_split_dispute_resolution(self):
        dispute = self.sys.check_for_recording_dispute(self.player, self.song, [self.bandmate])
        self.assertIsNotNone(dispute)
        self.assertEqual(len(dispute.options), 3)

        # Resolve by granting split
        res = self.sys.resolve_dispute(self.player, dispute, choice_idx=0, song=self.song, bandmate=self.bandmate)
        self.assertTrue(res["ok"])
        self.assertEqual(self.song.song_quality, 0.80)
        self.assertEqual(self.bandmate.satisfaction, 100.0)
        self.assertEqual(len(self.sys.dispute_history), 1)


if __name__ == "__main__":
    unittest.main()
