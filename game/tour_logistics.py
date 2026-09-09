from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class SleeperTourBus:
    bus_id: str
    model_name: str
    bunk_count: int = 12
    has_onboard_lounge: bool = True
    has_wifi_and_kitchen: bool = True
    weekly_lease_cost: int = 3000
    purchase_cost: int = 120000
    is_leased: bool = False
    is_owned: bool = False
    comfort_rating: int = 80


@dataclass
class TouringCrewMember:
    crew_id: str
    role_type: str         # "FOH_SOUND", "LIGHTING_LD", "GUITAR_TECH", "TOUR_MANAGER"
    name: str
    weekly_salary: int
    audio_boost: float = 0.0
    hype_boost: float = 0.0
    zero_gear_mishaps: bool = False
    route_efficiency: float = 0.0


class TourLogisticsSystem:
    """Manages 12-bunk luxury Sleeper Tour Buses, International Carnets, and professional Touring Crew."""

    CREW_ROSTER_DEFS = {
        "foh_engineer": {
            "role": "FOH_SOUND",
            "name": "Alex Vance (FOH Sound Engineer)",
            "salary": 1200,
            "audio_boost": 0.20,
            "desc": "Dialing in crystal-clear live mix, booming sub-bass, and zero vocal feedback.",
        },
        "lighting_tech": {
            "role": "LIGHTING_LD",
            "name": "Sarah Chen (Lighting Designer LD)",
            "salary": 1000,
            "hype_boost": 0.15,
            "desc": "Synchronized strobes, laser sweeps, and atmospheric stage wash.",
        },
        "guitar_tech": {
            "role": "GUITAR_TECH",
            "name": "Hank 'Spanner' Miller (Guitar Tech)",
            "salary": 900,
            "zero_gear_mishaps": True,
            "desc": "Instant guitar swaps, tuning checks, and spare tube heads ready backstage.",
        },
        "tour_manager": {
            "role": "TOUR_MANAGER",
            "name": "Marcus Kane (Tour Manager)",
            "salary": 1500,
            "route_efficiency": 0.25,
            "desc": "Automates hotel check-ins, runner drivers, venue settlements, and backstage hospitality.",
        },
    }

    def __init__(self):
        self.tour_bus: Optional[SleeperTourBus] = None
        self.hired_crew: Dict[str, TouringCrewMember] = {}
        self.international_carnet_active: bool = False

    def lease_tour_bus(self, player) -> Dict[str, Any]:
        if self.tour_bus and (self.tour_bus.is_leased or self.tour_bus.is_owned):
            return {"ok": False, "explanation": f"You already have a {self.tour_bus.model_name} in service."}

        cost = 3000
        if player.money < cost:
            return {"ok": False, "explanation": f"Need ${cost:,} first week lease for Sleeper Tour Bus."}

        player.money -= cost
        bus = SleeperTourBus(
            bus_id="luxury_eagle_bus",
            model_name="Eagle 12-Bunk Luxury Sleeper Coach",
            bunk_count=12,
            is_leased=True,
            comfort_rating=80,
        )
        self.tour_bus = bus
        player.comfort = 80

        summary = (
            f"🚐 LEASED 12-BUNK LUXURY SLEEPER TOUR BUS (${cost}/week)!\n"
            f"- Onboard Amenities: 12 Memory-Foam Bunks, Back Lounge, Kitchenette, High-Speed Starlink Wifi.\n"
            f"- Benefit: Eliminates nightly hotel bills across all tour cities! Comfort level set to 80."
        )
        return {"ok": True, "bus": bus, "explanation": summary}

    def buy_tour_bus(self, player) -> Dict[str, Any]:
        cost = 120000
        if player.money < cost:
            return {"ok": False, "explanation": f"Need ${cost:,} to purchase a Sleeper Tour Bus in full."}

        player.money -= cost
        bus = SleeperTourBus(
            bus_id="luxury_eagle_bus_owned",
            model_name="Custom Prevost 12-Bunk Tour Bus (Owned)",
            bunk_count=12,
            is_owned=True,
            comfort_rating=85,
        )
        self.tour_bus = bus
        player.comfort = 85
        player.fame = min(1000, player.fame + 25)

        summary = (
            f"🚐 PURCHASED CUSTOM TOUR BUS (${cost:,})!\n"
            f"- Ownership: Fully owned with zero weekly lease fees.\n"
            f"- Eliminates nightly hotel costs permanently while touring!"
        )
        return {"ok": True, "bus": bus, "explanation": summary}

    def hire_crew_member(self, player, role_key: str) -> Dict[str, Any]:
        c_def = self.CREW_ROSTER_DEFS.get(role_key)
        if not c_def:
            return {"ok": False, "explanation": "Unknown crew role."}

        if role_key in self.hired_crew:
            return {"ok": False, "explanation": f"You already have {self.hired_crew[role_key].name} on payroll."}

        salary = c_def["salary"]
        if player.money < salary:
            return {"ok": False, "explanation": f"Need ${salary:,} first week wage to hire {c_def['name']}."}

        player.money -= salary
        member = TouringCrewMember(
            crew_id=role_key,
            role_type=c_def["role"],
            name=c_def["name"],
            weekly_salary=salary,
            audio_boost=c_def.get("audio_boost", 0.0),
            hype_boost=c_def.get("hype_boost", 0.0),
            zero_gear_mishaps=c_def.get("zero_gear_mishaps", False),
            route_efficiency=c_def.get("route_efficiency", 0.0),
        )
        self.hired_crew[role_key] = member

        summary = (
            f"🛠️ HIRED TOURING CREW: {member.name} (${salary}/week)!\n"
            f"- Role Description: {c_def['desc']}"
        )
        return {"ok": True, "member": member, "explanation": summary}

    def process_weekly_crew_and_bus_payroll(self, player) -> List[str]:
        logs = []
        total_payroll = 0

        # Bus lease
        if self.tour_bus and self.tour_bus.is_leased:
            total_payroll += self.tour_bus.weekly_lease_cost

        # Crew payroll
        for member in self.hired_crew.values():
            total_payroll += member.weekly_salary

        if total_payroll > 0:
            if player.money >= total_payroll:
                player.money -= total_payroll
                logs.append(f"Paid -${total_payroll:,} weekly tour bus lease & crew payroll ({len(self.hired_crew)} crew members).")
            else:
                paid = player.money
                player.money = 0
                logs.append(f"⚠️ Insufficient funds for tour payroll! Paid -${paid:,}. Crew morale strained.")

        return logs
