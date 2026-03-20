import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from game.game import Game
from game.pygame_ui import PygameUI


class TestBootstrap(unittest.TestCase):
    def test_game_world_initializes(self):
        ui = PygameUI()
        try:
            game = Game(ui)
            self.assertTrue(game.setup_world())
            game.initialize_player()

            self.assertEqual(game.game_state, "character_creation")
            self.assertGreaterEqual(len(game.WORLD_MAP), 1)
            self.assertGreaterEqual(len(game.NPC_REGISTRY), 1)
            self.assertGreaterEqual(len(game.ACTIVE_CHARTS), 1)
            self.assertIsNotNone(game.player)
            self.assertIsNotNone(game.player.current_location)
        finally:
            pygame.quit()

    def test_title_screen_new_game_enters_character_creation(self):
        ui = PygameUI()
        try:
            game = Game(ui)
            game.setup_world()
            ui.present_choices = lambda options, title, context=None: "new_game"

            game.handle_title_screen()

            self.assertEqual(game.game_state, "character_creation")
            self.assertIsNotNone(game.player)
            self.assertIsNotNone(game.player.current_poi)
        finally:
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
