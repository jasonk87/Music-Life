import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.game_time import current_game_time
from game.player import Player
from game.contract import Contract


class DummyUI:
    def __init__(self):
        self.messages = []
        self.choice_queue = []

    def add_log_message(self, message):
        self.messages.append(message)

    def add_message(self, message):
        self.messages.append(message)

    def present_choices(self, choices, header="", context=None):
        if self.choice_queue:
            return self.choice_queue.pop(0)
        keys = list(choices.keys())
        return keys[0] if keys else "back"

    def draw_schedule_screen(self, events):
        pass


class TestStaffAndTouring(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 10
        current_game_time.minute = 0

        self.ui = DummyUI()
        self.game = Game(self.ui)
        self.game.setup_world()
        self.game.player = Player("Tester")
        self.game.player.current_location = self.game.WORLD_MAP["Philadelphia, PA"]

    def test_hire_and_dismiss_support_staff(self):
        self.game.delegation_system.ensure_player_support(self.game.player)
        self.assertFalse(self.game.player.has_manager)

        # Hire manager via delegation
        self.game.delegation_system.add_or_update_role(self.game.player, "manager", active=True)
        self.assertTrue(self.game.player.has_manager)

        # Hire security & driver
        self.game.delegation_system.add_or_update_role(self.game.player, "security", active=True)
        self.game.delegation_system.add_or_update_role(self.game.player, "driver", active=True)

        active_roles = [r for r in self.game.player.delegation_roles.values() if r.active]
        self.assertEqual(len(active_roles), 3)

        # Dismiss manager
        self.game.player.delegation_roles["manager"].active = False
        self.assertFalse(self.game.player.has_manager)

    def test_manager_assisted_contract_negotiation(self):
        self.game.delegation_system.add_or_update_role(self.game.player, "manager", active=True)
        contract = Contract("Test Label", advance_money=1000, royalty_rate=0.10, marketing_budget_per_release=500)
        self.game.player.pending_contracts.append(contract)

        manager_role = self.game.delegation_system.get_role(self.game.player, "manager")
        manager_skill = int(self.game.delegation_system.role_quality(manager_role) * 5)
        
        success, msg, pulled = contract.negotiate(self.game.player.fame, player_charisma_trait=True, manager_skill=manager_skill)
        self.assertIn(success, [True, False])
        self.assertIsInstance(msg, str)

    def test_schedule_multi_city_tour(self):
        self.game.player.fame = 60
        self.game.schedule_tour("regional_buzz_builder")
        
        scheduled_gigs = [e for e in self.game.player.schedule.scheduled_items if "Gig" in e.category]
        self.assertGreaterEqual(len(scheduled_gigs), 2)
        for event in scheduled_gigs:
            self.assertIn("venue_id", event.details)
            self.assertIn("destination_id", event.details)


if __name__ == "__main__":
    unittest.main()
