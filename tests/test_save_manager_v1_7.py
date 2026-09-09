import os
import unittest
from types import SimpleNamespace
from game.game import Game
from game.player import Player
from game.save_manager import JSONSaveManager


class DummyUI:
    def add_log_message(self, msg):
        pass


class TestSaveManagerV1_7(unittest.TestCase):
    def setUp(self):
        self.game = Game(DummyUI())
        self.game.player = Player("Dylan")
        self.game.player.money = 100000
        self.game.player.current_location = SimpleNamespace(name="Asbury Park, NJ")

        # Talk & gift Sal
        self.game.npc_system.talk_with_npc(self.game.player, "sal_moretti", topic="gear_talk")
        self.game.npc_system.give_gift_to_npc(self.game.player, "sal_moretti", "vintage_whiskey")

    def test_save_load_roundtrip_v1_7(self):
        save_file = "test_save_v1_7.json"
        saved = JSONSaveManager.save_game(self.game, filepath=save_file)
        self.assertTrue(saved)

        new_game = Game(DummyUI())
        loaded = JSONSaveManager.load_game(new_game, filepath=save_file)
        self.assertTrue(loaded)

        # Verify player
        self.assertEqual(new_game.player.name, "Dylan")

        # Verify Sal's state
        sal = new_game.npc_system.get_npc("sal_moretti")
        self.assertIsNotNone(sal)
        self.assertEqual(sal.affinity, 43.0)  # 10 + 8 (gear_talk) + 25 (whiskey) = 43
        self.assertEqual(len(sal.memories), 2)

        if os.path.exists(save_file):
            os.remove(save_file)


if __name__ == "__main__":
    unittest.main()
