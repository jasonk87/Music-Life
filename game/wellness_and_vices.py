from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class MusicianHealthProfile:
    addiction_meter: float = 0.0          # 0.0 to 100.0
    vocal_fatigue: float = 0.0            # 0.0 to 100.0 (high fatigue risks nodules)
    sobriety_streak_days: int = 0
    is_in_rehab: bool = False
    rehab_days_left: int = 0
    vocal_coaching_level: int = 0         # 0 to 5
    lifelong_stamina_bonus: float = 0.0   # Earned through clean living and coaching


class WellnessAndVicesSystem:
    """Manages musician backstage vices, addiction, vocal health, rehab, and sobriety streaks."""

    def __init__(self):
        self.profile = MusicianHealthProfile()

    def choose_backstage_lifestyle(self, player, choice: str) -> Dict[str, Any]:
        """
        Choices:
        - "wild_party": Backstage drinks & late-night partying (+30 Energy, +15 Hype, +12 Addiction, +15 Vocal Fatigue)
        - "vocal_warmup_tea": Herbal tea, vocal scales, and meditation (+20 Vocal Stamina, -15 Stress, +1 Sobriety Day)
        - "moderate_socialize": One drink with bandmates (+10 Energy, -5 Stress, +2 Addiction)
        """
        if choice == "wild_party":
            player.energy = min(100, player.energy + 30)
            player.stress = max(0, player.stress - 10)
            self.profile.addiction_meter = min(100.0, self.profile.addiction_meter + 12.0)
            self.profile.vocal_fatigue = min(100.0, self.profile.vocal_fatigue + 15.0)
            self.profile.sobriety_streak_days = 0

            return {
                "ok": True,
                "choice": "wild_party",
                "explanation": "🍾 Wild backstage party! Gained +30 Energy and crowd hype, but gained +12 Addiction and +15 Vocal Fatigue.",
            }

        elif choice == "vocal_warmup_tea":
            player.stress = max(0, player.stress - 15)
            self.profile.vocal_fatigue = max(0.0, self.profile.vocal_fatigue - 20.0)
            self.profile.addiction_meter = max(0.0, self.profile.addiction_meter - 3.0)
            self.profile.sobriety_streak_days += 1

            if self.profile.sobriety_streak_days % 30 == 0:
                self.profile.lifelong_stamina_bonus += 0.05
                bonus_msg = f" 🌟 SOBRIETY MILESTONE: {self.profile.sobriety_streak_days} days clean! Earned +5% permanent vocal stamina!"
            else:
                bonus_msg = ""

            return {
                "ok": True,
                "choice": "vocal_warmup_tea",
                "explanation": f"🍵 Calming vocal warmup with herbal throat-coat tea. Reduced vocal fatigue by 20 and lowered stress!{bonus_msg}",
            }

        elif choice == "moderate_socialize":
            player.energy = min(100, player.energy + 10)
            player.stress = max(0, player.stress - 5)
            self.profile.addiction_meter = min(100.0, self.profile.addiction_meter + 2.0)
            return {
                "ok": True,
                "choice": "moderate_socialize",
                "explanation": "🥂 Relaxed post-show cheers with the band (+10 Energy, -5 Stress).",
            }
        else:
            return {"ok": False, "explanation": "Unknown backstage choice."}

    def attend_vocal_coaching(self, player) -> Dict[str, Any]:
        cost = 350
        if player.money < cost:
            return {"ok": False, "explanation": f"Vocal coaching lesson costs ${cost}."}

        player.money -= cost
        self.profile.vocal_coaching_level = min(5, self.profile.vocal_coaching_level + 1)
        self.profile.vocal_fatigue = max(0.0, self.profile.vocal_fatigue - 25.0)
        self.profile.lifelong_stamina_bonus += 0.05

        return {
            "ok": True,
            "level": self.profile.vocal_coaching_level,
            "explanation": f"🎙️ Mastered diaphragmatic breath support with vocal coach! (Level {self.profile.vocal_coaching_level}/5, +5% permanent stamina).",
        }

    def check_in_rehab_clinic(self, player) -> Dict[str, Any]:
        cost = 4500
        if player.money < cost:
            return {"ok": False, "explanation": f"Inpatient wellness and rehab clinic requires ${cost:,}."}

        player.money -= cost
        self.profile.is_in_rehab = True
        self.profile.rehab_days_left = 7
        self.profile.addiction_meter = 0.0
        self.profile.vocal_fatigue = 0.0
        self.profile.sobriety_streak_days = 7
        player.health = 100
        player.energy = 100

        return {
            "ok": True,
            "explanation": f"🏥 Checked into holistic music wellness retreat for a 7-day program. Full detox complete, addiction reset to 0!",
        }
