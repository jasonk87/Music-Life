import unittest
from types import SimpleNamespace
from game.player import Player
from game.major_label_system import MajorLabelSystem


class TestMajorLabelsAndContracts(unittest.TestCase):
    def setUp(self):
        self.player = Player("Icon")
        self.player.money = 5000
        self.player.fame = 150
        self.player.street_cred = 80
        self.player.current_location = SimpleNamespace(name="New York City, NY")

    def test_ar_scouting_in_nyc(self):
        label_sys = MajorLabelSystem()
        offers = label_sys.check_ar_scouting(self.player)
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["name"], "Empire Records International")

    def test_sign_empire_records_deal_and_recoupment(self):
        label_sys = MajorLabelSystem()
        res = label_sys.negotiate_and_sign_contract(self.player, "empire_nyc")
        self.assertTrue(res["ok"])
        self.assertEqual(label_sys.signed_contract.advance_amount, 500000)
        self.assertEqual(self.player.money, 505000)

        # Recoupment simulation
        # $100,000 gross royalties -> 18% artist share = $18,000 against $500,000 advance
        recoup_res = label_sys.process_royalties_recoupment(self.player, gross_royalties=100000.0)
        self.assertFalse(recoup_res["recouped"])
        self.assertEqual(recoup_res["artist_payout"], 0.0)
        self.assertEqual(label_sys.signed_contract.recoupable_balance, 500000.0 - 18000.0)


if __name__ == "__main__":
    unittest.main()
