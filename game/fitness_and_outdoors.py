from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class FitnessProfile:
    physical_conditioning_level: int = 1   # 1 to 10
    stamina_bonus_earned: int = 0
    gym_membership_active: bool = False
    workouts_completed: int = 0
    martial_arts_belt: str = "White Belt"


class FitnessAndOutdoorsSystem:
    """Manages physical conditioning, weightlifting, martial arts, yoga, and outdoor surfing/hiking."""

    def __init__(self):
        self.profile = FitnessProfile()

    def join_gym(self, player) -> Dict[str, Any]:
        if self.profile.gym_membership_active:
            return {"ok": False, "explanation": "You already have an active gym membership."}

        cost = 100
        if player.money < cost:
            return {"ok": False, "explanation": f"Need ${cost} for monthly gym membership."}

        player.money -= cost
        self.profile.gym_membership_active = True
        return {
            "ok": True,
            "explanation": f"🏋️ Joined premium 24/7 fitness club (-${cost}/month)! Unlocked weightlifting, cardio tracks, and sauna access.",
        }

    def workout_at_gym(self, player, workout_type: str = "strength_training") -> Dict[str, Any]:
        """
        Types:
        - "strength_training": -20 Energy, +10 Health, +5 Stamina Cap
        - "yoga_and_breathwork": -10 Energy, -25 Stress, +10 Diaphragm control
        - "jiu_jitsu_sparring": -30 Energy, +15 Street Cred, +10 Mental Toughness
        """
        if not self.profile.gym_membership_active:
            return {"ok": False, "explanation": "You need an active gym membership to train."}

        if player.energy < 30:
            return {"ok": False, "explanation": "Too exhausted for an intensive workout. Rest first."}

        self.profile.workouts_completed += 1

        if workout_type == "strength_training":
            player.energy -= 20
            player.health = min(100, player.health + 10)
            self.profile.stamina_bonus_earned += 2
            msg = f"💪 HEAVY WEIGHTLIFTING SESSION! Completed squats, deadlifts, and bench presses. Health boosted to {player.health}!"

        elif workout_type == "yoga_and_breathwork":
            player.energy -= 10
            player.stress = max(0, player.stress - 25)
            msg = f"🧘 YOGA & PRANAYAMA BREATHWORK! Stretched hamstrings and expanded lung capacity. Stress wiped by 25 points."

        elif workout_type == "jiu_jitsu_sparring":
            player.energy -= 30
            player.street_cred = min(100, player.street_cred + 5)
            player.health = min(100, player.health + 5)
            if self.profile.workouts_completed % 10 == 0:
                self.profile.martial_arts_belt = "Blue Belt"
                msg = f"🥋 BJJ BELT PROMOTION! Earned your Blue Belt in Brazilian Jiu-Jitsu! (+5 Street Cred)."
            else:
                msg = f"🥋 Intensive BJJ grappling rolls! Sharpened mental resilience and agility."
        else:
            return {"ok": False, "explanation": "Unknown workout type."}

        return {"ok": True, "workouts": self.profile.workouts_completed, "explanation": msg}

    def go_outdoor_recreation(self, player, activity: str = "surf_ocean") -> Dict[str, Any]:
        loc_name = getattr(player.current_location, "name", str(player.current_location))

        if activity == "surf_ocean":
            player.energy = max(0, player.energy - 20)
            player.stress = max(0, player.stress - 30)
            player.health = min(100, player.health + 10)
            summary = f"🏄 CATCHING WAVES: Surfed coastal morning swell in {loc_name}! Cleared mental fog and lowered stress by 30!"
        else:
            player.energy = max(0, player.energy - 25)
            player.stress = max(0, player.stress - 30)
            player.health = min(100, player.health + 15)
            summary = f"🌲 MOUNTAIN TRAIL HIKE: Hiked scenic alpine forest trails outside {loc_name}! Inhaled crisp mountain air (+15 Health, -30 Stress)."

        return {"ok": True, "explanation": summary}
