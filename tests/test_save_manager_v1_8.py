import os
import unittest
from types import SimpleNamespace
from game.game import Game
from game.player import Player
from game.save_manager import JSONSaveManager
from game.dynamic_musicians import AutonomousMusician


class DummyUI:
    def add_log_message(self, msg):
        pass


class TestSaveManagerV1_8(unittest.TestCase):
    def setUp(self):
        self.game = Game(DummyUI())
        self.game.player = Player("MickJagger")
        self.game.player.money = 250000
        self.game.player.fame = 400
        self.game.player.current_location = SimpleNamespace(name="London, UK")

        # Interact with Elena Fox in London
        elena = self.game.dynamic_musicians.musicians["ai_elena_fox"]
        elena.affinity_with_player = 65.0
        elena.co_headlining_with_player = True

    def test_save_load_roundtrip_v1_8(self):
        save_file = "test_save_v1_8.json"
        saved = JSONSaveManager.save_game(self.game, filepath=save_file)
        self.assertTrue(saved)

        new_game = Game(DummyUI())
        loaded = JSONSaveManager.load_game(new_game, filepath=save_file)
        self.assertTrue(loaded)

        # Verify player
        self.assertEqual(new_game.player.name, "MickJagger")

        # Verify dynamic musician persistence
        elena = new_game.dynamic_musicians.musicians["ai_elena_fox"]
        self.assertIsNotNone(elena)
        self.assertEqual(elena.affinity_with_player, 65.0)
        self.assertTrue(elena.co_headlining_with_player)
        self.assertEqual(len(elena.catalog), 2)

        if os.path.exists(save_file):
            os.remove(save_file)


if __name__ == "__main__":
    unittest.main()
