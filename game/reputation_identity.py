from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from game.game_time import current_game_time


@dataclass
class ReputationSnapshot:
    entity_id: str
    scope: str
    recent: Dict[str, float] = field(default_factory=dict)
    long_term: Dict[str, float] = field(default_factory=dict)
    momentum: float = 0.0


class ReputationIdentitySystem:
    """Memory-driven narrative identity (soft interpretation, never source-of-truth).

    Reputation is inferred from repeated observed events in world memory plus visibility.
    It is scope-aware (global/city/org) and decays over time.
    """

    EVENT_DIMENSIONS: Dict[str, List[Tuple[str, float]]] = {
        "great_performance": [("reliable", 0.8), ("professional", 0.6), ("live_respected", 1.0), ("exciting", 0.45), ("rising", 0.35)],
        "poor_performance": [("fading", 0.6), ("chaotic", 0.35)],
        "missed_gig": [("flaky", 1.0), ("chaotic", 0.8), ("hard_to_work_with", 0.5)],
        "missed_obligation": [("flaky", 0.85), ("difficult", 0.45), ("hard_to_work_with", 0.35)],
        "late_obligation": [("flaky", 0.6), ("difficult", 0.3)],
        "contract_warning": [("difficult", 0.9), ("hard_to_work_with", 0.8)],
        "contract_dropped": [("hard_to_work_with", 1.2), ("fading", 0.7)],
        "contract_milestone_hit": [("reliable", 0.85), ("professional", 0.65), ("label_favorite", 0.55)],
        "breakout_release": [("rising", 1.25), ("exciting", 1.0), ("media_magnet", 0.75)],
        "poor_release_reception": [("fading", 0.75), ("controversial", 0.35)],
        "rushed_session": [("chaotic", 0.55), ("difficult", 0.25)],
        "studio_session_completed": [("professional", 0.45), ("reliable", 0.4)],
        "collaboration": [("professional", 0.4), ("exciting", 0.35)],
        "rivalry_escalation": [("controversial", 0.85), ("media_magnet", 0.55), ("exciting", 0.35)],
        "public_backlash": [("controversial", 1.0), ("difficult", 0.35)],
        "negative_press": [("controversial", 0.6), ("fading", 0.45)],
        "local_buzz_rising": [("rising", 0.4), ("exciting", 0.35)],
    }

    def __init__(self, game):
        self.game = game

    def snapshot(self, entity_id: str, scope: str = "global") -> ReputationSnapshot:
        now = current_game_time.copy()
        recent_scores: Dict[str, float] = {}
        long_scores: Dict[str, float] = {}

        if not hasattr(self.game, "world_memory"):
            return ReputationSnapshot(entity_id=entity_id, scope=scope)

        for entry in self.game.world_memory.entries:
            if entity_id not in (entry.involved_entities or []):
                continue
            if not self._entry_matches_scope(entry, scope):
                continue

            age_days = max(0, now.days_difference(entry.timestamp))
            event_dims = self.EVENT_DIMENSIONS.get(entry.event_type, [])
            if not event_dims:
                continue

            entry_weight = max(0.3, float(entry.impact_score or 0.0))
            recent_decay = max(0.0, 1.0 - (age_days / 21.0))
            long_decay = max(0.08, 1.0 - (age_days / 180.0))

            for dim, base in event_dims:
                recent_scores[dim] = recent_scores.get(dim, 0.0) + (base * entry_weight * recent_decay)
                long_scores[dim] = long_scores.get(dim, 0.0) + (base * entry_weight * long_decay)

        self._apply_visibility_and_relationship_bias(entity_id, scope, recent_scores, long_scores)
        momentum = self._momentum_from(recent_scores, long_scores)

        return ReputationSnapshot(
            entity_id=entity_id,
            scope=scope,
            recent=recent_scores,
            long_term=long_scores,
            momentum=momentum,
        )

    def _apply_visibility_and_relationship_bias(self, entity_id: str, scope: str, recent: Dict[str, float], long_term: Dict[str, float]):
        location = scope.split(":", 1)[1] if scope.startswith("city:") else None
        if hasattr(self.game, "visibility_system"):
            vis = self.game.visibility_system.get_visibility(entity_id, location)
            public = vis.get("public_visibility", 0.0)
            if public >= 8:
                recent["media_magnet"] = recent.get("media_magnet", 0.0) + min(2.2, public / 10.0)
            if vis.get("negative_pressure", 0.0) >= 3:
                recent["controversial"] = recent.get("controversial", 0.0) + min(1.8, vis.get("negative_pressure", 0.0) / 4.0)

        if scope.startswith("org:") and hasattr(self.game, "organization_contracts"):
            org_id = scope.split(":", 1)[1]
            contracts = self.game.organization_contracts.active_contracts_for(entity_id)
            if any(c.organization_id == org_id for c in contracts):
                long_term["label_favorite"] = long_term.get("label_favorite", 0.0) + 0.5

    def _entry_matches_scope(self, entry, scope: str) -> bool:
        if scope == "global":
            return True
        if scope.startswith("city:"):
            return entry.location == scope.split(":", 1)[1]
        if scope.startswith("org:"):
            org_id = scope.split(":", 1)[1]
            return isinstance(entry.metadata, dict) and entry.metadata.get("organization_id") == org_id
        return True

    def _momentum_from(self, recent: Dict[str, float], long_term: Dict[str, float]) -> float:
        up = recent.get("rising", 0.0) + recent.get("exciting", 0.0) + recent.get("live_respected", 0.0)
        down = recent.get("fading", 0.0) + recent.get("chaotic", 0.0) + recent.get("flaky", 0.0)
        baseline = (long_term.get("reliable", 0.0) - long_term.get("hard_to_work_with", 0.0)) * 0.12
        return max(-5.0, min(5.0, (up - down) * 0.25 + baseline))

    def summarize(self, entity_id: str, scope: str = "global", limit: int = 3) -> List[str]:
        snap = self.snapshot(entity_id, scope)
        combined: Dict[str, float] = {}
        for key in set(snap.recent) | set(snap.long_term):
            combined[key] = snap.recent.get(key, 0.0) * 0.6 + snap.long_term.get(key, 0.0) * 0.4

        ranked = sorted(combined.items(), key=lambda kv: kv[1], reverse=True)
        labels: List[str] = []
        for key, value in ranked:
            if value < 0.9:
                continue
            labels.append(key.replace("_", " "))
            if len(labels) >= limit:
                break
        return labels

    def bias_for(self, entity_id: str, location: Optional[str] = None, organization_id: Optional[str] = None) -> Dict[str, float]:
        global_snap = self.snapshot(entity_id, "global")
        local_snap = self.snapshot(entity_id, f"city:{location}") if location else ReputationSnapshot(entity_id, "city:none")
        org_snap = self.snapshot(entity_id, f"org:{organization_id}") if organization_id else ReputationSnapshot(entity_id, "org:none")

        reliable = global_snap.long_term.get("reliable", 0.0) + local_snap.recent.get("reliable", 0.0)
        flaky = global_snap.long_term.get("flaky", 0.0) + global_snap.recent.get("flaky", 0.0)
        professional = global_snap.long_term.get("professional", 0.0)
        difficult = global_snap.long_term.get("difficult", 0.0) + org_snap.recent.get("hard_to_work_with", 0.0)
        exciting = global_snap.recent.get("exciting", 0.0) + local_snap.recent.get("live_respected", 0.0)
        controversial = global_snap.recent.get("controversial", 0.0)
        label_favorite = org_snap.long_term.get("label_favorite", 0.0) + org_snap.recent.get("professional", 0.0)

        trust = max(-2.5, min(2.5, (reliable + professional * 0.7 - flaky - difficult * 0.8) * 0.16))
        scrutiny = max(0.0, min(2.5, (flaky * 0.8 + difficult + controversial * 0.9) * 0.14))
        opportunity = max(-2.0, min(2.5, (exciting + global_snap.momentum * 1.8 - scrutiny) * 0.15))
        negotiation = max(-2.0, min(2.2, (label_favorite + trust * 2.0 - scrutiny * 0.8) * 0.22))

        return {
            "trust": trust,
            "scrutiny": scrutiny,
            "opportunity": opportunity,
            "negotiation": negotiation,
            "momentum": global_snap.momentum,
        }
