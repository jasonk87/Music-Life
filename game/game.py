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
from game.chart import Chart
from game.feedback_generator import generate_feedback_for_song, SOURCES, generate_feedback_for_album
from game.sound import SoundManager
from game.ascii_art import ART

class Game:
    def __init__(self, ui):
        self.ui = ui
        self.sound_manager = SoundManager()
        self.player = None
        self.running = True
        self.game_state = "main_menu"
        self.character_menu_state = "main"
        self.explore_menu_state = "location"
        self.phone_menu_state = "main"
        self.music_menu_state = "main"
        self.web_menu_state = "main"
        self.text_to_view = ""
        self.active_performance = None
        self.performance_log = []
        self.performance_stage = None
        self.band_menu_state = "main"
        self.selected_contact_id = None
        self.selected_poi = None
        self.selected_npc = None
        self.conversation_history = []
        self.player_input = ""
        self.songwriting_stage = None
        self.song_in_progress = {}
        self.SONG_GENRES = ["Rock", "Pop", "Folk", "Indie", "Electronic", "Blues"]
        self.OPPORTUNITY_CATALOG = {
            "radio_interview_local": {
                "name": "Local Radio Interview",
                "trigger": lambda p, g: p.fame >= 50 and any(s.is_released and s.song_quality >= 0.6 for s in p.songs_written),
                "action_text": "Call K-ROK Radio for interview",
                "type": "phone"
            },
            "music_blog_feature": {
                "name": "IndiePulse Music Blog Feature",
                "trigger": lambda p, g: p.fame >= 75 and any(s.is_released for s in p.songs_written),
                "action_text": "Respond to email from IndiePulse blog",
                "type": "phone"
            },
            "battle_of_the_bands_local": {
                "name": "Hometown Battle of the Bands",
                "trigger": lambda p, g: p.fame >= 100 and len(p.songs_written) >= 2,
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
                venue = Venue(venue_id=venue_data["venue_id"], name=venue_data["name"], description=venue_data["description"],
                            venue_type=venue_data["venue_type"], category=venue_data["category"],
                            capacity=venue_data["capacity"], prestige=venue_data["prestige"],
                            parent_location_id=location_obj.name, **props)
                if owner_npc_id_temp_venue: venue.owner_npc_id = owner_npc_id_temp_venue
                venue.events_hosted_ids_from_json = list(venue_data.get("events_hosted_ids", []))
                venue.booking_fee = booking_fee_prop; venue.allows_player_booking = allows_player_booking_prop
                if not venue.interaction_options:
                    venue.interaction_options = ["View upcoming events", "Talk to the owner"]
                location_obj.add_venue(venue)

            for conn_data in city_def_data.get("intra_city_poi_connections", []):
                poi_ids_tuple = tuple(sorted(conn_data["pois"]))
                if len(poi_ids_tuple) == 2: location_obj.intra_city_poi_connections[frozenset(poi_ids_tuple)] = {k: v for k, v in conn_data.items() if k != "pois"}

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
                if target_loc_obj: curr_loc_obj.add_travel_connection(target_loc_obj.name, cost=conn_data["cost"], time_hours=conn_data["time_hours"])
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
        player_name = "Player" # Placeholder, will need a pygame input box
        self.player = Player(player_name)
        hometown_loc = self.WORLD_MAP.get("Your Hometown")
        player_home_obj = self.get_poi_or_venue_by_id(self.PLAYER_HOME_POI_ID_GLOBAL) if self.PLAYER_HOME_POI_ID_GLOBAL else None
        if hometown_loc and player_home_obj:
            self.player.current_location = hometown_loc
            self.player.current_poi = player_home_obj
        else:
            print("Error setting start home.")
            self.running = False

        self.update_npc_locations(current_game_time)
        self.process_time_based_player_needs(self.player, 0)
        if GEAR_CATALOG.get("worn_acoustic_guitar"): self.player.add_gear(GEAR_CATALOG["worn_acoustic_guitar"])
        if GEAR_CATALOG.get("guitar_picks_assorted"): self.player.add_gear(GEAR_CATALOG["guitar_picks_assorted"])

        self.LAST_CHART_UPDATE_DAY = current_game_time.day

    def check_for_new_opportunities(self):
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
                # Small chance per day for a friend to offer a feature
                if random.random() < 0.05: # 5% chance
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
                            self.player.active_opportunities[opp_id] = "available"
                            self.GAME_LOG.add_log_message(f"Your manager found a potential tour for you: '{tour['name']}'!")
                            self.GAME_LOG.add_log_message("Check your phone for the offer.")
                            break # Only offer one tour at a time

    def check_for_scheduled_events(self):
        # We need to iterate over a copy, as we might remove items
        for event in self.player.schedule.scheduled_items[:]:
            if event.start_time <= current_game_time:
                if event.category == "LABEL_RESPONSE":
                    self.handle_label_response(event)
                    self.player.schedule.scheduled_items.remove(event)

    def handle_label_response(self, event):
        label_id = event.details.get('label_id')
        song_id = event.details.get('song_id')

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

            venue = random.choice(city_venues)

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

            self.player.schedule.add_event(gig_start_time, gig_end_time, gig_event.name, "Gig (Tour)", {'event_id': gig_event.event_id})
            self.GAME_LOG.add_log_message(f"Booked: {gig_event.name} on {gig_start_time.get_time_string_for_schedule()}")

            last_gig_date = gig_date

        label = self.get_poi_or_venue_by_id(label_id)
        song = next((s for s in self.player.songs_written if s.song_id == song_id), None)

        if not label or not song:
            return # Should not happen

        self.GAME_LOG.add_log_message(f"You've received a response from {label.name} about '{song.title}'.")

        # Evaluation logic
        score = (song.song_quality * 50) + (song.recording_quality * 30) + (self.player.fame / 10)

        if score > 70: # Threshold for an offer
            self.GAME_LOG.add_log_message("They're interested! They've sent over a contract offer.")

            # Generate contract based on score
            advance = int(score * 10)
            royalty = min(0.25, 0.05 + (score / 1000.0)) # 5% base, up to 25%
            marketing = int(score * 5)

            contract = Contract(
                label_name=label.name,
                advance_money=advance,
                royalty_rate=royalty,
                marketing_budget_per_release=marketing
            )
            self.player.pending_contracts.append(contract)
        else:
            self.GAME_LOG.add_log_message("Unfortunately, they've decided to pass at this time.")


    def run(self):
        if not self.setup_world():
            print("World setup failed. Check log.")
            return

        self.GAME_LOG.add_log_message("Welcome to Music-Life Sim!")
        self.GAME_LOG.add_log_message("Ollama for NPCs: ensure it's running & model pulled (e.g., llama3).")

        self.initialize_player()

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            if (current_game_time.day % 7 == 1) and (current_game_time.day != self.LAST_CHART_UPDATE_DAY):
                self.GAME_LOG.add_log_message("--- Weekly World Update ---")

                # NPCs progress in their careers
                self.update_npc_careers()

                # Gather all released songs in the world
                all_released_songs = list(self.player.songs_written)
                for npc in self.NPC_REGISTRY.values():
                    all_released_songs.extend(npc.songs_written)

                # Update charts with all songs
                total_fame_gain = 0
                total_money_gain = 0
                all_feedback_events = []
                for chart in self.ACTIVE_CHARTS:
                    feedback_events = chart.update_weekly(all_released_songs, self.player, current_game_time)
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


            if current_game_time.day != self.last_opportunity_check_day:
                self.check_for_new_opportunities()
                self.last_opportunity_check_day = current_game_time.day

            self.check_for_scheduled_events()

            self.ui.clear_screen()
            self.ui.draw_hud(get_current_time_str(date_only=True), str(self.player.money), str(self.player.hair_length), str(self.player.beard_length))
            self.ui.draw_log()

            if self.game_state == "main_menu":
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

            self.ui.update_display()

        pygame.quit()

    def handle_main_menu(self):
        main_menu_opts = {
            "explore": "Explore",
            "travel": "Travel",
            "phone": "Phone",
            "character": "Character",
            "system": "System",
            "quit": "Quit"
        }

        choice = self.ui.present_choices(main_menu_opts, f"What would {self.player.name} like to do?")

        if choice == "quit":
            self.running = False
        else:
            self.game_state = choice

    def handle_explore_menu(self):
        if self.explore_menu_state == "location":
            location = self.player.current_location
            pois = location.points_of_interest + location.venues
            poi_options = {poi.poi_id if hasattr(poi, 'poi_id') else poi.venue_id: poi.name for poi in pois}
            poi_options["back"] = "Back"

            choice = self.ui.present_choices(poi_options, f"Explore {location.name}")
            if choice == "back":
                self.game_state = "main_menu"
            else:
                self.selected_poi = self.get_poi_or_venue_by_id(choice)
                self.explore_menu_state = "poi"
        elif self.explore_menu_state == "poi":
            if self.selected_poi:
                # Draw ASCII art for the location
                poi_id = self.selected_poi.poi_id if hasattr(self.selected_poi, 'poi_id') else self.selected_poi.venue_id
                art_to_display = ART.get(poi_id, ART['default'])
                self.ui.draw_ascii_art(art_to_display, 450, 120)

                interaction_options = {str(i): option for i, option in enumerate(self.selected_poi.get_interactions())}

                # Add dynamic opportunities for this POI
                for opp_id, opp_details in self.player.active_opportunities.items():
                    if opp_details["status"] == "available":
                        opp_data = self.OPPORTUNITY_CATALOG.get(opp_id)
                        if opp_data and opp_data.get("type") == "poi_interaction" and opp_details.get("poi_id") == poi_id:
                             interaction_options[opp_id] = opp_data["action_text"]

                interaction_options["back"] = "Back"

                choice = self.ui.present_choices(interaction_options, f"Interact with {self.selected_poi.name}")
                if choice == "back":
                    self.explore_menu_state = "location"
                    self.selected_poi = None
                else:
                    self.handle_interaction(interaction_options[choice])
                    if self.explore_menu_state not in ["shop", "write_song_menu", "talk", "dialogue", "dealership"]:
                        self.explore_menu_state = "location"
                        self.selected_poi = None
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
                            self.GAME_LOG.add_log_message(f"You can't afford the {vehicle_to_buy.name}.")
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
                            self.GAME_LOG.add_log_message(f"You can't afford {item_to_buy.name}.")
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
                confirm_options = {
                    "yes": f"Start writing '{title}' ({genre}) (Will take ~8 hours)",
                    "no": "Cancel"
                }
                choice = self.ui.present_choices(confirm_options, "Ready to start writing?")
                if choice == "yes":
                    self.songwriting_stage = "writing_components"
                    # This will fall through to the next stage in the same frame
                else:
                    self.GAME_LOG.add_log_message("Songwriting cancelled.")
                    self.explore_menu_state = "poi"
                    self.songwriting_stage = None

            if self.songwriting_stage == "writing_components":
                # This is a non-interactive stage, so we do the work and then change state.
                self.GAME_LOG.add_log_message("You spend a long day writing...")

                # Lyrics (2 hours)
                lyrical_depth = self._calculate_song_component_quality('songwriting')
                self.song_in_progress['lyrical_depth'] = lyrical_depth
                advance_game_time(120)
                self.GAME_LOG.add_log_message(f"The lyrics are coming together (Quality: {lyrical_depth:.2f})")

                # Melody (3 hours)
                catchiness = self._calculate_song_component_quality('songwriting', 'guitar')
                self.song_in_progress['catchiness'] = catchiness
                advance_game_time(180)
                self.GAME_LOG.add_log_message(f"You've got a catchy melody! (Quality: {catchiness:.2f})")

                # Arrangement / Complexity (3 hours)
                music_complexity = self._calculate_song_component_quality('guitar', 'songwriting', weight=0.7)
                self.song_in_progress['music_complexity'] = music_complexity
                originality = self._calculate_song_component_quality('songwriting') # Originality is based on songwriting
                self.song_in_progress['originality'] = originality
                advance_game_time(180)
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
                author = self.player.name

                originality=self.song_in_progress.get('originality', 0.5)
                catchiness=self.song_in_progress.get('catchiness', 0.5)
                lyrical_depth=self.song_in_progress.get('lyrical_depth', 0.5)
                music_complexity=self.song_in_progress.get('music_complexity', 0.5)

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
                    music_complexity=music_complexity
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
                advance_game_time(2 * 24 * 60) # 2 days

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
                        self.GAME_LOG.add_log_message("You can't afford to mail the demo.")
                        self.explore_menu_state = "poi"
                        return

                    self.player.money -= cost
                    advance_game_time(60) # 1 hour to prepare and mail

                    # Schedule the response
                    response_time = current_game_time.copy()
                    response_time.add_days(3)
                    self.player.schedule.add_event(
                        start_time=response_time,
                        end_time=response_time,
                        description=f"Response from {self.selected_poi.name} re: '{selected_song.title}'",
                        category="LABEL_RESPONSE",
                        details={'song_id': selected_song.song_id, 'label_id': self.selected_poi.poi_id}
                    )
                    self.GAME_LOG.add_log_message(f"You mail a demo of '{selected_song.title}' to {self.selected_poi.name}.")
                    self.GAME_LOG.add_log_message("You expect to hear back in a few days.")
                    self.explore_menu_state = "poi"
            else:
                self.explore_menu_state = "poi"
        elif self.explore_menu_state == "record_song":
            if self.selected_poi and self.selected_poi.category == "STUDIO_RECORDING":
                unrecorded_songs = [s for s in self.player.songs_written if not s.is_recorded]
                if not unrecorded_songs:
                    self.GAME_LOG.add_log_message("You have no unrecorded songs to record.")
                    self.explore_menu_state = "poi"
                    return

                song_options = {str(i): f"'{s.title}' (Quality: {s.song_quality:.2f})" for i, s in enumerate(unrecorded_songs)}
                song_options["back"] = "Cancel"

                choice = self.ui.present_choices(song_options, "Which song would you like to record?")

                if choice == "back":
                    self.explore_menu_state = "poi"
                else:
                    selected_song = unrecorded_songs[int(choice)]
                    studio_quality = self.selected_poi.studio_quality
                    # Let's say a session is 4 hours
                    session_cost = self.selected_poi.hourly_rate * 4

                    if self.player.money < session_cost:
                        self.GAME_LOG.add_log_message(f"You can't afford the ${session_cost} session fee.")
                        self.explore_menu_state = "poi"
                        return

                    self.player.money -= session_cost
                    advance_game_time(4 * 60)
                    self.GAME_LOG.add_log_message(f"You pay ${session_cost} and spend 4 hours in the studio.")

                    # Calculate recording quality
                    # Base is a weighted average of song quality and studio quality
                    base_quality = (selected_song.song_quality * 0.6) + (studio_quality * 0.4)
                    # Skill adds a bonus. Let's use 'guitar' skill for now.
                    skill_bonus = self.player.skills.get('guitar', 0) / 100.0 # e.g., 10 skill = 0.1 bonus

                    final_quality = min(1.0, base_quality + skill_bonus)

                    selected_song.mark_as_recorded(final_quality)
                    self.GAME_LOG.add_log_message(f"'{selected_song.title}' is now recorded! Recording Quality: {final_quality:.2f}")
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

                choice = self.ui.present_choices(npc_options, "Talk to who?")
                if choice == "back":
                    self.explore_menu_state = "poi"
                else:
                    self.selected_npc = self.NPC_REGISTRY[choice]
                    # Add to contacts if not already there
                    if self.selected_npc.npc_id not in self.player.contacts:
                        self.player.contacts.append(self.selected_npc.npc_id)
                        self.GAME_LOG.add_log_message(f"You added {self.selected_npc.name} to your contacts.")

                    self.explore_menu_state = "dialogue"
                    self.conversation_history = []
                    self.player_input = ""
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
                    if event.event_type == "OPEN_MIC":
                        self.active_performance = event
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

    def handle_interaction(self, interaction_text, time_cost=15):
        self.GAME_LOG.add_log_message(f"Selected interaction: {interaction_text}")

        # Some interactions have no time cost, handle them first
        if interaction_text == "View upcoming events":
            self.explore_menu_state = "view_events"
            return

        advance_game_time(time_cost)
        self.process_time_based_player_needs(self.player, time_cost)
        if interaction_text == "Browse items for sale":
            if self.selected_poi.shop_inventory_item_ids:
                self.explore_menu_state = "shop"
            else:
                self.GAME_LOG.add_log_message("Nothing for sale currently.")
        elif interaction_text.startswith("Submit Demo"):
            min_fame = self.selected_poi.min_fame_to_submit
            if self.player.fame >= min_fame:
                self.explore_menu_state = "submit_demo"
            else:
                self.GAME_LOG.add_log_message(f"You need at least {min_fame} fame to submit a demo here.")
        elif interaction_text == "Write a new song":
            self.explore_menu_state = "write_song_menu"
            self.songwriting_stage = "choose_genre"
            self.song_in_progress = {}
        elif interaction_text == "Book recording session":
            self.explore_menu_state = "record_song"
        elif interaction_text == "Create a Remix":
            self.explore_menu_state = "remix_menu"
        elif interaction_text == "Rest (8 hours)":
            self.rest()
        elif "Talk" in interaction_text: # More robust check
            self.explore_menu_state = "talk"
        elif interaction_text == "Browse vehicles":
            if self.selected_poi.shop_inventory_vehicle_ids:
                self.explore_menu_state = "dealership"
            else:
                self.GAME_LOG.add_log_message("No vehicles for sale currently.")

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
                dest_opts_list = [t for t in all_city_targets if t.name != self.player.current_poi.name]

                if not dest_opts_list:
                    self.GAME_LOG.add_log_message("No other places to travel to in this city.")
                else:
                    dest_map = {t.poi_id if hasattr(t, 'poi_id') else t.venue_id: t for t in dest_opts_list}
                    dest_disp = {k: f"{v.name} ({getattr(v,'category', getattr(v,'venue_type','N/A'))})" for k, v in dest_map.items()}
                    dest_disp["back"] = "Cancel"

                    chosen_dest_key = self.ui.present_choices(dest_disp, "Choose destination:")
                    if chosen_dest_key != "back":
                        chosen_dest_poi = dest_map[chosen_dest_key]
                        # For now, let's assume a fixed time and cost for intra-city travel
                        travel_time_minutes = 15
                        travel_cost = 2
                        if self.player.money >= travel_cost:
                            self.player.money -= travel_cost
                            self.player.travel_within_city(chosen_dest_poi, travel_time_minutes)
                            advance_game_time(travel_time_minutes)
                            self.update_npc_locations(current_game_time)
                            self.process_time_based_player_needs(self.player, travel_time_minutes)
                            self.GAME_LOG.add_log_message(f"You travelled to {chosen_dest_poi.name}.")
                        else:
                            self.GAME_LOG.add_log_message("You can't afford to travel.")
            self.game_state = "main_menu"
        elif choice == "inter_city":
            if self.player.vehicles:
                vehicle_options = {v.name: str(v) for v in self.player.vehicles}
                vehicle_options["none"] = "No vehicle"
                vehicle_options["back"] = "Cancel"
                vehicle_choice = self.ui.present_choices(vehicle_options, "Choose a vehicle")
                if vehicle_choice == "back":
                    self.game_state = "main_menu"
                    return

                selected_vehicle = None
                if vehicle_choice != "none":
                    for v in self.player.vehicles:
                        if v.name == vehicle_choice:
                            selected_vehicle = v
                            break
            else:
                selected_vehicle = None

            if not self.player.current_poi or self.player.current_poi.category not in ["TRANSPORT_BUS", "TRANSPORT_AIRPORT"]:
                self.GAME_LOG.add_log_message("You need to be at a Bus Station or Airport to travel to another city.")
                self.game_state = "main_menu"
                return

            connections = self.player.current_location.travel_connections
            if not connections:
                self.GAME_LOG.add_log_message(f"No inter-city routes from {self.player.current_location.name}.")
                self.game_state = "main_menu"
                return

            dest_opts = {dest_name: f"To {dest_name} (Cost: ${details['cost']}, Time: {details['time_hours']}h)" for dest_name, details in connections.items()}
            dest_opts["back"] = "Cancel"

            dest_choice = self.ui.present_choices(dest_opts, f"Departures from {self.player.current_poi.name}")
            if dest_choice != "back":
                travel_details = connections[dest_choice]
                if self.player.money >= travel_details['cost']:
                    self.player.money -= travel_details['cost']
                    dest_loc_obj = self.WORLD_MAP.get(dest_choice)
                    if dest_loc_obj:
                        travel_time = travel_details['time_hours']
                        if selected_vehicle:
                            travel_time /= selected_vehicle.speed

                        self.player.travel(dest_loc_obj, travel_time)
                        advance_game_time(travel_time * 60)
                        self.update_npc_locations(current_game_time)
                        self.process_time_based_player_needs(self.player, travel_time * 60)
                        self.GAME_LOG.add_log_message(f"You travelled to {dest_choice}.")
                else:
                    self.GAME_LOG.add_log_message("You can't afford to travel.")
            self.game_state = "main_menu"

    def rest(self, hours=8):
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

        advance_game_time(minutes_to_advance)
        self.process_time_based_player_needs(self.player, minutes_to_advance)

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

            venue = random.choice(city_venues)
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
                # 25% chance per week to release a new song
                if random.random() < 0.25:
                    self.generate_npc_song(npc)

                npc_fame = self._calculate_npc_fame(npc)

                # 15% chance per week to try and book a local gig
                if random.random() < 0.15:
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

                # 5% chance for high-fame NPCs to start a tour
                if npc_fame > 200 and not npc.on_tour and random.random() < 0.05:
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
                "schedule": "Schedule",
                "music": "Music",
                "contacts": "Contacts",
                "web": "Web",
            }
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
            else:
                self.phone_menu_state = choice
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
                "decline": "Decline Offer",
                "back": "Decide later"
            }

            # This is a bit of a hack. We should have a dedicated screen.
            # For now, we'll just print the contract to the log.
            self.GAME_LOG.add_log_message("--- Contract Offer ---")
            for line in str(contract).split('\n'):
                self.GAME_LOG.add_log_message(line)

            choice = self.ui.present_choices(offer_options, f"Offer from {contract.label_name}")

            if choice == "accept":
                self.player.label_deal = contract
                self.player.money += contract.advance_money
                self.GAME_LOG.add_log_message(f"You signed with {contract.label_name}! You received an advance of ${contract.advance_money}.")
                self.player.pending_contracts.clear()
                self.phone_menu_state = "main"
            elif choice == "decline":
                self.GAME_LOG.add_log_message(f"You declined the offer from {contract.label_name}.")
                self.player.pending_contracts.clear()
                self.phone_menu_state = "main"
            elif choice == "back":
                self.phone_menu_state = "main"


    def handle_web_menu(self):
        if self.web_menu_state == "main":
            web_options = {
                "view_charts": "View Music Charts",
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


    def handle_opportunity(self, opp_id):
        opp_data = self.OPPORTUNITY_CATALOG.get(opp_id)
        if not opp_data:
            return

        self.GAME_LOG.add_log_message(f"You pursue the opportunity: {opp_data['name']}")

        if opp_id == "radio_interview_local":
            # Time cost: 2 hours
            advance_game_time(120)

            # Logic for the interview
            self.GAME_LOG.add_log_message("You head down to the K-ROK radio station...")
            # Simple success chance for now
            if random.random() > 0.3: # 70% chance of success
                fame_gain = 25
                self.player.fame += fame_gain
                self.GAME_LOG.add_log_message(f"The interview went great! You feel your buzz growing. (+{fame_gain} Fame)")
            else:
                fame_gain = 5
                self.player.fame += fame_gain
                self.GAME_LOG.add_log_message(f"You were a bit nervous and stumbled on a few questions. Still, exposure is exposure. (+
{fame_gain} Fame)")

            self.player.active_opportunities[opp_id]['status'] = "completed"

        elif opp_id == "music_blog_feature":
            # Time cost: 1 hour
            advance_game_time(60)
            fame_gain = 15
            self.player.fame += fame_gain
            self.GAME_LOG.add_log_message(f"IndiePulse runs a great feature on your music! (+{fame_gain} Fame)")
            self.player.active_opportunities[opp_id]['status'] = "completed"

        elif opp_id.startswith('guest_feature_'):
            npc_id = opp_id.replace('guest_feature_', '')
            npc = self.NPC_REGISTRY.get(npc_id)
            if npc:
                self.GAME_LOG.add_log_message(f"You agree to play on {npc.name}'s new song.")
                advance_game_time(240) # 4 hours studio time

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
            advance_game_time(120) # 2 hours
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
                "release_song": "Release a Song",
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
                selected_song.mark_as_released(current_game_time)
                self.GAME_LOG.add_log_message(f"You've self-released '{selected_song.title}' to the world!")
                # In the future, this could cost money for distribution.
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
                "stats": "Stats",
                "skills": "Skills",
                "inventory": "Inventory",
                "band": "Band",
                "back": "Back"
            }
            choice = self.ui.present_choices(character_menu_opts, "Character")
            if choice == "back":
                self.game_state = "main_menu"
            else:
                self.character_menu_state = choice
        elif self.character_menu_state == "stats":
            self.ui.draw_character_stats(self.player)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.character_menu_state = "main"

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
                    for event in pygame.event.get():
                        if event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_ESCAPE:
                                self.character_menu_state = "main"
                                self.band_menu_state = "main"

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

                        self.player.band.add_member(npc_to_recruit)
                        self.GAME_LOG.add_log_message(f"{npc_to_recruit.name} agreed to join your band!")
                    else:
                        self.GAME_LOG.add_log_message(f"{npc_to_recruit.name} isn't interested. Maybe when you're more famous.")
                    self.band_menu_state = "main"
        elif self.character_menu_state == "skills":
            self.ui.draw_skills_screen(self.player)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.character_menu_state = "main"
        elif self.character_menu_state == "inventory":
            self.ui.draw_inventory_screen(self.player)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.character_menu_state = "main"

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

    def handle_performance_scene(self):
        if self.performance_stage == "choose_song":
            if not self.player.songs_written:
                self.GAME_LOG.add_log_message("You have no songs to perform!")
                self.game_state = "explore"
                return

            song_options = {str(i): f"'{s.title}' (Q: {s.song_quality:.2f})" for i, s in enumerate(self.player.songs_written)}
            song_options["back"] = "Cancel"
            choice = self.ui.present_choices(song_options, "Choose a song to perform:")

            if choice == "back":
                self.game_state = "explore"
            else:
                selected_song = self.player.songs_written[int(choice)]
                self.active_performance.song_to_perform = selected_song # Store it
                self.performance_stage = "intro"
                self.performance_log = [f"You take the stage at {self.active_performance.location.name} for {self.active_performance.name}...",
                                        f"You've decided to play '{selected_song.title}'."]

        elif self.performance_stage == "intro":
            # This is a timed, non-interactive stage
            self.ui.clear_screen()
            venue_id = self.active_performance.location.venue_id
            art_to_display = ART.get(venue_id, ART['default'])
            self.ui.draw_ascii_art(art_to_display, 300, 150)
            # Display the log
            for i, line in enumerate(self.performance_log):
                self.ui.draw_text(line, FONT_LOG, WHITE, 50, 500 + i * 25)
            self.ui.update_display()
            pygame.time.wait(2000) # Pause for 2 seconds

            # Skill check for the intro
            skills_to_use = self.player.band.band_skills if self.player.band else self.player.skills
            performance_score = 0
            if skills_to_use.get('stage_presence', 0) > 5:
                self.performance_log.append("The band looks confident on stage.")
                performance_score += 10
            else:
                self.performance_log.append("You nervously approach the mic.")
                performance_score -= 5
            self.performance_stage = "verse_1"

        elif self.performance_stage == "verse_1":
            self.ui.clear_screen()
            venue_id = self.active_performance.location.venue_id
            art_to_display = ART.get(venue_id, ART['default'])
            self.ui.draw_ascii_art(art_to_display, 300, 150)
            # Display the log
            for i, line in enumerate(self.performance_log):
                self.ui.draw_text(line, FONT_LOG, WHITE, 50, 500 + i * 25)
            self.ui.update_display()
            pygame.time.wait(2000)

            # Skill check for vocals
            skills_to_use = self.player.band.band_skills if self.player.band else self.player.skills
            song = self.active_performance.song_to_perform
            if (skills_to_use.get('vocals', 0) + song.song_quality * 50) > 30:
                self.performance_log.append("The vocals are clear and hit all the right notes.")
                performance_score += 20
            else:
                self.performance_log.append("The vocals are a bit shaky, but the band pushes through.")
                performance_score += 5

            self.active_performance.performance_score = performance_score # Store score
            self.performance_stage = "outro"

        elif self.performance_stage == "outro":
            self.ui.clear_screen()
            venue_id = self.active_performance.location.venue_id
            art_to_display = ART.get(venue_id, ART['default'])
            self.ui.draw_ascii_art(art_to_display, 300, 150)
            # Display the log
            for i, line in enumerate(self.performance_log):
                self.ui.draw_text(line, FONT_LOG, WHITE, 50, 500 + i * 25)
            self.ui.update_display()
            pygame.time.wait(2000)

            # Final skill check
            skills_to_use = self.player.band.band_skills if self.player.band else self.player.skills
            performance_score = self.active_performance.performance_score
            if (skills_to_use.get('guitar', 0) + skills_to_use.get('stage_presence', 0)) > 10:
                self.performance_log.append("The band finishes with a flourish! The crowd applauds.")
                performance_score += 15
            else:
                self.performance_log.append("The song ends. A few people clap politely.")
                performance_score += 5

            # Final rewards
            if self.active_performance.event_type == "BATTLE_OF_THE_BANDS":
                if performance_score > 40:
                    self.GAME_LOG.add_log_message("You won the Battle of the Bands!")
                    fame_gain = 50
                    money_gain = 500
                else:
                    self.GAME_LOG.add_log_message("You didn't win, but you put on a good show.")
                    fame_gain = 15
                    money_gain = 50
            else: # Default for Open Mic
                fame_gain = int(performance_score / 5)
                money_gain = int(performance_score / 2)

            self.player.fame += fame_gain
            self.player.money += money_gain
            self.GAME_LOG.add_log_message(f"Performance complete! You earned ${money_gain} and {fame_gain} fame.")

            # Cleanup
            if self.active_performance.is_tour_gig:
                if self.player.current_tour_id:
                    self.player.tour_ledgers[self.player.current_tour_id]['completed_gigs'].append(self.active_performance.event_id)
                    self.player.tour_ledgers[self.player.current_tour_id]['income'] += money_gain
            elif self.active_performance.event_type == "BATTLE_OF_THE_BANDS":
                self.player.active_opportunities["battle_of_the_bands_local"] = "completed"
            self.active_performance = None
            self.performance_log = []
            self.performance_stage = None
            self.game_state = "explore"
