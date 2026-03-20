import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game_data.gear_catalog import GEAR_CATALOG


class TestGearCatalog(unittest.TestCase):
    def test_catalog_keys_are_unique(self):
        """Guard against accidental duplicate dictionary keys."""
        expected_item_count = 24
        self.assertEqual(len(GEAR_CATALOG), expected_item_count)

    def test_cheap_burger_has_comfort_effect(self):
        """Ensure Cheap Greasy Burger keeps its intended comfort modifier."""
        self.assertEqual(
            GEAR_CATALOG["food_cheap_burger"].properties.get("comfort_effect"),
            -2,
        )


if __name__ == "__main__":
    unittest.main()
