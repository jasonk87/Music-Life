import os
import unittest
from types import SimpleNamespace
from game.game import Game
from game.player import Player
from game.save_manager import JSONSaveManager


class DummyUI:
    def add_log_message(self, msg):
        pass


class TestSaveManagerV1_9(unittest.TestCase):
    def setUp(self):
        self.game = Game(DummyUI())
        self.game.player = Player("Superstar")
        self.game.player.money = 100000
        self.game.player.current_location = SimpleNamespace(name="Tokyo, Japan")

        # Setup v1.9 state
        self.game.international_touring.apply_for_artist_visa(self.game.player, "Tokyo, Japan")
        self.game.international_touring.purchase_ata_carnet_customs_bond(self.game.player)
        self.game.physical_vinyl_drops.launch_webstore_variant_drop(self.game.player, "Tokyo Night", units=100)

    def test_save_load_roundtrip_v1_9(self):
        save_file = "test_save_v1_9.json"
        saved = JSONSaveManager.save_game(self.game, filepath=save_file)
        self.assertTrue(saved)

        new_game = Game(DummyUI())
        loaded = JSONSaveManager.load_game(new_game, filepath=save_file)
        self.assertTrue(loaded)

        self.assertEqual(new_game.player.name, "Superstar")
        self.assertTrue(new_game.international_touring.has_ata_carnet_bond)
        self.assertIn("japan_entertainment", new_game.international_touring.active_visas)
        self.assertEqual(len(new_game.physical_vinyl_drops.active_webstore_drops), 1)

        if os.path.exists(save_file):
            os.remove(save_file)


if __name__ == "__main__":
    unittest.main()
