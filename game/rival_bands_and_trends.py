from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class AIRivalBand:
    band_id: str
    name: str
    home_city: str
    genre: str
    fame: int
    buzz_score: int
    latest_hit: str
    total_albums_released: int = 2
    rivalry_intensity: str = "COMPETITIVE" # "FRIENDLY", "COMPETITIVE", "FEUD"


@dataclass
class CulturalTrendEra:
    trend_id: str
    name: str
    dominant_genre: str
    multiplier: float        # e.g. 1.30 = +30% stream boost to matching records
    days_remaining: int
    description: str


class RivalBandsAndTrendsSystem:
    """Manages persistent AI rival bands, scene ecosystem releases, and shifting cultural genre trends."""

    DEFAULT_RIVALS = {
        "silver_strays": AIRivalBand("silver_strays", "The Silver Strays", "London, UK", "Rock", 160, 85, "Neon Sunset Boulevard"),
        "static_reverie": AIRivalBand("static_reverie", "Static Reverie", "Seattle, WA", "Alternative", 140, 78, "Bleach & Velvet"),
        "neon_concrete": AIRivalBand("neon_concrete", "Neon Concrete", "Berlin, Germany", "Electronic", 150, 82, "Autobahn Strobe"),
        "apex_royalty": AIRivalBand("apex_royalty", "Apex Royalty", "Los Angeles, CA", "Pop", 220, 95, "Diamond Velvet Dream"),
        "copperhead_road": AIRivalBand("copperhead_road", "Copperhead Creek", "Nashville, TN", "Americana", 130, 72, "Dust & Diesel"),
        "subzero_syndicate": AIRivalBand("subzero_syndicate", "Sub-Zero Syndicate", "Detroit, MI", "Electronic", 125, 70, "Industrial Circuit"),
    }

    TREND_CYCLES = [
        CulturalTrendEra("grunge_revival", "90s Raw Grunge & Alt-Rock Revival", "Rock", 1.35, 90, "Distorted fuzz pedals, flannel aesthetics, and explosive raw guitar hooks dominate the airwaves."),
        CulturalTrendEra("synthwave_boom", "Retro 80s Cyber-Synthwave Boom", "Electronic", 1.30, 90, "Analog synthesizer arpeggios, gated reverb snares, and neon cinematic moods trend worldwide."),
        CulturalTrendEra("outlaw_americana", "Authentic Outlaw Americana & Folk Surge", "Americana", 1.30, 90, "Stripped-back acoustic storytelling, pedal steel, and gritty working-class ballads capture the public."),
        CulturalTrendEra("bedroom_lofi", "Intimate Lo-Fi Bedroom Indie Wave", "Indie", 1.25, 90, "Cassette tape flutter, warm vintage preamps, and vulnerable whispering vocal melodies lead Spotify editorial."),
    ]

    def __init__(self):
        self.rivals: Dict[str, AIRivalBand] = dict(self.DEFAULT_RIVALS)
        self.active_trend_index: int = 0
        self.active_trend: CulturalTrendEra = self.TREND_CYCLES[0]
        self.rival_news_feed: List[str] = []

    def get_current_trend(self) -> CulturalTrendEra:
        return self.active_trend

    def check_and_cycle_cultural_trends(self) -> Optional[str]:
        self.active_trend.days_remaining -= 1
        if self.active_trend.days_remaining <= 0:
            self.active_trend_index = (self.active_trend_index + 1) % len(self.TREND_CYCLES)
            new_t = self.TREND_CYCLES[self.active_trend_index]
            self.active_trend = CulturalTrendEra(
                trend_id=new_t.trend_id,
                name=new_t.name,
                dominant_genre=new_t.dominant_genre,
                multiplier=new_t.multiplier,
                days_remaining=90,
                description=new_t.description,
            )
            msg = f"🌊 CULTURAL ZEITGEIST SHIFT: '{self.active_trend.name}' is now the dominant global music wave! ({self.active_trend.dominant_genre} gets +{int((self.active_trend.multiplier-1)*100)}% streaming boost)."
            self.rival_news_feed.append(msg)
            return msg
        return None

    def simulate_rival_band_activity(self) -> List[str]:
        logs = []
        # Random rival releases a single or tour announcement
        r = random.choice(list(self.rivals.values()))
        actions = [
            f"🎸 SCENE BUZZ: Rival band '{r.name}' released a surprise single '{r.latest_hit}' charting on UK/US charts!",
            f"🎪 FESTIVAL RIVALRY: '{r.name}' announced a sold-out European arena tour starting in {r.home_city}.",
            f"🏆 INDUSTRY UPDATE: '{r.name}' nominated for Best Alternative Record at the International Music Awards.",
        ]
        chosen = random.choice(actions)
        logs.append(chosen)
        self.rival_news_feed.append(chosen)
        return logs
