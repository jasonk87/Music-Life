import unittest

from game.delegation_roles import DelegationSystem
from game.game_time import current_game_time
from game.llm_interaction_layer import InteractionContextBuilder, LLMInteractionEngine
from game.location import Location
from game.npc import NPC
from game.npc_identity_system import NPCIdentitySystem
from game.player import Player
from game.player_schedule import PlayerSchedule
from game.poi import PointOfInterest
from game.visibility_system import VisibilitySystem
from game.world_memory import WorldMemoryStore, WorldMemoryEntry


class DummyGame:
    def __init__(self):
        self.player = Player("Hero")
        self.player.schedule = PlayerSchedule()
        self.player.current_location = Location("Austin", "TX")
        self.player.current_poi = PointOfInterest("club", "Rusty Nail", "Venue", category="VENUE_CLUB")
        self.player.current_location.add_poi(self.player.current_poi)

        self.world_memory = WorldMemoryStore()
        self.visibility_system = VisibilitySystem()
        self.delegation_system = DelegationSystem()
        self.delegation_system.ensure_player_support(self.player)

        self.game_state = "main_menu"
        self.travel_manager = None


class TestNPCIdentitySystem(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 12
        current_game_time.minute = 0

        self.game = DummyGame()
        self.identity = NPCIdentitySystem(self.game)

    def test_persistent_npc_retained_after_meaningful_encounter(self):
        npc = NPC("fan_1", "Jules", "fan_voice")

        self.identity.mark_meaningful_encounter(npc, context="met_in_person", role_hint="fan")

        self.assertTrue(npc.is_persistent)
        self.assertIn("fan", npc.role_tags)
        self.assertTrue(npc.contact_access["known_contact"])

    def test_role_transition_contact_to_assistant(self):
        npc = NPC("contact_1", "Mika", "assistant")
        self.identity.ensure_identity_fields(npc)
        npc.role_tags.add("contact")

        self.identity.hire_npc_into_support_role(self.game.player, npc, "assistant", self.game.delegation_system)

        self.assertIn("assistant", npc.role_tags)
        self.assertNotIn("contact", npc.role_tags)
        self.assertEqual(self.game.player.delegation_roles["assistant"].npc_id, npc.npc_id)

    def test_relationship_continuity_across_role_changes(self):
        npc = NPC("friend_1", "Ari", "assistant")
        npc.relationship_score = 28
        self.identity.ensure_identity_fields(npc)
        npc.role_tags.add("contact")

        self.identity.transition_role(npc, "contact", "assistant", "promotion")
        self.identity.transition_role(npc, "assistant", "former_assistant", "left_role")

        self.assertEqual(npc.relationship_score, 28)
        self.assertIn("former_assistant", npc.role_tags)

    def test_access_contact_state_behavior(self):
        npc = NPC("celeb_1", "Starlight", "celebrity")
        self.identity.ensure_identity_fields(npc)
        self.identity.set_contact_access(npc, known_contact=True, has_phone_number=False, public_only=True)

        self.assertFalse(self.identity.can_reach(npc, channel="phone"))
        self.assertFalse(self.identity.can_reach(npc, channel="private"))

        self.identity.set_contact_access(npc, has_phone_number=True, public_only=False)
        self.assertTrue(self.identity.can_reach(npc, channel="phone"))

    def test_role_end_preserves_identity_and_history(self):
        npc = NPC("assistant_1", "Mika", "assistant")
        self.identity.ensure_identity_fields(npc)
        self.identity.hire_npc_into_support_role(self.game.player, npc, "assistant", self.game.delegation_system)

        self.identity.end_support_role(self.game.player, npc, "assistant", self.game.delegation_system, reason="fired")

        self.assertTrue(npc.is_persistent)
        self.assertIn("former_assistant", npc.role_tags)
        self.assertGreaterEqual(len(npc.role_history), 2)

    def test_interaction_layer_uses_persistent_personality_history_after_transition(self):
        npc = NPC("rival_1", "Rex", "rival")
        self.identity.ensure_identity_fields(npc)
        self.identity.mark_meaningful_encounter(npc, context="met_in_person", role_hint="rival")
        self.identity.transition_role(npc, "rival", "collaborator", "made_peace")

        self.game.world_memory.add(
            WorldMemoryEntry("rivalry_escalation", [self.game.player.name, npc.npc_id], "Austin", current_game_time.copy(), impact_score=4.0)
        )

        ctx = InteractionContextBuilder(self.game).build("in_person", npc, "artist")
        out = LLMInteractionEngine(self.game, llm_client=None).run_interaction(ctx, "talk").output

        self.assertEqual(ctx.personality_profile.archetype, "arrogant")
        self.assertIn("rivalry", out.spoken_text.lower())


if __name__ == "__main__":
    unittest.main()
