from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class InternationalVisa:
    visa_id: str
    territory: str       # "UK", "JAPAN", "SCHENGEN_EU"
    cost: int
    days_valid: int
    is_active: bool = True
    approved_day: int = 1


class InternationalTouringSystem:
    """Manages international artist visas, ATA Carnet customs bonds, and transoceanic jet lag."""

    VISA_REQUIREMENTS = {
        "London, UK": {"visa_id": "uk_creative", "territory": "UK", "name": "UK Creative Worker Temporary Work Visa", "cost": 600, "validity_days": 90},
        "Tokyo, Japan": {"visa_id": "japan_entertainment", "territory": "JAPAN", "name": "Japanese Ministry Entertainment Artist Visa", "cost": 800, "validity_days": 60},
        "Berlin, Germany": {"visa_id": "schengen_creative", "territory": "SCHENGEN_EU", "name": "Schengen European Union Artist Working Permit", "cost": 450, "validity_days": 90},
    }

    ATA_CARNET_BOND_COST = 1500

    def __init__(self):
        self.active_visas: Dict[str, InternationalVisa] = {}
        self.has_ata_carnet_bond: bool = False
        self.jet_lag_fatigue: int = 0

    def apply_for_artist_visa(self, player, destination_city: str) -> Dict[str, Any]:
        spec = self.VISA_REQUIREMENTS.get(destination_city)
        if not spec:
            return {"ok": False, "explanation": f"No international work visa required for {destination_city}."}

        vid = spec["visa_id"]
        if vid in self.active_visas and self.active_visas[vid].is_active:
            return {"ok": False, "explanation": f"You already hold an active {spec['name']}."}

        cost = spec["cost"]
        if player.money < cost:
            return {"ok": False, "explanation": f"Need ${cost:,} for consular visa application and sponsorship processing."}

        player.money -= cost
        visa = InternationalVisa(
            visa_id=vid,
            territory=spec["territory"],
            cost=cost,
            days_valid=spec["validity_days"],
            is_active=True,
            approved_day=current_game_time.day,
        )
        self.active_visas[vid] = visa
        player.fame = min(1000, player.fame + 10)

        summary = (
            f"🛂 APPROVED: {spec['name']}!\n"
            f"- Territory: {spec['territory']}\n"
            f"- Consular Fee: -${cost:,}\n"
            f"- Valid For: {spec['validity_days']} days\n"
            f"- Legal clearance granted to perform live shows and earn gate receipts in {destination_city}!"
        )
        return {"ok": True, "visa": visa, "explanation": summary}

    def purchase_ata_carnet_customs_bond(self, player) -> Dict[str, Any]:
        if self.has_ata_carnet_bond:
            return {"ok": False, "explanation": "You already hold an active ATA Carnet International Customs Bond."}

        if player.money < self.ATA_CARNET_BOND_COST:
            return {"ok": False, "explanation": f"Need ${self.ATA_CARNET_BOND_COST:,} for ATA Carnet bond deposit."}

        player.money -= self.ATA_CARNET_BOND_COST
        self.has_ata_carnet_bond = True

        summary = (
            f"📋 SECURED ATA CARNET INTERNATIONAL CUSTOMS BOND (-${self.ATA_CARNET_BOND_COST:,})!\n"
            f"- Registered full vintage gear inventory with international customs chambers.\n"
            f"- 100% protection against import tariffs and gear seizure at international border airports!"
        )
        return {"ok": True, "explanation": summary}

    def process_international_flight_arrival(self, player, destination_city: str) -> Dict[str, Any]:
        spec = self.VISA_REQUIREMENTS.get(destination_city)
        if spec:
            vid = spec["visa_id"]
            if vid not in self.active_visas or not self.active_visas[vid].is_active:
                # Fined at border control
                fine = 1500
                player.money = max(0, player.money - fine)
                player.stress = min(100, player.stress + 35)
                return {
                    "ok": False,
                    "border_fine": fine,
                    "explanation": f"⚠️ BORDER CONTROL INCIDENT: Landed in {destination_city} without valid {spec['name']}! Paid ${fine:,} emergency visa penalty and delayed 6 hours.",
                }

        # Apply Jet Lag
        self.jet_lag_fatigue = min(100, self.jet_lag_fatigue + 40)
        player.energy = max(10, player.energy - 35)

        carnet_status = "Customs cleared seamlessly via ATA Carnet." if self.has_ata_carnet_bond else "Customs inspection passed without bond."
        summary = (
            f"🛬 INTERNATIONAL FLIGHT TOUCHDOWN: {destination_city}!\n"
            f"- Jet Lag Fatigue: +40 (Current: {self.jet_lag_fatigue}%)\n"
            f"- Gear Clearance: {carnet_status}"
        )
        return {"ok": True, "explanation": summary}

    def recover_from_jet_lag(self, player, hours_slept: int = 8) -> str:
        relief = hours_slept * 5
        self.jet_lag_fatigue = max(0, self.jet_lag_fatigue - relief)
        return f"Recovered {relief} points of Jet Lag fatigue. (Remaining: {self.jet_lag_fatigue}%)"
