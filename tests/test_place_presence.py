import unittest

from game.place_presence import LocationActionEngine, LocalAction
from game.poi import PointOfInterest
from game.venue import Venue
from game.player import Player


class ZeroRng:
    def random(self):
        return 0.0


class TestPlacePresence(unittest.TestCase):
    def setUp(self):
        self.engine = LocationActionEngine()
        self.player = Player("Tester")
        self.player.money = 500

    def test_generate_pawn_hotel_street_club_actions(self):
        pawn = PointOfInterest("pawn_1", "Pawn", "", category="PAWN_SHOP", parent_location_id="Downtown")
        hotel = PointOfInterest("hotel_1", "Hotel", "", category="ACCOMMODATION_HOTEL", parent_location_id="Downtown")
        street = PointOfInterest("street_1", "Main St", "", category="DOWNTOWN", parent_location_id="Downtown")
        club = Venue("club_1", "Club", category="VENUE_CLUB", parent_location_id="Downtown")

        pawn_ids = {a.action_id for a in self.engine.generate_actions(self.player, pawn)}
        hotel_ids = {a.action_id for a in self.engine.generate_actions(self.player, hotel)}
        street_ids = {a.action_id for a in self.engine.generate_actions(self.player, street)}
        club_ids = {a.action_id for a in self.engine.generate_actions(self.player, club)}

        self.assertIn("buy_strings", pawn_ids)
        self.assertIn("rent_room", hotel_ids)
        self.assertIn("walk_district", street_ids)
        self.assertIn("network_scene", club_ids)

    def test_execute_action_consumes_time_and_money(self):
        store = PointOfInterest("music_1", "Strings Shop", "", category="SHOP_MUSIC", parent_location_id="Downtown")
        actions = self.engine.generate_actions(self.player, store)
        buy_strings = next(a for a in actions if a.action_id == "buy_strings")

        advanced = {"minutes": 0}

        def advance(minutes):
            advanced["minutes"] += minutes

        money_before = self.player.money
        result = self.engine.execute_action(
            player=self.player,
            place_obj=store,
            location_obj=None,
            action=buy_strings,
            advance_time=advance,
            logger=None,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(advanced["minutes"], buy_strings.minutes)
        self.assertEqual(self.player.money, money_before - buy_strings.cost)

    def test_contextual_encounter_visibility_pressure(self):
        street = PointOfInterest("street_1", "Main St", "", category="DOWNTOWN", parent_location_id="Downtown")
        action = next(a for a in self.engine.generate_actions(self.player, street) if a.action_id == "walk_district")
        self.player.fame = 180

        result = self.engine.execute_action(
            player=self.player,
            place_obj=street,
            location_obj=None,
            action=action,
            advance_time=lambda minutes: None,
            logger=None,
            rng=ZeroRng(),
        )

        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["encounter"])
        self.assertEqual(result["encounter"]["encounter_type"], "fan_encounter")
        self.assertEqual(result["encounter"]["reason_code"], "public_visibility_pressure")

    def test_execute_action_blocks_unavailable_actions(self):
        street = PointOfInterest("street_1", "Main St", "", category="DOWNTOWN", parent_location_id="Downtown")
        forged = LocalAction("buy_strings", "Buy strings", 1, cost=1, tags=["shopping"])
        advanced = {"minutes": 0}

        result = self.engine.execute_action(
            player=self.player,
            place_obj=street,
            location_obj=None,
            action=forged,
            advance_time=lambda minutes: advanced.__setitem__("minutes", advanced["minutes"] + minutes),
            logger=None,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "action_not_available_here")
        self.assertEqual(advanced["minutes"], 0)

    def test_execute_action_uses_canonical_cost_and_minutes(self):
        store = PointOfInterest("music_1", "Strings Shop", "", category="SHOP_MUSIC", parent_location_id="Downtown")
        forged = LocalAction("buy_strings", "Cheap strings", 1, cost=0, tags=["shopping"])
        advanced = {"minutes": 0}
        money_before = self.player.money

        result = self.engine.execute_action(
            player=self.player,
            place_obj=store,
            location_obj=None,
            action=forged,
            advance_time=lambda minutes: advanced.__setitem__("minutes", advanced["minutes"] + minutes),
            logger=None,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(advanced["minutes"], 15)
        self.assertEqual(self.player.money, money_before - 12)


if __name__ == "__main__":
    unittest.main()
