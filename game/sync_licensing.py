from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class SyncOpportunity:
    opportunity_id: str
    title: str
    media_type: str        # "MOVIE", "TV_DRAMA", "COMMERCIAL", "VIDEO_GAME"
    client_name: str
    city: str
    location_agency: str
    upfront_fee: int
    min_song_quality: float
    min_fame: int
    genre_preference: str
    streaming_boost_daily: int
    duration_days: int
    lore_description: str


@dataclass
class ActiveSyncPlacement:
    placement_id: str
    song_id: str
    song_title: str
    opportunity: SyncOpportunity
    day_placed: int
    days_remaining: int
    total_fee_earned: int


class SyncLicensingSystem:
    """Manages location-driven Sync Licensing deals across Hollywood, Madison Ave, Tokyo, and London."""

    CATALOG = {
        "hollywood_blockbuster": SyncOpportunity(
            opportunity_id="hollywood_blockbuster",
            title="A24 / Warner Major Feature Film Soundtrack",
            media_type="MOVIE",
            client_name="Sunset Studios Hollywood",
            city="Los Angeles, CA",
            location_agency="Hollywood Sunset Sync Agency",
            upfront_fee=45000,
            min_song_quality=0.80,
            min_fame=80,
            genre_preference="Rock/Indie/Alternative",
            streaming_boost_daily=12000,
            duration_days=30,
            lore_description="Key emotional montage scene in an upcoming psychological thriller starring A-list actors.",
        ),
        "netflix_prestige_drama": SyncOpportunity(
            opportunity_id="netflix_prestige_drama",
            title="HBO / Netflix Prestige Crime Drama End Credits",
            media_type="TV_DRAMA",
            client_name="Beverly Hills Media Group",
            city="Los Angeles, CA",
            location_agency="Beverly Hills Talent Agency",
            upfront_fee=22000,
            min_song_quality=0.75,
            min_fame=50,
            genre_preference="Indie/Folk/Rock",
            streaming_boost_daily=6500,
            duration_days=21,
            lore_description="End credits needle-drop for the season finale episode broadcast to millions of streaming subscribers.",
        ),
        "super_bowl_ad_nyc": SyncOpportunity(
            opportunity_id="super_bowl_ad_nyc",
            title="Super Bowl National Luxury Car Commercial",
            media_type="COMMERCIAL",
            client_name="Madison Ave Advertising Worldwide",
            city="New York City, NY",
            location_agency="East Village Sync & Ad Exchange",
            upfront_fee=180000,
            min_song_quality=0.85,
            min_fame=120,
            genre_preference="Rock/Electronic/Pop",
            streaming_boost_daily=25000,
            duration_days=14,
            lore_description="Prime-time 60-second national TV spot airing during the biggest sporting event of the year.",
        ),
        "tokyo_aaa_game": SyncOpportunity(
            opportunity_id="tokyo_aaa_game",
            title="Square Enix / Capcom AAA Action Game Main Theme",
            media_type="VIDEO_GAME",
            client_name="Shibuya Interactive Audio Studios",
            city="Tokyo, Japan",
            location_agency="Shibuya Sound Agency (Tokyo)",
            upfront_fee=55000,
            min_song_quality=0.80,
            min_fame=70,
            genre_preference="Rock/Electronic/Metal",
            streaming_boost_daily=15000,
            duration_days=45,
            lore_description="Boss battle and opening cinematic theme for a global video game franchise releasing worldwide.",
        ),
        "bbc_british_drama": SyncOpportunity(
            opportunity_id="bbc_british_drama",
            title="BBC Television Period Drama Soundtrack",
            media_type="TV_DRAMA",
            client_name="West End London Screen Media",
            city="London, UK",
            location_agency="Soho Square Sync Agency (London)",
            upfront_fee=28000,
            min_song_quality=0.75,
            min_fame=60,
            genre_preference="Indie/Acoustic/Folk",
            streaming_boost_daily=8000,
            duration_days=25,
            lore_description="Atmospheric acoustic theme for a hit BBC historical drama airing across the UK and Europe.",
        ),
    }

    def __init__(self):
        self.active_placements: List[ActiveSyncPlacement] = []
        self.completed_placements_count: int = 0

    def scout_sync_opportunities_in_city(self, player) -> List[SyncOpportunity]:
        loc_name = getattr(player.current_location, "name", str(player.current_location))
        found = []
        for opp in self.CATALOG.values():
            if opp.city == loc_name:
                found.append(opp)
        return found

    def pitch_song_for_sync(self, player, song, opp_key: str) -> Dict[str, Any]:
        opp = self.CATALOG.get(opp_key)
        if not opp:
            return {"ok": False, "explanation": "Unknown sync opportunity."}

        loc_name = getattr(player.current_location, "name", str(player.current_location))
        if opp.city != loc_name:
            return {"ok": False, "explanation": f"You must travel to {opp.city} to pitch directly to {opp.location_agency}."}

        if not getattr(song, "is_recorded", False):
            return {"ok": False, "explanation": f"'{song.title}' must be fully recorded to submit master audio files."}

        if getattr(player, "fame", 0) < opp.min_fame:
            return {"ok": False, "explanation": f"Music supervisors require at least {opp.min_fame} Fame to consider this pitch."}

        rec_qual = getattr(song, "recording_quality", 0.5)
        if rec_qual < opp.min_song_quality:
            return {"ok": False, "explanation": f"Music supervisors require at least {opp.min_song_quality:.2f} recording quality (Current: {rec_qual:.2f})."}

        # Calculate fee with major label or manager negotiating leverage
        fee = opp.upfront_fee
        if getattr(player, "signed_label_deal", None):
            fee = int(fee * 1.20)

        player.money += fee
        player.fame = min(1000, player.fame + 25)
        player.street_cred = min(100, player.street_cred + 15)

        placement = ActiveSyncPlacement(
            placement_id=f"sync_{opp_key}_{len(self.active_placements)+1}",
            song_id=getattr(song, "song_id", "s1"),
            song_title=getattr(song, "title", "Untitled"),
            opportunity=opp,
            day_placed=current_game_time.day,
            days_remaining=opp.duration_days,
            total_fee_earned=fee,
        )
        self.active_placements.append(placement)

        summary = (
            f"🎬 SYNC LICENSING DEAL SIGNED with {opp.client_name} ({opp.location_agency})!\n"
            f"- Project: {opp.title}\n"
            f"- Upfront Sync Fee: +${fee:,} (Deposited into account)\n"
            f"- Media Description: {opp.lore_description}\n"
            f"- Estimated Streaming Surge: +{opp.streaming_boost_daily:,} daily streams over next {opp.duration_days} days!"
        )
        return {"ok": True, "placement": placement, "explanation": summary}

    def process_daily_sync_streams(self, streaming_sys=None) -> List[str]:
        logs = []
        still_active = []
        for pl in self.active_placements:
            pl.days_remaining -= 1
            if streaming_sys and pl.song_id in streaming_sys.catalog:
                st = streaming_sys.catalog[pl.song_id]
                st.daily_streams += pl.opportunity.streaming_boost_daily
                st.total_streams += pl.opportunity.streaming_boost_daily
            if pl.days_remaining > 0:
                still_active.append(pl)
            else:
                self.completed_placements_count += 1
                logs.append(f"📺 Sync placement for '{pl.song_title}' on '{pl.opportunity.title}' has concluded its broadcast run.")

        self.active_placements = still_active
        return logs
