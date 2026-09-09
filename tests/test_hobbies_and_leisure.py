import unittest
from game.player import Player
from game.hobbies_and_leisure import HobbiesAndLeisureSystem


class TestHobbiesAndLeisure(unittest.TestCase):
    def setUp(self):
        self.player = Player("Artisan")
        self.player.money = 20000
        self.player.stress = 50
        self.player.comfort = 65

    def test_unlock_espresso_and_classic_cars(self):
        sys = HobbiesAndLeisureSystem()

        unlock_res = sys.unlock_hobby(self.player, "espresso_craft")
        self.assertTrue(unlock_res["ok"])
        self.assertIn("espresso_craft", sys.hobbies)

        # Practice hobby
        practice_res = sys.practice_hobby(self.player, "espresso_craft", hours=3)
        self.assertTrue(practice_res["ok"])
        self.assertEqual(sys.hobbies["espresso_craft"].total_hours_spent, 3)
        self.assertEqual(self.player.stress, 5)  # 50 - 15 - 30 = 5


if __name__ == "__main__":
    unittest.main()
