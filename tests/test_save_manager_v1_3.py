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


class TestSaveManagerV1_3(unittest.TestCase):
    def setUp(self):
        self.game = Game(DummyUI())
        self.game.player = Player("Bowie")
        self.game.player.money = 600000
        self.game.player.fame = 200
        self.game.player.street_cred = 90
        self.game.player.current_location = SimpleNamespace(name="New York City, NY")

        # Major label deal in NYC
        self.game.major_label_system.negotiate_and_sign_contract(self.game.player, "empire_nyc")

        # Late Night TV performance
        self.game.media_and_festivals_system.perform_late_night_tv(self.game.player, "tonight_30rock", "Heroes")

        # Vintage gear purchase in NYC
        self.game.vintage_gear_network.purchase_vintage_grail(self.game.player, "studer_a800_nyc")

        # Billboard chart entry
        s = Song("Heroes", "Bowie", "Rock", song_quality=0.95)
        s.is_recorded = True
        s.recording_quality = 0.98
        s.is_released = True
        self.game.player.songs_written = [s]
        self.game.billboard_charts.update_weekly_billboard_hot_100(self.game.player, [s])

    def test_save_load_roundtrip_v1_3(self):
        save_file = "test_save_v1_3.json"
        saved = JSONSaveManager.save_game(self.game, filepath=save_file)
        self.assertTrue(saved)

        new_game = Game(DummyUI())
        loaded = JSONSaveManager.load_game(new_game, filepath=save_file)
        self.assertTrue(loaded)

        # Verify player
        self.assertEqual(new_game.player.name, "Bowie")

        # Verify Major Label deal
        self.assertIsNotNone(new_game.major_label_system.signed_contract)
        self.assertEqual(new_game.major_label_system.signed_contract.label_name, "Empire Records International")
        self.assertEqual(new_game.major_label_system.signed_contract.advance_amount, 500000)

        # Verify TV performances
        self.assertEqual(len(new_game.media_and_festivals_system.tv_performances_logged), 1)
        self.assertEqual(new_game.media_and_festivals_system.tv_performances_logged[0]["show_name"], "The Tonight Broadcast Live")

        # Verify Vintage Gear
        self.assertEqual(len(new_game.vintage_gear_network.owned_grails), 1)
        self.assertEqual(new_game.vintage_gear_network.owned_grails[0].gear_id, "studer_a800_nyc")

        # Verify Billboard Charts
        self.assertTrue(len(new_game.billboard_charts.chart_entries) > 0)

        if os.path.exists(save_file):
            os.remove(save_file)


if __name__ == "__main__":
    unittest.main()
