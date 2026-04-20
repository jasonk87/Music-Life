import pygame
import sys
import collections
import os
import json
import pickle
import random

from game.player import Player
from game.location import Location
from game.venue import Venue
from game.poi import PointOfInterest
from game.event import Event
from game.npc import RelationshipStatus
from game.game_time import current_game_time, advance_game_time, get_current_time_str, calculate_player_age, GameTime
from game.contract import Contract
from game.dialogue import generate_npc_response, NPC_PERSONALITIES
from game.random_events import check_for_random_event, check_for_post_gig_random_event
from game.song import Song
from game.gear import GearItem
from game.pygame_ui import PygameUI
from game_data.gear_catalog import GEAR_CATALOG
from game.npc import NPC
from game_data.vehicle_catalog import VEHICLE_CATALOG
from game.traits import TRAIT_CATALOG
from game.chart import Chart
from game.feedback_generator import generate_feedback_for_song, SOURCES, generate_feedback_for_album
from game.sound import SoundManager
from game.ascii_art import ART
from game.performance import PerformanceManager
from game.obligation_resolver import ObligationResolver
from game.obligation_consequences import ObligationConsequenceEngine
from game.place_presence import LocationActionEngine
from game.inventory_loadout import InventoryLoadoutService
from game.npc_world_sim import NPCWorldSimulator
from game.world_memory import WorldMemoryStore, WorldMemoryEntry
from game.visibility_system import VisibilitySystem, PublicSignal
from game.delegation_roles import DelegationSystem
from game.transit_phase import TransitLayer
from game.ui_signals import UISignalLayer
from game.llm_interaction_layer import InteractionContextBuilder, LLMInteractionEngine, SocialMediaExpressionLayer
from game.scarcity_interference import ScarcityAvailabilitySystem, PublicInterferenceSystem
from game.trends import TrendManager
from game.band_drama import check_for_band_drama, resolve_weekly_wages
from game.staff import StaffMember
from game.themes import THEME_CATALOG
from game.album import Album
from game.marketing import CAMPAIGN_TYPES
from game.merch import MerchItem, MERCH_TEMPLATES
from game.rivals import simulate_rivals, get_news_feed
from game.celebrity_events import check_for_celebrity_event

