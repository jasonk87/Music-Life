import unittest
from game.player import Player
from game.staff import StaffManagementSystem, StaffMember


class TestStaffManagement(unittest.TestCase):
    def setUp(self):
        self.player = Player("EntourageBoss")
        self.player.money = 20000
        self.player.comfort = 60
        self.player.stress = 40

    def test_hire_staff_and_process_payroll(self):
        sys = StaffManagementSystem()

        hire_res = sys.hire_staff_member(self.player, "tour_chef")
        self.assertTrue(hire_res["ok"])
        self.assertEqual(len(sys.hired_staff), 1)
        self.assertEqual(self.player.comfort, 70)
        self.assertEqual(self.player.stress, 30)

        # Process weekly payroll
        initial_money = self.player.money
        logs = sys.process_weekly_staff_payroll(self.player)
        self.assertEqual(len(logs), 1)
        self.assertEqual(self.player.money, initial_money - 1200)


if __name__ == "__main__":
    unittest.main()
