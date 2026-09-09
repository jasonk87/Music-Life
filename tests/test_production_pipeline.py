import unittest
from unittest.mock import patch

from game.game_time import current_game_time
from game.location import Location
from game.npc import NPC
from game.npc_identity_system import NPCIdentitySystem
from game.organization_contracts import OrganizationContractSystem
from game.player import Player
from game.player_schedule import PlayerSchedule
from game.poi import PointOfInterest
from game.obligation_resolver import ObligationResolver
from game.production_pipeline import ProductionPipelineSystem
from game.visibility_system import VisibilitySystem
from game.world_memory import WorldMemoryStore


class DummyGame:
    def __init__(self):
        self.player = Player("Hero")
        self.player.schedule = PlayerSchedule()
        self.player.current_location = Location("Philadelphia, PA", "Metro")
        self.player.current_poi = PointOfInterest("studio", "Home Studio", "Studio", category="HOME")
        self.player.alt_poi = PointOfInterest("coffee", "Coffee Shop", "Cafe", category="POI_CAFE")
        self.player.current_location.add_poi(self.player.current_poi)
        self.player.current_location.add_poi(self.player.alt_poi)

        self.world_memory = WorldMemoryStore()
        self.visibility_system = VisibilitySystem()
        self.NPC_REGISTRY = {}
        self.game_state = "main_menu"
        self.travel_manager = None

        self.npc_identity = NPCIdentitySystem(self)

    def get_poi_or_venue_by_id(self, target_id):
        for poi in self.player.current_location.points_of_interest:
            if getattr(poi, "poi_id", None) == target_id:
                return poi
        return None


class TestProductionPipeline(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 10
        current_game_time.minute = 0

        self.game = DummyGame()
        self.pipeline = ProductionPipelineSystem(self.game)

    def test_project_progresses_through_multiple_stages(self):
        p = self.pipeline.create_project("single", self.game.player.name)

        for _ in range(8):
            self.pipeline.apply_work_session(
                p.project_id,
                minutes_spent=140,
                resource_quality=0.8,
                condition_score=0.8,
                pressure_level=0.2,
                interruption_level=0.1,
                budget_spend=10,
                collaborator_fit=0.7,
            )

        self.assertIn(p.current_stage, {"mix_master", "ready_for_release", "released"})

    def test_studio_work_items_enter_real_schedule(self):
        p = self.pipeline.create_project("song", self.game.player.name)
        ok = self.pipeline.schedule_work_item(p.project_id, "Songwriting Session", "Meeting", days_ahead=1, minutes=120)

        self.assertTrue(ok)
        events = self.game.player.schedule.get_upcoming_events(current_game_time.copy(), limit=5)
        self.assertTrue(any((e.details or {}).get("project_id") == p.project_id for e in events))

    def test_booked_creative_work_requires_poi_presence_not_just_city(self):
        p = self.pipeline.create_project("song", self.game.player.name)
        ok = self.pipeline.schedule_work_item(p.project_id, "Studio Writing Block", "Meeting", days_ahead=0, minutes=120)
        self.assertTrue(ok)

        event = self.game.player.schedule.scheduled_items[-1]
        self.assertEqual(event.details.get("destination_id"), "studio")

        # Same city, different POI should not count as already present.
        self.game.player.current_poi = self.game.player.alt_poi
        resolution = ObligationResolver(self.game)._evaluate_obligation(event, current_game_time.copy())
        self.assertNotEqual(resolution.status, "reachable")

    def test_schedule_work_item_resolves_destination_from_location_name_when_not_currently_at_poi(self):
        p = self.pipeline.create_project("song", self.game.player.name)
        self.game.player.current_poi = None

        ok = self.pipeline.schedule_work_item(
            p.project_id,
            "Studio Recording Block",
            "Studio Session",
            days_ahead=1,
            minutes=120,
            location_name="Home Studio",
            requires_presence=True,
        )
        self.assertTrue(ok)

        event = self.game.player.schedule.scheduled_items[-1]
        self.assertEqual(event.details.get("destination_id"), "studio")

    def test_quality_changes_from_time_pressure_and_resources(self):
        p_bad = self.pipeline.create_project("single", self.game.player.name)
        self.pipeline.apply_work_session(
            p_bad.project_id,
            minutes_spent=60,
            resource_quality=0.2,
            condition_score=0.25,
            pressure_level=0.9,
            interruption_level=0.8,
            budget_spend=0,
            collaborator_fit=0.2,
        )

        p_good = self.pipeline.create_project("single", self.game.player.name)
        self.pipeline.apply_work_session(
            p_good.project_id,
            minutes_spent=180,
            resource_quality=0.85,
            condition_score=0.85,
            pressure_level=0.2,
            interruption_level=0.1,
            budget_spend=0,
            collaborator_fit=0.8,
        )

        self.assertGreater(p_good.quality_score, p_bad.quality_score)

    def test_collaboration_with_persistent_npc_involvement(self):
        npc = NPC("artist_1", "Rook", "artist")
        self.game.NPC_REGISTRY[npc.npc_id] = npc
        self.game.npc_identity.mark_meaningful_encounter(npc, context="met_in_person", role_hint="artist")

        p = self.pipeline.create_project("song", self.game.player.name)
        self.pipeline.link_collaboration(p.project_id, npc.npc_id)

        self.assertIn(npc.npc_id, p.collaborator_ids)
        self.assertTrue(npc.is_persistent)

    def test_release_generates_memory_hooks(self):
        p = self.pipeline.create_project("single", self.game.player.name)
        p.current_stage = "ready_for_release"
        p.quality_score = 3.0

        ok = self.pipeline.release_project(p.project_id)

        self.assertTrue(ok)
        event_types = [e.event_type for e in self.game.world_memory.entries]
        self.assertIn("single_released", event_types)
        self.assertIn("breakout_release", event_types)

    def test_contract_pressure_interacts_with_real_project_deadline(self):
        orgs = OrganizationContractSystem(self.game)
        orgs.create_organization("label_x", "X Records", tier=0.8)
        contract = orgs.sign_contract("label_x", self.game.player.name)

        p = self.pipeline.create_project("album", self.game.player.name)
        p.quality_score = 1.5
        self.game.production_pipeline = self.pipeline

        orgs._generate_player_contract_pressure()

        self.assertIn("contract_pressure", p.metadata)
        self.assertLess(p.quality_score, 1.5)
        self.assertTrue(contract.active)

    def test_npc_project_participation_under_same_pipeline(self):
        npc = NPC("artist_2", "Mara", "artist")
        self.game.NPC_REGISTRY[npc.npc_id] = npc

        p = self.pipeline.create_project("single", npc.npc_id)
        with patch("random.random", return_value=0.0):
            self.pipeline.tick(minutes=120)

        self.assertGreater(p.progress_points, 0)

    def test_promo_public_work_items_generated_after_release(self):
        p = self.pipeline.create_project("album", self.game.player.name)
        p.current_stage = "ready_for_release"

        self.pipeline.release_project(p.project_id)

        upcoming = self.game.player.schedule.get_upcoming_events(current_game_time.copy(), limit=20)
        titles = [e.description for e in upcoming]
        self.assertTrue(any("Promo interview" in t for t in titles))
        self.assertTrue(any("Autograph signing" in t for t in titles))


if __name__ == "__main__":
    unittest.main()
