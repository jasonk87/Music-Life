import unittest
from types import SimpleNamespace
from game.player import Player
from game.pets_system import PetsSystem


class TestPetsSystem(unittest.TestCase):
    def setUp(self):
        self.player = Player("DogLover")
        self.player.money = 5000
        self.player.stress = 60
        self.player.current_location = SimpleNamespace(name="Asbury Park, NJ")

    def test_adopt_shelter_pet_and_care(self):
        sys = PetsSystem()

        adopt_res = sys.adopt_shelter_pet(self.player, "asbury_golden", custom_name="Sunny")
        self.assertTrue(adopt_res["ok"])
        self.assertEqual(len(sys.pets), 1)
        pet = sys.pets[0]
        self.assertEqual(pet.name, "Sunny")
        self.assertEqual(pet.species, "DOG")

        # Play & Walk
        play_res = sys.care_for_pet(self.player, pet.pet_id, "play_and_walk")
        self.assertTrue(play_res["ok"])
        self.assertEqual(self.player.stress, 15)  # 60 - 25 (adopt) - 20 (play) = 15

        # Feed gourmet food
        feed_res = sys.care_for_pet(self.player, pet.pet_id, "feed_gourmet_food")
        self.assertTrue(feed_res["ok"])
        self.assertEqual(pet.hunger, 0.0)


if __name__ == "__main__":
    unittest.main()
