import unittest

from game.visibility_system import VisibilitySystem
from game.world_memory import WorldMemoryStore, WorldMemoryEntry
from game.game_time import GameTime, current_game_time
from game.place_presence import LocationActionEngine
from game.player import Player
from game.poi import PointOfInterest
from game.location import Location
from game.npc import NPC
from game.npc_world_sim import NPCWorldSimulator, NPCObligation


class FixedRng:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


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


class TestVisibilitySystem(unittest.TestCase):
    def test_memory_amplification_and_idempotency(self):
        store = WorldMemoryStore()
        now = GameTime(2024, 1, 1, 8, 0)
        entry = WorldMemoryEntry(
            event_type="great_performance",
            involved_entities=["Hero"],
            location="venue_1",
            timestamp=now,
            impact_score=4.0,
            source_key="mem_1",
        )
        store.add(entry)
        vis = VisibilitySystem()

        vis.amplify_from_memory(store, now)
        first_signals = len(vis.signals)
        first_visibility = vis.get_visibility("Hero", "venue_1")["public_visibility"]

        vis.amplify_from_memory(store, now)
        second_signals = len(vis.signals)
        second_visibility = vis.get_visibility("Hero", "venue_1")["public_visibility"]

        self.assertEqual(first_signals, 1)
        self.assertEqual(second_signals, 1)
        self.assertLessEqual(second_visibility, first_visibility)  # decay only, no duplicate amplification

    def test_locality_sensitive_visibility(self):
        store = WorldMemoryStore()
        now = GameTime(2024, 1, 1, 8, 0)
        store.add(WorldMemoryEntry("great_performance", ["Hero"], "venue_1", now, impact_score=5.0, source_key="v1"))
        vis = VisibilitySystem()
        vis.amplify_from_memory(store, now)

        local = vis.get_visibility("Hero", "venue_1")
        other = vis.get_visibility("Hero", "venue_2")
        self.assertGreater(local["local_visibility"], other["local_visibility"])

    def test_visibility_affects_public_encounters(self):
        player = Player("Hero")
        player.fame = 0
        street = PointOfInterest("street_1", "Main St", "", category="DOWNTOWN", parent_location_id="City")
        engine = LocationActionEngine()
        action = next(a for a in engine.generate_actions(player, street) if a.action_id == "walk_district")

        low = engine.execute_action(player, street, None, action, lambda m: None, logger=None, rng=FixedRng(0.25), visibility_pressure=0.0)
        high = engine.execute_action(player, street, None, action, lambda m: None, logger=None, rng=FixedRng(0.25), visibility_pressure=20.0)

        self.assertIsNone(low["encounter"])
        self.assertIsNotNone(high["encounter"])

    def test_visibility_influences_opportunity_and_npc_signal(self):
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

        # No visibility yet -> collab should not appear due visibility gate.
        sim.advance(30)
        self.assertNotIn("collab_offer_npc_1", game.player.active_opportunities)

        # Add strong visibility and re-amplify, then collab can appear.
        game.world_memory.add(WorldMemoryEntry("great_performance", ["Hero"], "City A", current_game_time.copy(), impact_score=8.0, source_key="hero_perf"))
        game.visibility_system.amplify_from_memory(game.world_memory, current_game_time.copy())
        sim.advance(30)
        self.assertIn("collab_offer_npc_1", game.player.active_opportunities)

        # NPC missed obligation creates npc signal path after amplification.
        start = current_game_time.copy()
        end = current_game_time.copy()
        end.advance_time(20)
        npc.obligations.append(NPCObligation("m1", "Missed", start, end, destination_id="missing_place"))
        sim.advance(40)
        game.visibility_system.amplify_from_memory(game.world_memory, current_game_time.copy())
        npc_negative = game.visibility_system.recent_signals(signal_type="negative_press", entity_id=npc.npc_id)
        self.assertTrue(npc_negative)


if __name__ == "__main__":
    unittest.main()
