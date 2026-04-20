import unittest
from unittest.mock import patch

from game.delegation_roles import DelegationSystem
from game.player import Player
from game.inventory_loadout import RequirementAssessment
from game.world_memory import WorldMemoryStore


class TestDelegationRoles(unittest.TestCase):
    def setUp(self):
        self.system = DelegationSystem()
        self.player = Player("Delegator")
        self.system.ensure_player_support(self.player)
        self.memory = WorldMemoryStore()

    def test_manager_improves_opportunity_bias(self):
        self.system.add_or_update_role(self.player, "manager", competence=0.9, reliability=0.9)
        bonus, failure = self.system.manager_opportunity_bias(self.player, visibility_bias=12, reliability_bias=8)
        self.assertGreaterEqual(bonus, 10)
        self.assertIn(failure, {None, "manager_overbooked_pressure"})

    def test_assistant_success_and_failure_hooks(self):
        self.system.add_or_update_role(self.player, "assistant", competence=0.9, reliability=0.9)
        assessment = RequirementAssessment(status="missing_but_recoverable", missing=["strings"], missing_recoverable=["strings"])
        with patch("random.random", side_effect=[0.01]):
            updated, hook = self.system.assistant_adjust_requirements(self.player, assessment, "venue_1", self.memory)
        self.assertEqual(updated.status, "fully_satisfied")
        self.assertEqual(hook, "assistant_success")

        self.system.add_or_update_role(self.player, "assistant", competence=0.2, reliability=0.2)
        assessment2 = RequirementAssessment(status="missing_but_recoverable", missing=["strings"], missing_recoverable=["strings"])
        with patch("random.random", side_effect=[0.95, 0.01]):
            updated2, hook2 = self.system.assistant_adjust_requirements(self.player, assessment2, "venue_1", self.memory)
        self.assertEqual(updated2.status, "missing_but_recoverable")
        self.assertEqual(hook2, "assistant_prep_failure")

    def test_security_reduces_visibility_pressure(self):
        self.system.add_or_update_role(self.player, "security", competence=0.8, reliability=0.8)
        adjusted = self.system.security_adjust_visibility_pressure(self.player, 20.0, self.memory, "City A")
        self.assertLess(adjusted, 20.0)

    def test_driver_reduces_trip_burden_and_can_fail(self):
        self.system.add_or_update_role(self.player, "driver", competence=0.8, reliability=0.95)
        with patch("random.random", return_value=0.1):
            minutes, stress_mult, hook = self.system.driver_adjust_trip(self.player, 180, 1.0, self.memory, "route_1")
        self.assertLess(minutes, 180)
        self.assertLess(stress_mult, 1.0)
        self.assertEqual(hook, "driver_improved_trip_outcome")

        self.system.add_or_update_role(self.player, "driver", competence=0.5, reliability=0.1)
        with patch("random.random", return_value=0.9):
            minutes_fail, stress_fail, hook_fail = self.system.driver_adjust_trip(self.player, 180, 1.0, self.memory, "route_1")
        self.assertGreaterEqual(minutes_fail, 180)
        self.assertGreaterEqual(stress_fail, 1.0)
        self.assertEqual(hook_fail, "driver_unavailable")

    def test_delegation_does_not_bypass_truth(self):
        # Assistant should not magically satisfy severe missing mandatory requirements.
        self.system.add_or_update_role(self.player, "assistant", competence=0.95, reliability=0.95)
        severe = RequirementAssessment(status="missing_and_severe", missing=["instrument"], missing_severe=["instrument"])
        with patch("random.random", return_value=0.01):
            updated, hook = self.system.assistant_adjust_requirements(self.player, severe, "venue_1", self.memory)
        self.assertEqual(updated.status, "missing_and_severe")
        self.assertIsNone(hook)


if __name__ == "__main__":
    unittest.main()
