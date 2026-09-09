from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class MarketingCampaign:
    campaign_id: str
    name: str
    category: str       # "DIGITAL_VIRAL", "BILLBOARD", "RADIO", "STREET_TEAM", "PR_STUNT"
    cost: int
    buzz_min: int
    buzz_max: int
    cred_bonus: int
    fame_bonus: int
    description: str


# Legacy & Game UI compatibility dict
CAMPAIGN_TYPES = {
    "social_media": {"name": "Social Media Blast", "cost": 100, "buzz_gain_min": 5, "buzz_gain_max": 15},
    "street_team": {"name": "Street Team Flyers", "cost": 300, "buzz_gain_min": 10, "buzz_gain_max": 30},
    "radio_push": {"name": "Radio Push", "cost": 1000, "buzz_gain_min": 40, "buzz_gain_max": 80},
    "pr_stunt": {"name": "PR Stunt (Risky)", "cost": 500, "buzz_gain_min": -20, "buzz_gain_max": 100},
    "music_video": {"name": "Music Video", "cost": 5000, "buzz_gain_min": 150, "buzz_gain_max": 300},
    "tiktok_viral_push": {"name": "Short-Form Video Viral Audio Campaign", "cost": 800, "buzz_gain_min": 30, "buzz_gain_max": 90},
    "times_square_billboard": {"name": "Times Square Digital Billboard Takeover", "cost": 35000, "buzz_gain_min": 350, "buzz_gain_max": 600},
    "tastemaker_radio_push": {"name": "NPR Music & BBC 6 Music Editorial Push", "cost": 4000, "buzz_gain_min": 120, "buzz_gain_max": 220},
    "guerrilla_street_team": {"name": "Guerrilla Flyering & Poster Drive", "cost": 600, "buzz_gain_min": 25, "buzz_gain_max": 60},
    "provocative_pr_stunt": {"name": "Rooftop Pop-Up Stunt", "cost": 2500, "buzz_gain_min": 50, "buzz_gain_max": 250},
}


