import unittest
from game.player import Player
from game.song import Song
from game.label_imprint import IndieLabelImprint
from game.dynamic_musicians import AutonomousMusician
from game.dynamic_musician_interactions import DynamicMusicianInteractions


class TestDynamicMusicianInteractions(unittest.TestCase):
    def setUp(self):
        self.player = Player("TourMate")
        self.player.money = 20000
        self.player.fame = 100
        self.player.stress = 50

        self.musician = AutonomousMusician(
            artist_id="ai_test_band",
            name="The Cosmic Echoes",
            band_type="4_PIECE_BAND",
            genre="Psychedelic Rock",
            skill_level=8,
            fame=110,
            funds=3000,
            current_city="Austin, TX",
            affinity_with_player=15.0,
        )

        self.song = Song("Desert Astral Jam", "TourMate", "Psychedelic Rock", song_quality=0.75)

    def test_hang_out_and_jam(self):
        chat_res = DynamicMusicianInteractions.hang_out_and_chat(self.player, self.musician)
        self.assertTrue(chat_res["ok"])
        self.assertEqual(self.musician.affinity_with_player, 27.0)
        self.assertEqual(self.player.stress, 35)

        # Backstage co-writing jam
        jam_res = DynamicMusicianInteractions.jam_and_cowrite_song(self.player, self.musician, self.song)
        self.assertTrue(jam_res["ok"])
        self.assertGreater(self.song.song_quality, 0.85)

    def test_coheadlining_and_label_signing(self):
        self.musician.affinity_with_player = 55.0

        # Co-headlining tour
        tour_res = DynamicMusicianInteractions.propose_coheadlining_tour(self.player, self.musician)
        self.assertTrue(tour_res["ok"])
        self.assertTrue(self.musician.co_headlining_with_player)

        # Label signing
        label = IndieLabelImprint("Subterranean Records", self.player.name)
        sign_res = DynamicMusicianInteractions.sign_to_player_label_imprint(self.player, label, self.musician)
        self.assertTrue(sign_res["ok"])
        self.assertTrue(self.musician.is_signed_to_player_label)
        self.assertIn("ai_test_band", label.roster)


if __name__ == "__main__":
    unittest.main()
