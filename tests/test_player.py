import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game.player import Player
from game.gear import GearItem # Correct import
from game.game_time import GameTime, current_game_time

class TestPlayer(unittest.TestCase):

    def setUp(self):
        """Set up a new Player instance before each test."""
        # It's important to reset the global game time for consistent tests
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 8
        current_game_time.minute = 0
        self.player = Player("Test Player")

    def test_player_initialization(self):
        """Test that the player is initialized with correct default values."""
        self.assertEqual(self.player.name, "Test Player")
        self.assertEqual(self.player.money, 500)
        self.assertEqual(self.player.fame, 0)
        self.assertEqual(self.player.energy, 100)
        self.assertEqual(self.player.stress, 0)
        self.assertIsNotNone(self.player.schedule)
        self.assertEqual(len(self.player.pending_contracts), 0)

    def test_practice_skill(self):
        """Test the practice_skill method."""
        initial_guitar_skill = self.player.skills.get("guitar", 0)
        self.player.practice_skill("guitar", 2)
        # The formula is hours * 0.1
        self.assertAlmostEqual(self.player.skills["guitar"], initial_guitar_skill + 0.2)

        # Test practicing a new skill
        self.assertNotIn("bass", self.player.skills)
        self.player.practice_skill("bass", 3)
        self.assertIn("bass", self.player.skills)
        self.assertAlmostEqual(self.player.skills["bass"], 0.3)

    def test_add_and_remove_gear(self):
        """Test adding and removing gear from inventory."""
        gear1 = GearItem("picks", "Guitar Picks", "Some picks", "ACCESSORY", 1, 10)

        self.assertTrue(self.player.add_gear(gear1))
        self.assertEqual(self.player.get_current_gear_load(), 1)
        self.assertIn(gear1, self.player.gear_inventory)

        self.assertTrue(self.player.remove_gear(gear1))
        self.assertEqual(self.player.get_current_gear_load(), 0)
        self.assertNotIn(gear1, self.player.gear_inventory)

if __name__ == '__main__':
    unittest.main()
