import unittest
from game.dynamic_musicians import DynamicWorldMusiciansSystem, AutonomousMusician


class TestDynamicMusicians(unittest.TestCase):
    def setUp(self):
        self.sys = DynamicWorldMusiciansSystem()

    def test_get_musicians_in_city_and_poi(self):
        asbury_musicians = self.sys.get_musicians_in_city("Asbury Park, NJ")
        self.assertEqual(len(asbury_musicians), 1)
        self.assertEqual(asbury_musicians[0].name, "The Nightjars")

        pony_musicians = self.sys.get_musicians_at_poi("the_stone_pony")
        self.assertEqual(len(pony_musicians), 1)
        self.assertEqual(pony_musicians[0].artist_id, "ai_nightjars")

    def test_daily_ai_simulation_tick(self):
        initial_logs = self.sys.tick_daily_world_musicians()
        self.assertGreater(len(initial_logs), 0)

        # Force a musician into transit and tick
        nightjars = self.sys.musicians["ai_nightjars"]
        nightjars.status = "IN_TRANSIT"
        nightjars.travel_days_left = 1
        nightjars.destination_city = "Philadelphia, PA"

        transit_logs = self.sys.tick_daily_world_musicians()
        self.assertEqual(nightjars.current_city, "Philadelphia, PA")
        self.assertEqual(nightjars.status, "TOURING")


if __name__ == "__main__":
    unittest.main()
