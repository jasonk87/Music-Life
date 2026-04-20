import random
import unittest
from unittest.mock import patch

from game.delegation_roles import DelegationSystem
from game.game_time import current_game_time
from game.location import Location
from game.player import Player
from game.scarcity_interference import ScarcityAvailabilitySystem, PublicInterferenceSystem
from game.transit_phase import TransitLayer
from game.visibility_system import VisibilitySystem
from game.world_memory import WorldMemoryStore, WorldMemoryEntry


class DummyGame:
    def __init__(self):
        self.player = Player("Hero")
        self.player.current_location = Location("Austin", "TX")
        self.world_memory = WorldMemoryStore()
        self.visibility_system = VisibilitySystem()


class TestScarcityInterference(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 12
        current_game_time.minute = 0

        self.game = DummyGame()
        self.scarcity = ScarcityAvailabilitySystem()
        self.interference = PublicInterferenceSystem()
        self.delegation = DelegationSystem()
        self.delegation.ensure_player_support(self.game.player)

    def test_hotel_scarcity_under_demand_pressure(self):
        low_pressure = self.scarcity.check_hotel_availability("Austin", "budget", lead_hours=24, demand_pressure=0.9, rng=random.Random(1))
        high_pressure = self.scarcity.check_hotel_availability("Austin", "budget", lead_hours=24, demand_pressure=2.4, rng=random.Random(1))

        self.assertLess(high_pressure["score"], low_pressure["score"])
        self.assertGreaterEqual(high_pressure["price_multiplier"], low_pressure["price_multiplier"])

    def test_better_assistant_quality_improves_booking_outcomes(self):
        self.delegation.add_or_update_role(self.game.player, "assistant", competence=0.88, reliability=0.9, experience=0.86)
        high_assistant = self.delegation.get_role(self.game.player, "assistant")
        high_quality = self.delegation.role_quality(high_assistant)

        low_score = self.scarcity.check_hotel_availability("Los Angeles", "premium", lead_hours=10, demand_pressure=1.9, assistant_quality=0.2, rng=random.Random(2))
        high_score = self.scarcity.check_hotel_availability("Los Angeles", "premium", lead_hours=10, demand_pressure=1.9, assistant_quality=high_quality, rng=random.Random(2))

        self.assertGreater(high_score["score"], low_score["score"])

    def test_low_quality_assistant_under_pressure_worse_than_high_quality(self):
        low_success = 0
        high_success = 0
        for i in range(80):
            low = self.scarcity.attempt_hotel_booking(self.game, "Los Angeles", "premium", lead_hours=3, assistant_quality=0.15, rng=random.Random(i))
            high = self.scarcity.attempt_hotel_booking(self.game, "Los Angeles", "premium", lead_hours=3, assistant_quality=0.9, rng=random.Random(i))
            low_success += int(low.success)
            high_success += int(high.success)

        self.assertGreater(high_success, low_success)

    def test_assistant_planning_books_and_records_meaningful_hooks(self):
        self.delegation.add_or_update_role(self.game.player, "assistant", competence=0.85, reliability=0.88, experience=0.82)
        outcome = self.delegation.assistant_plan_lodging(
            player=self.game.player,
            scarcity_system=self.scarcity,
            game=self.game,
            city="Austin",
            preferred_tier="standard",
            lead_hours=12,
            world_memory=self.game.world_memory,
            rng=random.Random(5),
        )

        self.assertTrue(outcome.success)
        hooks = [e.event_type for e in self.game.world_memory.entries]
        self.assertIn("assistant_secured_booking", hooks)

    def test_manual_booking_still_possible_without_assistant(self):
        result = self.scarcity.attempt_hotel_booking(
            self.game,
            city="Austin",
            preferred_tier="standard",
            lead_hours=72,
            assistant_quality=0.0,
            world_memory=self.game.world_memory,
            rng=random.Random(4),
        )
        self.assertTrue(result.success)

    def test_security_posture_changes_interference_pressure(self):
        open_pressure = self.interference.interference_pressure(24.0, "downtown", "high", security_quality=0.55, security_posture="open")
        filtered_pressure = self.interference.interference_pressure(24.0, "downtown", "high", security_quality=0.55, security_posture="filtered")
        locked_pressure = self.interference.interference_pressure(24.0, "downtown", "high", security_quality=0.55, security_posture="locked")

        self.assertGreater(open_pressure, filtered_pressure)
        self.assertGreater(filtered_pressure, locked_pressure)

    def test_driver_quality_affects_travel_burden_and_bandwidth(self):
        # Travel burden
        self.delegation.add_or_update_role(self.game.player, "driver", competence=0.25, reliability=0.3, experience=0.2)
        with patch("random.random", return_value=0.05):
            low_minutes, low_stress, _ = self.delegation.driver_adjust_trip(self.game.player, 240, 1.0)

        self.delegation.add_or_update_role(self.game.player, "driver", competence=0.9, reliability=0.9, experience=0.85)
        with patch("random.random", return_value=0.05):
            high_minutes, high_stress, _ = self.delegation.driver_adjust_trip(self.game.player, 240, 1.0)

        self.assertLess(high_minutes, low_minutes)
        self.assertLess(high_stress, low_stress)

        # Bandwidth in transit actions (self-driving context)
        layer = TransitLayer()

        class Vehicle:
            name = "Sedan"

        class TM:
            vehicle = Vehicle()
            transport_mode = "car"
            ticket_class = "economy"

        actions = layer.available_actions(self.game, TM())
        self.assertIn("call", actions)  # high-quality driver allows passenger-like bandwidth

    def test_manager_quality_improves_opportunity_bias_without_state_bypass(self):
        self.game.player.active_opportunities = {}

        self.delegation.add_or_update_role(self.game.player, "manager", competence=0.2, reliability=0.25, experience=0.2)
        low_bonus, _ = self.delegation.manager_opportunity_bias(self.game.player, visibility_bias=8, reliability_bias=4)

        self.delegation.add_or_update_role(self.game.player, "manager", competence=0.9, reliability=0.92, experience=0.88)
        high_bonus, _ = self.delegation.manager_opportunity_bias(self.game.player, visibility_bias=8, reliability_bias=4)

        self.assertGreater(high_bonus, low_bonus)
        self.assertEqual(self.game.player.active_opportunities, {})  # bias only, no automatic truth mutation


if __name__ == "__main__":
    unittest.main()
