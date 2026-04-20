from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional
import random

from game.game_time import current_game_time
from game.world_memory import WorldMemoryEntry


@dataclass
class HotelBookingOutcome:
    success: bool
    city: str
    booked_tier: Optional[str]
    preferred_tier: str
    downgraded: bool
    price_multiplier: float
    event_type: Optional[str]
    notes: str = ""


class ScarcityAvailabilitySystem:
    """Reusable scarcity model; hotels are first-class but schema is extensible."""

    TIER_ORDER = ["budget", "standard", "premium"]

    def __init__(self):
        self.city_profiles: Dict[str, Dict] = {
            "Austin": {"inventory": {"budget": 18, "standard": 14, "premium": 8}, "base_demand": 1.0},
            "Los Angeles": {"inventory": {"budget": 26, "standard": 22, "premium": 14}, "base_demand": 1.18},
            "Nashville": {"inventory": {"budget": 15, "standard": 12, "premium": 7}, "base_demand": 1.06},
        }

    def _city_profile(self, city: str) -> Dict:
        return self.city_profiles.get(city, {"inventory": {"budget": 10, "standard": 8, "premium": 4}, "base_demand": 1.0})

    def demand_pressure(self, game, city: str) -> float:
        profile = self._city_profile(city)
        pressure = profile["base_demand"]

        # Local memory activity
        if hasattr(game, "world_memory"):
            recent = [e for e in game.world_memory.entries[-30:] if e.location in {city, None}]
            pressure += min(0.55, len(recent) * 0.015)

        # Visibility pressure for player in city
        if hasattr(game, "visibility_system") and hasattr(game, "player") and game.player:
            vis = game.visibility_system.get_visibility(game.player.name, city)
            pressure += min(0.7, vis.get("public_visibility", 0.0) / 40.0)
        if hasattr(game, "life_flow"):
            pressure *= game.life_flow.effective_pressure_multiplier()

        return max(0.75, pressure)

    def check_hotel_availability(
        self,
        city: str,
        tier: str,
        lead_hours: int,
        demand_pressure: float,
        assistant_quality: float = 0.0,
        rng: Optional[random.Random] = None,
    ) -> Dict:
        rng = rng or random
        profile = self._city_profile(city)
        inventory = profile["inventory"].get(tier, 0)

        lead_bonus = min(0.35, max(0.0, lead_hours / 72.0) * 0.35)
        quality_bonus = min(0.32, max(0.0, assistant_quality) * 0.32)
        scarcity_penalty = min(0.82, demand_pressure * 0.5)

        score = (inventory / 30.0) + lead_bonus + quality_bonus - scarcity_penalty
        roll = rng.random()
        available = roll <= max(0.05, min(0.95, score + 0.45))
        return {
            "available": available,
            "score": score,
            "roll": roll,
            "price_multiplier": max(1.0, 0.92 + demand_pressure * 0.3 - quality_bonus * 0.15),
        }

    def attempt_hotel_booking(
        self,
        game,
        city: str,
        preferred_tier: str,
        lead_hours: int,
        assistant_quality: float = 0.0,
        world_memory=None,
        rng: Optional[random.Random] = None,
    ) -> HotelBookingOutcome:
        rng = rng or random
        pressure = self.demand_pressure(game, city)

        tier_idx = self.TIER_ORDER.index(preferred_tier) if preferred_tier in self.TIER_ORDER else 1
        attempted_tiers = [self.TIER_ORDER[tier_idx]] + self.TIER_ORDER[:tier_idx][::-1]

        for tier in attempted_tiers:
            result = self.check_hotel_availability(
                city,
                tier,
                lead_hours=lead_hours,
                demand_pressure=pressure,
                assistant_quality=assistant_quality,
                rng=rng,
            )
            if result["available"]:
                downgraded = tier != preferred_tier
                event_type = "hotel_downgraded" if downgraded else "hotel_booked"
                if world_memory and hasattr(game, "player"):
                    world_memory.add(
                        WorldMemoryEntry(
                            event_type=event_type,
                            involved_entities=[game.player.name],
                            location=city,
                            timestamp=current_game_time.copy(),
                            tags=["logistics", "lodging"],
                            impact_score=1.2 if not downgraded else 1.8,
                            source_key=f"{event_type}:{game.player.name}:{city}:{current_game_time.get_time_string_for_schedule()}:{tier}",
                        )
                    )
                return HotelBookingOutcome(
                    success=True,
                    city=city,
                    booked_tier=tier,
                    preferred_tier=preferred_tier,
                    downgraded=downgraded,
                    price_multiplier=float(result["price_multiplier"]),
                    event_type=event_type,
                    notes="manual_or_assisted",
                )

        if world_memory and hasattr(game, "player"):
            world_memory.add(
                WorldMemoryEntry(
                    event_type="hotel_unavailable",
                    involved_entities=[game.player.name],
                    location=city,
                    timestamp=current_game_time.copy(),
                    tags=["logistics", "lodging"],
                    impact_score=2.1,
                    source_key=f"hotel_unavailable:{game.player.name}:{city}:{current_game_time.get_time_string_for_schedule()}",
                )
            )

        return HotelBookingOutcome(
            success=False,
            city=city,
            booked_tier=None,
            preferred_tier=preferred_tier,
            downgraded=False,
            price_multiplier=max(1.0, 1.0 + pressure * 0.35),
            event_type="hotel_unavailable",
            notes="no_inventory",
        )


class PublicInterferenceSystem:
    """Visibility + place + crowd pressure model with security posture integration."""

    def interference_pressure(
        self,
        base_visibility: float,
        place_type: str,
        crowd_level: str,
        security_quality: float = 0.0,
        security_posture: str = "filtered",
    ) -> float:
        place_mult = 1.0
        if place_type in {"downtown", "transport", "venue", "street", "airport"}:
            place_mult = 1.2

        crowd_mult = {"low": 0.9, "medium": 1.0, "high": 1.25}.get(crowd_level, 1.0)
        posture_mult = {"open": 1.12, "filtered": 0.88, "locked": 0.62}.get(security_posture, 0.88)

        raw = base_visibility * place_mult * crowd_mult * posture_mult
        reduction = min(0.45, max(0.0, security_quality) * 0.42)
        return max(0.0, raw * (1.0 - reduction))
