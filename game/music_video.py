from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class MusicVideo:
    video_id: str
    song_id: str
    song_title: str
    tier: str  # "DIY", "INDIE_DIRECTOR", "MAJOR_CINEMATIC"
    production_cost: int
    director_name: str
    concept: str
    views: int = 0
    likes: int = 0
    viral_spike_active: bool = False
    release_day: int = 0


class MusicVideoSystem:
    """Handles realistic music video shooting, director styles, streaming video platforms, and viral metrics."""

    TIERS = {
        "DIY": {
            "name": "DIY Camcorder / Smartphone Video",
            "cost": 150,
            "fame_reward": 5,
            "cred_reward": 15,
            "base_views": 1200,
            "viral_chance": 0.10,
        },
        "INDIE_DIRECTOR": {
            "name": "Indie Film Director Production",
            "cost": 2500,
            "fame_reward": 25,
            "cred_reward": 10,
            "base_views": 25000,
            "viral_chance": 0.35,
        },
        "MAJOR_CINEMATIC": {
            "name": "High-Budget Cinematic Production",
            "cost": 20000,
            "fame_reward": 75,
            "cred_reward": 5,
            "base_views": 250000,
            "viral_chance": 0.70,
        },
    }

    CONCEPTS = [
        "Gritty Underground Rehearsal Performance",
        "Surreal Retro 80s VHS Dreamscape",
        "Cinematic Late-Night Highway Narrative",
        "Intimate Acoustic Living Room One-Take",
        "High-Energy Punk Warehouse Moshpit",
    ]

    DIRECTORS = [
        "Jonas Akerlund Style",
        "Spike Jonze Style",
        "Michel Gondry Style",
        "Self-Directed DIY",
        "Local Film Student",
    ]

    def __init__(self):
        self.videos: List[MusicVideo] = []
        self.accumulated_unpaid_ad_revenue: float = 0.0

    def shoot_music_video(self, player, song, tier_key: str = "DIY", concept: Optional[str] = None) -> Dict[str, Any]:
        tier_info = self.TIERS.get(tier_key)
        if not tier_info:
            return {"ok": False, "explanation": f"Unknown video production tier '{tier_key}'."}

        cost = tier_info["cost"]
        if player.money < cost:
            return {"ok": False, "explanation": f"Insufficient funds. {tier_info['name']} requires ${cost}."}

        player.money -= cost
        director = "Self-Directed" if tier_key == "DIY" else random.choice(self.DIRECTORS)
        chosen_concept = concept or random.choice(self.CONCEPTS)

        is_viral = random.random() < tier_info["viral_chance"]
        multiplier = 3.5 if is_viral else 1.0
        initial_views = int(tier_info["base_views"] * multiplier * (1.0 + (player.fame * 0.01)))
        initial_likes = int(initial_views * 0.08)

        video = MusicVideo(
            video_id=str(uuid.uuid4()),
            song_id=getattr(song, "song_id", str(uuid.uuid4())),
            song_title=getattr(song, "title", "Untitled"),
            tier=tier_key,
            production_cost=cost,
            director_name=director,
            concept=chosen_concept,
            views=initial_views,
            likes=initial_likes,
            viral_spike_active=is_viral,
            release_day=current_game_time.day,
        )

        self.videos.append(video)
        setattr(song, "has_music_video", True)
        setattr(song, "music_video_quality", 0.9 if tier_key == "MAJOR_CINEMATIC" else (0.75 if tier_key == "INDIE_DIRECTOR" else 0.55))

        player.fame = min(1000, player.fame + tier_info["fame_reward"])
        player.street_cred = min(100, player.street_cred + tier_info["cred_reward"])

        msg = f"Released music video for '{video.song_title}' ({tier_info['name']}) directed by {director}!"
        if is_viral:
            msg += f" 🔥 VIRAL SPIKE! Video reached {initial_views:,} views on video platforms!"
        else:
            msg += f" Video debuted with {initial_views:,} views and {initial_likes:,} likes."

        return {
            "ok": True,
            "video": video,
            "explanation": msg,
        }

    def process_daily_views_and_ad_revenue(self, player) -> List[str]:
        logs = []
        total_daily_views = 0

        for video in self.videos:
            # Daily organic view accrual (0.01 per day decaying)
            decay = 0.95
            daily_views = max(10, int(video.views * 0.02 * decay))
            if video.viral_spike_active:
                daily_views *= 3
            video.views += daily_views
            video.likes += int(daily_views * 0.06)
            total_daily_views += daily_views

            # Video streaming monetization (~$1.50 per 1,000 views)
            ad_rev = (daily_views / 1000.0) * 1.50
            self.accumulated_unpaid_ad_revenue += ad_rev

        if self.accumulated_unpaid_ad_revenue >= 1.0:
            payout = int(self.accumulated_unpaid_ad_revenue)
            player.money += payout
            self.accumulated_unpaid_ad_revenue -= payout
            logs.append(f"Received +${payout} in video platform ad revenue ({total_daily_views:,} views today).")
        elif total_daily_views > 0:
            logs.append(f"Music videos gained +{total_daily_views:,} views across streaming video platforms.")

        return logs
