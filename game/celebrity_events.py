from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class CelebrityGalaEvent:
    event_id: str
    name: str
    min_fame_required: int
    ticket_or_wardrobe_cost: int
    fame_reward: int
    cred_reward: int
    stress_relief: int
    description: str
    red_carpet_lore: str


class CelebrityEventSystem:
    """Manages high-profile celebrity galas, award ceremonies, and red carpet invitations."""

    EVENTS = {
        "grammy_gala": CelebrityGalaEvent(
            event_id="grammy_gala",
            name="The International Golden Mic Music Awards",
            min_fame_required=200,
            ticket_or_wardrobe_cost=3000,
            fame_reward=80,
            cred_reward=30,
            stress_relief=15,
            description="The most prestigious black-tie music awards gala in the global industry.",
            red_carpet_lore="Paparazzi flashbulbs blinding the step-and-repeat as you give interviews to global music press.",
        ),
        "met_gala": CelebrityGalaEvent(
            event_id="met_gala",
            name="The Metropolitan Museum Costume Institute Gala",
            min_fame_required=500,
            ticket_or_wardrobe_cost=25000,
            fame_reward=180,
            cred_reward=40,
            stress_relief=20,
            description="The apex of global fashion, celebrity culture, and artistic prestige in NYC.",
            red_carpet_lore="Ascending the grand museum carpet in a bespoke custom couture ensemble tailored by Paris designers.",
        ),
        "super_bowl_afterparty": CelebrityGalaEvent(
            event_id="super_bowl_afterparty",
            name="Championship Super Bowl VIP Penthouse Party",
            min_fame_required=350,
            ticket_or_wardrobe_cost=5000,
            fame_reward=100,
            cred_reward=20,
            stress_relief=30,
            description="Ultra-exclusive billionaire & A-list athlete penthouse party with DJ sets till sunrise.",
            red_carpet_lore="Sipping vintage champagne with hall-of-fame athletes and Hollywood directors.",
        ),
        "humanitarian_charity_gala": CelebrityGalaEvent(
            event_id="humanitarian_charity_gala",
            name="Global Rainforest & Youth Arts Benefit Gala",
            min_fame_required=150,
            ticket_or_wardrobe_cost=2000,
            fame_reward=45,
            cred_reward=50,
            stress_relief=25,
            description="High-society philanthropic benefit auction and acoustic performance evening.",
            red_carpet_lore="Commended on stage by international ambassadors for your philanthropic commitment.",
        ),
    }

    @classmethod
    def check_for_invitation(cls, player) -> Optional[CelebrityGalaEvent]:
        eligible = [e for e in cls.EVENTS.values() if player.fame >= e.min_fame_required]
        if not eligible:
            return None
        return random.choice(eligible)

    @classmethod
    def attend_gala(cls, player, event_key: str) -> Dict[str, Any]:
        evt = cls.EVENTS.get(event_key)
        if not evt:
            return {"ok": False, "explanation": "Gala event not found."}

        if player.fame < evt.min_fame_required:
            return {"ok": False, "explanation": f"Need at least {evt.min_fame_required} Fame to receive an invite to {evt.name}."}

        if player.money < evt.ticket_or_wardrobe_cost:
            return {"ok": False, "explanation": f"Need ${evt.ticket_or_wardrobe_cost:,} for bespoke red carpet couture and VIP table seat."}

        player.money -= evt.ticket_or_wardrobe_cost
        player.fame = min(1000, player.fame + evt.fame_reward)
        player.street_cred = min(100, player.street_cred + evt.cred_reward)
        player.stress = max(0, player.stress - evt.stress_relief)

        summary = (
            f"✨ ATTENDED VIP CELEBRITY EVENT: {evt.name}!\n"
            f"- Wardrobe & Entry Cost: -${evt.ticket_or_wardrobe_cost:,}\n"
            f"- Red Carpet Atmosphere: {evt.red_carpet_lore}\n"
            f"- Public Acclaim: +{evt.fame_reward} Fame, +{evt.cred_reward} Street Cred, -{evt.stress_relief} Stress"
        )
        return {"ok": True, "event": evt, "explanation": summary}


# Backward-compatible function helper
def check_for_celebrity_event(player):
    evt = CelebrityEventSystem.check_for_invitation(player)
    if evt:
        return {
            "name": evt.name,
            "req": evt.min_fame_required,
            "desc": evt.description,
            "fame_gain": evt.fame_reward,
        }
    return None
