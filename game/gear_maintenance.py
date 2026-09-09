from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class InstrumentMaintenanceStatus:
    needs_setup: bool = False
    condition_pct: float = 100.0   # 0 to 100%
    fret_wear_pct: float = 0.0     # 0 to 100%
    tube_amp_bias_ok: bool = True
    last_service_day: int = 1


class GearMaintenanceSystem:
    """Manages professional luthier setups, tube amp biasing, and parking lot gear theft security."""

    def __init__(self):
        self.maintenance_status = InstrumentMaintenanceStatus()
        self.has_overnight_security: bool = False
        self.stolen_gear_incident_logged: List[str] = []

    def hire_luthier_guitar_setup(self, player, service_type: str = "full_pro_setup") -> Dict[str, Any]:
        """
        Service types:
        - "basic_intonation": $60 (truss rod & string action)
        - "full_pro_setup": $180 (fret leveling, polish, bone nut dressing, intonation)
        - "tube_amp_biasing": $140 (power tube replacement & plate voltage bias calibration)
        """
        costs = {
            "basic_intonation": 60,
            "full_pro_setup": 180,
            "tube_amp_biasing": 140,
        }
        cost = costs.get(service_type, 180)
        if player.money < cost:
            return {"ok": False, "explanation": f"Luthier service costs ${cost}."}

        player.money -= cost
        self.maintenance_status.condition_pct = 100.0
        self.maintenance_status.fret_wear_pct = 0.0
        self.maintenance_status.needs_setup = False
        self.maintenance_status.last_service_day = current_game_time.day

        if service_type == "tube_amp_biasing":
            self.maintenance_status.tube_amp_bias_ok = True
            msg = f"🔧 TUBE AMP BIAS SERVICE COMPLETED (-${cost})! Tube heads re-biased with matched 6L6 power tubes for maximum headroom and zero hum."
        else:
            msg = f"🎸 MASTER LUTHIER GUITAR SETUP COMPLETED (-${cost})! Fret leveling, hand-cut bone nut, and laser intonation calibrated. Tone response optimized to 100%!"

        return {"ok": True, "service": service_type, "explanation": msg}

    def hire_overnight_van_security(self, player) -> Dict[str, Any]:
        cost = 150
        if player.money < cost:
            return {"ok": False, "explanation": f"Private overnight parking lot security costs ${cost}."}

        player.money -= cost
        self.has_overnight_security = True
        return {
            "ok": True,
            "explanation": f"🔒 Hired overnight private venue security guard (-${cost})! Touring van, trailer, and vintage gear secured against break-ins.",
        }

    def check_overnight_parking_theft_risk(self, player) -> Optional[str]:
        """Rolls theft risk when parking overnight in metro areas if security not active."""
        if self.has_overnight_security:
            self.has_overnight_security = False
            return None

        # 8% baseline risk in rough urban tour stops
        risk_roll = random.random()
        if risk_roll < 0.08:
            incident = f"🚨 VAN BREAK-IN REPORT: Padlock cut overnight in motel alley! Pedalboard and cables stolen ($600 replacement cost)."
            player.money = max(0, player.money - 600)
            player.stress = min(100, player.stress + 25)
            self.stolen_gear_incident_logged.append(incident)
            return incident

        return None
