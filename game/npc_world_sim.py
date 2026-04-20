from dataclasses import dataclass, field
from typing import Dict, List, Optional

from game.game_time import current_game_time, GameTime
from game.world_memory import WorldMemoryEntry


@dataclass
class NPCObligation:
    obligation_id: str
    title: str
    start_time: GameTime
    end_time: GameTime
    destination_id: str
    category: str = "gig"
    status: str = "scheduled"


@dataclass
class NPCRelationshipState:
    familiarity: int = 0
    respect: int = 0
    trust: int = 0
    rivalry: int = 0


class NPCWorldSimulator:
    def __init__(self, game):
        self.game = game

    def ensure_npc_state(self, npc):
        if not hasattr(npc, "role_tags"):
            npc.role_tags = ["artist"]
        if not hasattr(npc, "professionalism"):
            npc.professionalism = 50
        if not hasattr(npc, "momentum"):
            npc.momentum = 0
        if not hasattr(npc, "energy"):
            npc.energy = 70
        if not hasattr(npc, "stress"):
            npc.stress = 30
        if not hasattr(npc, "health"):
            npc.health = 80
        if not hasattr(npc, "money_light"):
            npc.money_light = 500
        if not hasattr(npc, "visibility_light"):
            npc.visibility_light = getattr(npc, "fame", 0)
        if not hasattr(npc, "obligations"):
            npc.obligations: List[NPCObligation] = []
        if not hasattr(npc, "relationship_state"):
            npc.relationship_state = NPCRelationshipState()
        if not hasattr(npc, "npc_links"):
            npc.npc_links: Dict[str, NPCRelationshipState] = {}

    def advance(self, minutes: int):
        if minutes <= 0:
            return

        now = current_game_time.copy()
        cutoff = now.copy()
        cutoff.advance_time(minutes)

        for npc in self.game.NPC_REGISTRY.values():
            self.ensure_npc_state(npc)
            self._seed_schedule_obligation(npc, now)
            self._resolve_npc_obligations(npc, now, cutoff)
            self._drift_npc_state(npc, minutes)
            self._maybe_emit_player_situation(npc)

    def _seed_schedule_obligation(self, npc, now: GameTime):
        slot = self.game._get_time_slot_key(now)
        destination_obj = npc.schedule.get(slot)
        if not destination_obj:
            return

        destination_id = getattr(destination_obj, "poi_id", getattr(destination_obj, "venue_id", None))
        if not destination_id:
            return

        already_has = any(
            ob.destination_id == destination_id and ob.start_time.year == now.year and ob.start_time.month == now.month and ob.start_time.day == now.day and ob.start_time.hour == now.hour
            for ob in npc.obligations
        )
        if already_has:
            return

        start = now.copy()
        end = now.copy()
        end.advance_time(60)
        npc.obligations.append(
            NPCObligation(
                obligation_id=f"npc_{npc.npc_id}_{now.year}{now.month}{now.day}{now.hour}",
                title=f"{npc.name} scheduled appearance",
                start_time=start,
                end_time=end,
                destination_id=destination_id,
                category="appearance",
            )
        )

    def _resolve_npc_obligations(self, npc, now: GameTime, cutoff: GameTime):
        for ob in list(npc.obligations):
            if ob.status in {"attended", "late", "missed", "poor_performance"}:
                continue
            if ob.start_time > cutoff:
                continue

            destination = self.game.get_poi_or_venue_by_id(ob.destination_id)
            if not destination:
                ob.status = "missed"
                self._apply_npc_outcome(npc, ob, "missing_destination")
                continue

            travel_minutes = self._estimate_npc_travel_minutes(npc, destination)
            arrival = now.copy()
            arrival.advance_time(travel_minutes)

            if arrival <= ob.start_time:
                ob.status = "attended"
                npc.current_location = destination
                self._apply_npc_outcome(npc, ob, "attended")
            elif arrival <= ob.end_time:
                ob.status = "late"
                npc.current_location = destination
                self._apply_npc_outcome(npc, ob, "late")
            else:
                ob.status = "missed"
                self._apply_npc_outcome(npc, ob, "missed")

    def _estimate_npc_travel_minutes(self, npc, destination) -> int:
        current = npc.current_location
        if not current:
            return 120

        current_city = getattr(current, "parent_location_id", getattr(current, "name", None))
        destination_city = getattr(destination, "parent_location_id", getattr(destination, "name", None))
        if current_city == destination_city:
            if hasattr(self.game, "player") and self.game.player and self.game.player.current_location and self.game.player.current_location.name == current_city:
                # Reuse city graph if available from the current location object.
                location_obj = self.game.player.current_location
                current_id = getattr(current, "poi_id", getattr(current, "venue_id", None))
                destination_id = getattr(destination, "poi_id", getattr(destination, "venue_id", None))
                conn = location_obj.intra_city_poi_connections.get(frozenset((current_id, destination_id)), {}) if current_id and destination_id else {}
                if conn:
                    return min(int(mode.get("time", 30)) for mode in conn.values())
            return 30

        city_obj = self.game.WORLD_MAP.get(current_city)
        if city_obj:
            route = city_obj.travel_connections.get(destination_city)
            if route:
                return int(float(route.get("time_hours", 2)) * 60)

        return 180

    def _apply_npc_outcome(self, npc, obligation: NPCObligation, outcome_key: str):
        rel = npc.relationship_state
        location = obligation.destination_id
        if outcome_key == "attended":
            npc.momentum += 2
            npc.professionalism = min(100, npc.professionalism + 1)
            npc.fame += 1
            rel.familiarity = min(100, rel.familiarity + 1)
            rel.respect = min(100, rel.respect + 1)
            self.game.world_memory.add(
                WorldMemoryEntry(
                    event_type="npc_attended_obligation",
                    involved_entities=[npc.npc_id],
                    location=location,
                    timestamp=current_game_time.copy(),
                    tags=["professionalism", "momentum"],
                    impact_score=1.5,
                    metadata={"status": "attended"},
                    source_key=f"npc:{npc.npc_id}:{obligation.obligation_id}:attended",
                )
            )
        elif outcome_key == "late":
            npc.momentum = max(-50, npc.momentum - 1)
            npc.professionalism = max(0, npc.professionalism - 2)
            npc.stress = min(100, npc.stress + 4)
            rel.trust = max(-100, rel.trust - 1)
            self.game.world_memory.add(
                WorldMemoryEntry(
                    event_type="npc_late_obligation",
                    involved_entities=[npc.npc_id],
                    location=location,
                    timestamp=current_game_time.copy(),
                    tags=["professionalism"],
                    impact_score=1.5,
                    metadata={"status": "late"},
                    source_key=f"npc:{npc.npc_id}:{obligation.obligation_id}:late",
                )
            )
        else:  # missed / missing_destination
            npc.momentum = max(-50, npc.momentum - 3)
            npc.professionalism = max(0, npc.professionalism - 5)
            npc.stress = min(100, npc.stress + 8)
            rel.trust = max(-100, rel.trust - 3)
            rel.rivalry = min(100, rel.rivalry + 2)
            self.game.world_memory.add(
                WorldMemoryEntry(
                    event_type="npc_missed_obligation",
                    involved_entities=[npc.npc_id],
                    location=location,
                    timestamp=current_game_time.copy(),
                    tags=["professionalism", "rivalry"],
                    impact_score=2.5,
                    metadata={"status": "missed"},
                    source_key=f"npc:{npc.npc_id}:{obligation.obligation_id}:missed",
                )
            )

    def _drift_npc_state(self, npc, minutes: int):
        fatigue = max(1, int(minutes / 90))
        npc.energy = max(0, npc.energy - fatigue)
        if npc.energy < 20:
            npc.stress = min(100, npc.stress + 2)

    def _maybe_emit_player_situation(self, npc):
        if not self.game.player:
            return

        player = self.game.player
        player_reliability = self.game.world_memory.reliability_score(player.name, current_game_time.copy())
        player_city = player.current_location.name if player.current_location else None
        npc_city = getattr(npc.current_location, "parent_location_id", getattr(npc.current_location, "name", None))
        shared_city = player_city and npc_city and player_city == npc_city

        rel = npc.relationship_state
        if player_reliability < -4:
            rel.trust = max(-100, rel.trust - 1)
        elif player_reliability > 4:
            rel.respect = min(100, rel.respect + 1)

        # replacement gig: NPC misses an obligation, player shares city, and no existing offer.
        missed_recent = any(ob.status == "missed" for ob in npc.obligations[-2:])
        replacement_key = f"replacement_slot_{npc.npc_id}"
        if missed_recent and shared_city and replacement_key not in player.active_opportunities and player_reliability >= -6:
            player.active_opportunities[replacement_key] = {
                "status": "available",
                "type": "replacement_gig",
                "npc_id": npc.npc_id,
            }
            self.game.GAME_LOG.add_log_message(f"Scene buzz: {npc.name} missed a slot. You might be able to step in.")
            self.game.world_memory.add(
                WorldMemoryEntry(
                    event_type="replacement_slot",
                    involved_entities=[player.name, npc.npc_id],
                    location=player_city,
                    timestamp=current_game_time.copy(),
                    tags=["opportunity", "momentum"],
                    impact_score=2.0,
                    source_key=f"replacement:{npc.npc_id}:{current_game_time.get_time_string_for_schedule()}",
                )
            )

        collab_key = f"collab_offer_{npc.npc_id}"
        if shared_city and rel.respect >= 5 and rel.trust >= 3 and npc.momentum >= 1 and collab_key not in player.active_opportunities and player_reliability >= -2:
            player.active_opportunities[collab_key] = {
                "status": "available",
                "type": "collaboration_offer",
                "npc_id": npc.npc_id,
            }
            self.game.GAME_LOG.add_log_message(f"{npc.name} is open to a collaboration while you're both in {player_city}.")
            self.game.world_memory.add(
                WorldMemoryEntry(
                    event_type="collaboration",
                    involved_entities=[player.name, npc.npc_id],
                    location=player_city,
                    timestamp=current_game_time.copy(),
                    tags=["relationship", "momentum"],
                    impact_score=2.0,
                    source_key=f"collab:{npc.npc_id}:{current_game_time.get_time_string_for_schedule()}",
                )
            )

        rivalry_key = f"rivalry_{npc.npc_id}"
        if rel.rivalry >= 8 and npc.momentum >= 3 and rivalry_key not in player.active_opportunities:
            player.active_opportunities[rivalry_key] = {
                "status": "available",
                "type": "rivalry_escalation",
                "npc_id": npc.npc_id,
            }
            self.game.GAME_LOG.add_log_message(f"Rivalry escalates with {npc.name}; tension in the scene is rising.")
            self.game.world_memory.add(
                WorldMemoryEntry(
                    event_type="rivalry_escalation",
                    involved_entities=[player.name, npc.npc_id],
                    location=player_city,
                    timestamp=current_game_time.copy(),
                    tags=["rivalry"],
                    impact_score=2.5,
                    source_key=f"rivalry:{npc.npc_id}:{current_game_time.get_time_string_for_schedule()}",
                )
            )
