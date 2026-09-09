import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.game_time import current_game_time
from game.player import Player
from game.band import Band, BandMember
from game.save_manager import JSONSaveManager
from game.production_pipeline import ProductionPipelineSystem
from game.merch_system import MerchItem, MerchSystem
from game.rivals import simulate_rivals, get_news_feed
from game.ui_shell import PlayerUIShell


class TestAllFeaturesPackage(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 10
        current_game_time.minute = 0

        self.game = Game(None)
        self.game.setup_world()
        self.game.player = Player("Tester")

    def test_json_save_load_roundtrip(self):
        self.game.player.money = 1250
        self.game.player.street_cred = 85
        self.game.player.fame = 110

        merch_sys = MerchSystem()
        merch_sys.produce_merch(self.game.player, "diy_stickers")

        save_path = "test_savegame_temp.json"
        try:
            save_ok = JSONSaveManager.save_game(self.game, save_path)
            self.assertTrue(save_ok)
            self.assertTrue(os.path.exists(save_path))

            # Reset player state
            self.game.player.money = 0
            self.game.player.street_cred = 0

            load_ok = JSONSaveManager.load_game(self.game, save_path)
            self.assertTrue(load_ok)
            self.assertEqual(self.game.player.money, 1225)
            self.assertEqual(self.game.player.street_cred, 87) # 85 + 2 from merch production
            self.assertEqual(self.game.player.fame, 110)
        finally:
            if os.path.exists(save_path):
                os.remove(save_path)

    def test_production_pipeline_project_creation(self):
        pipeline = ProductionPipelineSystem(self.game)
        proj = pipeline.create_project(
            project_type="album",
            lead_artist_id=self.game.player.name,
            target_release="Debut Album",
        )
        self.assertIsNotNone(proj)
        self.assertEqual(proj.current_stage, "concept")

        # Work session
        updated = pipeline.apply_work_session(
            proj.project_id,
            minutes_spent=120,
            resource_quality=0.8,
            condition_score=0.8,
            pressure_level=0.1,
            interruption_level=0.0,
            budget_spend=100.0,
        )
        self.assertIsNotNone(updated)
        self.assertGreater(updated.quality_score, 0.0)

    def test_band_and_bandmate_recruitment(self):
        band = Band("The Echoes", self.game.player)
        mate = BandMember("Sam", "Bassist", skill_level=6, wage_demand=60)
        band.add_member(mate)

        self.assertEqual(len(band.members), 2)
        self.assertIn("Bassist", mate.role)

        band.remove_member(mate)
        self.assertEqual(len(band.members), 1)

    def test_ui_shell_top_context_badges(self):
        shell = PlayerUIShell(self.game)
        top = shell.top_context_bar()

        tags = top.get("tags", [])
        self.assertTrue(any("Street Cred" in t for t in tags))
        self.assertTrue(any("Fame" in t for t in tags))
        self.assertTrue(any("Cash" in t for t in tags))


if __name__ == "__main__":
    unittest.main()
