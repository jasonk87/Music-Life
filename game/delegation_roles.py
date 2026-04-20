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
    available: bool = True
    modifiers: Dict[str, float] = field(default_factory=dict)


class DelegationSystem:
    DEFAULTS = {
        "manager": {"upkeep": 150, "competence": 0.62, "reliability": 0.65},
        "assistant": {"upkeep": 90, "competence": 0.58, "reliability": 0.62},
        "security": {"upkeep": 120, "competence": 0.6, "reliability": 0.7},
        "driver": {"upkeep": 110, "competence": 0.6, "reliability": 0.68},
    }

    def ensure_player_support(self, player):
        if not hasattr(player, "delegation_roles"):
            player.delegation_roles = {}

    def add_or_update_role(self, player, role_type: str, active=True, competence=None, reliability=None, upkeep=None):
        self.ensure_player_support(player)
        base = self.DEFAULTS.get(role_type, {"upkeep": 100, "competence": 0.5, "reliability": 0.5})
        role = DelegationRole(
            role_type=role_type,
            active=active,
            upkeep=upkeep if upkeep is not None else base["upkeep"],
            competence=competence if competence is not None else base["competence"],
            reliability=reliability if reliability is not None else base["reliability"],
        )
        player.delegation_roles[role_type] = role
        return role

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

        quality = (role.competence + role.reliability) / 2.0
        bonus = int((quality * 12) + max(0, visibility_bias / 8) + max(0, reliability_bias / 10))

        failure_hook = None
        if random.random() > role.reliability:
            failure_hook = "manager_overbooked_pressure"
        return bonus, failure_hook

    def assistant_adjust_requirements(self, player, assessment, location_ref: Optional[str], world_memory=None):
        role = self.get_role(player, "assistant")
        if not role or not assessment:
            return assessment, None

        success_chance = min(0.96, role.competence * 0.6 + role.reliability * 0.45)
        failure_chance = max(0.02, (1.0 - role.reliability) * 0.35)

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

        reduction = min(0.55, 0.15 + role.competence * 0.35 + role.reliability * 0.15)
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
        return adjusted

    def driver_adjust_trip(self, player, travel_minutes: int, stress_cost: float = 1.0, world_memory=None, location_ref: Optional[str] = None):
        role = self.get_role(player, "driver")
        if not role:
            return travel_minutes, stress_cost, None

        reliability = role.reliability
        efficiency = role.competence
        failure_hook = None

        if random.random() > reliability:
            failure_hook = "driver_unavailable"
            adjusted_minutes = int(travel_minutes * 1.05)
            stress_mult = stress_cost * 1.05
        else:
            adjusted_minutes = int(travel_minutes * (1.0 - (0.08 + efficiency * 0.18)))
            stress_mult = stress_cost * (1.0 - (0.15 + reliability * 0.2))
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
