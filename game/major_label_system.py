from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class MajorLabelContract:
    contract_id: str
    label_name: str
    city: str
    headquarters: str
    advance_amount: int
    artist_royalty_pct: float     # e.g. 18.0 = 18%
    recoupable_balance: float      # Starts at advance amount
    master_ownership_years: int    # e.g. 15 years, or 99 for perpetuity
    has_360_deal: bool             # Label takes 15-20% of touring and merch
    touring_cut_pct: float         # e.g. 15.0%
    merch_cut_pct: float           # e.g. 20.0%
    video_fund: int                # Dedicated video budget from label
    albums_committed: int = 3
    albums_delivered: int = 0
    is_active: bool = False
    is_recouped: bool = False
    is_shelved: bool = False


class MajorLabelSystem:
    """Manages location-driven A&R scouting, major label HQ meetings, and 360 contract economics."""

    LABEL_CATALOG = {
        "empire_nyc": {
            "name": "Empire Records International",
            "city": "New York City, NY",
            "hq": "Manhattan Plaza Tower (NYC)",
            "advance": 500000,
            "royalty": 18.0,
            "master_years": 15,
            "is_360": True,
            "tour_cut": 15.0,
            "merch_cut": 20.0,
            "video_fund": 50000,
            "min_fame": 120,
            "desc": "Prestige corporate behemoth. Massive $500k advance and nationwide radio muscle, but takes 360 cuts of touring/merch.",
        },
        "pacific_la": {
            "name": "Pacific Sunset Music Group",
            "city": "Los Angeles, CA",
            "hq": "Sunset Boulevard Tower (Hollywood, LA)",
            "advance": 350000,
            "royalty": 20.0,
            "master_years": 10,
            "is_360": False,
            "tour_cut": 0.0,
            "merch_cut": 0.0,
            "video_fund": 100000,
            "min_fame": 100,
            "desc": "Hollywood entertainment giant. Huge $100k music video budgets and sync licensing for movies and television.",
        },
        "music_row_nash": {
            "name": "Music Row Heritage Records",
            "city": "Nashville, TN",
            "hq": "RCA Studio Row Boardroom (Nashville, TN)",
            "advance": 200000,
            "royalty": 22.0,
            "master_years": 7,
            "is_360": False,
            "tour_cut": 0.0,
            "merch_cut": 0.0,
            "video_fund": 30000,
            "min_fame": 75,
            "desc": "Artist-friendly traditional powerhouse. Clean 22% royalty split, master reversion in 7 years, zero 360 cuts.",
        },
        "crown_sound_london": {
            "name": "Crown Sound Worldwide",
            "city": "London, UK",
            "hq": "Soho Square HQ (London, UK)",
            "advance": 300000,
            "royalty": 19.0,
            "master_years": 12,
            "is_360": True,
            "tour_cut": 10.0,
            "merch_cut": 15.0,
            "video_fund": 60000,
            "min_fame": 90,
            "desc": "Global tastemaker with deep BBC Radio 1 connections and international European festival mainstage priority.",
        },
    }

    def __init__(self):
        self.signed_contract: Optional[MajorLabelContract] = None
        self.scouted_offers: Dict[str, Dict[str, Any]] = {}

    def check_ar_scouting(self, player) -> List[Dict[str, Any]]:
        """Checks if A&R scouts approach the player in their current city."""
        offers_found = []
        loc_name = getattr(player.current_location, "name", str(player.current_location))
        fame = getattr(player, "fame", 0)

        for label_key, label_def in self.LABEL_CATALOG.items():
            if label_def["city"] == loc_name and fame >= label_def["min_fame"]:
                if label_key not in self.scouted_offers:
                    self.scouted_offers[label_key] = label_def
                    offers_found.append(label_def)

        return offers_found

    def negotiate_and_sign_contract(self, player, label_key: str, negotiate_advance_bonus: bool = False) -> Dict[str, Any]:
        if self.signed_contract and self.signed_contract.is_active:
            return {"ok": False, "explanation": f"You are already signed to {self.signed_contract.label_name}."}

        label_def = self.LABEL_CATALOG.get(label_key)
        if not label_def:
            return {"ok": False, "explanation": "Unknown record label."}

        loc_name = getattr(player.current_location, "name", str(player.current_location))
        if label_def["city"] != loc_name:
            return {"ok": False, "explanation": f"You must travel to {label_def['city']} to meet in person at {label_def['hq']}."}

        if player.fame < label_def["min_fame"]:
            return {"ok": False, "explanation": f"A&R executives require at least {label_def['min_fame']} Fame to offer a deal."}

        advance = label_def["advance"]
        royalty = label_def["royalty"]
        if negotiate_advance_bonus:
            has_manager = getattr(player, "has_manager", False)
            if has_manager:
                advance = int(advance * 1.25)
                royalty += 1.5
            else:
                advance = int(advance * 1.10)

        contract = MajorLabelContract(
            contract_id=f"deal_{label_key}",
            label_name=label_def["name"],
            city=label_def["city"],
            headquarters=label_def["hq"],
            advance_amount=advance,
            artist_royalty_pct=royalty,
            recoupable_balance=float(advance),
            master_ownership_years=label_def["master_years"],
            has_360_deal=label_def["is_360"],
            touring_cut_pct=label_def["tour_cut"],
            merch_cut_pct=label_def["merch_cut"],
            video_fund=label_def["video_fund"],
            albums_committed=3,
            is_active=True,
        )

        self.signed_contract = contract
        player.money += advance
        player.fame = min(1000, player.fame + 50)
        player.signed_label_deal = contract.label_name

        summary = (
            f"🖊️ SIGNED MAJOR LABEL DEAL with {contract.label_name} at {contract.headquarters}!\n"
            f"- Advance Payout: +${advance:,} (Deposited into your bank account)\n"
            f"- Artist Royalty: {contract.artist_royalty_pct:.1f}%\n"
            f"- Master Reversion: {contract.master_ownership_years} Years\n"
            f"- Video Production Fund: ${contract.video_fund:,}\n"
            f"- 360 Scope: {'Yes (' + str(contract.touring_cut_pct) + '% Tour / ' + str(contract.merch_cut_pct) + '% Merch)' if contract.has_360_deal else 'No (Standard Distribution Only)'}"
        )

        return {
            "ok": True,
            "contract": contract,
            "explanation": summary,
        }

    def process_royalties_recoupment(self, player, gross_royalties: float) -> Dict[str, Any]:
        if not self.signed_contract or not self.signed_contract.is_active:
            return {"recouped": True, "artist_payout": gross_royalties}

        contract = self.signed_contract
        artist_share = gross_royalties * (contract.artist_royalty_pct / 100.0)

        if not contract.is_recouped:
            if contract.recoupable_balance > artist_share:
                contract.recoupable_balance -= artist_share
                return {
                    "recouped": False,
                    "artist_payout": 0.0,
                    "balance_remaining": contract.recoupable_balance,
                    "explanation": f"Label recouped ${artist_share:,.2f}. Unrecouped advance balance: ${contract.recoupable_balance:,.2f}.",
                }
            else:
                excess = artist_share - contract.recoupable_balance
                contract.recoupable_balance = 0.0
                contract.is_recouped = True
                player.money += int(excess)
                return {
                    "recouped": True,
                    "artist_payout": excess,
                    "explanation": f"🎉 FULLY RECOUPED! Advance repaid in full. Payout: +${int(excess)}!",
                }
        else:
            player.money += int(artist_share)
            return {
                "recouped": True,
                "artist_payout": artist_share,
                "explanation": f"Received +${int(artist_share)} in pure major label artist royalties ({contract.artist_royalty_pct:.1f}% cut).",
            }
