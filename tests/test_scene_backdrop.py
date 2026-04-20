import unittest

from game.game_time import current_game_time
from game.location import Location
from game.player import Player
from game.player_schedule import PlayerSchedule
from game.poi import PointOfInterest
from game.scene_backdrop import SceneBackdropRenderer, derive_world_visual_state
from game.ui_shell import PlayerUIShell
from game.ui_signals import UISignalLayer
from game.visibility_system import VisibilitySystem
from game.world_memory import WorldMemoryStore


class DummyTM:
    def __init__(self, mode="plane"):
        self.transport_mode = mode
        self.vehicle = None
        self.destination = type("Dest", (), {"name": "Dallas"})()


class DummyGame:
    def __init__(self):
        self.player = Player("Hero")
        self.player.schedule = PlayerSchedule()
        self.player.current_location = Location("Austin", "TX")
        self.player.current_poi = PointOfInterest("home", "Home", "Home", category="HOME", parent_location_id="Austin")
        self.player.current_location.add_poi(self.player.current_poi)

        self.visibility_system = VisibilitySystem()
        self.world_memory = WorldMemoryStore()

        self.game_state = "main_menu"
        self.travel_manager = None
        self.ui_signals = UISignalLayer(self)
        self.ui_shell = PlayerUIShell(self)
        self.scene_backdrop = SceneBackdropRenderer()

    def get_ui_shell_state(self):
        return self.ui_shell.build()


