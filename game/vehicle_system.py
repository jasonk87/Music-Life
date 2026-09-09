from dataclasses import dataclass
from typing import Dict, Optional
import random


class PlayerVehicle:
    def __init__(self, model_key: str, name: str, cost: int, speed: float, fuel_capacity: float, km_per_liter: float, reliability: float):
        self.model_key = model_key
        self.name = name
        self.cost = cost
        self.speed = speed
        self.fuel_capacity = fuel_capacity
        self.fuel_current = fuel_capacity
        self.km_per_liter = km_per_liter
        self.reliability = reliability
        self.engine_condition = 100.0

    def drive_distance(self, distance_km: float) -> Dict:
        fuel_needed = distance_km / max(1.0, self.km_per_liter)
        if self.fuel_current < fuel_needed:
            driven_possible = self.fuel_current * self.km_per_liter
            self.fuel_current = 0.0
            return {
                "success": False,
                "out_of_gas": True,
                "distance_driven": driven_possible,
                "message": f"Ran out of gas after driving {driven_possible:.1f} km!",
            }

        self.fuel_current -= fuel_needed

        breakdown_chance = (1.0 - self.reliability) * 0.15 + (100.0 - self.engine_condition) * 0.002
        if random.random() < breakdown_chance:
            self.engine_condition = max(0.0, self.engine_condition - 15.0)
            return {
                "success": False,
                "breakdown": True,
                "distance_driven": distance_km * 0.5,
                "message": f"Engine sputtering! Breakdown on highway. Engine condition: {self.engine_condition:.0f}%.",
            }

        return {"success": True, "out_of_gas": False, "breakdown": False, "distance_driven": distance_km, "message": "Smooth driving."}

    def refuel(self, player, liters: float, price_per_liter: float = 2.0) -> Dict:
        needed = self.fuel_capacity - self.fuel_current
        liters_to_add = min(needed, liters)
        total_cost = int(liters_to_add * price_per_liter)

        if player.money < total_cost:
            return {"ok": False, "explanation": f"Need ${total_cost} to buy {liters_to_add:.1f}L of fuel."}

        player.money -= total_cost
        self.fuel_current += liters_to_add
        return {"ok": True, "explanation": f"Refueled {liters_to_add:.1f}L for ${total_cost}. Fuel tank: {self.fuel_current:.1f}/{self.fuel_capacity:.1f}L."}

    def repair_engine(self, player, cost: int = 150) -> Dict:
        if player.money < cost:
            return {"ok": False, "explanation": f"Need ${cost} for mechanic engine repair."}

        player.money -= cost
        self.engine_condition = 100.0
        return {"ok": True, "explanation": f"Mechanic tuned up your engine back to 100% condition!"}


class VehicleMarket:
    VEHICLES = {
        "sedan_beatup": {"name": "Beat-Up Used Sedan", "cost": 800, "speed": 65.0, "fuel_cap": 45.0, "kml": 12.0, "reliability": 0.65},
        "van_touring": {"name": "Indie Touring Van", "cost": 2500, "speed": 80.0, "fuel_cap": 70.0, "kml": 9.0, "reliability": 0.82},
        "bus_luxury": {"name": "Luxury Tour Bus", "cost": 12000, "speed": 95.0, "fuel_cap": 150.0, "kml": 6.0, "reliability": 0.95},
    }

    @classmethod
    def buy_vehicle(cls, player, vehicle_key: str) -> Dict:
        info = cls.VEHICLES.get(vehicle_key)
        if not info:
            return {"ok": False, "explanation": "Unknown vehicle model."}

        if player.money < info["cost"]:
            return {"ok": False, "explanation": f"Need ${info['cost']} to buy {info['name']}."}

        player.money -= info["cost"]
        veh = PlayerVehicle(
            model_key=vehicle_key,
            name=info["name"],
            cost=info["cost"],
            speed=info["speed"],
            fuel_capacity=info["fuel_cap"],
            km_per_liter=info["kml"],
            reliability=info["reliability"],
        )
        player.vehicle = veh
        return {"ok": True, "explanation": f"Purchased {info['name']} for ${info['cost']}! Keys are yours."}
