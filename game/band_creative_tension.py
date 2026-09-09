from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class CreativeDisputeEvent:
    event_id: str
    title: str
    member_name: str
    song_title: str
    description: str
    options: List[Dict[str, Any]]
    resolved: bool = False
    chosen_option_index: Optional[int] = None


class BandCreativeTensionSystem:
    """Manages creative friction, songwriting credit disputes, and producer disagreements."""

    def __init__(self):
        self.dispute_history: List[CreativeDisputeEvent] = []

    def check_for_recording_dispute(self, player, song, bandmates: List[Any]) -> Optional[CreativeDisputeEvent]:
        if not bandmates or len(bandmates) == 0:
            return None

        member = random.choice(bandmates)
        member_name = getattr(member, "member_name", getattr(member, "name", "Bandmate"))

        event = CreativeDisputeEvent(
            event_id=f"dispute_{len(self.dispute_history)+1}",
            title="Publishing & Songwriting Credit Dispute",
            member_name=member_name,
            song_title=getattr(song, "title", "Track"),
            description=(
                f"{member_name} contributed the distinctive bass groove and bridge motif on '{song.title}'. "
                f"They are requesting a 25% co-writing credit on the official copyright registration."
            ),
            options=[
                {
                    "key": "GRANT_SPLIT",
                    "text": f"Grant 25% Co-Writing Credit to {member_name}",
                    "effect_desc": "Boosts bandmate morale (+30), improves song quality (+0.05), shares future royalties.",
                },
                {
                    "key": "STAND_FIRM",
                    "text": "Stand Firm as Sole Auteur & Songwriter",
                    "effect_desc": "Retains 100% publishing rights, but creates bitter creative resentment (Morale -30).",
                },
                {
                    "key": "CASH_BUYOUT",
                    "text": "Offer $1,500 Cash Arrangement Bonus",
                    "effect_desc": "Satisfies bandmate financially without sacrificing master copyright ownership.",
                },
            ],
            resolved=False,
        )
        return event

    def resolve_dispute(self, player, dispute: CreativeDisputeEvent, choice_idx: int, song, bandmate=None) -> Dict[str, Any]:
        if choice_idx < 0 or choice_idx >= len(dispute.options):
            return {"ok": False, "explanation": "Invalid dispute option selection."}

        opt = dispute.options[choice_idx]
        dispute.resolved = True
        dispute.chosen_option_index = choice_idx
        self.dispute_history.append(dispute)

        summary = ""
        if opt["key"] == "GRANT_SPLIT":
            song.song_quality = min(1.0, getattr(song, "song_quality", 0.5) + 0.05)
            if bandmate and hasattr(bandmate, "satisfaction"):
                bandmate.satisfaction = min(100.0, bandmate.satisfaction + 30.0)
            summary = (
                f"🤝 CO-WRITING AGREEMENT SIGNED: Shared 25% credit with {dispute.member_name} on '{song.title}'.\n"
                f"- Band morale surged and creative chemistry elevated the song quality to {song.song_quality:.2f}!"
            )

        elif opt["key"] == "STAND_FIRM":
            if bandmate and hasattr(bandmate, "satisfaction"):
                bandmate.satisfaction = max(0.0, bandmate.satisfaction - 30.0)
            player.stress = min(100, player.stress + 15)
            summary = (
                f"⚡ SOLE AUTEUR CREATIVE CONTROL: Maintained 100% sole writing credit on '{song.title}'.\n"
                f"- {dispute.member_name} felt dismissed. Creative tension increased in the studio."
            )

        elif opt["key"] == "CASH_BUYOUT":
            bonus = 1500
            if player.money >= bonus:
                player.money -= bonus
                if bandmate and hasattr(bandmate, "satisfaction"):
                    bandmate.satisfaction = min(100.0, bandmate.satisfaction + 15.0)
                summary = (
                    f"💵 ARRANGEMENT BONUS PAID: Paid ${bonus:,} bonus to {dispute.member_name}.\n"
                    f"- Maintained 100% publishing rights while keeping studio peace."
                )
            else:
                summary = f"⚠️ INSUFFICIENT FUNDS: Could not afford ${bonus} bonus. Split unresolved."

        return {"ok": True, "choice": opt["key"], "explanation": summary}
