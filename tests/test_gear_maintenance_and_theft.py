import unittest
from game.player import Player
from game.gear_maintenance import GearMaintenanceSystem


class TestGearMaintenanceAndTheft(unittest.TestCase):
    def setUp(self):
        self.player = Player("Rocker")
        self.player.money = 2000

    def test_luthier_setup_and_tube_biasing(self):
        sys = GearMaintenanceSystem()
        sys.maintenance_status.condition_pct = 60.0
        sys.maintenance_status.needs_setup = True

        setup_res = sys.hire_luthier_guitar_setup(self.player, "full_pro_setup")
        self.assertTrue(setup_res["ok"])
        self.assertEqual(sys.maintenance_status.condition_pct, 100.0)
        self.assertFalse(sys.maintenance_status.needs_setup)

        tube_res = sys.hire_luthier_guitar_setup(self.player, "tube_amp_biasing")
        self.assertTrue(tube_res["ok"])
        self.assertTrue(sys.maintenance_status.tube_amp_bias_ok)

    def test_van_security_guard(self):
        sys = GearMaintenanceSystem()

        sec_res = sys.hire_overnight_van_security(self.player)
        self.assertTrue(sec_res["ok"])
        self.assertTrue(sys.has_overnight_security)

        # Risk check should be null because security is active
        theft_incident = sys.check_overnight_parking_theft_risk(self.player)
        self.assertIsNone(theft_incident)
        self.assertFalse(sys.has_overnight_security)


if __name__ == "__main__":
    unittest.main()
