from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class RomanticPartner:
    partner_id: str
    name: str
    city: str
    occupation: str
    personality_trait: str
    affection_level: float = 20.0        # 0.0 to 100.0
    relationship_status: str = "DATING"   # "DATING", "EXCLUSIVE", "COHABITATING", "ENGAGED", "MARRIED"
    shared_home: bool = False
    favorite_activity: str = "dinner_date"
    supportiveness: float = 0.80


@dataclass
class FamilyProfile:
    parents_relationship: float = 75.0   # 0 to 100
    siblings_relationship: float = 70.0
    total_money_sent_home: int = 0
    last_call_day: int = 1
    homesickness_meter: float = 10.0     # 0 to 100


class RelationshipsAndFamilySystem:
    """Manages romance, dating partners across cities, marriage, and family ties/support."""

    POTENTIAL_PARTNERS = {
        "maya_artist_asbury": {
            "name": "Maya Lin",
            "city": "Asbury Park, NJ",
            "occupation": "Muralist & Vintage Store Owner",
            "personality_trait": "Creative, free-spirited, and deeply empathetic.",
            "favorite": "boardwalk_walk",
        },
        "lucas_audio_philly": {
            "name": "Lucas Ward",
            "city": "Philadelphia, PA",
            "occupation": "Indie Game Sound Designer",
            "personality_trait": "Thoughtful, tech-savvy, and vinyl record enthusiast.",
            "favorite": "coffee_chat",
        },
        "elena_botanist_austin": {
            "name": "Elena Morales",
            "city": "Austin, TX",
            "occupation": "Landscape Botanist & Coffee Roaster",
            "personality_trait": "Warm, grounded, and loves outdoor camping.",
            "favorite": "cook_dinner",
        },
        "jordan_novelist_nyc": {
            "name": "Jordan Hayes",
            "city": "New York City, NY",
            "occupation": "Music Journalist & Novelist",
            "personality_trait": "Witty, sharp, and loves late-night diners.",
            "favorite": "diner_talk",
        },
    }

    def __init__(self):
        self.partner: Optional[RomanticPartner] = None
        self.family = FamilyProfile()
        self.dating_history: List[str] = []

    def meet_and_ask_out(self, player, partner_key: str) -> Dict[str, Any]:
        if self.partner:
            return {"ok": False, "explanation": f"You are already in a relationship with {self.partner.name}."}

        p_def = self.POTENTIAL_PARTNERS.get(partner_key)
        if not p_def:
            return {"ok": False, "explanation": "Partner not found."}

        loc_name = getattr(player.current_location, "name", str(player.current_location))
        if p_def["city"] != loc_name:
            return {"ok": False, "explanation": f"You must be in {p_def['city']} to meet up with {p_def['name']}."}

        partner = RomanticPartner(
            partner_id=partner_key,
            name=p_def["name"],
            city=p_def["city"],
            occupation=p_def["occupation"],
            personality_trait=p_def["personality_trait"],
            affection_level=25.0,
            relationship_status="DATING",
        )
        self.partner = partner
        player.stress = max(0, player.stress - 15)

        summary = (
            f"❤️ Started dating {partner.name} ({partner.occupation}) in {partner.city}!\n"
            f"- Personality: {partner.personality_trait}\n"
            f"- Stress reduced by 15 points."
        )
        return {"ok": True, "partner": partner, "explanation": summary}

    def go_on_date(self, player, activity: str = "dinner_date") -> Dict[str, Any]:
        if not self.partner:
            return {"ok": False, "explanation": "You don't currently have a partner."}

        costs = {
            "coffee_chat": 15,
            "boardwalk_walk": 25,
            "cook_dinner": 40,
            "dinner_date": 120,
            "weekend_getaway": 600,
        }
        cost = costs.get(activity, 80)
        if player.money < cost:
            return {"ok": False, "explanation": f"Need ${cost} for this date activity."}

        player.money -= cost
        self.partner.affection_level = min(100.0, self.partner.affection_level + 15.0)
        player.stress = max(0, player.stress - 20)
        player.energy = min(100, player.energy + 10)

        # Check progression
        progression_msg = ""
        if self.partner.affection_level >= 50.0 and self.partner.relationship_status == "DATING":
            self.partner.relationship_status = "EXCLUSIVE"
            progression_msg = f" 💖 You and {self.partner.name} agreed to be mutually exclusive!"
        elif self.partner.affection_level >= 75.0 and self.partner.relationship_status == "EXCLUSIVE":
            self.partner.relationship_status = "COHABITATING"
            self.partner.shared_home = True
            player.comfort = min(100, player.comfort + 10)
            progression_msg = f" 🏡 {self.partner.name} moved in with you! Comfort +10."

        summary = (
            f"🍷 Wonderful date with {self.partner.name}! ({activity.replace('_', ' ').title()})\n"
            f"- Affection: {self.partner.affection_level:.0f}/100\n"
            f"- Stress -20, Energy +10.{progression_msg}"
        )
        return {"ok": True, "affection": self.partner.affection_level, "explanation": summary}

    def propose_marriage(self, player) -> Dict[str, Any]:
        if not self.partner:
            return {"ok": False, "explanation": "No partner to propose to."}

        if self.partner.affection_level < 85.0:
            return {"ok": False, "explanation": f"{self.partner.name} feels the relationship needs more time before marriage (Affection {self.partner.affection_level:.0f}/100, need 85+)."}

        ring_cost = 5000
        if player.money < ring_cost:
            return {"ok": False, "explanation": f"Need ${ring_cost:,} for a diamond engagement ring."}

        player.money -= ring_cost
        self.partner.relationship_status = "MARRIED"
        self.partner.affection_level = 100.0
        player.fame = min(1000, player.fame + 20)
        player.stress = 0

        summary = (
            f"💍 PROPOSAL ACCEPTED! You and {self.partner.name} are officially married!\n"
            f"- Celebrated intimate wedding ceremony with family & friends.\n"
            f"- Stress completely wiped to 0! +20 Fame."
        )
        return {"ok": True, "partner": self.partner, "explanation": summary}

    def call_family_home(self, player) -> Dict[str, Any]:
        player.stress = max(0, player.stress - 15)
        self.family.homesickness_meter = max(0.0, self.family.homesickness_meter - 25.0)
        self.family.parents_relationship = min(100.0, self.family.parents_relationship + 5.0)
        self.family.last_call_day = current_game_time.day

        return {
            "ok": True,
            "explanation": "📞 Heartwarming phone call with your parents and family back home. Eased homesickness and reduced stress by 15.",
        }

    def send_money_to_family(self, player, amount: int = 1000) -> Dict[str, Any]:
        if player.money < amount:
            return {"ok": False, "explanation": f"Insufficient funds to send ${amount:,} home."}

        player.money -= amount
        self.family.total_money_sent_home += amount
        self.family.parents_relationship = min(100.0, self.family.parents_relationship + 15.0)
        player.stress = max(0, player.stress - 10)

        return {
            "ok": True,
            "total_sent": self.family.total_money_sent_home,
            "explanation": f"🎁 Sent ${amount:,} home to support your family! Your parents are deeply proud and grateful (Family Bond: {self.family.parents_relationship:.0f}/100).",
        }
