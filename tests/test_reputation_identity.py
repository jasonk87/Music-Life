import unittest

from game.game_time import current_game_time, GameTime
from game.llm_interaction_layer import InteractionContextBuilder, LLMInteractionEngine, SocialMediaExpressionLayer
from game.location import Location
from game.npc import NPC
from game.npc_world_sim import NPCWorldSimulator
from game.organization_contracts import OrganizationContractSystem
from game.player import Player
from game.player_schedule import PlayerSchedule
from game.poi import PointOfInterest
from game.reputation_identity import ReputationIdentitySystem
from game.visibility_system import VisibilitySystem
from game.world_memory import WorldMemoryStore, WorldMemoryEntry


class Log:
    def __init__(self):
        self.messages = []

    def add_log_message(self, msg):
        self.messages.append(msg)


class DummyGame:
    def __init__(self):
        self.player = Player("Hero")
        self.player.schedule = PlayerSchedule()
        self.player.active_opportunities = {}
        self.player.current_location = Location("Austin", "TX")
        self.player.current_poi = PointOfInterest("club", "Rusty Nail", "Venue", category="VENUE_CLUB", parent_location_id="Austin")
        self.player.current_location.add_poi(self.player.current_poi)

        self.world_memory = WorldMemoryStore()
        self.visibility_system = VisibilitySystem()
        self.organization_contracts = OrganizationContractSystem(self)
        self.reputation_system = ReputationIdentitySystem(self)
        self.GAME_LOG = Log()
        self.game_state = "main_menu"
        self.travel_manager = None

        self.WORLD_MAP = {"Austin": self.player.current_location, "Los Angeles": Location("Los Angeles", "CA")}
        la_poi = PointOfInterest("la_stage", "LA Stage", "Venue", category="VENUE_CLUB", parent_location_id="Los Angeles")
        self.WORLD_MAP["Los Angeles"].add_poi(la_poi)

        self.NPC_REGISTRY = {}

    def get_poi_or_venue_by_id(self, target_id):
        for loc in self.WORLD_MAP.values():
            for poi in loc.points_of_interest:
                if poi.poi_id == target_id:
                    return poi
        return None

    def _get_time_slot_key(self, gt_obj):
        return "Weekday_Morning"


