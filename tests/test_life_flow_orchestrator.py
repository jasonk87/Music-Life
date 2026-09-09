import unittest

from game.delegation_roles import DelegationSystem
from game.game_time import current_game_time
from game.life_flow_orchestrator import LifeFlowOrchestrator
from game.location import Location
from game.organization_contracts import OrganizationContractSystem
from game.player import Player
from game.player_schedule import PlayerSchedule
from game.poi import PointOfInterest
from game.production_pipeline import ProductionPipelineSystem
from game.visibility_system import VisibilitySystem
from game.world_memory import WorldMemoryStore


class DummyGame:
    def __init__(self):
        self.player = Player("Hero")
        self.player.schedule = PlayerSchedule()
        self.player.current_location = Location("Philadelphia, PA", "Metro")
        self.player.current_poi = PointOfInterest("downtown", "Downtown", "Scene", category="POI_STREET")
        self.player.current_location.add_poi(self.player.current_poi)

        self.world_memory = WorldMemoryStore()
        self.visibility_system = VisibilitySystem()
        self.delegation_system = DelegationSystem()
        self.delegation_system.ensure_player_support(self.player)

        self.NPC_REGISTRY = {}
        self.organization_contracts = OrganizationContractSystem(self)
        self.production_pipeline = ProductionPipelineSystem(self)
        self.life_flow = LifeFlowOrchestrator(self)


class TestLifeFlowOrchestrator(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 10
        current_game_time.minute = 0
        self.game = DummyGame()

    def test_early_game_has_lower_density_and_overlap(self):
        self.game.player.fame = 2
        early = self.game.life_flow.snapshot()

        self.assertLess(early.intensity, 0.35)
        self.assertLess(early.collision_allowance, 0.4)

    def test_high_visibility_and_contract_state_raise_overlap_allowance(self):
        self.game.player.fame = 140
        self.game.visibility_system.entity_visibility[self.game.player.name] = {
            "base_visibility": 25.0,
            "recent_buzz": 18.0,
            "negative_pressure": 2.0,
        }
        self.game.organization_contracts.create_organization("label_a", "Apex")
        self.game.organization_contracts.sign_contract("label_a", self.game.player.name)
        self.game.production_pipeline.create_project("single", self.game.player.name)

        high = self.game.life_flow.snapshot()
        self.assertGreater(high.intensity, 0.45)
        self.assertGreater(high.collision_allowance, 0.45)

    def test_recovery_window_appears_after_heavy_pressure_stretch(self):
        for _ in range(8):
            self.game.life_flow.record_pressure("contract", 1.0)
        snap = self.game.life_flow.snapshot()

        self.assertTrue(snap.in_recovery_window)
        self.assertLess(snap.collision_allowance, 0.55)

    def test_support_staff_reduces_effective_overload(self):
        self.game.player.fame = 90
        no_staff = self.game.life_flow.snapshot()

        self.game.delegation_system.add_or_update_role(self.game.player, "assistant", competence=0.92, reliability=0.9, experience=0.9)
        self.game.delegation_system.add_or_update_role(self.game.player, "manager", competence=0.9, reliability=0.9, experience=0.9)
        self.game.delegation_system.add_or_update_role(self.game.player, "driver", competence=0.88, reliability=0.9, experience=0.86)
        staffed = self.game.life_flow.snapshot()

        self.assertLess(staffed.intensity, no_staff.intensity)

    def test_release_activity_raises_density_target(self):
        base = self.game.life_flow.snapshot()

        p = self.game.production_pipeline.create_project("album", self.game.player.name)
        p.current_stage = "ready_for_release"
        boosted = self.game.life_flow.snapshot()

        self.assertGreater(boosted.event_density_target, base.event_density_target)

    def test_orchestrator_biases_timing_without_removing_truth(self):
        self.game.organization_contracts.create_organization("label_a", "Apex")
        self.game.organization_contracts.sign_contract("label_a", self.game.player.name)

        self.game.organization_contracts.tick(minutes=60)
        events = self.game.player.schedule.get_upcoming_events(current_game_time.copy(), limit=20)

        milestones = [e for e in events if "release milestone" in e.description]
        self.assertTrue(milestones)
        # Base starts at +5 days; low-intensity pacing should spread this to at least +6.
        self.assertGreaterEqual(min(e.start_time.day for e in milestones), current_game_time.day + 6)

    def test_collision_permission_is_higher_in_intense_state(self):
        low_allowed = self.game.life_flow.allow_pressure("rivalry", base_weight=1.1, major=True)

        self.game.player.fame = 160
        self.game.visibility_system.entity_visibility[self.game.player.name] = {
            "base_visibility": 30.0,
            "recent_buzz": 22.0,
            "negative_pressure": 2.0,
        }
        self.game.life_flow.record_pressure("contract", 1.2)
        self.game.life_flow.record_pressure("production", 1.0)
        high_allowed = self.game.life_flow.allow_pressure("rivalry", base_weight=1.1, major=True)

        self.assertLessEqual(int(low_allowed), int(high_allowed))


if __name__ == "__main__":
    unittest.main()
