import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.early_life_loop import EarlyLifeLoop
from game.game_time import GameTime, current_game_time, advance_game_time
from game.location import Location
from game.player import Player
from game.poi import PointOfInterest
from game.world_memory import WorldMemoryStore


class DummyUI:
    def __init__(self):
        self.messages = []

    def add_log_message(self, message):
        self.messages.append(message)

    def add_message(self, message):
        self.messages.append(message)


class DummyGame:
    def __init__(self):
        self.GAME_LOG = DummyUI()
        self.world_memory = WorldMemoryStore()
        self._rebuilt = False

    def _advance_time_with_needs(self, minutes):
        advance_game_time(minutes)

    def _build_poi_venue_id_map(self):
        self._rebuilt = True


class TestEarlyLifeLoop(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 8
        current_game_time.minute = 0

        self.game = DummyGame()
        self.loop = EarlyLifeLoop(self.game)
        self.player = Player("Starter")
        self.player.money = 60
        self.player.energy = 90
        self.player.hunger = 10
        self.player.stress = 5

        self.location = Location("Asbury Park, NJ")
        home = PointOfInterest("asbury_home", "Home", "Home", category="HOME", parent_location_id="Asbury Park, NJ")
        self.location.add_poi(home)
        self.player.current_location = self.location
        self.player.current_poi = home

    def test_bootstrap_creates_grounded_job_sites(self):
        self.loop.bootstrap_player_jobs(self.player)
        categories = {poi.category for poi in self.location.points_of_interest}
        self.assertIn("JOB_RETAIL", categories)
        self.assertIn("JOB_WAREHOUSE", categories)
        self.assertIn("JOB_DINER", categories)
        self.assertIn("JOB_TEMP", categories)
        self.assertTrue(self.game._rebuilt)

    def test_shift_is_real_schedule_item_with_destination_and_presence(self):
        self.loop.bootstrap_player_jobs(self.player)
        result = self.loop.schedule_job_shift(self.player, "retail_corner_mart", start_time=GameTime(2024, 1, 1, 14, 0))
        self.assertTrue(result["ok"])
        item = self.player.schedule.scheduled_items[-1]
        self.assertEqual(item.category, "Job")
        self.assertTrue(item.requires_presence())
        self.assertEqual(item.get_destination_id(), result["destination_id"])

    def test_attendance_requires_presence_and_no_instant_payout(self):
        self.loop.bootstrap_player_jobs(self.player)
        before_money = self.player.money
        booked = self.loop.run_survival_shift(self.player, "delivery_shift")
        self.assertTrue(booked["ok"])
        self.assertEqual(self.player.money, before_money)

        event = self.player.schedule.scheduled_items[-1]
        current_game_time.year = event.start_time.year
        current_game_time.month = event.start_time.month
        current_game_time.day = event.start_time.day
        current_game_time.hour = event.start_time.hour
        current_game_time.minute = event.start_time.minute

        # At wrong place -> miss, no pay.
        outcome = self.loop.resolve_shift_event(self.player, event)
        self.assertEqual(outcome["status"], "missed")
        self.assertEqual(outcome["pay"], 0)

    def test_successful_shift_applies_clock_energy_pay_and_memory(self):
        self.loop.bootstrap_player_jobs(self.player)
        result = self.loop.schedule_job_shift(self.player, "retail_corner_mart", start_time=GameTime(2024, 1, 1, 10, 0))
        self.assertTrue(result["ok"])
        event = self.player.schedule.scheduled_items[-1]
        job_site = next(p for p in self.location.points_of_interest if p.poi_id == event.get_destination_id())
        self.player.current_poi = job_site

        start_money = self.player.money
        start_energy = self.player.energy

        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 10
        current_game_time.minute = 0

        outcome = self.loop.resolve_shift_event(self.player, event)
        self.assertIn(outcome["status"], {"job_shift_completed", "job_shift_late", "job_shift_partial"})
        self.assertGreater(self.player.money, start_money)
        self.assertLess(self.player.energy, start_energy)
        self.assertGreaterEqual(len(self.game.world_memory.entries), 1)
        self.assertEqual((current_game_time.hour, current_game_time.minute), (15, 0))

    def test_late_arrival_reduces_payout(self):
        self.loop.bootstrap_player_jobs(self.player)
        result = self.loop.schedule_job_shift(self.player, "retail_corner_mart", start_time=GameTime(2024, 1, 1, 9, 0))
        event = self.player.schedule.scheduled_items[-1]
        job_site = next(p for p in self.location.points_of_interest if p.poi_id == event.get_destination_id())
        self.player.current_poi = job_site

        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 11
        current_game_time.minute = 0

        outcome = self.loop.resolve_shift_event(self.player, event)
        self.assertIn(outcome["status"], {"job_shift_late", "job_shift_partial"})
        self.assertLess(outcome["pay"], event.details["shift_pay"])

    def test_shift_in_another_city_is_missed_when_absent(self):
        self.loop.bootstrap_player_jobs(self.player)
        result = self.loop.schedule_job_shift(self.player, "warehouse_distribution", start_time=GameTime(2024, 1, 1, 8, 0))
        event = self.player.schedule.scheduled_items[-1]
        other_city = Location("Philadelphia, PA")
        self.player.current_location = other_city
        self.player.current_poi = SimpleNamespace(poi_id="citycenter_square")

        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 8
        current_game_time.minute = 0

        outcome = self.loop.resolve_shift_event(self.player, event)
        self.assertEqual(outcome["status"], "missed")
        self.assertEqual(outcome["pay"], 0)
        self.assertEqual(result["destination_id"], event.details["destination_id"])


if __name__ == "__main__":
    unittest.main()
