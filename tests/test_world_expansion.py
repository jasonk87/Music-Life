import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.player import Player


class TestWorldExpansion(unittest.TestCase):
    def setUp(self):
        self.game = Game(None)
        self.game.setup_world()
        self.game.player = Player("Globetrotter")

    def test_all_fifteen_cities_loaded(self):
        expected_cities = [
            "Asbury Park, NJ",
            "Philadelphia, PA",
            "Austin, TX",
            "Nashville, TN",
            "Seattle, WA",
            "New York City, NY",
            "Los Angeles, CA",
            "Chicago, IL",
            "New Orleans, LA",
            "Memphis, TN",
            "Detroit, MI",
            "Atlanta, GA",
            "London, UK",
            "Tokyo, Japan",
            "Berlin, Germany",
        ]

        for city_name in expected_cities:
            loc = self.game.WORLD_MAP.get(city_name)
            self.assertIsNotNone(loc, f"Missing city: {city_name}")
            self.assertGreater(len(loc.points_of_interest), 0, f"No POIs in {city_name}")
            self.assertGreater(len(loc.venues), 0, f"No Venues in {city_name}")

    def test_transport_hub_in_every_city(self):
        for city_name, loc in self.game.WORLD_MAP.items():
            categories = [p.category for p in loc.points_of_interest]
            self.assertIn("TRANSPORT_HUB", categories, f"Missing TRANSPORT_HUB in {city_name}")

    def test_intercity_travel_connections(self):
        hometown = self.game.WORLD_MAP["Asbury Park, NJ"]
        self.assertGreater(len(hometown.travel_connections), 0)
        target_name = list(hometown.travel_connections.keys())[0]
        self.assertIn(target_name, self.game.WORLD_MAP)


if __name__ == "__main__":
    unittest.main()
