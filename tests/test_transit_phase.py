import unittest
from unittest.mock import patch

from game.delegation_roles import DelegationSystem
from game.game_time import current_game_time, GameTime, advance_game_time
from game.location import Location
from game.obligation_resolver import ObligationResolver
from game.player import Player
from game.player_schedule import PlayerSchedule
from game.poi import PointOfInterest
from game.transit_phase import TransitLayer
from game.visibility_system import VisibilitySystem
from game.world_memory import WorldMemoryStore


class FakeTravelManager:
    def __init__(self, player, destination, hours=3, transport_mode="bus", vehicle=None, ticket_class="economy"):
        self.player = player
        self.destination = destination
        self.transport_mode = transport_mode
        self.ticket_class = ticket_class
        self.vehicle = vehicle
        self.current_speed = 60.0
        self.distance_total = hours * 60.0
        self.distance_covered = 0.0
        self.travel_time_elapsed = 0.0

    def advance_one_hour(self):
        self.travel_time_elapsed += 1
        self.distance_covered = min(self.distance_total, self.distance_covered + 60.0)
        self.player.energy = max(0, self.player.energy - 1)
        return [], self.distance_covered >= self.distance_total

    def get_progress_percent(self):
        if self.distance_total <= 0:
            return 1.0
        return min(1.0, self.distance_covered / self.distance_total)


class DummyVehicle:
    def __init__(self, name="Sedan"):
        self.name = name


class DummyGame:
    def __init__(self):
        self.player = Player("Hero")
        self.player.schedule = PlayerSchedule()
        self.player.current_location = Location("Home City", "Home")
        home = PointOfInterest("home_hub", "Home Hub", "Hub", category="TRANSPORT_BUS")
        self.player.current_location.add_poi(home)
        self.player.current_poi = home
        self.player.active_opportunities = {}

        self.delegation_system = DelegationSystem()
        self.delegation_system.ensure_player_support(self.player)
        self.visibility_system = VisibilitySystem()
        self.world_memory = WorldMemoryStore()
        self.NPC_REGISTRY = {}
        self.WORLD_MAP = {}

        self._forced_assessment = None
        self.obligation_resolver = ObligationResolver(self)

    def _advance_time_with_needs(self, minutes):
        advance_game_time(minutes)

    def _assess_gig_requirements(self):
        return self._forced_assessment


class StubAssessment:
    def __init__(self, status, missing=None, missing_severe=None):
        self.status = status
        self.missing = list(missing or [])
        self.missing_severe = list(missing_severe or [])


class TestTransitPhase(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 8
        current_game_time.minute = 0

        self.game = DummyGame()
        self.layer = TransitLayer()
        self.destination = Location("Tour City", "Elsewhere")
        self.destination.add_poi(PointOfInterest("dest_hub", "Arrival Hub", "Hub", category="TRANSPORT_BUS"))

    def test_chunked_travel_progression_advances_world_time(self):
        tm = FakeTravelManager(self.game.player, self.destination, hours=3)
        session = self.layer.start_session(tm)
        before = current_game_time.copy()

        result = self.layer.execute_chunk(self.game, tm, session, "wait")

        self.assertFalse(result["arrived"])
        self.assertEqual(tm.travel_time_elapsed, 1)
        self.assertEqual((current_game_time.hour - before.hour) % 24, 1)

    def test_transit_action_effects_change_player_state(self):
        tm = FakeTravelManager(self.game.player, self.destination, hours=2)
        session = self.layer.start_session(tm)
        self.game.player.energy = 40

        self.layer.execute_chunk(self.game, tm, session, "sleep")

        self.assertGreater(self.game.player.energy, 40)

    def test_travel_context_limits_actions(self):
        tm = FakeTravelManager(self.game.player, self.destination, hours=2, transport_mode="car", vehicle=DummyVehicle("Sedan"))

        actions = self.layer.available_actions(self.game, tm)

        self.assertNotIn("call", actions)
        self.assertNotIn("sleep", actions)

    def test_driver_delegation_expands_transit_bandwidth(self):
        tm = FakeTravelManager(self.game.player, self.destination, hours=2, transport_mode="car", vehicle=DummyVehicle("Sedan"))
        self.game.delegation_system.add_or_update_role(self.game.player, "driver", competence=0.8, reliability=0.9)

        actions = self.layer.available_actions(self.game, tm)

        self.assertIn("call", actions)
        self.assertIn("sleep", actions)

    def test_visibility_pressure_can_trigger_transit_interruption(self):
        tm = FakeTravelManager(self.game.player, self.destination, hours=2)
        session = self.layer.start_session(tm)
        self.game.visibility_system.entity_visibility[self.game.player.name] = {
            "base_visibility": 25.0,
            "recent_buzz": 20.0,
            "negative_pressure": 8.0,
        }
        before_stress = self.game.player.stress

        with patch("game.transit_phase.random.random", return_value=0.0):
            result = self.layer.execute_chunk(self.game, tm, session, "wait")

        self.assertGreater(self.game.player.stress, before_stress)
        self.assertTrue(any("Transit interruption" in m for m in result["logs"]))

    def test_arrival_state_affects_downstream_readiness(self):
        tm = FakeTravelManager(self.game.player, self.destination, hours=1)
        session = self.layer.start_session(tm)
        self.game.player.energy = 10

        self.layer.execute_chunk(self.game, tm, session, "drink")

        risk_flags = self.game.obligation_resolver._readiness_risk_flags()
        self.assertIn("energy_risk_threshold_high", risk_flags)


if __name__ == "__main__":
    unittest.main()
