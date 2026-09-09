from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class FanClubTier:
    tier_name: str
    price_per_month: int
    subscribers_count: int
    perks_desc: str


class FanClubAndPRSystem:
    """Manages Direct-to-Fan recurring monthly VIP club revenue, paparazzi rumors, and PR crisis defense."""

    def __init__(self):
        self.is_club_launched: bool = False
        self.tiers = {
            "tier_bronze": FanClubTier("Bronze Supporter", 5, 0, "Exclusive demo snippets & private Discord access."),
            "tier_silver": FanClubTier("Silver Inner Circle", 15, 0, "Early ticket access, vinyl discounts, quarterly acoustic streams."),
            "tier_gold": FanClubTier("Gold VIP Pass", 50, 0, "Backstage meet-and-greets, signed test pressings, credits in liner notes."),
        }
        self.accumulated_club_revenue: int = 0
        self.pr_crises_resolved: List[str] = []

    def launch_vip_fan_club(self, player) -> Dict[str, Any]:
        if self.is_club_launched:
            return {"ok": False, "explanation": "VIP Fan Club is already active."}

        self.is_club_launched = True
        # Calculate initial subscribers based on street cred & fame
        fame = getattr(player, "fame", 10)
        cred = getattr(player, "street_cred", 50)

        self.tiers["tier_bronze"].subscribers_count = max(20, int(fame * 3.5 + cred * 2))
        self.tiers["tier_silver"].subscribers_count = max(5, int(fame * 1.2 + cred * 0.8))
        self.tiers["tier_gold"].subscribers_count = max(1, int(fame * 0.2 + cred * 0.1))

        total_subs = sum(t.subscribers_count for t in self.tiers.values())
        monthly_run = sum(t.subscribers_count * t.price_per_month for t in self.tiers.values())

        summary = (
            f"🌟 LAUNCHED OFFICIAL VIP DIRECT-TO-FAN CLUB!\n"
            f"- Initial Subscribers: {total_subs:,} passionate die-hard fans across 3 tiers\n"
            f"- Projected Monthly Recurring Revenue: +${monthly_run:,}/month\n"
            f"- Fans receive exclusive Discord roles, unreleased demos, and vinyl pre-orders."
        )
        return {"ok": True, "total_subscribers": total_subs, "explanation": summary}

    def process_monthly_fan_club_payout(self, player) -> List[str]:
        if not self.is_club_launched:
            return []

        # Organic subscriber growth based on fame
        fame = getattr(player, "fame", 10)
        new_bronze = max(1, int(fame * 0.15))
        self.tiers["tier_bronze"].subscribers_count += new_bronze

        monthly_total = sum(t.subscribers_count * t.price_per_month for t in self.tiers.values())
        player.money += monthly_total
        self.accumulated_club_revenue += monthly_total

        return [f"💌 DIRECT-TO-FAN VIP CLUB: Deposited +${monthly_total:,} in monthly recurring subscription revenue from {sum(t.subscribers_count for t in self.tiers.values()):,} members."]

    def hire_pr_crisis_firm(self, player, crisis_description: str) -> Dict[str, Any]:
        cost = 5000
        if player.money < cost:
            return {"ok": False, "explanation": f"PR Crisis Management agency requires ${cost:,} retainer."}

        player.money -= cost
        player.stress = max(0, player.stress - 30)
        player.street_cred = min(100, player.street_cred + 10)
        self.pr_crises_resolved.append(crisis_description)

        summary = (
            f"🎙️ PR CRISIS DEFUSED by Public Relations Agency (-${cost:,})!\n"
            f"- Media narrative controlled, apology/statement released, and press embargo secured.\n"
            f"- Stress reduced by 30 points."
        )
        return {"ok": True, "explanation": summary}
