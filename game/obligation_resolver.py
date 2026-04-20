from dataclasses import dataclass, field
from typing import List, Optional

from game.game_time import GameTime


PRESENCE_REQUIRED_CATEGORIES = {
    "Gig",
    "Gig (Tour)",
    "Job",
    "Rehearsal",
    "Meeting",
    "Label Visit",
    "Studio Session",
}


@dataclass
class TravelOption:
    mode: str
    minutes: int
    cost: int


@dataclass
class ObligationResolution:
    status: str
    item: object
    destination: Optional[object] = None
    option: Optional[TravelOption] = None
    arrival_time: Optional[GameTime] = None
    reason_code: Optional[str] = None
    explanation: str = ""
    risk_flags: List[str] = field(default_factory=list)


class ObligationResolver:
    """Central reachability/attendance resolver for schedule obligations."""

    MIN_ENERGY_TO_TRAVEL = 6
    LOW_ENERGY_WARNING = 20
    HIGH_STRESS_WARNING = 85

    def __init__(self, game):
        self.game = game

    def resolve_before_time_advance(self, minutes: int) -> Optional[ObligationResolution]:
        if minutes <= 0 or not self.game.player:
            return None

        from game.game_time import current_game_time

        now = current_game_time.copy()
        cutoff = now.copy()
        cutoff.advance_time(minutes)

        obligation = self.game.player.schedule.get_next_presence_obligation(now, cutoff)
        if not obligation:
            return None

        resolution = self._evaluate_obligation(obligation, now)
        if isinstance(obligation.details, dict):
            obligation.details["obligation_status"] = resolution.status
            obligation.details["obligation_reason_code"] = resolution.reason_code
            obligation.details["obligation_explanation"] = resolution.explanation
            obligation.details["obligation_risk_flags"] = list(resolution.risk_flags)
            obligation.details["obligation_evaluated_at"] = now.get_time_string_for_schedule()
            # New evaluation invalidates any previously applied downstream consequence snapshot.
            if obligation.details.get("obligation_consequence_applied_at") != obligation.details["obligation_evaluated_at"]:
                obligation.details.pop("obligation_consequence_applied_at", None)
        if resolution.status in {"requires_departure_now", "late_but_possible"}:
            self._apply_travel(resolution)

            if resolution.risk_flags:
                self.game.GAME_LOG.add_log_message(
                    f"Travel risk for '{obligation.description}': {self._format_risk_flags(resolution.risk_flags)}."
                )

        elif resolution.status in {"unreachable", "missed"}:
            detail = resolution.explanation or "no additional details"
            self.game.GAME_LOG.add_log_message(
                f"Attendance risk: {obligation.description} is {resolution.status.replace('_', ' ')} ({detail})."
            )

        return resolution

    def _evaluate_obligation(self, item, now: GameTime) -> ObligationResolution:
        destination = self._resolve_destination(item)
        if not destination:
            return ObligationResolution(
                "unreachable",
                item=item,
                reason_code="missing_destination",
                explanation="No destination metadata exists for this obligation.",
            )

        if self._is_player_at_destination(destination):
            return ObligationResolution(
                "reachable",
                item=item,
                destination=destination,
                explanation="Already at the obligation destination.",
                risk_flags=self._readiness_risk_flags(),
            )

        if self.game.player.energy < self.MIN_ENERGY_TO_TRAVEL:
            return ObligationResolution(
                "unreachable",
                item=item,
                destination=destination,
                reason_code="energy_threshold_too_high",
                explanation=(
                    f"Energy is too low to travel safely ({self.game.player.energy}/100). Rest or recover before attempting this trip."
                ),
            )

        option, blockers = self._best_travel_option(destination)
        if not option:
            reason_code, explanation = self._summarize_blockers(blockers)
            return ObligationResolution(
                "unreachable",
                item=item,
                destination=destination,
                reason_code=reason_code,
                explanation=explanation,
            )

        arrival = now.copy()
        arrival.advance_time(option.minutes)
        risk_flags = self._readiness_risk_flags(option)

        if arrival <= item.start_time:
            return ObligationResolution(
                "requires_departure_now",
                item=item,
                destination=destination,
                option=option,
                arrival_time=arrival,
                explanation="Reachable only by leaving now.",
                risk_flags=risk_flags,
            )

        if arrival <= item.end_time:
            return ObligationResolution(
                "late_but_possible",
                item=item,
                destination=destination,
                option=option,
                arrival_time=arrival,
                reason_code="travel_time_exceeds_start_window",
                explanation="Travel time causes a late arrival, but attendance is still possible before the event ends.",
                risk_flags=risk_flags,
            )

        if now >= item.start_time:
            return ObligationResolution(
                "missed",
                item=item,
                destination=destination,
                option=option,
                arrival_time=arrival,
                reason_code="travel_time_exceeds_available_window",
                explanation="Even immediate departure arrives after the obligation window has ended.",
            )

        return ObligationResolution(
            "unreachable",
            item=item,
            destination=destination,
            option=option,
            arrival_time=arrival,
            reason_code="travel_time_exceeds_available_window",
            explanation="Travel time exceeds the time available before the obligation window closes.",
        )

    def _resolve_destination(self, item):
        destination_id = item.get_destination_id()
        if destination_id:
            return self.game.get_poi_or_venue_by_id(destination_id)

        location_name = item.details.get("location_name") if isinstance(item.details, dict) else None
        if location_name:
            return self.game.WORLD_MAP.get(location_name)
        return None

    def _is_player_at_destination(self, destination) -> bool:
        player = self.game.player
        destination_id = getattr(destination, "poi_id", getattr(destination, "venue_id", None))
        current_id = getattr(player.current_poi, "poi_id", getattr(player.current_poi, "venue_id", None)) if player.current_poi else None
        if destination_id and destination_id == current_id:
            return True
        if getattr(destination, "name", None) and player.current_location and destination.name == player.current_location.name:
            return True
        return False

    def _best_travel_option(self, destination) -> tuple[Optional[TravelOption], List[str]]:
        player = self.game.player
        options: List[TravelOption] = []
        blockers: List[str] = []

        destination_location_name = getattr(destination, "parent_location_id", getattr(destination, "name", None))
        current_location = player.current_location
        if not current_location:
            return None, ["no_current_location"]

        # Intra-city travel
        if destination_location_name == current_location.name:
            current_id = getattr(player.current_poi, "poi_id", getattr(player.current_poi, "venue_id", None))
            destination_id = getattr(destination, "poi_id", getattr(destination, "venue_id", None))

            if not current_id or not destination_id:
                blockers.append("missing_intra_city_node")
                return None, blockers

            conn = current_location.intra_city_poi_connections.get(frozenset((current_id, destination_id)), {})
            if not conn:
                blockers.append("no_viable_transport")
                return None, blockers

            found_affordable = False
            found_mode = False

            for mode, details in conn.items():
                found_mode = True
                if mode == "bike" and details.get("requires_bike") and not player.has_bike:
                    blockers.append("vehicle_unavailable_or_broken")
                    continue

                cost = int(details.get("cost", 0))
                if cost > player.money:
                    blockers.append("insufficient_funds")
                    continue

                found_affordable = True
                options.append(TravelOption(mode=mode, minutes=int(details.get("time", 0)), cost=cost))

            if not found_mode:
                blockers.append("no_viable_transport")
            elif not found_affordable and "insufficient_funds" not in blockers:
                blockers.append("no_viable_transport")

            return min(options, key=lambda opt: opt.minutes, default=None), blockers

        # Inter-city travel using defined public route.
        blockers.append("currently_in_another_city")
        details = current_location.travel_connections.get(destination_location_name)
        if not details:
            blockers.append("no_viable_transport")
            return None, blockers

        public_cost = int(details.get("cost", 0))
        public_minutes = int(float(details.get("time_hours", 0)) * 60)

        if public_minutes <= 0:
            blockers.append("no_viable_transport")
        elif public_cost <= player.money:
            mode = str(details.get("method") or "public")
            options.append(TravelOption(mode=mode, minutes=public_minutes, cost=public_cost))
        else:
            blockers.append("insufficient_funds")

        if player.vehicles:
            for vehicle in player.vehicles:
                if getattr(vehicle, "condition", 100) <= 0 or getattr(vehicle, "fuel", 0) <= 0:
                    blockers.append("vehicle_unavailable_or_broken")
                    continue

                drive_minutes = public_minutes
                if drive_minutes <= 0:
                    blockers.append("no_viable_transport")
                    continue

                # Approximate fuel-related trip cost relative to public fare.
                fuel_cost = max(0, int(public_cost * 0.25))
                if fuel_cost > player.money:
                    blockers.append("insufficient_funds")
                    continue

                options.append(TravelOption(mode=f"drive:{vehicle.name}", minutes=drive_minutes, cost=fuel_cost))

        return min(options, key=lambda opt: opt.minutes, default=None), blockers

    def _summarize_blockers(self, blockers: List[str]) -> tuple[str, str]:
        if not blockers:
            return "no_viable_transport", "No travel options are currently available."

        priority = [
            "insufficient_funds",
            "vehicle_unavailable_or_broken",
            "currently_in_another_city",
            "no_viable_transport",
            "no_current_location",
        ]
        selected = next((code for code in priority if code in blockers), blockers[0])

        explanations = {
            "insufficient_funds": "Insufficient funds for every viable route option.",
            "no_viable_transport": "No viable transport path was found for this route.",
            "vehicle_unavailable_or_broken": "A required vehicle is unavailable, out of fuel, or broken.",
            "currently_in_another_city": "You are currently in another city and need an inter-city route.",
            "no_current_location": "Current location is unknown, so travel cannot be planned.",
            "missing_intra_city_node": "Current point of interest or destination node is missing from city travel graph.",
        }
        return selected, explanations.get(selected, "Travel could not be planned with current constraints.")

    def _readiness_risk_flags(self, option: Optional[TravelOption] = None) -> List[str]:
        flags = []
        player = self.game.player

        if player.energy < self.LOW_ENERGY_WARNING:
            flags.append("energy_risk_threshold_high")
        if player.stress > self.HIGH_STRESS_WARNING:
            flags.append("stress_risk_threshold_high")
        if option and option.minutes >= 6 * 60:
            flags.append("long_trip_fatigue_risk")

        return flags

    def _format_risk_flags(self, flags: List[str]) -> str:
        text_map = {
            "energy_risk_threshold_high": "energy is low",
            "stress_risk_threshold_high": "stress is very high",
            "long_trip_fatigue_risk": "trip is long and fatigue risk is elevated",
        }
        mapped = [text_map.get(flag, flag.replace("_", " ")) for flag in flags]
        return ", ".join(mapped)

    def _apply_travel(self, resolution: ObligationResolution):
        player = self.game.player
        destination = resolution.destination
        option = resolution.option
        if not destination or not option:
            return

        player.money -= option.cost

        target_city_name = getattr(destination, "parent_location_id", getattr(destination, "name", None))
        target_city = self.game.WORLD_MAP.get(target_city_name)
        if target_city:
            player.current_location = target_city

        if hasattr(destination, "poi_id") or hasattr(destination, "venue_id"):
            player.current_poi = destination
        elif target_city:
            player.current_poi = self.game._get_arrival_poi(target_city, "bus")

        self.game.GAME_LOG.add_log_message(
            f"Auto-travel for obligation: {resolution.item.description} via {option.mode} ({option.minutes}m, ${option.cost})."
        )
