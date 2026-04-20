from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from game.game_time import current_game_time


@dataclass
class LifeFlowSnapshot:
    intensity: float
    recent_pressure: float
    density_load: float
    collision_allowance: float
    event_density_target: float
    in_recovery_window: bool
    support_stability: float


class LifeFlowOrchestrator:
    """Simulation-first pacing layer that biases pressure timing and overlap.

    The orchestrator never invents content. It only shapes when existing pressures
    should cluster or spread by using world/player state and recent load.
    """

    def __init__(self, game):
        self.game = game
        self.pressure_log: List[Tuple[int, str, float]] = []
        self.recovery_until_day: int = -1
        self.last_snapshot: Optional[LifeFlowSnapshot] = None

    def _day_index(self) -> int:
        return current_game_time.year * 360 + current_game_time.month * 30 + current_game_time.day

    def record_pressure(self, source: str, magnitude: float):
        if magnitude <= 0:
            return
        self.pressure_log.append((self._day_index(), source, float(magnitude)))
        if len(self.pressure_log) > 240:
            self.pressure_log = self.pressure_log[-240:]

    def _recent_pressure(self, lookback_days: int = 7) -> float:
        today = self._day_index()
        total = 0.0
        for day_idx, _, magnitude in reversed(self.pressure_log):
            delta = today - day_idx
            if delta < 0:
                continue
            if delta > lookback_days:
                break
            decay = max(0.2, 1.0 - (delta * 0.12))
            total += magnitude * decay
        return total

    def _scheduled_density(self, horizon_days: int = 2) -> float:
        player = getattr(self.game, "player", None)
        if not player or not hasattr(player, "schedule"):
            return 0.0
        now = current_game_time.copy()
        events = player.schedule.get_upcoming_events(now, limit=30)
        end_idx = self._day_index() + horizon_days
        in_window = 0
        for item in events:
            item_idx = item.start_time.year * 360 + item.start_time.month * 30 + item.start_time.day
            if item_idx <= end_idx and item.requires_presence():
                in_window += 1
        return float(in_window)

    def _support_stability(self) -> float:
        player = getattr(self.game, "player", None)
        delegation = getattr(self.game, "delegation_system", None)
        if not player or not delegation:
            return 0.0

        weights = {"assistant": 0.32, "manager": 0.26, "security": 0.2, "driver": 0.22}
        score = 0.0
        for role_name, weight in weights.items():
            role = delegation.get_role(player, role_name)
            if not role:
                continue
            score += delegation.role_quality(role) * weight
        return max(0.0, min(1.0, score))

    def _stage_pressure(self) -> float:
        player = getattr(self.game, "player", None)
        if not player:
            return 0.0

        fame = max(0.0, min(1.0, getattr(player, "fame", 0) / 120.0))

        city = player.current_location.name if player.current_location else None
        vis = 0.0
        if hasattr(self.game, "visibility_system"):
            vis = self.game.visibility_system.get_visibility(player.name, city).get("public_visibility", 0.0)
        vis_norm = max(0.0, min(1.0, vis / 35.0))

        contract_count = 0
        if hasattr(self.game, "organization_contracts"):
            contract_count = len(self.game.organization_contracts.active_contracts_for(player.name))
        contract_load = min(1.0, contract_count / 3.0)

        project_load = 0.0
        if hasattr(self.game, "production_pipeline"):
            active = [p for p in self.game.production_pipeline.projects.values() if p.lead_artist_id == player.name and p.status == "active"]
            project_load = min(1.0, len(active) / 3.0)
            if any(p.current_stage in {"ready_for_release", "released"} for p in active):
                project_load = min(1.0, project_load + 0.2)

        contact_load = 0.0
        if hasattr(self.game, "NPC_REGISTRY"):
            contact_load = min(1.0, len(self.game.NPC_REGISTRY) / 18.0)

        return (fame * 0.22) + (vis_norm * 0.3) + (contract_load * 0.22) + (project_load * 0.18) + (contact_load * 0.08)

    def snapshot(self) -> LifeFlowSnapshot:
        recent = self._recent_pressure()
        density = self._scheduled_density()
        stage = self._stage_pressure()
        support = self._support_stability()

        in_recovery = self._day_index() <= self.recovery_until_day
        recovery_penalty = 0.22 if in_recovery else 0.0

        intensity = max(0.0, min(1.0, stage + min(0.35, recent / 20.0) + min(0.25, density / 10.0) - support * 0.28 - recovery_penalty))

        # Heavy stretches trigger temporary breathing room.
        if recent >= 6.5 and not in_recovery:
            self.recovery_until_day = self._day_index() + 2
            in_recovery = True
            intensity = max(0.0, intensity - 0.18)

        collision_allowance = max(0.08, min(0.9, 0.15 + intensity * 0.62 + stage * 0.12 - support * 0.14 - (0.15 if in_recovery else 0.0)))
        density_target = max(1.2, min(5.0, 1.2 + stage * 3.0 + intensity * 1.4 - (0.7 if in_recovery else 0.0)))

        snap = LifeFlowSnapshot(
            intensity=intensity,
            recent_pressure=recent,
            density_load=density,
            collision_allowance=collision_allowance,
            event_density_target=density_target,
            in_recovery_window=in_recovery,
            support_stability=support,
        )
        self.last_snapshot = snap
        return snap

    def modulate_days_ahead(self, base_days: int, source: str, major: bool = False) -> int:
        snap = self.snapshot()
        shift = 0

        if snap.in_recovery_window and major:
            shift += 1
        if snap.intensity < 0.25 and major:
            shift += 1
        if snap.intensity > 0.68:
            shift -= 1
        if source in {"release", "promo"} and snap.intensity > 0.55:
            shift -= 1

        adjusted = max(0, base_days + shift)
        return adjusted

    def allow_pressure(self, source: str, base_weight: float = 1.0, major: bool = False) -> bool:
        snap = self.snapshot()
        overload = max(0.0, snap.density_load - snap.event_density_target)

        allowance = snap.collision_allowance
        if major:
            allowance += 0.08
        if source in {"public", "rivalry", "interference"}:
            allowance += snap.intensity * 0.08
        if source in {"opportunity", "collab"} and snap.in_recovery_window:
            allowance -= 0.08

        burden = base_weight * (0.24 + overload * 0.12)
        return allowance >= burden

    def effective_pressure_multiplier(self) -> float:
        snap = self.snapshot()
        mult = 1.0 + snap.intensity * 0.35
        if snap.in_recovery_window:
            mult -= 0.16
        mult -= snap.support_stability * 0.15
        return max(0.65, min(1.35, mult))
