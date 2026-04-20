import unittest
from unittest.mock import patch

from game.game_time import current_game_time
from game.llm_interaction_layer import InteractionContextBuilder, LLMInteractionEngine
from game.location import Location
from game.npc import NPC
from game.npc_identity_system import NPCIdentitySystem
from game.organization_contracts import OrganizationContractSystem
from game.player import Player
from game.player_schedule import PlayerSchedule
from game.poi import PointOfInterest
from game.visibility_system import VisibilitySystem
from game.world_memory import WorldMemoryStore


class DummyGame:
    def __init__(self):
        self.player = Player("Hero")
        self.player.schedule = PlayerSchedule()
        self.player.current_location = Location("City Center", "Metro")
        self.player.current_poi = PointOfInterest("downtown", "Downtown", "Scene", category="POI_STREET")
        self.player.current_location.add_poi(self.player.current_poi)

        self.world_memory = WorldMemoryStore()
        self.visibility_system = VisibilitySystem()
        self.NPC_REGISTRY = {}
        self.game_state = "main_menu"
        self.travel_manager = None

        self.npc_identity = NPCIdentitySystem(self)


class TestOrganizationContracts(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 9
        current_game_time.minute = 0

        self.game = DummyGame()
        self.system = OrganizationContractSystem(self.game)
        self.system.create_organization("label_a", "Apex Records", home_city="City Center", tier=0.8)

        self.contact = NPC("rep_1", "Mara", "manager")
        self.contact.relationship_score = 35
        self.artist_npc = NPC("artist_1", "Rook", "artist")
        self.artist_npc.momentum = 0
        self.artist_npc.fame = 20
        self.game.NPC_REGISTRY[self.contact.npc_id] = self.contact
        self.game.NPC_REGISTRY[self.artist_npc.npc_id] = self.artist_npc

    def test_organization_with_persistent_contact_npc(self):
        ok = self.system.attach_member_npc("label_a", self.contact.npc_id, role_tag="label_contact")

        self.assertTrue(ok)
        org = self.system.organizations["label_a"]
        self.assertIn(self.contact.npc_id, org.member_npc_ids)
        self.assertTrue(self.contact.is_persistent)
        self.assertIn("label_contact", self.contact.role_tags)

    def test_contract_terms_generate_real_pressure_items(self):
        self.system.sign_contract("label_a", self.game.player.name, contact_npc_id=self.contact.npc_id)
        self.system.tick(minutes=60)

        upcoming = self.game.player.schedule.get_upcoming_events(current_game_time.copy(), limit=20)
        pressure_items = [e for e in upcoming if isinstance(e.details, dict) and e.details.get("pressure_item")]
        self.assertGreater(len(pressure_items), 0)

    def test_leverage_affects_deal_quality(self):
        self.game.player.fame = 5
        low = self.system.sign_contract("label_a", self.game.player.name)
        low_terms = low.terms

        self.system.contracts.pop(low.contract_id)
        self.game.player.fame = 260
        self.game.visibility_system.entity_visibility[self.game.player.name] = {
            "base_visibility": 25.0,
            "recent_buzz": 18.0,
            "negative_pressure": 2.0,
        }
        high = self.system.sign_contract("label_a", self.game.player.name)
        high_terms = high.terms

        self.assertGreater(high_terms.creative_control, low_terms.creative_control)
        self.assertLessEqual(high_terms.exclusivity, low_terms.exclusivity)

    def test_relationship_with_org_member_biases_terms(self):
        self.contact.relationship_score = 50
        good = self.system.sign_contract("label_a", self.game.player.name, contact_npc_id=self.contact.npc_id)
        good_strictness = good.terms.review_strictness

        self.system.contracts.pop(good.contract_id)
        self.contact.relationship_score = -50
        tough = self.system.sign_contract("label_a", self.game.player.name, contact_npc_id=self.contact.npc_id)

        self.assertLess(good_strictness, tough.terms.review_strictness)

    def test_npc_artist_under_org_pressure(self):
        contract = self.system.sign_contract("label_a", self.artist_npc.npc_id, contact_npc_id=self.contact.npc_id)
        with patch("random.random", return_value=0.0):
            self.system.tick(minutes=60)

        self.assertGreaterEqual(contract.misses, 1)

    def test_warning_review_drop_progression_from_repeated_misses(self):
        self.contact.relationship_score = -60
        contract = self.system.sign_contract("label_a", self.game.player.name, contact_npc_id=self.contact.npc_id)

        self.system.record_contract_outcome(contract.contract_id, "miss")
        self.system.record_contract_outcome(contract.contract_id, "miss")
        self.assertGreaterEqual(contract.warnings, 1)

        self.system.record_contract_outcome(contract.contract_id, "miss")
        self.assertFalse(contract.active)

    def test_org_contact_identity_continuity_across_interactions(self):
        self.system.attach_member_npc("label_a", self.contact.npc_id, role_tag="label_contact")
        contract = self.system.sign_contract("label_a", self.game.player.name, contact_npc_id=self.contact.npc_id)

        ctx = InteractionContextBuilder(self.game).build("phone_call", self.contact, "label_contact")
        out = LLMInteractionEngine(self.game, llm_client=None).run_interaction(ctx, "status?").output

        self.assertEqual(ctx.participant_id, self.contact.npc_id)
        self.assertIn("label_contact", self.contact.role_tags)
        self.assertTrue(contract.contact_npc_id == self.contact.npc_id)
        self.assertIn(self.contact.name, out.spoken_text)


if __name__ == "__main__":
    unittest.main()