class Game:
    def __init__(self, ui):
        self.ui = ui
        self.sound_manager = SoundManager()
        self.player = None
        self.running = True
        self.game_state = "title_screen"
        self.character_menu_state = "main"
        self.explore_menu_state = "location"
        self.phone_menu_state = "main"
        self.music_menu_state = "main"
        self.web_menu_state = "main"
        self.text_to_view = ""
        self.active_performance = None
        self.performance_setlist = []
        self.performance_manager = None # Added manager
        self.travel_manager = None # Added travel manager
        self.performance_log = []
        self.performance_stage = None
        self.band_menu_state = "main"
        self._local_action_lookup = {}
        self.selected_contact_id = None
        self.selected_poi = None
        self.selected_npc = None
        self.conversation_history = []
        self.player_input = ""
        self.songwriting_stage = None
        self.song_in_progress = {}
        self.SONG_GENRES = ["Rock", "Pop", "Folk", "Indie", "Electronic", "Blues"]
        self.trend_manager = TrendManager(self.SONG_GENRES)
        self.OPPORTUNITY_CATALOG = {
            "radio_interview_local": {
                "name": "Local Radio Interview",
                "trigger": lambda p, g: p.fame >= 20 and any(s.is_released and s.song_quality >= 0.6 for s in p.songs_written),
                "action_text": "Call K-ROK Radio for interview",
                "type": "phone"
            },
            "music_blog_feature": {
                "name": "IndiePulse Music Blog Feature",
                "trigger": lambda p, g: p.fame >= 35 and any(s.is_released for s in p.songs_written),
                "action_text": "Respond to email from IndiePulse blog",
                "type": "phone"
            },
            "battle_of_the_bands_local": {
                "name": "Hometown Battle of the Bands",
                "trigger": lambda p, g: p.fame >= 60 and len(p.songs_written) >= 2,
                "action_text": "Sign up for Battle of the Bands",
                "type": "venue_event",
                "venue_id": "hometown_community_hall"
            },
            "autograph_signing": {
                "name": "Autograph Signing",
                "trigger": lambda p, g: p.current_tour_id is not None and any(poi.category == "SHOP_MUSIC" for poi in g.player.current_location.points_of_interest),
                "action_text": "Hold an autograph signing session",
                "type": "poi_interaction",
                "poi_id_getter": lambda g: next((poi.poi_id for poi in g.player.current_location.points_of_interest if poi.category == "SHOP_MUSIC"), None)
            }
        }

        self.SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

        self.WORLD_MAP = {}
        self.NPC_REGISTRY = {}
        self.PLAYER_HOME_POI_ID_GLOBAL = None
        self.ACTIVE_CHARTS = []
        self.LAST_CHART_UPDATE_DAY = -1
        self.last_opportunity_check_day = -1
        self.TOURS = []

        self._poi_venue_id_map = {}

        self.GAME_LOG = self.ui
        self.obligation_resolver = ObligationResolver(self)
        self.obligation_consequence_engine = ObligationConsequenceEngine()
        self.location_action_engine = LocationActionEngine()
        self.inventory_service = InventoryLoadoutService()
        self.npc_world_sim = NPCWorldSimulator(self)
        self.world_memory = WorldMemoryStore()
        self.visibility_system = VisibilitySystem()
        self.delegation_system = DelegationSystem()
        self.transit_layer = TransitLayer()
        self.transit_session = None
        self.ui_signals = UISignalLayer(self)
        self.llm_context_builder = InteractionContextBuilder(self)
        self.llm_interactions = LLMInteractionEngine(self)
        self.social_expression = SocialMediaExpressionLayer()
        self.scarcity_system = ScarcityAvailabilitySystem()
        self.public_interference_system = PublicInterferenceSystem()
        self._local_action_lookup = {}
        self.performance_requirement_penalty = 1.0

    def _build_poi_venue_id_map(self):
        self._poi_venue_id_map.clear()
        for location in self.WORLD_MAP.values():
            for poi in location.points_of_interest: self._poi_venue_id_map[poi.poi_id] = poi
            for venue in location.venues: self._poi_venue_id_map[venue.venue_id] = venue

    def get_poi_or_venue_by_id(self, target_id):
        return self._poi_venue_id_map.get(target_id)

    def _get_day_of_week_name(self, day_number_in_month):
        return ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][(day_number_in_month - 1) % 7]

    def _get_time_slot_key(self, gt_obj):
        day_name = self._get_day_of_week_name(gt_obj.day); hour = gt_obj.hour
        day_type = "Weekend" if day_name in ["Saturday", "Sunday"] else "Weekday"
        if 6 <= hour <= 11: period = "Morning"
        elif 12 <= hour <= 17: period = "Afternoon"
        elif 18 <= hour <= 23: period = "Evening"
        else: period = "Night"
        return f"{day_type}_{period}"

    def _calculate_song_component_quality(self, primary_skill, secondary_skill=None, weight=0.75):
        """Calculates the quality of a song component based on player or band skills."""
        skills_to_use = self.player.band.band_skills if self.player.band else self.player.skills

        primary_skill_val = skills_to_use.get(primary_skill, 0)
        secondary_skill_val = skills_to_use.get(secondary_skill, 0) if secondary_skill else 0

        # Weighted average of skills
        combined_skill = (primary_skill_val * weight) + (secondary_skill_val * (1 - weight))

        # Add some randomness
        random_factor = random.uniform(0.5, 1.5)

        # Base quality is influenced by skill and randomness
        quality = combined_skill * random_factor

        # Normalize to 0-1 range
        # Let's assume max possible skill effect is around 50 for a quality of 1.0
        # This is a magic number and can be tuned.
        normalized_quality = min(1.0, quality / 50.0)

        return normalized_quality

    def _advance_time_with_needs(self, minutes):
        if minutes <= 0:
            return
        if self.player:
            resolution = self.obligation_resolver.resolve_before_time_advance(minutes)
            self.obligation_consequence_engine.apply_resolution(self.player, resolution, self.GAME_LOG)
            self._record_player_obligation_memory(resolution)
            self.visibility_system.amplify_from_memory(self.world_memory, current_game_time.copy())
            self.npc_world_sim.advance(minutes)
            self.visibility_system.amplify_from_memory(self.world_memory, current_game_time.copy())
            self._apply_visibility_consequence_amplification(resolution)
        advance_game_time(minutes)
        self.process_time_based_player_needs(self.player, minutes)
        self._check_player_survival_state()

    def _record_player_obligation_memory(self, resolution):
        if not resolution or not self.player:
            return

        event_type_map = {
            "missed": "missed_gig",
            "late_but_possible": "late_obligation",
            "reachable": "reachable_obligation",
            "requires_departure_now": "on_time_departure",
        }
        event_type = event_type_map.get(resolution.status)
        if not event_type:
            return

        destination_id = None
        if resolution.item and hasattr(resolution.item, "get_destination_id"):
            destination_id = resolution.item.get_destination_id()

        source_key = None
        if isinstance(getattr(resolution.item, "details", None), dict):
            source_key = resolution.item.details.get("obligation_evaluated_at")
            if source_key:
                source_key = f"{self.player.name}:{event_type}:{source_key}:{destination_id or 'none'}"

        entry = WorldMemoryEntry(
            event_type=event_type,
            involved_entities=[self.player.name],
            location=destination_id,
            timestamp=current_game_time.copy(),
            tags=["professionalism", "reliability"],
            impact_score=3.0 if event_type == "missed_gig" else 1.5,
            metadata={
                "reason_code": getattr(resolution, "reason_code", None),
                "status": resolution.status,
            },
            source_key=source_key,
        )
        self.world_memory.add(entry)

    def _apply_visibility_consequence_amplification(self, resolution):
        if not resolution or not self.player:
            return
        if resolution.status not in {"missed", "late_but_possible"}:
            return

        destination_id = resolution.item.get_destination_id() if resolution.item and hasattr(resolution.item, "get_destination_id") else None
        visibility = self.visibility_system.get_visibility(self.player.name, destination_id)
        public_pressure = visibility.get("public_visibility", 0.0)
        if public_pressure < 6:
            return

        penalty = int(min(8, public_pressure / 4))
        self.player.stress = min(100, self.player.stress + penalty)
        self.player.fame = max(0, self.player.fame - max(1, penalty // 2))
        self.GAME_LOG.add_log_message(
            f"Public exposure amplifies fallout: stress +{penalty}, fame -{max(1, penalty // 2)}."
        )

        self.visibility_system.signals.append(
            PublicSignal(
                signal_type="public_backlash",
                source_entities=[self.player.name],
                location_scope=destination_id,
                timestamp=current_game_time.copy(),
                strength=float(penalty),
                polarity="negative",
                metadata={"source_status": resolution.status},
            )
        )

    def _get_max_genre_gear_boost(self, genre):
        """Finds the highest genre boost from the player's non-broken gear."""
        max_boost = 0.0
        for item in self.player.gear_inventory:
            if not item.is_broken:
                boost = item.get_genre_boost(genre)
                if boost > max_boost:
                    max_boost = boost
        return max_boost

    def _calculate_recording_quality(self, song, studio_quality, producer_bonus=0.0):
        performance_skills = [
            self.player.skills.get("guitar", 0),
            self.player.skills.get("vocals", 0),
            self.player.skills.get("electronic", 0),
            self.player.skills.get("songwriting", 0),
        ]
        best_relevant_skill = max(performance_skills)
        skill_bonus = best_relevant_skill / 100.0

        gear_bonus = self._get_max_genre_gear_boost(song.genre)

        base_quality = (song.song_quality * 0.6) + (studio_quality * 0.4)
        return min(1.0, base_quality + skill_bonus + producer_bonus + gear_bonus)

    def _get_recording_setup(self, poi):
        if not poi:
            return None
        if poi.category == "STUDIO_RECORDING":
            return {
                "label": "studio",
                "title": "Which song would you like to record at the studio?",
                "studio_quality": getattr(poi, "studio_quality", 0.6) or 0.6,
                "base_session_cost": int((getattr(poi, "hourly_rate", 50) or 50) * 4),
                "minutes": 4 * 60,
                "log": f"You book time at {poi.name} and spend 4 focused hours recording.",
                "allow_producer": True,
            }
        if poi.category == "REHEARSAL_STUDIO":
            return {
                "label": "garage demo",
                "title": "Which song would you like to cut as a garage demo?",
                "studio_quality": max(0.35, getattr(poi, "studio_quality", 0.42) or 0.42),
                "base_session_cost": getattr(poi, "hourly_rate", 15) or 15,
                "minutes": 2 * 60,
                "log": f"You set up in {poi.name} and track a rough demo in 2 hours.",
                "allow_producer": False,
            }
        if poi.category == "HOME":
            return {
                "label": "home demo",
                "title": "Which song would you like to record as a home demo?",
                "studio_quality": max(0.25, getattr(poi, "studio_quality", 0.3) or 0.3),
                "base_session_cost": 0,
                "minutes": 2 * 60,
                "log": "You piece together a rough home demo over 2 hours.",
                "allow_producer": False,
            }
        return None

    def _reset_transient_runtime_state(self):
        self.active_performance = None
        self.performance_setlist = []
        self.performance_manager = None
        self.travel_manager = None
        self.transit_session = None
        self.performance_stage = None
        self.selected_contact_id = None
        self.selected_poi = None
        self.selected_npc = None
        self.conversation_history = []
        self.player_input = ""
        self.text_to_view = ""
        self.explore_menu_state = "location"
        self.phone_menu_state = "main"
        self.music_menu_state = "main"
        self.web_menu_state = "main"
        self.character_menu_state = "main"
        self.band_menu_state = "main"
        self._local_action_lookup = {}
        self.performance_requirement_penalty = 1.0

    def _normalize_opportunity_state(self):
        normalized = {}
        for opp_id, opp_details in self.player.active_opportunities.items():
            if isinstance(opp_details, dict):
                status = opp_details.get("status", "available")
                normalized[opp_id] = {"status": status, **{k: v for k, v in opp_details.items() if k != "status"}}
            else:
                normalized[opp_id] = {"status": str(opp_details) if opp_details else "available"}
        self.player.active_opportunities = normalized

    def _has_active_room_rental(self, poi):
        rental = self.player.rented_accommodation_info
        if not rental or not poi or not hasattr(poi, "poi_id"):
            return False
        if rental.get("poi_id") != poi.poi_id:
            return False
        checkout_time = rental.get("checkout_time_obj")
        if checkout_time and current_game_time > checkout_time:
            self.player.rented_accommodation_info = None
            return False
        return True

    def _get_intra_city_connection(self, origin_poi, destination_poi):
        if not self.player or not self.player.current_location or not origin_poi or not destination_poi:
            return None
        origin_id = origin_poi.poi_id if hasattr(origin_poi, "poi_id") else origin_poi.venue_id
        destination_id = destination_poi.poi_id if hasattr(destination_poi, "poi_id") else destination_poi.venue_id
        return self.player.current_location.intra_city_poi_connections.get(frozenset((origin_id, destination_id)))

    def _build_intra_city_mode_options(self, connection_details):
        if not connection_details:
            return {}

        mode_options = {}
        for mode_key in ["walk", "bike", "taxi"]:
            details = connection_details.get(mode_key)
            if not details:
                continue

            time_cost = details.get("time", 0)
            money_cost = details.get("cost", 0)
            if details.get("requires_bike") and not self.player.has_bike:
                mode_options[f"{mode_key}_locked"] = f"{mode_key.capitalize()} ({time_cost} min, ${money_cost}) - Need a bike"
            else:
                price_text = "Free" if money_cost == 0 else f"${money_cost}"
                mode_options[mode_key] = f"{mode_key.capitalize()} ({time_cost} min, {price_text})"
        return mode_options

    def _get_public_travel_mode(self, travel_details, departure_poi):
        route_method = str(travel_details.get("method", "")).strip().lower()
        if route_method in {"bus", "train", "plane"}:
            return route_method
        if departure_poi and getattr(departure_poi, "category", "") == "TRANSPORT_AIRPORT":
            return "plane"
        return "bus"

    def _public_travel_requires_hub(self, travel_mode, departure_poi):
        if not departure_poi:
            return False
        category = getattr(departure_poi, "category", "")
        if travel_mode == "plane":
            return category == "TRANSPORT_AIRPORT"
        if travel_mode in {"bus", "train"}:
            return category in {"TRANSPORT_BUS", "TRANSPORT_AIRPORT"}
        return False

    def _open_direct_npc_interaction(self, npc):
        if not npc:
            self.GAME_LOG.add_log_message("No one is available to talk right now.")
            self.explore_menu_state = "poi"
            return
        self.selected_npc = npc
        if npc.npc_id not in self.player.contacts:
            self.player.contacts.append(npc.npc_id)
            self.GAME_LOG.add_log_message(f"You added {npc.name} to your contacts.")
        self.explore_menu_state = "npc_interaction_menu"

    def _get_progress_hint(self):
        released_songs = [song for song in self.player.songs_written if song.is_released]
        recorded_songs = [song for song in self.player.songs_written if song.is_recorded]
        if not self.player.has_home and not self.player.rented_accommodation_info:
            return "You need cash, shelter, and a place to recover before the rest of the run collapses."
        if self.player.money < 40 and self.player.fame < 20:
            return "Take survival shifts, eat, and stay functional while you build your first real opening."
        if not self.player.songs_written:
            return "Write your first song at home or in a quiet spot."
        if not recorded_songs:
            return "Travel to a recording studio and record your strongest song."
        if not released_songs:
            return "Open Phone > Music and release your recorded single."
        if self.player.fame < 20:
            return "Promote your release, play open mics, and build to 20 fame."
        if self.player.current_location and self.player.current_location.name == "Your Hometown":
            return "Head to City Center for studios, PR, labels, and club gigs."
        if self.player.fame < 40:
            return "Build to 40 fame for label demos and stronger media opportunities."
        return "Use contacts, marketing, and gigs to turn momentum into bigger offers."

    def _get_progress_milestones(self):
        songs_written = len(self.player.songs_written)
        recorded_songs = sum(1 for song in self.player.songs_written if song.is_recorded)
        released_songs = sum(1 for song in self.player.songs_written if song.is_released)
        return [
            {
                "label": "First song written",
                "done": songs_written >= 1,
                "detail": "Unlock your core loop by writing at least one song.",
            },
            {
                "label": "First recording finished",
                "done": recorded_songs >= 1,
                "detail": "Take your best material into a studio and cut a clean recording.",
            },
            {
                "label": "First release out",
                "done": released_songs >= 1,
                "detail": "Use the phone music menu to get a single into the world.",
            },
            {
                "label": "Local media unlocked",
                "done": self.player.fame >= 20,
                "detail": "Reach 20 fame for local radio and stronger scene visibility.",
            },
            {
                "label": "City Center demo-ready",
                "done": self.player.fame >= 40,
                "detail": "Reach 40 fame to submit demos and push into bigger opportunities.",
            },
        ]

    def _build_travel_ui_data(self, travel_manager):
        mode_label = travel_manager.vehicle.name if travel_manager.vehicle else str(travel_manager.transport_mode).capitalize()
        route_origin = self.player.current_location.name if self.player and self.player.current_location else "Unknown"
        remaining_distance = max(0.0, travel_manager.distance_total - travel_manager.distance_covered)
        return {
            "eyebrow": "Travel In Progress",
            "title": f"En route to {travel_manager.destination.name}",
            "subtitle": "Long trips should feel physical. Watch the route, your condition, and what this leg is costing you.",
            "accent": (255, 140, 70),
            "progress_pct": travel_manager.get_progress_percent(),
            "progress_label": f"{travel_manager.distance_covered:.1f} / {travel_manager.distance_total:.1f} km covered",
            "condition_label": f"Energy {self.player.energy} | Stress {self.player.stress} | Hunger {self.player.hunger}",
            "route_rows": [
                ("From", route_origin),
                ("To", travel_manager.destination.name),
                ("Mode", mode_label),
                ("Class", str(travel_manager.ticket_class).capitalize()),
            ],
            "notes": [
                f"Time on the road: {int(travel_manager.travel_time_elapsed)}h",
                f"Distance remaining: {remaining_distance:.1f} km",
                "Passenger routes allow more idle actions than driving yourself.",
                "Vehicle trips can break down or run into fuel trouble.",
            ],
        }

    def _apply_weekly_survival_costs(self):
        base_cost = 50
        if self.player.has_home:
            base_cost += 35
        if self.player.current_location and self.player.current_location.name == "City Center":
            base_cost += 20
        if self.player.rented_accommodation_info:
            base_cost += 35
        self.delegation_system.ensure_player_support(self.player)
        active_role_upkeep = sum(role.upkeep for role in self.player.delegation_roles.values() if role.active)
        base_cost += active_role_upkeep

        if self.player.money >= base_cost:
            self.player.money -= base_cost
            self.player.unpaid_survival_weeks = 0
            self.GAME_LOG.add_log_message(f"Paid weekly living costs: ${base_cost}.")
            return

        shortfall = base_cost - self.player.money
        self.player.money = 0
        self.player.unpaid_survival_weeks += 1
        self.player.stress = min(100, self.player.stress + 12 + (self.player.unpaid_survival_weeks * 4))
        self.player.comfort = max(0, self.player.comfort - 12)
        self.player.health = max(0, self.player.health - 5)
        self.GAME_LOG.add_log_message(
            f"You come up ${shortfall} short on weekly living costs. Stress climbs and your situation gets rougher."
        )
        if self.player.unpaid_survival_weeks == 1 and self.player.has_home:
            self.GAME_LOG.add_log_message("Your landlord is warning you. Miss again and you could lose the apartment.")
        elif self.player.unpaid_survival_weeks >= 2 and self.player.has_home:
            self.player.has_home = False
            if self.player.current_poi and getattr(self.player.current_poi, "poi_id", None) == self.PLAYER_HOME_POI_ID_GLOBAL:
                self.player.current_poi = None
            self.GAME_LOG.add_log_message("You got evicted. Home is gone, and recovery just got harder.")

    def _resolve_outcome_roll(self, base_score, bands):
        roll = random.randint(1, 100)
        total = max(1, min(100, int(round(roll + base_score))))
        chosen_band = bands[-1]
        for band in bands:
            if total <= band["max"]:
                chosen_band = band
                break
        return {
            "roll": roll,
            "total": total,
            "band": chosen_band["key"],
            "data": chosen_band,
        }

    def _player_memory_opportunity_bias(self):
        if not self.player:
            return 0.0
        return self.world_memory.reliability_score(self.player.name, current_game_time.copy())

    def _venue_memory_bias(self, venue_id: Optional[str]) -> float:
        if not venue_id:
            return 0.0
        positive = self.world_memory.weighted_score(current_game_time.copy(), event_type="great_performance", location=venue_id)
        negative = self.world_memory.weighted_score(current_game_time.copy(), event_type="missed_gig", location=venue_id)
        return positive - negative

    def _calculate_song_visibility_score(self, song, channel_bonus=0):
        trend_bonus = 0
        if hasattr(self, "trend_manager") and self.trend_manager.get_top_genre() == song.genre:
            trend_bonus += 10
        support_bonus = 0
        if getattr(self.player, "signed_label_deal", None):
            support_bonus += int(self.player.signed_label_deal.get("marketing_support_bonus", 1.0) * 5)
        return (
            int(song.song_quality * 30)
            + int(song.recording_quality * 25)
            + min(20, int(song.buzz_score / 8))
            + min(18, int(self.player.fame / 4))
            + min(10, int(len(self.player.contacts) / 2))
            + trend_bonus
            + support_bonus
            + channel_bonus
        ) - max(0, int(self.player.stress / 12))

    def _resolve_marketing_outcome(self, campaign_type, song):
        campaign = CAMPAIGN_TYPES[campaign_type]
        channel_bonus_map = {
            "social_media": 0,
            "street_team": 4,
            "radio_push": 12,
            "pr_stunt": 6,
            "music_video": 18,
        }
        score = self._calculate_song_visibility_score(song, channel_bonus_map.get(campaign_type, 0)) - 45
        if campaign_type == "pr_stunt":
            score -= 8
        bands = [
            {"max": 8, "key": "backfire", "buzz": -12, "fame": -1, "message": f"{campaign['name']} backfires and people clown the push."},
            {"max": 30, "key": "quiet", "buzz": 4, "fame": 0, "message": f"{campaign['name']} lands softly. Most people scroll past it."},
            {"max": 75, "key": "solid", "buzz": 14, "fame": 2, "message": f"{campaign['name']} finds a real audience and starts moving the song."},
            {"max": 96, "key": "strong", "buzz": 32, "fame": 6, "message": f"{campaign['name']} catches real traction and spreads beyond your usual reach."},
            {"max": 100, "key": "breakout", "buzz": 65, "fame": 14, "message": f"{campaign['name']} takes off. The post gets picked up far beyond your circle."},
        ]
        outcome = self._resolve_outcome_roll(score, bands)
        # Rare co-sign if the campaign lands very high and the song is strong.
        if outcome["total"] >= 98 and song.recording_quality >= 0.7 and self.player.fame >= 15:
            outcome["data"]["buzz"] += 25
            outcome["data"]["fame"] += 8
            outcome["message_suffix"] = " A bigger artist reposts it, and that pushes the whole thing higher."
        else:
            outcome["message_suffix"] = ""
        return outcome

    def _resolve_demo_submission_outcome(self, song, label):
        score = (
            int(song.song_quality * 35)
            + int(song.recording_quality * 35)
            + min(20, int(self.player.fame / 2))
            + (8 if song.genre in getattr(label, "genres_preferred", []) else -6)
            + min(8, int(song.buzz_score / 12))
            - max(0, int(self.player.stress / 15))
        ) - 40
        bands = [
            {"max": 18, "key": "pass", "accepted": False, "advance_mult": 0.0, "marketing_mult": 0.0, "message": "They pass quickly. It sounds undercooked to them."},
            {"max": 50, "key": "soft_pass", "accepted": False, "advance_mult": 0.0, "marketing_mult": 0.0, "message": "They do not offer a deal, but they tell you to keep developing."},
            {"max": 82, "key": "interest", "accepted": True, "advance_mult": 0.8, "marketing_mult": 0.7, "message": "They hear potential and want to talk numbers."},
            {"max": 97, "key": "strong_interest", "accepted": True, "advance_mult": 1.1, "marketing_mult": 1.1, "message": "The demo gets real attention inside the office."},
            {"max": 100, "key": "bidding_heat", "accepted": True, "advance_mult": 1.4, "marketing_mult": 1.35, "message": "The demo hits unusually hard. They move fast before someone else does."},
        ]
        return self._resolve_outcome_roll(score, bands)

    def _resolve_shift_outcome(self, role_name, base_pay, hours):
        score = (
            min(15, int(self.player.energy / 8))
            + min(12, int((100 - self.player.stress) / 10))
            + min(10, int((100 - self.player.hunger) / 10))
            + min(8, int(self.player.health / 12))
            - (3 if "night" in role_name.lower() else 0)
            - (4 if hours >= 5 else 0)
        ) - 20
        bands = [
            {"max": 10, "key": "terrible", "pay_mult": 0.65, "injury": 6, "inspiration": 0, "message": "You drag through the shift and barely hold it together."},
            {"max": 32, "key": "rough", "pay_mult": 0.85, "injury": 3, "inspiration": 0, "message": "It is a rough shift. You get through it, but it costs you."},
            {"max": 82, "key": "steady", "pay_mult": 1.0, "injury": 0, "inspiration": 0, "message": "You put in the hours and get out clean."},
            {"max": 97, "key": "strong", "pay_mult": 1.15, "injury": 0, "inspiration": 3, "message": "You handle the shift well and even catch a small break."},
            {"max": 100, "key": "standout", "pay_mult": 1.3, "injury": 0, "inspiration": 6, "message": "Something clicks. The shift goes unusually well for you."},
        ]
        return self._resolve_outcome_roll(score, bands)

    def _resolve_media_outcome(self, media_type):
        released_songs = [song for song in self.player.songs_written if song.is_released]
        strongest_song = max(released_songs, key=lambda song: song.buzz_score + song.recording_quality, default=None)
        song_bonus = self._calculate_song_visibility_score(strongest_song, 0) if strongest_song else 0
        score = (
            min(18, int(self.player.fame / 3))
            + min(14, int(len(self.player.contacts) / 2))
            + min(18, int(song_bonus / 6))
            + (10 if self.player.has_pr_manager else 0)
            - max(0, int(self.player.stress / 10))
        ) - 40
        if media_type == "radio":
            bands = [
                {"max": 18, "key": "awkward", "fame": 4, "buzz": 3, "message": "The interview is rough and forgettable."},
                {"max": 55, "key": "solid", "fame": 10, "buzz": 8, "message": "The interview goes fine and people notice."},
                {"max": 90, "key": "strong", "fame": 18, "buzz": 16, "message": "You come off well and the station pushes the segment."},
                {"max": 100, "key": "breakout", "fame": 28, "buzz": 26, "message": "The interview lands hard and gives you a real local surge."},
            ]
        else:
            bands = [
                {"max": 20, "key": "small", "fame": 6, "buzz": 5, "message": "The feature runs, but it barely moves the needle."},
                {"max": 60, "key": "good", "fame": 12, "buzz": 12, "message": "The blog feature gives you useful scene traction."},
                {"max": 92, "key": "strong", "fame": 20, "buzz": 20, "message": "The piece spreads well and reaches outside your usual circle."},
                {"max": 100, "key": "surge", "fame": 32, "buzz": 30, "message": "The feature catches fire and pulls in a lot of new attention."},
            ]
        return self._resolve_outcome_roll(score, bands)

    def _maybe_trigger_npc_cosign(self, song, source_context):
        if not song:
            return
        visible_contacts = []
        for npc_id in self.player.contacts:
            npc = self.NPC_REGISTRY.get(npc_id)
            if not npc or not getattr(npc, "skills", None):
                continue
            if npc.relationship_with_player not in [RelationshipStatus.FRIENDLY, RelationshipStatus.ALLY]:
                continue
            npc_fame = self._calculate_npc_fame(npc)
            if npc_fame >= 60:
                visible_contacts.append((npc, npc_fame))

        if not visible_contacts:
            return

        strongest_npc, npc_fame = max(visible_contacts, key=lambda item: item[1])
        score = (
            int(song.song_quality * 30)
            + int(song.recording_quality * 25)
            + min(18, int(song.buzz_score / 5))
            + min(15, int(self.player.fame / 4))
            + min(15, int(npc_fame / 15))
        ) - 55
        outcome = self._resolve_outcome_roll(score, [
            {"max": 97, "key": "none"},
            {"max": 100, "key": "cosign"},
        ])
        if outcome["band"] == "cosign":
            buzz_gain = 22 + min(25, int(npc_fame / 10))
            fame_gain = 8 + min(18, int(npc_fame / 20))
            song.buzz_score += buzz_gain
            self.player.fame += fame_gain
            self.GAME_LOG.add_log_message(
                f"{strongest_npc.name} mentions '{song.title}' after {source_context}. (+{buzz_gain} buzz, +{fame_gain} fame)"
            )

    def _resolve_gig_rewards(self, performance_event, final_hype):
        setlist_quality = 0.0
        average_gear_boost = 0.0

        if self.performance_setlist:
            setlist_quality = sum(song.song_quality for song in self.performance_setlist) / len(self.performance_setlist)

            # Apply tone/gear bonus for the genres played in the setlist
            genre_boosts = [self._get_max_genre_gear_boost(song.genre) for song in self.performance_setlist]
            average_gear_boost = sum(genre_boosts) / len(genre_boosts)

        score = (
            int(final_hype / 2)
            + int(setlist_quality * 30)
            + int(average_gear_boost * 40)  # scale up the 0.0-0.3 boost to 0-12 score points
            + min(18, int(self.player.skills.get("stage_presence", 0)))
            + min(12, int(self.player.fame / 6))
            - max(0, int(self.player.stress / 10))
            - max(0, int((100 - self.player.energy) / 12))
            - int(self.player.vocal_strain / 10)
            - int(self.player.wrist_strain / 10)
        ) - 35
        score = int(score * getattr(self, "performance_requirement_penalty", 1.0))

        # Increase strain slightly per gig
        self.player.vocal_strain = min(100, self.player.vocal_strain + random.randint(3, 8))
        self.player.wrist_strain = min(100, self.player.wrist_strain + random.randint(2, 6))
        bands = [
            {"max": 18, "key": "messy", "pay_mult": 0.55, "fame_mult": 0.5, "message": "The set never really locks in."},
            {"max": 52, "key": "serviceable", "pay_mult": 0.85, "fame_mult": 0.8, "message": "You get through the set and a few people respond."},
            {"max": 88, "key": "strong", "pay_mult": 1.1, "fame_mult": 1.15, "message": "The room is with you and the set lands."},
            {"max": 100, "key": "standout", "pay_mult": 1.4, "fame_mult": 1.5, "message": "The performance cuts through and people will talk about it after."},
        ]
        outcome = self._resolve_outcome_roll(score, bands)
        base_payout = getattr(performance_event, "payout", 50)
        base_fame = getattr(performance_event, "fame_reward", 5)
        outcome["money_gain"] = max(10, int(base_payout * outcome["data"]["pay_mult"]))
        outcome["fame_gain"] = max(1, int(base_fame * outcome["data"]["fame_mult"]))

        venue_id = None
        if hasattr(performance_event, "location"):
            venue_id = getattr(performance_event.location, "venue_id", getattr(performance_event.location, "poi_id", None))
        if outcome.get("band") in {"strong", "standout"}:
            self.world_memory.add(
                WorldMemoryEntry(
                    event_type="great_performance",
                    involved_entities=[self.player.name],
                    location=venue_id,
                    timestamp=current_game_time.copy(),
                    tags=["momentum", "professionalism", "visibility"],
                    impact_score=4.0 if outcome.get("band") == "standout" else 2.5,
                    metadata={"hype": final_hype, "band": outcome.get("band")},
                    source_key=f"gig:{venue_id}:{current_game_time.get_time_string_for_schedule()}:{outcome.get('band')}",
                )
            )
        elif outcome.get("band") == "messy":
            self.world_memory.add(
                WorldMemoryEntry(
                    event_type="poor_performance",
                    involved_entities=[self.player.name],
                    location=venue_id,
                    timestamp=current_game_time.copy(),
                    tags=["professionalism"],
                    impact_score=2.5,
                    metadata={"hype": final_hype, "band": outcome.get("band")},
                    source_key=f"gig:{venue_id}:{current_game_time.get_time_string_for_schedule()}:messy",
                )
            )

        # Venue prestige impact
        if hasattr(performance_event, "location") and hasattr(performance_event.location, "update_prestige"):
            venue = performance_event.location
            prestige_shift = 0.0
            band_key = outcome.get("band") # From _resolve_outcome_roll which returns 'band' key
            if band_key == "standout" and final_hype > 85:
                prestige_shift = 0.2
            elif band_key == "strong" and final_hype > 70:
                prestige_shift = 0.1
            elif band_key == "messy":
                prestige_shift = -0.1

            if prestige_shift != 0:
                venue.update_prestige(prestige_shift)
                # Ensure the venue is marked as active
                venue.weeks_without_events = 0

        return outcome

    def _passes_contextual_threshold(self, score, threshold):
        return random.randint(1, 100) + score >= threshold

    def _apply_weekly_life_event(self):
        sickness_score = int((45 - self.player.health) / 2) + int(self.player.hunger / 12) + int(self.player.stress / 15)
        if self.player.health < 45 and self._passes_contextual_threshold(sickness_score, 92):
            health_loss = random.randint(6, 14)
            self.player.health = max(0, self.player.health - health_loss)
            self.player.energy = max(0, self.player.energy - 20)
            self.player.stress = min(100, self.player.stress + 10)
            self.GAME_LOG.add_log_message(f"SICKNESS: You spend the week fighting through it. (-{health_loss} health)")
            return

        burnout_score = int((self.player.stress - 70) / 2) + int((100 - self.player.energy) / 8)
        if self.player.stress > 88 and self._passes_contextual_threshold(burnout_score, 94):
            inspiration_loss = min(self.player.inspiration, random.randint(8, 20))
            self.player.inspiration -= inspiration_loss
            self.player.energy = max(0, self.player.energy - 12)
            self.GAME_LOG.add_log_message(f"BURNOUT: You can barely think straight. (-{inspiration_loss} inspiration)")
            return

        theft_score = int(self.player.money / 30) + (12 if not self.player.has_home else 0) + int(self.player.fame / 10)
        if (self.player.money > 0 or len(self.player.gear_inventory) > 0) and not self.player.has_bodyguard and self._passes_contextual_threshold(theft_score, 102):
            stealable_items = [item for item in self.player.gear_inventory if not item.is_broken]
            if len(stealable_items) > 0 and random.random() < 0.4:
                # Steal an item
                stolen_item = random.choice(stealable_items)
                if stolen_item:
                    self.player.remove_gear(stolen_item)
                    self.player.stress = min(100, self.player.stress + 20)
                    self.GAME_LOG.add_log_message(f"THEFT: Someone broke in and stole your {stolen_item.name}!")

                    # Try to put it in a local pawn shop
                    if self.player.current_location:
                        pawn_shops = [p for p in self.player.current_location.points_of_interest if getattr(p, "category", "") == "SHOP_PAWN"]
                        if pawn_shops:
                            shop = random.choice(pawn_shops)
                            shop.pawned_items.append(stolen_item)
                            self.GAME_LOG.add_log_message("You might be able to track it down at a local pawn shop.")
            else:
                # Steal cash
                cash_loss = min(self.player.money, random.randint(15, 60))
                if cash_loss > 0:
                    self.player.money -= cash_loss
                    self.player.stress = min(100, self.player.stress + 9)
                    self.GAME_LOG.add_log_message(f"THEFT: Someone catches you slipping and you lose ${cash_loss}.")
            return

        released_songs = [song for song in self.player.songs_written if song.is_released]
        if released_songs:
            breakout_song = max(
                released_songs,
                key=lambda song: song.buzz_score + song.recording_quality,
            )
            visibility_score = self._calculate_song_visibility_score(breakout_song, channel_bonus=0)
            if random.randint(1, 100) + visibility_score >= 99:
                buzz_gain = random.randint(25, 60)
                fame_gain = random.randint(18, 45)
                breakout_song.buzz_score += buzz_gain
                self.player.fame += fame_gain
                self.GAME_LOG.add_log_message(
                    f"A post around '{breakout_song.title}' escapes your normal orbit and catches online. (+{buzz_gain} buzz, +{fame_gain} fame)"
                )
                return

        hard_times_score = (
            int(self.player.stress / 8)
            + int(self.player.hunger / 10)
            + (10 if not self.player.has_home else 0)
            - min(8, int(self.player.health / 15))
        )
        if self._passes_contextual_threshold(hard_times_score, 92):
            cash_loss = min(self.player.money, random.randint(10, 45))
            health_loss = random.randint(4, 12)
            self.player.money -= cash_loss
            self.player.health = max(0, self.player.health - health_loss)
            self.player.stress = min(100, self.player.stress + random.randint(6, 14))
            self.GAME_LOG.add_log_message(
                f"HARD LUCK: A rough week costs you ${cash_loss} and leaves you worn down. (-{health_loss} health)"
            )
            return

        side_hustle_score = (
            min(12, int(self.player.energy / 10))
            + min(10, int((100 - self.player.stress) / 10))
            + min(8, int(len(self.player.contacts) / 2))
            + min(8, int(self.player.fame / 8))
        )
        if self._passes_contextual_threshold(side_hustle_score, 95):
            cash_gain = random.randint(20, 70)
            self.player.money += cash_gain
            self.player.stress = min(100, self.player.stress + 3)
            self.GAME_LOG.add_log_message(f"SIDE HUSTLE: You pick up extra cash this week. (+${cash_gain})")

    def _check_player_survival_state(self):
        if not self.player.alive:
            return

        if self.player.health <= 0:
            self.player.alive = False
            self.player.cause_of_death = "your body finally gave out"
        elif self.player.hunger >= 100 and self.player.energy <= 0 and self.player.stress >= 95:
            self.player.alive = False
            self.player.cause_of_death = "neglect and exhaustion"
        elif self.player.unpaid_survival_weeks >= 3 and self.player.health <= 15 and self._passes_contextual_threshold(10 + (self.player.unpaid_survival_weeks * 4), 96):
            self.player.alive = False
            self.player.cause_of_death = "a spiral you could not recover from"

        if not self.player.alive:
            self.GAME_LOG.add_log_message(f"GAME OVER: {self.player.name} died young from {self.player.cause_of_death}.")
            self.running = False

    def _get_career_overview_data(self):
        songs_written = len(self.player.songs_written)
        songs_recorded = sum(1 for song in self.player.songs_written if song.is_recorded)
        songs_released = sum(1 for song in self.player.songs_written if song.is_released)
        top_buzz = max((int(song.buzz_score) for song in self.player.songs_written), default=0)
        next_event = self.player.schedule.get_upcoming_events(current_game_time, limit=1)
        next_event_label = str(next_event[0]) if next_event else "Nothing scheduled"
        available_opportunities = sum(
            1 for details in self.player.active_opportunities.values()
            if details.get("status") == "available"
        )
        summary_rows = [
            ("Cash", f"${self.player.money}"),
            ("Fame", self.player.fame),
            ("Songs Written", songs_written),
            ("Recorded", songs_recorded),
            ("Released", songs_released),
            ("Top Buzz", top_buzz),
        ]
        opportunities = [
            {
                "label": "Next radio unlock",
                "value": "Ready" if self.player.fame >= 20 else f"{max(0, 20 - self.player.fame)} fame to go",
            },
            {
                "label": "Next blog unlock",
                "value": "Ready" if self.player.fame >= 35 else f"{max(0, 35 - self.player.fame)} fame to go",
            },
            {
                "label": "Next label demo unlock",
                "value": "Ready" if self.player.fame >= 40 else f"{max(0, 40 - self.player.fame)} fame to go",
            },
            {
                "label": "Open opportunities",
                "value": str(available_opportunities),
            },
            {
                "label": "Next scheduled event",
                "value": next_event_label,
            },
        ]
        focus_items = [
            f"Current base: {self.player.current_location.name if self.player.current_location else 'Unknown'}",
            f"Contacts in phone: {len(self.player.contacts)}",
            f"Pending label offers: {len(self.player.pending_contracts)}",
        ]
        return {
            "subtitle": f"{self.player.name}'s current momentum, bottlenecks, and next unlocks.",
            "summary_rows": summary_rows,
            "milestones": self._get_progress_milestones(),
            "opportunities": opportunities,
            "focus_items": focus_items,
            "focus_summary": self._get_progress_hint(),
        }

    def _get_main_menu_context(self):
        upcoming_events = self.player.schedule.get_upcoming_events(current_game_time, limit=2)
        details = [
            f"Location: {self.player.current_location.name if self.player.current_location else 'Unknown'}",
            f"Cash and fame: ${self.player.money}, {self.player.fame} fame",
            f"Health / Hunger / Stress: {self.player.health} / {self.player.hunger} / {self.player.stress}",
            f"Next event: {str(upcoming_events[0]) if upcoming_events else 'Nothing scheduled'}",
            f"Current focus: {self._get_progress_hint()}",
        ]
        return {
            "eyebrow": "Career Hub",
            "subtitle": "Choose the next move that pushes the run forward.",
            "panel_title": "Right Now",
            "details": details,
            "accent": (255, 215, 90),
            "footer": "Use arrow keys and Enter, or click.",
        }

    def _get_explore_context(self, location, poi=None):
        if poi:
            title = f"{poi.name} in {location.name}"
            type_str = getattr(poi, 'category', getattr(poi, 'venue_type', 'Unknown'))
            if hasattr(poi, 'prestige'):
                # Extract trend string from __str__ method of Venue
                str_rep = str(poi)
                trend = ""
                if "↑" in str_rep: trend = " ↑"
                elif "↓" in str_rep: trend = " ↓"
                type_str += f" (Prestige: {poi.prestige:.1f}{trend})"

            details = [
                f"Type: {type_str}",
                f"Interactions available: {len(getattr(poi, 'interaction_options', []))}",
                f"Energy / Stress: {self.player.energy} / {self.player.stress}",
                self._get_progress_hint(),
            ]
            subtitle = "Use places intentionally. Each stop should either create momentum or restore your stats."
        else:
            title = f"{location.name} scene map"
            details = [
                f"POIs and venues here: {len(location.points_of_interest) + len(location.venues)}",
                f"Known contacts: {len(self.player.contacts)}",
                f"Upcoming events: {len(self.player.schedule.get_upcoming_events(current_game_time, limit=5))}",
                self._get_progress_hint(),
            ]
            subtitle = "Pick a place that helps the next step in your current career arc."
        return {
            "eyebrow": "Explore",
            "subtitle": subtitle,
            "panel_title": "Scene Notes",
            "details": [title] + details,
            "accent": (90, 150, 255),
            "footer": "Use arrow keys and Enter, or click.",
        }

    def _get_arrival_poi(self, destination, transport_mode):
        if not destination:
            return None
        preferred_categories = []
        if transport_mode == "plane":
            preferred_categories.append("TRANSPORT_AIRPORT")
        elif transport_mode in ["bus", "train"]:
            preferred_categories.append("TRANSPORT_BUS")
        preferred_categories.extend(["TRANSPORT_BUS", "TRANSPORT_AIRPORT"])

        for category in preferred_categories:
            poi = next((poi for poi in destination.points_of_interest if getattr(poi, "category", "") == category), None)
            if poi:
                return poi
        return destination.points_of_interest[0] if destination.points_of_interest else None

    def setup_world(self):
        self.WORLD_MAP.clear(); self.NPC_REGISTRY.clear(); self._poi_venue_id_map.clear()

        locations_json_path = os.path.join(self.SCRIPT_DIR, "..", "game_data", "world", "locations.json")
        npcs_json_path = os.path.join(self.SCRIPT_DIR, "..", "game_data", "world", "npcs.json")

        try:
            with open(locations_json_path, 'r') as f: locations_data = json.load(f)
        except Exception as e: self.GAME_LOG.add_message(f"FATAL ERROR loading {locations_json_path}: {e}"); return False

        temp_location_id_map = {}
        for loc_data in locations_data:
            location = Location(loc_data["name"], loc_data["description"]); location.id = loc_data["id"]
            self.WORLD_MAP[location.name] = location; temp_location_id_map[location.id] = location

        for loc_id_from_json, location_obj in temp_location_id_map.items():
            poi_file_name = next((ld["poi_definition_file"] for ld in locations_data if ld["id"] == loc_id_from_json), None)
            if not poi_file_name: self.GAME_LOG.add_message(f"Warning: No POI file for {location_obj.name}."); continue

            city_def_json_path = os.path.join(self.SCRIPT_DIR, "..", "game_data", "world", "city_definitions", poi_file_name)
            try:
                with open(city_def_json_path, 'r') as f: city_def_data = json.load(f)
            except Exception as e: self.GAME_LOG.add_message(f"ERROR loading {city_def_json_path}: {e}"); continue

            for poi_data in city_def_data.get("points_of_interest", []):
                props = poi_data.get("properties", {}).copy()
                shop_inventory_ids = props.pop("shop_inventory_item_ids", None)
                shop_inventory_vehicle_ids = props.pop("shop_inventory_vehicle_ids", None)
                menu_items_data = props.pop("menu_items", None)
                owner_npc_id_temp = props.pop("owner_npc_id", None)
                poi = PointOfInterest(poi_id=poi_data["poi_id"], name=poi_data["name"], description=poi_data["description"],
                                    category=poi_data["category"], interaction_options=list(poi_data.get("interaction_options", [])),
                                    parent_location_id=location_obj.name, **props)
                if shop_inventory_ids is not None: poi.shop_inventory_item_ids = list(shop_inventory_ids)
                if shop_inventory_vehicle_ids is not None: poi.shop_inventory_vehicle_ids = list(shop_inventory_vehicle_ids)
                if menu_items_data is not None:
                    poi.menu_items = list(menu_items_data)
                    if poi.category == "FOOD_FASTFOOD" and not poi.interaction_options: poi.interaction_options = [item["display_text"] for item in poi.menu_items]
                if owner_npc_id_temp: poi.owner_npc_id = owner_npc_id_temp
                if poi.poi_id == "citycenter_indiehits_records":
                    poi.interaction_options = [f"Submit Demo (requires {poi.min_fame_to_submit} fame)", "Talk to A&R Rep (requires Manager)"]
                location_obj.add_poi(poi)

            for venue_data in city_def_data.get("venues", []):
                props = venue_data.get("properties", {}).copy()
                owner_npc_id_temp_venue = props.pop("owner_npc_id", None)
                booking_fee_prop = props.pop("booking_fee", 50)
                allows_player_booking_prop = props.pop("allows_player_booking", True)
                genre_bias_prop = props.pop("genre_bias", {})
                venue = Venue(venue_id=venue_data["venue_id"], name=venue_data["name"], description=venue_data["description"],
                            venue_type=venue_data["venue_type"], category=venue_data["category"],
                            capacity=venue_data["capacity"], prestige=venue_data["prestige"],
                            parent_location_id=location_obj.name, genre_bias=genre_bias_prop, **props)
                if owner_npc_id_temp_venue: venue.owner_npc_id = owner_npc_id_temp_venue
                venue.events_hosted_ids_from_json = list(venue_data.get("events_hosted_ids", []))
                venue.booking_fee = booking_fee_prop; venue.allows_player_booking = allows_player_booking_prop
                if not venue.interaction_options:
                    venue.interaction_options = ["View upcoming events", "Talk to the owner"]
                location_obj.add_venue(venue)

            for conn_data in city_def_data.get("intra_city_poi_connections", []):
                poi_ids_tuple = tuple(sorted(conn_data["pois"]))
                if len(poi_ids_tuple) == 2: location_obj.intra_city_poi_connections[frozenset(poi_ids_tuple)] = {k: v for k, v in conn_data.items() if k != "pois"}

            # Ensure all points are connected so the player can always travel between them
            location_obj.ensure_intra_city_connectivity()

        self._build_poi_venue_id_map()

        try:
            with open(npcs_json_path, 'r') as f: npcs_data = json.load(f)
        except Exception as e: self.GAME_LOG.add_message(f"ERROR loading {npcs_json_path}: {e}"); return False

        for npc_data in npcs_data:
            home_loc_obj = self.get_poi_or_venue_by_id(npc_data.get("home_location_poi_id")) or self.WORLD_MAP.get(npc_data.get("home_location_location_id"))
            current_loc_obj = self.get_poi_or_venue_by_id(npc_data.get("initial_current_location_poi_id")) or self.WORLD_MAP.get(npc_data.get("initial_current_location_location_id"))
            if not home_loc_obj and npc_data.get("schedule"): home_loc_obj = self.get_poi_or_venue_by_id(list(npc_data["schedule"].values())[0])
            if not current_loc_obj: current_loc_obj = home_loc_obj
            if not home_loc_obj: self.GAME_LOG.add_message(f"Warning: No home location for NPC {npc_data['name']}.")
            if not current_loc_obj: self.GAME_LOG.add_message(f"Warning: No current location for NPC {npc_data['name']}.")
            npc = NPC(npc_id=npc_data["npc_id"], name=npc_data["name"], personality_key=npc_data["personality_key"], home_location=home_loc_obj, current_location=current_loc_obj)
            for time_slot, loc_id_str in npc_data.get("schedule", {}).items():
                scheduled_loc_obj = self.get_poi_or_venue_by_id(loc_id_str)
                if scheduled_loc_obj: npc.schedule[time_slot] = scheduled_loc_obj
                else: self.GAME_LOG.add_message(f"Warning: Scheduled POI/Venue ID '{loc_id_str}' not found for {npc.name}'s schedule.")
            if "skills" in npc_data:
                npc.skills = npc_data["skills"]
            if "gift_preferences" in npc_data:
                npc.gift_preferences = npc_data["gift_preferences"]
            if "career_stage" in npc_data:
                npc.career_stage = npc_data["career_stage"]
            self.NPC_REGISTRY[npc.npc_id] = npc

        for loc in self.WORLD_MAP.values():
            for item_list in [loc.points_of_interest, loc.venues]:
                for item in item_list:
                    if hasattr(item, 'owner_npc_id') and isinstance(item.owner_npc_id, str):
                        owner_npc = self.NPC_REGISTRY.get(item.owner_npc_id)
                        if owner_npc: item.owner_npc_id = owner_npc
                        else: self.GAME_LOG.add_message(f"Warning: Owner NPC ID '{item.owner_npc_id}' not found for POI/Venue '{item.name}'."); item.owner_npc_id = None

        for loc_data in locations_data:
            curr_loc_obj = temp_location_id_map.get(loc_data["id"])
            if not curr_loc_obj: continue
            for conn_data in loc_data.get("travel_connections", []):
                target_loc_obj = temp_location_id_map.get(conn_data["to_location_id"])
                if target_loc_obj:
                    curr_loc_obj.add_travel_connection(
                        target_loc_obj.name,
                        cost=conn_data["cost"],
                        time_hours=conn_data["time_hours"],
                        method=conn_data.get("method"),
                    )
                else: self.GAME_LOG.add_message(f"Warning: Target location ID '{conn_data['to_location_id']}' for travel from '{curr_loc_obj.name}' not found.")

        event_defs = [
            {"id": "open_mic_hometown_hall", "venue_id": "hometown_community_hall", "name": "Open Mic Night", "type": "OPEN_MIC", "skills": {"vocals": 1, "guitar": 1}, "gear": ["INSTRUMENT_ACOUSTIC"], "desc": "A chance to show your skills..."},
            {"id": "debut_rusty_mug", "venue_id": "citycenter_rustymug", "name": "Debut at 'The Rusty Mug'", "type": "CLUB_GIG", "skills": {"vocals": 5, "guitar": 5, "stage_presence": 3}, "gear": ["INSTRUMENT_ELECTRIC", "AMPLIFIER"], "desc": "Your first real club gig!", "prep_tasks": {"Write Setlist (3 songs)": False, "Rehearse Set (2 hours)": False, "Promote Gig Locally": False}},
            {"id": "opening_act_grande", "venue_id": "citycenter_grandetheater", "name": "Opening Act for Major Band", "type": "CONCERT", "skills": {"vocals": 15, "guitar": 15, "stage_presence": 10, "songwriting": 10}, "gear": ["INSTRUMENT_ELECTRIC", "AMPLIFIER", "INSTRUMENT_BASS", "INSTRUMENT_DRUMS"], "desc": "A huge opportunity...", "prep_tasks": {"Finalize Setlist (5 songs)": False, "Intensive Rehearsal (10 hours)": False, "Coordinate with Main Act": False, "Sound Check (2 hours)": False}},
            {"id": "headliner_show_grande", "venue_id": "citycenter_grandetheater", "name": "Headliner Show", "type": "CONCERT", "skills": {"vocals": 25, "guitar": 25, "stage_presence": 20, "songwriting": 20}, "gear": ["INSTRUMENT_ELECTRIC", "AMPLIFIER", "INSTRUMENT_BASS", "INSTRUMENT_DRUMS"], "desc": "Your own headliner show at the Grande Concert Hall!", "required_fame": 500}
        ]
        for ed in event_defs:
            vo = self.get_poi_or_venue_by_id(ed["venue_id"])
            if vo and isinstance(vo, Venue) and ed["id"] in getattr(vo, 'events_hosted_ids_from_json', [ed["id"]]):
                is_tour_gig_flag = "tour" in ed.get("name", "").lower()
                evt = Event(name=ed["name"], event_type=ed["type"], location=vo, required_skills=ed["skills"], required_gear_types=ed["gear"], description=ed["desc"], is_tour_gig=is_tour_gig_flag, required_fame=ed.get("required_fame", 0))
                if "prep_tasks" in ed: evt.preparation_tasks_required = ed["prep_tasks"]
                vo.add_event(evt)
            else: self.GAME_LOG.add_message(f"Warning: Venue ID '{ed['venue_id']}' for event '{ed['name']}' not found or not a Venue.")

        player_home_obj = self.get_poi_or_venue_by_id("hometown_player_home")
        if player_home_obj: self.PLAYER_HOME_POI_ID_GLOBAL = player_home_obj.poi_id
        else: self.GAME_LOG.add_message("CRITICAL ERROR: Player home POI 'hometown_player_home' not found.")

        self.ACTIVE_CHARTS.clear()
        hometown_chart = Chart(name="Hometown Local Hits", max_size=10, chart_genre_preference="Indie")
        city_chart = Chart(name="City Center Top Tracks", max_size=20)
        self.ACTIVE_CHARTS.append(hometown_chart); self.ACTIVE_CHARTS.append(city_chart)
        if self.GAME_LOG:
            self.GAME_LOG.add_log_message(f"Initialized {len(self.ACTIVE_CHARTS)} charts.")
            self.GAME_LOG.add_log_message(f"World setup complete. Loaded {len(self.WORLD_MAP)} locations and {len(self.NPC_REGISTRY)} NPCs.")

        tours_json_path = os.path.join(self.SCRIPT_DIR, "..", "game_data", "tours.json")
        try:
            with open(tours_json_path, 'r') as f:
                self.TOURS = json.load(f)
            if self.GAME_LOG:
                self.GAME_LOG.add_log_message(f"Loaded {len(self.TOURS)} tour packages.")
        except Exception as e:
            self.GAME_LOG.add_message(f"ERROR loading {tours_json_path}: {e}")

        return True

    def initialize_player(self):
        # Initial creation of player object, but details will be filled in character creation
        self.player = Player("Player")
        self.delegation_system.ensure_player_support(self.player)
        hometown_loc = self.WORLD_MAP.get("Your Hometown")
        player_home_obj = self.get_poi_or_venue_by_id(self.PLAYER_HOME_POI_ID_GLOBAL) if self.PLAYER_HOME_POI_ID_GLOBAL else None
        if hometown_loc and player_home_obj:
            self.player.current_location = hometown_loc
            self.player.current_poi = player_home_obj
        else:
            print("Error setting start home.")
            self.running = False

        # Set initial state to character creation
        self.game_state = "character_creation"

        self.update_npc_locations(current_game_time)
        self.process_time_based_player_needs(self.player, 0)
        self._normalize_opportunity_state()
        self.player.grit = random.randint(0, 15)

        # Gear will be added after character creation based on background
        # if GEAR_CATALOG.get("worn_acoustic_guitar"): self.player.add_gear(GEAR_CATALOG["worn_acoustic_guitar"])
        # if GEAR_CATALOG.get("guitar_picks_assorted"): self.player.add_gear(GEAR_CATALOG["guitar_picks_assorted"])

        self.LAST_CHART_UPDATE_DAY = current_game_time.day

    def check_for_new_opportunities(self):
        reliability_bias = self._player_memory_opportunity_bias()
        visibility_profile = self.visibility_system.get_visibility(self.player.name, self.player.current_location.name if self.player.current_location else None)
        visibility_bias = visibility_profile.get("public_visibility", 0.0)
        manager_bonus, manager_failure_hook = self.delegation_system.manager_opportunity_bias(self.player, visibility_bias, reliability_bias)
        manager_role = self.delegation_system.get_role(self.player, "manager")
        manager_quality = self.delegation_system.role_quality(manager_role) if manager_role else 0.0
        if manager_failure_hook:
            self.world_memory.add(
                WorldMemoryEntry(
                    event_type=manager_failure_hook,
                    involved_entities=[self.player.name],
                    location=self.player.current_location.name if self.player.current_location else None,
                    timestamp=current_game_time.copy(),
                    tags=["delegation", "manager"],
                    impact_score=2.0,
                    source_key=f"manager:{self.player.name}:{current_game_time.get_time_string_for_schedule()}:{manager_failure_hook}",
                )
            )
        elif manager_role and manager_quality >= 0.78 and manager_bonus >= 15:
            self.world_memory.add(
                WorldMemoryEntry(
                    event_type="manager_secured_strong_opportunity",
                    involved_entities=[self.player.name],
                    location=self.player.current_location.name if self.player.current_location else None,
                    timestamp=current_game_time.copy(),
                    tags=["delegation", "manager", "opportunity"],
                    impact_score=1.6,
                    source_key=f"manager_strong:{self.player.name}:{current_game_time.get_time_string_for_schedule()}",
                )
            )

        # Check for static opportunities from the catalog
        for opp_id, opp_data in self.OPPORTUNITY_CATALOG.items():
            if opp_id not in self.player.active_opportunities:
                if opp_data['trigger'](self.player, self):
                    opp_details = {"status": "available"}
                    if "poi_id_getter" in opp_data:
                        poi_id = opp_data["poi_id_getter"](self)
                        if poi_id:
                            opp_details["poi_id"] = poi_id
                        else:
                            continue # Can't trigger if there's no valid POI for it

                    self.player.active_opportunities[opp_id] = opp_details
                    self.GAME_LOG.add_log_message(f"A new opportunity has arisen: {opp_data['name']}!")
                    self.GAME_LOG.add_log_message("Check your phone for more details.")

        # Check for dynamic, NPC-driven opportunities
        for npc_id in self.player.contacts:
            npc = self.NPC_REGISTRY.get(npc_id)
            if npc and npc.skills and npc.relationship_with_player in [RelationshipStatus.FRIENDLY, RelationshipStatus.ALLY]:
                visible_song = max((song for song in self.player.songs_written if song.is_released), key=lambda song: song.buzz_score + song.recording_quality, default=None)
                feature_score = min(12, int(self._calculate_npc_fame(npc) / 15))
                if visible_song:
                    feature_score += min(16, int(self._calculate_song_visibility_score(visible_song, 0) / 10))
                feature_score += int(max(-8, min(8, reliability_bias / 4)))
                feature_score += int(max(-6, min(10, visibility_bias / 5)))
                if self._passes_contextual_threshold(feature_score, 103):
                    opp_id = f"guest_feature_{npc.npc_id}"
                    if opp_id not in self.player.active_opportunities:
                        self.player.active_opportunities[opp_id] = {"status": "available"}
                        self.GAME_LOG.add_log_message(f"{npc.name} was impressed with your work and wants you to feature on their new track!")
                        self.GAME_LOG.add_log_message("Check your phone for more details.")

        # Check for manager-driven tour opportunities
        if self.player.has_manager and not self.player.current_tour_id:
            # Simple logic: offer a tour if fame is high enough and not already on tour.
            for tour in self.TOURS:
                if tour['min_fame'] <= self.player.fame <= tour['max_fame']:
                    if tour['tour_id'] not in self.player.completed_tour_ids:
                        opp_id = f"tour_offer_{tour['tour_id']}"
                        if opp_id not in self.player.active_opportunities:
                            manager_roll = random.randint(1, 100) + int(max(-12, min(14, reliability_bias))) + int(max(-8, min(12, visibility_bias / 4))) + manager_bonus
                            if manager_roll >= 55:
                                self.player.active_opportunities[opp_id] = {"status": "available"}
                                self.GAME_LOG.add_log_message(f"Your manager found a potential tour for you: '{tour['name']}'!")
                                self.GAME_LOG.add_log_message("Check your phone for the offer.")
                                break # Only offer one tour at a time

    def _find_scheduled_event(self, event_id, venue_id=None):
        venue = self.get_poi_or_venue_by_id(venue_id) if venue_id else None
        venues_to_search = [venue] if isinstance(venue, Venue) else []
        if not venues_to_search:
            for location in self.WORLD_MAP.values():
                venues_to_search.extend(location.venues)

        for candidate_venue in venues_to_search:
            for candidate_event in candidate_venue.events_hosted:
                if candidate_event.event_id == event_id:
                    return candidate_event
        return None

    def check_for_scheduled_events(self):
        # We need to iterate over a copy, as we might remove items
        for event in self.player.schedule.scheduled_items[:]:
            if event.start_time <= current_game_time:
                if event.category == "LABEL_RESPONSE":
                    self.handle_label_response(event)
                    self.player.schedule.scheduled_items.remove(event)
                elif event.category in ["Gig", "Gig (Tour)"]:
                    scheduled_event = self._find_scheduled_event(
                        event.details.get("event_id"),
                        event.details.get("venue_id"),
                    )

                    if not scheduled_event:
                        self.GAME_LOG.add_log_message(f"You missed '{event.description}' because the booking data could not be found.")
                    elif self.game_state == "performance":
                        self.GAME_LOG.add_log_message(f"'{event.description}' is happening now, but you're already busy.")
                    else:
                        expected_dest = event.details.get("destination_id") or event.details.get("venue_id")
                        current_dest = None
                        if self.player.current_poi:
                            current_dest = getattr(self.player.current_poi, "poi_id", getattr(self.player.current_poi, "venue_id", None))

                        if expected_dest and expected_dest != current_dest:
                            miss_reason = event.details.get("obligation_explanation") or "you were not at the venue when doors opened"
                            root_cause = event.details.get("obligation_reason_code")
                            if root_cause:
                                self.GAME_LOG.add_log_message(f"You missed '{event.description}' [{root_cause}]: {miss_reason}.")
                            else:
                                self.GAME_LOG.add_log_message(f"You missed '{event.description}': {miss_reason}.")
                        else:
                            gig_req = self._assess_gig_requirements()
                            self.performance_requirement_penalty = 1.0
                            if gig_req.status == "missing_and_severe":
                                self.GAME_LOG.add_log_message(
                                    f"You missed '{event.description}' due to missing critical loadout: {', '.join(gig_req.missing_severe)}."
                                )
                            else:
                                if gig_req.status in {"partially_satisfied", "missing_but_recoverable"}:
                                    self.performance_requirement_penalty = 0.82
                                    self.player.stress = min(100, self.player.stress + 7)
                                    self.GAME_LOG.add_log_message(
                                        f"You improvise with an incomplete kit ({', '.join(gig_req.missing)}). Performance quality will suffer."
                                    )
                                self.active_performance = scheduled_event
                                self.performance_stage = "choose_song"
                                self.game_state = "performance"
                                self.GAME_LOG.add_log_message(f"It's time for '{scheduled_event.name}' at {scheduled_event.location.name}.")

                    self.player.schedule.scheduled_items.remove(event)

    def handle_label_response(self, event):
        label_id = event.details.get('label_id')
        song_id = event.details.get('song_id')
        label = self.get_poi_or_venue_by_id(label_id)
        song = next((s for s in self.player.songs_written if s.song_id == song_id), None)

        if not label or not song:
            return

        self.GAME_LOG.add_log_message(f"You've received a response from {label.name} about '{song.title}'.")
        submission_outcome = event.details.get("submission_outcome", "soft_pass")

        if submission_outcome in ["interest", "strong_interest", "bidding_heat"]:
            score = (
                (song.song_quality * 50)
                + (song.recording_quality * 35)
                + self.player.fame
                + song.buzz_score
            )
            advance = int(score * 10 * event.details.get("advance_mult", 1.0))
            royalty = min(0.25, 0.05 + (score / 1000.0))
            marketing = int(score * 5 * event.details.get("marketing_mult", 1.0))
            contract = Contract(
                label_name=label.name,
                label_poi_id=label_id,
                advance_money=advance,
                royalty_rate=royalty,
                marketing_budget_per_release=marketing
            )
            self.player.pending_contracts.append(contract)
            self.GAME_LOG.add_log_message("They're interested. A contract offer is waiting in your phone.")
        else:
            self.GAME_LOG.add_log_message("They pass for now.")

    def schedule_tour(self, tour_id):
        tour_data = next((t for t in self.TOURS if t['tour_id'] == tour_id), None)
        if not tour_data:
            self.GAME_LOG.add_log_message(f"Error: Could not find data for tour ID {tour_id}")
            return

        self.player.current_tour_id = tour_id
        self.player.tour_ledgers[tour_id] = {
            "name": tour_data['name'],
            "expenses": 0,
            "income": 0,
            "status": "ongoing",
            "completed_gigs": []
        }
        self.GAME_LOG.add_log_message(f"Your manager starts booking the '{tour_data['name']}' tour.")

        last_gig_date = current_game_time.copy()

        for i, gig_template in enumerate(tour_data['gig_templates']):
            # Determine gig date
            offset = random.randint(gig_template['days_offset_min'], gig_template['days_offset_max'])
            gig_date = last_gig_date.copy()
            gig_date.add_days(offset)

            # Find a venue
            city_name = random.choice(gig_template['city_options'])
            city_venues = [v for v in self.WORLD_MAP[city_name].venues if v.venue_type in gig_template['venue_type_options']]
            if not city_venues:
                self.GAME_LOG.add_log_message(f"Manager couldn't find a suitable venue in {city_name} for leg {i+1}. Tour booking failed.")
                self.player.current_tour_id = None
                return

            city_venues = sorted(
                city_venues,
                key=lambda v: v.prestige + self._venue_memory_bias(getattr(v, "venue_id", None)),
                reverse=True,
            )
            venue = city_venues[0]

            # Create a temporary event for this gig
            gig_event = Event(
                name=f"{tour_data['name']} @ {venue.name}",
                event_type=gig_template['event_type'],
                location=venue,
                is_tour_gig=True
            )
            # Add to the venue's events for the duration of the gig
            # This is a simplification; a real implementation might need a more robust temporary event system
            venue.events_hosted.append(gig_event)

            # Schedule it for the player
            gig_start_time = gig_date
            gig_start_time.hour = 19 # Gigs are in the evening
            gig_end_time = gig_start_time.copy()
            gig_end_time.add_hours(3)

            self.player.schedule.add_event(
                gig_start_time,
                gig_end_time,
                gig_event.name,
                "Gig (Tour)",
                {"event_id": gig_event.event_id, "venue_id": venue.venue_id, "destination_id": venue.venue_id, "requires_presence": True},
            )
            self.GAME_LOG.add_log_message(f"Booked: {gig_event.name} on {gig_start_time.get_time_string_for_schedule()}")

            last_gig_date = gig_date


    def run(self):
        if not self.setup_world():
            print("World setup failed. Check log.")
            return

        self.GAME_LOG.add_log_message("Welcome to Music-Life Sim!")
        self.GAME_LOG.add_log_message("Offline NPC dialogue is available by default. External AI dialogue is optional.")

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            if self.player and (current_game_time.day % 7 == 1) and (current_game_time.day != self.LAST_CHART_UPDATE_DAY):
                self.GAME_LOG.add_log_message("--- Weekly World Update ---")

                # Venue Prestige Decay
                from game.rivals import NEWS_FEED
                for loc in self.WORLD_MAP.values():
                    for venue in loc.venues:
                        venue.weeks_without_events += 1
                        if venue.weeks_without_events > 4:
                            # Venue is stagnant, lose prestige slowly
                            venue.update_prestige(-0.1)

                        if venue.prestige < 1.0:
                            # Management changes hands
                            venue.prestige = venue.base_prestige
                            venue.weeks_without_events = 0
                            venue.events_hosted.clear()
                            venue.prestige_history.clear()
                            NEWS_FEED.insert(0, f"SCENE: {venue.name} in {loc.name} closed its doors after a rough patch, but new management is attempting a reopening.")
                            self.GAME_LOG.add_log_message(f"NEWS: {venue.name} is under new management.")

                # Band Wages
                wage_report = resolve_weekly_wages(self.player, self.player.band)
                if wage_report:
                     self.GAME_LOG.add_log_message("--- Band Wages ---")
                     for line in wage_report.split('\n'):
                         self.GAME_LOG.add_log_message(line)

                # Staff Wages
                total_staff_wages = sum(s.wage_per_week for s in self.player.staff)
                if total_staff_wages > 0:
                    if self.player.money >= total_staff_wages:
                        self.player.money -= total_staff_wages
                        self.GAME_LOG.add_log_message(f"Paid staff wages: ${total_staff_wages}")
                    else:
                        # Unpaid staff leave?
                        self.GAME_LOG.add_log_message(f"Could not pay staff (${total_staff_wages}). They have quit!")
                        self.player.staff = []

                self._apply_weekly_survival_costs()
                self._apply_weekly_life_event()

                # NPCs progress in their careers
                self.update_npc_careers()

                # Rival Simulation
                simulate_rivals(self.NPC_REGISTRY)

                # Celebrity Events
                cel_evt = check_for_celebrity_event(self.player)
                if cel_evt:
                    self.GAME_LOG.add_log_message(f"INVITE: {cel_evt['desc']}")
                    # Auto-accept for now or add to opportunities?
                    # Let's add fame immediately as 'attendance' abstractly
                    self.player.fame += cel_evt['fame_gain']
                    self.GAME_LOG.add_log_message(f"You attended and gained {cel_evt['fame_gain']} Fame!")

                # Update Trends
                shift_happened = self.trend_manager.update_weekly()
                if shift_happened:
                    top_genre = self.trend_manager.get_top_genre()
                    self.GAME_LOG.add_log_message(f"--- NEWS: A cultural shift! {top_genre} is the new wave! ---")
                else:
                    top_genre = self.trend_manager.get_top_genre()
                    self.GAME_LOG.add_log_message(f"Trends: {top_genre} is currently popular.")

            # Daily Upkeep (e.g. Bodyguard)
            # This check runs every frame, so we need a "last_upkeep_day" tracker.
            # Using last_opportunity_check_day is decent but strictly for opportunities.
            # Let's re-use it or add a specific daily update block.
            if self.player and current_game_time.day != self.last_opportunity_check_day:
                # Daily Logic
                if self.player.has_bodyguard:
                    if self.player.money >= self.player.bodyguard_cost:
                        self.player.money -= self.player.bodyguard_cost
                        self.GAME_LOG.add_log_message(f"Paid bodyguard upkeep (${self.player.bodyguard_cost}).")
                    else:
                        self.player.has_bodyguard = False
                        self.GAME_LOG.add_log_message("Couldn't pay bodyguard. They quit!")

                # Check for NPC Favors (Allies)
                for npc_id in self.player.contacts:
                    npc = self.NPC_REGISTRY.get(npc_id)
                    if npc and npc.relationship_with_player == RelationshipStatus.ALLY:
                        ally_score = 8 + min(12, int(self._calculate_npc_fame(npc) / 20))
                        if self._passes_contextual_threshold(ally_score, 102):
                            # Send a gift
                            possible_gifts = ["food_energy_bar", "guitar_strings_basic", "guitar_picks_assorted"]
                            gift_id = random.choice(possible_gifts)
                            gift_item = GEAR_CATALOG.get(gift_id)
                            if gift_item:
                                self.player.add_gear(gift_item)
                                self.GAME_LOG.add_log_message(f"MSG from {npc.name}: 'Hey, saw this and thought of you!' (Received {gift_item.name})")

                # Check for Band Drama (Daily)
                drama_result = check_for_band_drama(self.player, self.player.band)
                if drama_result['event_triggered']:
                    self.GAME_LOG.add_log_message(f"BAND DRAMA: {drama_result['message']}")

                # Gather all released songs in the world
                all_released_songs = list(self.player.songs_written)
                for npc in self.NPC_REGISTRY.values():
                    all_released_songs.extend(npc.songs_written)

                # Update charts with all songs
                total_fame_gain = 0
                total_money_gain = 0
                all_feedback_events = []
                for chart in self.ACTIVE_CHARTS:
                    # Pass trend_manager to chart update
                    feedback_events = chart.update_weekly(all_released_songs, self.player, current_game_time, self.trend_manager)
                    all_feedback_events.extend(feedback_events)
                    # Calculate fame and money from chart positions for the PLAYER only
                    for entry in chart.entries:
                        if entry['artist_name'] == self.player.name:
                            fame_gain = max(0, (chart.max_size - entry['current_position'] + 1))
                            money_gain = fame_gain * 10 # $10 per "fame point" from charting
                            total_fame_gain += fame_gain
                            total_money_gain += money_gain

                if total_money_gain > 0 or total_fame_gain > 0:
                    self.player.money += total_money_gain
                    self.player.fame += total_fame_gain
                    self.GAME_LOG.add_log_message(f"Your songs earned you ${total_money_gain} and {total_fame_gain} fame this week.")

                # Process chart feedback events for log messages
                for event in all_feedback_events:
                    details = event['chart_details']
                    artist = details['artist_name']
                    song = details['song_title']
                    chart_name = details['chart_name']
                    position = details['current_position']

                    if artist == self.player.name:
                        if event['type'] == 'chart_debut':
                            self.GAME_LOG.add_log_message(f"Your song '{song}' has debuted on the {chart_name} chart at #{position}!")
                        elif event['type'] == 'hit_number_one':
                            self.GAME_LOG.add_log_message(f"You've done it! '{song}' is the #1 song on the {chart_name} chart!")
                    else:
                        # Less intrusive gossip for NPCs
                        if event['type'] == 'chart_debut' and position <= 10: # Only report significant debuts
                             self.GAME_LOG.add_log_message(f"GOSSIP: {artist}'s new song '{song}' entered the {chart_name} chart at #{position}.")
                        elif event['type'] == 'hit_number_one':
                             self.GAME_LOG.add_log_message(f"GOSSIP: Wow, {artist} hit #1 on the {chart_name} chart with '{song}'!")

                self.LAST_CHART_UPDATE_DAY = current_game_time.day
                self._check_player_survival_state()


            if self.player and current_game_time.day != self.last_opportunity_check_day:
                self.check_for_new_opportunities()
                self.last_opportunity_check_day = current_game_time.day

            self.ui.clear_screen()

            if self.player:
                self.check_for_scheduled_events()
                self._check_player_survival_state()

                date_str = get_current_time_str(date_only=True)
                if self.player.current_poi:
                    location_str = f"{self.player.current_poi.name}"
                elif self.player.current_location:
                    location_str = self.player.current_location.name
                else:
                    location_str = "On the road"

                upcoming_events = self.player.schedule.get_upcoming_events(current_game_time, limit=1)
                if upcoming_events:
                    next_event_str = str(upcoming_events[0])
                else:
                    next_event_str = "Nothing scheduled"

                self.ui.draw_hud(self.player, date_str, location_str, next_event_str, self._get_progress_hint())
                self.ui.draw_log()

            if self.game_state == "title_screen":
                self.handle_title_screen()
            elif self.game_state == "character_creation":
                self.handle_character_creation()
            elif self.game_state == "main_menu":
                self.handle_main_menu()
            elif self.game_state == "explore":
                self.handle_explore_menu()
            elif self.game_state == "travel":
                self.handle_travel_menu()
            elif self.game_state == "phone":
                self.handle_phone_menu()
            elif self.game_state == "music_menu":
                self.handle_music_menu()
            elif self.game_state == "character":
                self.handle_character_menu()
            elif self.game_state == "system":
                self.handle_system_menu()
            elif self.game_state == "view_text":
                self.handle_text_viewer()
            elif self.game_state == "performance":
                self.handle_performance_scene()
            elif self.game_state == "travel_active":
                self.handle_travel_active_state()

            self.ui.update_display()

        pygame.quit()

    def handle_title_screen(self):
        has_save = os.path.exists("savegame.dat")
        title_options = {
            "new_game": "New Game",
            "load_game": "Load Game" if has_save else "Load Game (No save found)",
            "quit": "Quit",
        }
        choice = self.ui.present_choices(
            title_options,
            "Music-Life",
            context={
                "eyebrow": "Life Sim Sandbox",
                "subtitle": "Start a new life, load an existing one, and build your path from wherever the systems take you.",
                "panel_title": "Start",
                "details": [
                    "New Game starts character creation.",
                    "Load Game resumes your last save." if has_save else "No save file is currently available on disk.",
                    "You are nobody special by default. What happens next depends on your choices and the world.",
                ],
                "accent": (90, 150, 255),
                "footer": "Use arrow keys and Enter, or click.",
            },
        )
        if choice == "quit":
            self.running = False
        elif choice == "load_game":
            if not has_save:
                self.GAME_LOG.add_log_message("No save file found. Start a new game to create a character.")
                self.game_state = "title_screen"
            else:
                self.load_game()
                if self.player is None:
                    self.game_state = "title_screen"
        else:
            self.initialize_player()

    def handle_character_creation(self):
        self.ui.clear_screen()
        self.ui.draw_text("New Character", self.ui.FONT_TITLE, (255, 255, 255), 640, 50, centered=True)
        self.ui.update_display()

        # 1. Get Name
        name = self.ui.get_text_input(
            "Enter your name:",
            context={
                "subtitle": "This is the name the world will know you by for now. You can treat it as a real name, stage name, or alias.",
                "panel_title": "Identity",
                "details": [
                    "Grounded starts matter here. You are building a life before you build a legend.",
                    "Shorter names read better in logs, charts, schedules, and dialogue.",
                    "Leave it blank if you want the game to assign a fallback identity.",
                ],
                "placeholder": "Type a name or alias",
                "max_length": 28,
            },
        )
        if not name:
            name = "The Unknown Artist"
        self.player.name = name

        # 2. Choose Background
        backgrounds = {
            "rocker": "The Rocker (Guitar++, Vocals+)",
            "pop_star": "The Pop Star (Vocals++, Stage Presence+)",
            "indie": "The Indie Artist (Songwriting++, Guitar+)",
            "electronic": "The Producer (Electronic++, Songwriting+)",
            "busker": "The Busker (Performance+, Stamina+)"
        }

        bg_choice = self.ui.present_choices(backgrounds, "Choose your starting background:")

        # Apply Background Stats/Gear
        if bg_choice == "rocker":
            self.player.skills['guitar'] = 15
            self.player.skills['vocals'] = 10
            self.player.add_gear(GEAR_CATALOG.get("worn_acoustic_guitar"))
            self.player.add_gear(GEAR_CATALOG.get("guitar_picks_assorted"))
            self.player.traits.append(TRAIT_CATALOG["resilient"])
        elif bg_choice == "pop_star":
            self.player.skills['vocals'] = 15
            self.player.skills['stage_presence'] = 10
            self.player.add_gear(GEAR_CATALOG.get("microphone_basic"))
            self.player.money += 200 # Extra starting cash for clothes/style
            self.player.traits.append(TRAIT_CATALOG["charismatic"])
        elif bg_choice == "indie":
            self.player.skills['songwriting'] = 15
            self.player.skills['guitar'] = 10
            self.player.add_gear(GEAR_CATALOG.get("worn_acoustic_guitar"))
            self.player.add_gear(GEAR_CATALOG.get("notebook_lyrics"))
            self.player.traits.append(TRAIT_CATALOG["virtuoso"])
        elif bg_choice == "electronic":
            self.player.skills['electronic'] = 15
            self.player.skills['songwriting'] = 10
            self.player.add_gear(GEAR_CATALOG.get("laptop_basic"))
            self.player.add_gear(GEAR_CATALOG.get("headphones_studio"))
            self.player.traits.append(TRAIT_CATALOG["night_owl"])
        elif bg_choice == "busker":
            self.player.skills['stage_presence'] = 15
            self.player.skills['guitar'] = 5
            self.player.energy = 100 # High stamina
            self.player.add_gear(GEAR_CATALOG.get("worn_acoustic_guitar"))
            self.player.money += 50 # Humble beginnings
            self.player.traits.append(TRAIT_CATALOG["resilient"])

        # Fallback if catalog items missing or not assigned above
        if not self.player.gear_inventory and GEAR_CATALOG.get("worn_acoustic_guitar"):
             self.player.add_gear(GEAR_CATALOG.get("worn_acoustic_guitar"))

        self.GAME_LOG.add_log_message(f"Welcome, {self.player.name}! Your journey begins now.")
        self.game_state = "main_menu"

    def handle_main_menu(self):
        main_menu_opts = {
            "explore": "Explore",
            "travel": "Travel",
            "phone": "Phone",
            "character": "Character",
            "system": "System",
            "quit": "Quit"
        }

        choice = self.ui.present_choices(
            main_menu_opts,
            f"What would {self.player.name} like to do?",
            context=self._get_main_menu_context(),
        )

        if choice == "quit":
            self.running = False
        else:
            self.game_state = choice

    def handle_explore_menu(self):
        if self.explore_menu_state == "location":
            location = self.player.current_location
            if not self.player.current_poi:
                self.GAME_LOG.add_log_message("You are not at a specific location. Travel to a place before trying to explore it.")
                self.game_state = "main_menu"
                return

            self.selected_poi = self.player.current_poi
            self.explore_menu_state = "poi"
        elif self.explore_menu_state == "poi":
            if self.selected_poi:
                location = self.player.current_location
                # Draw ASCII art for the location
                poi_id = self.selected_poi.poi_id if hasattr(self.selected_poi, 'poi_id') else self.selected_poi.venue_id
                art_to_display = ART.get(poi_id, ART['default'])
                self.ui.draw_ascii_art(art_to_display, 450, 120)

                interaction_options = {str(i): option for i, option in enumerate(self.selected_poi.get_interactions())}

                local_actions = self.location_action_engine.generate_actions(self.player, self.selected_poi, location)
                self._local_action_lookup = {}
                for idx, local_action in enumerate(local_actions):
                    action_key = f"local_{idx}"
                    interaction_options[action_key] = f"Local: {local_action.menu_label()}"
                    self._local_action_lookup[action_key] = local_action

                # Add dynamic opportunities for this POI
                for opp_id, opp_details in self.player.active_opportunities.items():
                    if opp_details["status"] == "available":
                        opp_data = self.OPPORTUNITY_CATALOG.get(opp_id)
                        if opp_data and opp_data.get("type") == "poi_interaction" and opp_details.get("poi_id") == poi_id:
                             interaction_options[opp_id] = opp_data["action_text"]

                if not self.player.has_home and getattr(self.selected_poi, "category", "") in ["TRANSPORT_BUS", "TRANSPORT_AIRPORT"]:
                    interaction_options["rough_sleep"] = "Sleep Rough (4 hours)"

                interaction_options["wander"] = "Look around (Trigger Events)"
                interaction_options["back"] = "Back"

                choice = self.ui.present_choices(
                    interaction_options,
                    f"Interact with {self.selected_poi.name}",
                    context=self._get_explore_context(location, self.selected_poi) if location else None,
                )
                if choice == "back":
                    self.explore_menu_state = "location"
                    self.selected_poi = None
                    self.game_state = "main_menu"
                elif choice in self._local_action_lookup:
                    self.handle_local_presence_action(self._local_action_lookup[choice])
                    self.explore_menu_state = "location"
                    self.selected_poi = None
                elif choice == "wander":
                    self.GAME_LOG.add_log_message("You take a moment to look around...")
                    self._advance_time_with_needs(15)

                    # Gain Inspiration
                    insp_gain = random.randint(2, 5)
                    self.player.inspiration = min(100, self.player.inspiration + insp_gain)
                    self.GAME_LOG.add_log_message(f"You feel inspired by the surroundings. (+{insp_gain} Inspiration)")

                    event_result = check_for_random_event(self.player, current_poi_name=self.selected_poi.name, chance=0.8, ui=self.ui, logger=self.GAME_LOG)
                    if not event_result["event_triggered"]:
                        self.GAME_LOG.add_log_message("It seems quiet right now.")
                else:
                    self.handle_interaction(interaction_options[choice])
                    if self.explore_menu_state not in ["shop", "write_song_menu", "talk", "dialogue", "dealership", "pawn_sell", "pawn_buy"]:
                        self.explore_menu_state = "location"
                        self.selected_poi = None
            else:
                self.explore_menu_state = "location"
        elif self.explore_menu_state == "pawn_sell":
            if self.selected_poi:
                pawnable_items = [i for i in self.player.gear_inventory if not i.is_broken and i.cost > 0]
                if not pawnable_items:
                    self.GAME_LOG.add_log_message("You have no valuable items to pawn.")
                    self.explore_menu_state = "poi"
                else:
                    inventory_opts = {}
                    for i, item in enumerate(pawnable_items):
                        pawn_value = max(1, int(item.cost * 0.25)) # Pawn for 25% of cost
                        inventory_opts[str(i)] = f"{item.name} (Pawn for ${pawn_value})"
                    inventory_opts["back"] = "Cancel"

                    choice = self.ui.present_choices(inventory_opts, "Select item to pawn:")
                    if choice == "back":
                        self.explore_menu_state = "poi"
                    else:
                        item_to_pawn = pawnable_items[int(choice)]
                        pawn_value = max(1, int(item_to_pawn.cost * 0.25))

                        self.player.remove_gear(item_to_pawn)
                        self.player.money += pawn_value

                        self.selected_poi.pawned_items.append(item_to_pawn)

                        self.GAME_LOG.add_log_message(f"You pawned your {item_to_pawn.name} for ${pawn_value}.")
                        self.explore_menu_state = "poi"
            else:
                self.explore_menu_state = "location"
        elif self.explore_menu_state == "pawn_buy":
            if self.selected_poi:
                pawned_items = self.selected_poi.pawned_items
                if not pawned_items:
                    self.GAME_LOG.add_log_message("The pawn shop has no items for sale.")
                    self.explore_menu_state = "poi"
                else:
                    inventory_opts = {}
                    for i, item in enumerate(pawned_items):
                        buyback_price = max(1, int(item.cost * 0.60)) # Buy back for 60% of cost
                        inventory_opts[str(i)] = f"{item.name} (Buy for ${buyback_price})"
                    inventory_opts["back"] = "Cancel"

                    choice = self.ui.present_choices(inventory_opts, "Browse Pawn Shop:")
                    if choice == "back":
                        self.explore_menu_state = "poi"
                    else:
                        item_to_buy = pawned_items[int(choice)]
                        buyback_price = max(1, int(item_to_buy.cost * 0.60))

                        if self.player.money >= buyback_price:
                            if self.player.can_carry_gear(item_to_buy):
                                self.player.money -= buyback_price
                                self.selected_poi.pawned_items.remove(item_to_buy)
                                self.player.add_gear(item_to_buy)
                                self.GAME_LOG.add_log_message(f"You bought back a {item_to_buy.name} for ${buyback_price}.")
                                self.explore_menu_state = "poi"
                            else:
                                self.GAME_LOG.add_log_message(f"You can't carry {item_to_buy.name}.")
                        else:
                            self.GAME_LOG.add_log_message(f"You can't afford {item_to_buy.name}. Need ${buyback_price}, Cash: ${self.player.money}.")
            else:
                self.explore_menu_state = "location"
        elif self.explore_menu_state == "dealership":
            if self.selected_poi:
                vehicle_inventory = {}
                if self.selected_poi.shop_inventory_vehicle_ids:
                    for vehicle_id in self.selected_poi.shop_inventory_vehicle_ids:
                        vehicle = VEHICLE_CATALOG.get(vehicle_id)
                        if vehicle:
                            vehicle_inventory[vehicle_id] = f"{vehicle.name} - ${vehicle.cost}"
                vehicle_inventory["back"] = "Back"

                choice = self.ui.present_choices(vehicle_inventory, f"Vehicles at {self.selected_poi.name}")
                if choice == "back":
                    self.explore_menu_state = "poi"
                else:
                    vehicle_to_buy = VEHICLE_CATALOG.get(choice)
                    if vehicle_to_buy:
                        if any(v.name == vehicle_to_buy.name for v in self.player.vehicles):
                            self.GAME_LOG.add_log_message(f"You already own a {vehicle_to_buy.name}.")
                        elif self.player.money >= vehicle_to_buy.cost:
                            self.player.money -= vehicle_to_buy.cost
                            self.player.add_vehicle(vehicle_to_buy)
                            self.GAME_LOG.add_log_message(f"You bought a {vehicle_to_buy.name}.")
                            self.sound_manager.play_buy_sound()
                        else:
                            self.GAME_LOG.add_log_message(f"You can't afford the {vehicle_to_buy.name}. Cost: ${vehicle_to_buy.cost}, Cash: ${self.player.money}.")
            else:
                self.explore_menu_state = "location"
        elif self.explore_menu_state == "shop":
            if self.selected_poi:
                shop_inventory = {}
                for item_id in self.selected_poi.shop_inventory_item_ids:
                    item = GEAR_CATALOG.get(item_id)
                    if item:
                        shop_inventory[item_id] = f"{item.name} - ${item.cost} (Size: {item.size})"
                shop_inventory["back"] = "Back"

                choice = self.ui.present_choices(shop_inventory, f"Items at {self.selected_poi.name}")
                if choice == "back":
                    self.explore_menu_state = "poi"
                else:
                    item_to_buy = GEAR_CATALOG.get(choice)
                    if item_to_buy:
                        if self.player.money >= item_to_buy.cost:
                            if self.player.can_carry_gear(item_to_buy):
                                self.player.money -= item_to_buy.cost
                                self.player.add_gear(item_to_buy)
                                self.GAME_LOG.add_log_message(f"You bought {item_to_buy.name}.")
                                self.sound_manager.play_buy_sound()
                            else:
                                self.GAME_LOG.add_log_message(f"You can't carry {item_to_buy.name}.")
                        else:
                            self.GAME_LOG.add_log_message(f"You can't afford {item_to_buy.name}. Cost: ${item_to_buy.cost}, Cash: ${self.player.money}.")
            else:
                self.explore_menu_state = "location"
        elif self.explore_menu_state == "write_song_menu":
            if self.songwriting_stage == "choose_genre":
                genre_options = {genre: genre for genre in self.SONG_GENRES}
                genre_options["back"] = "Cancel"

                choice = self.ui.present_choices(genre_options, "Choose a genre for your song:")
                if choice == "back":
                    self.explore_menu_state = "poi"
                    self.songwriting_stage = None
                else:
                    self.song_in_progress['genre'] = choice
                    self.songwriting_stage = "choose_theme"

            elif self.songwriting_stage == "choose_theme":
                theme_options = {k: f"{v['name']} ({v['description']})" for k, v in THEME_CATALOG.items()}
                theme_options["none"] = "No specific theme"

                choice = self.ui.present_choices(theme_options, "Choose a lyrical theme:")
                if choice != "none":
                    self.song_in_progress['theme'] = choice

                self.songwriting_stage = "get_title"

            elif self.songwriting_stage == "get_title":
                song_title = self.ui.get_text_input("Enter a title for your new song:")
                if song_title:
                    self.song_in_progress['title'] = song_title
                    self.songwriting_stage = "confirm_start"
                else:
                    self.GAME_LOG.add_log_message("Songwriting cancelled.")
                    self.explore_menu_state = "poi"
                    self.songwriting_stage = None

            elif self.songwriting_stage == "confirm_start":
                title = self.song_in_progress.get('title', 'Untitled')
                genre = self.song_in_progress.get('genre', 'Unknown')

                insp_cost = 50
                can_use_insp = self.player.inspiration >= insp_cost

                start_label = f"Start writing '{title}' ({genre}) (Will take ~8 hours)"
                start_insp_label = f"Start with Inspiration (Cost {insp_cost} Insp, Quality++)"

                confirm_options = {"yes": start_label}
                if can_use_insp:
                    confirm_options["yes_insp"] = start_insp_label
                if self.player.band and len(self.player.band.members) > 1:
                    confirm_options["band"] = f"Collaborate with {self.player.band.name} (Uses Band Skills & Chemistry)"
                confirm_options["no"] = "Cancel"

                choice = self.ui.present_choices(confirm_options, f"Ready to write? (Inspiration: {self.player.inspiration}/100)")

                if choice in ["yes", "yes_insp", "band"]:
                    if choice == "yes_insp":
                        self.player.inspiration -= insp_cost
                        self.song_in_progress['inspiration_bonus'] = 0.2 # 20% quality boost
                        self.GAME_LOG.add_log_message("You channel your inspiration into the song!")
                    else:
                        self.song_in_progress['inspiration_bonus'] = 0.0

                    self.song_in_progress['is_collaborative'] = (choice == "band")
                    self.songwriting_stage = "writing_components"
                    # This will fall through to the next stage in the same frame
                else:
                    self.GAME_LOG.add_log_message("Songwriting cancelled.")
                    self.explore_menu_state = "poi"
                    self.songwriting_stage = None

            if self.songwriting_stage == "writing_components":
                # This is a non-interactive stage, so we do the work and then change state.
                insp_bonus = self.song_in_progress.get('inspiration_bonus', 0.0)
                is_collaborative = self.song_in_progress.get('is_collaborative', False)

                if is_collaborative:
                    self.GAME_LOG.add_log_message(f"You call a band meeting to write '{self.song_in_progress.get('title')}'.")
                    band = self.player.band

                    # Band chemistry determines how well skills blend and how likely conflicts are
                    chem_bonus = (band.chemistry - 50) / 200.0 # From -0.25 to +0.25

                    # Simulating conflicts
                    conflict_chance = max(0.05, 0.5 - (band.chemistry / 150.0))
                    if random.random() < conflict_chance:
                        # Find two different members to argue
                        if len(band.members) >= 2:
                            m1, m2 = random.sample(band.members, 2)
                            self.GAME_LOG.add_log_message(f"DRAMA: {m1.name} and {m2.name} argue over the creative direction!")
                            band.update_chemistry(-5)
                            chem_bonus -= 0.15 # Massive penalty to the song quality
                            self.player.stress = min(100, self.player.stress + 10)
                        else:
                            self.GAME_LOG.add_log_message("DRAMA: Creative blocks and frustration hit the room.")
                            chem_bonus -= 0.1
                    elif random.random() < (band.chemistry / 150.0):
                        self.GAME_LOG.add_log_message("SYNERGY: The band locks into a perfect groove!")
                        chem_bonus += 0.15
                        band.update_chemistry(2)
                        self.player.stress = max(0, self.player.stress - 5)

                    # Lyrics (2 hours)
                    lyrical_depth = self._calculate_song_component_quality('songwriting') + insp_bonus + chem_bonus
                    self.song_in_progress['lyrical_depth'] = max(0.1, min(1.0, lyrical_depth))
                    self._advance_time_with_needs(120)
                    self.GAME_LOG.add_log_message(f"The band hashes out the lyrics. (Quality: {self.song_in_progress['lyrical_depth']:.2f})")

                    # Melody (3 hours)
                    catchiness = self._calculate_song_component_quality('songwriting', 'guitar') + insp_bonus + chem_bonus
                    self.song_in_progress['catchiness'] = max(0.1, min(1.0, catchiness))
                    self._advance_time_with_needs(180)
                    self.GAME_LOG.add_log_message(f"Working out the vocal melodies together. (Quality: {self.song_in_progress['catchiness']:.2f})")

                    # Arrangement / Complexity (3 hours)
                    music_complexity = self._calculate_song_component_quality('guitar', 'songwriting', weight=0.7) + insp_bonus + chem_bonus
                    self.song_in_progress['music_complexity'] = max(0.1, min(1.0, music_complexity))

                    originality = self._calculate_song_component_quality('songwriting') + insp_bonus + chem_bonus
                    self.song_in_progress['originality'] = max(0.1, min(1.0, originality))

                    self._advance_time_with_needs(180)
                    self.GAME_LOG.add_log_message(f"The final arrangement comes together. (Complexity: {self.song_in_progress['music_complexity']:.2f}, Originality: {self.song_in_progress['originality']:.2f})")

                else:
                    self.GAME_LOG.add_log_message("You spend a long day writing solo...")

                    # Lyrics (2 hours)
                    # Temporarily force player skills if not collaborating
                    old_band = self.player.band
                    self.player.band = None
                    lyrical_depth = self._calculate_song_component_quality('songwriting') + insp_bonus
                    self.player.band = old_band
                    self.song_in_progress['lyrical_depth'] = min(1.0, lyrical_depth)
                    self._advance_time_with_needs(120)
                    self.GAME_LOG.add_log_message(f"The lyrics are coming together (Quality: {lyrical_depth:.2f})")

                    # Melody (3 hours)
                    self.player.band = None
                    catchiness = self._calculate_song_component_quality('songwriting', 'guitar') + insp_bonus
                    self.player.band = old_band
                    self.song_in_progress['catchiness'] = min(1.0, catchiness)
                    self._advance_time_with_needs(180)
                    self.GAME_LOG.add_log_message(f"You've got a catchy melody! (Quality: {catchiness:.2f})")

                    # Arrangement / Complexity (3 hours)
                    self.player.band = None
                    music_complexity = self._calculate_song_component_quality('guitar', 'songwriting', weight=0.7) + insp_bonus
                    originality = self._calculate_song_component_quality('songwriting') + insp_bonus
                    self.player.band = old_band

                    self.song_in_progress['music_complexity'] = min(1.0, music_complexity)
                    self.song_in_progress['originality'] = min(1.0, originality)

                    self._advance_time_with_needs(180)
                    self.GAME_LOG.add_log_message(f"The arrangement is taking shape (Complexity: {music_complexity:.2f}, Originality: {originality:.2f})")

                self.GAME_LOG.add_log_message("The song is written! Now to finalize it.")
                self.songwriting_stage = "invite_feature"
                # Fall through to the invite stage immediately

            if self.songwriting_stage == "invite_feature":
                eligible_features = []
                for npc_id in self.player.contacts:
                    npc = self.NPC_REGISTRY.get(npc_id)
                    if npc and npc.skills:
                        if self.player.band is None or npc not in self.player.band.members:
                            if npc.relationship_with_player in [RelationshipStatus.FRIENDLY, RelationshipStatus.ALLY]:
                                eligible_features.append(npc)

                if not eligible_features:
                    self.songwriting_stage = "finalize_song"
                    # Fall through if no one is available
                else:
                    feature_options = {npc.npc_id: f"Ask {npc.name} to feature on the song." for npc in eligible_features}
                    feature_options["none"] = "Finish the song solo"

                    choice = self.ui.present_choices(feature_options, "A collaboration could make this song a hit...")
                    if choice == "none":
                        self.songwriting_stage = "finalize_song"
                    else:
                        self.song_in_progress['featured_artist_id'] = choice
                        self.songwriting_stage = "finalize_song"

            if self.songwriting_stage == "finalize_song":
                # This is also a non-interactive stage
                title = self.song_in_progress.get('title', 'Untitled')
                genre = self.song_in_progress.get('genre', 'Rock')
                theme = self.song_in_progress.get('theme', None)
                author = self.player.name

                originality=self.song_in_progress.get('originality', 0.5)
                catchiness=self.song_in_progress.get('catchiness', 0.5)
                lyrical_depth=self.song_in_progress.get('lyrical_depth', 0.5)
                music_complexity=self.song_in_progress.get('music_complexity', 0.5)

                # Apply Theme Bonus
                if theme:
                    t_data = THEME_CATALOG.get(theme)
                    if t_data and genre in t_data['genre_affinity']:
                        bonus = t_data['bonus_multiplier']
                        # Bonus applies to specific stats or overall quality. Let's boost stats.
                        originality = min(1.0, originality * bonus)
                        lyrical_depth = min(1.0, lyrical_depth * bonus)
                        self.GAME_LOG.add_log_message(f"Theme '{t_data['name']}' fits {genre} perfectly! (Quality Bonus)")

                featured_artist_id = self.song_in_progress.get('featured_artist_id')
                if featured_artist_id:
                    npc = self.NPC_REGISTRY.get(featured_artist_id)
                    if npc:
                        author = f"{self.player.name} (feat. {npc.name})"
                        # Add a bonus based on the NPC's primary skill
                        # This is a simple way to represent their contribution
                        primary_skill = max(npc.skills, key=npc.skills.get)
                        skill_bonus = npc.skills.get(primary_skill, 0) / 200.0 # 50 skill = 0.25 bonus
                        catchiness += skill_bonus
                        music_complexity += skill_bonus

                new_song = Song(
                    title=title,
                    author=author,
                    genre=genre,
                    originality=originality,
                    catchiness=catchiness,
                    lyrical_depth=lyrical_depth,
                    music_complexity=music_complexity,
                    theme=theme
                )

                self.player.songs_written.append(new_song)
                self.GAME_LOG.add_log_message(f"You finished writing '{new_song.title}'! Overall Quality: {new_song.song_quality:.2f}")

                # Clean up and exit songwriting mode
                self.song_in_progress = {}
                self.songwriting_stage = None
                self.explore_menu_state = "poi"

        elif self.explore_menu_state == "remix_menu":
            # This is a full state machine, but simplified for now
            released_songs = [s for s in self.player.songs_written if s.is_released and not s.is_remix]
            if not released_songs:
                self.GAME_LOG.add_log_message("You have no songs that can be remixed.")
                self.explore_menu_state = "poi"
                return

            song_options = {str(i): f"'{s.title}' (Q: {s.song_quality:.2f})" for i, s in enumerate(released_songs)}
            song_options["back"] = "Cancel"

            choice = self.ui.present_choices(song_options, "Which song would you like to remix?")

            if choice == "back":
                self.explore_menu_state = "poi"
            else:
                original_song = released_songs[int(choice)]
                self.GAME_LOG.add_log_message(f"You spend a few days working on a remix of '{original_song.title}'...")
                self._advance_time_with_needs(2 * 24 * 60) # 2 days

                # Calculate remix quality
                electronic_skill = self.player.skills.get('electronic', 0)
                musicianship_skill = self.player.skills.get('musicianship', 0)

                # Remix quality depends on original quality and new skills
                remix_quality = (original_song.song_quality * 0.5) + (electronic_skill / 100.0 * 0.3) + (musicianship_skill / 100.0 * 0.2)
                remix_quality = min(1.0, remix_quality * random.uniform(0.8, 1.2)) # Add randomness

                # Create new song object for the remix
                remix_song = Song(
                    title=f"{original_song.title} (Remix)",
                    author=self.player.name,
                    genre="Electronic", # Remixes are often electronic
                    song_quality=remix_quality
                )
                remix_song.is_remix = True
                remix_song.original_song_id = original_song.song_id

                self.player.songs_written.append(remix_song)
                self.GAME_LOG.add_log_message(f"You finished the remix! Final Quality: {remix_song.song_quality:.2f}")
                self.explore_menu_state = "poi"
        elif self.explore_menu_state == "submit_demo":
            if self.selected_poi and self.selected_poi.category == "OFFICE_RECORD_LABEL":
                recorded_songs = [s for s in self.player.songs_written if s.is_recorded]
                if not recorded_songs:
                    self.GAME_LOG.add_log_message("You have no recorded songs to submit as a demo.")
                    self.explore_menu_state = "poi"
                    return

                song_options = {str(i): f"'{s.title}' (Rec Q: {s.recording_quality:.2f})" for i, s in enumerate(recorded_songs)}
                song_options["back"] = "Cancel"

                choice = self.ui.present_choices(song_options, "Which song would you like to submit?")

                if choice == "back":
                    self.explore_menu_state = "poi"
                else:
                    selected_song = recorded_songs[int(choice)]
                    cost = 20 # Mailing cost
                    if self.player.money < cost:
                        self.GAME_LOG.add_log_message(f"You can't afford to mail the demo. Need $20, Cash: ${self.player.money}.")
                        self.explore_menu_state = "poi"
                        return

                    self.player.money -= cost
                    self._advance_time_with_needs(60) # 1 hour to prepare and mail
                    outcome = self._resolve_demo_submission_outcome(selected_song, self.selected_poi)

                    # Schedule the response
                    response_time = current_game_time.copy()
                    response_time.add_days(3)
                    self.player.schedule.add_event(
                        start_time=response_time,
                        end_time=response_time,
                        description=f"Response from {self.selected_poi.name} re: '{selected_song.title}'",
                        category="LABEL_RESPONSE",
                        details={
                            'song_id': selected_song.song_id,
                            'label_id': self.selected_poi.poi_id,
                            'submission_outcome': outcome["band"],
                            'advance_mult': outcome["data"].get("advance_mult", 1.0),
                            'marketing_mult': outcome["data"].get("marketing_mult", 1.0),
                        }
                    )
                    self.GAME_LOG.add_log_message(f"You mail a demo of '{selected_song.title}' to {self.selected_poi.name}.")
                    self.GAME_LOG.add_log_message(outcome["data"]["message"])
                    self.GAME_LOG.add_log_message("You expect to hear back in a few days.")
                    self.explore_menu_state = "poi"
            else:
                self.explore_menu_state = "poi"
        elif self.explore_menu_state == "record_song":
            recording_setup = self._get_recording_setup(self.selected_poi)
            if recording_setup:
                unrecorded_songs = [s for s in self.player.songs_written if not s.is_recorded]
                if not unrecorded_songs:
                    self.GAME_LOG.add_log_message("You have no unrecorded songs to record.")
                    self.explore_menu_state = "poi"
                    return

                song_options = {str(i): f"'{s.title}' (Quality: {s.song_quality:.2f})" for i, s in enumerate(unrecorded_songs)}
                song_options["back"] = "Cancel"

                choice = self.ui.present_choices(song_options, recording_setup["title"])

                if choice == "back":
                    self.explore_menu_state = "poi"
                else:
                    selected_song = unrecorded_songs[int(choice)]
                    studio_quality = recording_setup["studio_quality"]

                    prod_cost = 0
                    prod_bonus = 0.0
                    prod_choice = "none"
                    if recording_setup["allow_producer"]:
                        prod_options = {
                            "none": "Self-Produced (No Cost)",
                            "local": "Hire Local Producer (+$200, +Quality)",
                            "pro": "Hire Pro Producer (+$1000, ++Quality)"
                        }
                        prod_choice = self.ui.present_choices(prod_options, "Select Producer:")
                        if prod_choice == "local":
                            prod_cost = 200
                            prod_bonus = 0.1
                        elif prod_choice == "pro":
                            prod_cost = 1000
                            prod_bonus = 0.25

                    session_cost = recording_setup["base_session_cost"] + prod_cost

                    if self.player.money < session_cost:
                        self.GAME_LOG.add_log_message(f"You can't afford the ${session_cost} total session cost. Cash: ${self.player.money}.")
                        self.explore_menu_state = "poi"
                        return

                    self.player.money -= session_cost
                    self._advance_time_with_needs(recording_setup["minutes"])
                    if session_cost > 0:
                        self.GAME_LOG.add_log_message(f"{recording_setup['log']} (-${session_cost})")
                    else:
                        self.GAME_LOG.add_log_message(recording_setup["log"])

                    final_quality = self._calculate_recording_quality(selected_song, studio_quality, prod_bonus)

                    selected_song.mark_as_recorded(final_quality)
                    self.GAME_LOG.add_log_message(f"'{selected_song.title}' is now recorded! Recording Quality: {final_quality:.2f}")
                    if prod_choice != "none":
                        self.GAME_LOG.add_log_message(f"Producer's touch added {prod_bonus:.2f} quality!")
                    self.explore_menu_state = "poi"
            else:
                # Should not happen if triggered correctly
                self.explore_menu_state = "location"
        elif self.explore_menu_state == "talk":
            npcs_here = [npc for npc in self.NPC_REGISTRY.values() if npc.current_location == self.selected_poi]
            if not npcs_here:
                self.GAME_LOG.add_log_message("No one here to talk to.")
                self.explore_menu_state = "poi"
            else:
                npc_options = {npc.npc_id: npc.name for npc in npcs_here}
                npc_options["back"] = "Back"

                choice = self.ui.present_choices(npc_options, "Interact with who?")
                if choice == "back":
                    self.explore_menu_state = "poi"
                else:
                    self.selected_npc = self.NPC_REGISTRY[choice]
                    # Add to contacts if not already there
                    if self.selected_npc.npc_id not in self.player.contacts:
                        self.player.contacts.append(self.selected_npc.npc_id)
                        self.GAME_LOG.add_log_message(f"You added {self.selected_npc.name} to your contacts.")

                    self.explore_menu_state = "npc_interaction_menu"

        elif self.explore_menu_state == "npc_interaction_menu":
            if self.selected_npc:
                interaction_opts = {
                    "chat": "Chat",
                    "gift": "Give Gift",
                    "flirt": "Flirt",
                    "jam": "Jam Session (Requires Instrument)",
                    "back": "Back"
                }

                choice = self.ui.present_choices(interaction_opts, f"Interaction: {self.selected_npc.name}")

                if choice == "back":
                    self.explore_menu_state = "talk"
                    self.selected_npc = None
                elif choice == "chat":
                    self.explore_menu_state = "dialogue"
                    self.conversation_history = []
                    self.player_input = ""
                elif choice == "gift":
                    self.explore_menu_state = "gifting"
                elif choice == "flirt":
                    # Simple romance logic
                    roll = random.random()
                    if roll < 0.3 + (self.selected_npc.romance_interest / 100.0):
                        self.selected_npc.romance_interest += 10
                        self.GAME_LOG.add_log_message(f"You flirted with {self.selected_npc.name}. They blushed! (Interest: {self.selected_npc.romance_interest})")
                        self.selected_npc.romance_status = "Dating" # Fast track for demo
                    else:
                        self.GAME_LOG.add_log_message(f"You flirted with {self.selected_npc.name}. They didn't seem interested.")
                    self.explore_menu_state = "poi"
                elif choice == "jam":
                    self.handle_jam_session(self.selected_npc)
                    # Stay in menu or go back? Let's go back to see the result log clearly.
                    self.explore_menu_state = "poi"
            else:
                self.explore_menu_state = "poi"

        elif self.explore_menu_state == "view_events":
            if self.selected_poi and isinstance(self.selected_poi, Venue):
                if not self.selected_poi.events_hosted:
                    self.GAME_LOG.add_log_message("There are no events scheduled here right now.")
                    self.explore_menu_state = "poi"
                    return

                event_options = {str(i): f"{event.name} ({event.event_type})" for i, event in enumerate(self.selected_poi.events_hosted)}

                # Add dynamic opportunities that are venue-specific
                for opp_id, status in self.player.active_opportunities.items():
                    if status == "available":
                        opp_data = self.OPPORTUNITY_CATALOG.get(opp_id)
                        if opp_data and opp_data.get("type") == "venue_event" and opp_data.get("venue_id") == self.selected_poi.venue_id:
                            event_options[opp_id] = opp_data["action_text"]

                event_options["back"] = "Back"

                choice = self.ui.present_choices(event_options, f"Events at {self.selected_poi.name}")

                if choice == "back":
                    self.explore_menu_state = "poi"
                elif choice in self.OPPORTUNITY_CATALOG:
                    # Dynamic Venue Event (Battle of the Bands)
                    opp_data = self.OPPORTUNITY_CATALOG[choice]
                    temp_event = Event(name=opp_data['name'], event_type="BATTLE_OF_THE_BANDS", location=self.selected_poi)
                    self.active_performance = temp_event
                    self.game_state = "performance"
                    self.performance_stage = "choose_song"
                else:
                    # Regular, hardcoded event
                    event = self.selected_poi.events_hosted[int(choice)]
                    if event.event_type == "OPEN_MIC" or event.event_type == "CLUB_GIG":
                        can_perform, message, _ = event.can_perform(self.player)
                        if not can_perform:
                            self.GAME_LOG.add_log_message(message)
                            self.explore_menu_state = "poi"
                            return
                        self.active_performance = event
                        self.performance_setlist = []
                        self.game_state = "performance"
                        self.performance_stage = "choose_song"
                    else:
                        self.GAME_LOG.add_log_message("You can't sign up for this type of event yet.")
                        self.explore_menu_state = "poi"
            else:
                self.explore_menu_state = "poi"

        elif self.explore_menu_state == "gifting":
            if not self.player.gear_inventory:
                self.GAME_LOG.add_log_message("You have nothing to give.")
                self.explore_menu_state = "dialogue"
                return

            inventory_options = {str(i): item.name for i, item in enumerate(self.player.gear_inventory)}
            inventory_options["back"] = "Cancel"

            choice = self.ui.present_choices(inventory_options, f"Give a gift to {self.selected_npc.name}:")

            if choice == "back":
                self.explore_menu_state = "dialogue"
            else:
                item_to_give = self.player.gear_inventory[int(choice)]

                # Check preferences
                relationship_gain = 1 # Default gain for any gift
                if item_to_give.category in self.selected_npc.gift_preferences:
                    relationship_gain = self.selected_npc.gift_preferences[item_to_give.category]
                    self.GAME_LOG.add_log_message(f"{self.selected_npc.name} loves the {item_to_give.name}!")
                else:
                    self.GAME_LOG.add_log_message(f"{self.selected_npc.name} seems pleased with the gift.")

                self.selected_npc.update_relationship(relationship_gain)
                self.player.remove_gear(item_to_give)
                self.explore_menu_state = "dialogue"

        elif self.explore_menu_state == "dialogue":
            if self.selected_npc:
                self.ui.draw_dialogue_screen(self.selected_npc.name, self.conversation_history, self.player_input)
                for event in pygame.event.get():
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_RETURN:
                            if self.player_input.lower() == "bye":
                                self.selected_npc.update_relationship(1) # Small boost for talking
                                self.explore_menu_state = "poi"
                                self.selected_npc = None
                            elif self.player_input.lower() == "gift":
                                self.explore_menu_state = "gifting"
                                self.player_input = ""
                            else:
                                self.conversation_history.append(f"You: {self.player_input}")
                                response = generate_npc_response(self.player_input, self.selected_npc, self.player.name)
                                self.conversation_history.append(f"{self.selected_npc.name}: {response}")
                                self.player_input = ""
                        elif event.key == pygame.K_BACKSPACE:
                            self.player_input = self.player_input[:-1]
                        else:
                            self.player_input += event.unicode
            else:
                self.explore_menu_state = "poi"

    def handle_jam_session(self, npc):
        self.GAME_LOG.add_log_message(f"You ask {npc.name} to jam with you.")

        # Check if player has an instrument
        player_instruments = [item for item in self.player.gear_inventory if item.gear_type.startswith("INSTRUMENT") and not item.is_broken]
        if not player_instruments:
            self.GAME_LOG.add_log_message("You don't have a working instrument with you!")
            return

        # Apply durability to one random instrument used
        used_instrument = random.choice(player_instruments)
        used_instrument.take_damage(random.randint(5, 15)) # Jamming is hard work
        if used_instrument.is_broken:
             self.GAME_LOG.add_log_message(f"CRACK! Your {used_instrument.name} broke during the jam!")

        # Check if NPC is musical
        if not npc.skills:
            self.GAME_LOG.add_log_message(f"{npc.name} doesn't seem to play any instruments.")
            return

        self._advance_time_with_needs(60) # 1 hour jam

        # Calculate compatibility/quality
        # Player skill: Max of their instrument skills
        player_skill_level = 0
        for skill in ['guitar', 'bass', 'drums', 'keyboard', 'electronic']:
             player_skill_level = max(player_skill_level, self.player.skills.get(skill, 0))

        # NPC skill: Max of their skills
        npc_skill_level = max(npc.skills.values()) if npc.skills else 0

        # Skill difference
        diff = abs(player_skill_level - npc_skill_level)

        if player_skill_level < 5 and npc_skill_level < 5:
            self.GAME_LOG.add_log_message("It's a bit rough, but you both have fun making noise.")
            xp = 0.5
            rel_gain = 2
        elif player_skill_level > npc_skill_level + 20:
            self.GAME_LOG.add_log_message(f"You show {npc.name} a few tricks. They seem impressed.")
            xp = 0.2
            rel_gain = 5
        elif npc_skill_level > player_skill_level + 20:
            self.GAME_LOG.add_log_message(f"You struggle to keep up, but you learn a lot from {npc.name}.")
            xp = 2.0
            rel_gain = 3
        else:
            self.GAME_LOG.add_log_message("You lock into a great groove! The chemistry is undeniable.")
            xp = 1.0
            rel_gain = 8

        # Apply rewards
        primary_instrument_skill = "guitar" # Simplified: Assume guitar for now or pick based on inventory
        if any(i.name.lower().find("drum") != -1 for i in player_instruments): primary_instrument_skill = "drums"
        # ... logic to pick specific skill to upgrade could be better

        self.player.practice_skill(primary_instrument_skill, xp * 5) # Scale factor
        npc.update_relationship(rel_gain)

        # Gain Inspiration from Jamming
        insp_gain = random.randint(5, 10)
        self.player.inspiration = min(100, self.player.inspiration + insp_gain)
        self.GAME_LOG.add_log_message(f"Jamming gave you new ideas! (+{insp_gain} Inspiration)")

        self.player.energy -= 10
        self.player.stress = max(0, self.player.stress - 15) # Jamming relieves stress
        self.GAME_LOG.add_log_message(f"Jam session finished. Stress -15.")


    def _current_poi_id(self):
        if not self.player or not self.player.current_poi:
            return None
        return getattr(self.player.current_poi, "poi_id", getattr(self.player.current_poi, "venue_id", None))

    def _assess_local_action_requirements(self, local_action):
        requirements_map = {
            "pawn_item": [{"match_type": "semantic", "key": "instrument", "count": 1, "mandatory": False}],
            "network_scene": [{"match_type": "semantic", "key": "instrument", "count": 1, "mandatory": False}],
        }
        reqs = requirements_map.get(local_action.action_id, [])
        if not reqs:
            return None
        return self.inventory_service.assess_requirements(
            self.player,
            reqs,
            self.PLAYER_HOME_POI_ID_GLOBAL,
            self._current_poi_id(),
        )

    def _assess_gig_requirements(self):
        gig_requirements = [
            {"match_type": "semantic", "key": "instrument", "count": 1, "mandatory": True},
            {"match_type": "semantic", "key": "strings", "count": 1, "mandatory": True},
        ]
        assessment = self.inventory_service.assess_requirements(
            self.player,
            gig_requirements,
            self.PLAYER_HOME_POI_ID_GLOBAL,
            self._current_poi_id(),
        )
        location_ref = self._current_poi_id()
        assessment, assistant_hook = self.delegation_system.assistant_adjust_requirements(
            self.player,
            assessment,
            location_ref=location_ref,
            world_memory=self.world_memory,
        )
        if assistant_hook == "assistant_success":
            self.player.stress = max(0, self.player.stress - 2)
        elif assistant_hook == "assistant_prep_failure":
            self.player.stress = min(100, self.player.stress + 3)
        return assessment

    def handle_local_presence_action(self, local_action):
        if not self.selected_poi:
            self.GAME_LOG.add_log_message("No active place selected for local actions.")
            return

        local_req = self._assess_local_action_requirements(local_action)
        if local_req and local_req.status == "missing_and_severe":
            self.GAME_LOG.add_log_message(
                f"You cannot {local_action.label.lower()} right now. Missing: {', '.join(local_req.missing_severe)}."
            )
            return

        base_pressure = self.visibility_system.exposure_pressure(
            self.player.name,
            getattr(self.selected_poi, "parent_location_id", getattr(self.selected_poi, "venue_id", None)),
            getattr(self.selected_poi, "category", "").lower(),
            "high" if getattr(self.selected_poi, "category", "").lower() in {"downtown", "venue_club", "venue_bar"} else "medium",
            current_game_time.hour >= 18 or current_game_time.hour <= 1,
        )
        visibility_pressure = self.delegation_system.security_adjust_visibility_pressure(
            self.player,
            base_pressure,
            world_memory=self.world_memory,
            location_ref=getattr(self.selected_poi, "parent_location_id", None),
        )
        security_role = self.delegation_system.get_role(self.player, "security")
        security_quality = self.delegation_system.role_quality(security_role) if security_role else 0.0
        security_posture = security_role.modifiers.get("posture", "filtered") if security_role else "open"
        place_bucket = getattr(self.selected_poi, "category", "").lower()
        crowded = "high" if place_bucket in {"downtown", "venue_club", "venue_bar"} else "medium"
        visibility_pressure = self.public_interference_system.interference_pressure(
            base_visibility=visibility_pressure,
            place_type="venue" if "venue" in place_bucket else "street",
            crowd_level=crowded,
            security_quality=security_quality,
            security_posture=security_posture,
        )
        if visibility_pressure >= 18 and random.random() < min(0.55, visibility_pressure / 125.0):
            self.player.stress = min(100, self.player.stress + 4)
            self.world_memory.add(
                WorldMemoryEntry(
                    event_type="public_interference_spike",
                    involved_entities=[self.player.name],
                    location=getattr(self.selected_poi, "parent_location_id", None),
                    timestamp=current_game_time.copy(),
                    tags=["visibility", "interference"],
                    impact_score=1.7,
                    source_key=f"interference:{self.player.name}:{current_game_time.get_time_string_for_schedule()}:{getattr(self.selected_poi, 'parent_location_id', None)}",
                )
            )

        result = self.location_action_engine.execute_action(
            player=self.player,
            place_obj=self.selected_poi,
            location_obj=self.player.current_location,
            action=local_action,
            advance_time=self._advance_time_with_needs,
            logger=self.GAME_LOG,
            visibility_pressure=visibility_pressure,
        )

        if not result.get("ok"):
            self.GAME_LOG.add_log_message(result.get("explanation", "You cannot do that right now."))
            return

        self.GAME_LOG.add_log_message(result.get("explanation", "You spend time locally."))

        for granted_item_id in result.get("item_grants", []):
            granted_item = GEAR_CATALOG.get(granted_item_id)
            if granted_item:
                self.player.add_gear(granted_item)
                self.GAME_LOG.add_log_message(f"You obtain {granted_item.name} and add it to your carry.")

        if local_action.action_id == "stash_belongings" and self.player.gear_inventory:
            poi_id = getattr(self.selected_poi, "poi_id", None)
            if poi_id:
                self.inventory_service.ensure_player_fields(self.player)
                stash = self.player.temporary_stashes.setdefault(poi_id, [])
                item = self.player.gear_inventory.pop()
                stash.append(item)
                self.GAME_LOG.add_log_message(f"You stash {item.name} at this lodging for later.")
        elif local_action.action_id == "rent_room":
            checkout_time = current_game_time.copy()
            checkout_time.add_hours(16)
            self.player.rented_accommodation_info = {
                "poi_id": getattr(self.selected_poi, "poi_id", None),
                "checkout_time_obj": checkout_time,
            }

        encounter = result.get("encounter")
        if encounter:
            encounter_type = encounter.get("encounter_type", "encounter")
            reason_code = encounter.get("reason_code", "unknown")
            self.GAME_LOG.add_log_message(f"Encounter: {encounter_type} [{reason_code}].")



    def handle_interaction(self, interaction_text, time_cost=15):
        self.GAME_LOG.add_log_message(f"Selected interaction: {interaction_text}")

        home_only_actions = {
            "Rest (8 hours)",
            "Practice guitar (at home)",
            "Write a new song",
            "Create a Remix",
            "Relax at home (2 hours)",
        }
        if (
            self.selected_poi
            and getattr(self.selected_poi, "poi_id", None) == self.PLAYER_HOME_POI_ID_GLOBAL
            and not self.player.has_home
            and interaction_text in home_only_actions
        ):
            self.GAME_LOG.add_log_message("You do not live here anymore. You need cash or somewhere else to recover.")
            return

        # Some interactions have no time cost, handle them first
        if interaction_text == "View upcoming events":
            self.explore_menu_state = "view_events"
            return
        no_time_cost = interaction_text in [
            "Browse items for sale",
            "Buy Food Items",
            "Write a new song",
            "Book recording session",
            "Create a Remix",
            "Rest (8 hours)",
            "Browse vehicles",
            "Pawn Item",
            "Browse Pawn Shop",
            "Vocal Rest Treatment ($50, 4 hours)",
            "Physical Therapy ($100, 2 hours)",
            "Detox/Rehab ($500, 3 days)",
        ] or interaction_text.startswith("Submit Demo") or interaction_text.startswith("Order ") \
            or interaction_text.startswith("Book Rehearsal Slot") \
            or interaction_text.startswith("Rent Room") or interaction_text.startswith("Sleep (8 hours") \
            or interaction_text in ["Practice guitar (at home)", "Relax at home (2 hours)", "Get a haircut", "Shave or Trim beard", "Grab Coffee ($5)", "Grab Coffee ($6)", "People Watch", "Look for Local Flyers", "Look for Gig Flyers", "Relax", "Look for today's paper", "Ask for a journalist", "Inquire about PR representation", "Inquire about Local Artist Spotlight", "Sleep Rough (4 hours)"] \
            or "Talk" in interaction_text

        if not no_time_cost:
            self._advance_time_with_needs(time_cost)
        if interaction_text == "Browse items for sale":
            if self.selected_poi.shop_inventory_item_ids:
                self.explore_menu_state = "shop"
            else:
                self.GAME_LOG.add_log_message("Nothing for sale currently.")
        elif interaction_text == "Buy Food Items":
            if self.selected_poi.shop_inventory_item_ids:
                self.explore_menu_state = "shop"
            else:
                self.GAME_LOG.add_log_message("No food items are available here right now.")
        elif interaction_text == "Look around (Trigger Events)": # Renaming or handling if text differs
             pass # Handled by choice logic earlier, but if passed here:
             # Actually, "wander" key handles it directly in loop.
             # But if we want it to give inspiration:
             pass
        elif interaction_text == "Hire Bodyguard ($100/day)":
            if self.player.has_bodyguard:
                self.GAME_LOG.add_log_message("You already have a bodyguard.")
            elif self.player.money >= 100:
                self.player.money -= 100
                self.player.has_bodyguard = True
                self.GAME_LOG.add_log_message("You hired a bodyguard! Daily upkeep is $100.")
            else:
                self.GAME_LOG.add_log_message(f"You can't afford the initial fee. Need $100, Cash: ${self.player.money}.")
        elif interaction_text.startswith("Work Shift:"):
            # Parse earnings and time from text, e.g. "Work Shift: Stock Shelves ($20 / 4h)"
            try:
                parts = interaction_text.split("($")
                earnings_part = parts[1].split("/")[0].strip()
                time_part = parts[1].split("/")[1].split("h")[0].strip()

                earnings = int(earnings_part)
                hours = int(time_part)
                role_name = interaction_text.replace("Work Shift:", "").split("($")[0].strip()
                outcome = self._resolve_shift_outcome(role_name, earnings, hours)
                actual_earnings = max(8, int(round(earnings * outcome["data"]["pay_mult"])))

                self.GAME_LOG.add_log_message(f"You clock in for a {hours} hour {role_name.lower()} shift.")
                self._advance_time_with_needs(hours * 60)

                # Apply fatigue
                self.player.energy = max(0, self.player.energy - (12 * hours))
                self.player.stress = min(100, self.player.stress + (6 * hours))
                self.player.hunger = min(100, self.player.hunger + (5 * hours)) # Work makes you hungry
                self.player.comfort = max(0, self.player.comfort - (2 * hours))
                self.player.health = max(0, self.player.health - outcome["data"]["injury"])
                self.player.inspiration = min(100, self.player.inspiration + outcome["data"]["inspiration"])

                self.player.money += actual_earnings
                self.GAME_LOG.add_log_message(outcome["data"]["message"])
                self.GAME_LOG.add_log_message(
                    f"Shift complete. You earned ${actual_earnings}. (Energy -{12*hours}, Stress +{6*hours})"
                )
            except Exception as e:
                self.GAME_LOG.add_log_message(f"Error starting shift: {e}")
        elif interaction_text == "Practice guitar (at home)":
            hours = 2
            self.GAME_LOG.add_log_message("You settle in for a focused practice session.")
            self._advance_time_with_needs(hours * 60)
            self.player.practice_skill("guitar", hours)
            self.player.energy = max(0, self.player.energy - 8)
            self.player.inspiration = min(100, self.player.inspiration + 5)
            self.GAME_LOG.add_log_message("Your playing feels a little tighter. (+5 Inspiration)")
        elif interaction_text == "Relax at home (2 hours)":
            self.GAME_LOG.add_log_message("You take some time to decompress at home.")
            self._advance_time_with_needs(120)
            self.player.stress = max(0, self.player.stress - 15)
            self.player.energy = min(100, self.player.energy + 5)
            self.player.comfort = min(100, self.player.comfort + 10)
        elif interaction_text == "Sleep Rough (4 hours)":
            self.GAME_LOG.add_log_message("You try to sleep rough for a few hours.")
            self._advance_time_with_needs(240)
            self.player.energy = min(100, self.player.energy + 12)
            self.player.stress = min(100, self.player.stress + 6)
            self.player.comfort = max(0, self.player.comfort - 10)
            self.player.health = max(0, self.player.health - 2)
        elif interaction_text.startswith("Rent Room"):
            room_cost = 50 if "($50" in interaction_text else 60 if "($60" in interaction_text else 450 if "($450" in interaction_text else 0
            if self.player.money < room_cost:
                self.GAME_LOG.add_log_message(f"You need ${room_cost} to rent a room here.")
            else:
                self.player.money -= room_cost
                checkout_time = current_game_time.copy()
                checkout_time.add_hours(16)
                self.player.rented_accommodation_info = {
                    "poi_id": self.selected_poi.poi_id,
                    "checkout_time_obj": checkout_time,
                }
                self.GAME_LOG.add_log_message(f"You rent a room at {self.selected_poi.name} until {checkout_time.get_time_string_for_schedule()}.")
        elif interaction_text.startswith("Sleep (8 hours"):
            if self._has_active_room_rental(self.selected_poi) or (self.selected_poi and self.selected_poi.category == "HOME"):
                self.rest()
            else:
                self.GAME_LOG.add_log_message("You need to rent a room here before you can sleep.")
        elif interaction_text.startswith("Book Rehearsal Slot"):
            rehearsal_cost = 25 if "$25" in interaction_text else 10
            if self.player.money < rehearsal_cost:
                self.GAME_LOG.add_log_message(f"You need ${rehearsal_cost} to book rehearsal time.")
            else:
                self.player.money -= rehearsal_cost
                self.GAME_LOG.add_log_message("You book the room and rehearse for an hour.")
                self._advance_time_with_needs(60)
                self.player.practice_skill("guitar", 1)
                self.player.practice_skill("stage_presence", 1)
                self.player.energy = max(0, self.player.energy - 6)
                self.player.stress = max(0, self.player.stress - 4)
        elif interaction_text.startswith("Order "):
            if not self.selected_poi or not getattr(self.selected_poi, "menu_items", None):
                self.GAME_LOG.add_log_message("Nothing is available to order right now.")
                return

            menu_item = next(
                (item for item in self.selected_poi.menu_items if item["display_text"] == interaction_text),
                None,
            )
            if not menu_item:
                self.GAME_LOG.add_log_message("That item is no longer available.")
                return

            cost = menu_item.get("cost", 0)
            if self.player.money < cost:
                self.GAME_LOG.add_log_message("You cannot afford that order.")
                return

            self.player.money -= cost
            self._advance_time_with_needs(30)
            effects = menu_item.get("effects", {})
            self.player.hunger = max(0, min(100, self.player.hunger + effects.get("hunger", 0)))
            self.player.energy = max(0, min(100, self.player.energy + effects.get("energy", 0)))
            self.player.comfort = max(0, min(100, self.player.comfort + effects.get("comfort", 0)))
            self.GAME_LOG.add_log_message(f"You order {menu_item['display_text']}.")
        elif interaction_text == "Get a haircut":
            haircut_cost = 15
            if self.player.money < haircut_cost:
                self.GAME_LOG.add_log_message(f"You need ${haircut_cost} for a haircut.")
            else:
                self.player.money -= haircut_cost
                self._advance_time_with_needs(45)
                self.player.hair_length = max(0, self.player.hair_length - 2)
                self.player.hair_growth_progress = 0.0
                self.GAME_LOG.add_log_message("Fresh cut. You look sharper.")
        elif interaction_text == "Shave or Trim beard":
            beard_cost = 10
            if self.player.money < beard_cost:
                self.GAME_LOG.add_log_message(f"You need ${beard_cost} for beard grooming.")
            else:
                self.player.money -= beard_cost
                self._advance_time_with_needs(30)
                self.player.beard_length = max(0, self.player.beard_length - 2)
                self.player.beard_growth_progress = 0.0
                self.GAME_LOG.add_log_message("Beard trimmed.")
        elif interaction_text in ["Grab Coffee ($5)", "Grab Coffee ($6)"]:
            coffee_cost = 6 if "$6" in interaction_text else 5
            if self.player.money < coffee_cost:
                self.GAME_LOG.add_log_message("You cannot afford a coffee right now.")
            else:
                self.player.money -= coffee_cost
                self._advance_time_with_needs(30)
                self.player.energy = min(100, self.player.energy + 8)
                self.player.stress = max(0, self.player.stress - 3)
                self.GAME_LOG.add_log_message("The coffee helps you reset.")
        elif interaction_text == "People Watch":
            self._advance_time_with_needs(60)
            self.player.inspiration = min(100, self.player.inspiration + 8)
            self.player.stress = max(0, self.player.stress - 5)
            self.GAME_LOG.add_log_message("Watching the crowd gives you ideas. (+8 Inspiration)")
        elif interaction_text in ["Look for Local Flyers", "Look for Gig Flyers"]:
            self._advance_time_with_needs(45)
            self.player.inspiration = min(100, self.player.inspiration + 5)
            self.GAME_LOG.add_log_message("You pick up a few leads and scene rumors.")
            if self.player.current_location and self.player.current_location.venues:
                venue = self.player.current_location.venues[0]
                self.GAME_LOG.add_log_message(f"Flyer spotted: check {venue.name} for upcoming shows.")
        elif interaction_text == "Relax":
            self._advance_time_with_needs(60)
            self.player.stress = max(0, self.player.stress - 8)
            self.player.comfort = min(100, self.player.comfort + 5)
            self.GAME_LOG.add_log_message("The downtime helps you clear your head.")
        elif interaction_text == "Look for today's paper":
            self._advance_time_with_needs(15)
            feed = get_news_feed()
            if feed:
                self.GAME_LOG.add_log_message(feed[0])
            else:
                self.GAME_LOG.add_log_message("Nothing about the local music scene made the paper today.")
        elif interaction_text == "Ask for a journalist":
            self._advance_time_with_needs(20)
            if self.player.fame >= 40:
                self.GAME_LOG.add_log_message("A journalist agrees to keep an eye on your next show.")
            else:
                self.GAME_LOG.add_log_message("The newsroom staff tells you to build more local buzz first.")
        elif interaction_text == "Inquire about PR representation":
            self._advance_time_with_needs(30)
            if self.player.has_pr_manager:
                self.GAME_LOG.add_log_message("You already have PR representation.")
            elif self.player.fame >= self.player.pr_manager_fame_requirement_to_hire:
                self.player.has_pr_manager = True
                self.GAME_LOG.add_log_message("Sharp PR agrees to represent you.")
            else:
                self.GAME_LOG.add_log_message("Sharp PR says you need more traction before they can help.")
        elif interaction_text == "Inquire about Local Artist Spotlight":
            self._advance_time_with_needs(30)
            if any(song.is_recorded for song in self.player.songs_written):
                self.GAME_LOG.add_log_message("The station tells you to send over your strongest recorded track.")
            else:
                self.GAME_LOG.add_log_message("The station wants a recorded demo before they can consider you.")
        elif interaction_text == "Repair Instrument":
            # Simple repair all for now or submenu? Let's do simple repair mechanics.
            # Find broken/damaged instruments
            damaged = [i for i in self.player.gear_inventory if i.durability < 100 and "INSTRUMENT" in i.gear_type]
            if not damaged:
                self.GAME_LOG.add_log_message("You don't have any damaged instruments.")
            else:
                # Calculate total cost
                total_cost = sum([int((100 - i.durability) * 0.5) for i in damaged]) # $0.5 per point
                if total_cost == 0: total_cost = 5 # Minimum bench fee

                if self.player.money >= total_cost:
                    self.player.money -= total_cost
                    for i in damaged:
                        i.repair()
                    self.GAME_LOG.add_log_message(f"Repaired {len(damaged)} instruments for ${total_cost}.")
                else:
                    self.GAME_LOG.add_log_message(f"Repair costs ${total_cost}. Cash: ${self.player.money}.")
        elif interaction_text.startswith("Submit Demo"):
            min_fame = self.selected_poi.min_fame_to_submit
            if self.player.fame >= min_fame:
                self.explore_menu_state = "submit_demo"
            else:
                self.GAME_LOG.add_log_message(f"You need at least {min_fame} fame to submit a demo here. Current fame: {self.player.fame}.")
        elif interaction_text == "Write a new song":
            self.explore_menu_state = "write_song_menu"
            self.songwriting_stage = "choose_genre"
            self.song_in_progress = {}
        elif interaction_text == "Book recording session":
            self.explore_menu_state = "record_song"
        elif interaction_text in ["Record a rough demo", "Record a home demo"]:
            self.explore_menu_state = "record_song"
        elif interaction_text == "Create a Remix":
            self.explore_menu_state = "remix_menu"
        elif interaction_text == "Rest (8 hours)":
            self.rest()
        elif "Talk" in interaction_text: # More robust check
            owner_npc = getattr(self.selected_poi, "owner_npc_id", None)
            if hasattr(owner_npc, "npc_id"):
                self._open_direct_npc_interaction(owner_npc)
            else:
                matched_npc = None
                if self.selected_poi:
                    lowered = interaction_text.lower()
                    for npc in self.NPC_REGISTRY.values():
                        if npc.current_location == self.selected_poi and any(part in npc.name.lower() for part in lowered.replace("talk to", "").split()):
                            matched_npc = npc
                            break
                if matched_npc:
                    self._open_direct_npc_interaction(matched_npc)
                else:
                    self.explore_menu_state = "talk"
        elif interaction_text == "Browse vehicles":
            if self.selected_poi.shop_inventory_vehicle_ids:
                self.explore_menu_state = "dealership"
            else:
                self.GAME_LOG.add_log_message("No vehicles for sale currently.")
        elif interaction_text == "Pawn Item":
            self.explore_menu_state = "pawn_sell"
        elif interaction_text == "Browse Pawn Shop":
            self.explore_menu_state = "pawn_buy"
        elif interaction_text == "Vocal Rest Treatment ($50, 4 hours)":
            if self.player.money < 50:
                self.GAME_LOG.add_log_message("You can't afford this treatment.")
            else:
                self.player.money -= 50
                self._advance_time_with_needs(240)
                self.player.vocal_strain = max(0, self.player.vocal_strain - 50)
                self.GAME_LOG.add_log_message("You rest your voice with professional guidance. (Vocal Strain -50)")
        elif interaction_text == "Physical Therapy ($100, 2 hours)":
            if self.player.money < 100:
                self.GAME_LOG.add_log_message("You can't afford physical therapy.")
            else:
                self.player.money -= 100
                self._advance_time_with_needs(120)
                self.player.wrist_strain = max(0, self.player.wrist_strain - 40)
                self.GAME_LOG.add_log_message("The therapist works out the knots in your arms. (Wrist Strain -40)")
        elif interaction_text == "Detox/Rehab ($500, 3 days)":
            if self.player.money < 500:
                self.GAME_LOG.add_log_message("Rehab isn't cheap. You need $500.")
            else:
                self.player.money -= 500
                self.GAME_LOG.add_log_message("You check yourself in to get clean. This will take a while...")
                self._advance_time_with_needs(72 * 60)
                self.player.substance_dependency = 0
                self.player.health = min(100, self.player.health + 20)
                self.GAME_LOG.add_log_message("You've completed the program. You feel terrible, but clean. (Dependency removed)")

    def handle_travel_menu(self):
        travel_options = {
            "intra_city": f"Travel within {self.player.current_location.name}",
            "inter_city": "Travel to another city",
            "back": "Back"
        }
        choice = self.ui.present_choices(travel_options, "Travel")

        if choice == "back":
            self.game_state = "main_menu"
        elif choice == "intra_city":
            if not self.player.current_poi:
                self.GAME_LOG.add_log_message("You are not at a specific Point of Interest to travel from.")
            else:
                city_obj = self.player.current_location
                all_city_targets = city_obj.points_of_interest + city_obj.venues
                reachable_targets = []
                for target in all_city_targets:
                    if target.name == self.player.current_poi.name:
                        continue
                    if self._get_intra_city_connection(self.player.current_poi, target):
                        reachable_targets.append(target)

                if not reachable_targets:
                    self.GAME_LOG.add_log_message("No direct local routes are available from here right now.")
                else:
                    dest_map = {t.poi_id if hasattr(t, 'poi_id') else t.venue_id: t for t in reachable_targets}
                    dest_disp = {k: v.name for k, v in dest_map.items()}
                    dest_disp["back"] = "Cancel"

                    chosen_dest_key = self.ui.present_choices(
                        dest_disp,
                        f"Travel from {self.player.current_poi.name}",
                        context={
                            "eyebrow": "Local Movement",
                            "subtitle": "Pick a reachable place first, then choose how you want to get there.",
                            "panel_title": "Travel Notes",
                            "details": [
                                "Walking is cheap but burns time.",
                                "Bike routes only work if you actually own a bike.",
                                "Taxis save time but cost cash you may need elsewhere.",
                            ],
                        },
                    )
                    if chosen_dest_key != "back":
                        chosen_dest_poi = dest_map[chosen_dest_key]
                        connection_details = self._get_intra_city_connection(self.player.current_poi, chosen_dest_poi)
                        mode_options = self._build_intra_city_mode_options(connection_details)
                        mode_options["back"] = "Back"

                        chosen_mode = self.ui.present_choices(
                            mode_options,
                            f"How do you want to get to {chosen_dest_poi.name}?",
                            context={
                                "eyebrow": "Route Choice",
                                "subtitle": f"Leaving from {self.player.current_poi.name}. Different transport choices trade time for money and access.",
                                "panel_title": "Route Data",
                                "details": [
                                    f"Destination: {chosen_dest_poi.name}",
                                    f"Current cash: ${self.player.money}",
                                    "More transport types can plug into this same flow later.",
                                ],
                            },
                        )
                        if chosen_mode in ("walk_locked", "bike_locked", "taxi_locked", "back"):
                            if chosen_mode.endswith("_locked"):
                                self.GAME_LOG.add_log_message("That route is not available with your current transport options.")
                        else:
                            travel_mode = connection_details[chosen_mode]
                            travel_time_minutes = travel_mode.get("time", 0)
                            travel_cost = travel_mode.get("cost", 0)
                            if self.player.money >= travel_cost:
                                self.player.money -= travel_cost
                                self.player.travel_within_city(chosen_dest_poi, travel_time_minutes)
                                self._advance_time_with_needs(travel_time_minutes)
                                self.update_npc_locations(current_game_time)
                                price_text = "for free" if travel_cost == 0 else f"for ${travel_cost}"
                                self.GAME_LOG.add_log_message(
                                    f"You traveled to {chosen_dest_poi.name} by {chosen_mode} in {travel_time_minutes} minutes {price_text}."
                                )
                            else:
                                self.GAME_LOG.add_log_message(f"You can't afford that trip. Need ${travel_cost}, Cash: ${self.player.money}.")
            self.game_state = "main_menu"
        elif choice == "inter_city":
            connections = self.player.current_location.travel_connections
            if not connections:
                self.GAME_LOG.add_log_message(f"No inter-city routes from {self.player.current_location.name}.")
                self.game_state = "main_menu"
                return

            dest_opts = {}
            for dest_name, details in connections.items():
                route_mode = self._get_public_travel_mode(details, self.player.current_poi)
                dest_opts[dest_name] = f"{dest_name} by {route_mode.capitalize()} ({details['time_hours']}h, ${details['cost']})"
            dest_opts["back"] = "Cancel"

            departure_name = self.player.current_poi.name if self.player.current_poi else self.player.current_location.name
            dest_choice = self.ui.present_choices(
                dest_opts,
                f"Leaving {self.player.current_location.name}",
                context={
                    "eyebrow": "Inter-City Travel",
                    "subtitle": f"Choose where to go from {departure_name}. Longer trips now depend on route method, cost, and where you are standing.",
                    "panel_title": "Departure Notes",
                    "details": [
                        f"Current cash: ${self.player.money}",
                        "Public routes require the right hub for that route.",
                        "Owned vehicles can leave from anywhere, but carry fuel and breakdown risk.",
                    ],
                },
            )
            if dest_choice != "back":
                travel_details = connections[dest_choice]
                public_mode = self._get_public_travel_mode(travel_details, self.player.current_poi)
                selected_vehicle = None

                transport_options = {"public": f"Public {public_mode.capitalize()} (${travel_details['cost']}, {travel_details['time_hours']}h)"}
                for index, vehicle in enumerate(self.player.vehicles):
                    transport_options[f"vehicle_{index}"] = f"Drive {vehicle.name}"
                transport_options["back"] = "Cancel"

                transport_choice = self.ui.present_choices(
                    transport_options,
                    f"How do you want to travel to {dest_choice}?",
                    context={
                        "eyebrow": "Transport Mode",
                        "subtitle": "Public transit is more predictable. Personal vehicles trade cost certainty for mechanical risk and freedom.",
                        "panel_title": "Trip Snapshot",
                        "details": [
                            f"Route type: {public_mode.capitalize()}",
                            f"Base ticket: ${travel_details['cost']}",
                            f"Estimated trip time: {travel_details['time_hours']}h",
                        ],
                    },
                )
                if transport_choice == "back":
                    self.game_state = "main_menu"
                    return

                using_public_transit = transport_choice == "public"
                if not using_public_transit:
                    vehicle_index = int(transport_choice.replace("vehicle_", ""))
                    selected_vehicle = self.player.vehicles[vehicle_index]

                # Ticket Class Selection
                ticket_class = "economy"
                if using_public_transit:
                    if not self._public_travel_requires_hub(public_mode, self.player.current_poi):
                        if public_mode == "plane":
                            self.GAME_LOG.add_log_message("You need to be at an airport to catch that flight.")
                        else:
                            self.GAME_LOG.add_log_message("You need to be at a bus or transit hub to take public transport out of the city.")
                        self.game_state = "main_menu"
                        return
                    class_opts = {
                        "economy": f"Economy (${travel_details['cost']})",
                        "business": f"Business (${travel_details['cost']*2}) - Less Stress",
                        "first": f"First Class (${travel_details['cost']*5}) - Comfort"
                    }
                    ticket_class = self.ui.present_choices(
                        class_opts,
                        f"Choose your {public_mode} ticket",
                        context={
                            "eyebrow": "Seat Class",
                            "subtitle": "Pay more for a less miserable trip.",
                            "panel_title": "Class Effects",
                            "details": [
                                "Economy is cheapest and roughest.",
                                "Business reduces travel stress.",
                                "First class is expensive but more comfortable.",
                            ],
                        },
                    )

                # Check money for public transport here (approx check)
                base_cost = travel_details['cost']
                multiplier = 1
                if ticket_class == "business": multiplier = 2
                elif ticket_class == "first": multiplier = 5

                can_afford_ticket = True
                if using_public_transit and self.player.money < base_cost * multiplier:
                    can_afford_ticket = False

                if can_afford_ticket:
                    dest_loc_obj = self.WORLD_MAP.get(dest_choice)
                    if dest_loc_obj:
                        # Estimate distance from time (assuming 60km/h average for generic "time_hours" in data)
                        estimated_distance = travel_details['time_hours'] * 60.0

                        transport_mode = selected_vehicle if selected_vehicle else public_mode

                        cost_override = None
                        if using_public_transit:
                            cost_override = travel_details['cost']

                        # Initialize Travel
                        self.travel_manager = self.player.start_travel(dest_loc_obj, estimated_distance, transport_mode, cost_override, ticket_class)

                        if self.travel_manager:
                            self.transit_session = self.transit_layer.start_session(self.travel_manager)
                            self.game_state = "travel_active"
                            if using_public_transit:
                                self.GAME_LOG.add_log_message(f"Departing for {dest_loc_obj.name} by {public_mode} in {ticket_class} class.")
                            else:
                                self.GAME_LOG.add_log_message(f"You hit the road for {dest_loc_obj.name} in your {selected_vehicle.name}.")
                            self.GAME_LOG.add_log_message(
                                f"Transit phase active: {self.transit_session.chunk_minutes}-minute decision chunks until arrival."
                            )
                        else:
                            self.GAME_LOG.add_log_message("Travel preparation failed. Check your gear load/capacity or requirements.")
                else:
                    self.GAME_LOG.add_log_message(f"You can't afford to travel. Estimated fare: ${base_cost * multiplier}, Cash: ${self.player.money}.")

            if self.game_state != "travel_active":
                self.game_state = "main_menu"

    def rest(self, hours=8):
        if self.player.current_poi and getattr(self.player.current_poi, "poi_id", None) == self.PLAYER_HOME_POI_ID_GLOBAL and not self.player.has_home:
            self.GAME_LOG.add_log_message("You do not have that apartment anymore.")
            return
        self.GAME_LOG.add_log_message(f"You rest for {hours} hours.")
        minutes_to_advance = hours * 60

        # Get rest quality from current POI, default to 0.5
        rest_quality = getattr(self.player.current_poi, 'rest_quality', 0.5)

        # Energy and stress recovery are now based on rest quality
        energy_gain = int(hours * 5 * (1 + rest_quality)) # Base 5/hr, max 10/hr at quality 1.0
        stress_reduction = int(hours * 3 * (1 + rest_quality)) # Base 3/hr, max 6/hr

        self.player.energy = min(100, self.player.energy + energy_gain)
        self.player.stress = max(0, self.player.stress - stress_reduction)

        self.GAME_LOG.add_log_message(f"You recovered {energy_gain} energy and lost {stress_reduction} stress.")

        self._advance_time_with_needs(minutes_to_advance)

    def process_time_based_player_needs(self, player, minutes_just_passed):
        if minutes_just_passed <= 0: return
        hours_passed_float = minutes_just_passed / 60.0
        if player.current_poi and hasattr(player.current_poi, 'comfort_modifier_hourly'):
            comfort_change = hours_passed_float * player.current_poi.comfort_modifier_hourly
            player.comfort = min(100, max(0, player.comfort + comfort_change))
            player.comfort = int(round(player.comfort))
        is_at_player_home = player.current_poi and self.PLAYER_HOME_POI_ID_GLOBAL and \
                            hasattr(player.current_poi, 'poi_id') and \
                            player.current_poi.poi_id == self.PLAYER_HOME_POI_ID_GLOBAL
        if is_at_player_home:
            homesickness_reduction_per_hour_at_home = 5
            player.homesickness = max(0, player.homesickness - (hours_passed_float * homesickness_reduction_per_hour_at_home))
            player.homesickness = int(round(player.homesickness))
        else:
            homesickness_increase_per_hour_away = 0.5
            player.homesickness = min(100, player.homesickness + (hours_passed_float * homesickness_increase_per_hour_away))
            player.homesickness = int(round(player.homesickness))
        if player.homesickness > 75:
            stress_increase_rate_from_homesickness = ((player.homesickness - 75) / 25.0) * 1.0
            player.stress = min(100, player.stress + (hours_passed_float * stress_increase_rate_from_homesickness))
            player.stress = int(round(player.stress))
        hunger_increase_per_hour = 2.5
        player.hunger = min(100, player.hunger + (hours_passed_float * hunger_increase_per_hour))
        player.hunger = int(round(player.hunger))
        if player.hunger > 90:
            stress_from_starvation_hourly_rate = 2.0
            player.stress = min(100, player.stress + (hours_passed_float * stress_from_starvation_hourly_rate))
            player.stress = int(round(player.stress))
            # Starvation saps energy rapidly
            energy_loss_starvation = 5.0 * hours_passed_float
            player.energy = max(0, player.energy - energy_loss_starvation)
            player.energy = int(round(player.energy))

        if player.hunger > 80:
            player.health = max(0, player.health - int(round(hours_passed_float * 1.5)))
        if player.stress > 85:
            player.health = max(0, player.health - int(round(hours_passed_float * 1.0)))
        if player.comfort < 20:
            player.health = max(0, player.health - int(round(hours_passed_float * 0.5)))
        if player.energy <= 10 and minutes_just_passed >= 240:
            player.health = max(0, player.health - 2)
        if not player.has_home and not player.rented_accommodation_info:
            player.comfort = max(0, player.comfort - int(round(hours_passed_float * 1.5)))
            player.stress = min(100, player.stress + int(round(hours_passed_float * 1.0)))

        # Withdrawals
        if player.substance_dependency > 20:
            withdrawal_rate = (player.substance_dependency / 100.0) * 2.0
            player.stress = min(100, player.stress + int(round(hours_passed_float * withdrawal_rate)))
            player.energy = max(0, player.energy - int(round(hours_passed_float * withdrawal_rate)))

        if player.current_poi and getattr(player.current_poi, "category", "") == "HOME" and player.hunger < 50 and player.stress < 60:
            player.health = min(100, player.health + int(round(hours_passed_float * 0.3)))

        # Passive recovery from strain if resting
        if player.energy > 60 and player.stress < 40:
            player.vocal_strain = max(0, player.vocal_strain - (hours_passed_float * 0.5))
            player.wrist_strain = max(0, player.wrist_strain - (hours_passed_float * 0.5))

        POINTS_PER_DAY_HAIR = 10.0; POINTS_PER_DAY_BEARD = 12.5
        hair_growth_to_add = (minutes_just_passed / (24.0 * 60.0)) * POINTS_PER_DAY_HAIR
        player.hair_growth_progress += hair_growth_to_add
        beard_growth_to_add = (minutes_just_passed / (24.0 * 60.0)) * POINTS_PER_DAY_BEARD
        player.beard_growth_progress += beard_growth_to_add

        if player.hair_growth_progress >= player.HAIR_POINTS_PER_LENGTH_LEVEL:
            levels_gained = int(player.hair_growth_progress // player.HAIR_POINTS_PER_LENGTH_LEVEL)
            player.hair_length = min(player.MAX_HAIR_LENGTH, player.hair_length + levels_gained)
            player.hair_growth_progress %= player.HAIR_POINTS_PER_LENGTH_LEVEL
            if levels_gained > 0 and self.GAME_LOG: self.GAME_LOG.add_message(f"DEBUG: Your hair grew! New length: {player.hair_length}/{player.MAX_HAIR_LENGTH}")

        if player.beard_growth_progress >= player.BEARD_POINTS_PER_LENGTH_LEVEL:
            levels_gained = int(player.beard_growth_progress // player.BEARD_POINTS_PER_LENGTH_LEVEL)
            player.beard_length = min(player.MAX_BEARD_LENGTH, player.beard_length + levels_gained)
            player.beard_growth_progress %= player.BEARD_POINTS_PER_LENGTH_LEVEL
            if levels_gained > 0 and self.GAME_LOG: self.GAME_LOG.add_message(f"DEBUG: Your beard grew! New length: {player.beard_length}/{player.MAX_BEARD_LENGTH}")

    def update_npc_locations(self, gt_obj):
        time_slot_key = self._get_time_slot_key(gt_obj)
        for npc in self.NPC_REGISTRY.values():
            # Check for tour completion first
            if npc.on_tour and gt_obj >= npc.tour_end_date:
                npc.on_tour = False
                npc.tour_end_date = None
                self.GAME_LOG.add_log_message(f"GOSSIP: {npc.name} has returned from their tour.")

            # If on tour, they are not at a specific location and don't follow a schedule
            if npc.on_tour:
                npc.current_location = None
                continue

            dest_ref = npc.schedule.get(time_slot_key)
            dest = None
            if isinstance(dest_ref, (PointOfInterest, Venue, Location)): dest = dest_ref
            elif isinstance(dest_ref, str): dest = self.get_poi_or_venue_by_id(dest_ref) or self.WORLD_MAP.get(dest_ref)
            if dest is None : dest = npc.home_location
            if npc.npc_id == "sarah001":
                comm_hall = self.get_poi_or_venue_by_id("hometown_community_hall")
                if comm_hall and any(e.name == "Open Mic Night" and e.is_active for e in getattr(comm_hall, 'events_hosted', [])):
                    scheduled_loc_for_open_mic = npc.schedule.get("open_mic_night_at_community_hall")
                    if isinstance(scheduled_loc_for_open_mic, str): scheduled_loc_for_open_mic = self.get_poi_or_venue_by_id(scheduled_loc_for_open_mic)
                    if scheduled_loc_for_open_mic == comm_hall: dest = comm_hall
            if npc.current_location != dest: npc.current_location = dest

    def _calculate_npc_fame(self, npc):
        """Calculates a fame score for an NPC to determine which venues they can book."""
        if not npc.skills:
            return 0

        # 1. Fame from skills
        skill_fame = sum(npc.skills.get(s, 0) for s in ['songwriting', 'guitar', 'vocals', 'stage_presence'])

        # 2. Fame from chart performance
        chart_fame = 0
        for chart in self.ACTIVE_CHARTS:
            for entry in chart.entries:
                if entry['artist_name'] == npc.name:
                    # More points for higher positions on the chart
                    chart_fame += (chart.max_size - entry['current_position'] + 1) * 5

        total_fame = skill_fame + chart_fame
        return total_fame

    def _schedule_npc_tour(self, npc, tour_data):
        """Schedules a tour for an NPC, adding events to venues in different cities."""
        self.GAME_LOG.add_log_message(f"GOSSIP: Looks like {npc.name} is going on the '{tour_data['name']}' tour!")
        npc.on_tour = True

        # Calculate tour duration to set an end date
        total_days = 0
        for gig_template in tour_data['gig_templates']:
            total_days += gig_template['days_offset_max']

        tour_end_date = current_game_time.copy()
        tour_end_date.add_days(total_days + 7) # Add an extra week for buffer
        npc.tour_end_date = tour_end_date

        last_gig_date = current_game_time.copy()
        for i, gig_template in enumerate(tour_data['gig_templates']):
            offset = random.randint(gig_template['days_offset_min'], gig_template['days_offset_max'])
            gig_date = last_gig_date.copy()
            gig_date.add_days(offset)

            city_name = random.choice(gig_template['city_options'])
            city_venues = [v for v in self.WORLD_MAP[city_name].venues if v.venue_type in gig_template['venue_type_options']]
            if not city_venues:
                continue # Skip if no suitable venue

            city_venues = sorted(
                city_venues,
                key=lambda v: v.prestige + self._venue_memory_bias(getattr(v, "venue_id", None)),
                reverse=True,
            )
            venue = city_venues[0]
            gig_name = f"TOUR: {npc.name} at {venue.name} ({gig_date.get_time_string_for_schedule(date_only=True)})"

            new_gig = Event(
                name=gig_name,
                event_type=gig_template['event_type'],
                location=venue,
                is_npc_gig=True
            )
            venue.add_event(new_gig)
            last_gig_date = gig_date

    def update_npc_careers(self):
        """
        Weekly check to update the careers of NPCs, especially musicians.
        This includes releasing new songs and booking gigs.
        """
        for npc in self.NPC_REGISTRY.values():
            if npc.career_stage == "active_musician" and npc.skills:
                npc_fame = self._calculate_npc_fame(npc)
                release_score = min(15, int(npc.skills.get('songwriting', 0))) + min(10, int(npc_fame / 20))
                if self._passes_contextual_threshold(release_score, 92):
                    self.generate_npc_song(npc)

                gig_score = min(14, int(npc_fame / 12)) + min(10, int(npc.skills.get('stage_presence', 0)))
                if self._passes_contextual_threshold(gig_score, 96):
                    if npc_fame > 20: # Must have a minimum level of fame to book gigs
                        home_location = self.WORLD_MAP.get(npc.home_location.parent_location_id if hasattr(npc.home_location, 'parent_location_id') else npc.home_location.name)
                        if home_location:
                            suitable_venues = [v for v in home_location.venues if v.allows_player_booking and v.prestige <= (npc_fame / 10)]
                            if suitable_venues:
                                venue_to_book = random.choice(suitable_venues)
                                gig_date = current_game_time.copy()
                                gig_date.add_days(random.randint(14, 28))
                                gig_name = f"Show: {npc.name} ({gig_date.get_time_string_for_schedule(date_only=True)})"
                                if not any(gig_name in e.name for e in venue_to_book.events_hosted):
                                    new_gig = Event(name=gig_name, event_type="CLUB_GIG", location=venue_to_book, is_npc_gig=True)
                                    venue_to_book.add_event(new_gig)
                                    self.GAME_LOG.add_log_message(f"GOSSIP: You see a flyer that {npc.name} is playing a show at {venue_to_book.name} soon.")

                                    # Simulate the gig outcome for the venue's prestige
                                    venue_to_book.weeks_without_events = 0
                                    npc_quality = npc_fame + sum(npc.skills.values())
                                    if npc_quality > (venue_to_book.prestige * 50):
                                        # Legendary show for this venue
                                        venue_to_book.update_prestige(0.1)
                                    elif npc_quality < (venue_to_book.prestige * 10):
                                        # Flop
                                        venue_to_book.update_prestige(-0.1)

                tour_score = min(18, int(npc_fame / 18))
                if npc_fame > 200 and not npc.on_tour and self._passes_contextual_threshold(tour_score, 108):
                    suitable_tours = [t for t in self.TOURS if t['min_fame'] <= npc_fame]
                    if suitable_tours:
                        tour_to_take = random.choice(suitable_tours)
                        self._schedule_npc_tour(npc, tour_to_take)

    def generate_npc_song(self, npc):
        """
        Generates a new song for an NPC based on their skills.
        """
        # Simplified song generation for NPCs
        songwriting_skill = npc.skills.get('songwriting', 0)
        # Use their best instrument skill
        instrument_skills = {k: v for k, v in npc.skills.items() if k not in ['songwriting', 'stage_presence', 'vocals']}
        best_instrument_skill = max(instrument_skills.values()) if instrument_skills else 0

        # Simple quality calculation based on skills. Max possible is ~1.0
        base_quality = (songwriting_skill * 0.6 + best_instrument_skill * 0.4) / 50.0
        random_factor = random.uniform(0.8, 1.2)
        song_quality = min(1.0, base_quality * random_factor)

        # Recording quality is derived from their overall skill level
        recording_quality = min(1.0, song_quality * random.uniform(0.7, 1.1))

        # Create the song
        title = f"{npc.name}'s Tune #{len(npc.songs_written) + 1}"
        genre = random.choice(self.SONG_GENRES)

        new_song = Song(
            title=title,
            author=npc.name,
            genre=genre,
            song_quality=song_quality
        )
        new_song.mark_as_recorded(recording_quality)
        new_song.mark_as_released(current_game_time)

        npc.songs_written.append(new_song)
        self.GAME_LOG.add_log_message(f"GOSSIP: You hear that {npc.name} just dropped a new track called '{title}'.")

    def handle_phone_menu(self):
        if self.phone_menu_state == "main":
            phone_menu_opts = {
                "news": "Read News Feed",
                "schedule": "Schedule",
                "music": "Music",
                "contacts": "Contacts",
                "web": "Web",
            }
            if self.player.has_manager:
                phone_menu_opts["agent"] = "Call Agent"

            # Add dynamic opportunities
            if self.player.pending_contracts:
                phone_menu_opts["label_offers"] = f"View Record Deal Offer ({len(self.player.pending_contracts)})"

            for opp_id, opp_details in self.player.active_opportunities.items():
                if opp_details["status"] == "available":
                    if opp_id.startswith('guest_feature_'):
                        npc_id = opp_id.replace('guest_feature_', '')
                        npc = self.NPC_REGISTRY.get(npc_id)
                        if npc:
                            phone_menu_opts[opp_id] = f"Accept feature request from {npc.name}"
                    elif opp_id.startswith('tour_offer_'):
                        tour_id = opp_id.replace('tour_offer_', '')
                        tour_data = next((t for t in self.TOURS if t['tour_id'] == tour_id), None)
                        if tour_data:
                            phone_menu_opts[opp_id] = f"Accept tour offer: '{tour_data['name']}'"
                    else:
                        opp_data = self.OPPORTUNITY_CATALOG.get(opp_id)
                        if opp_data and opp_data.get("type") == "phone":
                            phone_menu_opts[opp_id] = opp_data["action_text"]

            phone_menu_opts["back"] = "Back"

            choice = self.ui.present_choices(phone_menu_opts, "Phone")

            if choice == "back":
                self.game_state = "main_menu"
            elif choice == "music":
                self.game_state = "music_menu"
                self.music_menu_state = "main"
            elif choice == "label_offers":
                self.phone_menu_state = "label_offers"
            elif choice in self.OPPORTUNITY_CATALOG or choice.startswith('guest_feature_') or choice.startswith('tour_offer_'):
                # Handle the selected opportunity
                self.handle_opportunity(choice)
                self.phone_menu_state = "main" # Return to phone menu
            elif choice == "agent":
                self.phone_menu_state = "agent"
            elif choice == "news":
                self.phone_menu_state = "news"
            else:
                self.phone_menu_state = choice
        elif self.phone_menu_state == "news":
            feed = get_news_feed()
            if not feed:
                info = "No news yet."
            else:
                info = "--- LATEST NEWS ---\n" + "\n".join(feed[:10])

            self.ui.present_choices({"back": "Back"}, info)
            self.phone_menu_state = "main"

        elif self.phone_menu_state == "agent":
            self.handle_agent_menu()
        elif self.phone_menu_state == "contacts":
            self.handle_contacts_menu()
        elif self.phone_menu_state == "schedule":
            upcoming_events = self.player.schedule.get_upcoming_events(current_game_time, limit=5)
            self.ui.draw_schedule_screen(upcoming_events)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.phone_menu_state = "main"
        elif self.phone_menu_state == "web":
            self.handle_web_menu()
        elif self.phone_menu_state == "label_offers":
            # For now, we only handle one offer at a time.
            if not self.player.pending_contracts:
                self.GAME_LOG.add_log_message("You have no pending contract offers.")
                self.phone_menu_state = "main"
                return

            contract = self.player.pending_contracts[0]
            offer_options = {
                "accept": "Accept Offer",
                "negotiate": f"Negotiate Terms ({contract.label_patience} attempts left)",
            }
            if self.player.has_manager:
                offer_options["manager_negotiate"] = f"Ask Manager to Negotiate ({contract.label_patience} attempts left)"
            offer_options["decline"] = "Decline Offer"
            offer_options["back"] = "Decide later"

            # This is a bit of a hack. We should have a dedicated screen.
            # For now, we'll just print the contract to the log.
            self.GAME_LOG.add_log_message("--- Contract Offer ---")
            for line in str(contract).split('\n'):
                self.GAME_LOG.add_log_message(line)

            choice = self.ui.present_choices(offer_options, f"Offer from {contract.label_name}")

            if choice == "accept":
                marketing_support_bonus = 1.0 + min(1.0, contract.marketing_budget_per_release / 1000.0)
                self.player.signed_label_deal = {
                    "label_name": contract.label_name,
                    "label_poi_id": contract.label_poi_id,
                    "advance_money": contract.advance_money,
                    "royalty_rate": contract.royalty_rate,
                    "marketing_budget_per_release": contract.marketing_budget_per_release,
                    "marketing_support_bonus": marketing_support_bonus,
                }
                self.player.money += contract.advance_money
                self.GAME_LOG.add_log_message(f"You signed with {contract.label_name}! You received an advance of ${contract.advance_money}.")
                self.player.pending_contracts.clear()
                self.phone_menu_state = "main"
            elif choice == "negotiate":
                has_charisma = self.player.has_trait("charismatic")
                success, msg, pulled = contract.negotiate(self.player.fame, has_charisma)
                self.GAME_LOG.add_log_message(msg)
                if pulled:
                    self.player.pending_contracts.pop(0)
                    self.phone_menu_state = "main"
            elif choice == "decline":
                self.GAME_LOG.add_log_message(f"You declined the offer from {contract.label_name}.")
                self.player.pending_contracts.clear()
                self.phone_menu_state = "main"
            elif choice == "back":
                self.phone_menu_state = "main"


    def handle_agent_menu(self):
        opts = {
            "find_gig": "Find Gig (Immediate)",
            "seek_label": "Seek Record Deal",
            "plan_tour": "Plan Tour (Start Wizard)",
            "back": "Hang Up"
        }
        choice = self.ui.present_choices(opts, "Agent on the line: 'What can I do for you?'")

        if choice == "back":
            self.phone_menu_state = "main"
        elif choice == "find_gig":
            # Simplified gig finding logic
            self.GAME_LOG.add_log_message("Agent: 'Let me make some calls...'")
            self._advance_time_with_needs(60) # 1 hour

            if random.random() < 0.5 + (self.player.fame / 500.0):
                self.GAME_LOG.add_log_message("Agent: 'I found a slot at a club for tomorrow night!'")
                candidate_venues = sorted(
                    self.player.current_location.venues,
                    key=lambda venue: venue.prestige + self._venue_memory_bias(getattr(venue, "venue_id", None)),
                    reverse=True,
                ) if self.player.current_location else []
                if not candidate_venues:
                    self.GAME_LOG.add_log_message("Agent: 'Actually, I couldn't lock down a venue in your current city.'")
                    return

                venue = candidate_venues[0]
                booked_event = Event(
                    name=f"Agent Booked Gig @ {venue.name}",
                    event_type="OPEN_MIC" if self.player.fame < 50 else "CLUB_GIG",
                    location=venue,
                )
                venue.add_event(booked_event)
                gig_time = current_game_time.copy()
                gig_time.add_days(1)
                gig_time.hour = 20
                gig_end_time = gig_time.copy()
                gig_end_time.add_hours(2)
                self.player.schedule.add_event(
                    gig_time,
                    gig_end_time,
                    booked_event.name,
                    "Gig",
                    {"event_id": booked_event.event_id, "venue_id": venue.venue_id, "destination_id": venue.venue_id, "requires_presence": True},
                )
            else:
                self.GAME_LOG.add_log_message("Agent: 'Sorry, nothing available right now.'")

        elif choice == "seek_label":
            self.GAME_LOG.add_log_message("Agent: 'Let me pitch your portfolio to some A&R reps. Give me a few hours.'")
            self._advance_time_with_needs(180) # 3 hours

            manager_skill = 1
            for staff in self.player.staff:
                if staff.role == "Manager":
                    manager_skill = staff.skill_level
                    break

            # Base chance is dependent on fame, plus manager skill
            base_chance = min(0.8, (self.player.fame / 1000.0) + (manager_skill * 0.05))

            if random.random() < base_chance:
                # Success! Generate a contract
                label_names = ["Big Sonic Records", "IndiePulse Music", "Neon Nights Audio", "Monolith Media"]
                label_name = random.choice(label_names)

                advance = random.randint(500, 5000) + (self.player.fame * 10) + (manager_skill * 1000)
                royalty = random.uniform(0.05, 0.20) + (manager_skill * 0.01)
                marketing = random.randint(100, 2000) + (self.player.fame * 5)

                new_contract = Contract(label_name, advance, min(0.5, royalty), marketing)
                self.player.pending_contracts.append(new_contract)

                self.GAME_LOG.add_log_message(f"Agent: 'Great news! I got an offer from {label_name}!'")
                self.GAME_LOG.add_log_message("Check the 'Label Offers' menu on your phone to review the contract.")
            else:
                self.GAME_LOG.add_log_message("Agent: 'Sorry, none of the labels I pitched to are biting right now. Build up your fame and try again later.'")

        elif choice == "plan_tour":
            self.GAME_LOG.add_log_message("Agent: 'Let me look at some routing options for a regional tour...'")
            self._advance_time_with_needs(240) # 4 hours

            if self.player.fame < 100:
                self.GAME_LOG.add_log_message("Agent: 'You don't have enough pull yet for a multi-city tour. We need to build your local fame first.'")
            else:
                self.GAME_LOG.add_log_message("Agent: 'I've mapped out a short 3-stop regional tour!'")
                # Find venues across different cities if possible, or just 3 decent venues
                all_venues = []
                for loc in self.WORLD_MAP.values():
                    all_venues.extend(loc.venues)

                if len(all_venues) >= 3:
                    tour_venues = random.sample(all_venues, 3)
                    start_time = current_game_time.copy()
                    start_time.add_days(2) # Start in 2 days

                    for i, venue in enumerate(tour_venues):
                        gig_time = start_time.copy()
                        gig_time.add_days(i * 2) # Every 2 days
                        gig_time.hour = 20

                        booked_event = Event(
                            name=f"Tour Gig @ {venue.name}",
                            event_type="CLUB_GIG",
                            location=venue,
                        )
                        venue.add_event(booked_event)

                        gig_end_time = gig_time.copy()
                        gig_end_time.add_hours(2)

                        self.player.schedule.add_event(
                            gig_time,
                            gig_end_time,
                            f"Tour: {venue.name}",
                            "Gig",
                            {"event_id": booked_event.event_id, "venue_id": venue.venue_id, "destination_id": venue.venue_id, "requires_presence": True},
                        )
                    self.GAME_LOG.add_log_message("Check your Schedule for the new tour dates!")
                else:
                    self.GAME_LOG.add_log_message("Agent: 'Actually, I couldn't find enough suitable venues to string together a tour right now.'")

    def handle_web_menu(self):
        if self.web_menu_state == "main":
            web_options = {
                "view_charts": "View Music Charts",
                "marketing": "Digital Marketing Portal",
                "back": "Back to Phone"
            }
            choice = self.ui.present_choices(web_options, "Web Browser")
            if choice == "back":
                self.game_state = "phone"
                self.phone_menu_state = "main"
            else:
                self.web_menu_state = choice

        elif self.web_menu_state == "view_charts":
            chart_options = {str(i): chart.name for i, chart in enumerate(self.ACTIVE_CHARTS)}
            chart_options["back"] = "Back"

            choice = self.ui.present_choices(chart_options, "Which chart to view?")
            if choice == "back":
                self.web_menu_state = "main"
            else:
                chart_to_view = self.ACTIVE_CHARTS[int(choice)]
                self.text_to_view = str(chart_to_view)
                self.game_state = "view_text"
                self.web_menu_state = "main"

        elif self.web_menu_state == "marketing":
            # Select Campaign
            camp_opts = {k: f"{v['name']} (${v['cost']})" for k, v in CAMPAIGN_TYPES.items()}
            camp_opts["back"] = "Back"

            choice = self.ui.present_choices(camp_opts, "Select Marketing Campaign:")

            if choice == "back":
                self.web_menu_state = "main"
            else:
                self.marketing_campaign_type = choice
                self.web_menu_state = "marketing_select_song"

        elif self.web_menu_state == "marketing_select_song":
            # Select Song (Released only)
            released = [s for s in self.player.songs_written if s.is_released]
            if not released:
                self.GAME_LOG.add_log_message("No released songs to market.")
                self.web_menu_state = "marketing"
                return

            song_opts = {str(i): s.title for i, s in enumerate(released)}
            song_opts["back"] = "Back"

            choice = self.ui.present_choices(song_opts, "Select Song to Market:")

            if choice == "back":
                self.web_menu_state = "marketing"
            else:
                song = released[int(choice)]
                cost = CAMPAIGN_TYPES[self.marketing_campaign_type]['cost']

                if self.player.money >= cost:
                    self.player.money -= cost
                    outcome = self._resolve_marketing_outcome(self.marketing_campaign_type, song)
                    song.buzz_score = max(0, song.buzz_score + outcome["data"]["buzz"])
                    self.player.fame = max(0, self.player.fame + outcome["data"]["fame"])
                    self.GAME_LOG.add_log_message(outcome["data"]["message"] + outcome.get("message_suffix", ""))
                    self.GAME_LOG.add_log_message(
                        f"Roll {outcome['roll']} -> {outcome['total']}: '{song.title}' now has {song.buzz_score:.0f} buzz and you sit at {self.player.fame} fame."
                    )
                else:
                    self.GAME_LOG.add_log_message(f"You cannot afford this campaign. Cost: ${cost}, Cash: ${self.player.money}.")

                self.web_menu_state = "main"


    def handle_opportunity(self, opp_id):
        opp_data = self.OPPORTUNITY_CATALOG.get(opp_id)
        if not opp_data:
            return

        self.GAME_LOG.add_log_message(f"You pursue the opportunity: {opp_data['name']}")

        if opp_id == "radio_interview_local":
            # Time cost: 2 hours
            self._advance_time_with_needs(120)

            self.GAME_LOG.add_log_message("You head down to the K-ROK radio station...")
            outcome = self._resolve_media_outcome("radio")
            self.player.fame += outcome["data"]["fame"]
            best_song = max((song for song in self.player.songs_written if song.is_released), key=lambda song: song.buzz_score + song.recording_quality, default=None)
            if best_song:
                best_song.buzz_score += outcome["data"]["buzz"]
            self.GAME_LOG.add_log_message(
                f"{outcome['data']['message']} (Roll {outcome['roll']} -> {outcome['total']}, fame: {self.player.fame})"
            )
            self._maybe_trigger_npc_cosign(best_song, "the radio interview")

            self.player.active_opportunities[opp_id]['status'] = "completed"

        elif opp_id == "music_blog_feature":
            # Time cost: 1 hour
            self._advance_time_with_needs(60)
            outcome = self._resolve_media_outcome("blog")
            self.player.fame += outcome["data"]["fame"]
            best_song = max((song for song in self.player.songs_written if song.is_released), key=lambda song: song.buzz_score + song.recording_quality, default=None)
            if best_song:
                best_song.buzz_score += outcome["data"]["buzz"]
            self.GAME_LOG.add_log_message(
                f"{outcome['data']['message']} (Roll {outcome['roll']} -> {outcome['total']}, fame: {self.player.fame})"
            )
            self._maybe_trigger_npc_cosign(best_song, "the blog feature")
            self.player.active_opportunities[opp_id]['status'] = "completed"

        elif opp_id.startswith('guest_feature_'):
            npc_id = opp_id.replace('guest_feature_', '')
            npc = self.NPC_REGISTRY.get(npc_id)
            if npc:
                self.GAME_LOG.add_log_message(f"You agree to play on {npc.name}'s new song.")
                self._advance_time_with_needs(240) # 4 hours studio time

                # Simple skill check based on player's best skill
                primary_skill = max(self.player.skills, key=self.player.skills.get)
                skill_val = self.player.skills.get(primary_skill, 0)

                if skill_val > 10:
                    money_gain = 250
                    fame_gain = 20
                    self.GAME_LOG.add_log_message(f"You nailed your part! {npc.name} is impressed. (+${money_gain}, +{fame_gain} Fame)")
                else:
                    money_gain = 100
                    fame_gain = 10
                    self.GAME_LOG.add_log_message(f"You did a decent job on the track. (+${money_gain}, +{fame_gain} Fame)")

                self.player.money += money_gain
                self.player.fame += fame_gain
                self.player.active_opportunities[opp_id]['status'] = "completed"
        elif opp_id.startswith('tour_offer_'):
            tour_id = opp_id.replace('tour_offer_', '')
            self.schedule_tour(tour_id)
            self.player.active_opportunities[opp_id]['status'] = "completed"
            self.ui.draw_schedule_screen(self.player)
        elif opp_id == "autograph_signing":
            self._advance_time_with_needs(120) # 2 hours
            fame_gain = 10 + random.randint(0, 10)
            money_gain = 50 + random.randint(0, 50)
            self.player.fame += fame_gain
            self.player.money += money_gain
            self.GAME_LOG.add_log_message(f"The autograph signing was a success! (+${money_gain}, +{fame_gain} Fame)")
            self.player.active_opportunities[opp_id]['status'] = "completed"
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.phone_menu_state = "main"

    def handle_music_menu(self):
        if self.music_menu_state == "main":
            music_menu_opts = {
                "view_songs": "View Your Songs",
                "release_song": "Release a Song (Single)",
                "create_album": "Assemble Album (Needs 3+ Songs)",
                "back": "Back to Phone"
            }
            choice = self.ui.present_choices(music_menu_opts, "Music")
            if choice == "back":
                self.game_state = "phone"
                self.phone_menu_state = "main"
            else:
                self.music_menu_state = choice

        elif self.music_menu_state == "view_songs":
            if not self.player.songs_written:
                self.GAME_LOG.add_log_message("You haven't written any songs yet.")
                self.music_menu_state = "main"
                return

            song_options = {str(i): str(s) for i, s in enumerate(self.player.songs_written)}
            song_options["back"] = "Back"

            choice = self.ui.present_choices(song_options, "Your Songs")
            if choice == "back":
                self.music_menu_state = "main"

        elif self.music_menu_state == "release_song":
            releasable_songs = [s for s in self.player.songs_written if s.is_recorded and not s.is_released]

            if not releasable_songs:
                self.GAME_LOG.add_log_message("You have no recorded songs ready for release.")
                self.music_menu_state = "main"
                return

            song_options = {str(i): f"'{s.title}' (Rec Q: {s.recording_quality:.2f})" for i, s in enumerate(releasable_songs)}
            song_options["back"] = "Cancel"

            choice = self.ui.present_choices(song_options, "Which song would you like to self-release?")

            if choice == "back":
                self.music_menu_state = "main"
            else:
                selected_song = releasable_songs[int(choice)]
                release_cost = 15
                if self.player.money < release_cost:
                    self.GAME_LOG.add_log_message(f"You need ${release_cost} to distribute a single.")
                    self.music_menu_state = "main"
                    return

                self.player.money -= release_cost
                selected_song.mark_as_released(current_game_time)
                self.GAME_LOG.add_log_message(f"You've self-released '{selected_song.title}' to the world! (-${release_cost})")
                self.GAME_LOG.add_log_message(f"Current fame: {self.player.fame}. Consider marketing the single from the phone web menu.")
                self.music_menu_state = "main"

        elif self.music_menu_state == "create_album":
            # 1. Select unreleased, recorded songs
            candidates = [s for s in self.player.songs_written if s.is_recorded and not s.is_released]

            if len(candidates) < 3:
                self.GAME_LOG.add_log_message("You need at least 3 recorded, unreleased songs to make an album.")
                self.music_menu_state = "main"
                return

            # Simple selection: Select all? Or picking loop?
            # For simplicity in this text UI, let's auto-select all candidates or offer to select subset?
            # Let's offer a "Select All" or "Pick Top 5" approach.
            # Real simulation would allow checkbox selection.

            opts = {
                "all": f"Use All {len(candidates)} Available Songs",
                "back": "Cancel"
            }
            choice = self.ui.present_choices(opts, "Select tracks for album:")

            if choice == "all":
                album_title = self.ui.get_text_input("Enter Album Title:")
                if not album_title: album_title = "Self-Titled"

                release_cost = 50
                if self.player.money < release_cost:
                    self.GAME_LOG.add_log_message(f"You need ${release_cost} to distribute an album.")
                    self.music_menu_state = "main"
                    return

                new_album = Album(album_title, self.player.name, candidates, release_date=current_game_time)

                # Release Logic
                self.player.money -= release_cost
                self.player.albums_released.append(new_album)
                for s in candidates:
                    s.is_released = True
                    s.release_date = current_game_time

                self.GAME_LOG.add_log_message(f"You released '{new_album.title}'! (-${release_cost})")
                self.GAME_LOG.add_log_message(f"Critics rate it: {int(new_album.quality * 100)}/100")

                # Fame Bonus
                fame_gain = int(new_album.quality * 50) + (len(candidates) * 5)
                self.player.fame += fame_gain
                self.GAME_LOG.add_log_message(f"Your fame increases by {fame_gain}! Total fame: {self.player.fame}")

                self.music_menu_state = "main"
            else:
                self.music_menu_state = "main"

    def handle_contacts_menu(self):
        if self.phone_menu_state == "contacts": # Main contacts list view
            if not self.player.contacts:
                self.GAME_LOG.add_log_message("You have no contacts.")
                self.phone_menu_state = "main"
                return

            contacts_menu_opts = {}
            for npc_id in self.player.contacts:
                npc = self.NPC_REGISTRY.get(npc_id)
                if npc:
                    contacts_menu_opts[npc_id] = f"{npc.name} ({npc.relationship_with_player.name})"
            contacts_menu_opts["back"] = "Back"

            choice = self.ui.present_choices(contacts_menu_opts, "Contacts")
            if choice == "back":
                self.phone_menu_state = "main"
            else:
                self.selected_contact_id = choice
                self.phone_menu_state = "contact_details"

        elif self.phone_menu_state == "contact_details":
            npc = self.NPC_REGISTRY.get(self.selected_contact_id)
            if not npc:
                self.GAME_LOG.add_log_message("Error: Contact not found.")
                self.phone_menu_state = "contacts"
                return

            self.ui.draw_contact_details_screen(npc)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.phone_menu_state = "contacts"

    def handle_character_menu(self):
        if self.character_menu_state == "main":
            character_menu_opts = {
                "career": "Career Overview",
                "stats": "Stats",
                "skills": "Skills",
                "inventory": "Inventory",
                "band": "Band",
                "staff": "Staff (Roadies/Security)",
                "merch": "Merchandise",
                "back": "Back"
            }
            choice = self.ui.present_choices(character_menu_opts, "Character")
            if choice == "back":
                self.game_state = "main_menu"
            else:
                self.character_menu_state = choice
        elif self.character_menu_state == "career":
            self.ui.draw_career_overview(self._get_career_overview_data())
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.character_menu_state = "main"
        elif self.character_menu_state == "stats":
            self.ui.draw_character_stats(self.player)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.character_menu_state = "main"

        elif self.character_menu_state == "staff":
            if not self.player.staff:
                info = "You have no staff."
            else:
                info = "Staff:\n" + "\n".join([str(s) for s in self.player.staff])

            opts = {
                "hire_roadie": "Hire Roadie (Lvl 1, $200/wk)",
                "hire_bodyguard": "Hire Bodyguard (Lvl 1, $300/wk)",
                "fire": "Fire Staff",
                "back": "Back"
            }

            # Simple text display via log or header?
            # Using present_choices header
            choice = self.ui.present_choices(opts, info)

            if choice == "back":
                self.character_menu_state = "main"
            elif choice == "hire_roadie":
                if self.player.money >= 200:
                    new_staff = StaffMember(f"Roadie #{len(self.player.staff)+1}", "Roadie", 200, 1)
                    self.player.staff.append(new_staff)
                    self.GAME_LOG.add_log_message("Hired a Roadie!")
                else:
                    self.GAME_LOG.add_log_message("Cannot afford hiring cost (1st week wage).")
            elif choice == "hire_bodyguard":
                if self.player.money >= 300:
                    new_staff = StaffMember(f"Guard #{len(self.player.staff)+1}", "Bodyguard", 300, 1)
                    self.player.staff.append(new_staff)
                    self.player.has_bodyguard = True # Sync with old boolean
                    self.GAME_LOG.add_log_message("Hired a Bodyguard!")
                else:
                    self.GAME_LOG.add_log_message("Cannot afford hiring cost.")
            elif choice == "fire":
                if not self.player.staff:
                    self.GAME_LOG.add_log_message("No staff to fire.")
                else:
                    fire_opts = {str(i): s.name for i, s in enumerate(self.player.staff)}
                    fire_opts["back"] = "Back"
                    c = self.ui.present_choices(fire_opts, "Fire who?")
                    if c != "back":
                        removed = self.player.staff.pop(int(c))
                        self.GAME_LOG.add_log_message(f"Fired {removed.name}.")
                        if removed.role == "Bodyguard" and not any(s.role == "Bodyguard" for s in self.player.staff):
                            self.player.has_bodyguard = False

        elif self.character_menu_state == "merch":
            if not self.player.merch_stock:
                info = "You have no merch stock."
            else:
                info = "Current Stock:\n" + "\n".join([str(m) for m in self.player.merch_stock])

            opts = {
                "order": "Order New Merch",
                "back": "Back"
            }
            choice = self.ui.present_choices(opts, info)

            if choice == "back":
                self.character_menu_state = "main"
            elif choice == "order":
                self.character_menu_state = "merch_order"

        elif self.character_menu_state == "merch_order":
            order_opts = {k: f"{v['name']} (Cost: ${v['cost']}, Sell: ${v['price']})" for k, v in MERCH_TEMPLATES.items()}
            order_opts["back"] = "Back"

            choice = self.ui.present_choices(order_opts, "Select Merch to Order (Batch of 50):")

            if choice == "back":
                self.character_menu_state = "merch"
            else:
                template = MERCH_TEMPLATES[choice]
                batch_size = 50
                total_cost = template['cost'] * batch_size

                if self.player.money >= total_cost:
                    self.player.money -= total_cost
                    # Check if player already has this item type
                    existing_item = next((m for m in self.player.merch_stock if m.name == template['name']), None)
                    if existing_item:
                        existing_item.stock += batch_size
                    else:
                        new_item = MerchItem(template['name'], template['cost'], template['price'], batch_size)
                        self.player.merch_stock.append(new_item)

                    self.GAME_LOG.add_log_message(f"Ordered {batch_size} {template['name']}s for ${total_cost}.")
                    self.character_menu_state = "merch"
                else:
                    self.GAME_LOG.add_log_message(f"Cannot afford ${total_cost}.")

        elif self.character_menu_state == "band":
            if self.band_menu_state == "main":
                if self.player.band is None:
                    band_options = {"form_band": "Form a new band", "back": "Back"}
                    choice = self.ui.present_choices(band_options, "You are not in a band.")
                    if choice == "back":
                        self.character_menu_state = "main"
                    elif choice == "form_band":
                        self.band_menu_state = "recruit"
                else:
                    self.ui.draw_band_screen(self.player.band)
                    # Show menu options for band management
                    band_opts = {
                        "interact": "Manage Members (Interact/Fire)",
                        "recruit": "Recruit New Member",
                        "back": "Back"
                    }
                    choice = self.ui.present_choices(band_opts, f"Band: {self.player.band.name} (Chem: {self.player.band.chemistry})")

                    if choice == "back":
                        self.character_menu_state = "main"
                    elif choice == "recruit":
                        self.band_menu_state = "recruit"
                    elif choice == "interact":
                        self.band_menu_state = "interact"

            elif self.band_menu_state == "recruit":
                recruitable_npcs = {npc.npc_id: npc for npc in self.NPC_REGISTRY.values() if npc.skills and npc not in (self.player.band.members if self.player.band else [])}
                if not recruitable_npcs:
                    self.GAME_LOG.add_log_message("There's no one suitable to recruit right now.")
                    self.band_menu_state = "main"
                    return

                npc_options = {npc_id: f"{npc.name} ({', '.join(npc.skills.keys())})" for npc_id, npc in recruitable_npcs.items()}
                npc_options["back"] = "Cancel"

                choice = self.ui.present_choices(npc_options, "Who do you want to recruit?")
                if choice == "back":
                    self.band_menu_state = "main"
                else:
                    npc_to_recruit = recruitable_npcs[choice]
                    # Simple fame check for now
                    if self.player.fame >= 100:
                        if self.player.band is None:
                            band_name = self.ui.get_text_input("Enter a name for your new band:")
                            if not band_name:
                                band_name = f"{self.player.name} and the Noise"
                            self.player.band = Band(band_name, self.player)

                        # Set initial wage demand based on fame/skill
                        npc_to_recruit.wage_demand = 50 + int(self._calculate_npc_fame(npc_to_recruit) / 2)

                        self.player.band.add_member(npc_to_recruit)
                        self.GAME_LOG.add_log_message(f"{npc_to_recruit.name} agreed to join your band! (Wage demand: ${npc_to_recruit.wage_demand}/week)")
                    else:
                        self.GAME_LOG.add_log_message(f"{npc_to_recruit.name} isn't interested. Maybe when you're more famous.")
                    self.band_menu_state = "main"

            elif self.band_menu_state == "interact":
                # Interaction menu for band members
                if not self.player.band or len(self.player.band.members) <= 1:
                    self.band_menu_state = "main"
                    return

                member_options = {member.npc_id: f"{member.name} (Sat: {member.satisfaction})" for member in self.player.band.members if member != self.player}
                member_options["back"] = "Back"

                choice = self.ui.present_choices(member_options, "Interact with band member:")

                if choice == "back":
                    self.band_menu_state = "main"
                else:
                     target_member = next((m for m in self.player.band.members if m.npc_id == choice), None)
                     if target_member:
                         action_opts = {
                             "praise": "Praise (+Satisfaction, +Chemistry)",
                             "critique": "Critique (-Satisfaction, +Skill/Quality?)",
                             "bonus": "Give Bonus $100 (+Satisfaction)",
                             "fire": "Fire from Band"
                         }
                         action = self.ui.present_choices(action_opts, f"Action for {target_member.name}:")

                         if action == "praise":
                             target_member.satisfaction = min(100, target_member.satisfaction + 5)
                             self.player.band.update_chemistry(2)
                             self.GAME_LOG.add_log_message(f"You praised {target_member.name}. They seem happy.")
                         elif action == "critique":
                             target_member.satisfaction = max(0, target_member.satisfaction - 5)
                             self.player.band.update_chemistry(-1)
                             self.GAME_LOG.add_log_message(f"You critiqued {target_member.name}. It was harsh but necessary.")
                         elif action == "bonus":
                             if self.player.money >= 100:
                                 self.player.money -= 100
                                 target_member.satisfaction = min(100, target_member.satisfaction + 15)
                                 self.GAME_LOG.add_log_message(f"You gave {target_member.name} a bonus. They love it!")
                             else:
                                 self.GAME_LOG.add_log_message("You can't afford a bonus.")
                         elif action == "fire":
                             self.player.band.members.remove(target_member)
                             self.player.band.recalculate_skills()
                             target_member.satisfaction = 0
                             self.GAME_LOG.add_log_message(f"You fired {target_member.name}. The atmosphere is awkward.")
                             self.band_menu_state = "main"
        elif self.character_menu_state == "skills":
            self.ui.draw_skills_screen(self.player)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.character_menu_state = "main"
        elif self.character_menu_state == "inventory":
            # Check if at home
            at_home = self.player.current_poi and self.PLAYER_HOME_POI_ID_GLOBAL and self.player.current_poi.poi_id == self.PLAYER_HOME_POI_ID_GLOBAL

            opts = {
                "inspect": "Inspect/Use Items",
                "storage": "Home Storage (Stash/Retrieve)" if at_home and self.player.has_home else "Home Storage (Need a home)",
                "back": "Back"
            }

            choice = self.ui.present_choices(opts, "Inventory Management")

            if choice == "back":
                self.character_menu_state = "main"
            elif choice == "inspect":
                self.character_menu_state = "inventory_inspect"
            elif choice == "storage":
                if at_home and self.player.has_home:
                    self.character_menu_state = "inventory_storage"
                else:
                    self.GAME_LOG.add_log_message("You need access to your home to use storage.")

        elif self.character_menu_state == "inventory_inspect":
            inventory_options = {str(i): f"{item.name} ({item.gear_type})" for i, item in enumerate(self.player.gear_inventory)}
            inventory_options["back"] = "Back"

            choice = self.ui.present_choices(inventory_options, "Select item to use/inspect:")

            if choice == "back":
                self.character_menu_state = "inventory"
            else:
                selected_item = self.player.gear_inventory[int(choice)]
                if selected_item.gear_type == "FOOD":
                    self.GAME_LOG.add_log_message(f"Using {selected_item.name}...")
                    success, msg = self.player.consume_item(selected_item)
                    self.GAME_LOG.add_log_message(msg)
                else:
                    self.GAME_LOG.add_log_message(f"You inspect {selected_item.name}. It looks fine.")

        elif self.character_menu_state == "inventory_storage":
            # Show stash/retrieve options
            mode_opts = {"stash": "Stash Item (to Home)", "retrieve": "Retrieve Item (from Home)", "auto_pack": "Auto-Pack (Requires Roadie)", "back": "Back"}
            mode = self.ui.present_choices(mode_opts, "Storage")

            if mode == "back":
                self.character_menu_state = "inventory"
            elif mode == "stash":
                if not self.player.gear_inventory:
                    self.GAME_LOG.add_log_message("Nothing to stash.")
                else:
                    inv_opts = {str(i): item.name for i, item in enumerate(self.player.gear_inventory)}
                    inv_opts["back"] = "Back"
                    c = self.ui.present_choices(inv_opts, "Select item to stash:")
                    if c != "back":
                        item = self.player.gear_inventory[int(c)]
                        success, msg = self.player.stash_item(item)
                        self.GAME_LOG.add_log_message(msg)
            elif mode == "retrieve":
                if not self.player.home_storage:
                    self.GAME_LOG.add_log_message("Storage is empty.")
                else:
                    store_opts = {str(i): item.name for i, item in enumerate(self.player.home_storage)}
                    store_opts["back"] = "Back"
                    c = self.ui.present_choices(store_opts, "Select item to retrieve:")
                    if c != "back":
                        item = self.player.home_storage[int(c)]
                        success, msg = self.player.retrieve_item(item)
                        self.GAME_LOG.add_log_message(msg)
            elif mode == "auto_pack":
                msg = self.player.auto_pack()
                self.GAME_LOG.add_log_message(msg)

    def save_game(self, filename="savegame.dat"):
        save_data = {
            'player': self.player,
            'game_time': current_game_time,
            'world_map': self.WORLD_MAP,
            'npc_registry': self.NPC_REGISTRY,
            'active_charts': self.ACTIVE_CHARTS,
            'last_chart_update_day': self.LAST_CHART_UPDATE_DAY,
        }
        try:
            with open(filename, 'wb') as f:
                pickle.dump(save_data, f)
            self.GAME_LOG.add_log_message("Game saved successfully.")
        except Exception as e:
            self.GAME_LOG.add_log_message(f"Error saving game: {e}")

    def load_game(self, filename="savegame.dat"):
        if not os.path.exists(filename):
            self.GAME_LOG.add_log_message("No save file found.")
            return

        try:
            with open(filename, 'rb') as f:
                save_data = pickle.load(f)

            self.player = save_data['player']
            self.WORLD_MAP = save_data['world_map']
            self.NPC_REGISTRY = save_data['npc_registry']
            self.ACTIVE_CHARTS = save_data['active_charts']
            self.LAST_CHART_UPDATE_DAY = save_data['last_chart_update_day']

            # Restore game time
            loaded_time = save_data['game_time']
            current_game_time.year = loaded_time.year
            current_game_time.month = loaded_time.month
            current_game_time.day = loaded_time.day
            current_game_time.hour = loaded_time.hour
            current_game_time.minute = loaded_time.minute

            # Re-initialize transient data
            self._build_poi_venue_id_map()
            self._normalize_opportunity_state()
            self._reset_transient_runtime_state()
            self.game_state = "main_menu"

            self.GAME_LOG.add_log_message("Game loaded successfully.")

        except Exception as e:
            self.GAME_LOG.add_log_message(f"Error loading game: {e}")

    def handle_system_menu(self):
        system_menu_opts = {
            "save": "Save",
            "load": "Load",
            "back": "Back"
        }
        choice = self.ui.present_choices(system_menu_opts, "System")
        if choice == "back":
            self.game_state = "main_menu"
        elif choice == "save":
            self.save_game()
            self.game_state = "main_menu" # Go back to main menu after saving
        elif choice == "load":
            self.load_game()
            self.game_state = "main_menu" # Go back to main menu after loading

    def handle_text_viewer(self):
        self.ui.draw_text_viewer(self.text_to_view)
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                    self.game_state = "phone" # Go back to the phone menu
                    self.phone_menu_state = "web"
                    self.web_menu_state = "main"

    def handle_travel_active_state(self):
        tm = self.travel_manager
        if not tm:
            self.game_state = "main_menu"
            return

        if not self.transit_session:
            self.transit_session = self.transit_layer.start_session(tm)

        actions = self.transit_layer.available_actions(self, tm)
        if hasattr(self.ui, "present_travel_choices"):
            choice = self.ui.present_travel_choices(actions, self._build_travel_ui_data(tm))
        else:
            pct = tm.get_progress_percent()
            bar_length = 20
            filled = int(pct * bar_length)
            bar = "[" + "="*filled + " "*(bar_length-filled) + "]"
            status_text = f"Traveling to {tm.destination.name} ({tm.transport_mode.upper()})\n"
            status_text += f"Progress: {bar} {int(pct*100)}%\n"
            status_text += f"Distance: {tm.distance_covered:.1f}/{tm.distance_total:.1f} km"
            choice = self.ui.present_choices(actions, status_text)

        result = self.transit_layer.execute_chunk(self, tm, self.transit_session, choice)

        for feed_item in result.get("feed", []):
            self.GAME_LOG.add_log_message(f"Transit feed: {feed_item['text']}")

        for message in result.get("logs", []):
            self.GAME_LOG.add_log_message(message)

        self.GAME_LOG.add_log_message(
            f"Transit update: {result.get('remaining_minutes', 0)}m remaining after {self.transit_session.chunks_completed} chunk(s)."
        )

        if result.get("arrived"):
            self.player.current_location = tm.destination
            self.player.current_poi = self._get_arrival_poi(tm.destination, tm.transport_mode)
            arrival_name = self.player.current_poi.name if self.player.current_poi else tm.destination.name
            self.GAME_LOG.add_log_message(
                f"Arrived at {arrival_name} in {tm.destination.name}. "
                f"Arrival state: Energy {self.player.energy}, Stress {self.player.stress}, Hunger {self.player.hunger}."
            )
            self.travel_manager = None
            self.transit_session = None
            self.game_state = "main_menu"

    def handle_performance_scene(self):
        # 1. Selection Phase
        if self.performance_stage == "choose_song":
            if not self.player.songs_written:
                self.GAME_LOG.add_log_message("You have no songs to perform!")
                self.game_state = "explore"
                return

            songs_required = getattr(self.active_performance, "songs_required_count", 1)
            if len(self.player.songs_written) < songs_required:
                self.GAME_LOG.add_log_message(
                    f"You need at least {songs_required} songs to play this event."
                )
                self.game_state = "explore"
                self.active_performance = None
                self.performance_stage = None
                return

            song_options = {str(i): f"'{s.title}' (Q: {s.song_quality:.2f})" for i, s in enumerate(self.player.songs_written)}
            song_options["back"] = "Cancel"
            title = "Choose your opener:" if songs_required > 1 else "Choose a song to perform:"
            choice = self.ui.present_choices(song_options, title)

            if choice == "back":
                self.game_state = "explore"
                self.active_performance = None
                self.performance_stage = None
            else:
                selected_song = self.player.songs_written[int(choice)]
                remaining_songs = [song for song in self.player.songs_written if song.song_id != selected_song.song_id]
                remaining_songs.sort(key=lambda song: song.song_quality, reverse=True)
                self.performance_setlist = [selected_song] + remaining_songs[: max(0, songs_required - 1)]
                self.active_performance.song_to_perform = selected_song
                # Initialize Manager
                self.performance_manager = PerformanceManager(self, self.active_performance, selected_song, self.ui)
                self.performance_manager.state = "player_input" # Start game
                self.performance_stage = "playing"

        # 2. Playing Phase (Delegated to Manager)
        elif self.performance_stage == "playing":
            if self.performance_manager.state == "player_input":
                # Present choices via main loop's UI helper
                actions = {
                    "safe": "Play it Safe (Low Risk)",
                    "hype": "Hype the Crowd (Med Risk, High Hype)",
                    "solo": "Improvise Solo (High Risk, High Reward)"
                }
                self.performance_manager.draw_screen()
                choice = self.ui.present_choices(actions, f"Action for {self.performance_manager.get_current_section()}:")
                self.performance_manager.handle_input(choice)

            elif self.performance_manager.state == "resolution":
                self.performance_manager.draw_screen()
                # Wait for user acknowledgment
                # We can use a simple wait loop or a present_choice with just "Continue"
                self.ui.present_choices({"ok": "Continue"}, "Result")
                self.performance_manager.handle_input("ok") # Advance state

            elif self.performance_manager.state == "summary":
                self.performance_manager.draw_screen()
                self.ui.present_choices({"finish": "Finish Show"}, "Performance Complete")
                self.performance_stage = "finish"

        # 3. Completion Phase
        elif self.performance_stage == "finish":
            # Calculate Rewards based on final hype
            final_hype = self.performance_manager.crowd_hype
            reward_outcome = self._resolve_gig_rewards(self.active_performance, final_hype)
            money_gain = reward_outcome["money_gain"]
            fame_gain = reward_outcome["fame_gain"]

            self.player.money += money_gain
            self.player.fame += fame_gain

            self.GAME_LOG.add_log_message(f"Show over! The crowd hype reached {final_hype}/100.")
            self.GAME_LOG.add_log_message(
                f"{reward_outcome['data']['message']} (Roll {reward_outcome['roll']} -> {reward_outcome['total']})"
            )
            self.GAME_LOG.add_log_message(f"Ticket Sales: +${money_gain} | Fame: +{fame_gain}")
            if self.performance_setlist:
                setlist_titles = ", ".join(song.title for song in self.performance_setlist)
                self.GAME_LOG.add_log_message(f"Setlist: {setlist_titles}")
                strongest_song = max(self.performance_setlist, key=lambda song: song.song_quality + song.recording_quality)
                strongest_song.buzz_score += max(2, int(final_hype / 8))
                self._maybe_trigger_npc_cosign(strongest_song, f"the show at {self.active_performance.location.name}")

            # Merch Sales Logic
            if self.player.merch_stock:
                total_merch_sales = 0
                for item in self.player.merch_stock:
                    if item.stock > 0:
                        # Buyers based on hype
                        potential_buyers = int(final_hype / 2) # e.g. 100 hype -> 50 buyers max
                        # Buying chance based on fame?
                        actual_sales = 0
                        for _ in range(potential_buyers):
                            if item.stock > 0 and random.random() < 0.2: # 20% buy rate
                                item.stock -= 1
                                total_merch_sales += item.sale_price
                                actual_sales += 1

                        if actual_sales > 0:
                            self.GAME_LOG.add_log_message(f"Sold {actual_sales} {item.name}s.")

                if total_merch_sales > 0:
                    self.player.money += total_merch_sales
                    self.GAME_LOG.add_log_message(f"Merch Income: +${total_merch_sales}")

            # Cleanup
            self.performance_manager = None
            self.active_performance = None
            self.performance_setlist = []
            self.performance_stage = None
            self.game_state = "explore"
