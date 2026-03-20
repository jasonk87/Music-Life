import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.player import Player
from game.poi import PointOfInterest


class DummyUI:
    def add_log_message(self, message):
        pass

    def add_message(self, message):
        pass


class TestCityCenterFlow(unittest.TestCase):
    def test_rent_room_sets_rental_info(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        motel = PointOfInterest("motel", "Sleep EZ Motel", "Cheap room", category="ACCOMMODATION_CHEAP")
        game.selected_poi = motel
        game.player.money = 100

        game.handle_interaction("Rent Room ($50/night)")

        self.assertEqual(game.player.money, 50)
        self.assertEqual(game.player.rented_accommodation_info["poi_id"], "motel")

    def test_pr_representation_requires_fame_threshold(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        game.player.fame = 100

        game.handle_interaction("Inquire about PR representation")

        self.assertTrue(game.player.has_pr_manager)


if __name__ == "__main__":
    unittest.main()
