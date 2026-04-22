import os
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.event import Event
from game.game import Game
from game.game_time import GameTime, current_game_time
from game.location import Location
from game.player import Player
from game.player_schedule import PlayerSchedule
from game.poi import PointOfInterest
from game.vehicle import Vehicle
from game.venue import Venue


class DummyUI:
    def __init__(self, choices=None):
        self.messages = []
        self.choices = list(choices or [])

    def add_log_message(self, message):
        self.messages.append(message)

    def add_message(self, message):
        self.messages.append(message)

    def present_choices(self, options, title, context=None):
        return self.choices.pop(0)


class MockLocation:
    def __init__(self, name, venues=None):
        self.name = name
        self.venues = venues or []
        self.points_of_interest = []


class TestEventFlow(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 8
        current_game_time.minute = 0

    def test_event_has_unique_id(self):
        venue = Venue("venue_1", "Test Venue")
        event = Event("Test Event", venue)
        self.assertTrue(event.event_id)

    def test_scheduled_gig_promotes_to_active_performance(self):
        ui = DummyUI()
        game = Game(ui)
        game.player = Player("Tester")
        venue = Venue("venue_1", "Test Venue")
        venue_event = Event("Scheduled Set", venue, event_type="OPEN_MIC")
        venue.add_event(venue_event)

        location = MockLocation("Test City", [venue])
        game.WORLD_MAP = {location.name: location}
        game._poi_venue_id_map = {venue.venue_id: venue}
        game.player.current_location = location
        game.player.current_poi = venue
        game.player.schedule = PlayerSchedule()
        start = GameTime(2024, 1, 1, 8, 0)
        game.player.schedule.add_event(
            start,
            start,
            venue_event.name,
            "Gig",
            {"event_id": venue_event.event_id, "venue_id": venue.venue_id},
        )

        gig_req_ok = type("GigReq", (), {"status": "satisfied", "missing": [], "missing_severe": []})()
        with patch.object(game, "_assess_gig_requirements", return_value=gig_req_ok):
            game.check_for_scheduled_events()

        self.assertEqual(game.game_state, "performance")
        self.assertEqual(game.performance_stage, "choose_song")
        self.assertIs(game.active_performance, venue_event)
        self.assertEqual(len(game.player.schedule.scheduled_items), 0)

    def test_scheduled_gig_requires_presence_at_real_venue_even_without_destination_metadata(self):
        ui = DummyUI()
        game = Game(ui)
        game.player = Player("Tester")

        target_venue = Venue("venue_target", "Target Venue")
        other_venue = Venue("venue_other", "Other Venue")
        venue_event = Event("Scheduled Set", target_venue, event_type="OPEN_MIC")
        target_venue.add_event(venue_event)

        location = MockLocation("Test City", [target_venue, other_venue])
        game.WORLD_MAP = {location.name: location}
        game._poi_venue_id_map = {
            target_venue.venue_id: target_venue,
            other_venue.venue_id: other_venue,
        }
        game.player.current_location = location
        game.player.current_poi = other_venue
        game.player.schedule = PlayerSchedule()

        start = GameTime(2024, 1, 1, 8, 0)
        game.player.schedule.add_event(
            start,
            start,
            venue_event.name,
            "Gig",
            {"event_id": venue_event.event_id, "location_name": location.name},
        )

        game.check_for_scheduled_events()

        self.assertNotEqual(game.game_state, "performance")
        self.assertIsNone(game.active_performance)
        self.assertEqual(len(game.player.schedule.scheduled_items), 0)
        self.assertTrue(any("missed" in msg.lower() for msg in ui.messages))
        memory_hits = game.world_memory.query(event_type="missed_gig", entity_id=game.player.name)
        self.assertTrue(memory_hits)

    def test_scheduled_gig_missing_loadout_fails_terminally_and_records_memory(self):
        ui = DummyUI()
        game = Game(ui)
        game.player = Player("Tester")

        venue = Venue("venue_1", "Test Venue")
        venue_event = Event("Scheduled Set", venue, event_type="OPEN_MIC")
        venue.add_event(venue_event)

        location = MockLocation("Test City", [venue])
        game.WORLD_MAP = {location.name: location}
        game._poi_venue_id_map = {venue.venue_id: venue}
        game.player.current_location = location
        game.player.current_poi = venue
        game.player.gear_inventory = []
        game.player.schedule = PlayerSchedule()

        start = GameTime(2024, 1, 1, 8, 0)
        game.player.schedule.add_event(
            start,
            start,
            venue_event.name,
            "Gig",
            {"event_id": venue_event.event_id, "venue_id": venue.venue_id},
        )

        game.check_for_scheduled_events()

        self.assertNotEqual(game.game_state, "performance")
        self.assertEqual(len(game.player.schedule.scheduled_items), 0)
        self.assertTrue(any("missing critical loadout" in msg.lower() for msg in ui.messages))
        memory_hits = game.world_memory.query(event_type="missed_gig", entity_id=game.player.name)
        self.assertTrue(memory_hits)
        self.assertEqual(memory_hits[-1].metadata.get("reason_code"), "missing_required_loadout")

    def test_scheduled_gig_window_elapsed_is_terminal_failure_even_at_correct_venue(self):
        ui = DummyUI()
        game = Game(ui)
        game.player = Player("Tester")

        venue = Venue("venue_1", "Test Venue")
        venue_event = Event("Scheduled Set", venue, event_type="OPEN_MIC")
        venue.add_event(venue_event)

        location = MockLocation("Test City", [venue])
        game.WORLD_MAP = {location.name: location}
        game._poi_venue_id_map = {venue.venue_id: venue}
        game.player.current_location = location
        game.player.current_poi = venue
        game.player.schedule = PlayerSchedule()

        start = GameTime(2024, 1, 1, 7, 0)
        end = GameTime(2024, 1, 1, 7, 30)
        game.player.schedule.add_event(
            start,
            end,
            venue_event.name,
            "Gig",
            {"event_id": venue_event.event_id, "venue_id": venue.venue_id},
        )

        game.check_for_scheduled_events()

        self.assertNotEqual(game.game_state, "performance")
        self.assertEqual(len(game.player.schedule.scheduled_items), 0)
        self.assertTrue(any("window already closed" in msg.lower() for msg in ui.messages))
        memory_hits = game.world_memory.query(event_type="missed_gig", entity_id=game.player.name)
        self.assertTrue(memory_hits)
        self.assertEqual(memory_hits[-1].metadata.get("reason_code"), "window_elapsed")

    def test_booked_creative_meeting_fails_explicitly_when_not_at_booked_poi(self):
        ui = DummyUI()
        game = Game(ui)
        game.player = Player("Tester")

        location = Location("Test City", "City")
        booked_poi = PointOfInterest("studio_a", "Studio A", "Studio", category="STUDIO_RECORDING")
        other_poi = PointOfInterest("cafe_a", "Cafe A", "Cafe", category="POI_CAFE")
        location.add_poi(booked_poi)
        location.add_poi(other_poi)

        game.player.current_location = location
        game.player.current_poi = other_poi
        game.player.schedule = PlayerSchedule()

        start = GameTime(2024, 1, 1, 8, 0)
        game.player.schedule.add_event(
            start,
            start,
            "Songwriting Session",
            "Meeting",
            {"destination_id": booked_poi.poi_id, "requires_presence": True},
        )

        due_event = game.player.schedule.scheduled_items[0]
        game.check_for_scheduled_events()

        self.assertEqual(len(game.player.schedule.scheduled_items), 0)
        self.assertEqual(due_event.details.get("creative_obligation_status"), "failed_absent")
        self.assertTrue(any("missed" in msg.lower() for msg in ui.messages))
        memory_hits = game.world_memory.query(event_type="missed_obligation", entity_id=game.player.name)
        self.assertTrue(memory_hits)
        self.assertEqual(memory_hits[-1].location, booked_poi.poi_id)

    def test_booked_rehearsal_at_correct_poi_still_fails_without_required_loadout(self):
        ui = DummyUI()
        game = Game(ui)
        game.player = Player("Tester")

        location = Location("Test City", "City")
        rehearsal_poi = PointOfInterest("rehearsal_a", "Rehearsal A", "Room", category="STUDIO_RECORDING")
        location.add_poi(rehearsal_poi)

        game.player.current_location = location
        game.player.current_poi = rehearsal_poi
        game.player.gear_inventory = []
        game.player.schedule = PlayerSchedule()

        start = GameTime(2024, 1, 1, 8, 0)
        game.player.schedule.add_event(
            start,
            start,
            "Booked Rehearsal Session",
            "Rehearsal",
            {"destination_id": rehearsal_poi.poi_id, "requires_presence": True},
        )

        due_event = game.player.schedule.scheduled_items[0]
        game.check_for_scheduled_events()

        self.assertEqual(len(game.player.schedule.scheduled_items), 0)
        self.assertEqual(due_event.details.get("creative_obligation_status"), "failed_readiness")
        self.assertEqual(due_event.details.get("creative_obligation_reason_code"), "missing_required_loadout")
        self.assertTrue(any("required loadout missing" in msg.lower() for msg in ui.messages))
        memory_hits = game.world_memory.query(event_type="missed_obligation", entity_id=game.player.name)
        self.assertTrue(memory_hits)
        self.assertEqual(memory_hits[-1].metadata.get("reason_code"), "missing_required_loadout")

    def test_booked_creative_window_elapsed_is_explicit_terminal_failure(self):
        ui = DummyUI()
        game = Game(ui)
        game.player = Player("Tester")

        location = Location("Test City", "City")
        studio = PointOfInterest("studio_a", "Studio A", "Studio", category="STUDIO_RECORDING")
        location.add_poi(studio)

        game.player.current_location = location
        game.player.current_poi = studio
        game.player.schedule = PlayerSchedule()

        start = GameTime(2024, 1, 1, 7, 0)
        end = GameTime(2024, 1, 1, 7, 30)
        game.player.schedule.add_event(
            start,
            end,
            "Booked Studio Session",
            "Studio Session",
            {"destination_id": studio.poi_id, "requires_presence": True},
        )

        due_event = game.player.schedule.scheduled_items[0]
        game.check_for_scheduled_events()

        self.assertEqual(len(game.player.schedule.scheduled_items), 0)
        self.assertEqual(due_event.details.get("creative_obligation_status"), "failed_window_elapsed")
        self.assertEqual(due_event.details.get("creative_obligation_reason_code"), "window_elapsed")
        self.assertTrue(any("window closed" in msg.lower() for msg in ui.messages))
        memory_hits = game.world_memory.query(event_type="missed_obligation", entity_id=game.player.name)
        self.assertTrue(memory_hits)
        self.assertEqual(memory_hits[-1].metadata.get("reason_code"), "window_elapsed")

    def test_arrival_poi_prefers_transport_hub(self):
        game = Game(DummyUI())
        destination = Location("City Center", "Hub city")
        airport = PointOfInterest("airport", "Airport", "Flights", category="TRANSPORT_AIRPORT")
        cafe = PointOfInterest("cafe", "Cafe", "Coffee", category="POI_CAFE")
        destination.add_poi(cafe)
        destination.add_poi(airport)

        arrival = game._get_arrival_poi(destination, "plane")

        self.assertIs(arrival, airport)

    def test_venue_exposes_interactions_like_poi(self):
        venue = Venue("venue_1", "Test Venue", interaction_options=["Talk to the owner"])

        self.assertEqual(venue.get_interactions(), ["Talk to the owner"])

    def test_intra_city_travel_uses_route_data(self):
        ui = DummyUI(choices=["intra_city", "hall", "walk"])
        game = Game(ui)
        game.player = Player("Tester")
        game.player.money = 10
        city = Location("Test City", "City")
        home = PointOfInterest("home", "Home", "Apartment", category="HOME")
        hall = Venue("hall", "Community Hall")
        city.add_poi(home)
        city.add_venue(hall)
        city.intra_city_poi_connections[frozenset(("home", "hall"))] = {
            "walk": {"time": 12, "cost": 0},
            "taxi": {"time": 3, "cost": 6},
        }
        game.player.current_location = city
        game.player.current_poi = home
        game.game_state = "travel"

        game.handle_travel_menu()

        self.assertIs(game.player.current_poi, hall)
        self.assertEqual(game.player.money, 10)
        self.assertEqual(game.game_state, "main_menu")

    def test_inter_city_public_travel_requires_hub_and_sets_mode(self):
        ui = DummyUI(choices=["inter_city", "Other City", "public", "business"])
        game = Game(ui)
        game.player = Player("Tester")
        game.player.money = 200
        city = Location("Home City", "City")
        other_city = Location("Other City", "Elsewhere")
        bus_stop = PointOfInterest("bus_stop", "Bus Stop", "Transit", category="TRANSPORT_BUS")
        city.add_poi(bus_stop)
        city.add_travel_connection("Other City", 20, 2, method="Bus")
        game.WORLD_MAP = {"Other City": other_city}
        game.player.current_location = city
        game.player.current_poi = bus_stop
        game.game_state = "travel"

        game.handle_travel_menu()

        self.assertEqual(game.game_state, "travel_active")
        self.assertIsNotNone(game.travel_manager)
        self.assertEqual(game.travel_manager.transport_mode, "bus")
        self.assertEqual(game.travel_manager.ticket_class, "business")

    def test_inter_city_vehicle_travel_can_leave_without_hub(self):
        ui = DummyUI(choices=["inter_city", "Other City", "vehicle_0"])
        game = Game(ui)
        game.player = Player("Tester")
        city = Location("Home City", "City")
        other_city = Location("Other City", "Elsewhere")
        home = PointOfInterest("home", "Home", "Apartment", category="HOME")
        car = Vehicle("Beater", 1000, 80, 40, 10, 20)
        city.add_poi(home)
        city.add_travel_connection("Other City", 20, 2, method="Bus")
        game.WORLD_MAP = {"Other City": other_city}
        game.player.current_location = city
        game.player.current_poi = home
        game.player.vehicles.append(car)
        game.game_state = "travel"

        game.handle_travel_menu()

        self.assertEqual(game.game_state, "travel_active")
        self.assertIsNotNone(game.travel_manager)
        self.assertIs(game.travel_manager.vehicle, car)


if __name__ == "__main__":
    unittest.main()
