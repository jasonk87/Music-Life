from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class PersonalHobby:
    hobby_key: str
    name: str
    skill_level: int = 1         # 1 to 10
    gear_owned: List[str] = field(default_factory=list)
    total_hours_spent: int = 0
    description: str = ""


class HobbiesAndLeisureSystem:
    """Manages personal recreation: espresso crafting, classic car wrenching, gourmet cooking, gaming, and gardening."""

    HOBBY_DEFS = {
        "espresso_craft": {
            "name": "Artisanal Espresso & Coffee Roasting",
            "desc": "Dialing in precision single-origin coffee extractions and latte art.",
            "starter_kit_cost": 850,
            "starter_item": "La Marzocco Home Espresso Machine & Grinder",
        },
        "classic_cars": {
            "name": "Vintage Muscle Car & Motorcycle Restoration",
            "desc": "Rebuilding carburetors, suspension tuning, and garage wrenching on classic rides.",
            "starter_kit_cost": 15000,
            "starter_item": "1967 Ford Mustang Fastback Project Car & Snap-on Tool Chest",
        },
        "gourmet_cooking": {
            "name": "Gourmet Culinary Arts & Baking",
            "desc": "Mastering French, Japanese, and Italian cuisine from scratch.",
            "starter_kit_cost": 600,
            "starter_item": "Handmade Japanese Damascus Chef Knives & Le Creuset Dutch Oven",
        },
        "pc_gaming": {
            "name": "Custom PC Gaming & Retro Consoles",
            "desc": "Building liquid-cooled gaming rigs and playing immersive RPGs on tour downtime.",
            "starter_kit_cost": 2500,
            "starter_item": "High-End Liquid-Cooled RTX Gaming Battle Station",
        },
        "organic_gardening": {
            "name": "Organic Herb & Greenhouse Gardening",
            "desc": "Growing fresh culinary herbs, heirloom tomatoes, and bonsai trees at home.",
            "starter_kit_cost": 400,
            "starter_item": "Raised Cedar Garden Beds & Drip Irrigation System",
        },
    }

    def __init__(self):
        self.hobbies: Dict[str, PersonalHobby] = {}

    def unlock_hobby(self, player, hobby_key: str) -> Dict[str, Any]:
        if hobby_key in self.hobbies:
            return {"ok": False, "explanation": f"You are already practicing {self.hobbies[hobby_key].name}."}

        h_def = self.HOBBY_DEFS.get(hobby_key)
        if not h_def:
            return {"ok": False, "explanation": "Unknown hobby."}

        cost = h_def["starter_kit_cost"]
        if player.money < cost:
            return {"ok": False, "explanation": f"Need ${cost:,} for {h_def['starter_item']} to begin."}

        player.money -= cost
        hobby = PersonalHobby(
            hobby_key=hobby_key,
            name=h_def["name"],
            skill_level=1,
            gear_owned=[h_def["starter_item"]],
            total_hours_spent=0,
            description=h_def["desc"],
        )
        self.hobbies[hobby_key] = hobby
        player.comfort = min(100, player.comfort + 5)
        player.stress = max(0, player.stress - 15)

        summary = (
            f"☕ UNLOCKED PERSONAL HOBBY: {hobby.name}!\n"
            f"- Acquired: {h_def['starter_item']} (-${cost:,})\n"
            f"- Stress reduced by 15. Home comfort increased by 5!"
        )
        return {"ok": True, "hobby": hobby, "explanation": summary}

    def practice_hobby(self, player, hobby_key: str, hours: int = 2) -> Dict[str, Any]:
        hobby = self.hobbies.get(hobby_key)
        if not hobby:
            return {"ok": False, "explanation": "You haven't unlocked this hobby yet."}

        hobby.total_hours_spent += hours
        player.stress = max(0, player.stress - (hours * 10))
        player.energy = max(0, player.energy - (hours * 5))

        # Skill leveling
        leveled_up = False
        if hobby.total_hours_spent >= hobby.skill_level * 10 and hobby.skill_level < 10:
            hobby.skill_level += 1
            leveled_up = True
            player.comfort = min(100, player.comfort + 2)

        level_msg = f" 🌟 LEVELED UP! {hobby.name} skill is now Level {hobby.skill_level}/10!" if leveled_up else ""

        summary = (
            f"🛠️ Spent {hours} hours on {hobby.name}.\n"
            f"- Stress reduced by {hours * 10}!{level_msg}"
        )
        return {"ok": True, "skill_level": hobby.skill_level, "explanation": summary}
