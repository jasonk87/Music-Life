from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
import random

from game.game_time import current_game_time


CATEGORY_TO_PLACE_TYPE = {
    "PAWN_SHOP": "pawn_shop",
    "ACCOMMODATION_HOTEL": "hotel",
    "ACCOMMODATION_MOTEL": "motel",
    "HOME": "home",
    "STUDIO_RECORDING": "studio_recording",
    "VENUE_CLUB": "club",
    "VENUE_BAR": "bar",
    "VENUE_GENERAL": "venue",
    "SHOP_MUSIC": "music_store",
    "DOWNTOWN": "street",
    "TRANSPORT_GAS": "gas_station",
    "CIVIC_COURTHOUSE": "courthouse",
}


@dataclass
class PlaceProfile:
    canonical_id: str
    place_type: str
    district: str
    hours: str
    services: List[str]
    risk_profile: str
    cost_band: str
    interaction_tags: List[str]
    display_name: str


@dataclass
class LocalAction:
    action_id: str
    label: str
    minutes: int
    cost: int = 0
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def menu_label(self) -> str:
        cost_text = f" - ${self.cost}" if self.cost > 0 else ""
        return f"{self.label} ({self.minutes}m{cost_text})"


@dataclass
class EncounterResult:
    encounter_type: str
    reason_code: str
    context: Dict[str, str]


class PlaceProfileBuilder:
    @staticmethod
    def build(place_obj, location_obj=None) -> PlaceProfile:
        place_id = getattr(place_obj, "poi_id", getattr(place_obj, "venue_id", "unknown_place"))
        category = str(getattr(place_obj, "category", "GENERAL") or "GENERAL")
        place_type = CATEGORY_TO_PLACE_TYPE.get(category, category.lower())

        district = getattr(place_obj, "district", None) or getattr(place_obj, "parent_location_id", None) or getattr(location_obj, "name", "Unknown District")
        hours = getattr(place_obj, "hours", None) or "always_open"
        services = list(getattr(place_obj, "interaction_options", []) or [])

        lowered = place_type.lower()
        if "hotel" in lowered:
            risk_profile = "low"
            cost_band = "mid"
        elif "motel" in lowered:
            risk_profile = "medium"
            cost_band = "budget"
        elif lowered in {"street", "downtown", "bar", "club"}:
            risk_profile = "high"
            cost_band = "mid"
        elif lowered in {"pawn_shop", "gas_station"}:
            risk_profile = "medium"
            cost_band = "budget"
        else:
            risk_profile = "medium"
            cost_band = "mid"

        tags = [lowered, risk_profile, cost_band]
        if "venue" in lowered or lowered in {"club", "bar"}:
            tags.append("music_scene")
        if lowered in {"street", "downtown"}:
            tags.append("public")

        return PlaceProfile(
            canonical_id=place_id,
            place_type=lowered,
            district=str(district),
            hours=hours,
            services=services,
            risk_profile=risk_profile,
            cost_band=cost_band,
            interaction_tags=tags,
            display_name=getattr(place_obj, "name", place_id),
        )


class ContextualEncounterEngine:
    def maybe_trigger(self, player, profile: PlaceProfile, action: LocalAction, rng: Optional[random.Random] = None, visibility_pressure: float = 0.0) -> Optional[EncounterResult]:
        rng = rng or random
        visibility = max(0, player.fame - 30)
        public_place = profile.place_type in {"street", "downtown", "bar", "club", "venue"}
        busy_hour = current_game_time.hour >= 18 or current_game_time.hour <= 1
        risk_bonus = 0.1 if profile.risk_profile == "high" else 0.05 if profile.risk_profile == "medium" else 0.0

        trigger_chance = 0.04 + risk_bonus
        if public_place:
            trigger_chance += 0.05
        if busy_hour:
            trigger_chance += 0.04
        if visibility > 0:
            trigger_chance += min(0.25, visibility / 250.0)
        if player.has_bodyguard:
            trigger_chance = max(0.01, trigger_chance - 0.05)
        trigger_chance += min(0.25, visibility_pressure / 40.0)

        if rng.random() > trigger_chance:
            return None

        if visibility > 25 and public_place:
            encounter_type = "fan_encounter"
            reason_code = "public_visibility_pressure"
        elif profile.risk_profile == "high" and not player.has_bodyguard:
            encounter_type = "harassment_risk"
            reason_code = "high_risk_public_no_security"
        elif action.action_id.startswith("network") or "network" in action.tags:
            encounter_type = "local_opportunity"
            reason_code = "networking_surface"
        elif profile.place_type in {"pawn_shop", "music_store", "hotel", "motel"}:
            encounter_type = "staff_vendor_interaction"
            reason_code = "service_contact"
        else:
            encounter_type = "petty_crime_attempt"
            reason_code = "street_opportunism"

        return EncounterResult(
            encounter_type=encounter_type,
            reason_code=reason_code,
            context={
                "place_type": profile.place_type,
                "district": profile.district,
                "hour": str(current_game_time.hour),
                "fame": str(player.fame),
                "security": "yes" if player.has_bodyguard else "no",
                "action": action.action_id,
            },
        )


