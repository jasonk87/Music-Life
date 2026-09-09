from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class BusinessManagerCPA:
    name: str
    city: str
    agency_firm: str
    annual_retainer: int
    tax_deduction_efficiency: float   # e.g. 0.60 = reduces tax bill by 60%
    audit_protection: bool = True


@dataclass
class CopyrightLawsuit:
    lawsuit_id: str
    plaintiff_name: str
    plaintiff_song: str
    accused_song_id: str
    accused_song_title: str
    damages_claimed: int
    settlement_offer: int
    is_active: bool = True
    is_resolved: bool = False
    verdict: Optional[str] = None


class FinanceAndLegalSystem:
    """Manages IRS/HMRC tax assessments, Entertainment CPAs, and copyright plagiarism lawsuits."""

    def __init__(self):
        self.hired_cpa: Optional[BusinessManagerCPA] = None
        self.pending_lawsuits: List[CopyrightLawsuit] = []
        self.total_taxes_paid: int = 0
        self.last_tax_year: int = 2023

    def hire_entertainment_cpa(self, player, firm_key: str = "philly_liberty_cpa") -> Dict[str, Any]:
        firms = {
            "philly_liberty_cpa": {
                "name": "David Miller, CPA",
                "city": "Philadelphia, PA",
                "firm": "Liberty Financial & Tax Management",
                "retainer": 5000,
                "efficiency": 0.50,
            },
            "nyc_manhattan_cpa": {
                "name": "Goldstein & Partners Entertainment CPA",
                "city": "New York City, NY",
                "firm": "Manhattan Music Accounting LLP",
                "retainer": 12000,
                "efficiency": 0.65,
            },
            "beverly_hills_cpa": {
                "name": "Sterling Business Management",
                "city": "Los Angeles, CA",
                "firm": "Beverly Hills Entertainment Management",
                "retainer": 15000,
                "efficiency": 0.75,
            },
        }
        chosen = firms.get(firm_key, firms["philly_liberty_cpa"])
        if player.money < chosen["retainer"]:
            return {"ok": False, "explanation": f"Need ${chosen['retainer']:,} annual retainer to hire {chosen['firm']}."}

        player.money -= chosen["retainer"]
        cpa = BusinessManagerCPA(
            name=chosen["name"],
            city=chosen["city"],
            agency_firm=chosen["firm"],
            annual_retainer=chosen["retainer"],
            tax_deduction_efficiency=chosen["efficiency"],
        )
        self.hired_cpa = cpa

        summary = (
            f"💼 HIRED ENTERTAINMENT CPA: {cpa.name} ({cpa.agency_firm}) in {cpa.city}!\n"
            f"- Tax Write-Off Efficiency: {int(cpa.tax_deduction_efficiency * 100)}% tax liability reduction\n"
            f"- Retainer Paid: -${cpa.annual_retainer:,}\n"
            f"- Full IRS audit protection and tour expense deductions enabled."
        )
        return {"ok": True, "cpa": cpa, "explanation": summary}

    def calculate_and_pay_annual_taxes(self, player, gross_annual_earnings: int) -> Dict[str, Any]:
        # Standard progressive bracket ~25%
        raw_tax = int(gross_annual_earnings * 0.25)
        deductions_applied = 0
        final_tax = raw_tax

        if self.hired_cpa:
            deductions_applied = int(raw_tax * self.hired_cpa.tax_deduction_efficiency)
            final_tax = raw_tax - deductions_applied

        if player.money < final_tax:
            final_tax = player.money

        player.money -= final_tax
        self.total_taxes_paid += final_tax
        self.last_tax_year = current_game_time.year

        cpa_note = f" (CPA {self.hired_cpa.name} wrote off ${deductions_applied:,} in tour expenses & gear depreciation!)" if self.hired_cpa else " (No CPA hired - full liability paid)"

        summary = (
            f"🏛️ TAX SEASON (April 15): Paid ${final_tax:,} in annual income taxes on ${gross_annual_earnings:,} gross earnings.\n"
            f"- Deductions:{cpa_note}"
        )
        return {"ok": True, "taxes_paid": final_tax, "deductions": deductions_applied, "explanation": summary}

    def trigger_sample_copyright_lawsuit(self, song_id: str, song_title: str) -> CopyrightLawsuit:
        lawsuit = CopyrightLawsuit(
            lawsuit_id=f"suit_{random.randint(1000, 9999)}",
            plaintiff_name="Estate of 70s Soul Guitarist Marcus Vance",
            plaintiff_song="'Midnight Groove' (1976)",
            accused_song_id=song_id,
            accused_song_title=song_title,
            damages_claimed=85000,
            settlement_offer=25000,
        )
        self.pending_lawsuits.append(lawsuit)
        return lawsuit

    def resolve_lawsuit_settlement(self, player, lawsuit_id: str, choose_settle: bool = True) -> Dict[str, Any]:
        suit = next((s for s in self.pending_lawsuits if s.lawsuit_id == lawsuit_id and s.is_active), None)
        if not suit:
            return {"ok": False, "explanation": "Lawsuit not found or already resolved."}

        if choose_settle:
            cost = suit.settlement_offer
            if player.money < cost:
                return {"ok": False, "explanation": f"Need ${cost:,} to settle the copyright claim."}
            player.money -= cost
            suit.is_active = False
            suit.is_resolved = True
            suit.verdict = "SETTLED_OUT_OF_COURT"
            return {
                "ok": True,
                "cost": cost,
                "explanation": f"⚖️ SETTLED OUT OF COURT with {suit.plaintiff_name} for ${cost:,}. Lawsuit dismissed with zero admission of liability.",
            }
        else:
            # Go to court trial
            win_chance = 0.65
            if random.random() < win_chance:
                suit.is_active = False
                suit.is_resolved = True
                suit.verdict = "VERDICT_DEFENDANT_WIN"
                player.fame = min(1000, player.fame + 15)
                player.street_cred = min(100, player.street_cred + 20)
                return {
                    "ok": True,
                    "cost": 0,
                    "explanation": f"⚖️ COURTROOM VICTORY! Federal jury ruled in your favor! '{suit.accused_song_title}' declared original work! (+20 Street Cred).",
                }
            else:
                damages = suit.damages_claimed
                if player.money < damages:
                    damages = player.money
                player.money -= damages
                suit.is_active = False
                suit.is_resolved = True
                suit.verdict = "VERDICT_PLAINTIFF_WIN"
                return {
                    "ok": True,
                    "cost": damages,
                    "explanation": f"⚖️ JURY VERDICT: Infringement found. Ordered to pay ${damages:,} in copyright damages to {suit.plaintiff_name}.",
                }
