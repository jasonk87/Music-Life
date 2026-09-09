from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class StaffMember:
    name: str
    role: str               # "Roadie", "Personal_Assistant", "Tour_Chef", "Personal_Trainer", "Security_Detail"
    wage_per_week: int
    skill_level: int = 1    # 1 to 10
    satisfaction: int = 100
    perk_description: str = ""

    def __str__(self):
        return f"{self.name} ({self.role}, Lvl {self.skill_level}) - ${self.wage_per_week}/wk"


class StaffManagementSystem:
    """Manages personal staff entourage: Personal Assistant, Tour Chef, Personal Trainer, Security."""

    CANDIDATES = {
        "assistant": StaffMember(
            name="Clara Higgins",
            role="Personal_Assistant",
            wage_per_week=800,
            skill_level=5,
            perk_description="Manages daily schedules, automates hotel check-ins, and reduces player stress by 15.",
        ),
        "tour_chef": StaffMember(
            name="Chef Marco Rossi",
            role="Tour_Chef",
            wage_per_week=1200,
            skill_level=7,
            perk_description="Prepares organic gourmet tour meals. Eliminates hunger and boosts health recovery.",
        ),
        "trainer": StaffMember(
            name="Coach Tyson Brooks",
            role="Personal_Trainer",
            wage_per_week=950,
            skill_level=6,
            perk_description="Daily tour conditioning regimens. Increases player maximum stamina by +10.",
        ),
        "security": StaffMember(
            name="Dmitri 'The Wall' Volkov",
            role="Security_Detail",
            wage_per_week=1400,
            skill_level=8,
            perk_description="Elite close-protection security. 100% protection against paparazzi harassment and crowd mobs.",
        ),
    }

    def __init__(self):
        self.hired_staff: Dict[str, StaffMember] = {}

    def hire_staff_member(self, player, role_key: str) -> Dict[str, Any]:
        candidate = self.CANDIDATES.get(role_key)
        if not candidate:
            return {"ok": False, "explanation": "Staff candidate not found."}

        if role_key in self.hired_staff:
            return {"ok": False, "explanation": f"You already have a {candidate.role.replace('_', ' ')} on your personal staff."}

        if player.money < candidate.wage_per_week:
            return {"ok": False, "explanation": f"Need at least ${candidate.wage_per_week:,} for the first week's salary."}

        player.money -= candidate.wage_per_week
        self.hired_staff[role_key] = candidate
        player.comfort = min(100, player.comfort + 10)
        player.stress = max(0, player.stress - 10)

        summary = (
            f"🤝 HIRED PERSONAL STAFF: {candidate.name} ({candidate.role.replace('_', ' ')})!\n"
            f"- Weekly Salary: ${candidate.wage_per_week:,}/week\n"
            f"- Entourage Benefit: {candidate.perk_description}\n"
            f"- Comfort +10, Stress -10."
        )
        return {"ok": True, "staff": candidate, "explanation": summary}

    def process_weekly_staff_payroll(self, player) -> List[str]:
        logs = []
        total_wages = sum(s.wage_per_week for s in self.hired_staff.values())
        if total_wages <= 0:
            return logs

        if player.money >= total_wages:
            player.money -= total_wages
            logs.append(f"💼 ENTOURAGE PAYROLL: Paid ${total_wages:,} for {len(self.hired_staff)} personal staff members.")
        else:
            logs.append(f"⚠️ PAYROLL DEFICIT: Unable to fully pay personal staff (${total_wages:,} owed).")
        return logs
