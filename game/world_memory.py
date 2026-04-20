from dataclasses import dataclass, field
from typing import Dict, List, Optional

from game.game_time import GameTime


@dataclass
class WorldMemoryEntry:
    event_type: str
    involved_entities: List[str]
    location: Optional[str]
    timestamp: GameTime
    tags: List[str] = field(default_factory=list)
    impact_score: float = 0.0
    metadata: Dict = field(default_factory=dict)
    source_key: Optional[str] = None


class WorldMemoryStore:
    def __init__(self, decay_days: float = 30.0):
        self.entries: List[WorldMemoryEntry] = []
        self.decay_days = decay_days
        self._source_keys = set()

    def add(self, entry: WorldMemoryEntry) -> bool:
        if entry.source_key and entry.source_key in self._source_keys:
            return False
        self.entries.append(entry)
        if entry.source_key:
            self._source_keys.add(entry.source_key)
        return True

    def query(
        self,
        event_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        location: Optional[str] = None,
        since: Optional[GameTime] = None,
    ) -> List[WorldMemoryEntry]:
        result = []
        for entry in self.entries:
            if event_type and entry.event_type != event_type:
                continue
            if entity_id and entity_id not in entry.involved_entities:
                continue
            if location and entry.location != location:
                continue
            if since and entry.timestamp < since:
                continue
            result.append(entry)
        return result

    def weight_for(self, entry: WorldMemoryEntry, now: GameTime) -> float:
        days = now.days_difference(entry.timestamp)
        decay = max(0.05, 1.0 - (days / self.decay_days))
        return decay

    def weighted_score(
        self,
        now: GameTime,
        event_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        location: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> float:
        score = 0.0
        for entry in self.query(event_type=event_type, entity_id=entity_id, location=location):
            if tag and tag not in entry.tags:
                continue
            score += entry.impact_score * self.weight_for(entry, now)
        return score

    def reliability_score(self, entity_id: str, now: GameTime) -> float:
        positive = self.weighted_score(now, event_type="great_performance", entity_id=entity_id)
        replacement = self.weighted_score(now, event_type="replacement_slot", entity_id=entity_id)
        negative_miss = self.weighted_score(now, event_type="missed_gig", entity_id=entity_id)
        negative_late = self.weighted_score(now, event_type="late_obligation", entity_id=entity_id)
        return positive + replacement - negative_miss - negative_late
