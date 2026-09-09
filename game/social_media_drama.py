from typing import Dict, Optional
import random

from game.rivals import add_news


class SocialMediaDramaSystem:
    SCANDAL_TYPES = {
        "stage_mishap": {
            "title": "Stage Equipment Collapse",
            "description": "A video of your amplifier collapsing on stage went viral on social media!",
            "buzz_gain": 25,
            "street_cred_change": -3,
            "fame_gain": 8,
        },
        "acoustic_clip": {
            "title": "Viral Alleyway Acoustic Jam",
            "description": "A fan recorded a raw 30-second clip of you jamming behind the venue. It blew up online!",
            "buzz_gain": 40,
            "street_cred_change": 10,
            "fame_gain": 18,
        },
        "overnight_feud": {
            "title": "Social Media Feud",
            "description": "A rival artist posted a call-out dissing your latest single.",
            "buzz_gain": 20,
            "street_cred_change": -5,
            "fame_gain": 12,
        },
    }

    def maybe_trigger_viral_moment(self, player) -> Optional[Dict]:
        if random.random() < 0.18:
            scandal_key = random.choice(list(self.SCANDAL_TYPES.keys()))
            data = self.SCANDAL_TYPES[scandal_key]

            player.fame += data["fame_gain"]
            player.street_cred = max(0, min(100, getattr(player, "street_cred", 50) + data["street_cred_change"]))

            if getattr(player, "songs_written", None):
                strongest = max(player.songs_written, key=lambda s: s.song_quality)
                strongest.buzz_score += data["buzz_gain"]

            add_news(f"VIRAL: {data['title']} — {data['description']}")
            return {"key": scandal_key, **data}
        return None

    def resolve_pr_press_conference(self, player, choice: str) -> Dict:
        if choice == "apologize":
            player.street_cred = max(0, getattr(player, "street_cred", 50) - 5)
            player.fame += 5
            add_news(f"PRESS: {player.name} issued a formal public apology.")
            return {"explanation": "You issued a polite PR apology. Street Cred dropped slightly, but mainstream press was pacified."}
        elif choice == "lean_in":
            player.street_cred = min(100, getattr(player, "street_cred", 50) + 8)
            player.fame += 15
            add_news(f"PRESS: {player.name} leaned into the controversy, firing back at critics!")
            return {"explanation": "You leaned into the drama! Underground fans loved the defiance (+8 Street Cred, +15 Fame)."}
        else:
            add_news(f"PRESS: {player.name} declined to comment on recent media chatter.")
            return {"explanation": "You ignored the press noise. The news cycle moved on."}
