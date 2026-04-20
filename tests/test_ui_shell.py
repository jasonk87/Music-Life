import unittest

from game.delegation_roles import DelegationSystem
from game.game_time import current_game_time, GameTime
from game.location import Location
from game.npc import NPC
from game.place_presence import LocationActionEngine
from game.player import Player
from game.player_schedule import PlayerSchedule
from game.poi import PointOfInterest
from game.production_pipeline import ProductionPipelineSystem
from game.transit_phase import TransitLayer
from game.ui_shell import PlayerUIShell
from game.ui_signals import UISignalLayer
from game.visibility_system import VisibilitySystem
from game.world_memory import WorldMemoryEntry, WorldMemoryStore


class Log:
    def add_log_message(self, msg):
        pass


class DummyDestination:
    name = "Dallas"


class DummyTravelManager:
    def __init__(self):
        self.destination = DummyDestination()
        self.transport_mode = "plane"
        self.distance_total = 500
        self.distance_covered = 100
        self.current_speed = 400
        self.vehicle = None


class DummyGame:
    def __init__(self):
        self.player = Player("Hero")
        self.player.schedule = PlayerSchedule()
        self.player.current_location = Location("Austin", "TX")
        self.player.current_poi = PointOfInterest("club", "Rusty Nail", "Venue", category="VENUE_CLUB", parent_location_id="Austin")
        self.player.current_location.add_poi(self.player.current_poi)
        self.player.contacts = []
        self.player.active_opportunities = {}

        self.visibility_system = VisibilitySystem()
        self.world_memory = WorldMemoryStore()
        self.location_action_engine = LocationActionEngine()
        self.transit_layer = TransitLayer()
        self.delegation_system = DelegationSystem()
        self.delegation_system.ensure_player_support(self.player)
        self.production_pipeline = ProductionPipelineSystem(self)

        self.game_state = "main_menu"
        self.travel_manager = None
        self.NPC_REGISTRY = {}
        self.GAME_LOG = Log()
        self.selected_npc = None
        self.conversation_history = []

        self.ui_signals = UISignalLayer(self)
        self.ui_shell = PlayerUIShell(self)


class TestUIShell(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 10
        current_game_time.minute = 0
        self.game = DummyGame()

        self.game.player.schedule.add_event(
            GameTime(2024, 1, 1, 20, 0),
            GameTime(2024, 1, 1, 22, 0),
            "Live Show",
            "Gig",
            {"location_name": "The Rusty Nail", "requires_presence": True},
        )
        self.game.player.schedule.add_event(
            GameTime(2024, 1, 2, 9, 0),
            GameTime(2024, 1, 2, 10, 0),
            "Flight to LA",
            "Meeting",
            {"location_name": "Airport", "requires_presence": True},
        )
        self.game.player.schedule.add_event(
            GameTime(2024, 1, 5, 11, 0),
            GameTime(2024, 1, 5, 12, 0),
            "Interview",
            "Meeting",
            {"location_name": "Local Radio", "requires_presence": True},
        )

    def test_top_context_bar_is_grounded(self):
        bar = self.game.ui_shell.top_context_bar()
        self.assertIn("Austin", bar["headline"])
        self.assertTrue(bar["clock"])
        self.assertIsInstance(bar["tags"], list)

    def test_schedule_grouping_today_tomorrow_upcoming(self):
        panel = self.game.ui_shell.schedule_panel()
        self.assertTrue(panel["Today"])
        self.assertTrue(panel["Tomorrow"])
        self.assertTrue(panel["Upcoming"])

    def test_shell_language_avoids_risk_and_obligation_and_advice(self):
        shell = self.game.ui_shell.build()
        text_blob = " ".join(shell["top_context"]["tags"] + shell["world_feed"] + shell["schedule"]["Today"] + shell["scene"]["actions"]).lower()
        self.assertNotIn("risk", text_blob)
        self.assertNotIn("obligation", text_blob)
        self.assertNotIn("should", text_blob)

    def test_scene_actions_render_from_current_place_context(self):
        scene = self.game.ui_shell.scene_panel()
        self.assertTrue(scene["actions"])
        joined = " ".join(scene["actions"]).lower()
        self.assertTrue("go inside" in joined or "network" in joined or "look" in joined)

    def test_transit_mode_rendering_contains_destination_and_time(self):
        self.game.game_state = "travel_active"
        self.game.travel_manager = DummyTravelManager()
        scene = self.game.ui_shell.scene_panel()

        self.assertEqual(scene["transit"]["destination"], "Dallas")
        self.assertTrue(scene["transit"]["time_remaining"])
        self.assertTrue(scene["actions"])

    def test_world_feed_renders_from_existing_signals(self):
        self.game.world_memory.add(
            WorldMemoryEntry("great_performance", [self.game.player.name], "Austin", current_game_time.copy(), impact_score=4.0, source_key="perf1")
        )
        self.game.visibility_system.amplify_from_memory(self.game.world_memory, current_game_time.copy())

        feed = self.game.ui_shell.world_feed_panel()
        self.assertTrue(feed)

    def test_project_summary_is_lightweight(self):
        p = self.game.production_pipeline.create_project("album", self.game.player.name)
        p.current_stage = "recording"
        proj = self.game.ui_shell.project_panel()
        self.assertTrue(any("Album" in line for line in proj))

    def test_support_outcome_appears_as_natural_feed_item(self):
        self.game.world_memory.add(
            WorldMemoryEntry("assistant_secured_booking", [self.game.player.name], "Austin", current_game_time.copy(), impact_score=2.0, source_key="assist1")
        )
        feed = self.game.ui_shell.world_feed_panel()
        self.assertTrue(any("assistant" in line.lower() or "booking" in line.lower() for line in feed))


if __name__ == "__main__":
    unittest.main()