class LocationActionEngine:
    def __init__(self):
        self.encounters = ContextualEncounterEngine()

    def _has_performance_loadout(self, player) -> bool:
        has_instrument = False
        has_strings = False
        for item in getattr(player, "gear_inventory", []) or []:
            if getattr(item, "is_broken", False):
                continue
            gear_type = str(getattr(item, "gear_type", "") or "")
            item_id = str(getattr(item, "item_id", "") or "").lower()
            item_name = str(getattr(item, "name", "") or "").lower()
            if gear_type.startswith("INSTRUMENT"):
                has_instrument = True
            if "string" in item_id or "string" in item_name:
                has_strings = True
        return has_instrument and has_strings

    def _canonicalize_action(self, player, place_obj, location_obj, requested_action: LocalAction) -> Optional[LocalAction]:
        offered_actions = self.generate_actions(player, place_obj, location_obj)
        requested_id = requested_action.action_id

        # Dynamic practice actions can encode a target skill (e.g. practice_music:vocals)
        lookup_id = "practice_music" if requested_id.startswith("practice_music") else requested_id

        canonical = next((a for a in offered_actions if a.action_id == lookup_id), None)
        if not canonical:
            return None

        if requested_id.startswith("practice_music"):
            minutes = max(1, int(requested_action.minutes))
            return LocalAction(
                action_id=requested_id,
                label=canonical.label,
                minutes=minutes,
                cost=canonical.cost,
                description=canonical.description,
                tags=list(canonical.tags),
            )

        return LocalAction(
            action_id=canonical.action_id,
            label=canonical.label,
            minutes=canonical.minutes,
            cost=canonical.cost,
            description=canonical.description,
            tags=list(canonical.tags),
        )

    def generate_actions(self, player, place_obj, location_obj=None) -> List[LocalAction]:
        profile = PlaceProfileBuilder.build(place_obj, location_obj)
        actions: List[LocalAction] = []

        if profile.place_type == "pawn_shop":
            actions.extend([
                LocalAction("browse_gear", "Browse gear shelves", 20, tags=["shopping"]),
                LocalAction("buy_strings", "Buy strings", 15, cost=12, tags=["shopping"]),
                LocalAction("buy_essential_gear", "Buy essential gear", 30, cost=50, tags=["shopping"]),
                LocalAction("pawn_item", "Pawn an item", 25, tags=["cash"]),
            ])
        elif profile.place_type in {"hotel", "motel"}:
            nightly = 80 if profile.place_type == "hotel" else 45
            actions.extend([
                LocalAction("rent_room", "Rent a room", 15, cost=nightly, tags=["rest"]),
                LocalAction("sleep_rest", "Sleep/Rest", 120, tags=["rest", "recovery"]),
                LocalAction("practice_music", "Practice lightly", 60, tags=["practice"]),
                LocalAction("shower_reset", "Take a shower", 20, tags=["recovery"]),
                LocalAction("stash_belongings", "Stash belongings", 20, tags=["logistics"]),
            ])
        elif profile.place_type == "home":
            actions.extend([
                LocalAction("sleep_rest", "Sleep/Rest", 120, tags=["rest", "recovery"]),
                LocalAction("practice_music", "Practice music", 60, tags=["practice"]),
                LocalAction("shower_reset", "Take a shower", 20, tags=["recovery"]),
                LocalAction("stash_belongings", "Stash belongings", 20, tags=["logistics"]),
            ])
        elif profile.place_type == "studio_recording":
            actions.extend([
                LocalAction("practice_music", "Intensive practice", 60, tags=["practice"]),
            ])
        elif profile.place_type in {"street", "downtown"}:
            actions.extend([
                LocalAction("walk_district", "Walk the district", 30, tags=["public"]),
                LocalAction("look_for_food", "Look for cheap food", 25, cost=8, tags=["public"]),
                LocalAction("meet_people", "Try to meet people", 40, tags=["network"]),
            ])
        elif profile.place_type in {"club", "bar"}:
            actions.extend([
                LocalAction("go_inside", "Go inside", 20, cost=10, tags=["public"]),
                LocalAction("network_scene", "Network with the scene", 45, tags=["network", "public"]),
                LocalAction("have_drink", "Have a drink", 25, cost=9, tags=["public"]),
                LocalAction("perform_open_mic", "Perform Open Mic", 60, tags=["performance", "public"]),
            ])
        elif profile.place_type == "venue":
            actions.extend([
                LocalAction("check_in", "Check in at venue", 20, tags=["logistics"]),
                LocalAction("wait_backstage", "Wait near stage", 30, tags=["public"]),
                LocalAction("explore_area", "Explore nearby blocks", 30, tags=["public"]),
                LocalAction("perform_open_mic", "Perform Open Mic", 60, tags=["performance", "public"]),
            ])
        elif profile.place_type == "music_store":
            actions.extend([
                LocalAction("browse_instruments", "Browse instruments", 25, tags=["shopping"]),
                LocalAction("buy_strings", "Buy strings", 15, cost=12, tags=["shopping"]),
                LocalAction("buy_essential_gear", "Buy essential gear", 30, cost=50, tags=["shopping"]),
                LocalAction("test_instrument", "Test instrument", 15, tags=["practice", "shopping"]),
                LocalAction("talk_staff", "Talk to staff", 20, tags=["network"]),
            ])
        else:
            actions.extend([
                LocalAction("look_around", "Look around", 20, tags=["public"]),
                LocalAction("take_break", "Take a quick break", 20, tags=["recovery"]),
            ])

        return actions

    def execute_action(
        self,
        player,
        place_obj,
        location_obj,
        action: LocalAction,
        advance_time: Callable[[int], None],
        logger,
        rng: Optional[random.Random] = None,
        visibility_pressure: float = 0.0,
    ) -> Dict:
        profile = PlaceProfileBuilder.build(place_obj, location_obj)
        canonical_action = self._canonicalize_action(player, place_obj, location_obj, action)
        if canonical_action is None:
            return {
                "ok": False,
                "reason_code": "action_not_available_here",
                "explanation": "That action is not available at this location.",
            }
        action = canonical_action

        # --- VALIDATION PHASE ---
        if action.cost > player.money:
            return {
                "ok": False,
                "reason_code": "insufficient_funds",
                "explanation": f"You need ${action.cost} for {action.label}.",
            }

        if action.action_id == "sleep_rest":
            if profile.place_type == "home" and not getattr(player, "has_home", False):
                return {"ok": False, "reason_code": "no_home", "explanation": "You do not have a home anymore."}
            if profile.place_type in {"hotel", "motel"}:
                # Check for active rental
                rental = getattr(player, "rented_accommodation_info", None)
                poi_id = getattr(place_obj, "poi_id", None)
                if not rental or not poi_id or rental.get("poi_id") != poi_id:
                    return {"ok": False, "reason_code": "no_rental", "explanation": "You need to rent a room here first."}
                checkout_time = rental.get("checkout_time_obj")
                if checkout_time and current_game_time > checkout_time:
                    player.rented_accommodation_info = None
                    return {"ok": False, "reason_code": "rental_expired", "explanation": "Your room rental has expired."}

        if action.action_id.startswith("practice_music"):
            if profile.place_type not in {"home", "hotel", "motel", "studio_recording"}:
                return {"ok": False, "reason_code": "wrong_location", "explanation": "You cannot practice intensely here."}

        if action.action_id == "perform_open_mic":
            # Check if there is an actual event going on
            events = getattr(place_obj, "events", getattr(place_obj, "events_hosted", []))
            has_event = any(e.event_type == "OPEN_MIC" for e in events)
            has_other_event = any(e.event_type != "OPEN_MIC" for e in events)

            if has_other_event and not has_event:
                return {"ok": False, "reason_code": "competing_event", "explanation": "There is already another event scheduled here."}

            if not has_event and current_game_time.hour < 18:
                return {"ok": False, "reason_code": "wrong_time", "explanation": "There is no open mic event, and it doesn't start until evening (18:00+)."}
            if player.energy < 10:
                return {"ok": False, "reason_code": "exhausted", "explanation": "You are too exhausted to perform."}
            if not self._has_performance_loadout(player):
                return {
                    "ok": False,
                    "reason_code": "missing_required_loadout",
                    "explanation": "You need a working instrument and spare strings to perform.",
                }

        # --- EXECUTION PHASE ---
        if action.cost:
            player.money -= action.cost

        advance_time(action.minutes)

        # Baseline local action effects.
        player.energy = max(0, player.energy - max(1, int(action.minutes / 20)))
        player.stress = min(100, player.stress + (1 if "public" in action.tags else 0))

        if action.action_id in {"shower_reset", "take_break"}:
            player.stress = max(0, player.stress - 6)
            player.comfort = min(100, player.comfort + 8)
        elif action.action_id in {"network_scene", "meet_people", "talk_staff"}:
            player.inspiration = min(100, player.inspiration + 5)
        elif action.action_id in {"have_drink"}:
            player.stress = max(0, player.stress - 4)
            player.health = max(0, player.health - 1)
        elif action.action_id in {"look_for_food"}:
            player.hunger = max(0, player.hunger - 12)

        encounter = self.encounters.maybe_trigger(player, profile, action, rng=rng, visibility_pressure=visibility_pressure)

        result = {
            "ok": True,
            "action_id": action.action_id,
            "minutes": action.minutes,
            "cost": action.cost,
            "place_type": profile.place_type,
            "encounter": None,
            "item_grants": [],
            "explanation": f"You spend {action.minutes} minutes: {action.label}.",
        }

        if action.action_id == "buy_strings" or action.action_id == "buy_specific_item:guitar_strings_basic":
            result["item_grants"].append("guitar_strings_basic")
        elif action.action_id == "buy_essential_gear" or action.action_id == "buy_specific_item:worn_acoustic_guitar":
            result["item_grants"].append("worn_acoustic_guitar")

        if action.action_id.startswith("practice_music"):
            parts = action.action_id.split(":")
            target_skill = parts[1] if len(parts) > 1 else "guitar"
            hours = action.minutes / 60.0

            if profile.place_type == "studio_recording":
                player.practice_skill(target_skill, hours * 1.0)
                if target_skill == "guitar": player.practice_skill("vocals", hours * 1.0)
                result["explanation"] = f"You practice intensely in the studio."
            elif profile.place_type == "home":
                player.practice_skill(target_skill, hours * 0.8)
                result["explanation"] = f"You practice {target_skill} at home."
            else:
                player.practice_skill(target_skill, hours * 0.5)
                result["explanation"] = f"You squeeze in some light practice."

        if action.action_id == "test_instrument":
            player.practice_skill("guitar", 0.2)
            result["explanation"] = "You noodle around on a display instrument."

        if action.action_id == "sleep_rest":
            rest_quality = getattr(place_obj, "rest_quality", 0.5)
            hours = action.minutes / 60.0
            energy_gain = int(hours * 5 * (1 + rest_quality))
            stress_reduction = int(hours * 3 * (1 + rest_quality))
            player.energy = min(100, player.energy + energy_gain)
            player.stress = max(0, player.stress - stress_reduction)
            result["explanation"] = f"You sleep for {int(hours)} hours."

        if action.action_id == "perform_open_mic":
            stage = player.skills.get("stage_presence", 0)
            vocals = player.skills.get("vocals", 0)
            songwriting = player.skills.get("songwriting", 0)
            score = (stage * 2.2) + (vocals * 1.8) + (songwriting * 1.4) + random.uniform(-2.5, 2.5)
            score += max(-3, int((player.energy - 40) / 20))
            score -= int(player.stress / 25)
            tips = max(0, int(score * 1.3))
            fame_gain = 2 if score >= 16 else 1 if score >= 10 else 0

            player.money += tips
            player.fame += fame_gain
            result["explanation"] = f"You played a short open mic set. Tips: ${tips}. Fame +{fame_gain}."
            result["open_mic_score"] = score
            result["tips"] = tips
            result["fame_gain"] = fame_gain

        if encounter:
            result["encounter"] = {
                "encounter_type": encounter.encounter_type,
                "reason_code": encounter.reason_code,
                "context": encounter.context,
            }
            if encounter.encounter_type == "fan_encounter":
                player.stress = min(100, player.stress + 4)
                player.fame += 1
            elif encounter.encounter_type == "harassment_risk":
                player.stress = min(100, player.stress + 8 + int(min(6, visibility_pressure / 6)))
                if not player.has_bodyguard:
                    player.health = max(0, player.health - 1)
            elif encounter.encounter_type == "local_opportunity":
                player.inspiration = min(100, player.inspiration + 8)

        return result
