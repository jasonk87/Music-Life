from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class StageProductionRig:
    rig_id: str
    name: str
    tier_type: str         # "CLUB", "THEATER", "ARENA_SPECTACLE"
    purchase_cost: int
    hype_multiplier: float
    ticket_price_premium: int
    lighting_elements: str
    pyro_elements: str


class StageProductionSystem:
    """Manages custom concert stage lighting rigs, visual scenography, and pyrotechnics."""

    RIG_CATALOG = {
        "diy_club_rig": StageProductionRig(
            rig_id="diy_club_rig",
            name="Vintage Club Haze & Par-Can Rig",
            tier_type="CLUB",
            purchase_cost=1500,
            hype_multiplier=1.10,
            ticket_price_premium=5,
            lighting_elements="Warm vintage amber incandescent par cans, oil haze machine.",
            pyro_elements="None (Intimate aesthetic).",
        ),
        "theatrical_tour_rig": StageProductionRig(
            rig_id="theatrical_tour_rig",
            name="Theatrical Laser & Marshall Stack Rig",
            tier_type="THEATER",
            purchase_cost=18000,
            hype_multiplier=1.25,
            ticket_price_premium=15,
            lighting_elements="Synchronized laser prisms, 8x Marshall dummy stack backdrop, modular strobe bars.",
            pyro_elements="Low-lying dry ice fog blanket.",
        ),
        "arena_spectacle_rig": StageProductionRig(
            rig_id="arena_spectacle_rig",
            name="Arena 4K LED & Cryo-Pyro Spectacle Rig",
            tier_type="ARENA_SPECTACLE",
            purchase_cost=95000,
            hype_multiplier=1.40,
            ticket_price_premium=35,
            lighting_elements="Full curved 4K LED video wall, moving robotic spot beam arrays, laser sky ceiling.",
            pyro_elements="Dual CO2 cryo jets, flame projector cannons, pneumatic drum riser.",
        ),
    }

    def __init__(self):
        self.active_rig: StageProductionRig = self.RIG_CATALOG["diy_club_rig"]
        self.owned_rig_ids: List[str] = ["diy_club_rig"]

    def purchase_and_equip_rig(self, player, rig_key: str) -> Dict[str, Any]:
        rig = self.RIG_CATALOG.get(rig_key)
        if not rig:
            return {"ok": False, "explanation": "Stage production rig not found."}

        if rig_key in self.owned_rig_ids:
            self.active_rig = rig
            return {"ok": True, "rig": rig, "explanation": f"💡 Equipped {rig.name} as your active touring stage production!"}

        if player.money < rig.purchase_cost:
            return {"ok": False, "explanation": f"Need ${rig.purchase_cost:,} to purchase {rig.name}."}

        player.money -= rig.purchase_cost
        self.owned_rig_ids.append(rig_key)
        self.active_rig = rig
        player.fame = min(1000, player.fame + 25)
        player.street_cred = min(100, player.street_cred + 15)

        summary = (
            f"🎆 ACQUIRED STAGE PRODUCTION RIG: {rig.name}!\n"
            f"- Lighting & Visuals: {rig.lighting_elements}\n"
            f"- FX & Pyro: {rig.pyro_elements}\n"
            f"- Concert Hype Boost: +{int((rig.hype_multiplier - 1.0)*100)}%\n"
            f"- Ticket Price Premium: +${rig.ticket_price_premium} per ticket sold!"
        )
        return {"ok": True, "rig": rig, "explanation": summary}
