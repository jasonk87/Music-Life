import os
import unittest
from types import SimpleNamespace
from game.game import Game
from game.player import Player
from game.save_manager import JSONSaveManager


class DummyUI:
    def add_log_message(self, msg):
        pass


class TestSaveManagerV1_5(unittest.TestCase):
    def setUp(self):
        self.game = Game(DummyUI())
        self.game.player = Player("Lennon")
        self.game.player.money = 500000
        self.game.player.fame = 200
        self.game.player.street_cred = 85
        self.game.player.current_location = SimpleNamespace(name="Asbury Park, NJ")

        # Romance
        self.game.relationships_and_family.meet_and_ask_out(self.game.player, "maya_artist_asbury")
        self.game.relationships_and_family.send_money_to_family(self.game.player, amount=5000)

        # Pet
        self.game.pets_system.adopt_shelter_pet(self.game.player, "asbury_golden", custom_name="Barnaby")

        # Hobby
        self.game.hobbies_and_leisure.unlock_hobby(self.game.player, "espresso_craft")

        # Fitness
        self.game.fitness_and_outdoors.join_gym(self.game.player)

        # Investments
        self.game.investments_and_wealth.buy_stock_shares(self.game.player, "SPY", dollar_amount=25000)
        self.game.investments_and_wealth.buy_commercial_property(self.game.player, "asbury_boardwalk_cafe")

        # Charity
        self.game.community_charity.donate_to_initiative(self.game.player, "youth_instrument_fund")

    def test_save_load_roundtrip_v1_5(self):
        save_file = "test_save_v1_5.json"
        saved = JSONSaveManager.save_game(self.game, filepath=save_file)
        self.assertTrue(saved)

        new_game = Game(DummyUI())
        loaded = JSONSaveManager.load_game(new_game, filepath=save_file)
        self.assertTrue(loaded)

        # Verify player
        self.assertEqual(new_game.player.name, "Lennon")

        # Verify Relationships
        self.assertIsNotNone(new_game.relationships_and_family.partner)
        self.assertEqual(new_game.relationships_and_family.partner.name, "Maya Lin")
        self.assertEqual(new_game.relationships_and_family.family.total_money_sent_home, 5000)

        # Verify Pet
        self.assertEqual(len(new_game.pets_system.pets), 1)
        self.assertEqual(new_game.pets_system.pets[0].name, "Barnaby")

        # Verify Hobby
        self.assertIn("espresso_craft", new_game.hobbies_and_leisure.hobbies)

        # Verify Fitness
        self.assertTrue(new_game.fitness_and_outdoors.profile.gym_membership_active)

        # Verify Investments
        self.assertEqual(new_game.investments_and_wealth.stocks["SPY"].total_invested, 25000)
        self.assertTrue(new_game.investments_and_wealth.commercial_properties["asbury_boardwalk_cafe"].is_owned)

        # Verify Charity
        self.assertEqual(new_game.community_charity.total_donated, 5000)

        if os.path.exists(save_file):
            os.remove(save_file)


if __name__ == "__main__":
    unittest.main()
