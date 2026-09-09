from dataclasses import dataclass
from typing import Dict, List, Optional
from game.gear import GearItem


@dataclass
class MealType:
    name: str
    cost: int
    hunger_reduction: float
    energy_boost: float
    health_effect: float
    stress_relief: float


class FoodSystem:
    MEALS = {
        "bodega_snack": MealType("Bodega Junk Food", 5, 20.0, 5.0, -2.0, -2.0),
        "greasy_diner": MealType("Greasy Spoon Breakfast", 14, 45.0, 20.0, 0.0, -8.0),
        "diner_square": MealType("Square Diner Meal", 22, 70.0, 35.0, 5.0, -12.0),
        "wellness_bowl": MealType("Organic Wellness Bowl", 32, 60.0, 25.0, 20.0, -18.0),
    }

    PORTABLE_ITEMS = {
        "energy_bar": {"name": "Energy Bar", "cost": 4, "hunger": 15, "energy": 10},
        "canned_soup": {"name": "Canned Soup", "cost": 6, "hunger": 30, "energy": 5},
        "trail_mix": {"name": "Trail Mix", "cost": 8, "hunger": 25, "energy": 15},
    }

    def buy_and_eat_meal(self, player, meal_key: str) -> Dict:
        meal = self.MEALS.get(meal_key)
        if not meal:
            return {"ok": False, "explanation": "Unknown meal selection."}

        if player.money < meal.cost:
            return {"ok": False, "explanation": f"Need ${meal.cost} to buy {meal.name}."}

        player.money -= meal.cost
        player.hunger = max(0.0, player.hunger - meal.hunger_reduction)
        player.energy = min(100.0, player.energy + meal.energy_boost)
        player.health = max(0.0, min(100.0, player.health + meal.health_effect))
        player.stress = max(0.0, player.stress + meal.stress_relief)

        return {
            "ok": True,
            "meal_name": meal.name,
            "explanation": f"Ate {meal.name} (${meal.cost}). Hunger reduced to {player.hunger:.0f}%, Energy: {player.energy:.0f}%.",
        }

    def buy_portable_food(self, player, item_key: str) -> Dict:
        info = self.PORTABLE_ITEMS.get(item_key)
        if not info:
            return {"ok": False, "explanation": "Unknown food item."}

        if player.money < info["cost"]:
            return {"ok": False, "explanation": f"Need ${info['cost']} to buy {info['name']}."}

        player.money -= info["cost"]
        gear = GearItem(
            item_id=f"food_{item_key}",
            name=info["name"],
            description=f"Portable food: reduces hunger by {info['hunger']}.",
            gear_type="FOOD",
            size=1,
            cost=info["cost"],
            hunger_reduction=info["hunger"],
            energy_boost=info["energy"],
        )
        player.gear_inventory.append(gear)
        return {"ok": True, "explanation": f"Bought {info['name']} and packed it in your bag."}

    def eat_from_inventory(self, player, item_index: int) -> Dict:
        if item_index < 0 or item_index >= len(player.gear_inventory):
            return {"ok": False, "explanation": "Item not in bag."}

        item = player.gear_inventory[item_index]
        if item.gear_type != "FOOD":
            return {"ok": False, "explanation": "Item is not edible food."}

        player.hunger = max(0.0, player.hunger - item.hunger_reduction)
        player.energy = min(100.0, player.energy + item.energy_boost)
        player.gear_inventory.pop(item_index)

        return {"ok": True, "explanation": f"Ate {item.name} from your bag! Hunger: {player.hunger:.0f}%."}
