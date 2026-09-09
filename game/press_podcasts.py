from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class PublicPersonaProfile:
    auteur_score: int = 20        # Focus on artistic genius and studio perfectionism
    working_class_score: int = 20 # Focus on authenticity, roots, and blue-collar fans
    maverick_score: int = 20      # Focus on rebellion, anti-corporate edge, controversy
    total_podcasts_done: int = 0


class PressPodcastsSystem:
    """Manages long-form music podcast appearances and public persona development."""

    PODCAST_SHOWS = {
        "song_exploder": {
            "name": "Song Exploder Masterclass Podcast",
            "host": "Hrishikesh Hirway style host",
            "focus": "Deconstructing individual master tracks stem-by-stem.",
            "min_fame": 40,
        },
        "zane_lowe_deep_dive": {
            "name": "Apple Music Global 1-on-1 Interview",
            "host": "Zane Lowe style host",
            "focus": "High-energy career retrospectives and creative breakthroughs.",
            "min_fame": 75,
        },
        "maron_garage_talk": {
            "name": "WTF Garage Long-Form Conversation",
            "host": "Marc Maron style host",
            "focus": "Raw, funny, existential talk about neurosis, early struggles, and vinyl.",
            "min_fame": 60,
        },
    }

    def __init__(self):
        self.persona = PublicPersonaProfile()
        self.podcast_history: List[Dict[str, Any]] = []

    def guest_on_podcast(self, player, show_key: str, answer_style: str = "auteur") -> Dict[str, Any]:
        """
        answer_style:
        - "auteur": Deep technical talk about tape saturation, harmonics, and artistic vision (+15 Auteur, +10 Fame)
        - "working_class": Humble talk about paying dues, touring in broken vans, and fan gratitude (+15 Working Class, +15 Cred)
        - "maverick": Roasting major label greed, streaming pennies, and mainstream pop cliches (+15 Maverick, +10 Cred, +15 Fame)
        """
        show = self.PODCAST_SHOWS.get(show_key)
        if not show:
            return {"ok": False, "explanation": "Podcast show not found."}

        if getattr(player, "fame", 0) < show["min_fame"]:
            return {"ok": False, "explanation": f"Podcast bookers require at least {show['min_fame']} Fame."}

        self.persona.total_podcasts_done += 1

        if answer_style == "auteur":
            self.persona.auteur_score += 15
            player.fame = min(1000, player.fame + 15)
            player.street_cred = min(100, player.street_cred + 5)
            msg = f"🎙️ Deep artistic discussion on '{show['name']}'. Listeners hailed your technical genius and uncompromising vision (+15 Sonic Auteur)."

        elif answer_style == "working_class":
            self.persona.working_class_score += 15
            player.street_cred = min(100, player.street_cred + 15)
            player.fame = min(1000, player.fame + 10)
            msg = f"🎙️ Grounded, honest conversation on '{show['name']}'. Fans connected deeply with your authentic working-class journey (+15 Working Class Hero)."

        else: # maverick
            self.persona.maverick_score += 15
            player.street_cred = min(100, player.street_cred + 12)
            player.fame = min(1000, player.fame + 20)
            msg = f"🎙️ Outspoken firestorm on '{show['name']}'! Your critique of music industry gatekeepers went viral on social media (+15 Outspoken Maverick)."

        record = {
            "show_name": show["name"],
            "answer_style": answer_style,
            "day": current_game_time.day,
        }
        self.podcast_history.append(record)

        return {"ok": True, "record": record, "explanation": msg}
