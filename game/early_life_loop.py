from dataclasses import dataclass
import random
from typing import Optional

from game.game_time import current_game_time
from game.poi import PointOfInterest
from game.world_memory import WorldMemoryEntry
from game_data.gear_catalog import GEAR_CATALOG


@dataclass(frozen=True)
class LodgingTier:
    weekly_cost: int
    comfort_floor: int
    stress_on_miss: int


@dataclass(frozen=True)
class EarlyJob:
    job_id: str
    title: str
    category: str
    location_name: str
    location_category: str
    pay: int
    shift_duration_minutes: int
    energy_cost: int
    stress_cost: int
    recurrence_days: int = 2


class EarlyLifeLoop:
    """Grounded early-career survival pressure and location-based shift work."""

    LODGING_ORDER = ("small_apartment", "shared_room", "motel", "couch")
    LODGING = {
        "small_apartment": LodgingTier(weekly_cost=170, comfort_floor=58, stress_on_miss=10),
        "shared_room": LodgingTier(weekly_cost=105, comfort_floor=48, stress_on_miss=8),
        "motel": LodgingTier(weekly_cost=70, comfort_floor=38, stress_on_miss=6),
        "couch": LodgingTier(weekly_cost=30, comfort_floor=30, stress_on_miss=5),
    }
    JOB_CATALOG = (
        EarlyJob("retail_corner_mart", "Retail Shift", "RETAIL", "Corner Mart", "JOB_RETAIL", pay=52, shift_duration_minutes=300, energy_cost=18, stress_cost=5),
        EarlyJob("warehouse_distribution", "Warehouse Shift", "WAREHOUSE", "Distribution Center", "JOB_WAREHOUSE", pay=68, shift_duration_minutes=420, energy_cost=31, stress_cost=8),
        EarlyJob("kitchen_diner", "Kitchen Shift", "FOOD_SERVICE", "Night Diner", "JOB_DINER", pay=59, shift_duration_minutes=360, energy_cost=24, stress_cost=6),
        EarlyJob("temp_loading_yard", "Temp Shift", "TEMP_LABOR", "Loading Yard", "JOB_TEMP", pay=64, shift_duration_minutes=390, energy_cost=29, stress_cost=7),
    )

    def __init__(self, game):
        self.game = game

    def ensure_player_state(self, player):
        if not hasattr(player, "lodging_tier"):
            player.lodging_tier = "shared_room"
        if player.lodging_tier not in self.LODGING:
            player.lodging_tier = "shared_room"
        if not hasattr(player, "early_life_days_elapsed"):
            player.early_life_days_elapsed = 0
        if not hasattr(player, "early_jobs"):
            player.early_jobs = {}
        if not hasattr(player, "active_survival_job_id"):
            player.active_survival_job_id = None
        if not hasattr(player, "job_reliability"):
            player.job_reliability = 50

    def bootstrap_player_jobs(self, player):
        self.ensure_player_state(player)
        location = player.current_location
        if not location:
            return
        self._ensure_job_sites_for_location(location)
        first_listing = not player.early_jobs
        if location:
            for job in self.JOB_CATALOG:
                poi = self._find_job_site(location, job.job_id)
                if not poi:
                    continue
                player.early_jobs[job.job_id] = {
                    "job_id": job.job_id,
                    "title": job.title,
                    "category": job.category,
                    "location_id": poi.poi_id,
                    "location_name": poi.name,
                    "pay": job.pay,
                    "shift_duration_minutes": job.shift_duration_minutes,
                    "energy_cost": job.energy_cost,
                    "stress_cost": job.stress_cost,
                    "recurrence_days": job.recurrence_days,
                }
            if first_listing and player.early_jobs:
                player.active_survival_job_id = sorted(player.early_jobs.keys())[0]

    def schedule_job_shift(self, player, job_id: Optional[str] = None, start_time=None):
        self.ensure_player_state(player)
        self.bootstrap_player_jobs(player)
        selected_job_id = job_id or player.active_survival_job_id
        if not selected_job_id or selected_job_id not in player.early_jobs:
            return {"ok": False, "reason": "no_job_available"}

        job = player.early_jobs[selected_job_id]
        start = start_time.copy() if start_time else self._next_shift_start(current_game_time.copy())
        end = start.copy()
        end.advance_time(job["shift_duration_minutes"])
        description = f"{job['title']} — {job['location_name']}"
        details = {
            "job_id": job["job_id"],
            "destination_id": job["location_id"],
            "location_name": player.current_location.name if player.current_location else None,
            "requires_presence": True,
            "shift_pay": job["pay"],
            "shift_duration_minutes": job["shift_duration_minutes"],
            "shift_energy_cost": job["energy_cost"],
            "shift_stress_cost": job["stress_cost"],
            "shift_status": "scheduled",
        }
        player.schedule.add_event(start, end, description, "Job", details)
        return {"ok": True, "job_id": selected_job_id, "start": start, "end": end, "destination_id": job["location_id"]}

    def ensure_next_shift_exists(self, player):
        if getattr(self.game, "recurring_work", True) is False:
            return
        if not player or not hasattr(player, "schedule"):
            return
        upcoming_job = any(
            item.category == "Job" and item.start_time >= current_game_time
            for item in player.schedule.scheduled_items
        )
        if not upcoming_job:
            self.schedule_job_shift(player)

    def resolve_shift_event(self, player, event_item):
        self.ensure_player_state(player)
        details = event_item.details if isinstance(event_item.details, dict) else {}
        shift_pay = int(details.get("shift_pay", 0))
        shift_energy = int(details.get("shift_energy_cost", 20))
        shift_stress = int(details.get("shift_stress_cost", 5))
        destination_id = details.get("destination_id") or details.get("poi_id")

        current_id = None
        if player.current_poi:
            current_id = getattr(player.current_poi, "poi_id", getattr(player.current_poi, "venue_id", None))
        if not destination_id or current_id != destination_id:
            self._apply_missed_shift(player, event_item, reason="absent")
            self.ensure_next_shift_exists(player)
            return {"status": "missed", "pay": 0}

        now = current_game_time.copy()
        if now >= event_item.end_time:
            self._apply_missed_shift(player, event_item, reason="window_elapsed")
            self.ensure_next_shift_exists(player)
            return {"status": "missed", "pay": 0}

        total_minutes = max(30, self._minutes_between(event_item.start_time, event_item.end_time))
        late_minutes = max(0, self._minutes_between(event_item.start_time, now))
        worked_minutes = max(0, total_minutes - late_minutes)
        attendance_ratio = worked_minutes / float(total_minutes)
        payout = int(shift_pay * attendance_ratio)

        remaining = max(0, self._minutes_between(now, event_item.end_time))
        if remaining > 0:
            self.game._advance_time_with_needs(remaining)

        player.money += payout
        player.energy = max(0, player.energy - int(shift_energy * max(0.35, attendance_ratio)))
        player.stress = min(100, player.stress + int(shift_stress * max(0.5, attendance_ratio)))
        player.job_reliability = min(100, player.job_reliability + (2 if attendance_ratio >= 0.95 else 1))

        if attendance_ratio >= 0.95:
            event_type = "job_shift_completed"
            line = f"You finish '{event_item.description}' and get paid ${payout}."
        elif attendance_ratio >= 0.5:
            event_type = "job_shift_late"
            line = f"You arrive late to '{event_item.description}' and get partial pay (${payout})."
        else:
            event_type = "job_shift_partial"
            line = f"You barely catch part of '{event_item.description}' and take home ${payout}."
        self.game.GAME_LOG.add_log_message(line)
        self._record_memory(
            event_type=event_type,
            player=player,
            impact=max(0.7, min(2.5, attendance_ratio * 2.0)),
            metadata={"description": event_item.description, "payout": payout, "attendance_ratio": round(attendance_ratio, 2)},
        )
        self.ensure_next_shift_exists(player)
        return {"status": event_type, "pay": payout, "attendance_ratio": attendance_ratio}

    def run_survival_shift(self, player, shift_type):
        """
        Compatibility fallback only.
        This no longer grants immediate pay and only schedules a real shift event.
        """
        self.ensure_player_state(player)
        self.bootstrap_player_jobs(player)
        mapping = {
            "delivery_shift": "retail_corner_mart",
            "dishwasher_shift": "kitchen_diner",
            "warehouse_shift": "warehouse_distribution",
        }
        job_id = mapping.get(shift_type, player.active_survival_job_id)
        result = self.schedule_job_shift(player, job_id=job_id, start_time=self._next_shift_start(current_game_time.copy()))
        if result.get("ok"):
            self.game.GAME_LOG.add_log_message("Shift booked. You still need to physically get there and work it to get paid.")
        return result

    def run_practice_block(self, player, skill_name, hours):
        """Deprecated: Wraps abstract practice into location-aware presence."""
        from game.place_presence import LocalAction
        self.ensure_player_state(player)
        if not player.current_poi:
            return {"ok": False, "reason": "wrong_location"}

        # Check if the engine actually offers this action at this location
        offered_actions = self.game.location_action_engine.generate_actions(player, player.current_poi, player.current_location)
        if not any(a.action_id == "practice_music" for a in offered_actions):
            return {"ok": False, "reason": "wrong_location"}

        # Hand off to the engine. Validation happens there.
        dummy_action = LocalAction(f"practice_music:{skill_name}", "Practice", int(hours * 60), tags=["practice"])
        res = self.game.location_action_engine.execute_action(player, player.current_poi, player.current_location, dummy_action, self.game._advance_time_with_needs, self.game.GAME_LOG)
        return {"ok": res.get("ok", False), "skill_name": skill_name, "hours": hours, "reason": res.get("reason_code", "failed")}

    def run_open_mic_set(self, player):
        """Deprecated: Wraps abstract open mic into location-aware presence."""
        from game.place_presence import LocalAction
        self.ensure_player_state(player)
        if not player.current_poi:
            return {"ok": False, "reason": "wrong_location"}

        # Check if the engine actually offers this action at this location
        offered_actions = self.game.location_action_engine.generate_actions(player, player.current_poi, player.current_location)
        if not any(a.action_id == "perform_open_mic" for a in offered_actions):
            return {"ok": False, "reason": "wrong_location"}

        # Hand off to the engine. Validation happens there.
        dummy_action = LocalAction("perform_open_mic", "Perform Open Mic", 60, tags=["performance"])
        res = self.game.location_action_engine.execute_action(player, player.current_poi, player.current_location, dummy_action, self.game._advance_time_with_needs, self.game.GAME_LOG)

        if res.get("ok"):
            return {"ok": True, "tips": res.get("tips", 0), "fame_gain": res.get("fame_gain", 0), "score": res.get("open_mic_score", 0)}
        return {"ok": False, "reason": res.get("reason_code", "failed")}

    def purchase_essential_item(self, player, item_id):
        """Deprecated: Wraps abstract purchase into location-aware presence."""
        from game.place_presence import LocalAction
        self.ensure_player_state(player)
        if not player.current_poi:
            return {"ok": False, "reason": "wrong_location"}

        from game_data.gear_catalog import GEAR_CATALOG
        item = GEAR_CATALOG.get(item_id)
        if not item:
            return {"ok": False, "reason": "missing_item"}

        cost = item.cost

        # For wrappers, the action must truthfully execute through the engine as one of the
        # approved generated actions. If it's strings, use buy_strings. If gear, use buy_essential_gear.
        # Otherwise, the engine does not support buying it here.
        action_id_map = {
            "guitar_strings_basic": "buy_strings",
            "worn_acoustic_guitar": "buy_essential_gear"
        }
        mapped_action_id = action_id_map.get(item_id)
        if not mapped_action_id:
             return {"ok": False, "reason": "unsupported_item"}

        # Check if the engine actually offers this action at this location to fail cleanly
        offered_actions = self.game.location_action_engine.generate_actions(player, player.current_poi, player.current_location)
        if not any(a.action_id == mapped_action_id for a in offered_actions):
            return {"ok": False, "reason": "wrong_location"}

        # Hand off to the engine. Validation happens there.
        dummy_action = LocalAction(mapped_action_id, f"Buy {item_id}", 15, cost=cost, tags=["shopping"])
        res = self.game.location_action_engine.execute_action(player, player.current_poi, player.current_location, dummy_action, self.game._advance_time_with_needs, self.game.GAME_LOG)

        if res.get("ok"):
            # Provide gear if granted
            if item_id in res.get("item_grants", []):
                if player.add_gear(item):
                    return {"ok": True, "item_id": item_id, "cost": cost, "reason": ""}
                else:
                    # Rare failure, must refund
                    player.money += cost
                    return {"ok": False, "item_id": item_id, "reason": "inventory_full"}
            else:
                return {"ok": False, "reason": "failed"}

        return {"ok": False, "item_id": item_id, "cost": cost, "reason": res.get("reason_code", "failed")}

    def apply_time_advance(self, player, start_time, end_time):
        if not player:
            return
        self.ensure_player_state(player)
        start_idx = self._day_index(start_time)
        end_idx = self._day_index(end_time)
        if end_idx <= start_idx:
            return
        for _ in range(end_idx - start_idx):
            self._apply_daily_survival(player)

    def _apply_daily_survival(self, player):
        player.early_life_days_elapsed += 1
        food_cost = 7
        if player.money >= food_cost:
            player.money -= food_cost
            player.hunger = max(0, player.hunger - 8)
            player.energy = min(100, player.energy + 4)
        else:
            player.hunger = min(100, player.hunger + 8)
            player.health = max(0, player.health - 2)
            player.stress = min(100, player.stress + 5)
            self.game.GAME_LOG.add_log_message("You skip meals to stretch cash. Hunger and stress rise.")
        if player.early_life_days_elapsed % 7 == 0:
            self._apply_lodging_payment(player)

    def _apply_lodging_payment(self, player):
        tier = self.LODGING[player.lodging_tier]
        if player.money >= tier.weekly_cost:
            player.money -= tier.weekly_cost
            player.comfort = max(player.comfort, tier.comfort_floor)
            self.game.GAME_LOG.add_log_message(f"Lodging paid for {player.lodging_tier.replace('_', ' ')} (${tier.weekly_cost}).")
            return
        self.game.GAME_LOG.add_log_message("You can't cover lodging this week.")
        current_idx = self.LODGING_ORDER.index(player.lodging_tier)
        if current_idx < len(self.LODGING_ORDER) - 1:
            player.lodging_tier = self.LODGING_ORDER[current_idx + 1]
            player.stress = min(100, player.stress + tier.stress_on_miss + 3)
            self.game.GAME_LOG.add_log_message(f"You downgrade to {player.lodging_tier.replace('_', ' ')} to stay afloat.")
        else:
            player.stress = min(100, player.stress + tier.stress_on_miss + 6)
            player.energy = max(0, player.energy - 12)
            player.comfort = max(0, player.comfort - 10)
            self.game.GAME_LOG.add_log_message("Sleeping rough wears you down this week.")

    def _apply_missed_shift(self, player, event_item, reason):
        player.stress = min(100, player.stress + 9)
        player.job_reliability = max(0, player.job_reliability - 6)
        if reason == "window_elapsed":
            line = f"You missed '{event_item.description}' because the shift window already passed."
            event_type = "job_shift_missed_window"
        else:
            line = f"You missed '{event_item.description}' because you weren't at the job site."
            event_type = "job_shift_missed_absence"
        self.game.GAME_LOG.add_log_message(line)
        self._record_memory(
            event_type=event_type,
            player=player,
            impact=2.0,
            metadata={"description": event_item.description, "reason": reason},
        )

    def _ensure_job_sites_for_location(self, location):
        existing_ids = {poi.poi_id for poi in location.points_of_interest}
        for job in self.JOB_CATALOG:
            site_id = self._job_site_id(location, job.job_id)
            if site_id in existing_ids:
                continue
            poi = PointOfInterest(
                poi_id=site_id,
                name=job.location_name,
                description=f"Survival work site for {job.title.lower()}.",
                category=job.location_category,
                parent_location_id=location.name,
            )
            location.add_poi(poi)
        location.ensure_intra_city_connectivity()
        if hasattr(self.game, "_build_poi_venue_id_map"):
            self.game._build_poi_venue_id_map()

    def _find_job_site(self, location, job_id):
        site_id = self._job_site_id(location, job_id)
        for poi in location.points_of_interest:
            if poi.poi_id == site_id:
                return poi
        return None

    def _job_site_id(self, location, job_id):
        base = location.name.lower().replace(" ", "_")
        return f"{base}_{job_id}"

    def _next_shift_start(self, now):
        start = now.copy()
        if start.hour >= 18:
            start.add_days(1)
            start.hour = 8
            start.minute = 0
        elif start.hour < 8:
            start.hour = 8
            start.minute = 0
        else:
            start.advance_time(60)
            start.minute = 0
        return start

    def _record_memory(self, event_type, player, impact, metadata=None):
        if not hasattr(self.game, "world_memory"):
            return
        entry = WorldMemoryEntry(
            event_type=event_type,
            involved_entities=[player.name],
            location=player.current_location.name if player.current_location else None,
            timestamp=current_game_time.copy(),
            tags=["survival", "early_career", "work" if "job_" in event_type else "life"],
            impact_score=impact,
            metadata=metadata or {},
            source_key=f"{player.name}:{event_type}:{current_game_time.get_time_string_for_schedule()}",
        )
        self.game.world_memory.add(entry)

    def _minutes_between(self, earlier, later):
        return int(max(0, (self._day_index(later) - self._day_index(earlier)) * 24 * 60 + (later.hour - earlier.hour) * 60 + (later.minute - earlier.minute)))

    def _day_index(self, game_time):
        return (game_time.year * 360) + (game_time.month * 30) + game_time.day
