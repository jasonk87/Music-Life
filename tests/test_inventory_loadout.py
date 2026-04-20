import unittest

from game.inventory_loadout import InventoryLoadoutService
from game.place_presence import LocationActionEngine
from game.player import Player
from game.poi import PointOfInterest
from game_data.gear_catalog import GEAR_CATALOG


class TestInventoryLoadout(unittest.TestCase):
    def setUp(self):
        self.service = InventoryLoadoutService()
        self.player = Player("Planner")
        self.service.ensure_player_fields(self.player)

        # Reset inventory to deterministic test state.
        self.player.gear_inventory = []
        self.player.home_storage = []
        self.player.temporary_stashes = {}

    def test_accessibility_distinguishes_owned_vs_accessible(self):
        home_poi = "home_1"
        current_poi = "venue_9"
        strings = GEAR_CATALOG["guitar_strings_basic"]
        self.player.home_storage.append(strings)

        accessible = self.service.accessible_now(self.player, home_poi_id=home_poi, current_poi_id=current_poi)
        self.assertEqual(len(accessible), 0)

        accessible_home = self.service.accessible_now(self.player, home_poi_id=home_poi, current_poi_id=home_poi)
        self.assertEqual(len(accessible_home), 1)
        self.assertEqual(accessible_home[0].item_id, "guitar_strings_basic")

    def test_apply_loadout_pulls_from_home_when_present(self):
        home_poi = "home_1"
        guitar = GEAR_CATALOG["worn_acoustic_guitar"]
        strings = GEAR_CATALOG["guitar_strings_basic"]
        self.player.home_storage.extend([guitar, strings])

        self.service.apply_loadout(self.player, "local_gig_kit", home_poi_id=home_poi, current_poi_id=home_poi)

        ids = [item.item_id for item in self.player.gear_inventory]
        self.assertIn("worn_acoustic_guitar", ids)
        self.assertIn("guitar_strings_basic", ids)

    def test_requirement_check_missing_strings_recoverable(self):
        home_poi = "home_1"
        self.player.gear_inventory.append(GEAR_CATALOG["worn_acoustic_guitar"])
        requirements = [
            {"match_type": "semantic", "key": "instrument", "count": 1, "mandatory": True},
            {"match_type": "semantic", "key": "strings", "count": 1, "mandatory": True},
        ]

        assessment = self.service.assess_requirements(self.player, requirements, home_poi_id=home_poi, current_poi_id="club_1")
        self.assertEqual(assessment.status, "missing_but_recoverable")
        self.assertIn("strings", assessment.missing)

    def test_recovery_case_buy_strings_then_requirements_pass(self):
        self.player.gear_inventory.append(GEAR_CATALOG["worn_acoustic_guitar"])
        street_shop = PointOfInterest("music_1", "Music Store", "", category="SHOP_MUSIC", parent_location_id="City")
        engine = LocationActionEngine()
        buy_strings = next(a for a in engine.generate_actions(self.player, street_shop) if a.action_id == "buy_strings")

        result = engine.execute_action(
            player=self.player,
            place_obj=street_shop,
            location_obj=None,
            action=buy_strings,
            advance_time=lambda minutes: None,
            logger=None,
        )
        self.assertTrue(result["ok"])
        self.assertIn("guitar_strings_basic", result["item_grants"])

        # Simulate game integration applying grants to carry inventory.
        for grant in result["item_grants"]:
            self.player.gear_inventory.append(GEAR_CATALOG[grant])

        requirements = [
            {"match_type": "semantic", "key": "instrument", "count": 1, "mandatory": True},
            {"match_type": "semantic", "key": "strings", "count": 1, "mandatory": True},
        ]
        assessment = self.service.assess_requirements(self.player, requirements, home_poi_id="home_1", current_poi_id="music_1")
        self.assertEqual(assessment.status, "fully_satisfied")


if __name__ == "__main__":
    unittest.main()