class TestSceneBackdrop(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 10
        current_game_time.minute = 0
        self.game = DummyGame()
        self.renderer = SceneBackdropRenderer()

    def test_scene_selection_from_grounded_home_context(self):
        shell = self.game.get_ui_shell_state()
        world = derive_world_visual_state(self.game)
        spec = self.renderer.build_spec(shell, world)

        self.assertEqual(spec.family, "home")
        self.assertIn(spec.housing_status, {1, 2, 3, 4})

    def test_transit_mode_changes_family(self):
        self.game.game_state = "travel_active"
        self.game.travel_manager = DummyTM(mode="plane")

        shell = self.game.get_ui_shell_state()
        spec = self.renderer.build_spec(shell, derive_world_visual_state(self.game))

        self.assertEqual(spec.family, "transit")
        self.assertIn(spec.variant, {"commercial_plane", "private_jet"})
        self.assertGreaterEqual(spec.transport_prestige, 6)
        self.assertGreaterEqual(spec.readability_overlay_alpha_top, 60)

    def test_housing_tier_changes_home_variant(self):
        shell = self.game.get_ui_shell_state()

        self.game.player.money = 80
        rough = self.renderer.build_spec(shell, derive_world_visual_state(self.game))

        self.game.player.money = 7000
        rich = self.renderer.build_spec(shell, derive_world_visual_state(self.game))

        self.assertNotEqual(rough.variant, rich.variant)
        self.assertGreater(rich.housing_status, rough.housing_status)

    def test_palette_variation_differs_by_headline_context(self):
        shell_a = self.game.get_ui_shell_state()
        spec_a = self.renderer.build_spec(shell_a, derive_world_visual_state(self.game))

        # alter headline through poi
        self.game.player.current_poi = PointOfInterest("hotel", "Hotel Suite", "Hotel", category="ACCOMMODATION_HOTEL", parent_location_id="Austin")
        shell_b = self.game.get_ui_shell_state()
        spec_b = self.renderer.build_spec(shell_b, derive_world_visual_state(self.game))

        self.assertNotEqual(spec_a.palette, spec_b.palette)
        self.assertNotEqual(spec_a.style_variant, "")

    def test_renderer_is_read_only_on_game_state(self):
        shell_before = self.game.get_ui_shell_state()
        state_before = {
            "money": self.game.player.money,
            "fame": self.game.player.fame,
            "poi": self.game.player.current_poi.name,
        }

        _ = self.renderer.build_spec(shell_before, derive_world_visual_state(self.game))

        state_after = {
            "money": self.game.player.money,
            "fame": self.game.player.fame,
            "poi": self.game.player.current_poi.name,
        }
        self.assertEqual(state_before, state_after)

    def test_backdrop_does_not_break_shell_access(self):
        shell = self.game.get_ui_shell_state()
        spec = self.game.scene_backdrop.build_spec(shell, derive_world_visual_state(self.game))

        self.assertIn("top_context", shell)
        self.assertTrue(spec.label)
        self.assertTrue(spec.continuity_key)

    def test_venue_scale_and_crowd_mode_shift_with_state(self):
        self.game.player.current_poi = PointOfInterest("venue", "Main Stage", "Venue", category="VENUE_CLUB", parent_location_id="Austin")
        self.game.player.fame = 20
        low_spec = self.renderer.build_spec(self.game.get_ui_shell_state(), derive_world_visual_state(self.game))

        self.game.player.fame = 320
        self.game.visibility_system.entity_visibility[self.game.player.name] = {
            "base_visibility": 20.0,
            "recent_buzz": 15.0,
            "negative_pressure": 0.0,
        }
        high_spec = self.renderer.build_spec(self.game.get_ui_shell_state(), derive_world_visual_state(self.game))

        self.assertIn(low_spec.venue_scale, {"tiny", "small", "medium"})
        self.assertIn(high_spec.venue_scale, {"large", "arena"})
        self.assertIn(high_spec.crowd_mode, {"dense_clusters", "arena_bands"})
        self.assertGreater(high_spec.work_prestige, low_spec.work_prestige)

    def test_transit_prestige_mapping_distinguishes_modes(self):
        self.game.game_state = "travel_active"
        self.game.travel_manager = DummyTM(mode="bus")
        shell = self.game.get_ui_shell_state()

        bike_spec = self.renderer.build_spec(shell, {**derive_world_visual_state(self.game), "transport_mode": "bike"})
        limo_spec = self.renderer.build_spec(shell, {**derive_world_visual_state(self.game), "transport_mode": "limo"})
        jet_spec = self.renderer.build_spec(shell, {**derive_world_visual_state(self.game), "transport_mode": "private_jet"})

        self.assertLess(bike_spec.transport_prestige, limo_spec.transport_prestige)
        self.assertLess(limo_spec.transport_prestige, jet_spec.transport_prestige)

    def test_continuity_key_stabilizes_style_across_calls(self):
        shell = self.game.get_ui_shell_state()
        world = derive_world_visual_state(self.game)
        a = self.renderer.build_spec(shell, world)
        b = self.renderer.build_spec(shell, world)
        self.assertEqual(a.style_variant, b.style_variant)
        self.assertEqual(a.palette, b.palette)

    def test_variation_changes_with_different_continuity_keys(self):
        shell = self.game.get_ui_shell_state()
        base_world = derive_world_visual_state(self.game)
        s1 = self.renderer.build_spec(shell, {**base_world, "home_key": "hero:home_a"})
        s2 = self.renderer.build_spec(shell, {**base_world, "home_key": "hero:home_b"})
        self.assertNotEqual(s1.continuity_key, s2.continuity_key)
        self.assertTrue(s1.style_variant != s2.style_variant or s1.palette != s2.palette)

    def test_audio_cue_mapping_matches_scene_type(self):
        self.game.game_state = "travel_active"
        self.game.travel_manager = DummyTM(mode="plane")
        transit = self.renderer.build_spec(self.game.get_ui_shell_state(), derive_world_visual_state(self.game))
        transit_cues = self.renderer.get_scene_audio_cues(transit)
        self.assertIn("ambient", transit_cues)
        self.assertIn("plane", transit_cues["ambient"])

        self.game.game_state = "main_menu"
        self.game.player.current_poi = PointOfInterest("venue", "Main Stage", "Venue", category="VENUE_CLUB", parent_location_id="Austin")
        self.game.player.fame = 320
        self.game.visibility_system.entity_visibility[self.game.player.name] = {"base_visibility": 18.0, "recent_buzz": 14.0, "negative_pressure": 0.0}
        work = self.renderer.build_spec(self.game.get_ui_shell_state(), derive_world_visual_state(self.game))
        work_cues = self.renderer.get_scene_audio_cues(work)
        self.assertIn(work_cues["crowd"], {"crowd_applause", "crowd_roar"})


if __name__ == "__main__":
    unittest.main()
