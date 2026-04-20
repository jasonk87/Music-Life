from dataclasses import dataclass, field
from typing import Dict, Optional
import random

from game.world_memory import WorldMemoryEntry
from game.game_time import current_game_time


@dataclass
class DelegationRole:
    role_type: str
    active: bool = True
    upkeep: int = 0
    competence: float = 0.5
    reliability: float = 0.5
    experience: float = 0.5
    available: bool = True
    modifiers: Dict[str, float] = field(default_factory=dict)


class DelegationSystem:
    DEFAULTS = {
        "manager": {"upkeep": 150, "competence": 0.62, "reliability": 0.65, "experience": 0.58},
        "assistant": {"upkeep": 90, "competence": 0.58, "reliability": 0.62, "experience": 0.55},
        "security": {"upkeep": 120, "competence": 0.6, "reliability": 0.7, "experience": 0.6},
        "driver": {"upkeep": 110, "competence": 0.6, "reliability": 0.68, "experience": 0.57},
    }

    def ensure_player_support(self, player):
        if not hasattr(player, "delegation_roles"):
            player.delegation_roles = {}

    def add_or_update_role(self, player, role_type: str, active=True, competence=None, reliability=None, upkeep=None, experience=None):
        self.ensure_player_support(player)
        base = self.DEFAULTS.get(role_type, {"upkeep": 100, "competence": 0.5, "reliability": 0.5, "experience": 0.5})
        c = competence if competence is not None else base["competence"]
        r = reliability if reliability is not None else base["reliability"]
        e = experience if experience is not None else base["experience"]
        quality = max(0.0, min(1.0, (c * 0.45) + (r * 0.35) + (e * 0.20)))
        scaled_upkeep = upkeep if upkeep is not None else int(base["upkeep"] * (0.7 + quality))
        role = DelegationRole(
            role_type=role_type,
            active=active,
            upkeep=scaled_upkeep,
            competence=c,
            reliability=r,
            experience=e,
        )
        role.modifiers.setdefault("quality_tier", "high" if quality >= 0.78 else "mid" if quality >= 0.55 else "low")
        if role_type == "security":
            role.modifiers.setdefault("posture", "filtered")
        player.delegation_roles[role_type] = role
        return role

    def role_quality(self, role: DelegationRole) -> float:
        return max(0.0, min(1.0, (role.competence * 0.45) + (role.reliability * 0.35) + (role.experience * 0.20)))

    def get_role(self, player, role_type: str) -> Optional[DelegationRole]:
        self.ensure_player_support(player)
        role = player.delegation_roles.get(role_type)
        if role and role.active and role.available:
            return role
        return None

    def manager_opportunity_bias(self, player, visibility_bias: float, reliability_bias: float):
        role = self.get_role(player, "manager")
        if not role:
            return 0, None

        quality = self.role_quality(role)
        bonus = int((quality * 18) + max(0, visibility_bias / 8) + max(0, reliability_bias / 10))

        failure_hook = None
        overload = max(0.0, (visibility_bias / 60.0) + (max(0, reliability_bias) / 70.0))
        fail_threshold = min(0.96, role.reliability + role.experience * 0.15 - overload * 0.25)
        if random.random() > max(0.08, fail_threshold):
            failure_hook = "manager_overbooked_pressure"
        return bonus, failure_hook

    def assistant_adjust_requirements(self, player, assessment, location_ref: Optional[str], world_memory=None):
        role = self.get_role(player, "assistant")
        if not role or not assessment:
            return assessment, None

        quality = self.role_quality(role)
        success_chance = min(0.985, role.competence * 0.52 + role.reliability * 0.33 + role.experience * 0.25)
        failure_chance = max(0.01, (1.0 - quality) * 0.22)

        hook = None
        # Rescue recoverable misses.
        if assessment.status in {"missing_but_recoverable", "partially_satisfied"} and assessment.missing:
            if random.random() <= success_chance:
                assessment.missing_recoverable.clear()
                assessment.missing.clear()
                assessment.status = "fully_satisfied"
                hook = "assistant_success"
            elif random.random() <= failure_chance:
                hook = "assistant_prep_failure"

        if world_memory and hook:
            world_memory.add(
                WorldMemoryEntry(
                    event_type=hook,
                    involved_entities=[player.name],
                    location=location_ref,
                    timestamp=current_game_time.copy(),
                    tags=["delegation", "assistant"],
                    impact_score=1.8 if hook == "assistant_success" else 2.2,
                    source_key=f"{hook}:{player.name}:{current_game_time.get_time_string_for_schedule()}:{location_ref}",
                )
            )

        return assessment, hook

    def security_adjust_visibility_pressure(self, player, base_pressure: float, world_memory=None, location_ref: Optional[str] = None):
        role = self.get_role(player, "security")
        if not role:
            return base_pressure

        quality = self.role_quality(role)
        posture = role.modifiers.get("posture", "filtered")
        posture_mult = {"open": 0.7, "filtered": 1.0, "locked": 1.25}.get(posture, 1.0)
        reduction = min(0.78, (0.12 + quality * 0.52) * posture_mult)
        adjusted = max(0.0, base_pressure * (1.0 - reduction))

        if world_memory and base_pressure - adjusted > 1.0:
            world_memory.add(
                WorldMemoryEntry(
                    event_type="security_prevented_escalation",
                    involved_entities=[player.name],
                    location=location_ref,
                    timestamp=current_game_time.copy(),
                    tags=["delegation", "security"],
                    impact_score=1.6,
                    source_key=f"security:{player.name}:{current_game_time.get_time_string_for_schedule()}:{location_ref}",
                )
            )
            if posture in {"filtered", "locked"} and base_pressure > 12:
                world_memory.add(
                    WorldMemoryEntry(
                        event_type="security_filtered_crowd",
                        involved_entities=[player.name],
                        location=location_ref,
                        timestamp=current_game_time.copy(),
                        tags=["delegation", "security", "interference"],
                        impact_score=1.5,
                        source_key=f"security_filtered:{player.name}:{current_game_time.get_time_string_for_schedule()}:{location_ref}:{posture}",
                    )
                )
        return adjusted

    def driver_adjust_trip(self, player, travel_minutes: int, stress_cost: float = 1.0, world_memory=None, location_ref: Optional[str] = None):
        role = self.get_role(player, "driver")
        if not role:
            return travel_minutes, stress_cost, None

        reliability = role.reliability
        efficiency = role.competence
        quality = self.role_quality(role)
        failure_hook = None

        if random.random() > min(0.98, reliability + role.experience * 0.12):
            failure_hook = "driver_unavailable"
            adjusted_minutes = int(travel_minutes * 1.05)
            stress_mult = stress_cost * 1.05
        else:
            adjusted_minutes = int(travel_minutes * (1.0 - (0.06 + efficiency * 0.14 + quality * 0.08)))
            stress_mult = stress_cost * (1.0 - (0.12 + reliability * 0.16 + quality * 0.1))
            failure_hook = "driver_improved_trip_outcome"

        adjusted_minutes = max(5, adjusted_minutes)
        stress_mult = max(0.5, stress_mult)

        if world_memory and failure_hook:
            world_memory.add(
                WorldMemoryEntry(
                    event_type=failure_hook,
                    involved_entities=[player.name],
                    location=location_ref,
                    timestamp=current_game_time.copy(),
                    tags=["delegation", "driver"],
                    impact_score=1.4,
                    source_key=f"driver:{failure_hook}:{player.name}:{current_game_time.get_time_string_for_schedule()}:{location_ref}",
                )
            )

        return adjusted_minutes, stress_mult, failure_hook

    def set_security_posture(self, player, posture: str):
        role = self.get_role(player, "security")
        if not role:
            return False
        if posture not in {"open", "filtered", "locked"}:
            return False
        role.modifiers["posture"] = posture
        return True

    def assistant_plan_lodging(self, player, scarcity_system, game, city: str, preferred_tier: str, lead_hours: int, world_memory=None, rng=None):
        role = self.get_role(player, "assistant")
        quality = self.role_quality(role) if role else 0.0
        effective_lead = lead_hours + int(quality * 18)
        outcome = scarcity_system.attempt_hotel_booking(
            game=game,
            city=city,
            preferred_tier=preferred_tier,
            lead_hours=effective_lead,
            assistant_quality=quality,
            world_memory=world_memory,
            rng=rng,
        )

        if world_memory and role and outcome.success:
            world_memory.add(
                WorldMemoryEntry(
                    event_type="assistant_secured_booking" if quality >= 0.65 else "assistant_low_quality_booking",
                    involved_entities=[player.name],
                    location=city,
                    timestamp=current_game_time.copy(),
                    tags=["delegation", "assistant", "logistics"],
                    impact_score=1.4 if quality >= 0.65 else 1.9,
                    source_key=f"assistant_hotel:{player.name}:{city}:{current_game_time.get_time_string_for_schedule()}:{outcome.booked_tier}:{quality:.2f}",
                )
            )
        return outcome
