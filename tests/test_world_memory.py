import unittest

from game.world_memory import WorldMemoryStore, WorldMemoryEntry
from game.game_time import GameTime, current_game_time
from game.npc_world_sim import NPCWorldSimulator
from game.npc import NPC
from game.player import Player
from game.location import Location
from game.poi import PointOfInterest


class Log:
    def __init__(self):
        self.messages = []

    def add_log_message(self, msg):
        self.messages.append(msg)


class FakeGame:
    def __init__(self):
        self.GAME_LOG = Log()
        self.world_memory = WorldMemoryStore()
        self.player = Player("Hero")
        self.player.active_opportunities = {}
        self.WORLD_MAP = {}
        self.NPC_REGISTRY = {}

    def get_poi_or_venue_by_id(self, target_id):
        for loc in self.WORLD_MAP.values():
            for poi in loc.points_of_interest:
                if poi.poi_id == target_id:
                    return poi
        return None

    def _get_time_slot_key(self, gt_obj):
        return "Weekday_Morning"


class TestWorldMemory(unittest.TestCase):
    def test_query_and_decay_weighting(self):
        store = WorldMemoryStore(decay_days=10)
        now = GameTime(2024, 1, 20, 8, 0)
        old = GameTime(2024, 1, 1, 8, 0)

        store.add(WorldMemoryEntry("great_performance", ["player"], "venue_1", old, impact_score=5.0))
        store.add(WorldMemoryEntry("great_performance", ["player"], "venue_1", now, impact_score=5.0))

        queried = store.query(event_type="great_performance", entity_id="player")
        self.assertEqual(len(queried), 2)
        self.assertGreater(store.weight_for(queried[1], now), store.weight_for(queried[0], now))

    def test_opportunity_and_relationship_influenced_by_memory(self):
        game = FakeGame()
        city = Location("City A")
        poi = PointOfInterest("a_stage", "A Stage", "", parent_location_id="City A")
        city.points_of_interest = [poi]
        game.WORLD_MAP = {"City A": city}
        game.player.current_location = city
        game.player.current_poi = poi

        npc = NPC("npc_1", "Ray", "gruff_club_owner", current_location=poi)
        game.NPC_REGISTRY[npc.npc_id] = npc

        sim = NPCWorldSimulator(game)
        sim.ensure_npc_state(npc)
        npc.relationship_state.respect = 6
        npc.relationship_state.trust = 4
        npc.momentum = 2

        # Negative reliability memory should bias against collaboration and reduce trust.
        game.world_memory.add(WorldMemoryEntry("missed_gig", ["Hero"], "venue_1", current_game_time.copy(), impact_score=6.0))
        trust_before = npc.relationship_state.trust
        sim.advance(30)
        self.assertLessEqual(npc.relationship_state.trust, trust_before)
        self.assertNotIn("collab_offer_npc_1", game.player.active_opportunities)

        # Positive recent performance memory should enable collab conditions.
        game.world_memory.add(WorldMemoryEntry("great_performance", ["Hero"], "venue_1", current_game_time.copy(), impact_score=8.0))
        sim.advance(30)
        self.assertIn("collab_offer_npc_1", game.player.active_opportunities)


if __name__ == "__main__":
    unittest.main()
