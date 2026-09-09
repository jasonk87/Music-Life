from dataclasses import dataclass
from typing import Dict, List, Optional
import random


@dataclass
class MerchItem:
    item_id: str
    name: str
    category: str  # "tshirt", "sticker", "cassette", "vinyl"
    cost_to_produce: int
    suggested_price: int
    unit_count: int
    quality: float = 0.5


class MerchSystem:
    CATALOG = {
        "diy_stickers": {"name": "DIY Band Stickers (Pack of 50)", "category": "sticker", "cost": 25, "unit_count": 50, "default_price": 2},
        "diy_cassettes": {"name": "Demo Cassettes (Batch of 20)", "category": "cassette", "cost": 60, "unit_count": 20, "default_price": 7},
        "screenprint_tshirts": {"name": "Screenprinted T-Shirts (Batch of 15)", "category": "tshirt", "cost": 120, "unit_count": 15, "default_price": 20},
        "limited_vinyl": {"name": "Limited 7\" Vinyl Pressing (Batch of 10)", "category": "vinyl", "cost": 150, "unit_count": 10, "default_price": 25},
    }

    def produce_merch(self, player, item_key: str, price_override: Optional[int] = None) -> Dict:
        definition = self.CATALOG.get(item_key)
        if not definition:
            return {"ok": False, "explanation": "Unknown merch item."}

        cost = definition["cost"]
        if player.money < cost:
            return {"ok": False, "explanation": f"Need ${cost} to produce {definition['name']}."}

        player.money -= cost
        price = price_override if price_override is not None else definition["default_price"]

        if not hasattr(player, "merch_stock"):
            player.merch_stock = []

        existing = next((m for m in player.merch_stock if isinstance(m, MerchItem) and m.item_id == item_key), None)
        if existing:
            existing.unit_count += definition["unit_count"]
            existing.suggested_price = price
        else:
            new_item = MerchItem(
                item_id=item_key,
                name=definition["name"],
                category=definition["category"],
                cost_to_produce=cost,
                suggested_price=price,
                unit_count=definition["unit_count"],
            )
            player.merch_stock.append(new_item)

        player.street_cred = min(100, getattr(player, "street_cred", 50) + 2)
        player.inspiration = min(100, player.inspiration + 3)
        return {
            "ok": True,
            "explanation": f"Produced {definition['name']}. Added {definition['unit_count']} units to merch stock.",
        }

    def resolve_gig_merch_booth(self, player, gig_turnout: int, performance_score: float) -> Dict:
        if not getattr(player, "merch_stock", None):
            return {"units_sold": 0, "total_revenue": 0, "logs": ["No merch in stock to sell."]}

        total_revenue = 0
        total_units_sold = 0
        logs = []

        street_cred = getattr(player, "street_cred", 50)
        buyer_appetite = max(1, int((gig_turnout * 0.3) * (0.8 + (street_cred / 100.0))))

        for item in list(player.merch_stock):
            if not isinstance(item, MerchItem) or item.unit_count <= 0:
                continue

            base_demand_mult = 1.0
            unit_cost = item.cost_to_produce / max(1, item.unit_count)
            if item.suggested_price > unit_cost * 3.5:
                base_demand_mult *= 0.7

            max_possible_sales = min(item.unit_count, max(1, int(buyer_appetite * base_demand_mult * max(0.5, performance_score / 12.0))))
            actual_sales = random.randint(max(0, max_possible_sales - 2), max_possible_sales)
            actual_sales = min(item.unit_count, actual_sales)

            if actual_sales > 0:
                revenue = actual_sales * item.suggested_price
                item.unit_count -= actual_sales
                total_units_sold += actual_sales
                total_revenue += revenue
                logs.append(f"Merch table: sold {actual_sales}x {item.name} for ${revenue}.")

        player.money += total_revenue
        if total_units_sold > 0:
            player.street_cred = min(100, street_cred + min(5, max(1, total_units_sold // 3)))

        return {
            "units_sold": total_units_sold,
            "total_revenue": total_revenue,
            "logs": logs,
        }
