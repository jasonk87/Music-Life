import unittest
from game.player import Player
from game.real_estate import RealEstateSystem


class TestRealEstateAndHomeStudio(unittest.TestCase):
    def setUp(self):
        self.player = Player("Producer")
        self.player.money = 500000
        self.player.comfort = 65

    def test_rent_and_buy_properties(self):
        sys = RealEstateSystem()
        self.assertEqual(sys.current_residence_id, "asbury_apt")

        # Rent Berlin Loft
        rent_res = sys.rent_property(self.player, "berlin_loft")
        self.assertTrue(rent_res["ok"])
        self.assertEqual(sys.current_residence_id, "berlin_loft")
        self.assertEqual(self.player.comfort, 85)

        # Buy Philadelphia Rowhouse
        buy_res = sys.buy_property(self.player, "philly_rowhouse")
        self.assertTrue(buy_res["ok"])
        self.assertTrue(sys.properties["philly_rowhouse"].is_owned)
        self.assertEqual(sys.current_residence_id, "philly_rowhouse")

    def test_home_studio_acoustic_gear_upgrades(self):
        sys = RealEstateSystem()
        base_qual = sys.calculate_home_recording_quality()
        self.assertEqual(base_qual, 0.50)

        # Install Bass Traps & Preamp
        res1 = sys.install_studio_gear(self.player, "gear_bass_traps")
        self.assertTrue(res1["ok"])
        res2 = sys.install_studio_gear(self.player, "gear_tube_preamp")
        self.assertTrue(res2["ok"])

        upgraded_qual = sys.calculate_home_recording_quality()
        self.assertGreater(upgraded_qual, base_qual)
        self.assertAlmostEqual(upgraded_qual, 0.50 + 0.15 + 0.20, places=2)

    def test_noise_complaint_quiet_hours(self):
        sys = RealEstateSystem()
        # Asbury Apartment has low noise tolerance (0.30)
        complaint = sys.check_noise_complaint(hour=23)
        self.assertIsNotNone(complaint)
        self.assertIn("Noise Complaint", complaint)

        # Daytime at 14:00 has no noise complaint
        day_check = sys.check_noise_complaint(hour=14)
        self.assertIsNone(day_check)


if __name__ == "__main__":
    unittest.main()
