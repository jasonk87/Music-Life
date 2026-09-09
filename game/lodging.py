from dataclasses import dataclass
from typing import Dict, Optional

from game.game_time import current_game_time


@dataclass
class LodgingOption:
    name: str
    tier: str  # "rough", "motel", "hotel", "luxury"
    nightly_cost: int
    energy_recovery_pct: float  # 0.50 to 1.20
    stress_relief: float  # -5 to -30
    comfort_bonus: float  # -10 to +30
    health_recovery: float  # 0 to +20


class LodgingSystem:
    OPTIONS = {
        "rough_sleep": LodgingOption("Sleep in Van / Bench", "rough", 0, 0.50, -2.0, -10.0, 0.0),
        "motel_budget": LodgingOption("Sleep EZ Budget Motel", "motel", 40, 0.85, -15.0, 5.0, 5.0),
        "motel_roadside": LodgingOption("Roadside Motel", "motel", 50, 0.90, -18.0, 10.0, 8.0),
        "hotel_luxury": LodgingOption("Four Seasons Luxury Suite", "luxury", 250, 1.20, -35.0, 30.0, 20.0),
    }

    def book_lodging(self, game, lodging_key: str) -> Dict:
        opt = self.OPTIONS.get(lodging_key)
        if not opt:
            return {"ok": False, "explanation": "Invalid lodging selection."}

        player = game.player
        if player.money < opt.nightly_cost:
            return {"ok": False, "explanation": f"Cannot afford ${opt.nightly_cost} for {opt.name}. Cash: ${player.money}."}

        player.money -= opt.nightly_cost

        # Apply rest effects
        recovered_energy = int(100 * opt.energy_recovery_pct)
        player.energy = min(100, player.energy + recovered_energy)
        player.stress = max(0.0, player.stress + opt.stress_relief)
        player.comfort = max(0.0, min(100.0, player.comfort + opt.comfort_bonus))
        player.health = max(0.0, min(100.0, player.health + opt.health_recovery))

        if hasattr(game, "GAME_LOG") and hasattr(game.GAME_LOG, "add_log_message"):
            game.GAME_LOG.add_log_message(
                f"Slept at {opt.name}. Energy: {player.energy}%, Stress: {player.stress:.0f}, Health: {player.health:.0f}%."
            )

        return {
            "ok": True,
            "lodging_name": opt.name,
            "cost": opt.nightly_cost,
            "explanation": f"You spent the night at {opt.name} (${opt.nightly_cost}). Energy recovered to {player.energy}%.",
        }
