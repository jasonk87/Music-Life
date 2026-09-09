from dataclasses import dataclass, field
from math import ceil
from typing import Dict, List, Optional
import random

from game.game_time import current_game_time


@dataclass
class TransitAction:
    action_id: str
    label: str
    duration_minutes: int
    money_cost: int = 0
    requires_passenger_bandwidth: bool = False


@dataclass
class TransitSession:
    chunk_minutes: int
    chunks_completed: int = 0
    action_history: List[str] = field(default_factory=list)


class TransitLayer:
    """Lightweight travel-phase layer over the existing TravelManager flow."""

    BASE_ACTIONS: Dict[str, TransitAction] = {
        "wait": TransitAction("wait", "Travel for one hour", 60),
        "sleep": TransitAction("sleep", "Sleep / Rest", 60, requires_passenger_bandwidth=True),
        "phone": TransitAction("phone", "Open phone", 0, requires_passenger_bandwidth=True),
        "call": TransitAction("call", "Call a contact / 15 min", 15, requires_passenger_bandwidth=True),
        "prepare": TransitAction("prepare", "Mental Preparation", 60),
        "gear_check": TransitAction("gear_check", "Check Gear / Prep", 60),
        "eat": TransitAction("eat", "Eat Meal", 60, money_cost=12),
        "drink": TransitAction("drink", "Have a Drink", 60, money_cost=9, requires_passenger_bandwidth=True),
    }

    def start_session(self, travel_manager) -> TransitSession:
        remaining_minutes = self.estimate_remaining_minutes(travel_manager)
        chunk = 120 if remaining_minutes >= 480 and self._is_passenger_context(None, travel_manager) else 60
        return TransitSession(chunk_minutes=chunk)

    def estimate_remaining_minutes(self, tm) -> int:
        remaining_distance = max(0.0, tm.distance_total - tm.distance_covered)
        speed = max(5.0, float(getattr(tm, "current_speed", 60.0) or 60.0))
        return max(0, int(ceil((remaining_distance / speed) * 60))) + getattr(tm, "delay_minutes", 0)

    def available_actions(self, game, tm) -> Dict[str, str]:
        player = game.player
        can_passenger_multitask = self._is_passenger_context(player, tm)

        actions: Dict[str, str] = {"continue": "Continue until arrival or interruption"}
        for action_id, definition in self.BASE_ACTIONS.items():
            if definition.requires_passenger_bandwidth and not can_passenger_multitask:
                continue
            if action_id in {"sleep", "gear_check"} and not can_passenger_multitask:
                continue
            if action_id == "eat" and player.money < definition.money_cost:
                continue
            if action_id == "drink" and player.money < definition.money_cost:
                continue
            actions[action_id] = definition.label
        vehicle = getattr(tm, 'vehicle', None)
        if vehicle and hasattr(vehicle, 'fuel'):
            missing = max(0, vehicle.fuel_capacity - vehicle.fuel)
            if missing > 0:
                actions['refuel'] = f"Fuel stop / ${ceil(missing * 3)} / 30 min"
            if vehicle.condition < 100:
                actions['repair'] = f"Roadside repairs / ${ceil((100 - vehicle.condition) * 3)} / 2 hours"
        return actions

    def execute_chunk(self, game, tm, session: TransitSession, action_id: str) -> Dict:
        player = game.player
        actions = self.available_actions(game, tm)
        if action_id not in actions:
            action_id = "wait"

        logs: List[str] = []
        # The departure city remains the route origin, but the player is no
        # longer physically present in its station or venue.
        player.current_poi = None
        if action_id in {'phone', 'call', 'continue'}:
            arrived = False
            def spend(minutes):
                nonlocal arrived
                events, arrived, elapsed = self.advance_travel(game, tm, minutes)
                logs.extend(events)
                for line in events:
                    game.GAME_LOG.add_log_message(line)
                if action_id in {'phone', 'call'} and arrived and elapsed < minutes:
                    player.current_location = tm.destination
                    player.current_poi = game._get_arrival_poi(tm.destination, tm.transport_mode)
                    game._advance_time_with_needs(minutes - elapsed)
            if action_id == 'phone':
                from game.phone_actions import onboard_phone
                onboard_phone(game, tm, spend)
            elif action_id == 'call':
                from game.phone_actions import choose_contact
                choose_contact(game, spend)
            else:
                for _ in range(48):
                    upcoming = player.schedule.get_upcoming_events(current_game_time.copy(), limit=1) if hasattr(player, 'schedule') else []
                    deadline = upcoming[0].start_time if upcoming else None
                    minutes = min(60, max(1, round(deadline.days_difference(current_game_time) * 1440))) if deadline else 60
                    spend(minutes)
                    if arrived or logs or player.energy < 20 or player.hunger >= 75:
                        if not arrived and not logs:
                            logs.append('Journey paused: you need rest or food.')
                        break
                    if deadline and current_game_time >= deadline:
                        logs.append('A calendar commitment is starting. You are still in transit.')
                        break
                    if hasattr(player, 'schedule'):
                        upcoming = player.schedule.get_upcoming_events(current_game_time.copy(), limit=1)
                        if upcoming and upcoming[0].start_time.days_difference(current_game_time) * 1440 <= 60:
                            logs.append('A commitment starts within the hour. Check the calendar before continuing.')
                            break
            session.action_history.append(action_id)
            session.chunks_completed += 1
            return {'arrived': arrived, 'logs': logs, 'feed': [], 'action_id': action_id,
                    'remaining_minutes': self.estimate_remaining_minutes(tm)}
        if action_id in ('refuel', 'repair'):
            vehicle = tm.vehicle
            cost = (ceil(max(0, vehicle.fuel_capacity - vehicle.fuel) * 3) if action_id == 'refuel'
                    else ceil(max(0, 100 - vehicle.condition) * 3))
            if player.money < cost:
                logs.append(f'This service costs ${cost}. No payment taken.')
            else:
                player.money -= cost
                if action_id == 'refuel': vehicle.refuel(vehicle.fuel_capacity)
                else: vehicle.repair()
                minutes = 30 if action_id == 'refuel' else 120
                game._advance_time_with_needs(minutes)
                tm.travel_time_elapsed += minutes / 60
                logs.append(f"{'Fuel stop' if action_id == 'refuel' else 'Roadside repairs'} complete. Paid ${cost}.")
                session.chunks_completed += 1
                session.action_history.append(action_id)
            return {'arrived': False, 'logs': logs, 'feed': [], 'action_id': action_id,
                    'remaining_minutes': self.estimate_remaining_minutes(tm)}
        if action_id == 'gear_check':
            from game.career_actions import report
            report(game, 'Before the next stop', '\n'.join(self._run_prep_check(game)))
            return {'arrived': False, 'logs': [], 'feed': [], 'action_id': action_id,
                    'remaining_minutes': self.estimate_remaining_minutes(tm)}
        action = self.BASE_ACTIONS[action_id]
        session.action_history.append(action_id)
        feed = []

        if action.money_cost > 0:
            player.money -= action.money_cost
            logs.append(f"Transit spend: ${action.money_cost} for {action.label.lower()}.")

        events, arrived, elapsed = self.advance_travel(game, tm, 60)
        logs.extend(events)

        # Action effects
        if action_id == "sleep":
            sleep_boost = 12
            if getattr(tm, "ticket_class", "economy") in {"business", "first"}:
                sleep_boost += 4
            if game.delegation_system.get_role(player, "driver"):
                sleep_boost += 3
            player.energy = min(100, player.energy + sleep_boost * elapsed / 60)
            player.stress = max(0, player.stress - 3 * elapsed / 60)
            logs.append("You catch meaningful rest during transit.")
        elif action_id == "prepare":
            player.stress = max(0, player.stress - 4 * elapsed / 60)
            player.inspiration = min(100, player.inspiration + elapsed / 60)
            logs.append("You mentally rehearse and focus on execution.")
        elif action_id == "gear_check":
            logs.extend(self._run_prep_check(game))
        elif action_id == "eat":
            player.hunger = max(0, player.hunger - 28)
            player.energy = min(100, player.energy + 3)
            logs.append("You get a meal in and stabilize your energy.")
        elif action_id == "drink":
            player.stress = max(0, player.stress - 7)
            player.energy = max(0, player.energy - 5)
            logs.append("You unwind with a drink, but feel less sharp.")
        else:
            logs.append("You focus on the ride and let time pass.")

        interruption_logs = self._apply_transit_visibility_pressure(game, tm)
        logs.extend(interruption_logs)
        logs.extend(self._apply_transit_delegation_events(game, tm))

        session.chunks_completed += 1

        return {
            "arrived": arrived,
            "logs": logs,
            "feed": feed,
            "action_id": action_id,
            "remaining_minutes": self.estimate_remaining_minutes(tm),
        }

    def advance_travel(self, game, tm, minutes):
        if hasattr(tm, 'advance_minutes'):
            events, arrived, elapsed = tm.advance_minutes(minutes)
        else:  # Compatibility for older integrations with hourly managers.
            events, arrived = tm.advance_one_hour()
            elapsed = 60
        game._advance_time_with_needs(elapsed)
        return events, arrived, elapsed

    def _is_passenger_context(self, player, tm) -> bool:
        if getattr(tm, "transport_mode", None) in {"walk", "bike"}:
            return False
        if getattr(tm, "vehicle", None) is None:
            return True
        if player is None:
            return False
        # Delegated driver allows safer bandwidth while moving.
        if hasattr(player, "delegation_roles"):
            role = player.delegation_roles.get("driver")
            if role and role.active and role.available:
                quality = max(0.0, min(1.0, (role.competence * 0.45) + (role.reliability * 0.35) + (getattr(role, "experience", 0.5) * 0.2)))
                return quality >= 0.58
        return False

    def _run_prep_check(self, game) -> List[str]:
        player = game.player
        if not hasattr(player, "schedule"):
            return ["You run a quick prep check, but nothing urgent comes up."]

        next_obligation = player.schedule.get_next_presence_obligation(current_game_time.copy())
        if not next_obligation:
            return ["You check your setup. No immediate obligations ahead."]

        assessment = game._assess_gig_requirements()
        if assessment.status == "fully_satisfied":
            return [f"Prep check for '{next_obligation.description}': gear requirements look solid."]
        if assessment.status == "missing_and_severe":
            return [f"Prep warning: critical missing requirements ({', '.join(assessment.missing_severe)})."]
        return [f"Prep warning: recoverable gaps detected ({', '.join(assessment.missing)})."]

    def _collect_world_feed(self, game) -> List[Dict[str, str]]:
        feed: List[Dict[str, str]] = []
        player = game.player
        player_name = player.name if player else None

        if hasattr(game, "visibility_system") and player_name:
            recent = game.visibility_system.recent_signals(entity_id=player_name, limit=2)
            for signal in recent:
                feed.append({
                    "type": "signal",
                    "text": f"{signal.signal_type.replace('_', ' ')} ({signal.polarity}, strength {signal.strength:.1f})",
                })

        if hasattr(game, "world_memory") and player_name:
            recent_events = [e for e in reversed(game.world_memory.entries[-6:]) if player_name in e.involved_entities]
            for entry in recent_events[:2]:
                feed.append({"type": "memory", "text": f"{entry.event_type.replace('_', ' ')} @ {entry.location or 'unknown'}"})

        if hasattr(player, "schedule"):
            upcoming = player.schedule.get_upcoming_events(current_game_time.copy(), limit=1)
            if upcoming:
                feed.append({"type": "obligation", "text": f"Upcoming: {upcoming[0].description} ({upcoming[0].start_time})"})

        if getattr(player, "active_opportunities", None):
            open_count = sum(1 for x in player.active_opportunities.values() if isinstance(x, dict) and x.get("status") == "available")
            if open_count:
                feed.append({"type": "opportunity", "text": f"{open_count} active opportunity hooks in your phone."})

        return feed[:4]

    def _apply_transit_delegation_events(self, game, tm) -> List[str]:
        player = game.player
        logs: List[str] = []
        if not hasattr(game, "delegation_system"):
            return logs

        manager_role = game.delegation_system.get_role(player, "manager")
        if manager_role and random.random() < 0.22:
            logs.append("Manager ping: stay reachable, a booking window may open before arrival.")

        assistant_role = game.delegation_system.get_role(player, "assistant")
        if assistant_role and random.random() < 0.18:
            logs.append("Assistant ping: double-check your next obligation requirements.")

        return logs

    def _apply_transit_visibility_pressure(self, game, tm) -> List[str]:
        player = game.player
        if not hasattr(game, "visibility_system"):
            return []

        location_ref = player.current_location.name if player.current_location else None
        pressure = game.visibility_system.exposure_pressure(
            player.name,
            location_ref,
            place_type="transport",
            risk_profile="high" if getattr(tm, "transport_mode", "bus") in {"plane", "bus", "train"} else "medium",
            busy_hour=(6 <= current_game_time.hour <= 22),
        )
        pressure = game.delegation_system.security_adjust_visibility_pressure(
            player,
            pressure,
            world_memory=game.world_memory,
            location_ref=location_ref,
        )

        if pressure > 18 and random.random() < min(0.55, pressure / 120.0):
            player.stress = min(100, player.stress + 4)
            return ["Transit interruption: public recognition pressure made this leg more stressful."]
        return []
