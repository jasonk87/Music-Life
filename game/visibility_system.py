from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from game.game_time import GameTime


@dataclass
class PublicSignal:
    signal_type: str
    source_entities: List[str]
    location_scope: Optional[str]
    timestamp: GameTime
    strength: float
    polarity: str
    metadata: Dict = field(default_factory=dict)


class VisibilitySystem:
    def __init__(self):
        self.entity_visibility: Dict[str, Dict[str, float]] = {}
        self.location_visibility: Dict[Tuple[str, str], float] = {}
        self.signals: List[PublicSignal] = []
        self._processed_sources = set()

    def _ensure_entity(self, entity_id: str):
        if entity_id not in self.entity_visibility:
            self.entity_visibility[entity_id] = {
                "base_visibility": 0.0,
                "recent_buzz": 0.0,
                "negative_pressure": 0.0,
            }

    def amplify_from_memory(self, memory_store, now: GameTime):
        for idx, entry in enumerate(memory_store.entries):
            source_key = entry.source_key or f"idx:{idx}:{entry.event_type}:{entry.timestamp.get_time_string_for_schedule()}"
            if source_key in self._processed_sources:
                continue
            self._processed_sources.add(source_key)

            self._amplify_entry(entry, now)

        self._decay(now, memory_store)

    def _amplify_entry(self, entry, now: GameTime):
        entities = entry.involved_entities or []
        if not entities:
            return

        event_map = {
            "great_performance": (2.8, "positive", "local_buzz_rising"),
            "poor_performance": (2.2, "negative", "negative_press"),
            "missed_gig": (2.6, "negative", "public_backlash"),
            "late_obligation": (1.4, "mixed", "industry_attention"),
            "replacement_slot": (2.0, "positive", "industry_attention"),
            "collaboration": (2.4, "positive", "industry_attention"),
            "rivalry_escalation": (2.8, "mixed", "rivalry_publicity"),
            "npc_missed_obligation": (1.6, "negative", "negative_press"),
            "npc_attended_obligation": (1.2, "positive", "local_buzz_rising"),
        }
        impact, polarity, signal_type = event_map.get(entry.event_type, (0.8, "mixed", "local_buzz_rising"))
        impact *= max(0.3, entry.impact_score / 2.0)

        for entity in entities:
            self._ensure_entity(entity)
            profile = self.entity_visibility[entity]
            if polarity == "positive":
                profile["base_visibility"] += impact * 0.7
                profile["recent_buzz"] += impact
            elif polarity == "negative":
                profile["base_visibility"] += impact * 0.4
                profile["recent_buzz"] += impact * 0.5
                profile["negative_pressure"] += impact
            else:
                profile["base_visibility"] += impact * 0.6
                profile["recent_buzz"] += impact * 0.8
                profile["negative_pressure"] += impact * 0.35

            if entry.location:
                key = (entity, entry.location)
                self.location_visibility[key] = self.location_visibility.get(key, 0.0) + impact

        self.signals.append(
            PublicSignal(
                signal_type=signal_type,
                source_entities=list(entities),
                location_scope=entry.location,
                timestamp=now.copy(),
                strength=impact,
                polarity=polarity,
                metadata={"event_type": entry.event_type, **entry.metadata},
            )
        )

    def _decay(self, now: GameTime, memory_store):
        for entity, profile in self.entity_visibility.items():
            profile["recent_buzz"] *= 0.92
            profile["negative_pressure"] *= 0.95

        for key, score in list(self.location_visibility.items()):
            self.location_visibility[key] = score * 0.96

    def get_visibility(self, entity_id: str, location: Optional[str] = None) -> Dict[str, float]:
        self._ensure_entity(entity_id)
        profile = dict(self.entity_visibility[entity_id])
        local = 0.0
        if location:
            local = self.location_visibility.get((entity_id, location), 0.0)
        profile["local_visibility"] = local
        profile["public_visibility"] = profile["base_visibility"] + profile["recent_buzz"] + (local * 0.5)
        return profile

    def exposure_pressure(
        self,
        entity_id: str,
        location: Optional[str],
        place_type: str,
        risk_profile: str,
        busy_hour: bool,
    ) -> float:
        vis = self.get_visibility(entity_id, location)
        pressure = vis["public_visibility"]
        if place_type in {"street", "club", "bar", "venue", "downtown"}:
            pressure *= 1.15
        if risk_profile == "high":
            pressure *= 1.25
        if busy_hour:
            pressure *= 1.2
        pressure += vis["negative_pressure"] * 0.8
        return max(0.0, pressure)

    def recent_signals(self, signal_type: Optional[str] = None, entity_id: Optional[str] = None, limit: int = 20):
        filtered = []
        for signal in reversed(self.signals):
            if signal_type and signal.signal_type != signal_type:
                continue
            if entity_id and entity_id not in signal.source_entities:
                continue
            filtered.append(signal)
            if len(filtered) >= limit:
                break
        return filtered
