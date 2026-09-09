import os
import unittest
from types import SimpleNamespace
from game.game import Game
from game.player import Player
from game.save_manager import JSONSaveManager
from game.song import Song


class DummyUI:
    def add_log_message(self, msg):
        pass


class TestSaveManagerV1_4(unittest.TestCase):
    def setUp(self):
        self.game = Game(DummyUI())
        self.game.player = Player("Freddie")
        self.game.player.money = 500000
        self.game.player.fame = 250
        self.game.player.street_cred = 95
        self.game.player.current_location = SimpleNamespace(name="Los Angeles, CA")

        # Sync deal
        s = Song("Bohemian Rhapsody", "Freddie", "Rock", song_quality=0.98)
        s.is_recorded = True
        s.recording_quality = 0.99
        self.game.player.songs_written = [s]
        self.game.sync_licensing_system.pitch_song_for_sync(self.game.player, s, "hollywood_blockbuster")

        # Wellness
        self.game.wellness_and_vices_system.profile.sobriety_streak_days = 45
        self.game.wellness_and_vices_system.profile.vocal_coaching_level = 3

        # Finance
        self.game.finance_and_legal_system.hire_entertainment_cpa(self.game.player, "beverly_hills_cpa")

        # Tour Logistics
        self.game.tour_logistics_system.lease_tour_bus(self.game.player)
        self.game.tour_logistics_system.hire_crew_member(self.game.player, "foh_engineer")

        # Gear maintenance
        self.game.gear_maintenance_system.hire_luthier_guitar_setup(self.game.player, "tube_amp_biasing")

        # Fan Club
        self.game.fan_club_and_pr_system.launch_vip_fan_club(self.game.player)

    def test_save_load_roundtrip_v1_4(self):
        save_file = "test_save_v1_4.json"
        saved = JSONSaveManager.save_game(self.game, filepath=save_file)
        self.assertTrue(saved)

        new_game = Game(DummyUI())
        loaded = JSONSaveManager.load_game(new_game, filepath=save_file)
        self.assertTrue(loaded)

        # Verify player
        self.assertEqual(new_game.player.name, "Freddie")

        # Verify Sync licensing
        self.assertEqual(len(new_game.sync_licensing_system.active_placements), 1)
        self.assertEqual(new_game.sync_licensing_system.active_placements[0].song_title, "Bohemian Rhapsody")

        # Verify Wellness
        self.assertEqual(new_game.wellness_and_vices_system.profile.sobriety_streak_days, 45)
        self.assertEqual(new_game.wellness_and_vices_system.profile.vocal_coaching_level, 3)

        # Verify CPA
        self.assertIsNotNone(new_game.finance_and_legal_system.hired_cpa)
        self.assertEqual(new_game.finance_and_legal_system.hired_cpa.name, "Sterling Business Management")

        # Verify Tour Logistics
        self.assertIsNotNone(new_game.tour_logistics_system.tour_bus)
        self.assertTrue(new_game.tour_logistics_system.tour_bus.is_leased)
        self.assertEqual(len(new_game.tour_logistics_system.hired_crew), 1)

        # Verify Gear Maintenance
        self.assertTrue(new_game.gear_maintenance_system.maintenance_status.tube_amp_bias_ok)

        # Verify Fan Club
        self.assertTrue(new_game.fan_club_and_pr_system.is_club_launched)
        self.assertGreater(new_game.fan_club_and_pr_system.tiers["tier_bronze"].subscribers_count, 0)

        if os.path.exists(save_file):
            os.remove(save_file)


if __name__ == "__main__":
    unittest.main()
