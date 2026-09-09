import unittest
from game.player import Player
from game.investments_and_wealth import InvestmentsAndWealthSystem


class TestInvestmentsAndWealth(unittest.TestCase):
    def setUp(self):
        self.player = Player("Investor")
        self.player.money = 300000

    def test_stock_investing_and_commercial_real_estate(self):
        sys = InvestmentsAndWealthSystem()

        # Invest in S&P 500
        stock_res = sys.buy_stock_shares(self.player, "SPY", dollar_amount=50000)
        self.assertTrue(stock_res["ok"])
        self.assertEqual(sys.stocks["SPY"].total_invested, 50000)

        # Buy commercial cafe building
        buy_res = sys.buy_commercial_property(self.player, "asbury_boardwalk_cafe")
        self.assertTrue(buy_res["ok"])
        self.assertTrue(sys.commercial_properties["asbury_boardwalk_cafe"].is_owned)

        # Monthly income processing
        initial_money = self.player.money
        logs = sys.process_monthly_investment_income(self.player)
        self.assertTrue(len(logs) >= 2)
        self.assertGreater(self.player.money, initial_money)


if __name__ == "__main__":
    unittest.main()
