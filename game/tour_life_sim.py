from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class BandmateContract:
    member_name: str
    role: str
    publishing_split_pct: float  # e.g. 50.0 = 50%
    weekly_wage: int
    burnout: float = 0.0          # 0 - 100
    satisfaction: float = 80.0    # 0 - 100
    ego: float = 50.0             # 0 - 100


class TourLifeSimulation:
    """Simulates realistic highway tour hazards, roadside encounters, and bandmate publishing/morale dynamics."""

    HIGHWAY_HAZARDS = [
        {
            "id": "speed_trap",
            "name": "State Trooper Speed Trap",
            "desc": "Flashing red and blue lights behind you. The officer clocks the touring van doing 15mph over.",
            "cost": 180,
            "delay_hours": 1,
            "stress": 15,
            "driver_avoids": True,
        },
        {
            "id": "weigh_station",
            "name": "Mandatory Commercial Weigh Station",
            "desc": "State DOT pulls the gear trailer into an inspection bay for a 2-hour tire and axle check.",
            "cost": 0,
            "delay_hours": 2,
            "stress": 10,
            "driver_avoids": False,
        },
        {
            "id": "overheating_engine",
            "name": "Radiator Overheating on Mountain Pass",
            "desc": "Steam billows from under the hood. You pull over at a scenic overlook to let the radiator cool.",
            "cost": 65,
            "delay_hours": 2,
            "stress": 20,
            "driver_avoids": False,
        },
        {
            "id": "blizzard_delay",
            "name": "Sudden Highway Blizzard & Whiteout",
            "desc": "Heavy snow covers the interstate. You creep along at 25mph, barely making soundcheck.",
            "cost": 0,
            "delay_hours": 3,
            "stress": 25,
            "driver_avoids": False,
        },
        {
            "id": "roadside_diner_jam",
            "name": "Late-Night Highway Diner Encounter",
            "desc": "You stop at a 24-hour chrome diner. A friendly trucker buys the band coffee and shares folklore.",
            "cost": -20,  # Cash saved / tipped
            "delay_hours": 1,
            "stress": -15,
            "driver_avoids": False,
        },
    ]

    BANDMATE_DISPUTES = [
        {
            "id": "publishing_split",
            "name": "Songwriting Publishing Split Clash",
            "trigger_field": "publishing_split_pct",
            "desc": "demands a higher songwriting royalty split, arguing their basslines/drums make the hooks.",
            "options": [
                {"choice": "compromise", "label": "Offer +10% Publishing Split", "satisfaction_change": 25, "band_morale_change": 10},
                {"choice": "refuse", "label": "Refuse: Leader Writes the Songs", "satisfaction_change": -30, "band_morale_change": -15},
                {"choice": "bonus", "label": "Pay $250 Cash Studio Bonus", "satisfaction_change": 15, "band_morale_change": 5, "cost": 250},
            ],
        },
        {
            "id": "tour_burnout",
            "name": "Severe Tour Exhaustion & Homesickness",
            "trigger_field": "burnout",
            "desc": "is completely exhausted from back-to-back night drives and threatens to skip soundcheck.",
            "options": [
                {"choice": "hotel", "label": "Book Individual Motel Rooms ($150)", "satisfaction_change": 30, "burnout_change": -40, "cost": 150},
                {"choice": "peptalk", "label": "Give Encouraging Band Pep Talk", "satisfaction_change": 10, "burnout_change": -10},
                {"choice": "push", "label": "Tell them to suck it up and play", "satisfaction_change": -25, "burnout_change": 15},
            ],
        },
    ]

    def __init__(self):
        self.contracts: Dict[str, BandmateContract] = {}

    def register_bandmate(self, name: str, role: str = "Bassist", split_pct: float = 25.0, weekly_wage: int = 150) -> BandmateContract:
        contract = BandmateContract(
            member_name=name,
            role=role,
            publishing_split_pct=split_pct,
            weekly_wage=weekly_wage,
        )
        self.contracts[name] = contract
        return contract

    def roll_highway_encounter(self, player, has_driver: bool = False) -> Optional[Dict[str, Any]]:
        # 30% chance of an authentic road encounter per long travel leg
        if random.random() > 0.35:
            return None

        hazard = random.choice(self.HIGHWAY_HAZARDS)
        if hazard["driver_avoids"] and has_driver:
            return {
                "hazard_id": hazard["id"],
                "name": hazard["name"],
                "avoided": True,
                "explanation": f"Your hired Professional Driver spotted the {hazard['name']} ahead and took a smart bypass, saving time and money!",
            }

        # Apply costs and stress
        if hazard["cost"] > 0 and player.money >= hazard["cost"]:
            player.money -= hazard["cost"]
        player.stress = max(0, min(100, player.stress + hazard["stress"]))

        return {
            "hazard_id": hazard["id"],
            "name": hazard["name"],
            "avoided": False,
            "delay_hours": hazard["delay_hours"],
            "cost": hazard["cost"],
            "stress_change": hazard["stress"],
            "explanation": f"⚠️ Highway Event: {hazard['name']} — {hazard['desc']} (Delay: {hazard['delay_hours']}h, Cost: ${hazard['cost']}, Stress: +{hazard['stress']})",
        }

    def check_bandmate_dynamics(self, player) -> Optional[Dict[str, Any]]:
        if not self.contracts:
            return None

        # Pick a random bandmate to evaluate
        member_name = random.choice(list(self.contracts.keys()))
        member = self.contracts[member_name]

        # Natural burnout increase over time
        member.burnout = min(100.0, member.burnout + random.uniform(5.0, 15.0))

        if member.burnout >= 60.0:
            dispute = self.BANDMATE_DISPUTES[1]  # tour_burnout
            return {
                "member_name": member.member_name,
                "dispute_id": dispute["id"],
                "dispute_name": dispute["name"],
                "desc": f"{member.member_name} ({member.role}) {dispute['desc']}",
                "options": dispute["options"],
            }
        elif member.satisfaction <= 40.0 or random.random() < 0.20:
            dispute = self.BANDMATE_DISPUTES[0]  # publishing_split
            return {
                "member_name": member.member_name,
                "dispute_id": dispute["id"],
                "dispute_name": dispute["name"],
                "desc": f"{member.member_name} ({member.role}) {dispute['desc']}",
                "options": dispute["options"],
            }

        return None

    def resolve_dispute_choice(self, player, member_name: str, dispute_id: str, choice_key: str) -> Dict[str, Any]:
        member = self.contracts.get(member_name)
        if not member:
            return {"ok": False, "explanation": f"Bandmate '{member_name}' not found."}

        dispute = next((d for d in self.BANDMATE_DISPUTES if d["id"] == dispute_id), None)
        if not dispute:
            return {"ok": False, "explanation": "Unknown dispute ID."}

        opt = next((o for o in dispute["options"] if o["choice"] == choice_key), None)
        if not opt:
            return {"ok": False, "explanation": "Unknown resolution option."}

        cost = opt.get("cost", 0)
        if cost > 0:
            if player.money < cost:
                return {"ok": False, "explanation": f"Need ${cost} to choose this resolution."}
            player.money -= cost

        member.satisfaction = max(0.0, min(100.0, member.satisfaction + opt.get("satisfaction_change", 0)))
        if "burnout_change" in opt:
            member.burnout = max(0.0, min(100.0, member.burnout + opt["burnout_change"]))

        if choice_key == "compromise":
            member.publishing_split_pct = min(50.0, member.publishing_split_pct + 10.0)

        return {
            "ok": True,
            "member_name": member.member_name,
            "satisfaction": member.satisfaction,
            "burnout": member.burnout,
            "explanation": f"Resolved conflict with {member.member_name}. Satisfaction is now {member.satisfaction:.0f}%, Burnout: {member.burnout:.0f}%.",
        }
