import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.player import Player
from game.sound import SoundManager
from game.festival_system import FestivalSystem
from game.social_media_drama import SocialMediaDramaSystem
from game.pygame_ui import PygameUI


class TestFestivalsAndAudio(unittest.TestCase):
    def setUp(self):
        self.game = Game(None)
        self.game.setup_world()
        self.game.player = Player("Tester")

    def test_sound_manager_buffers(self):
        sm = SoundManager()
        self.assertIsNotNone(sm.create_chime_buffer())
        self.assertIsNotNone(sm.create_noise_burst_buffer())
        self.assertIsNotNone(sm.create_rumble_buffer())

        # Should execute silently without exception
        sm.play_cash_sound()
        sm.play_cheer_sound()
        sm.play_boo_sound()
        sm.play_rhythm_beat()

    def test_festival_system_tournament_bracket(self):
        fest = FestivalSystem()
        self.game.player.money = 200

        res = fest.start_tournament(self.game, "battle_of_the_bands_hometown")
        self.assertTrue(res["ok"])
        self.assertEqual(self.game.player.money, 150)
        self.assertIsNotNone(self.game.active_tournament)

        # Win round 1
        r1 = fest.advance_tournament_round(self.game, 15.0)
        self.assertTrue(r1["ok"])
        self.assertFalse(r1["tournament_complete"])

        # Win round 2
        r2 = fest.advance_tournament_round(self.game, 16.0)
        self.assertTrue(r2["ok"])

        # Win round 3 (Finals)
        r3 = fest.advance_tournament_round(self.game, 20.0)
        self.assertTrue(r3["ok"])
        self.assertTrue(r3["tournament_complete"])
        self.assertIsNone(self.game.active_tournament)

    def test_social_media_drama_resolution(self):
        drama = SocialMediaDramaSystem()
        self.game.player.street_cred = 50

        # PR choices
        apology = drama.resolve_pr_press_conference(self.game.player, "apologize")
        self.assertEqual(self.game.player.street_cred, 45)

        defiant = drama.resolve_pr_press_conference(self.game.player, "lean_in")
        self.assertEqual(self.game.player.street_cred, 53)

    def test_pygame_ui_hype_gauge(self):
        ui = PygameUI()
        # Draw hype gauge should execute cleanly
        ui.draw_crowd_hype_gauge(75.0, 40, 180)


if __name__ == "__main__":
    unittest.main()
