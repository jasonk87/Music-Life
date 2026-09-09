import unittest
from types import SimpleNamespace
from game.player import Player
from game.fitness_and_outdoors import FitnessAndOutdoorsSystem


class TestFitnessAndOutdoors(unittest.TestCase):
    def setUp(self):
        self.player = Player("Athlete")
        self.player.money = 2000
        self.player.energy = 80
        self.player.health = 80
        self.player.stress = 50
        self.player.current_location = SimpleNamespace(name="Los Angeles, CA")

    def test_gym_membership_and_workouts(self):
        sys = FitnessAndOutdoorsSystem()

        join_res = sys.join_gym(self.player)
        self.assertTrue(join_res["ok"])
        self.assertTrue(sys.profile.gym_membership_active)

        # Strength training
        work_res = sys.workout_at_gym(self.player, "strength_training")
        self.assertTrue(work_res["ok"])
        self.assertEqual(self.player.health, 90)
        self.assertEqual(sys.profile.stamina_bonus_earned, 2)

    def test_outdoor_surfing(self):
        sys = FitnessAndOutdoorsSystem()

        surf_res = sys.go_outdoor_recreation(self.player, "surf_ocean")
        self.assertTrue(surf_res["ok"])
        self.assertEqual(self.player.stress, 20)  # 50 - 30 = 20


if __name__ == "__main__":
    unittest.main()
