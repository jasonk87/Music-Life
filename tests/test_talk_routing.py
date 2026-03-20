import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.npc import NPC
from game.player import Player
from game.poi import PointOfInterest


class DummyUI:
    def add_log_message(self, message):
        pass

    def add_message(self, message):
        pass


class TestTalkRouting(unittest.TestCase):
    def test_owner_talk_routes_directly_to_owner_interaction(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        owner = NPC("owner_1", "Vic Vega", "gruff_club_owner")
        venue = PointOfInterest("venue", "Venue", "Club", category="VENUE_CLUB")
        venue.owner_npc_id = owner
        game.selected_poi = venue

        game.handle_interaction("Talk to the owner")

        self.assertEqual(game.explore_menu_state, "npc_interaction_menu")
        self.assertIs(game.selected_npc, owner)
        self.assertIn(owner.npc_id, game.player.contacts)


if __name__ == "__main__":
    unittest.main()