class TestReputationIdentity(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 10
        current_game_time.minute = 0
        self.game = DummyGame()

    def _add_entry(self, event_type, location="Austin", impact=3.0, metadata=None, entities=None):
        entities = entities or [self.game.player.name]
        key = f"{event_type}:{location}:{len(self.game.world_memory.entries)}"
        self.game.world_memory.add(
            WorldMemoryEntry(
                event_type=event_type,
                involved_entities=entities,
                location=location,
                timestamp=current_game_time.copy(),
                impact_score=impact,
                metadata=metadata or {},
                source_key=key,
            )
        )

    def test_repeated_behavior_strengthens_signal_more_than_single_event(self):
        self._add_entry("missed_gig", impact=3.0)
        one = self.game.reputation_system.snapshot(self.game.player.name)

        self._add_entry("missed_gig", impact=3.0)
        self._add_entry("missed_gig", impact=3.0)
        repeated = self.game.reputation_system.snapshot(self.game.player.name)

        self.assertGreater(repeated.long_term.get("flaky", 0.0), one.long_term.get("flaky", 0.0))

    def test_scoped_reputation_differs_by_city_and_org(self):
        self._add_entry("great_performance", location="Austin", impact=4.0)
        self._add_entry("missed_gig", location="Los Angeles", impact=4.0)
        self._add_entry(
            "contract_warning",
            location="Austin",
            impact=3.0,
            metadata={"organization_id": "label_x"},
        )

        austin = self.game.reputation_system.snapshot(self.game.player.name, scope="city:Austin")
        la = self.game.reputation_system.snapshot(self.game.player.name, scope="city:Los Angeles")
        org = self.game.reputation_system.snapshot(self.game.player.name, scope="org:label_x")

        self.assertGreater(austin.long_term.get("live_respected", 0.0), la.long_term.get("live_respected", 0.0))
        self.assertGreater(la.long_term.get("flaky", 0.0), austin.long_term.get("flaky", 0.0))
        self.assertGreater(org.long_term.get("hard_to_work_with", 0.0), 0.0)

    def test_recent_momentum_and_long_term_identity_both_apply(self):
        old = GameTime(2023, 6, 1, 10, 0)
        self.game.world_memory.add(
            WorldMemoryEntry("missed_gig", [self.game.player.name], "Austin", old, impact_score=5.0, source_key="old_miss")
        )
        self._add_entry("breakout_release", impact=5.0)

        snap = self.game.reputation_system.snapshot(self.game.player.name)
        self.assertGreater(snap.long_term.get("flaky", 0.0), 0.0)
        self.assertGreater(snap.recent.get("rising", 0.0), 0.0)
        self.assertGreater(snap.momentum, -1.0)

    def test_reputation_biases_org_terms_without_hard_lock(self):
        self.game.organization_contracts.create_organization("label_a", "Apex", home_city="Austin")
        self._add_entry("contract_milestone_hit", metadata={"organization_id": "label_a"}, impact=4.0)
        self._add_entry("great_performance", impact=4.0)

        contract = self.game.organization_contracts.sign_contract("label_a", self.game.player.name)

        self.assertTrue(contract.active)
        self.assertLess(contract.terms.review_strictness, 0.9)

    def test_npc_reputation_participates_in_collab_case(self):
        npc = NPC("npc_1", "Rook", "artist", current_location=self.game.player.current_location)
        npc.schedule = {}
        npc.relationship_state = type("Rel", (), {"respect": 4, "trust": 2, "rivalry": 0})()
        npc.momentum = 2
        npc.obligations = []
        self.game.NPC_REGISTRY[npc.npc_id] = npc

        self._add_entry("great_performance", entities=[self.game.player.name])
        self._add_entry("contract_milestone_hit", entities=[self.game.player.name])
        self._add_entry("great_performance", entities=[npc.npc_id])
        self.game.visibility_system.entity_visibility[self.game.player.name] = {
            "base_visibility": 4.0,
            "recent_buzz": 2.0,
            "negative_pressure": 0.0,
        }
        self.game.visibility_system.entity_visibility[npc.npc_id] = {
            "base_visibility": 3.0,
            "recent_buzz": 2.0,
            "negative_pressure": 0.0,
        }

        sim = NPCWorldSimulator(self.game)
        sim.ensure_npc_state(npc)
        npc.relationship_state.respect = 5
        npc.relationship_state.trust = 3
        sim._maybe_emit_player_situation(npc)

        self.assertIn("collab_offer_npc_1", self.game.player.active_opportunities)

    def test_expression_layers_reference_grounded_reputation(self):
        self._add_entry("great_performance", impact=4.5)
        participant = NPC("mgr_1", "Kai", "manager")

        ctx = InteractionContextBuilder(self.game).build("assistant_briefing", participant, "manager")
        out = LLMInteractionEngine(self.game, llm_client=None).run_interaction(ctx, "brief").output
        self.assertTrue(ctx.identity_hooks)
        self.assertIn("Scene read", out.spoken_text)

        layer = SocialMediaExpressionLayer(self.game)
        post = layer.generate_from_memory(self.game.world_memory.entries[-1], style="news_blurb")
        self.assertIsNotNone(post)
        self.assertIn("current read", post["text"])

    def test_decay_allows_recovery_over_time(self):
        old = GameTime(2023, 1, 1, 10, 0)
        self.game.world_memory.add(
            WorldMemoryEntry("missed_gig", [self.game.player.name], "Austin", old, impact_score=6.0, source_key="ancient_miss")
        )
        self._add_entry("great_performance", impact=5.0)
        self._add_entry("great_performance", impact=5.0)

        bias = self.game.reputation_system.bias_for(self.game.player.name, location="Austin")
        self.assertGreater(bias["trust"], -0.5)


if __name__ == "__main__":
    unittest.main()
