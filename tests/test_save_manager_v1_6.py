import os
import unittest
from types import SimpleNamespace
from game.game import Game
from game.player import Player
from game.save_manager import JSONSaveManager
from game.album_system import AlbumRelease


class DummyUI:
    def add_log_message(self, msg):
        pass


class TestSaveManagerV1_6(unittest.TestCase):
    def setUp(self):
        self.game = Game(DummyUI())
        self.game.player = Player("DavidBowie")
        self.game.player.money = 500000
        self.game.player.fame = 300
        self.game.player.street_cred = 95
        self.game.player.current_location = SimpleNamespace(name="Berlin, Germany")

        # Stage production
        self.game.stage_production.purchase_and_equip_rig(self.game.player, "arena_spectacle_rig")

        # Reviews
        alb = AlbumRelease(
            album_id="alb_heroes",
            title="Heroes",
            artist="DavidBowie",
            track_ids=["t1", "t2"],
            tracks_data=[],
            format_type="VINYL",
            release_date_str="2024-05-01",
            release_day=1,
            overall_quality=0.98,
            concept_coherence=1.2,
        )
        self.game.music_press_reviews.generate_press_reviews_for_album(self.game.player, alb)

        # Podcasts
        self.game.press_podcasts.guest_on_podcast(self.game.player, "song_exploder", answer_style="auteur")

    def test_save_load_roundtrip_v1_6(self):
        save_file = "test_save_v1_6.json"
        saved = JSONSaveManager.save_game(self.game, filepath=save_file)
        self.assertTrue(saved)

        new_game = Game(DummyUI())
        loaded = JSONSaveManager.load_game(new_game, filepath=save_file)
        self.assertTrue(loaded)

        # Verify player
        self.assertEqual(new_game.player.name, "DavidBowie")

        # Verify Stage Rig
        self.assertEqual(new_game.stage_production.active_rig.rig_id, "arena_spectacle_rig")
        self.assertIn("arena_spectacle_rig", new_game.stage_production.owned_rig_ids)

        # Verify Reviews
        self.assertEqual(len(new_game.music_press_reviews.review_archive), 2)
        pf = next(r for r in new_game.music_press_reviews.review_archive if r.publication == "Pitchfork")
        self.assertEqual(pf.album_title, "Heroes")
        self.assertTrue(pf.is_best_new_music)

        # Verify Podcasts
        self.assertEqual(new_game.press_podcasts.persona.auteur_score, 35)
        self.assertEqual(len(new_game.press_podcasts.podcast_history), 1)

        if os.path.exists(save_file):
            os.remove(save_file)


if __name__ == "__main__":
    unittest.main()
