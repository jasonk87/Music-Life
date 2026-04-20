import unittest
from game.npc import NPC
from game.player import Player
from game.location import Location
from game.poi import PointOfInterest
from game.game_time import current_game_time
from game.npc_world_sim import NPCWorldSimulator, NPCObligation
from game.world_memory import WorldMemoryStore
from game.visibility_system import VisibilitySystem
from game.world_memory import WorldMemoryEntry


class Log:
    def __init__(self):
        self.messages = []

    def add_log_message(self, msg):
        self.messages.append(msg)


class FakeGame:
    def __init__(self):
        self.GAME_LOG = Log()
        self.player = Player("Hero")
        self.player.active_opportunities = {}
        self.WORLD_MAP = {}
        self.NPC_REGISTRY = {}
        self.world_memory = WorldMemoryStore()
        self.visibility_system = VisibilitySystem()

    def get_poi_or_venue_by_id(self, target_id):
        for loc in self.WORLD_MAP.values():
            for poi in loc.points_of_interest:
                if poi.poi_id == target_id:
                    return poi
        return None

    def _get_time_slot_key(self, gt_obj):
        return "Weekday_Morning"


class TestNPCWorldSim(unittest.TestCase):
    def setUp(self):
        self.game = FakeGame()

        city_a = Location("City A")
        city_b = Location("City B")
        city_a.add_travel_connection("City B", cost=20, time_hours=2)

        poi_a = PointOfInterest("a_stage", "A Stage", "", parent_location_id="City A")
        poi_b = PointOfInterest("b_stage", "B Stage", "", parent_location_id="City B")
        city_a.points_of_interest = [poi_a]
        city_b.points_of_interest = [poi_b]

        self.game.WORLD_MAP = {"City A": city_a, "City B": city_b}
        self.game.player.current_location = city_a
        self.game.player.current_poi = poi_a

        npc = NPC("npc_1", "Rival Ray", "gruff_club_owner", home_location=poi_b, current_location=poi_a)
        npc.schedule = {}
        self.game.NPC_REGISTRY[npc.npc_id] = npc
        self.npc = npc
        self.poi_b = poi_b

        current_game_time.year, current_game_time.month, current_game_time.day, current_game_time.hour, current_game_time.minute = (2024, 1, 1, 8, 0)

        self.sim = NPCWorldSimulator(self.game)
        self.sim.ensure_npc_state(self.npc)

    def test_npc_movement_and_obligation_resolution(self):
        start = current_game_time.copy()
        end = current_game_time.copy()
        end.advance_time(180)
        self.npc.obligations.append(
            NPCObligation("ob_1", "City B slot", start, end, destination_id=self.poi_b.poi_id)
        )

        self.sim.advance(240)

        self.assertIn(self.npc.obligations[0].status, {"attended", "late"})
        self.assertEqual(getattr(self.npc.current_location, "poi_id", None), self.poi_b.poi_id)

    def test_relationship_state_changes_from_missed_outcome(self):
        start = current_game_time.copy()
        end = current_game_time.copy()
        end.advance_time(30)
        # Impossible destination ID => miss
        self.npc.obligations.append(
            NPCObligation("ob_2", "Broken booking", start, end, destination_id="missing_place")
        )

        trust_before = self.npc.relationship_state.trust
        rivalry_before = self.npc.relationship_state.rivalry

        self.sim.advance(60)

        self.assertEqual(self.npc.obligations[0].status, "missed")
        self.assertLess(self.npc.relationship_state.trust, trust_before)
        self.assertGreater(self.npc.relationship_state.rivalry, rivalry_before)
        memory_events = self.game.world_memory.query(event_type="npc_missed_obligation", entity_id=self.npc.npc_id)
        self.assertTrue(memory_events)

    def test_replacement_and_collab_opportunity_triggers(self):
        # Force missed outcome to create replacement opportunity.
        start = current_game_time.copy()
        end = current_game_time.copy()
        end.advance_time(30)
        self.npc.obligations.append(
            NPCObligation("ob_3", "Missed slot", start, end, destination_id="missing_place")
        )
        self.sim.advance(60)
        self.assertIn("replacement_slot_npc_1", self.game.player.active_opportunities)

        # Boost relationship + momentum for collab.
        self.npc.relationship_state.respect = 6
        self.npc.relationship_state.trust = 4
        self.npc.momentum = 2
        self.npc.current_location = self.game.player.current_location
        self.game.world_memory.add(
            WorldMemoryEntry(
                event_type="great_performance",
                involved_entities=[self.game.player.name],
                location="City A",
                timestamp=current_game_time.copy(),
                impact_score=6.0,
                source_key="test_perf",
            )
        )
        self.game.visibility_system.amplify_from_memory(self.game.world_memory, current_game_time.copy())
        self.sim.advance(30)
        self.assertIn("collab_offer_npc_1", self.game.player.active_opportunities)


if __name__ == "__main__":
    unittest.main()
