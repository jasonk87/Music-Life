from dataclasses import dataclass
from typing import Dict, List, Optional

from game.vehicle_system import VehicleMarket, PlayerVehicle
from game.game_time import current_game_time
from game.rivals import add_news


@dataclass
class RentalVehicle:
    model_key: str
    name: str
    daily_rate: int
    days_rented: int = 0


class TransitHubSystem:
    RENTALS = {
        "sedan_rental": RentalVehicle("sedan_beatup", "Sedan Rental", 30),
        "van_rental": RentalVehicle("van_touring", "Touring Van Rental", 60),
    }

    TAXI_FARE = 15

    def buy_vehicle(self, player, vehicle_key: str) -> Dict:
        has_manager = getattr(player, "has_manager", False)
        discount = 0.80 if has_manager else 1.0

        res = VehicleMarket.buy_vehicle(player, vehicle_key)
        if res["ok"] and has_manager:
            refund = int(player.vehicle.cost * 0.20)
            player.money += refund
            res["explanation"] += f" Manager negotiated a ${refund} discount!"
        return res

    def rent_vehicle(self, player, model_key: str, days: int = 3) -> Dict:
        rental = self.RENTALS.get(model_key)
        if not rental or not isinstance(days, int) or days < 1:
            return {"ok": False, "explanation": "Unknown rental vehicle."}

        has_manager = getattr(player, "has_manager", False)
        total_cost = int(rental.daily_rate * days * (0.80 if has_manager else 1.0))

        if player.money < total_cost:
            return {"ok": False, "explanation": f"Need ${total_cost} to rent {rental.name} for {days} days."}

        player.money -= total_cost
        base_veh = VehicleMarket.VEHICLES.get(rental.model_key, {})
        player.vehicle = PlayerVehicle(
            model_key=rental.model_key,
            name=f"{rental.name} (Rented)",
            cost=0,
            speed=base_veh.get("speed", 75.0),
            fuel_capacity=base_veh.get("fuel_cap", 60.0),
            km_per_liter=base_veh.get("kml", 10.0),
            reliability=base_veh.get("reliability", 0.85),
        )

        player.vehicle.rental_until = current_game_time.day_index() + days

        msg = f"Rented {rental.name} for {days} days (${total_cost})."
        if has_manager:
            msg += " Manager secured a 20% rental discount!"
        return {"ok": True, "explanation": msg}

    def hail_taxi(self, game, target_poi_id: str) -> Dict:
        player = game.player
        if player.money < self.TAXI_FARE:
            return {"ok": False, "explanation": f"Need ${self.TAXI_FARE} fare to hail a city taxi."}

        player.money -= self.TAXI_FARE
        target_poi = game.get_poi_or_venue_by_id(target_poi_id)
        if target_poi:
            player.current_poi = target_poi

        return {"ok": True, "explanation": f"Hailed taxi for ${self.TAXI_FARE}. Arrived directly at {player.current_poi.name}!"}

    def manager_prebook_tour_fleet(self, game) -> Dict:
        player = game.player
        if not getattr(player, "has_manager", False):
            return {"ok": False, "explanation": "You need an active Manager to pre-book tour fleet transport."}

        # Auto-reserve touring van & driver for upcoming gigs
        res = self.rent_vehicle(player, "van_rental", days=5)
        if not res["ok"]:
            return res

        if hasattr(game, "delegation_system"):
            game.delegation_system.add_or_update_role(player, "driver", active=True, competence=0.8, upkeep=120)

        add_news(f"TOUR PRE-BOOKING: {player.name}'s manager pre-booked a Touring Van & Driver for upcoming shows!")
        return {
            "ok": True,
            "explanation": f"Manager pre-booked your Tour Fleet! Rented 5-day Touring Van & assigned a professional driver.",
        }
