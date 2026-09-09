import unittest
from game.player import Player
from game.finance_and_legal import FinanceAndLegalSystem


class TestFinanceAndLegal(unittest.TestCase):
    def setUp(self):
        self.player = Player("Mogul")
        self.player.money = 200000

    def test_hire_cpa_and_tax_deductions(self):
        sys = FinanceAndLegalSystem()

        hire_res = sys.hire_entertainment_cpa(self.player, "philly_liberty_cpa")
        self.assertTrue(hire_res["ok"])
        self.assertIsNotNone(sys.hired_cpa)

        # Tax season with CPA (50% write-off on $100k gross)
        # Raw tax: $25k -> Deduction: $12.5k -> Final: $12.5k
        tax_res = sys.calculate_and_pay_annual_taxes(self.player, gross_annual_earnings=100000)
        self.assertTrue(tax_res["ok"])
        self.assertEqual(tax_res["taxes_paid"], 12500)
        self.assertEqual(tax_res["deductions"], 12500)

    def test_copyright_lawsuit_settlement(self):
        sys = FinanceAndLegalSystem()
        suit = sys.trigger_sample_copyright_lawsuit("s1", "Chart Hit")
        self.assertEqual(len(sys.pending_lawsuits), 1)

        settle_res = sys.resolve_lawsuit_settlement(self.player, suit.lawsuit_id, choose_settle=True)
        self.assertTrue(settle_res["ok"])
        self.assertTrue(suit.is_resolved)
        self.assertEqual(suit.verdict, "SETTLED_OUT_OF_COURT")


if __name__ == "__main__":
    unittest.main()
