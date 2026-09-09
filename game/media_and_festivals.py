from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class LateNightTVShow:
    show_id: str
    name: str
    city: str
    studio_location: str
    host_name: str
    min_fame: int
    national_viewers: int
    fame_boost: int
    cred_boost: int


@dataclass
class GlobalFestivalMainstage:
    festival_id: str
    name: str
    city: str
    venue_site: str
    capacity: int
    min_fame: int
    artist_guarantee_fee: int
    cultural_prestige: int
    weather_hazard: str
    genre_focus: str


class MediaAndFestivalsSystem:
    """Manages location-driven Late-Night TV studio appearances and Global Festival Mainstage performances."""

    TV_SHOWS = {
        "tonight_30rock": LateNightTVShow(
            show_id="tonight_30rock",
            name="The Tonight Broadcast Live",
            city="New York City, NY",
            studio_location="Studio 6B, 30 Rockefeller Plaza",
            host_name="Jimmy Fallon style host",
            min_fame=100,
            national_viewers=4500000,
            fame_boost=45,
            cred_boost=10,
        ),
        "bbc_live_lounge": LateNightTVShow(
            show_id="bbc_live_lounge",
            name="BBC Live Lounge & Late Show",
            city="London, UK",
            studio_location="BBC Television Centre (White City)",
            host_name="Jools Holland style host",
            min_fame=80,
            national_viewers=2800000,
            fame_boost=35,
            cred_boost=20,
        ),
        "hollywood_late_live": LateNightTVShow(
            show_id="hollywood_late_live",
            name="Jimmy Kimmel Live Outdoor Stage",
            city="Los Angeles, CA",
            studio_location="Hollywood Boulevard Studio Stage",
            host_name="Hollywood Late Night host",
            min_fame=90,
            national_viewers=3200000,
            fame_boost=40,
            cred_boost=12,
        ),
    }

    FESTIVALS = {
        "glastonbury": GlobalFestivalMainstage(
            festival_id="glastonbury",
            name="Glastonbury Festival (Pyramid Stage)",
            city="London, UK",
            venue_site="Worthy Farm (Pilton / London Circuit)",
            capacity=120000,
            min_fame=150,
            artist_guarantee_fee=150000,
            cultural_prestige=5,
            weather_hazard="Heavy English Rain & Muddy Sludge",
            genre_focus="Rock/Indie/Legendary",
        ),
        "coachella": GlobalFestivalMainstage(
            festival_id="coachella",
            name="Coachella Valley Music & Arts Festival",
            city="Los Angeles, CA",
            venue_site="Empire Polo Club (Indio / LA Circuit)",
            capacity=85000,
            min_fame=130,
            artist_guarantee_fee=125000,
            cultural_prestige=5,
            weather_hazard="Desert Heatwave & Dust Storm",
            genre_focus="Indie/Pop/Electronic",
        ),
        "fuji_rock": GlobalFestivalMainstage(
            festival_id="fuji_rock",
            name="Fuji Rock Festival (Green Stage)",
            city="Tokyo, Japan",
            venue_site="Naeba Ski Resort (Tokyo Circuit)",
            capacity=45000,
            min_fame=110,
            artist_guarantee_fee=95000,
            cultural_prestige=4,
            weather_hazard="Mountain Mist & Torrential Alpine Rain",
            genre_focus="Alternative/Rock",
        ),
        "lollapalooza": GlobalFestivalMainstage(
            festival_id="lollapalooza",
            name="Lollapalooza (Grant Park Mainstage)",
            city="Chicago, IL",
            venue_site="Grant Park (Chicago Lakefront)",
            capacity=70000,
            min_fame=120,
            artist_guarantee_fee=110000,
            cultural_prestige=4,
            weather_hazard="Lake Michigan Thunderstorm",
            genre_focus="Alternative/Rock/Hip-Hop",
        ),
        "acl_festival": GlobalFestivalMainstage(
            festival_id="acl_festival",
            name="Austin City Limits Music Festival",
            city="Austin, TX",
            venue_site="Zilker Park (Austin Skyline)",
            capacity=75000,
            min_fame=95,
            artist_guarantee_fee=85000,
            cultural_prestige=4,
            weather_hazard="Scorching Texas Sun",
            genre_focus="Roots/Rock/Indie",
        ),
        "tempelhof_superbloom": GlobalFestivalMainstage(
            festival_id="tempelhof_superbloom",
            name="Tempelhof Sounds & Superbloom",
            city="Berlin, Germany",
            venue_site="Tempelhof Historic Airfield Runway",
            capacity=50000,
            min_fame=105,
            artist_guarantee_fee=90000,
            cultural_prestige=4,
            weather_hazard="Windy Airfield Gusts",
            genre_focus="Indie/Electronic",
        ),
    }

    def __init__(self):
        self.tv_performances_logged: List[Dict[str, Any]] = []
        self.festival_sets_logged: List[Dict[str, Any]] = []

    def perform_late_night_tv(self, player, show_key: str, song_title: str) -> Dict[str, Any]:
        show = self.TV_SHOWS.get(show_key)
        if not show:
            return {"ok": False, "explanation": "Unknown TV show."}

        loc_name = getattr(player.current_location, "name", str(player.current_location))
        if show.city != loc_name:
            return {"ok": False, "explanation": f"You must travel to {show.city} to tape at {show.studio_location}."}

        if player.fame < show.min_fame:
            return {"ok": False, "explanation": f"TV producers require at least {show.min_fame} Fame for a guest music performance."}

        player.fame = min(1000, player.fame + show.fame_boost)
        player.street_cred = min(100, player.street_cred + show.cred_boost)

        record = {
            "show_name": show.name,
            "city": show.city,
            "song": song_title,
            "viewers": show.national_viewers,
            "day": current_game_time.day,
        }
        self.tv_performances_logged.append(record)

        summary = (
            f"📺 BROADCAST HIT! Performed '{song_title}' live on {show.name} at {show.studio_location}!\n"
            f"- National TV Audience: {show.national_viewers:,} viewers\n"
            f"- Fame Surge: +{show.fame_boost} Fame\n"
            f"- Cultural Credibility: +{show.cred_boost} Street Cred"
        )
        return {"ok": True, "performance": record, "explanation": summary}

    def headline_festival_mainstage(self, player, fest_key: str, setlist_titles: List[str]) -> Dict[str, Any]:
        fest = self.FESTIVALS.get(fest_key)
        if not fest:
            return {"ok": False, "explanation": "Unknown festival."}

        loc_name = getattr(player.current_location, "name", str(player.current_location))
        if fest.city != loc_name:
            return {"ok": False, "explanation": f"You must travel to {fest.city} to play at {fest.venue_site}."}

        if player.fame < fest.min_fame:
            return {"ok": False, "explanation": f"Festival headliner bookers require at least {fest.min_fame} Fame."}

        # Check 360 contract cuts
        payout = fest.artist_guarantee_fee
        contract_msg = ""
        if hasattr(player, "major_contract") and player.major_contract and player.major_contract.has_360_deal:
            cut = int(payout * (player.major_contract.touring_cut_pct / 100.0))
            payout -= cut
            contract_msg = f" (Label took ${cut:,} under 360 terms)"

        player.money += payout
        fame_gain = int(fest.capacity * 0.001 * fest.cultural_prestige)
        cred_gain = fest.cultural_prestige * 4
        player.fame = min(1000, player.fame + fame_gain)
        player.street_cred = min(100, player.street_cred + cred_gain)

        record = {
            "festival_name": fest.name,
            "city": fest.city,
            "attendance": fest.capacity,
            "payout": payout,
            "day": current_game_time.day,
        }
        self.festival_sets_logged.append(record)

        summary = (
            f"🎪 HEADLINED {fest.name} at {fest.venue_site}!\n"
            f"- Crowd Size: {fest.capacity:,} roaring festival goers!\n"
            f"- Weather Element: Handled '{fest.weather_hazard}' with legendary composure!\n"
            f"- Artist Fee Guarantee: +${payout:,}{contract_msg}\n"
            f"- Cultural Impact: +{fame_gain} Fame, +{cred_gain} Street Cred"
        )
        return {"ok": True, "festival_set": record, "explanation": summary}
