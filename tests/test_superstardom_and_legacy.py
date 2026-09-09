import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.player import Player
from game.song import Song
from game.npc import NPC
from game.game_time import current_game_time
from game.superstardom import SuperstardomSystem, RecordPlaque
from game.label_imprint import IndieLabelImprint


class TestSuperstardomAndLegacy(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 12
        current_game_time.day = 28
        current_game_time.hour = 10
        current_game_time.minute = 0

        self.game = Game(None)
        self.game.setup_world()
        self.game.player = Player("Rockstar")

    def test_record_certifications_and_plaques(self):
        hit_song = Song("Hit Anthem", "Rockstar", "Indie", song_quality=0.9)
        hit_song.is_released = True
        hit_song.buzz_score = 40
        self.game.player.songs_written.append(hit_song)
        self.game.player.fame = 200

        plaques = self.game.superstardom.check_certifications(self.game.player)
        self.assertGreater(len(plaques), 0)
        self.assertTrue(any(p.cert_type in {"Gold", "Platinum", "Diamond"} for p in plaques))

    def test_annual_music_awards(self):
        hit_song = Song("Award Winning Single", "Rockstar", "Rock", song_quality=0.95)
        hit_song.is_released = True
        hit_song.buzz_score = 60
        self.game.player.songs_written.append(hit_song)
        self.game.player.fame = 250

        award_result = self.game.superstardom.run_annual_music_awards(self.game.player)
        self.assertIsNotNone(award_result)
        self.assertTrue(award_result["won"])
        self.assertIn("Song of the Year", award_result["award"])

    def test_indie_label_imprint_roster_and_revenues(self):
        label = IndieLabelImprint("Rebel Sounds", "Rockstar")
        npc = NPC("npc_101", "Alex Vance", "Guitarist", "Philadelphia, PA", "looking_for_band", 7)
        npc.genre = "Punk"

        sign_res = label.sign_artist(npc, advance_amount=500)
        self.assertTrue(sign_res["ok"])
        self.assertIn("npc_101", label.roster)

        self.game.player.money = 1000
        release_res = label.fund_and_release_single(self.game, "npc_101", budget=400)
        self.assertTrue(release_res["ok"])
        self.assertGreater(release_res["label_share"], 0)
        self.assertGreater(self.game.player.money, 600)


if __name__ == "__main__":
    unittest.main()
