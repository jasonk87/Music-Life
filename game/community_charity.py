from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class CharitableInitiative:
    cause_key: str
    title: str
    target_community: str
    cost: int
    cred_boost: int
    fame_boost: int
    lore_impact: str


class CommunityCharitySystem:
    """Manages community philanthropy, youth music scholarships, and homeless shelter benefit drives."""

    CHARITY_INITIATIVES = {
        "youth_instrument_fund": CharitableInitiative(
            cause_key="youth_instrument_fund",
            title="Inner-City Public School Music & Instrument Grant",
            target_community="Underfunded Public Schools",
            cost=5000,
            cred_boost=20,
            fame_boost=15,
            lore_impact="Purchased 30 electric guitars, drum kits, and horns for youth music education programs.",
        ),
        "shelter_food_drive": CharitableInitiative(
            cause_key="shelter_food_drive",
            title="Community Center Winter Food & Warmth Drive",
            target_community="Local Homeless & Community Shelters",
            cost=2500,
            cred_boost=15,
            fame_boost=10,
            lore_impact="Provided 500 hot nutritious meals, winter coats, and blankets to families in need.",
        ),
        "animal_rescue_sponsor": CharitableInitiative(
            cause_key="animal_rescue_sponsor",
            title="No-Kill Animal Rescue Medical Sponsorship",
            target_community="City Animal Shelters",
            cost=1800,
            cred_boost=12,
            fame_boost=10,
            lore_impact="Covered emergency surgical care and adoption sponsorships for 25 shelter dogs and cats.",
        ),
    }

    def __init__(self):
        self.completed_donations: List[Dict[str, Any]] = []
        self.total_donated: int = 0

    def donate_to_initiative(self, player, cause_key: str) -> Dict[str, Any]:
        init = self.CHARITY_INITIATIVES.get(cause_key)
        if not init:
            return {"ok": False, "explanation": "Charitable initiative not found."}

        if player.money < init.cost:
            return {"ok": False, "explanation": f"Need ${init.cost:,} to sponsor {init.title}."}

        player.money -= init.cost
        self.total_donated += init.cost
        player.street_cred = min(100, player.street_cred + init.cred_boost)
        player.fame = min(1000, player.fame + init.fame_boost)
        player.stress = max(0, player.stress - 20)

        record = {
            "title": init.title,
            "amount": init.cost,
            "day": current_game_time.day,
        }
        self.completed_donations.append(record)

        summary = (
            f"🤝 SPONSORED PHILANTHROPIC INITIATIVE: {init.title}!\n"
            f"- Donation Amount: -${init.cost:,}\n"
            f"- Community Impact: {init.lore_impact}\n"
            f"- Public Respect: +{init.cred_boost} Street Cred, +{init.fame_boost} Fame, -20 Stress"
        )
        return {"ok": True, "donation": record, "explanation": summary}
