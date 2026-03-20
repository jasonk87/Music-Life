import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.player import Player


class DummyUI:
    def add_log_message(self, message):
        pass

    def add_message(self, message):
        pass


class TestOpportunityState(unittest.TestCase):
    def test_normalize_opportunity_state_converts_legacy_values(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        game.player.active_opportunities = {
            "tour_offer_test": "available",
            "radio_interview_local": {"status": "completed", "poi_id": "radio"},
        }

        game._normalize_opportunity_state()

        self.assertEqual(game.player.active_opportunities["tour_offer_test"]["status"], "available")
        self.assertEqual(game.player.active_opportunities["radio_interview_local"]["status"], "completed")
        self.assertEqual(game.player.active_opportunities["radio_interview_local"]["poi_id"], "radio")


if __name__ == "__main__":
    unittest.main()
