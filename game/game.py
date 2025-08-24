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
from game.game_time import current_game_time, advance_game_time, get_current_time_str, calculate_player_age, GameTime
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
        self.selected_poi = None
        self.selected_npc = None
        self.conversation_history = []
        self.player_input = ""
        self.songwriting_stage = None
        self.song_in_progress = {}
        self.SONG_GENRES = ["Rock", "Pop", "Folk", "Indie", "Electronic", "Blues"]

        self.SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

        self.WORLD_MAP = {}
        self.NPC_REGISTRY = {}
        self.PLAYER_HOME_POI_ID_GLOBAL = None
        self.ACTIVE_CHARTS = []
        self.LAST_CHART_UPDATE_DAY = -1

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

    def _calculate_song_component_quality(self, primary_skill, secondary_skill=None, weight=0.75):
        """Calculates the quality of a song component based on player skills."""
        primary_skill_val = self.player.skills.get(primary_skill, 0)
        secondary_skill_val = self.player.skills.get(secondary_skill, 0) if secondary_skill else 0

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
        if 6 <= hour <= 11: period = "Morning"
        elif 12 <= hour <= 17: period = "Afternoon"
        elif 18 <= hour <= 23: period = "Evening"
        else: period = "Night"
        return f"{day_type}_{period}"

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
                # ... (chart update logic remains the same) ...
                pass

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
            elif self.game_state == "character":
                self.handle_character_menu()
            elif self.game_state == "system":
                self.handle_system_menu()

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
                interaction_options = {str(i): option for i, option in enumerate(self.selected_poi.get_interactions())}
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
                self.songwriting_stage = "finalize_song"
                # Fall through to the finalize stage immediately

            if self.songwriting_stage == "finalize_song":
                # This is also a non-interactive stage
                title = self.song_in_progress.get('title', 'Untitled')
                genre = self.song_in_progress.get('genre', 'Rock')

                new_song = Song(
                    title=title,
                    author=self.player.name,
                    genre=genre,
                    originality=self.song_in_progress.get('originality', 0.5),
                    catchiness=self.song_in_progress.get('catchiness', 0.5),
                    lyrical_depth=self.song_in_progress.get('lyrical_depth', 0.5),
                    music_complexity=self.song_in_progress.get('music_complexity', 0.5)
                )

                self.player.songs_written.append(new_song)
                self.GAME_LOG.add_log_message(f"You finished writing '{title}'! Overall Quality: {new_song.song_quality:.2f}")

                # Clean up and exit songwriting mode
                self.song_in_progress = {}
                self.songwriting_stage = None
                self.explore_menu_state = "poi"

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
                    self.explore_menu_state = "dialogue"
                    self.conversation_history = []
                    self.player_input = ""
        elif self.explore_menu_state == "dialogue":
            if self.selected_npc:
                self.ui.draw_dialogue_screen(self.selected_npc.name, self.conversation_history, self.player_input)
                for event in pygame.event.get():
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_RETURN:
                            if self.player_input.lower() == "bye":
                                self.explore_menu_state = "poi"
                                self.selected_npc = None
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
        advance_game_time(time_cost)
        self.process_time_based_player_needs(self.player, time_cost)
        if interaction_text == "Browse items for sale":
            if self.selected_poi.shop_inventory_item_ids:
                self.explore_menu_state = "shop"
            else:
                self.GAME_LOG.add_log_message("Nothing for sale currently.")
        elif interaction_text == "Write a new song":
            self.explore_menu_state = "write_song_menu"
            self.songwriting_stage = "choose_genre"
            self.song_in_progress = {}
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
        advance_game_time(minutes_to_advance)
        self.process_time_based_player_needs(self.player, minutes_to_advance)
        # Simplified energy/stress recovery
        self.player.energy = min(100, self.player.energy + hours * 10)
        self.player.stress = max(0, self.player.stress - hours * 5)

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

    def handle_phone_menu(self):
        if self.phone_menu_state == "main":
            phone_menu_opts = {
                "schedule": "Schedule",
                "music": "Music",
                "contacts": "Contacts",
                "web": "Web",
                "back": "Back"
            }

            choice = self.ui.present_choices(phone_menu_opts, "Phone")
            if choice == "back":
                self.game_state = "main_menu"
            else:
                self.phone_menu_state = choice
        elif self.phone_menu_state == "contacts":
            self.handle_contacts_menu()
        elif self.phone_menu_state == "schedule":
            self.ui.draw_schedule_screen(self.player)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.phone_menu_state = "main"

    def handle_music_menu(self):
        music_menu_opts = {
            "write": "Write Song",
            "record": "Record Song",
            "release": "Release Song",
            "back": "Back"
        }
        choice = self.ui.present_choices(music_menu_opts, "Music")
        if choice == "back":
            self.game_state = "phone"

    def handle_contacts_menu(self):
        if not self.player.contacts:
            self.GAME_LOG.add_log_message("You have no contacts.")
            self.phone_menu_state = "main"
            return

        contacts_menu_opts = {contact['npc_id']: contact['name'] for contact in self.player.contacts}
        contacts_menu_opts["back"] = "Back"

        choice = self.ui.present_choices(contacts_menu_opts, "Contacts")
        if choice == "back":
            self.phone_menu_state = "main"
        else:
            # Placeholder for what to do when a contact is selected
            npc_name = contacts_menu_opts[choice]
            self.GAME_LOG.add_log_message(f"You selected {npc_name} from your contacts.")
            self.phone_menu_state = "main"

    def handle_character_menu(self):
        if self.character_menu_state == "main":
            character_menu_opts = {
                "stats": "Stats",
                "skills": "Skills",
                "inventory": "Inventory",
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
