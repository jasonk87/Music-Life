from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid

from game.game_time import current_game_time
from game.rivals import add_news


@dataclass
class SignedArtist:
    npc_id: str
    name: str
    genre: str
    skill_level: int
    royalty_split: float
    advance_paid: int
    releases_count: int = 0
    total_earnings_generated: float = 0.0


class IndieLabelImprint:
    FOUNDING_COST = 5000
    MIN_FAME_REQUIRED = 150

    def __init__(self, label_name: str, owner_name: str):
        self.label_name = label_name
        self.owner_name = owner_name
        self.roster: Dict[str, SignedArtist] = {}
        self.total_label_revenue: float = 0.0

    def sign_artist(self, npc, advance_amount: int = 500) -> Dict:
        if npc.npc_id in self.roster:
            return {"ok": False, "explanation": f"{npc.name} is already signed to {self.label_name}."}

        artist = SignedArtist(
            npc_id=npc.npc_id,
            name=npc.name,
            genre=getattr(npc, "genre", "Indie"),
            skill_level=getattr(npc, "skill_level", 5),
            royalty_split=0.50,
            advance_paid=advance_amount,
        )
        self.roster[npc.npc_id] = artist
        npc.signed_label_deal = self.label_name
        npc.career_stage = "label_artist"
        add_news(f"LABEL SIGNING: {self.label_name} has officially signed {npc.name}!")
        return {"ok": True, "explanation": f"Signed {npc.name} to {self.label_name}! Paid ${advance_amount} advance."}

    def fund_and_release_single(self, game, npc_id: str, budget: int = 400) -> Dict:
        artist = self.roster.get(npc_id)
        if not artist:
            return {"ok": False, "explanation": "Artist not in label roster."}

        player = game.player
        if player.money < budget:
            return {"ok": False, "explanation": f"Insufficient funds to budget ${budget} for release."}

        player.money -= budget
        artist.releases_count += 1

        gross_revenue = budget * 2.5 + (artist.skill_level * 150)
        label_cut = gross_revenue * artist.royalty_split
        artist_cut = gross_revenue * (1.0 - artist.royalty_split)

        self.total_label_revenue += label_cut
        artist.total_earnings_generated += gross_revenue
        player.money += label_cut
        player.fame += 5

        add_news(f"LABEL RELEASE: {self.label_name} dropped a new single by {artist.name}, generating ${gross_revenue:.0f} gross!")
        return {
            "ok": True,
            "gross": gross_revenue,
            "label_share": label_cut,
            "artist_share": artist_cut,
            "explanation": f"Released single for {artist.name}! Gross revenue: ${gross_revenue:.0f}. Label share (+${label_cut:.0f}) deposited to your funds.",
        }
