from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class StockInvestment:
    symbol: str
    name: str
    shares_owned: int = 0
    total_invested: int = 0
    current_value: float = 0.0
    dividend_yield_pct: float = 3.5


@dataclass
class CommercialProperty:
    property_key: str
    name: str
    city: str
    purchase_price: int
    monthly_rental_income: int
    is_owned: bool = False


class InvestmentsAndWealthSystem:
    """Manages S&P 500 stock index portfolios, dividend compounding, and commercial rental real estate."""

    COMMERCIAL_CATALOG = {
        "asbury_boardwalk_cafe": CommercialProperty(
            property_key="asbury_boardwalk_cafe",
            name="Boardwalk Artisan Coffee Shop Building",
            city="Asbury Park, NJ",
            purchase_price=180000,
            monthly_rental_income=1400,
        ),
        "philly_rehearsal_studios": CommercialProperty(
            property_key="philly_rehearsal_studios",
            name="South Street 6-Room Band Rehearsal Complex",
            city="Philadelphia, PA",
            purchase_price=350000,
            monthly_rental_income=2800,
        ),
        "austin_food_truck_park": CommercialProperty(
            property_key="austin_food_truck_park",
            name="South Congress Food Truck & Music Park Lot",
            city="Austin, TX",
            purchase_price=500000,
            monthly_rental_income=4200,
        ),
    }

    def __init__(self):
        self.stocks = {
            "SPY": StockInvestment("SPY", "S&P 500 Broad Market Index Fund", dividend_yield_pct=1.8),
            "TECH_DIV": StockInvestment("TECH_DIV", "Blue-Chip Tech & Dividend Portfolio", dividend_yield_pct=4.2),
        }
        self.commercial_properties: Dict[str, CommercialProperty] = dict(self.COMMERCIAL_CATALOG)
        self.total_dividends_earned: float = 0.0
        self.total_commercial_rent_earned: int = 0

    def buy_stock_shares(self, player, symbol: str, dollar_amount: int) -> Dict[str, Any]:
        stock = self.stocks.get(symbol)
        if not stock:
            return {"ok": False, "explanation": "Stock fund not found."}

        if dollar_amount <= 0:
            return {"ok": False, "explanation": "Investment amount must be greater than zero."}

        if player.money < dollar_amount:
            return {"ok": False, "explanation": f"Insufficient funds. Need ${dollar_amount:,}."}

        player.money -= dollar_amount
        stock.total_invested += dollar_amount
        stock.current_value += dollar_amount
        stock.shares_owned += int(dollar_amount / 100) # simplified share units

        summary = (
            f"📈 INVESTED IN {stock.name} ({symbol})!\n"
            f"- Amount Added: ${dollar_amount:,}\n"
            f"- Total Portfolio Value: ${int(stock.current_value):,}\n"
            f"- Annual Dividend Yield: {stock.dividend_yield_pct}%"
        )
        return {"ok": True, "stock": stock, "explanation": summary}

    def buy_commercial_property(self, player, prop_key: str) -> Dict[str, Any]:
        prop = self.commercial_properties.get(prop_key)
        if not prop:
            return {"ok": False, "explanation": "Commercial property not found."}

        if prop.is_owned:
            return {"ok": False, "explanation": f"You already own {prop.name}."}

        if player.money < prop.purchase_price:
            return {"ok": False, "explanation": f"Need ${prop.purchase_price:,} to purchase {prop.name}."}

        player.money -= prop.purchase_price
        prop.is_owned = True
        player.fame = min(1000, player.fame + 20)

        summary = (
            f"🏢 ACQUIRED COMMERCIAL REAL ESTATE ASSET: {prop.name} in {prop.city}!\n"
            f"- Purchase Price: -${prop.purchase_price:,}\n"
            f"- Monthly Commercial Rental Income: +${prop.monthly_rental_income:,}/month\n"
            f"- Title deed registered to your investment company."
        )
        return {"ok": True, "property": prop, "explanation": summary}

    def process_monthly_investment_income(self, player) -> List[str]:
        logs = []
        # 1. Commercial rents
        total_rent = sum(p.monthly_rental_income for p in self.commercial_properties.values() if p.is_owned)
        if total_rent > 0:
            player.money += total_rent
            self.total_commercial_rent_earned += total_rent
            logs.append(f"🏢 COMMERCIAL REAL ESTATE: Deposited +${total_rent:,} in monthly commercial rental income.")

        # 2. Stock dividends
        total_div = sum((s.current_value * (s.dividend_yield_pct / 100.0) / 12.0) for s in self.stocks.values() if s.current_value > 0)
        if total_div >= 1.0:
            div_int = int(total_div)
            player.money += div_int
            self.total_dividends_earned += total_div
            logs.append(f"📊 STOCK DIVIDENDS: Deposited +${div_int:,} in monthly stock index dividend payouts.")

        return logs
