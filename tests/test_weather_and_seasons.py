import unittest
from game.game_time import current_game_time
from game.weather_and_seasons import WeatherAndSeasonsSystem


class TestWeatherAndSeasons(unittest.TestCase):
    def setUp(self):
        current_game_time.month = 1 # Winter

    def test_winter_seasons_and_chicago_blizzard(self):
        sys = WeatherAndSeasonsSystem()
        self.assertEqual(sys.get_current_season(), "WINTER")

        chicago_rep = sys.get_city_weather("Chicago, IL")
        self.assertEqual(chicago_rep.season, "WINTER")
        self.assertEqual(chicago_rep.condition, "BLIZZARD")
        self.assertIn("Heavy snowfall", chicago_rep.travel_impact)

    def test_spring_cherry_blossom_in_tokyo(self):
        current_game_time.month = 4 # Spring
        sys = WeatherAndSeasonsSystem()
        self.assertEqual(sys.get_current_season(), "SPRING")

        tokyo_rep = sys.get_city_weather("Tokyo, Japan")
        self.assertEqual(tokyo_rep.condition, "CHERRY_BLOSSOM_BREEZE")
        self.assertIn("sakura", tokyo_rep.atmosphere_lore)


if __name__ == "__main__":
    unittest.main()
