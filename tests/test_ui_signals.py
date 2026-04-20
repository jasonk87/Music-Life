import unittest

from game.delegation_roles import DelegationSystem
from game.game_time import current_game_time, GameTime
from game.location import Location
from game.player import Player
from game.player_schedule import PlayerSchedule
from game.poi import PointOfInterest
from game.transit_phase import TransitLayer
from game.ui_signals import UISignalLayer
from game.visibility_system import VisibilitySystem
from game.world_memory import WorldMemoryEntry, WorldMemoryStore


class FakeTravelManager:
    def __init__(self, destination):
        self.destination = destination
        self.transport_mode = "plane"
        self.ticket_class = "economy"
        self.vehicle = None
        self.current_speed = 800.0
        self.distance_total = 1600.0
        self.distance_covered = 400.0


class DummyGame:
    def __init__(self):
        self.player = Player("Hero")
        self.player.schedule = PlayerSchedule()
        self.player.current_location = Location("Austin", "TX")
        self.player.current_poi = PointOfInterest("downtown", "Downtown", "Scene", category="TRANSPORT_BUS")
        self.player.current_location.add_poi(self.player.current_poi)
        self.player.active_opportunities = {}

        self.world_memory = WorldMemoryStore()
        self.visibility_system = VisibilitySystem()
        self.delegation_system = DelegationSystem()
        self.delegation_system.ensure_player_support(self.player)
        self.transit_layer = TransitLayer()

        self.game_state = "main_menu"
        self.travel_manager = None
        self.active_performance = None


class TestUISignalLayer(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 10
        current_game_time.minute = 0

        self.game = DummyGame()
        self.signals = UISignalLayer(self.game)

    def test_schedule_view_has_natural_sections_without_obligation_language(self):
        self.game.player.schedule.add_event(
            GameTime(2024, 1, 1, 18, 0),
            GameTime(2024, 1, 1, 20, 0),
            "Show @ The Rusty Nail",
            "Gig",
            {"requires_presence": True, "location_name": "Austin"},
        )
        self.game.player.schedule.add_event(
            GameTime(2024, 1, 2, 9, 0),
            GameTime(2024, 1, 2, 12, 0),
            "Flight to LA",
            "Travel",
            {"requires_presence": True, "location_name": "Los Angeles"},
        )

        view = self.signals.get_schedule_view()

        self.assertIn("Today", view)
        self.assertIn("Tomorrow", view)
        lines = [item["line"] for group in view.values() for item in group]
        joined = " ".join(lines).lower()
        self.assertNotIn("obligation", joined)
        self.assertNotIn("risk", joined)

    def test_condition_tags_are_descriptive_without_numbers(self):
        self.game.player.energy = 18
        self.game.player.stress = 88
        self.game.player.money = 15
        self.game.visibility_system.entity_visibility[self.game.player.name] = {
            "base_visibility": 12.0,
            "recent_buzz": 10.0,
            "negative_pressure": 2.0,
        }

        tags = self.signals.get_condition_tags()

        self.assertIn("Exhausted", tags)
        self.assertIn("On Edge", tags)
        self.assertIn("Broke", tags)
        self.assertIn("People Recognizing You", tags)
        self.assertTrue(all(not any(ch.isdigit() for ch in tag) for tag in tags))

    def test_world_feed_uses_memory_and_visibility_signals(self):
        now = current_game_time.copy()
        self.game.world_memory.add(WorldMemoryEntry("great_performance", [self.game.player.name], "Austin", now, impact_score=7.0))
        self.game.visibility_system.amplify_from_memory(self.game.world_memory, now)

        feed = self.signals.get_world_feed(limit=4)
        texts = [item["text"] for item in feed]

        self.assertTrue(any("Crowd liked your set" in text for text in texts))
        self.assertTrue(any("People are talking about your recent set" in text for text in texts))

    def test_outputs_do_not_include_predictive_or_advisory_text(self):
        now = current_game_time.copy()
        self.game.world_memory.add(WorldMemoryEntry("missed_gig", [self.game.player.name], "Austin", now, impact_score=6.0))
        self.game.visibility_system.amplify_from_memory(self.game.world_memory, now)

        payload = []
        payload.extend([item["line"] for group in self.signals.get_schedule_view().values() for item in group])
        payload.extend(self.signals.get_condition_tags())
        payload.extend([item["text"] for item in self.signals.get_world_feed(limit=6)])
        payload.extend(self.signals.get_recent_events(limit=4))

        joined = " ".join(payload).lower()
        for banned in ["should", "must", "warning", "at risk", "risk", "recommended"]:
            self.assertNotIn(banned, joined)

    def test_transit_context_includes_destination_time_and_actions(self):
        destination = Location("Los Angeles", "CA")
        self.game.travel_manager = FakeTravelManager(destination)
        self.game.game_state = "travel_active"

        context = self.signals.get_current_context()

        self.assertEqual(context["state"], "in_transit")
        self.assertEqual(context["destination"], "Los Angeles")
        self.assertTrue(context["time_remaining"])
        self.assertGreater(len(context["available_actions"]), 0)

    def test_delegation_outcomes_are_visible_without_hints(self):
        now = current_game_time.copy()
        self.game.world_memory.add(WorldMemoryEntry("assistant_success", [self.game.player.name], "Austin", now, impact_score=2.0))
        self.game.world_memory.add(WorldMemoryEntry("security_prevented_escalation", [self.game.player.name], "Austin", now, impact_score=2.0))

        feed_texts = [item["text"] for item in self.signals.get_world_feed(limit=6)]
        recent = self.signals.get_recent_events(limit=6)
        joined = " ".join(feed_texts + recent).lower()

        self.assertIn("assistant packed your bags", joined)
        self.assertIn("security kept things calm", joined)
        for banned in ["probability", "reliability", "%", "optimize", "best action"]:
            self.assertNotIn(banned, joined)


if __name__ == "__main__":
    unittest.main()
