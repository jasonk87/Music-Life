import unittest
from game.themes import THEME_CATALOG
from game.traits import TRAIT_CATALOG


class TestThemesAndTraits(unittest.TestCase):
    def test_theme_catalog_expansion(self):
        self.assertGreaterEqual(len(THEME_CATALOG), 12)
        self.assertIn("cyberpunk_dystopia", THEME_CATALOG)
        self.assertIn("blue_collar_struggle", THEME_CATALOG)
        self.assertIn("cosmic_psychedelia", THEME_CATALOG)

        theme = THEME_CATALOG["cyberpunk_dystopia"]
        self.assertGreaterEqual(theme["bonus_multiplier"], 1.15)
        self.assertIn("Synthwave", theme["genre_affinity"])

    def test_trait_catalog_expansion(self):
        self.assertGreaterEqual(len(TRAIT_CATALOG), 12)
        self.assertIn("audiophile_perfectionist", TRAIT_CATALOG)
        self.assertIn("resilient_road_dog", TRAIT_CATALOG)
        self.assertIn("resilient", TRAIT_CATALOG)
        self.assertIn("analog_purist", TRAIT_CATALOG)

        audiophile = TRAIT_CATALOG["audiophile_perfectionist"]
        self.assertEqual(audiophile.effect_type, "recording_quality_mult")

    def test_all_background_traits_exist(self):
        # Verify that all traits used by backgrounds exist in TRAIT_CATALOG
        expected_traits = ["resilient", "resilient_road_dog", "charismatic", "virtuoso", "night_owl"]
        for trait_id in expected_traits:
            self.assertIn(trait_id, TRAIT_CATALOG)
            self.assertIsNotNone(TRAIT_CATALOG[trait_id])


if __name__ == "__main__":
    unittest.main()
