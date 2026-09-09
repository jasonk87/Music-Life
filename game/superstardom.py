from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random

from game.game_time import current_game_time
from game.rivals import add_news


@dataclass
class RecordPlaque:
    title: str
    artist: str
    cert_type: str  # "Gold", "Platinum", "Diamond"
    sales_units: int
    date_awarded: str


class SuperstardomSystem:
    CERT_THRESHOLDS = {
        "Gold": 50000,
        "Platinum": 100000,
        "Diamond": 500000,
    }

    def __init__(self, game):
        self.game = game
        self.plaques: List[RecordPlaque] = []
        self.awards_won: List[str] = []

    def check_certifications(self, player) -> List[RecordPlaque]:
        new_plaques = []
        # Check songs
        for song in getattr(player, "songs_written", []):
            if not getattr(song, "is_released", False):
                continue
            sales = getattr(song, "sales_units", int(getattr(song, "buzz_score", 0) * 1500 + getattr(player, "fame", 0) * 500))
            song.sales_units = sales

            for cert, threshold in self.CERT_THRESHOLDS.items():
                if sales >= threshold and not any(p.title == song.title and p.cert_type == cert for p in self.plaques):
                    plaque = RecordPlaque(
                        title=song.title,
                        artist=player.name,
                        cert_type=cert,
                        sales_units=sales,
                        date_awarded=current_game_time.get_time_string_for_schedule(),
                    )
                    self.plaques.append(plaque)
                    new_plaques.append(plaque)
                    player.fame += 25 if cert == "Gold" else 60 if cert == "Platinum" else 150
                    add_news(f"CERTIFICATION: '{song.title}' by {player.name} has officially been certified {cert.upper()}!")

        return new_plaques

    def run_annual_music_awards(self, player) -> Optional[Dict]:
        if current_game_time.month != 12 or current_game_time.day != 28:
            return None

        released_songs = [s for s in getattr(player, "songs_written", []) if getattr(s, "is_released", False)]
        if not released_songs:
            return None

        best_song = max(released_songs, key=lambda s: getattr(s, "song_quality", 0.5) * 0.6 + getattr(s, "buzz_score", 0) * 0.4)
        score = getattr(best_song, "song_quality", 0.5) * 50 + getattr(player, "fame", 0) * 0.3

        if score >= 45: # Winning threshold
            award_name = "Indie Music Award: Song of the Year"
            self.awards_won.append(award_name)
            player.fame += 80
            player.money += 3000
            player.street_cred = min(100, getattr(player, "street_cred", 50) + 15)
            add_news(f"AWARDS: {player.name} WON '{award_name}' for '{best_song.title}'!")
            return {
                "won": True,
                "award": award_name,
                "song_title": best_song.title,
                "prize_money": 3000,
                "fame_reward": 80,
                "explanation": f"CONGRATULATIONS! You won '{award_name}' for '{best_song.title}'! +$3,000 Prize Money, +80 Fame, +15 Street Cred!",
            }
        else:
            return {
                "won": False,
                "award": "Indie Music Award Nomination",
                "song_title": best_song.title,
                "explanation": f"Nominated for Song of the Year with '{best_song.title}', but fell short of the top trophy. Keep creating!",
            }
