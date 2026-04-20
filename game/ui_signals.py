from __future__ import annotations

from typing import Dict, List, Optional

from game.game_time import current_game_time


class UISignalLayer:
    """Transforms simulation state into concise, display-ready UI signals."""

    def __init__(self, game):
        self.game = game

    def get_current_context(self) -> Dict:
        player = self.game.player
        if not player:
            return {"label": "No active character", "city": None, "place_type": None, "state": "idle"}

        city = player.current_location.name if player.current_location else "Unknown"
        place_name = player.current_poi.name if player.current_poi else city
        place_type = self._format_place_type(player.current_poi)

        if self.game.game_state == "travel_active" and self.game.travel_manager:
            tm = self.game.travel_manager
            remaining_minutes = 0
            if hasattr(self.game, "transit_layer"):
                remaining_minutes = self.game.transit_layer.estimate_remaining_minutes(tm)
            next_item = self._next_scheduled_item_text()
            available_actions = []
            if hasattr(self.game, "transit_layer"):
                available_actions = list(self.game.transit_layer.available_actions(self.game, tm).values())
            return {
                "label": f"On {tm.transport_mode} to {tm.destination.name}",
                "city": city,
                "place_type": "Transit",
                "state": "in_transit",
                "destination": tm.destination.name,
                "time_remaining": self._format_duration(remaining_minutes),
                "next_item": next_item,
                "available_actions": available_actions,
            }

        if self.game.game_state == "performance" and self.game.active_performance:
            return {
                "label": f"Backstage - {self.game.active_performance.name}",
                "city": city,
                "place_type": "Backstage",
                "state": "backstage",
            }

        return {
            "label": f"{city} - {place_type} - {place_name}",
            "city": city,
            "place_type": place_type,
            "state": "grounded",
        }

    def get_schedule_view(self, limit: int = 8) -> Dict[str, List[Dict]]:
        player = self.game.player
        groups = {"Today": [], "Tomorrow": [], "Upcoming": []}
        if not player or not hasattr(player, "schedule"):
            return groups

        now = current_game_time.copy()
        upcoming = player.schedule.get_upcoming_events(now, limit=limit)
        for item in upcoming:
            day_diff = self._day_difference(now, item.start_time)
            if day_diff <= 0:
                bucket = "Today"
            elif day_diff == 1:
                bucket = "Tomorrow"
            else:
                bucket = "Upcoming"

            destination = item.get_destination_id() if hasattr(item, "get_destination_id") else None
            city = item.details.get("location_name") if isinstance(item.details, dict) else None
            groups[bucket].append(
                {
                    "time": self._format_clock(item.start_time),
                    "title": item.description,
                    "city": city,
                    "destination": destination,
                    "line": self._format_schedule_line(item, city),
                }
            )

        return groups

    def get_condition_tags(self) -> List[str]:
        player = self.game.player
        if not player:
            return []

        tags: List[str] = []
        if player.energy <= 20:
            tags.append("Exhausted")
        elif player.energy <= 40:
            tags.append("Tired")
        elif player.energy >= 75:
            tags.append("Well Rested")

        if player.stress >= 82:
            tags.append("On Edge")
        elif player.stress <= 25:
            tags.append("Feeling Good")

        if player.money <= 20:
            tags.append("Broke")
        elif player.money <= 80:
            tags.append("Low Cash")

        city = player.current_location.name if player.current_location else None
        visibility = self.game.visibility_system.get_visibility(player.name, city) if hasattr(self.game, "visibility_system") else {}
        if visibility.get("public_visibility", 0.0) >= 14:
            tags.append("People Recognizing You")

        place_category = getattr(player.current_poi, "category", "") if player.current_poi else ""
        if place_category in {"TRANSPORT_AIRPORT", "TRANSPORT_BUS", "venue_club", "VENUE_CLUB"}:
            tags.append("Crowded Area")

        if self.game.game_state == "travel_active":
            tags.append("In Transit")

        return tags[:6]

    def get_world_feed(self, limit: int = 6) -> List[Dict[str, str]]:
        feed: List[Dict[str, str]] = []
        player = self.game.player
        if not player:
            return feed

        if hasattr(self.game, "visibility_system"):
            for signal in self.game.visibility_system.recent_signals(entity_id=player.name, limit=3):
                text = self._signal_to_text(signal)
                if text:
                    feed.append({"type": "signal", "text": text})

        if hasattr(self.game, "world_memory"):
            for entry in reversed(self.game.world_memory.entries[-20:]):
                text = self._memory_to_world_text(entry, player.name)
                if text:
                    feed.append({"type": "memory", "text": text})
                if len(feed) >= limit:
                    break

        for item in self._opportunity_feed_items(limit=limit - len(feed)):
            feed.append(item)
            if len(feed) >= limit:
                break

        deduped: List[Dict[str, str]] = []
        seen = set()
        for item in feed:
            if item["text"] in seen:
                continue
            seen.add(item["text"])
            deduped.append(item)
            if len(deduped) >= limit:
                break
        return deduped

    def get_recent_events(self, limit: int = 8) -> List[str]:
        player = self.game.player
        if not player or not hasattr(self.game, "world_memory"):
            return []

        events: List[str] = []
        for entry in reversed(self.game.world_memory.entries):
            if player.name not in (entry.involved_entities or []):
                continue
            text = self._memory_to_player_text(entry)
            if not text:
                continue
            events.append(text)
            if len(events) >= limit:
                break
        return events

    def _format_place_type(self, place_obj) -> str:
        if not place_obj:
            return "City"
        return getattr(place_obj, "category", getattr(place_obj, "venue_type", "Place")).replace("_", " ").title()

    def _day_difference(self, now, target) -> int:
        now_total = now.year * 360 + now.month * 30 + now.day
        target_total = target.year * 360 + target.month * 30 + target.day
        return target_total - now_total

    def _format_clock(self, gt_obj) -> str:
        hour = gt_obj.hour % 12
        if hour == 0:
            hour = 12
        ampm = "AM" if gt_obj.hour < 12 else "PM"
        return f"{hour}:{gt_obj.minute:02d} {ampm}"

    def _format_schedule_line(self, item, city: Optional[str]) -> str:
        clock = self._format_clock(item.start_time)
        if city:
            return f"{clock} - {item.description} ({city})"
        return f"{clock} - {item.description}"

    def _format_duration(self, minutes: int) -> str:
        if minutes <= 0:
            return "Arriving"
        hours = minutes // 60
        rem = minutes % 60
        if hours and rem:
            return f"{hours}h {rem}m"
        if hours:
            return f"{hours}h"
        return f"{rem}m"

    def _next_scheduled_item_text(self) -> Optional[str]:
        player = self.game.player
        if not player or not hasattr(player, "schedule"):
            return None
        upcoming = player.schedule.get_upcoming_events(current_game_time.copy(), limit=1)
        if not upcoming:
            return None
        item = upcoming[0]
        return f"{self._format_clock(item.start_time)} - {item.description}"

    def _signal_to_text(self, signal) -> Optional[str]:
        mapping = {
            "local_buzz_rising": "People are talking about your recent set.",
            "negative_press": "Word is spreading about a rough moment.",
            "public_backlash": "Crowds are reacting to recent drama.",
            "industry_attention": "Industry chatter around your name is growing.",
            "rivalry_publicity": "Rival stories are circulating in the scene.",
        }
        return mapping.get(signal.signal_type, None)

    def _memory_to_world_text(self, entry, player_name: str) -> Optional[str]:
        event_map = {
            "great_performance": "Crowd liked your set last night.",
            "missed_gig": "A local act filled in at a show you missed.",
            "late_obligation": "You showed up after doors and people noticed.",
            "replacement_slot": "Another artist stepped into an open slot.",
            "collaboration": "Talk around a new collaboration is picking up.",
            "rivalry_escalation": "A rivalry story is making rounds.",
            "assistant_success": "Assistant packed your bags.",
            "assistant_prep_failure": "Assistant forgot something important.",
            "driver_improved_trip_outcome": "Your driver kept the trip smooth.",
            "driver_unavailable": "Your driver wasn't available.",
            "security_prevented_escalation": "Security kept things calm.",
            "manager_overbooked_pressure": "Manager shuffled plans at the last minute.",
        }
        if player_name not in (entry.involved_entities or []):
            return None
        return event_map.get(entry.event_type)

    def _memory_to_player_text(self, entry) -> Optional[str]:
        event_map = {
            "great_performance": "You played a strong set.",
            "poor_performance": "You had a rough set.",
            "missed_gig": "You missed your set.",
            "late_obligation": "You arrived late.",
            "reachable_obligation": "You made it on time.",
            "assistant_success": "Your assistant packed your bags.",
            "assistant_prep_failure": "Your assistant forgot something.",
            "driver_improved_trip_outcome": "Your driver kept the ride smooth.",
            "driver_unavailable": "Your driver wasn't available.",
            "security_prevented_escalation": "Security kept things calm.",
            "manager_overbooked_pressure": "Your manager had to reshuffle plans.",
        }
        return event_map.get(entry.event_type)

    def _opportunity_feed_items(self, limit: int) -> List[Dict[str, str]]:
        if limit <= 0:
            return []
        player = self.game.player
        if not player or not getattr(player, "active_opportunities", None):
            return []

        items = []
        available = [k for k, v in player.active_opportunities.items() if isinstance(v, dict) and v.get("status") == "available"]
        if available:
            items.append({"type": "opportunity", "text": "New booking and collab conversations are active."})
        return items[:limit]
