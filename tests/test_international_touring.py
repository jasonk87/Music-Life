import unittest
from game.player import Player
from game.international_touring import InternationalTouringSystem


class TestInternationalTouring(unittest.TestCase):
    def setUp(self):
        self.player = Player("GlobeTrotter")
        self.player.money = 25000
        self.sys = InternationalTouringSystem()

    def test_apply_visas_and_carnet(self):
        # Apply for UK Visa
        uk_res = self.sys.apply_for_artist_visa(self.player, "London, UK")
        self.assertTrue(uk_res["ok"])
        self.assertIn("uk_creative", self.sys.active_visas)

        # Purchase ATA Carnet bond
        carnet_res = self.sys.purchase_ata_carnet_customs_bond(self.player)
        self.assertTrue(carnet_res["ok"])
        self.assertTrue(self.sys.has_ata_carnet_bond)

        # Land in London
        arr_res = self.sys.process_international_flight_arrival(self.player, "London, UK")
        self.assertTrue(arr_res["ok"])
        self.assertEqual(self.sys.jet_lag_fatigue, 40)

        # Recover from jet lag
        msg = self.sys.recover_from_jet_lag(self.player, hours_slept=8)
        self.assertEqual(self.sys.jet_lag_fatigue, 0)


if __name__ == "__main__":
    unittest.main()