class MarketingSystem:
    """Multi-channel music marketing engine: Times Square billboards, TikTok algorithms, radio, and street teams."""

    CAMPAIGNS = {
        "social_media": MarketingCampaign(
            campaign_id="social_media",
            name="Social Media Blast",
            category="DIGITAL_VIRAL",
            cost=100,
            buzz_min=5,
            buzz_max=15,
            cred_bonus=2,
            fame_bonus=5,
            description="Boosted social media ads and sponsored story posts.",
        ),
        "street_team": MarketingCampaign(
            campaign_id="street_team",
            name="Street Team Flyers",
            category="STREET_TEAM",
            cost=300,
            buzz_min=10,
            buzz_max=30,
            cred_bonus=10,
            fame_bonus=5,
            description="Distributing flyers outside concert halls.",
        ),
        "radio_push": MarketingCampaign(
            campaign_id="radio_push",
            name="Radio Push",
            category="RADIO",
            cost=1000,
            buzz_min=40,
            buzz_max=80,
            cred_bonus=15,
            fame_bonus=20,
            description="Radio promotion campaign servicing local commercial stations.",
        ),
        "pr_stunt": MarketingCampaign(
            campaign_id="pr_stunt",
            name="PR Stunt (Risky)",
            category="PR_STUNT",
            cost=500,
            buzz_min=-20,
            buzz_max=100,
            cred_bonus=5,
            fame_bonus=25,
            description="Publicity stunt designed to capture headlines.",
        ),
        "music_video": MarketingCampaign(
            campaign_id="music_video",
            name="Music Video",
            category="DIGITAL_VIRAL",
            cost=5000,
            buzz_min=150,
            buzz_max=300,
            cred_bonus=20,
            fame_bonus=50,
            description="High-definition cinematic music video promotion.",
        ),
        "tiktok_viral_push": MarketingCampaign(
            campaign_id="tiktok_viral_push",
            name="Short-Form Video Viral Audio Campaign",
            category="DIGITAL_VIRAL",
            cost=800,
            buzz_min=30,
            buzz_max=90,
            cred_bonus=5,
            fame_bonus=15,
            description="Seeding 30-second song audio clips with 50 creators on TikTok & Instagram Reels.",
        ),
        "times_square_billboard": MarketingCampaign(
            campaign_id="times_square_billboard",
            name="Times Square & Sunset Blvd Digital Billboard Takeover",
            category="BILLBOARD",
            cost=35000,
            buzz_min=350,
            buzz_max=600,
            cred_bonus=25,
            fame_bonus=100,
            description="Towering 8-story 4K digital billboard ad running in Times Square NYC and Sunset Blvd LA.",
        ),
        "tastemaker_radio_push": MarketingCampaign(
            campaign_id="tastemaker_radio_push",
            name="NPR Music & BBC 6 Music Editorial Radio Push",
            category="RADIO",
            cost=4000,
            buzz_min=120,
            buzz_max=220,
            cred_bonus=35,
            fame_bonus=40,
            description="Targeted radio servicing to legendary tastemaker DJs in Seattle (KEXP), London (BBC), and Philly (WXPN).",
        ),
        "guerrilla_street_team": MarketingCampaign(
            campaign_id="guerrilla_street_team",
            name="Guerrilla Flyering & Wheat-Paste Poster Drive",
            category="STREET_TEAM",
            cost=600,
            buzz_min=25,
            buzz_max=60,
            cred_bonus=20,
            fame_bonus=10,
            description="Plastering 2,000 screen-printed tour posters outside iconic music venues and record shops.",
        ),
        "provocative_pr_stunt": MarketingCampaign(
            campaign_id="provocative_pr_stunt",
            name="Guerilla Rooftop Unannounced Pop-Up Stunt",
            category="PR_STUNT",
            cost=2500,
            buzz_min=50,
            buzz_max=250,
            cred_bonus=15,
            fame_bonus=60,
            description="Unannounced rooftop concert halting city traffic and going viral on live streams.",
        ),
    }

    @classmethod
    def launch_campaign(cls, player, song, campaign_key: str) -> Dict[str, Any]:
        camp = cls.CAMPAIGNS.get(campaign_key)
        if not camp:
            # Fallback to CAMPAIGN_TYPES
            dict_camp = CAMPAIGN_TYPES.get(campaign_key)
            if not dict_camp:
                return {"ok": False, "explanation": "Marketing campaign not found."}
            camp = MarketingCampaign(
                campaign_id=campaign_key,
                name=dict_camp["name"],
                category="GENERAL",
                cost=dict_camp["cost"],
                buzz_min=dict_camp.get("buzz_gain_min", 10),
                buzz_max=dict_camp.get("buzz_gain_max", 30),
                cred_bonus=5,
                fame_bonus=10,
                description=dict_camp["name"],
            )

        if player.money < camp.cost:
            return {"ok": False, "explanation": f"Need ${camp.cost:,} to launch {camp.name}."}

        player.money -= camp.cost
        buzz_earned = random.randint(camp.buzz_min, camp.buzz_max)
        song.buzz_score = getattr(song, "buzz_score", 0) + buzz_earned
        player.fame = min(1000, player.fame + camp.fame_bonus)
        player.street_cred = min(100, player.street_cred + camp.cred_bonus)

        summary = (
            f"📣 LAUNCHED MARKETING CAMPAIGN: {camp.name}!\n"
            f"- Targeted Single: '{song.title}'\n"
            f"- Campaign Investment: -${camp.cost:,}\n"
            f"- Buzz Generated: +{buzz_earned} Buzz Points (Total Song Buzz: {song.buzz_score})\n"
            f"- Cultural Reach: +{camp.fame_bonus} Fame, +{camp.cred_bonus} Street Cred"
        )
        return {"ok": True, "buzz": buzz_earned, "campaign": camp, "explanation": summary}


def run_marketing_campaign(campaign_type: str, song):
    data = CAMPAIGN_TYPES.get(campaign_type)
    if not data:
        return 0, "Invalid campaign."

    buzz = random.randint(data['buzz_gain_min'], data['buzz_gain_max'])
    song.buzz_score = getattr(song, "buzz_score", 0) + buzz

    msg = f"Campaign '{data['name']}' complete. Generated {buzz} buzz for '{song.title}'."
    if buzz < 0:
        msg = f"Campaign '{data['name']}' backfired! Lost {-buzz} buzz."

    return buzz, msg
