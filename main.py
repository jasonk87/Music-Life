# game/main.py
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
import random
import json
import os
import pygame
from game.pygame_ui import PygameUI
import collections

from game_data.gear_catalog import GEAR_CATALOG
from game.npc import NPC
from game.chart import Chart
from game.feedback_generator import generate_feedback_for_song, SOURCES, generate_feedback_for_album

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

WORLD_MAP = {}
NPC_REGISTRY = {}
PLAYER_HOME_POI_ID_GLOBAL = None
ACTIVE_CHARTS = []
LAST_CHART_UPDATE_DAY = -1

GAME_LOG = None

class LogPanel:
    def __init__(self, window, max_lines=None):
        self.window = window
        self.messages = collections.deque()
        height, width = self.window.getmaxyx()
        self.max_lines = max_lines if max_lines is not None else height - 2
        self.width = width - 2

    def add_message(self, message_string):
        for sub_message in message_string.split('\n'):
            self.messages.append(sub_message[:self.width])
            if len(self.messages) > self.max_lines:
                self.messages.popleft()
        self.render()

    def render(self):
        self.window.clear()
        self.window.box()
        for i, msg in enumerate(self.messages):
            self.window.addstr(i + 1, 1, msg)
        self.window.refresh()

def process_time_based_player_needs(player, minutes_just_passed):
    if minutes_just_passed <= 0: return
    hours_passed_float = minutes_just_passed / 60.0
    if player.current_poi and hasattr(player.current_poi, 'comfort_modifier_hourly'):
        comfort_change = hours_passed_float * player.current_poi.comfort_modifier_hourly
        player.comfort = min(100, max(0, player.comfort + comfort_change))
        player.comfort = int(round(player.comfort))
    is_at_player_home = player.current_poi and PLAYER_HOME_POI_ID_GLOBAL and \
                        hasattr(player.current_poi, 'poi_id') and \
                        player.current_poi.poi_id == PLAYER_HOME_POI_ID_GLOBAL
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
        if levels_gained > 0 and GAME_LOG: GAME_LOG.add_message(f"DEBUG: Your hair grew! New length: {player.hair_length}/{player.MAX_HAIR_LENGTH}")

    if player.beard_growth_progress >= player.BEARD_POINTS_PER_LENGTH_LEVEL:
        levels_gained = int(player.beard_growth_progress // player.BEARD_POINTS_PER_LENGTH_LEVEL)
        player.beard_length = min(player.MAX_BEARD_LENGTH, player.beard_length + levels_gained)
        player.beard_growth_progress %= player.BEARD_POINTS_PER_LENGTH_LEVEL
        if levels_gained > 0 and GAME_LOG: GAME_LOG.add_message(f"DEBUG: Your beard grew! New length: {player.beard_length}/{player.MAX_BEARD_LENGTH}")

_POI_VENUE_ID_MAP = {}

def _build_poi_venue_id_map():
    _POI_VENUE_ID_MAP.clear()
    for location in WORLD_MAP.values():
        for poi in location.points_of_interest: _POI_VENUE_ID_MAP[poi.poi_id] = poi
        for venue in location.venues: _POI_VENUE_ID_MAP[venue.venue_id] = venue

def get_poi_or_venue_by_id(target_id):
    return _POI_VENUE_ID_MAP.get(target_id)

def setup_world():
    global WORLD_MAP, NPC_REGISTRY, PLAYER_HOME_POI_ID_GLOBAL
    WORLD_MAP.clear(); NPC_REGISTRY.clear(); _POI_VENUE_ID_MAP.clear()

    locations_json_path = os.path.join(SCRIPT_DIR, "game_data", "world", "locations.json")
    npcs_json_path = os.path.join(SCRIPT_DIR, "game_data", "world", "npcs.json")

    try:
        with open(locations_json_path, 'r') as f: locations_data = json.load(f)
    except Exception as e: GAME_LOG.add_message(f"FATAL ERROR loading {locations_json_path}: {e}"); return False

    temp_location_id_map = {}
    for loc_data in locations_data:
        location = Location(loc_data["name"], loc_data["description"]); location.id = loc_data["id"]
        WORLD_MAP[location.name] = location; temp_location_id_map[location.id] = location

    for loc_id_from_json, location_obj in temp_location_id_map.items():
        poi_file_name = next((ld["poi_definition_file"] for ld in locations_data if ld["id"] == loc_id_from_json), None)
        if not poi_file_name: GAME_LOG.add_message(f"Warning: No POI file for {location_obj.name}."); continue

        city_def_json_path = os.path.join(SCRIPT_DIR, "game_data", "world", "city_definitions", poi_file_name)
        try:
            with open(city_def_json_path, 'r') as f: city_def_data = json.load(f)
        except Exception as e: GAME_LOG.add_message(f"ERROR loading {city_def_json_path}: {e}"); continue

        for poi_data in city_def_data.get("points_of_interest", []):
            props = poi_data.get("properties", {}).copy()
            shop_inventory_ids = props.pop("shop_inventory_item_ids", None)
            menu_items_data = props.pop("menu_items", None)
            owner_npc_id_temp = props.pop("owner_npc_id", None)
            poi = PointOfInterest(poi_id=poi_data["poi_id"], name=poi_data["name"], description=poi_data["description"],
                                  category=poi_data["category"], interaction_options=list(poi_data.get("interaction_options", [])),
                                  parent_location_id=location_obj.name, **props)
            if shop_inventory_ids is not None: poi.shop_inventory_item_ids = list(shop_inventory_ids)
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

    _build_poi_venue_id_map()

    try:
        with open(npcs_json_path, 'r') as f: npcs_data = json.load(f)
    except Exception as e: GAME_LOG.add_message(f"ERROR loading {npcs_json_path}: {e}"); return False

    for npc_data in npcs_data:
        home_loc_obj = get_poi_or_venue_by_id(npc_data.get("home_location_poi_id")) or WORLD_MAP.get(npc_data.get("home_location_location_id"))
        current_loc_obj = get_poi_or_venue_by_id(npc_data.get("initial_current_location_poi_id")) or WORLD_MAP.get(npc_data.get("initial_current_location_location_id"))
        if not home_loc_obj and npc_data.get("schedule"): home_loc_obj = get_poi_or_venue_by_id(list(npc_data["schedule"].values())[0])
        if not current_loc_obj: current_loc_obj = home_loc_obj
        if not home_loc_obj: GAME_LOG.add_message(f"Warning: No home location for NPC {npc_data['name']}.")
        if not current_loc_obj: GAME_LOG.add_message(f"Warning: No current location for NPC {npc_data['name']}.")
        npc = NPC(npc_id=npc_data["npc_id"], name=npc_data["name"], personality_key=npc_data["personality_key"], home_location=home_loc_obj, current_location=current_loc_obj)
        for time_slot, loc_id_str in npc_data.get("schedule", {}).items():
            scheduled_loc_obj = get_poi_or_venue_by_id(loc_id_str)
            if scheduled_loc_obj: npc.schedule[time_slot] = scheduled_loc_obj
            else: GAME_LOG.add_message(f"Warning: Scheduled POI/Venue ID '{loc_id_str}' not found for {npc.name}'s schedule.")
        NPC_REGISTRY[npc.npc_id] = npc

    for loc in WORLD_MAP.values():
        for item_list in [loc.points_of_interest, loc.venues]:
            for item in item_list:
                if hasattr(item, 'owner_npc_id') and isinstance(item.owner_npc_id, str):
                    owner_npc = NPC_REGISTRY.get(item.owner_npc_id)
                    if owner_npc: item.owner_npc_id = owner_npc
                    else: GAME_LOG.add_message(f"Warning: Owner NPC ID '{item.owner_npc_id}' not found for POI/Venue '{item.name}'."); item.owner_npc_id = None

    for loc_data in locations_data:
        curr_loc_obj = temp_location_id_map.get(loc_data["id"])
        if not curr_loc_obj: continue
        for conn_data in loc_data.get("travel_connections", []):
            target_loc_obj = temp_location_id_map.get(conn_data["to_location_id"])
            if target_loc_obj: curr_loc_obj.add_travel_connection(target_loc_obj.name, cost=conn_data["cost"], time_hours=conn_data["time_hours"])
            else: GAME_LOG.add_message(f"Warning: Target location ID '{conn_data['to_location_id']}' for travel from '{curr_loc_obj.name}' not found.")

    event_defs = [
        {"id": "open_mic_hometown_hall", "venue_id": "hometown_community_hall", "name": "Open Mic Night", "type": "OPEN_MIC", "skills": {"vocals": 1, "guitar": 1}, "gear": ["INSTRUMENT_ACOUSTIC"], "desc": "A chance to show your skills..."},
        {"id": "debut_rusty_mug", "venue_id": "citycenter_rustymug", "name": "Debut at 'The Rusty Mug'", "type": "CLUB_GIG", "skills": {"vocals": 5, "guitar": 5, "stage_presence": 3}, "gear": ["INSTRUMENT_ELECTRIC", "AMPLIFIER"], "desc": "Your first real club gig!", "prep_tasks": {"Write Setlist (3 songs)": False, "Rehearse Set (2 hours)": False, "Promote Gig Locally": False}},
        {"id": "opening_act_grande", "venue_id": "citycenter_grandetheater", "name": "Opening Act for Major Band", "type": "CONCERT", "skills": {"vocals": 15, "guitar": 15, "stage_presence": 10, "songwriting": 10}, "gear": ["INSTRUMENT_ELECTRIC", "AMPLIFIER", "INSTRUMENT_BASS", "INSTRUMENT_DRUMS"], "desc": "A huge opportunity...", "prep_tasks": {"Finalize Setlist (5 songs)": False, "Intensive Rehearsal (10 hours)": False, "Coordinate with Main Act": False, "Sound Check (2 hours)": False}}
    ]
    for ed in event_defs:
        vo = get_poi_or_venue_by_id(ed["venue_id"])
        if vo and isinstance(vo, Venue) and ed["id"] in getattr(vo, 'events_hosted_ids_from_json', [ed["id"]]):
            is_tour_gig_flag = "tour" in ed.get("name", "").lower()
            evt = Event(name=ed["name"], event_type=ed["type"], location=vo, required_skills=ed["skills"], required_gear_types=ed["gear"], description=ed["desc"], is_tour_gig=is_tour_gig_flag)
            if "prep_tasks" in ed: evt.preparation_tasks_required = ed["prep_tasks"]
            vo.add_event(evt)
        else: GAME_LOG.add_message(f"Warning: Venue ID '{ed['venue_id']}' for event '{ed['name']}' not found or not a Venue.")

    player_home_obj = get_poi_or_venue_by_id("hometown_player_home")
    if player_home_obj: PLAYER_HOME_POI_ID_GLOBAL = player_home_obj.poi_id
    else: GAME_LOG.add_message("CRITICAL ERROR: Player home POI 'hometown_player_home' not found.")

    ACTIVE_CHARTS.clear()
    hometown_chart = Chart(name="Hometown Local Hits", max_size=10, chart_genre_preference="Indie")
    city_chart = Chart(name="City Center Top Tracks", max_size=20)
    ACTIVE_CHARTS.append(hometown_chart); ACTIVE_CHARTS.append(city_chart)
    if GAME_LOG:
        GAME_LOG.add_log_message(f"Initialized {len(ACTIVE_CHARTS)} charts.")
        GAME_LOG.add_log_message(f"World setup complete. Loaded {len(WORLD_MAP)} locations and {len(NPC_REGISTRY)} NPCs.")
    return True

def get_day_of_week_name(day_number_in_month): return ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][(day_number_in_month - 1) % 7]
def get_time_slot_key(gt_obj):
    day_name = get_day_of_week_name(gt_obj.day); hour = gt_obj.hour
    day_type = "Weekend" if day_name in ["Saturday", "Sunday"] else "Weekday"
    if 6 <= hour <= 11: period = "Morning"
    elif 12 <= hour <= 17: period = "Afternoon"
    elif 18 <= hour <= 23: period = "Evening"
    else: period = "Night"
    return f"{day_type}_{period}"

def update_npc_locations(gt_obj):
    time_slot_key = get_time_slot_key(gt_obj)
    for npc in NPC_REGISTRY.values():
        dest_ref = npc.schedule.get(time_slot_key)
        dest = None
        if isinstance(dest_ref, (PointOfInterest, Venue, Location)): dest = dest_ref
        elif isinstance(dest_ref, str): dest = get_poi_or_venue_by_id(dest_ref) or WORLD_MAP.get(dest_ref)
        if dest is None : dest = npc.home_location
        if npc.npc_id == "sarah001":
            comm_hall = get_poi_or_venue_by_id("hometown_community_hall")
            if comm_hall and any(e.name == "Open Mic Night" and e.is_active for e in getattr(comm_hall, 'events_hosted', [])):
                scheduled_loc_for_open_mic = npc.schedule.get("open_mic_night_at_community_hall")
                if isinstance(scheduled_loc_for_open_mic, str): scheduled_loc_for_open_mic = get_poi_or_venue_by_id(scheduled_loc_for_open_mic)
                if scheduled_loc_for_open_mic == comm_hall: dest = comm_hall
        if npc.current_location != dest: npc.current_location = dest

def present_choices(options, title="Choose an option:"): # Old, for non-Curses or background logic if needed
    if GAME_LOG: GAME_LOG.add_message(f"--- {title} ---")
    else: print(f"--- {title} ---") # Fallback if GAME_LOG not init
    # ... (rest of the old present_choices, its input() will break curses)
    return None # Should not be relied upon in Curses flow

def present_choices_curses(window, options, title="Choose an option:"):
    window.clear()
    window.box()
    max_h, max_w = window.getmaxyx()
    title_x = max(2, (max_w - len(title)) // 2)
    window.addstr(1, title_x, title, curses.A_BOLD)

    options_list = list(options.items()) if isinstance(options, dict) else [(str(i + 1), opt) for i, opt in enumerate(options)]
    if not options_list:
        window.addstr(3, 2, "Error: No options for menu.")
        window.refresh()
        window.getch()
        return None

    selected_idx = 0
    option_display_y_start = 3
    max_items_on_screen = max_h - option_display_y_start - 2
    current_scroll_top_idx = 0

    while True:
        for i in range(max_items_on_screen):
            actual_option_idx = current_scroll_top_idx + i
            display_y = option_display_y_start + i
            if display_y >= max_h - 1:
                break

            if actual_option_idx < len(options_list):
                key, text = options_list[actual_option_idx]
                display_text = f"{text}"[:max_w - 6]
                attr = curses.A_REVERSE if actual_option_idx == selected_idx else curses.A_NORMAL
                window.addstr(display_y, 3, display_text, attr)
            else:
                window.move(display_y, 3)
                window.clrtoeol()

        if len(options_list) > max_items_on_screen:
            if current_scroll_top_idx > 0:
                window.addstr(option_display_y_start, max_w - 4, "^")
            else:
                window.addstr(option_display_y_start, max_w - 4, " ")
            if current_scroll_top_idx + max_items_on_screen < len(options_list):
                window.addstr(option_display_y_start + max_items_on_screen - 1, max_w - 4, "v")
            else:
                window.addstr(option_display_y_start + max_items_on_screen - 1, max_w - 4, " ")

        window.refresh()
        key_press = window.getch()

        if key_press == curses.KEY_UP:
            selected_idx = (selected_idx - 1 + len(options_list)) % len(options_list)
            if selected_idx < current_scroll_top_idx:
                current_scroll_top_idx = selected_idx
            elif selected_idx >= current_scroll_top_idx + max_items_on_screen:
                current_scroll_top_idx = selected_idx - max_items_on_screen + 1
            window.clear()
            window.box()
            window.addstr(1, title_x, title, curses.A_BOLD)

        elif key_press == curses.KEY_DOWN:
            selected_idx = (selected_idx + 1) % len(options_list)
            if selected_idx >= current_scroll_top_idx + max_items_on_screen:
                current_scroll_top_idx = selected_idx - max_items_on_screen + 1
            elif selected_idx < current_scroll_top_idx:
                current_scroll_top_idx = selected_idx
            window.clear()
            window.box()
            window.addstr(1, title_x, title, curses.A_BOLD)

        elif key_press == curses.KEY_ENTER or key_press == ord('\n') or key_press == ord('\r'):
            return options_list[selected_idx][0]

        elif 32 <= key_press <= 126:
            pressed_key_str = chr(key_press)
            for i, (opt_key, _) in enumerate(options_list):
                if opt_key == pressed_key_str:
                    return opt_key


def get_string_curses(window, r, c, prompt_string, max_len=30):
    window.addstr(r, c, prompt_string)
    window.refresh(); curses.echo()
    input_str = window.getstr(r, c + len(prompt_string), max_len).decode('utf-8').strip()
    curses.noecho()
    return input_str

def display_hud_curses(hud_window, player, gt_obj):
    hud_window.clear(); hud_window.box()
    age = calculate_player_age(player.start_date, gt_obj, player.age)
    loc_name = player.current_location.name if player.current_location else 'N/A'
    poi_name = player.current_poi.name if player.current_poi else 'N/A'
    width = hud_window.getmaxyx()[1]
    line1 = f"| {player.name} | Age: {age} | Fame: {player.fame} | Money: ${player.money:,} "
    line2 = f"| Loc: {loc_name}/{poi_name} | Time: {gt_obj.hour:02d}:{gt_obj.minute:02d} ({get_current_time_str(date_only=True)})"
    hud_window.addstr(1, 1, line1[:width-2]); hud_window.addstr(2, 1, line2[:width-2])
    hud_window.refresh()

def get_hair_length_description(val):
    if val == 0: return "Bald"
    elif val <= 2: return "Very Short"
    elif val <= 4: return "Short"
    elif val <= 6: return "Medium"
    elif val <= 8: return "Long"
    else: return "Very Long"

def get_beard_length_description(val):
    if val == 0: return "Clean-shaven"
    elif val <= 2: return "Stubble"
    elif val <= 4: return "Short Beard"
    elif val <= 6: return "Medium Beard"
    elif val <= 8: return "Long Beard"
    else: return "Wizard Beard"

def talk_to_npc_instance(player, npc, main_window):
    if not npc: GAME_LOG.add_message("No one specific to talk to."); return
    main_window.clear(); main_window.box()
    main_window.addstr(1,2, f"--- Talking to {npc.name} ---", curses.A_BOLD)
    main_window.addstr(2,2, "Type 'bye' to end.")
    chat_log_win_height = main_window.getmaxyx()[0] - 8
    chat_log_win = main_window.subwin(chat_log_win_height, main_window.getmaxyx()[1]-4, main_window.getbegyx()[0]+3, main_window.getbegyx()[1]+2)
    chat_log_win.scrollok(True)
    chat_messages = collections.deque(maxlen=chat_log_win_height-2)
    def add_chat_message(msg):
        for line in msg.split('\n'): chat_messages.append(line[:chat_log_win.getmaxyx()[1]-2])
        chat_log_win.clear()
        for i, chat_msg in enumerate(chat_messages): chat_log_win.addstr(i, 0, chat_msg)
        chat_log_win.refresh()
    input_prompt_y = main_window.getbegyx()[0] + 3 + chat_log_win_height + 1
    input_prompt_x = main_window.getbegyx()[1] + 2
    talk_duration_minutes = 0
    while True:
        main_window.move(input_prompt_y, input_prompt_x); main_window.clrtoeol()
        p_input = get_string_curses(main_window, input_prompt_y, input_prompt_x, f"{player.name}: ")
        add_chat_message(f"{player.name}: {p_input}")
        talk_duration_minutes += 5
        if p_input.lower() == 'bye':
            add_chat_message(f"{npc.name} nods."); npc.add_memory(f"Ended chat with {player.name}.")
            GAME_LOG.add_message(f"Ended chat with {npc.name}.")
            break
        if not p_input.strip(): continue
        response = generate_npc_response(p_input, npc, player_name=player.name)
        add_chat_message(f"{npc.name}: {response}")
        if "LLM Error" in response or "unexpected error" in response:
            npc.add_memory(f"LLM error with {player.name}."); talk_duration_minutes = max(15, talk_duration_minutes)
            GAME_LOG.add_message(f"LLM Error during chat with {npc.name}."); break
        clar_opts = {"1": "Friendly", "2": "Neutral", "3": "Unfriendly", "0": "Continue"}
        main_window.move(input_prompt_y + 1, input_prompt_x); main_window.clrtoeol()
        intent_choice = present_choices_curses(main_window, clar_opts, "Your intent towards NPC:")
        main_window.move(input_prompt_y + 1, input_prompt_x); main_window.clrtoeol()
        pts = 0; mem_detail = ""
        if intent_choice == "1": pts = 5; mem_detail = f"Player friendly: '{p_input}'"
        elif intent_choice == "3": pts = -5; mem_detail = f"Player unfriendly: '{p_input}'"
        if pts != 0:
            npc.update_relationship(pts); npc.add_memory(mem_detail)
            add_chat_message(f"(System: Your relationship with {npc.name} changed by {pts}.)")
            GAME_LOG.add_message(f"Relationship with {npc.name} changed by {pts} due to intent on: '{p_input}'")
        is_contact = any(c['npc_id'] == npc.npc_id for c in player.contacts)
        if not is_contact and npc.relationship_score >= 30:
            main_window.move(input_prompt_y + 1, input_prompt_x); main_window.clrtoeol()
            contact_q_opts = {"1": "Ask for number", "0": "Don't ask"}
            if present_choices_curses(main_window, contact_q_opts, f"Deepen connection with {npc.name}?")=="1":
                main_window.move(input_prompt_y + 1, input_prompt_x); main_window.clrtoeol()
                agrees = (npc.relationship_score >= 70 and random.random()<0.95) or \
                         (npc.relationship_score >= 50 and random.random()<0.75) or (random.random()<0.50)
                if agrees:
                    player.contacts.append({'npc_id':npc.npc_id, 'name':npc.name, 'notes':f"Met at {player.current_poi.name if player.current_poi else player.current_location.name}, {get_current_time_str(True)}. Rel: {npc.relationship_score}"})
                    add_chat_message(f"(System: You exchanged numbers with {npc.name}!)")
                    GAME_LOG.add_message(f"Exchanged numbers with {npc.name}!"); npc.add_memory(f"Exchanged numbers with {player.name}."); npc.update_relationship(10)
                else:
                    add_chat_message(f"(System: {npc.name} politely declines to exchange numbers right now.)")
                    GAME_LOG.add_message(f"{npc.name} declined number exchange."); npc.add_memory(f"Declined number exchange with {player.name}."); npc.update_relationship(-2)
                talk_duration_minutes += 5
            main_window.move(input_prompt_y + 1, input_prompt_x); main_window.clrtoeol()
    main_window.addstr(input_prompt_y + 2, 2, "Chat ended. Press any key.")
    main_window.refresh(); main_window.getch()
    final_talk_time = max(15, talk_duration_minutes)
    advance_game_time(final_talk_time); update_npc_locations(current_game_time); process_time_based_player_needs(player, final_talk_time)

def handle_phone_menu(player, main_window):
    while True:
        main_window.clear(); main_window.box()
        opts = {"1":"Check Schedule", "2":"Local News", "3":"Contacts", "4":"Music Management", "0":"Put Phone Away"}
        choice = present_choices_curses(main_window, opts, f"Phone Options ({player.name} - {get_current_time_str()})")
        adv_time = 1
        main_window.clear(); main_window.box()

        if choice == "1": # Check Schedule
            sched_opts = {"1":"Today", "2":"Tomorrow", "3":"This Week", "0":"Back"}
            view_choice = present_choices_curses(main_window, sched_opts, "Select schedule view:")
            main_window.clear(); main_window.box()
            if view_choice == "0": continue
            target_time = current_game_time.copy()
            if view_choice == "2": target_time.advance_time(24*60)
            items, title_str = [], ""
            if view_choice in ["1","2"]:
                items=player.schedule.get_events_for_day(target_time.year,target_time.month,target_time.day)
                title_str=f"{sched_opts[view_choice]}'s Schedule ({target_time.year}-{target_time.month:02d}-{target_time.day:02d})"
            elif view_choice == "3":
                items=player.schedule.get_events_for_week(target_time.year,target_time.month,target_time.day)
                title_str=f"This Week's Schedule (Start: {target_time.year}-{target_time.month:02d}-{target_time.day:02d})"
            main_window.addstr(1, 2, title_str, curses.A_BOLD)
            if not items: main_window.addstr(3, 2, "Nothing scheduled.")
            else:
                for i, item_obj in enumerate(items):
                    main_window.addstr(i + 3, 2, str(item_obj)[:main_window.getmaxyx()[1]-4])
            main_window.addstr(main_window.getmaxyx()[0] - 2, 2, "Press any key..."); main_window.refresh(); main_window.getch()
            adv_time = 10

        elif choice == "2":
            main_window.addstr(1,2, "--- Local News ---"); main_window.addstr(3,2, "(Feature TBD)")
            main_window.addstr(main_window.getmaxyx()[0] - 2, 2, "Press any key..."); main_window.refresh(); main_window.getch()
            adv_time = 5

        elif choice == "3": # Contacts
            main_window.addstr(1,2, "--- Contacts ---", curses.A_BOLD)
            if not player.contacts: main_window.addstr(3,2, "Contact list empty."); adv_time=1
            else:
                contact_map = {str(i+1): c for i, c in enumerate(player.contacts)}
                contact_opts_curses = {k : f"{v['name']} (Notes: {v.get('notes','N/A')})" for k,v in contact_map.items()}
                contact_opts_curses["0"] = "Back"
                sel_c_key = present_choices_curses(main_window, contact_opts_curses, "Select contact to call:")
                main_window.clear(); main_window.box()
                if sel_c_key != "0" and sel_c_key in contact_map:
                    contact_to_call = contact_map[sel_c_key]
                    main_window.addstr(1,2, f"Calling {contact_to_call['name']}...", curses.A_BOLD); main_window.refresh(); curses.napms(1000)
                    call_mins = random.randint(2,5); adv_time += call_mins
                    npc_obj = NPC_REGISTRY.get(contact_to_call['npc_id'])
                    responses = [f"{contact_to_call['name']} doesn't pick up.", f"{contact_to_call['name']} is busy."]
                    chosen_response = random.choice(responses)
                    if npc_obj: npc_obj.add_memory(f"Call from {player.name} ({chosen_response}).")
                    main_window.addstr(3,2, chosen_response); GAME_LOG.add_message(f"Call to {contact_to_call['name']}: {chosen_response}")
                elif sel_c_key == "0": main_window.addstr(1,2, "Call cancelled."); GAME_LOG.add_message("Contact call cancelled.")
                else: main_window.addstr(1,2, "Invalid contact."); GAME_LOG.add_message("Invalid contact selection.")
            main_window.addstr(main_window.getmaxyx()[0] - 2, 2, "Press any key..."); main_window.refresh(); main_window.getch()

        elif choice == "4": # Music Management
            adv_time_music_mgmt = 5
            music_management_active = True
            while music_management_active:
                main_window.clear(); main_window.box()
                unread_feedback_count = sum(1 for f_item in player.feedback_received if not f_item.get("read", False))
                pending_offers_count = sum(1 for offer in player.active_label_offers if offer.get("status") == "pending_player_decision")
                music_opts_curses = {
                    "1": "Self-Release Song", "2": "Promote Released Song", "3": "Plan a Local Gig",
                    "4": f"Reviews/Fan Mail{' (NEW)' if unread_feedback_count > 0 else ''}",
                    "5": "View Charts", "6": f"Label Offers{' (NEW)' if pending_offers_count > 0 else ''}",
                    "7": "View Released Songs"}
                if player.signed_label_deal: music_opts_curses["8"] = "View Current Label Deal"
                music_opts_curses["0"] = "Back to Phone Menu"
                music_choice = present_choices_curses(main_window, music_opts_curses, "Music Management")
                main_window.clear(); main_window.box()

                if music_choice == "1": # Self-Release Song
                    main_window.addstr(1,2, "--- Self-Release Song ---", curses.A_BOLD)
                    recorded_unreleased = [s for s in player.songs_written if s.is_recorded and not s.is_released]
                    if not recorded_unreleased:
                        main_window.addstr(3,2, "No recorded songs ready for release.")
                        GAME_LOG.add_message("Self-Release: No recorded, unreleased songs.")
                    else:
                        song_map = {str(i+1): s for i, s in enumerate(recorded_unreleased)}
                        song_disp = {k: f"{v.title} (Q:{v.song_quality:.2f} RecQ:{v.recording_quality:.2f})" for k,v in song_map.items()}
                        song_disp["0"] = "Cancel"
                        chosen_song_key = present_choices_curses(main_window, song_disp, "Choose song to release:")
                        main_window.clear(); main_window.box()
                        if chosen_song_key and chosen_song_key != "0" and chosen_song_key in song_map:
                            song_to_release = song_map[chosen_song_key]; release_cost = 100
                            main_window.addstr(1,2, f"Release '{song_to_release.title}' for ${release_cost}?", curses.A_BOLD)
                            confirm_key = present_choices_curses(main_window, {"1":"Yes", "0":"No"}, "Confirm Release:")
                            main_window.clear(); main_window.box()
                            if confirm_key == "1":
                                if player.money >= release_cost:
                                    player.money -= release_cost
                                    if song_to_release.mark_as_released(current_game_time.copy()):
                                        main_window.addstr(1,2, f"'{song_to_release.title}' released! Money: ${player.money}")
                                        GAME_LOG.add_message(f"Self-released '{song_to_release.title}'.")
                                        # Feedback & fame logic here
                                        adv_time_music_mgmt += 60
                                    else: main_window.addstr(1,2, "Release failed."); player.money += release_cost
                                else: main_window.addstr(1,2, f"Not enough money (need ${release_cost}).")
                            else: main_window.addstr(1,2, "Release cancelled.")
                        else: main_window.addstr(1,2, "Release process cancelled.")

                elif music_choice == "2": # Promote Released Song
                    main_window.addstr(1,2, "--- Promote Released Song ---", curses.A_BOLD)
                    released = [s for s in player.songs_written if s.is_released]
                    if not released: main_window.addstr(3,2, "No songs released to promote.")
                    else:
                        song_map = {str(i+1): s for i,s in enumerate(released)}
                        song_disp = {k: f"{v.title} (Buzz: {v.buzz_score:.1f})" for k,v in song_map.items()}
                        song_disp["0"] = "Cancel"
                        chosen_song_key = present_choices_curses(main_window, song_disp, "Choose song to promote:")
                        main_window.clear(); main_window.box()
                        if chosen_song_key and chosen_song_key != "0" and chosen_song_key in song_map:
                            song_to_promote = song_map[chosen_song_key]
                            main_window.addstr(1,2, f"Promoting: {song_to_promote.title}", curses.A_BOLD)
                            promo_actions = {"1":"Social Media ($50, 2hr)", "2":"Flyers ($20, 4hr)", "0":"Cancel"}
                            action_key = present_choices_curses(main_window, promo_actions, "Promotion type:")
                            main_window.clear(); main_window.box()
                            cost, time_h, buzz_r, msg_promo = 0,0,(0,0),""
                            if action_key == "1": cost,time_h,buzz_r,msg_promo = 50,2,(5,15),"Social media"
                            elif action_key == "2": cost,time_h,buzz_r,msg_promo = 20,4,(2,8),"Flyers"

                            if cost > 0:
                                if player.money >= cost:
                                    player.money -= cost; adv_time_music_mgmt += time_h*60
                                    buzz_inc = round(random.uniform(buzz_r[0],buzz_r[1]),1)
                                    song_to_promote.buzz_score = min(100, song_to_promote.buzz_score + buzz_inc)
                                    main_window.addstr(1,2, f"{msg_promo} campaign run for '{song_to_promote.title}'. Buzz +{buzz_inc:.1f}")
                                    GAME_LOG.add_message(f"Promoted '{song_to_promote.title}' via {msg_promo}. Buzz: {song_to_promote.buzz_score:.1f}")
                                else: main_window.addstr(1,2, f"Not enough money for {msg_promo}.")
                            elif action_key != "0": main_window.addstr(1,2,"Promotion type TBD or cancelled.")
                        else: main_window.addstr(1,2, "Promotion cancelled.")

                elif music_choice == "3": # Plan a Local Gig
                    main_window.addstr(1,2, "--- Plan a Local Gig ---", curses.A_BOLD)
                    y_offset_gig = 3
                    if not player.current_location or not hasattr(player.current_location, 'venues') or not player.current_location.venues:
                        main_window.addstr(y_offset_gig, 2, "No venues in current location.")
                        GAME_LOG.add_message("Plan Local Gig: No venues in current location.")
                    else:
                        suitable_venues = [v for v in player.current_location.venues if v.category in ["CLUB_SMALL", "CAFE", "VENUE_BAR", "COMMUNITY_HALL"] and getattr(v, 'allows_player_booking', True)]
                        if not suitable_venues:
                            main_window.addstr(y_offset_gig, 2, f"No suitable venues in {player.current_location.name}.")
                            GAME_LOG.add_message(f"Plan Local Gig: No suitable venues in {player.current_location.name}.")
                        else:
                            venue_map = {str(i+1): v for i,v in enumerate(suitable_venues)}
                            venue_disp = {k:f"{v.name} (Fee: ${getattr(v,'booking_fee',50)})" for k,v in venue_map.items()}
                            venue_disp["0"] = "Cancel"
                            chosen_venue_key = present_choices_curses(main_window, venue_disp, "Choose venue:")
                            main_window.clear(); main_window.box(); y_offset_gig=1
                            if chosen_venue_key and chosen_venue_key != "0" and chosen_venue_key in venue_map:
                                selected_venue = venue_map[chosen_venue_key]; booking_fee = getattr(selected_venue, 'booking_fee',50)
                                main_window.addstr(y_offset_gig,2,f"Booking: {selected_venue.name} (Fee: ${booking_fee})", curses.A_BOLD); y_offset_gig+=2
                                if player.money < booking_fee:
                                    main_window.addstr(y_offset_gig,2,f"Not enough money (need ${booking_fee}).")
                                    GAME_LOG.add_message(f"Plan Local Gig: Not enough money for {selected_venue.name} (Need ${booking_fee}).")
                                else:
                                    try:
                                        days_str = get_string_curses(main_window,y_offset_gig,2,"Days from now (7-28)? "); y_offset_gig+=1
                                        days_adv = int(days_str)
                                        if not (7<=days_adv<=28): raise ValueError("Must be 7-28 days.")

                                        songs_str = get_string_curses(main_window,y_offset_gig,2,f"#Songs (1-7, have {len(player.songs_written)})? "); y_offset_gig+=1
                                        num_songs = int(songs_str)
                                        if not (1<=num_songs<=7): raise ValueError("Setlist 1-7 songs.")
                                        if len(player.songs_written)<num_songs: raise ValueError(f"Not enough songs ({len(player.songs_written)}) for {num_songs} songs.")

                                        player.money-=booking_fee; adv_time_music_mgmt+=15
                                        gig_date = current_game_time.copy(); gig_date.advance_time(days_adv*24*60); gig_date.hour,gig_date.minute = 20,0
                                        ev_name = f"{player.name} Live at {selected_venue.name}"
                                        new_event = Event(name=ev_name,location=selected_venue,event_type="PLAYER_BOOKED_GIG", required_skills={"vocals":1,"stage_presence":1}, description="Self-organized gig.", is_player_organized=True)
                                        new_event.songs_required_count = num_songs
                                        selected_venue.add_event(new_event)
                                        gig_end = gig_date.copy(); gig_end.advance_time((num_songs*10)+30)
                                        player.schedule.add_event(gig_date,gig_end,ev_name,"Gig (Self-Booked)",details={"venue_id":selected_venue.venue_id,"event_id":new_event.name})
                                        main_window.addstr(y_offset_gig,2,f"Booked '{ev_name}' for {gig_date.get_time_string_for_schedule()}!"); y_offset_gig+=1
                                        main_window.addstr(y_offset_gig,2,f"Paid ${booking_fee}. Money: ${player.money}"); y_offset_gig+=1
                                        main_window.addstr(y_offset_gig,2,"Promote your gig for better turnout!")
                                        GAME_LOG.add_message(f"Booked player gig: {ev_name} for {gig_date.get_time_string_for_schedule()}. Paid ${booking_fee}.")
                                    except ValueError as e:
                                        main_window.addstr(y_offset_gig,2,f"Booking Error: {e}")
                                        GAME_LOG.add_message(f"Plan Local Gig: Booking error - {e}")
                                        if 'booking_fee' in locals() and player.money + booking_fee >= 0 : player.money+=booking_fee
                                    except Exception as e:
                                        main_window.addstr(y_offset_gig,2,f"Unexpected Error: {e}")
                                        GAME_LOG.add_message(f"Plan Local Gig: Unexpected error - {e}")
                                        if 'booking_fee' in locals() and player.money + booking_fee >= 0 : player.money+=booking_fee
                            else:
                                main_window.addstr(y_offset_gig,2,"Gig planning cancelled.")
                                GAME_LOG.add_message("Plan Local Gig: Cancelled at venue selection.")

                elif music_choice == "0": # Back to Phone Menu
                    music_management_active = False
                    adv_time = adv_time_music_mgmt
                    continue

                if music_choice in ["1","2","3"]:
                    main_window.addstr(main_window.getmaxyx()[0] - 2, 2, "Press any key...")
                    main_window.refresh()
                    main_window.getch()
                adv_time = adv_time_music_mgmt

            if music_choice == "4": # Check Reviews/Fan Mail
                main_window.addstr(1,2, "--- Reviews & Fan Mail ---", curses.A_BOLD)
                if not player.feedback_received:
                    main_window.addstr(3,2, "No feedback received yet.")
                else:
                    max_h, max_w = main_window.getmaxyx()
                    review_start_line = 3
                    for i, fb_item in enumerate(reversed(player.feedback_received)):
                        if review_start_line + 4 >= max_h -1:
                            main_window.addstr(review_start_line, 2, "--More--(press key)")
                            main_window.getch()
                            main_window.clear(); main_window.box()
                            main_window.addstr(1,2, "--- Reviews & Fan Mail (cont.) ---", curses.A_BOLD)
                            review_start_line = 3

                        main_window.addstr(review_start_line, 2, f"{'[UNREAD] ' if not fb_item.get('read') else ''}From: {fb_item['source']} (Song: '{fb_item['song_title']}')"[:max_w-4])
                        review_start_line += 1
                        main_window.addstr(review_start_line, 4, f"Date: {fb_item['date_generated'].get_time_string_for_schedule()}"[:max_w-6])
                        review_start_line += 1
                        main_window.addstr(review_start_line, 4, f"Quote: \"{fb_item['quote']}\""[:max_w-6])
                        review_start_line +=1
                        if fb_item.get('impact'):
                            main_window.addstr(review_start_line,4, f"Impact: {str(fb_item['impact'])}"[:max_w-6])
                            review_start_line+=1
                        if not fb_item.get('read'): fb_item['read'] = True
                        review_start_line +=1
                main_window.addstr(main_window.getmaxyx()[0] - 2, 2, "Press any key to continue...")
                main_window.refresh(); main_window.getch()
                adv_time_music_mgmt += 10

            if music_choice == "5": # View Charts
                main_window.addstr(1,2, "--- Current Music Charts ---", curses.A_BOLD)
                if not ACTIVE_CHARTS: main_window.addstr(3,2, "No music charts available.")
                else:
                    line_num = 3
                    for i, chart_obj in enumerate(ACTIVE_CHARTS):
                        if line_num + 2 + len(chart_obj.entries) >= main_window.getmaxyx()[0] -2:
                             main_window.addstr(line_num,2,"--More--(press key)"); main_window.getch(); main_window.clear();main_window.box(); line_num=1
                             main_window.addstr(line_num,2, "--- Charts (cont.) ---", curses.A_BOLD); line_num+=2
                        main_window.addstr(line_num, 2, f"{i+1}. {chart_obj.name}"); line_num+=1
                        chart_lines = str(chart_obj).split('\n')
                        for chart_line in chart_lines:
                            if line_num >= main_window.getmaxyx()[0]-2: break
                            main_window.addstr(line_num, 4, chart_line[:main_window.getmaxyx()[1]-6]); line_num+=1
                        line_num+=1
                main_window.addstr(main_window.getmaxyx()[0] - 2, 2, "Press any key..."); main_window.refresh(); main_window.getch()
                adv_time_music_mgmt += 5

            elif music_choice == "6": # View Label Offers
                main_window.addstr(1,2, "--- Record Label Offers ---", curses.A_BOLD)
                pending_offers = [o for o in player.active_label_offers if o.get("status") == "pending_player_decision" and current_game_time < o["expiry_date_obj"]]
                for o in player.active_label_offers:
                    if o.get("status") == "pending_player_decision" and current_game_time >= o["expiry_date_obj"]:
                        o["status"] = "expired"; GAME_LOG.add_message(f"Offer from {o['label_name']} expired.")

                if not pending_offers: main_window.addstr(3,2, "No active label offers.")
                else:
                    offer_map = {str(i+1): offer for i,offer in enumerate(pending_offers)}
                    offer_disp = {k: f"{v['label_name']} ({v['offer_type']}) - Adv: ${v['advance_payment']:,}, Exp: {v['expiry_date_obj'].get_time_string_for_schedule()}" for k,v in offer_map.items()}
                    offer_disp["0"] = "Back"
                    chosen_offer_key = present_choices_curses(main_window, offer_disp, "Select offer to view/respond:")
                    main_window.clear(); main_window.box()
                    if chosen_offer_key and chosen_offer_key != "0" and chosen_offer_key in offer_map:
                        chosen_offer = offer_map[chosen_offer_key]
                        main_window.addstr(1,2,f"Details for {chosen_offer['label_name']}:", curses.A_BOLD)
                        # TODO: Display full offer details here, paginated if necessary
                        main_window.addstr(3,2,f"Type: {chosen_offer['offer_type']}")
                        main_window.addstr(4,2,f"Advance: ${chosen_offer['advance_payment']:,}, Royalty: {chosen_offer['royalty_rate_player']*100:.0f}%")
                        main_window.addstr(5,2,f"Expires: {chosen_offer['expiry_date_obj'].get_time_string_for_schedule()}")

                        response_key = present_choices_curses(main_window, {"1":"Accept","2":"Decline","0":"Decide Later"}, "Your Decision?")
                        main_window.clear(); main_window.box()
                        if response_key == "1":
                            # Original acceptance logic is complex and involves history updates.
                            # This should be encapsulated or carefully called.
                            # For now, simplified message.
                            player.money += chosen_offer['advance_payment']
                            chosen_offer['status'] = "accepted"
                            # ... (rest of acceptance logic from original, ensuring GAME_LOG for messages) ...
                            main_window.addstr(1,2,f"Accepted offer from {chosen_offer['label_name']}!"); GAME_LOG.add_message(f"Accepted label offer: {chosen_offer['label_name']}")
                            adv_time_music_mgmt += 30
                        elif response_key == "2":
                            chosen_offer['status'] = "declined_by_player"
                            # ... (rest of decline logic) ...
                            main_window.addstr(1,2,f"Declined offer from {chosen_offer['label_name']}."); GAME_LOG.add_message(f"Declined label offer: {chosen_offer['label_name']}")
                            adv_time_music_mgmt += 15
                        else: main_window.addstr(1,2,"Decided to wait on the offer.")
                    else: main_window.addstr(1,2,"No offer selected or backed out.")
                main_window.addstr(main_window.getmaxyx()[0]-2,2,"Press any key..."); main_window.refresh(); main_window.getch()
                adv_time_music_mgmt += 5

            elif music_choice == "7": # View Released Songs
                main_window.addstr(1,2, "--- Your Released Music ---", curses.A_BOLD)
                released = [s for s in player.songs_written if s.is_released]
                if not released: main_window.addstr(3,2, "No music released yet.")
                else:
                    y_curr = 3; max_w = main_window.getmaxyx()[1]
                    for i, song_obj in enumerate(released):
                        if y_curr + 3 >= main_window.getmaxyx()[0]-2: main_window.addstr(y_curr,2,"--More--(key)");main_window.getch();main_window.clear();main_window.box();y_curr=1;main_window.addstr(y_curr,2,"--Released (cont.)--", curses.A_BOLD);y_curr+=2
                        main_window.addstr(y_curr,2,f"{i+1}. {str(song_obj)}"[:max_w-4]); y_curr+=1
                        # Chart info display logic here if needed
                main_window.addstr(main_window.getmaxyx()[0]-2,2,"Press any key..."); main_window.refresh(); main_window.getch()
                adv_time_music_mgmt +=10

            elif music_choice == "8": # View Current Label Deal
                main_window.addstr(1,2, "--- Current Label Deal ---", curses.A_BOLD)
                if player.signed_label_deal:
                    deal = player.signed_label_deal; y_curr=3; max_w = main_window.getmaxyx()[1]
                    # TODO: Paginate this properly if it gets too long
                    main_window.addstr(y_curr,2,f"Label: {deal['label_name']}"[:max_w-4]); y_curr+=1
                    main_window.addstr(y_curr,2,f"Type: {deal['offer_type']}"[:max_w-4]); y_curr+=1
                    # ... display all other deal terms, ensuring they fit ...
                else: main_window.addstr(3,2, "Not currently signed.")
                main_window.addstr(main_window.getmaxyx()[0]-2,2,"Press any key..."); main_window.refresh(); main_window.getch()
                adv_time_music_mgmt += 5

            elif music_choice == "0":
                music_management_active = False

            adv_time = adv_time_music_mgmt
            if not music_management_active: continue
            main_window.clear(); main_window.box()


        elif choice == "0": GAME_LOG.add_message("Putting phone away."); adv_time=1; break
        else: main_window.addstr(1,2,"Invalid phone option."); main_window.refresh(); main_window.getch()

        if adv_time > 0: advance_game_time(adv_time); update_npc_locations(current_game_time); process_time_based_player_needs(player, adv_time)

        if choice == "0": break

    main_window.clear(); main_window.box(); main_window.refresh()

def handle_travel_menu(player, main_window):
    while True:
        main_window.clear(); main_window.box()
        city_name = player.current_location.name if player.current_location else 'N/A'
        title = f"--- Travel Options --- (In {city_name}) --- {get_current_time_str()} ---"

        travel_opts_curses = {"1":f"Travel within {city_name}", "2":"Travel to another City", "0":"Back"}
        choice = present_choices_curses(main_window, travel_opts_curses, title)
        adv_time_local = 0

        main_window.clear(); main_window.box()

        if choice == "1": # Travel within city
            if not player.current_poi:
                main_window.addstr(3,2,"Not at a POI. Explore first to pick a starting point.");
                GAME_LOG.add_message("Travel: Attempted intra-city travel without being at a POI.")
            else:
                city_obj = player.current_location
                all_city_targets = city_obj.points_of_interest + city_obj.venues
                dest_opts_list = [t for t in all_city_targets if t.name != player.current_poi.name]

                if not dest_opts_list:
                    main_window.addstr(3,2,"No other POIs/Venues in this city location to travel to from here.")
                    GAME_LOG.add_message(f"Travel: No other POIs in {city_obj.name} from {player.current_poi.name}")
                else:
                    dest_map_curses = {str(i+1): t for i,t in enumerate(dest_opts_list)}
                    dest_disp_curses = {k: f"{v.name} ({getattr(v,'category', getattr(v,'venue_type','N/A'))})" for k,v in dest_map_curses.items()}
                    dest_disp_curses["0"] = "Cancel"

                    chosen_dest_key = present_choices_curses(main_window, dest_disp_curses, "Choose destination:")
                    main_window.clear(); main_window.box()

                    if chosen_dest_key and chosen_dest_key != "0" and chosen_dest_key in dest_map_curses:
                        chosen_dest_poi = dest_map_curses[chosen_dest_key]
                        orig_id = player.current_poi.poi_id if hasattr(player.current_poi,'poi_id') else getattr(player.current_poi,'venue_id',None)
                        dest_id = chosen_dest_poi.poi_id if hasattr(chosen_dest_poi,'poi_id') else getattr(chosen_dest_poi,'venue_id',None)

                        if not orig_id or not dest_id:
                            main_window.addstr(3,2,"Error determining route IDs."); GAME_LOG.add_message("Travel: Error with POI/Venue IDs for routing.")
                        else:
                            conn_key = frozenset({orig_id, dest_id})
                            modes_data = city_obj.intra_city_poi_connections.get(conn_key)
                            if not modes_data:
                                main_window.addstr(3,2,f"No direct route between {player.current_poi.name} and {chosen_dest_poi.name}.")
                                GAME_LOG.add_message(f"Travel: No direct route: {player.current_poi.name} to {chosen_dest_poi.name}")
                            else:
                                avail_modes_map_curses = {}
                                avail_modes_disp_curses = {}
                                c_num = 1
                                for mode_name, mode_info in modes_data.items():
                                    if mode_name=="bike" and not player.has_bike: continue
                                    avail_modes_disp_curses[str(c_num)] = f"{mode_name.capitalize()}: {mode_info['time']} mins, ${mode_info['cost']}"
                                    avail_modes_map_curses[str(c_num)] = (mode_name, mode_info)
                                    c_num+=1
                                avail_modes_disp_curses["0"] = "Cancel"

                                if not avail_modes_map_curses:
                                    main_window.addstr(3,2,"No travel modes available for this route (e.g., need bike?).")
                                    GAME_LOG.add_message(f"Travel: No modes for route {player.current_poi.name} to {chosen_dest_poi.name}")
                                else:
                                    mode_key = present_choices_curses(main_window, avail_modes_disp_curses, "Choose travel mode:")
                                    main_window.clear(); main_window.box()
                                    if mode_key and mode_key != "0" and mode_key in avail_modes_map_curses:
                                        mode_n, mode_d = avail_modes_map_curses[mode_key]
                                        if player.money < mode_d['cost']:
                                            main_window.addstr(3,2,f"Not enough money for {mode_n}. Need ${mode_d['cost']}.")
                                        elif player.get_current_gear_load() > player.get_current_gear_capacity(mode_n):
                                            main_window.addstr(3,2,f"Too much gear to carry via {mode_n}.")
                                        else:
                                            player.money -= mode_d['cost']
                                            GAME_LOG.add_message(f"Paid ${mode_d['cost']} for {mode_n} to {chosen_dest_poi.name}.")
                                            player.travel_within_city(chosen_dest_poi, mode_d['time'])
                                            adv_time_local = mode_d['time']
                                            main_window.addstr(3,2,f"Travelled to {chosen_dest_poi.name} by {mode_n}."); main_window.refresh(); curses.napms(1500)
                                            if adv_time_local > 0: advance_game_time(adv_time_local); update_npc_locations(current_game_time); process_time_based_player_needs(player, adv_time_local)
                                            return # Exit travel menu after successful travel
                                    else: main_window.addstr(3,2,"Travel mode selection cancelled.")
                    else: main_window.addstr(3,2,"Destination selection cancelled.")
            main_window.addstr(main_window.getmaxyx()[0]-2, 2, "Press any key..."); main_window.refresh(); main_window.getch()

        elif choice == "2": # Travel to another City
            if not player.current_poi or player.current_poi.category not in ["TRANSPORT_BUS", "TRANSPORT_AIRPORT"]:
                main_window.addstr(3,2, "Need to be at a Bus Station or Airport to travel to another city.")
                main_window.addstr(4,2, "Use 'Explore POI/Area' at a transport hub to buy tickets.")
                GAME_LOG.add_message("Travel: Attempted inter-city travel from non-transport POI.")
            else:
                main_window.addstr(3,2, "Use 'Explore current POI/Area' option from the main menu")
                main_window.addstr(4,2, f"at the {player.current_poi.name} to find departures and buy tickets.")
            main_window.addstr(main_window.getmaxyx()[0]-2, 2, "Press any key..."); main_window.refresh(); main_window.getch()

        elif choice == "0":
            GAME_LOG.add_message("Exited travel menu.")
            break
        else:
            main_window.addstr(3,2,"Invalid travel option selected."); main_window.refresh(); main_window.getch()

        # This time advancement is only for non-travel actions or cancelled travel within the travel menu loop
        if adv_time_local > 0: # Should only be non-zero if travel DIDN'T happen but some other action did.
             advance_game_time(adv_time_local); update_npc_locations(current_game_time); process_time_based_player_needs(player, adv_time_local)

    main_window.clear(); main_window.box(); main_window.refresh()

def pygame_main():
    ui = PygameUI()

    # Replace GAME_LOG with ui.add_log_message
    global GAME_LOG
    GAME_LOG = ui

    if not setup_world():
        # Pygame equivalent of showing an error and exiting
        print("World setup failed. Check log.")
        return

    GAME_LOG.add_log_message("Welcome to Music-Life Sim!")
    GAME_LOG.add_log_message("Ollama for NPCs: ensure it's running & model pulled (e.g., llama3).")

    # Pygame equivalent of get_string_curses
    player_name = "Player" # Placeholder, will need a pygame input box
    player = Player(player_name)
    hometown_loc = WORLD_MAP.get("Your Hometown")
    player_home_obj = get_poi_or_venue_by_id(PLAYER_HOME_POI_ID_GLOBAL) if PLAYER_HOME_POI_ID_GLOBAL else None
    if hometown_loc and player_home_obj:
        player.current_location = hometown_loc
        player.current_poi = player_home_obj
    else:
        print("Error setting start home.")
        return

    update_npc_locations(current_game_time)
    process_time_based_player_needs(player, 0)
    if GEAR_CATALOG.get("worn_acoustic_guitar"): player.add_gear(GEAR_CATALOG["worn_acoustic_guitar"])
    if GEAR_CATALOG.get("guitar_picks_assorted"): player.add_gear(GEAR_CATALOG["guitar_picks_assorted"])

    global LAST_CHART_UPDATE_DAY
    LAST_CHART_UPDATE_DAY = current_game_time.day

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if (current_game_time.day % 7 == 1) and (current_game_time.day != LAST_CHART_UPDATE_DAY):
            # ... (chart update logic remains the same) ...
            pass

        ui.clear_screen()
        ui.draw_hud(get_current_time_str(date_only=True), str(player.money), str(player.hair_length), str(player.beard_length))
        ui.draw_log()

        main_menu_opts = {
            "1": "Practice skill", "2": "Travel", "3": "Explore POI/Area",
            "4": "Check Gigs (City)", "5": "Prep Gig", "6": "Attempt Gig",
            "7": "Player Stats", "8": "Talk", "9": "Eat Food", "10": "Phone",
            "0": "Quit"
        }

        choice = ui.present_choices(main_menu_opts, f"What would {player.name} like to do?")

        if choice == "0":
            running = False

        # Handle other choices...

        ui.update_display()

    pygame.quit()

def main(): # Old main, effectively deprecated for Curses UI
    if not setup_world(): GAME_LOG.add_message("World setup failed. Exiting.") if GAME_LOG else print("World setup failed. Exiting."); return
    (GAME_LOG.add_message("Welcome to Music-Life Sim!\nOllama for NPCs: ensure it's running & model pulled (e.g., llama3).") if GAME_LOG
     else print("Welcome to Music-Life Sim!\nOllama for NPCs: ensure it's running & model pulled (e.g., llama3)."))
    player_name_main = input("Enter character's name: ")
    player = Player(player_name_main)
    hometown_loc = WORLD_MAP.get("Your Hometown")
    player_home_obj = get_poi_or_venue_by_id(PLAYER_HOME_POI_ID_GLOBAL) if PLAYER_HOME_POI_ID_GLOBAL else None
    if hometown_loc and player_home_obj:
        player.current_location = hometown_loc; player.current_poi = player_home_obj
    else: GAME_LOG.add_message("Error setting start home. Defaulting...") if GAME_LOG else print("Error setting start home. Defaulting...")
    update_npc_locations(current_game_time); process_time_based_player_needs(player,0)
    if GEAR_CATALOG.get("worn_acoustic_guitar"): player.add_gear(GEAR_CATALOG["worn_acoustic_guitar"])
    if GEAR_CATALOG.get("guitar_picks_assorted"): player.add_gear(GEAR_CATALOG["guitar_picks_assorted"])
    (GAME_LOG.add_message(f"\n--- {get_current_time_str()} ---") if GAME_LOG else print(f"\n--- {get_current_time_str()} ---"))
    (GAME_LOG.add_message(str(player)) if GAME_LOG else print(player))
    global LAST_CHART_UPDATE_DAY
    LAST_CHART_UPDATE_DAY = current_game_time.day
    while True:
        if (current_game_time.day % 7 == 1) and (current_game_time.day != LAST_CHART_UPDATE_DAY):
            if hasattr(player, 'songs_written'):
                for song_item in player.songs_written:
                    if hasattr(song_item, 'buzz_score'):
                        song_item.buzz_score = round(max(0, song_item.buzz_score * 0.7), 1)
                        if song_item.buzz_score < 0.1 : song_item.buzz_score = 0.0
            update_all_charts(player, current_game_time.copy())
            LAST_CHART_UPDATE_DAY = current_game_time.day
        main_menu_opts = {"1":"Practice skill", "2":"Travel", "3":"Explore POI/Area", "4":"Check Gigs (City)",
                          "5":"Prep Gig", "6":"Attempt Gig", "7":"Player Stats", "8":"Talk", "9":"Eat Food", "10":"Phone"}
        if player.has_manager or player.has_pr_manager: main_menu_opts["11"]="Staff Actions"
        main_menu_opts["00"]="Adv Time (1hr)"; main_menu_opts["0"]="Quit"
        choice = present_choices(main_menu_opts, f"What would {player.name} like to do?")
        if choice is None: continue
        adv_time_general = 0
        if choice == "1":
            skill = input("Skill to practice (vocals, guitar, stage_presence, songwriting)? ").lower()
            try: hrs = int(input(f"Hours for {skill}? ")); assert hrs > 0
            except: GAME_LOG.add_message("Invalid hours.") if GAME_LOG else print("Invalid hours."); continue
            player.practice_skill(skill, hrs); adv_time_general = hrs*60
        elif choice == "2": handle_travel_menu(player, main_window); continue # Modified to pass main_window
        elif choice == "3":
            poi = player.current_poi; loc = player.current_location
            GAME_LOG.add_message(f"\n--- Exploring {poi.name if poi else loc.name} ---\nDesc: {poi.description if poi else loc.description}") if GAME_LOG else print(f"\n--- Exploring {poi.name if poi else loc.name} ---\nDesc: {poi.description if poi else loc.description}")
            if poi:
                interactions = list(poi.interaction_options)
                if isinstance(poi, Venue) and any(e.is_active and (e.are_preparations_complete() or not e.preparation_tasks_required) and 16 <= current_game_time.hour <= 19 for e in poi.events_hosted):
                    if "Hold Pre-Show Autograph Signing (1 hour)" not in interactions: interactions.append("Hold Pre-Show Autograph Signing (1 hour)")
                if poi.category == "OFFICE_NEWS_AGENCY" and player.active_opportunities.get("interview_city_chronicle") == "pending_player_action":
                    if "Attend Scheduled Interview" not in interactions: interactions.append("Attend Scheduled Interview")
                if player.signed_label_deal and hasattr(poi, 'poi_id') and player.signed_label_deal.get('label_poi_id') == poi.poi_id:
                    deal = player.signed_label_deal
                    if "Meet with A&R Representative" not in interactions: interactions.append("Meet with A&R Representative")
                    if deal.get("music_video_budget_single", 0) > 0 and not deal.get("music_video_produced_for_deal", False):
                        if "Discuss Music Video Production" not in interactions: interactions.append(f"Discuss Music Video Production (Budget: ${deal['music_video_budget_single']:,})")
                    if deal.get("albums_remaining_on_commitment", 0) > 0:
                        if "Discuss Album Release with Label" not in interactions: interactions.append("Discuss Album Release with Label")
                if interactions:
                    idx_choice_str = present_choices(interactions, f"Actions at {poi.name}:")
                    if idx_choice_str and idx_choice_str.isdigit():
                        chosen_text = interactions[int(idx_choice_str)-1]; GAME_LOG.add_message(f"Chose: {chosen_text}") if GAME_LOG else print(f"Chose: {chosen_text}")
                        action_taken_custom_time = False
                        if chosen_text == "Hold Pre-Show Autograph Signing (1 hour)":
                            from game.interactions import handle_autograph_interaction
                            outcome = handle_autograph_interaction(player, NPC(f"pgfan_temp","Generated Fan","adoring_fan"), "pre_gig_signing")
                            adv_time_general = outcome.get("minutes_passed", 60); action_taken_custom_time = True
                        elif poi.category == "SHOP_MUSIC" and chosen_text == "Browse items for sale":
                            if poi.shop_inventory_item_ids:
                                display = []; item_map = {}; idx=1
                                for item_id in poi.shop_inventory_item_ids:
                                    item=GEAR_CATALOG.get(item_id)
                                    if item: display.append(f"{item.name} - ${item.cost} (Size: {item.size})"); item_map[str(idx)]=item; idx+=1
                                if not display: GAME_LOG.add_message("Out of stock.") if GAME_LOG else print("Out of stock.")
                                else:
                                    buy_key = present_choices(display, f"Items at {poi.name}: (0 to cancel)")
                                    if buy_key and buy_key!="0" and buy_key in item_map:
                                        sel_item=item_map[buy_key]
                                        if player.money>=sel_item.cost:
                                            if player.can_carry_gear(sel_item): player.money-=sel_item.cost; player.add_gear(sel_item); GAME_LOG.add_message(f"Money: ${player.money}") if GAME_LOG else print(f"Money: ${player.money}")
                                            else: GAME_LOG.add_message(f"Can't carry {sel_item.name}.") if GAME_LOG else print(f"Can't carry {sel_item.name}.")
                                        else: GAME_LOG.add_message(f"Not enough money for {sel_item.name}.") if GAME_LOG else print(f"Not enough money for {sel_item.name}.")
                                    elif buy_key=="0": GAME_LOG.add_message("Cancelled purchase.") if GAME_LOG else print("Cancelled purchase.")
                            else: GAME_LOG.add_message("Nothing for sale currently.") if GAME_LOG else print("Nothing for sale currently.")
                            adv_time_general = 15; action_taken_custom_time = True
                        elif poi.category in ["TRANSPORT_BUS", "TRANSPORT_AIRPORT"] and chosen_text == "View Departures & Buy Tickets":
                            connections = loc.travel_connections
                            if not connections: GAME_LOG.add_message(f"No inter-city routes from {loc.name}.") if GAME_LOG else print(f"No inter-city routes from {loc.name}.")
                            else:
                                dest_opts_dict = {}
                                conn_map = {}
                                for i, (dest_name, details) in enumerate(connections.items()):
                                    mode = "Bus" if poi.category == "TRANSPORT_BUS" else "Plane"
                                    dest_opts_dict[str(i+1)] = f"To {dest_name} by {mode} (Cost: ${details['cost']}, Time: {details['time_hours']}h)"
                                    conn_map[str(i+1)] = (dest_name, details)
                                dest_opts_dict["0"] = "Cancel"
                                dest_key = present_choices(dest_opts_dict, f"Departures from {poi.name}:")
                                if dest_key and dest_key != "0" and dest_key in conn_map:
                                    chosen_dest_name_from_menu, chosen_travel_details = conn_map[dest_key]
                                    if input(f"Travel to {chosen_dest_name_from_menu} for ${chosen_travel_details['cost']} ({chosen_travel_details['time_hours']}h)? (y/n) > ").lower()=='y':
                                        if player.money >= chosen_travel_details['cost']:
                                            cost_of_travel = chosen_travel_details['cost']
                                            player.money -= cost_of_travel
                                            if player.current_tour_id and player.current_tour_id in player.tour_ledgers:
                                                tour_ledger = player.tour_ledgers[player.current_tour_id]
                                                if tour_ledger["status"] == "ongoing":
                                                    next_tour_gig_city = None
                                                    for gig_detail_item in tour_ledger.get("gigs_details", []):
                                                        if not gig_detail_item.get("performed", False):
                                                            if gig_detail_item["city_name"] == chosen_dest_name_from_menu:
                                                                next_tour_gig_city = gig_detail_item["city_name"]; break
                                                    if next_tour_gig_city:
                                                        tour_ledger["expenses"] += cost_of_travel
                                                        GAME_LOG.add_message(f"LOG: Travel cost ${cost_of_travel} for '{chosen_dest_name_from_menu}' added to expenses for tour '{tour_ledger['name']}'.") if GAME_LOG else print(f"LOG: Travel cost ${cost_of_travel} for '{chosen_dest_name_from_menu}' added to expenses for tour '{tour_ledger['name']}'.")
                                            dest_loc_obj = WORLD_MAP.get(chosen_dest_name_from_menu)
                                            if dest_loc_obj:
                                                travel_duration_hours = chosen_travel_details['time_hours']
                                                travel_duration_minutes = travel_duration_hours * 60
                                                travel_start_time = current_game_time.copy()
                                                travel_end_time = current_game_time.copy(); travel_end_time.advance_time(travel_duration_minutes)
                                                player.schedule.add_event(start_time=travel_start_time, end_time=travel_end_time, description=f"Travel: {loc.name} to {chosen_dest_name_from_menu}", category="Travel", details={"from_city_id": loc.id if hasattr(loc,'id') else loc.name, "to_city_id": dest_loc_obj.id if hasattr(dest_loc_obj,'id') else dest_loc_obj.name, "transport_poi_id": poi.poi_id})
                                                player.travel(dest_loc_obj, travel_duration_hours)
                                                adv_time_general = travel_duration_minutes; action_taken_custom_time = True
                                                GAME_LOG.add_message(f"Ticket bought. Travelled to {chosen_dest_name_from_menu}.") if GAME_LOG else print(f"Ticket bought. Travelled to {chosen_dest_name_from_menu}.")
                                            else: GAME_LOG.add_message(f"Error: Dest city '{chosen_dest_name_from_menu}' not found.") if GAME_LOG else print(f"Error: Dest city '{chosen_dest_name_from_menu}' not found."); player.money += cost_of_travel
                                        else: GAME_LOG.add_message(f"Not enough money. Need ${chosen_travel_details['cost']}.") if GAME_LOG else print(f"Not enough money. Need ${chosen_travel_details['cost']}.")
                                    else: GAME_LOG.add_message("Travel cancelled.") if GAME_LOG else print("Travel cancelled.")
                            adv_time_general = 20 if not action_taken_custom_time else adv_time_general; action_taken_custom_time=True
                        elif (poi.category == "HOME" and chosen_text == "Rest (8 hours)") or \
                             (poi.category == "ACCOMMODATION_CHEAP" and chosen_text.startswith("Sleep")):
                            hours_to_rest = 8; can_sleep_here = False
                            if poi.category == "HOME": can_sleep_here = True
                            elif poi.category == "ACCOMMODATION_CHEAP":
                                if player.rented_accommodation_info and player.rented_accommodation_info["poi_id"] == poi.poi_id: can_sleep_here = True
                                else: GAME_LOG.add_message("You haven't rented a room here or it expired.") if GAME_LOG else print("You haven't rented a room here or it expired.")
                            if can_sleep_here:
                                comfort_eff=0; hunger_eff=0
                                if player.comfort < 25: comfort_eff=-0.2
                                elif player.comfort < 50: comfort_eff=-0.1
                                if player.hunger > 75: hunger_eff=-0.2
                                elif player.hunger > 50: hunger_eff=-0.1
                                eff_rest_q = max(0.05, poi.rest_quality + comfort_eff + hunger_eff)
                                energy_g = int(hours_to_rest*10*eff_rest_q); stress_chg = int(hours_to_rest*poi.stress_modifier_hourly)
                                if poi.category == "HOME": player.homesickness=max(0,player.homesickness-(hours_to_rest*10)); player.comfort=min(100,player.comfort+(hours_to_rest*2))
                                player.energy=min(100,player.energy+energy_g); player.stress=max(0,player.stress+stress_chg)
                                GAME_LOG.add_message(f"Rested for {hours_to_rest}h. Energy: {player.energy}, Stress: {player.stress}.") if GAME_LOG else print(f"Rested for {hours_to_rest}h. Energy: {player.energy}, Stress: {player.stress}.")
                                if poi.category == "ACCOMMODATION_CHEAP": player.rented_accommodation_info = None
                                adv_time_general = hours_to_rest*60; action_taken_custom_time = True
                        elif poi.category == "ACCOMMODATION_CHEAP" and chosen_text.startswith("Rent Room"):
                            try:
                                rent_cost = int(chosen_text.split('$')[1].split('/')[0])
                                if player.money>=rent_cost:
                                    player.money-=rent_cost;
                                    co_time=current_game_time.copy(); co_time.advance_time(24*60)
                                    player.rented_accommodation_info = {"poi_id":poi.poi_id, "checkout_time_obj":co_time}
                                    GAME_LOG.add_message(f"Rented room for ${rent_cost} until {co_time}. Money: ${player.money}.") if GAME_LOG else print(f"Rented room for ${rent_cost} until {co_time}. Money: ${player.money}.")
                                else: GAME_LOG.add_message(f"Not enough money. Need ${rent_cost}.") if GAME_LOG else print(f"Not enough money. Need ${rent_cost}.")
                            except: GAME_LOG.add_message("Error parsing rent cost.") if GAME_LOG else print("Error parsing rent cost.")
                            adv_time_general = 10; action_taken_custom_time = True
                        elif poi.category == "HOME" and chosen_text == "Write a new song":
                            GAME_LOG.add_message("\n--- Write a New Song ---") if GAME_LOG else print("\n--- Write a New Song ---")
                            song_title = input("Enter a title for your new song: ")
                            if not song_title.strip():
                                GAME_LOG.add_message("Songwriting cancelled. You need a title.") if GAME_LOG else print("Songwriting cancelled. You need a title.")
                                adv_time_general = 5
                            else:
                                songwriting_skill = player.skills.get("songwriting", 0)
                                base_min = 0.1; base_max = 0.7
                                skill_bonus_range = min(0.25, (songwriting_skill / 10) * 0.05)
                                final_min = min(base_min + skill_bonus_range, 0.8)
                                final_max = min(base_max + skill_bonus_range, 1.0)
                                originality = round(random.uniform(final_min, final_max), 2)
                                catchiness = round(random.uniform(final_min, final_max), 2)
                                lyrical_depth = round(random.uniform(final_min, final_max), 2)
                                music_complexity = round(random.uniform(final_min, final_max), 2)
                                available_genres = ["Indie", "Rock", "Pop", "Folk", "Blues", "Electronic"]
                                genre_choices = {str(i+1): g for i, g in enumerate(available_genres)}
                                genre_choices["0"] = "Cancel / Default to Indie"
                                GAME_LOG.add_message("\nChoose a genre for your song:") if GAME_LOG else print("\nChoose a genre for your song:")
                                genre_choice_key = present_choices(genre_choices, "Select Genre:")
                                song_genre = "Indie"
                                if genre_choice_key and genre_choice_key != "0" and genre_choice_key in genre_choices: song_genre = genre_choices[genre_choice_key]
                                elif genre_choice_key == "0": GAME_LOG.add_message("Defaulting genre to Indie.") if GAME_LOG else print("Defaulting genre to Indie.")
                                else: GAME_LOG.add_message("Invalid genre choice, defaulting to Indie.") if GAME_LOG else print("Invalid genre choice, defaulting to Indie.")
                                new_song = Song(title=song_title, author=player.name, genre=song_genre, originality=originality, catchiness=catchiness, lyrical_depth=lyrical_depth, music_complexity=music_complexity)
                                player.songs_written.append(new_song)
                                songwriting_time_minutes = random.randint(120, 300)
                                skill_gain_factor = songwriting_time_minutes / 60.0
                                player.skills["songwriting"] = round(player.skills.get("songwriting", 0) + (0.15 * skill_gain_factor) + (new_song.song_quality * 0.1), 2)
                                player.energy = max(0, player.energy - random.randint(20, 40))
                                player.stress = max(0, player.stress - random.randint(0,10) + int(5 * (1-new_song.song_quality)))
                                player.comfort = min(100, player.comfort + random.randint(0,10))
                                GAME_LOG.add_message(f"\nYou finished writing a new song:\n  {new_song}") if GAME_LOG else print(f"\nYou finished writing a new song:\n  {new_song}")
                                GAME_LOG.add_message(f"It took you {songwriting_time_minutes // 60}h {songwriting_time_minutes % 60}m. Your songwriting skill is now {player.skills['songwriting']:.2f}.") if GAME_LOG else print(f"It took you {songwriting_time_minutes // 60}h {songwriting_time_minutes % 60}m. Your songwriting skill is now {player.skills['songwriting']:.2f}.")
                                GAME_LOG.add_message(f"Energy: {player.energy}, Stress: {player.stress}, Comfort: {player.comfort}") if GAME_LOG else print(f"Energy: {player.energy}, Stress: {player.stress}, Comfort: {player.comfort}")
                                adv_time_general = songwriting_time_minutes
                            action_taken_custom_time = True
                        elif poi.category == "STUDIO_RECORDING" and chosen_text == "Book recording session":
                            studio_hourly_rate = getattr(poi, 'hourly_rate', 50)
                            studio_quality = getattr(poi, 'studio_quality', 0.5)
                            unrecorded_songs = [s for s in player.songs_written if not s.is_recorded]
                            if not unrecorded_songs: GAME_LOG.add_message("You have no unrecorded songs to work on!") if GAME_LOG else print("You have no unrecorded songs to work on!"); adv_time_general = 5
                            else:
                                GAME_LOG.add_message("Which song to record?") if GAME_LOG else print("Which song to record?"); song_to_record_choices = {str(i+1): s for i,s in enumerate(unrecorded_songs)}
                                song_to_record_display = [f"{s.title} (Q: {s.song_quality:.2f})" for s in unrecorded_songs]
                                song_key = present_choices(song_to_record_display, "Choose song (0 to cancel):")
                                if song_key and song_key != "0" and song_key in song_to_record_choices:
                                    song_to_record = song_to_record_choices[song_key]
                                    try:
                                        rec_hours_input = input(f"Hours for '{song_to_record.title}'? (${studio_hourly_rate}/hr, StudioQ: {studio_quality*100:.0f}%): ")
                                        if not rec_hours_input.isdigit() or int(rec_hours_input) <=0: GAME_LOG.add_message("Invalid hours.") if GAME_LOG else print("Invalid hours."); raise ValueError
                                        rec_hours = int(rec_hours_input)
                                        rec_cost = rec_hours * studio_hourly_rate
                                        if player.money >= rec_cost:
                                            player.money -= rec_cost; rec_mins = rec_hours*60
                                            rec_start = current_game_time.copy(); rec_end = rec_start.copy(); rec_end.advance_time(rec_mins)
                                            player.schedule.add_event(rec_start,rec_end,f"Recording '{song_to_record.title}' at {poi.name}","Recording",details={"poi_id":poi.poi_id,"song_id":song_to_record.song_id,"cost":rec_cost,"hours":rec_hours})
                                            base_rec_q = studio_quality * 0.6
                                            perf_skill_avg = (player.skills.get("vocals",0) + player.skills.get("guitar",0)) / 20.0
                                            base_rec_q += perf_skill_avg * 0.3
                                            base_rec_q += random.uniform(-0.1, 0.1)
                                            final_rec_quality = round(max(0.1, min(1.0, base_rec_q + (song_to_record.song_quality * 0.1))), 2)
                                            song_to_record.mark_as_recorded(final_rec_quality)
                                            GAME_LOG.add_message(f"Recorded '{song_to_record.title}' (RecQ: {final_rec_quality:.2f}). Cost ${rec_cost}. Money: ${player.money}") if GAME_LOG else print(f"Recorded '{song_to_record.title}' (RecQ: {final_rec_quality:.2f}). Cost ${rec_cost}. Money: ${player.money}")
                                            adv_time_general = rec_mins
                                        else: GAME_LOG.add_message(f"Not enough money. Need ${rec_cost}.") if GAME_LOG else print(f"Not enough money. Need ${rec_cost}.")
                                    except ValueError: GAME_LOG.add_message("Recording cancelled.") if GAME_LOG else print("Recording cancelled.")
                                else: GAME_LOG.add_message("Recording cancelled.") if GAME_LOG else print("Recording cancelled.")
                            action_taken_custom_time = True
                        elif poi.category == "REHEARSAL_STUDIO" and chosen_text.startswith("Book Rehearsal Slot"): action_taken_custom_time = True
                        elif poi.category == "OFFICE_RECORD_LABEL" and chosen_text.startswith("Submit Demo"):
                            GAME_LOG.add_message("\n--- Submit Demo to Record Label ---") if GAME_LOG else print("\n--- Submit Demo to Record Label ---")
                            adv_time_general = 10; action_taken_custom_time = True
                            if player.fame < getattr(poi, 'min_fame_to_submit', 0): GAME_LOG.add_message(f"{poi.name} isn't interested in demos from artists at your current level of fame (Need {getattr(poi, 'min_fame_to_submit', 0)} fame).") if GAME_LOG else print(f"{poi.name} isn't interested in demos from artists at your current level of fame (Need {getattr(poi, 'min_fame_to_submit', 0)} fame).")
                            elif not player.songs_written: GAME_LOG.add_message("You have no songs to create a demo from!") if GAME_LOG else print("You have no songs to create a demo from!")
                            else:
                                recorded_songs = [s for s in player.songs_written if s.is_recorded]
                                if not recorded_songs: GAME_LOG.add_message("You have songs, but none are recorded. A demo needs a recording.") if GAME_LOG else print("You have songs, but none are recorded. A demo needs a recording.")
                                else:
                                    GAME_LOG.add_message("Select a recorded song for your demo:") if GAME_LOG else print("Select a recorded song for your demo:")
                                    song_choices_dict = {str(i+1): song for i, song in enumerate(recorded_songs)}
                                    song_display_list = [f"{s.title} (Genre: {s.genre}, CompQ: {s.song_quality:.2f}, RecQ: {s.recording_quality:.2f})" for s in recorded_songs]
                                    chosen_song_key = present_choices(song_display_list, "Choose song for demo (0 to cancel):")
                                    if chosen_song_key and chosen_song_key != "0":
                                        chosen_song_idx = int(chosen_song_key) -1
                                        if 0 <= chosen_song_idx < len(recorded_songs):
                                            chosen_song = recorded_songs[chosen_song_idx]; label_poi = poi
                                            GAME_LOG.add_message(f"You submit your demo of '{chosen_song.title}' to {label_poi.name}.") if GAME_LOG else print(f"You submit your demo of '{chosen_song.title}' to {label_poi.name}.")
                                            adv_time_general = 60
                                            success_score = chosen_song.song_quality * 35 + chosen_song.recording_quality * 35 + min(30, player.fame / 5) + getattr(label_poi, 'player_interest_score', 0.0) * 0.25
                                            genre_match_bonus = 0
                                            if label_poi.genres_preferred and chosen_song.genre in label_poi.genres_preferred: genre_match_bonus = 20
                                            elif not label_poi.genres_preferred: genre_match_bonus = 5
                                            success_score += genre_match_bonus; outcome_roll = random.randint(0, 100)
                                            GAME_LOG.add_message(f"(Debug: Score: {success_score:.1f}, Roll: {outcome_roll})") if GAME_LOG else print(f"(Debug: Score: {success_score:.1f}, Roll: {outcome_roll})")
                                            if success_score > outcome_roll + 50 :
                                                GAME_LOG.add_message(f"{label_poi.name} is very impressed! \"This is great stuff, {player.name}! We need to talk. My office, tomorrow?\"") if GAME_LOG else print(f"{label_poi.name} is very impressed! \"This is great stuff, {player.name}! We need to talk. My office, tomorrow?\"")
                                                player.fame += 25
                                                if hasattr(label_poi, 'player_interest_score'): label_poi.player_interest_score = min(100, label_poi.player_interest_score + 10)
                                            elif success_score > outcome_roll + 20:
                                                GAME_LOG.add_message(f"{label_poi.name} likes what they hear. \"Interesting... we'll be in touch if something opens up.\"") if GAME_LOG else print(f"{label_poi.name} likes what they hear. \"Interesting... we'll be in touch if something opens up.\"")
                                                player.fame += 10
                                            elif success_score > outcome_roll - 20:
                                                 GAME_LOG.add_message(f"{label_poi.name} listens politely. \"Thanks for the submission. We'll keep it on file.\"") if GAME_LOG else print(f"{label_poi.name} listens politely. \"Thanks for the submission. We'll keep it on file.\"")
                                                 player.fame += 2
                                            else: GAME_LOG.add_message(f"{label_poi.name} doesn't seem too interested. \"Uh, yeah, thanks. We get a lot of these.\"") if GAME_LOG else print(f"{label_poi.name} doesn't seem too interested. \"Uh, yeah, thanks. We get a lot of these.\"")
                                        else: GAME_LOG.add_message("Invalid song selection for demo.") if GAME_LOG else print("Invalid song selection for demo.")
                                    else: GAME_LOG.add_message("Demo submission cancelled.") if GAME_LOG else print("Demo submission cancelled.")
                            action_taken_custom_time = True
                        elif poi.category == "SHOP_MUSIC" and chosen_text == "Repair Gear": GAME_LOG.add_message("Repair Gear logic TBD.") if GAME_LOG else print("Repair Gear logic TBD."); adv_time_general = 45; action_taken_custom_time = True
                        elif poi.category == "SHOP_FOOD" and chosen_text == "Buy Food Items": GAME_LOG.add_message("Buy Food (Grocery) logic TBD.") if GAME_LOG else print("Buy Food (Grocery) logic TBD."); adv_time_general = 10; action_taken_custom_time = True
                        elif poi.category == "FOOD_FASTFOOD":
                            selected_menu_item_data=None
                            for mi in poi.menu_items:
                                if mi["display_text"] == chosen_text: selected_menu_item_data=mi; break
                            if selected_menu_item_data:
                                cost=selected_menu_item_data["cost"]; eff=selected_menu_item_data["effects"]
                                if player.money>=cost:
                                    player.money-=cost; player.hunger=max(0,player.hunger+eff.get("hunger",0)); player.energy=min(100,player.energy+eff.get("energy",0)); player.comfort=min(100,max(0,player.comfort+eff.get("comfort",0)))
                                    GAME_LOG.add_message(f"Consumed {GEAR_CATALOG.get(selected_menu_item_data['item_id']).name if GEAR_CATALOG.get(selected_menu_item_data['item_id']) else 'food'}. Stats updated.") if GAME_LOG else print(f"Consumed {GEAR_CATALOG.get(selected_menu_item_data['item_id']).name if GEAR_CATALOG.get(selected_menu_item_data['item_id']) else 'food'}. Stats updated.")
                                else: GAME_LOG.add_message(f"Not enough money for {chosen_text}.") if GAME_LOG else print(f"Not enough money for {chosen_text}.")
                            else: GAME_LOG.add_message(f"Action '{chosen_text}' unclear at fast food.") if GAME_LOG else print(f"Action '{chosen_text}' unclear at fast food.")
                            adv_time_general = 20; action_taken_custom_time = True
                        elif poi.category == "OFFICE_NEWS_AGENCY" and chosen_text == "Attend Scheduled Interview": action_taken_custom_time = True
                        elif poi.category == "OFFICE_PR_AGENCY" and chosen_text == "Inquire about PR representation": action_taken_custom_time = True
                        elif poi.category == "SHOP_BARBER": action_taken_custom_time = True
                        elif chosen_text == "Propose Album to Label":
                            GAME_LOG.add_message("\n--- Propose Album to Label ---") if GAME_LOG else print("\n--- Propose Album to Label ---")
                            if player.signed_label_deal and player.signed_label_deal.get('label_poi_id') == poi.poi_id:
                                GAME_LOG.add_message(f"You discuss your upcoming album plans with {player.signed_label_deal['label_name']}.") if GAME_LOG else print(f"You discuss your upcoming album plans with {player.signed_label_deal['label_name']}.")
                                relationship_score = player.signed_label_deal.get('label_relationship_score', 50)
                                if relationship_score > 70: GAME_LOG.add_message("They seem enthusiastic and offer some minor positive suggestions.") if GAME_LOG else print("They seem enthusiastic and offer some minor positive suggestions.")
                                elif relationship_score > 40: GAME_LOG.add_message("They listen and nod, saying they'll consider your ideas for the album direction.") if GAME_LOG else print("They listen and nod, saying they'll consider your ideas for the album direction.")
                                else: GAME_LOG.add_message("They seem a bit skeptical but agree to review any material you submit.") if GAME_LOG else print("They seem a bit skeptical but agree to review any material you submit.")
                                GAME_LOG.add_message("(Detailed album proposal mechanics and song review to be implemented later.)") if GAME_LOG else print("(Detailed album proposal mechanics and song review to be implemented later.)")
                                adv_time_general = 60
                            else: GAME_LOG.add_message("You need to be signed to this label to propose an album.") if GAME_LOG else print("You need to be signed to this label to propose an album."); adv_time_general = 5
                            action_taken_custom_time = True
                        elif chosen_text == "Meet with A&R Representative":
                            GAME_LOG.add_message("\n--- Meet with A&R Representative ---") if GAME_LOG else print("\n--- Meet with A&R Representative ---")
                            if player.signed_label_deal and player.signed_label_deal.get('label_poi_id') == poi.poi_id:
                                deal = player.signed_label_deal
                                GAME_LOG.add_message(f"You sit down with an A&R representative from {deal['label_name']}.") if GAME_LOG else print(f"You sit down with an A&R representative from {deal['label_name']}.")
                                adv_time_general = 45; action_taken_custom_time = True
                                GAME_LOG.add_message("\nTopics of Discussion:") if GAME_LOG else print("\nTopics of Discussion:")
                                meeting_options = {"1": "Discuss progress on current objectives", "2": "Discuss general label relationship", "0": "End meeting"}
                                while True:
                                    meeting_choice = present_choices(meeting_options, "What to discuss?")
                                    if meeting_choice == "0": GAME_LOG.add_message("You conclude the meeting.") if GAME_LOG else print("You conclude the meeting."); break
                                    if meeting_choice == "1":
                                        GAME_LOG.add_message("\n--- Current Label Objectives ---") if GAME_LOG else print("\n--- Current Label Objectives ---")
                                        if deal.get('objectives'):
                                            for i, obj_item in enumerate(deal['objectives']): GAME_LOG.add_message(f"  {i+1}. {obj_item}") if GAME_LOG else print(f"  {i+1}. {obj_item}")
                                            GAME_LOG.add_message("(Objective tracking and completion status TBD)") if GAME_LOG else print("(Objective tracking and completion status TBD)")
                                        else: GAME_LOG.add_message("No specific objectives currently assigned.") if GAME_LOG else print("No specific objectives currently assigned.")
                                        if deal['label_relationship_score'] < 40 : GAME_LOG.add_message("The rep seems concerned about progress.") if GAME_LOG else print("The rep seems concerned about progress."); deal['label_relationship_score'] = max(0, deal['label_relationship_score'] - 2)
                                        elif deal['label_relationship_score'] > 70: GAME_LOG.add_message("The rep is pleased with your proactive approach.") if GAME_LOG else print("The rep is pleased with your proactive approach."); deal['label_relationship_score'] = min(100, deal['label_relationship_score'] + 2)
                                        else: GAME_LOG.add_message("The rep nods and takes notes.") if GAME_LOG else print("The rep nods and takes notes.")
                                        adv_time_general += 15
                                    elif meeting_choice == "2":
                                        GAME_LOG.add_message("\n--- Label Relationship ---") if GAME_LOG else print("\n--- Label Relationship ---")
                                        GAME_LOG.add_message(f"Your current standing with the label is: {deal['label_relationship_score']}/100.") if GAME_LOG else print(f"Your current standing with the label is: {deal['label_relationship_score']}/100.")
                                        if deal['label_relationship_score'] > 80: GAME_LOG.add_message("They praise your recent work and commitment. Things are excellent!") if GAME_LOG else print("They praise your recent work and commitment. Things are excellent!"); deal['label_relationship_score'] = min(100, deal['label_relationship_score'] + 3)
                                        elif deal['label_relationship_score'] > 60: GAME_LOG.add_message("The relationship is positive. They appreciate your efforts.") if GAME_LOG else print("The relationship is positive. They appreciate your efforts."); deal['label_relationship_score'] = min(100, deal['label_relationship_score'] + 1)
                                        elif deal['label_relationship_score'] > 40: GAME_LOG.add_message("Things are okay. They expect continued dedication.") if GAME_LOG else print("Things are okay. They expect continued dedication.")
                                        elif deal['label_relationship_score'] > 20: GAME_LOG.add_message("There's some tension. They remind you of their expectations.") if GAME_LOG else print("There's some tension. They remind you of their expectations."); deal['label_relationship_score'] = max(0, deal['label_relationship_score'] - 3)
                                        else: GAME_LOG.add_message("The relationship is strained. The rep expresses clear disappointment.") if GAME_LOG else print("The relationship is strained. The rep expresses clear disappointment."); deal['label_relationship_score'] = max(0, deal['label_relationship_score'] - 5)
                                        GAME_LOG.add_message(f"New relationship score: {deal['label_relationship_score']}/100.") if GAME_LOG else print(f"New relationship score: {deal['label_relationship_score']}/100.")
                                        adv_time_general += 15
                                    if adv_time_general >= 120: GAME_LOG.add_message("The A&R rep indicates the meeting needs to wrap up.") if GAME_LOG else print("The A&R rep indicates the meeting needs to wrap up."); break
                            else: GAME_LOG.add_message("You need to be signed to this label for a formal meeting.") if GAME_LOG else print("You need to be signed to this label for a formal meeting."); adv_time_general = 5
                            action_taken_custom_time = True
                        elif chosen_text.startswith("Discuss Music Video Production"):
                            GAME_LOG.add_message("\n--- Music Video Production ---") if GAME_LOG else print("\n--- Music Video Production ---")
                            if player.signed_label_deal and player.signed_label_deal.get('label_poi_id') == poi.poi_id and player.signed_label_deal.get("music_video_budget_single", 0) > 0 and player.signed_label_deal.get("music_video_produced_for_deal", False) is False:
                                deal = player.signed_label_deal; budget = deal['music_video_budget_single']
                                GAME_LOG.add_message(f"The label, {deal['label_name']}, is ready to fund a music video with a budget of ${budget:,}.") if GAME_LOG else print(f"The label, {deal['label_name']}, is ready to fund a music video with a budget of ${budget:,}.")
                                released_songs = [s for s in player.songs_written if s.is_released and not s.has_music_video]
                                if not released_songs: GAME_LOG.add_message("You have no released songs that don't already have a music video.") if GAME_LOG else print("You have no released songs that don't already have a music video."); adv_time_general = 10
                                else:
                                    GAME_LOG.add_message("Select a song for the music video:") if GAME_LOG else print("Select a song for the music video:")
                                    song_choices_dict = {str(i+1): song for i, song in enumerate(released_songs)}
                                    song_display_list = [f"{s.title} (Quality: {s.song_quality:.2f}, Buzz: {s.buzz_score:.1f})" for s in released_songs]
                                    chosen_song_key = present_choices(song_display_list, "Choose song (0 to cancel):")
                                    if chosen_song_key and chosen_song_key != "0" and chosen_song_key in song_choices_dict:
                                        selected_song = song_choices_dict[chosen_song_key]
                                        if input(f"Produce music video for '{selected_song.title}' using the full budget of ${budget:,}? (This will take ~2 weeks) (y/n) > ").lower() == 'y':
                                            adv_time_general = 14 * 24 * 60; action_taken_custom_time = True
                                            base_quality = 0.2 + (budget / 10000) * 0.3 + (player.fame / 200) * 0.2 + selected_song.song_quality * 0.3
                                            video_quality = round(max(0.1, min(1.0, base_quality + random.uniform(-0.1, 0.1))), 2)
                                            selected_song.has_music_video = True; selected_song.music_video_quality = video_quality
                                            buzz_increase = video_quality * random.randint(30, 60)
                                            selected_song.buzz_score = min(100, selected_song.buzz_score + buzz_increase)
                                            player.signed_label_deal["music_video_produced_for_deal"] = True
                                            player.signed_label_deal["music_video_budget_single"] = 0
                                            GAME_LOG.add_message(f"\nMusic video for '{selected_song.title}' is complete!") if GAME_LOG else print(f"\nMusic video for '{selected_song.title}' is complete!")
                                            GAME_LOG.add_message(f"  Video Quality: {video_quality*100:.0f}/100") if GAME_LOG else print(f"  Video Quality: {video_quality*100:.0f}/100")
                                            GAME_LOG.add_message(f"  Song Buzz increased by {buzz_increase:.1f} to {selected_song.buzz_score:.1f}!") if GAME_LOG else print(f"  Song Buzz increased by {buzz_increase:.1f} to {selected_song.buzz_score:.1f}!")
                                            GAME_LOG.add_message(f"This project took significant time and effort.") if GAME_LOG else print(f"This project took significant time and effort.")
                                            player.energy = max(0, player.energy - 30); player.stress = min(100, player.stress + 15)
                                            deal['label_relationship_score'] = min(100, deal['label_relationship_score'] + 5)
                                            GAME_LOG.add_message(f"Your relationship with {deal['label_name']} improved slightly (+5).") if GAME_LOG else print(f"Your relationship with {deal['label_name']} improved slightly (+5).")
                                        else: GAME_LOG.add_message("Music video production cancelled.") if GAME_LOG else print("Music video production cancelled."); adv_time_general = 10
                                    else: GAME_LOG.add_message("No song selected or production cancelled.") if GAME_LOG else print("No song selected or production cancelled."); adv_time_general = 10
                            else: GAME_LOG.add_message("Conditions not met for music video production discussion (e.g., no budget, already produced, or not at your label's office).") if GAME_LOG else print("Conditions not met for music video production discussion (e.g., no budget, already produced, or not at your label's office)."); adv_time_general = 5
                            action_taken_custom_time = True
                        elif chosen_text == "Discuss Album Release with Label":
                            GAME_LOG.add_message("\n--- Discuss Album Release ---") if GAME_LOG else print("\n--- Discuss Album Release ---")
                            adv_time_general = 15; action_taken_custom_time = True
                            if player.signed_label_deal and player.signed_label_deal.get('label_poi_id') == poi.poi_id and player.signed_label_deal.get("albums_remaining_on_commitment", 0) > 0:
                                deal = player.signed_label_deal; label_id = deal['label_poi_id']
                                MIN_SONGS_FOR_ALBUM = random.randint(6,8)
                                eligible_songs_for_album = [s for s in player.songs_written if s.is_recorded and s.is_released and (s.considered_for_album_with_label_id is None or s.considered_for_album_with_label_id != label_id)]
                                if len(eligible_songs_for_album) < MIN_SONGS_FOR_ALBUM: GAME_LOG.add_message(f"{deal['label_name']} feels you don't have enough new, unreleased (on an album with them) material. Need at least {MIN_SONGS_FOR_ALBUM} suitable songs. You have {len(eligible_songs_for_album)}.") if GAME_LOG else print(f"{deal['label_name']} feels you don't have enough new, unreleased (on an album with them) material. Need at least {MIN_SONGS_FOR_ALBUM} suitable songs. You have {len(eligible_songs_for_album)}.")
                                else:
                                    GAME_LOG.add_message(f"You propose releasing an album with {deal['label_name']}. You have {len(eligible_songs_for_album)} potentially suitable recorded songs.") if GAME_LOG else print(f"You propose releasing an album with {deal['label_name']}. You have {len(eligible_songs_for_album)} potentially suitable recorded songs.")
                                    avg_quality = sum(s.song_quality for s in eligible_songs_for_album) / len(eligible_songs_for_album) if eligible_songs_for_album else 0
                                    avg_rec_quality = sum(s.recording_quality for s in eligible_songs_for_album) / len(eligible_songs_for_album) if eligible_songs_for_album else 0
                                    approval_chance = deal.get('label_relationship_score', 50) + (avg_quality * 50) + (avg_rec_quality * 25) - (MIN_SONGS_FOR_ALBUM - len(eligible_songs_for_album)) * 5
                                    GAME_LOG.add_message(f"(Debug: Album Approval Score Base: {deal.get('label_relationship_score', 50)}, AvgSongQBonus: {avg_quality*50:.1f}, AvgRecQBonus: {avg_rec_quality*25:.1f} -> Total: {approval_chance:.1f})") if GAME_LOG else print(f"(Debug: Album Approval Score Base: {deal.get('label_relationship_score', 50)}, AvgSongQBonus: {avg_quality*50:.1f}, AvgRecQBonus: {avg_rec_quality*25:.1f} -> Total: {approval_chance:.1f})")
                                    if approval_chance >= 65 :
                                        GAME_LOG.add_message(f"{deal['label_name']} is excited! \"This sounds like a strong collection, {player.name}! Let's do it.\"") if GAME_LOG else print(f"{deal['label_name']} is excited! \"This sounds like a strong collection, {player.name}! Let's do it.\"")
                                        album_songs_to_release = sorted(eligible_songs_for_album, key=lambda x: x.song_quality, reverse=True)[:random.randint(MIN_SONGS_FOR_ALBUM, MIN_SONGS_FOR_ALBUM + 2)]
                                        GAME_LOG.add_message("\nThe following songs will be featured on the album:") if GAME_LOG else print("\nThe following songs will be featured on the album:")
                                        for s_idx, s_obj in enumerate(album_songs_to_release): GAME_LOG.add_message(f"  {s_idx+1}. {s_obj.title}") if GAME_LOG else print(f"  {s_idx+1}. {s_obj.title}")
                                        if input(f"Proceed with releasing these {len(album_songs_to_release)} songs as an album? (This will take 4-8 weeks) (y/n) > ").lower() == 'y':
                                            release_time_weeks = random.randint(4, 8)
                                            adv_time_general += (release_time_weeks * 7 * 24 * 60) - 15
                                            player.fame += random.randint(15, 30) + int(avg_quality * 10)
                                            deal["albums_remaining_on_commitment"] = max(0, deal["albums_remaining_on_commitment"] - 1)
                                            for song_item in album_songs_to_release:
                                                song_item.considered_for_album_with_label_id = label_id
                                                song_item.buzz_score = min(100, song_item.buzz_score + random.uniform(5,15) * song_item.song_quality)
                                            GAME_LOG.add_message(f"\nYour new album has been released through {deal['label_name']}!") if GAME_LOG else print(f"\nYour new album has been released through {deal['label_name']}!")
                                            GAME_LOG.add_message(f"Fame increased. Albums remaining on contract: {deal['albums_remaining_on_commitment']}.") if GAME_LOG else print(f"Fame increased. Albums remaining on contract: {deal['albums_remaining_on_commitment']}.")
                                            GAME_LOG.add_message("The critics and fans are starting to react...") if GAME_LOG else print("The critics and fans are starting to react...")
                                            album_review = generate_feedback_for_album(player, album_songs_to_release, deal['label_name'], current_game_time)
                                            if album_review:
                                                player.feedback_received.append(album_review)
                                                GAME_LOG.add_message(f"Review from {album_review['source']}: \"{album_review['quote'][:100]}...\"") if GAME_LOG else print(f"Review from {album_review['source']}: \"{album_review['quote'][:100]}...\"")
                                                if 'fame' in album_review['impact']: player.fame = max(0, player.fame + album_review['impact']['fame'])
                                                if 'stress' in album_review['impact']: player.stress = min(100, max(0, player.stress + album_review['impact']['stress']))
                                                if 'label_relationship' in album_review['impact']: deal['label_relationship_score'] = min(100, max(0, deal['label_relationship_score'] + album_review['impact']['label_relationship']))
                                                GAME_LOG.add_message(f"(Fame: {player.fame}, Stress: {player.stress}, Label Rel: {deal['label_relationship_score']})") if GAME_LOG else print(f"(Fame: {player.fame}, Stress: {player.stress}, Label Rel: {deal['label_relationship_score']})")
                                            deal['label_relationship_score'] = min(100, max(0,deal['label_relationship_score'] + 10 + int(avg_quality*10)))
                                            player.stress = max(0, player.stress - random.randint(5,15)); player.energy = max(0, player.energy - 20)
                                        else: GAME_LOG.add_message("Album release cancelled by player.") if GAME_LOG else print("Album release cancelled by player.")
                                    elif approval_chance >= 40: GAME_LOG.add_message(f"{deal['label_name']} is hesitant. \"Hmm, it's promising, but maybe not quite there yet. Work on a few more stronger tracks.\"") if GAME_LOG else print(f"{deal['label_name']} is hesitant. \"Hmm, it's promising, but maybe not quite there yet. Work on a few more stronger tracks.\""); deal['label_relationship_score'] = max(0, deal['label_relationship_score'] - 2)
                                    else: GAME_LOG.add_message(f"{deal['label_name']} doesn't think this collection is ready. \"This isn't what we're looking for right now, {player.name}.\"") if GAME_LOG else print(f"{deal['label_name']} doesn't think this collection is ready. \"This isn't what we're looking for right now, {player.name}.\""); deal['label_relationship_score'] = max(0, deal['label_relationship_score'] - 5); player.stress = min(100, player.stress + 5)
                            else: GAME_LOG.add_message("Cannot discuss album release. Not signed, or no albums left on commitment with this label.") if GAME_LOG else print("Cannot discuss album release. Not signed, or no albums left on commitment with this label.")
                        if not action_taken_custom_time: adv_time_general = 15
                else: GAME_LOG.add_message("Not much to do here specifically.") if GAME_LOG else print("Not much to do here specifically."); adv_time_general = 10
            else:
                if loc.venues: GAME_LOG.add_message("\nVenues:") if GAME_LOG else print("\nVenues:"); [GAME_LOG.add_message(f"  - {v.name}") if GAME_LOG else print(f"  - {v.name}") for v in loc.venues]
                if loc.points_of_interest: GAME_LOG.add_message("\nPOIs:") if GAME_LOG else print("\nPOIs:"); [GAME_LOG.add_message(f"  - {p.name}") if GAME_LOG else print(f"  - {p.name}") for p in loc.points_of_interest]
                adv_time_general = 15
        elif choice == "4":
            GAME_LOG.add_message(f"\n--- Gigs in {player.current_location.name} ---") if GAME_LOG else print(f"\n--- Gigs in {player.current_location.name} ---")
            gigs = [e for e in player.current_location.get_all_events_at_location() if e.is_active]
            if not gigs: GAME_LOG.add_message("No gigs now.") if GAME_LOG else print("No gigs now.")
            else: [GAME_LOG.add_message(f"\n{i+1}. {g.name} ({g.event_type}) at {g.location.name}\n   Desc: {g.description}\n   Reqs: {g.required_skills}\n   Fame: {g.fame_reward}, Payout: ${g.payout}" + (f"\n   Prep: {', '.join([t for t,d in g.preparation_tasks_required.items() if not d]) if any(not d for d in g.preparation_tasks_required.values()) else ' Prep Complete!'}" if g.preparation_tasks_required else "")) for i,g in enumerate(gigs)]
            adv_time_general = 5
        elif choice == "5":
            all_gigs_prep = player.current_location.get_all_events_at_location()
            preparable = [e for e in all_gigs_prep if e.is_active and e.preparation_tasks_required and not e.are_preparations_complete()]
            if not preparable: GAME_LOG.add_message("No gigs need prep or all preps done.") if GAME_LOG else print("No gigs need prep or all preps done.")
            else:
                opts_prep={str(i+1):e for i,e in enumerate(preparable)}; disp_prep=[f"{e.name} (at {e.location.name}) - Pending: {', '.join([t for t,d in e.preparation_tasks_required.items() if not d])}" for e in preparable]
                gig_key_prep = present_choices(disp_prep, "Prepare for which gig?")
                if gig_key_prep and gig_key_prep in opts_prep:
                    event_prep=opts_prep[gig_key_prep]; tasks_pending_prep={str(i+1):task for i,(task,done) in enumerate(event_prep.preparation_tasks_required.items()) if not done}
                    if not tasks_pending_prep: GAME_LOG.add_message(f"All preps for {event_prep.name} done.") if GAME_LOG else print(f"All preps for {event_prep.name} done."); continue
                    task_disp_prep = [name for name in tasks_pending_prep.values()]
                    task_key_prep = present_choices(task_disp_prep, f"Task for {event_prep.name}?")
                    if task_key_prep and task_key_prep in tasks_pending_prep:
                        task_to_do_prep = tasks_pending_prep[task_key_prep]; GAME_LOG.add_message(f"Completing: {task_to_do_prep}...") if GAME_LOG else print(f"Completing: {task_to_do_prep}..."); event_prep.complete_preparation_task(task_to_do_prep)
                        adv_time_general = 120
        elif choice == "6":
            all_gigs_perform = player.current_location.get_all_events_at_location()
            performable = [e for e in all_gigs_perform if e.is_active and (not e.preparation_tasks_required or e.are_preparations_complete())]
            if not performable: GAME_LOG.add_message("No gigs ready to perform here.") if GAME_LOG else print("No gigs ready to perform here.")
            else:
                opts_gig={str(i+1):e for i,e in enumerate(performable)}; disp_gig=[f"{e.name} (at {e.location.name})" for e in performable]
                gig_key_perform = present_choices(disp_gig, "Attempt which gig?")
                if gig_key_perform and gig_key_perform in opts_gig:
                    event_perform = opts_gig[gig_key_perform]
                    can_perform_bool, message_str, _ = event_perform.can_perform(player)
                    if not can_perform_bool: GAME_LOG.add_message(f"Cannot perform {event_perform.name}: {message_str}") if GAME_LOG else print(f"Cannot perform {event_perform.name}: {message_str}"); adv_time_general = 60
                    else:
                        GAME_LOG.add_message(f"\n--- Select Setlist for {event_perform.name} --- \nRequires {event_perform.songs_required_count} song(s).") if GAME_LOG else print(f"\n--- Select Setlist for {event_perform.name} --- \nRequires {event_perform.songs_required_count} song(s).")
                        if not player.songs_written or len(player.songs_written) < event_perform.songs_required_count: GAME_LOG.add_message("You don't have enough songs for this event!") if GAME_LOG else print("You don't have enough songs for this event!"); continue
                        songs_disp = [str(s) for s in player.songs_written]
                        chosen_setlist = []
                        for i in range(event_perform.songs_required_count):
                            song_idx_str = present_choices(songs_disp, f"Choose song {i+1}/{event_perform.songs_required_count} (0 to cancel):")
                            if not song_idx_str or song_idx_str == "0": chosen_setlist = []; break
                            try:
                                chosen_song_idx = int(song_idx_str)-1
                                if 0 <= chosen_song_idx < len(player.songs_written): chosen_setlist.append(player.songs_written[chosen_song_idx])
                                else: GAME_LOG.add_message("Invalid song.") if GAME_LOG else print("Invalid song."); chosen_setlist = []; break
                            except ValueError: GAME_LOG.add_message("Invalid input.") if GAME_LOG else print("Invalid input."); chosen_setlist = []; break
                        if len(chosen_setlist) == event_perform.songs_required_count:
                            GAME_LOG.add_message("\nSetlist finalized.") if GAME_LOG else print("\nSetlist finalized."); [GAME_LOG.add_message(f" {j+1}. {s.title}") if GAME_LOG else print(f" {j+1}. {s.title}") for j,s in enumerate(chosen_setlist)]
                            perform_success, tour_completed_after_gig = event_perform.perform_event(player, setlist=chosen_setlist)
                            if perform_success:
                                gig_dur_mins = 180
                                venue_sched = event_perform.location; venue_name_sched = venue_sched.name if hasattr(venue_sched,'name') else "Venue"
                                start_sched = current_game_time.copy(); end_sched = start_sched.copy(); end_sched.advance_time(gig_dur_mins)
                                player.schedule.add_event(start_sched,end_sched,f"Gig: {event_perform.name} at {venue_name_sched}", "Gig", details={"event_id":event_perform.name, "venue_id": venue_sched.venue_id if hasattr(venue_sched,'venue_id') else venue_name_sched})
                                adv_time_general = gig_dur_mins
                                player.check_and_unlock_staff()
                                post_gig_outcome = check_for_post_gig_random_event(player,event_perform.event_type,venue_name=venue_name_sched)
                                if post_gig_outcome.get("event_triggered"):
                                    ev_mins = post_gig_outcome.get("minutes_passed",15)
                                    if ev_mins > 0: adv_time_general += ev_mins
                                    player.check_and_unlock_staff()
                                owner = getattr(event_perform.location,'owner_npc_id',None)
                                if owner and isinstance(owner, NPC): owner.update_relationship(15); owner.add_memory(f"{player.name} had successful gig '{event_perform.name}'.")
                                if not event_perform.is_active and hasattr(event_perform.location,'remove_event'): event_perform.location.remove_event(event_perform)
                                if tour_completed_after_gig and player.current_tour_id:
                                    tour_ledger = player.tour_ledgers.get(player.current_tour_id)
                                    if tour_ledger:
                                        net_profit = tour_ledger["income"] - tour_ledger["expenses"]
                                        GAME_LOG.add_message(f"\n--- Tour '{tour_ledger['name']}' Concluded! ---") if GAME_LOG else print(f"\n--- Tour '{tour_ledger['name']}' Concluded! ---")
                                        GAME_LOG.add_message(f"Total Income: ${tour_ledger['income']}") if GAME_LOG else print(f"Total Income: ${tour_ledger['income']}")
                                        GAME_LOG.add_message(f"Total Expenses: ${tour_ledger['expenses']}") if GAME_LOG else print(f"Total Expenses: ${tour_ledger['expenses']}")
                                        GAME_LOG.add_message(f"Net Profit/Loss: ${net_profit}") if GAME_LOG else print(f"Net Profit/Loss: ${net_profit}")
                                        tour_ledger["status"] = "completed"; player.current_tour_id = None
                                        player.tour_fatigue = max(0, player.tour_fatigue - 25)
                                        GAME_LOG.add_message(f"You can finally rest a bit! Tour fatigue reduced to {player.tour_fatigue}.") if GAME_LOG else print(f"You can finally rest a bit! Tour fatigue reduced to {player.tour_fatigue}.")
                            else:
                                adv_time_general = 60
                                owner = getattr(event_perform.location,'owner_npc_id',None)
                                if owner and isinstance(owner, NPC): owner.update_relationship(-10); owner.add_memory(f"{player.name} failed gig '{event_perform.name}'.")
                        else: GAME_LOG.add_message("Gig cancelled due to setlist.") if GAME_LOG else print("Gig cancelled due to setlist."); adv_time_general = 15
        elif choice == "7": GAME_LOG.add_message("\n--- Player Stats ---") if GAME_LOG else print("\n--- Player Stats ---"); GAME_LOG.add_message(str(player)) if GAME_LOG else print(player); GAME_LOG.add_message(get_current_time_str()) if GAME_LOG else print(get_current_time_str()); adv_time_general = 1
        elif choice == "8":
            npcs_here = [n for n in NPC_REGISTRY.values() if n.current_location == player.current_poi or n.current_location == player.current_location]
            if not npcs_here: GAME_LOG.add_message("No one around.") if GAME_LOG else print("No one around.")
            else:
                npc_choices = {str(i+1):n for i,n in enumerate(npcs_here)}; npc_disp = [f"{n.name}" for n in npcs_here]
                npc_key = present_choices(npc_disp, "Talk to whom?")
                if npc_key and npc_key in npc_choices: talk_to_npc_instance(player, npc_choices[npc_key], main_window) # Pass main_window
        elif choice == "9":
            food_items = [item for item in player.gear_inventory if item.gear_type == "FOOD"]
            if not food_items: GAME_LOG.add_message("No food in inventory.") if GAME_LOG else print("No food in inventory.")
            else:
                food_opts={str(i+1):item for i,item in enumerate(food_items)}
                food_disp=[f"{item.name} (Hunger: -{item.hunger_reduction}, Energy: +{item.energy_boost})" + (f", Comfort: {item.get_property('comfort_effect'):+}" if item.get_property("comfort_effect") else "") for item in food_items]
                food_key = present_choices(food_disp, "Eat which item? (0 to cancel)")
                if food_key and food_key!="0" and food_key in food_opts:
                    item=food_opts[food_key]; player.hunger=max(0,player.hunger-item.hunger_reduction); player.energy=min(100,player.energy+item.energy_boost)
                    player.comfort=min(100,max(0,player.comfort+(item.get_property("comfort_effect") or 0)))
                    player.remove_gear(item); adv_time_general=15
                    GAME_LOG.add_message(f"Ate {item.name}. Hunger: {player.hunger}, Energy: {player.energy}, Comfort: {player.comfort}") if GAME_LOG else print(f"Ate {item.name}. Hunger: {player.hunger}, Energy: {player.energy}, Comfort: {player.comfort}")
                elif food_key=="0": GAME_LOG.add_message("Cancelled eating.") if GAME_LOG else print("Cancelled eating.")
        elif choice == "10": handle_phone_menu(player, main_window)
        elif choice == "11":
            if not (player.has_manager or player.has_pr_manager): GAME_LOG.add_message("No staff yet.") if GAME_LOG else print("No staff yet.")
            else:
                GAME_LOG.add_message("\n--- Staff Actions ---") if GAME_LOG else print("\n--- Staff Actions ---"); staff_opts = {}; idx = 1
                if player.has_manager:
                    staff_opts[str(idx)]="Talk to Artist Manager"; idx+=1
                    staff_opts[str(idx)]="Discuss Tour Opportunities"; idx+=1
                    staff_opts[str(idx)]="Review Past Tours"; idx+=1
                if player.has_pr_manager: staff_opts[str(idx)]="Check PR Opportunities"; idx+=1
                staff_opts["0"]="Back"
                sub_choice = present_choices(staff_opts, "Staff action:")
                action_text = staff_opts.get(sub_choice); adv_min_staff = 0
                if action_text == "Talk to Artist Manager": GAME_LOG.add_message("Discussing strategy... (TBD)") if GAME_LOG else print("Discussing strategy... (TBD)"); adv_min_staff=30
                elif action_text == "Discuss Tour Opportunities":
                    adv_min_staff = 0
                    if not player.has_manager: GAME_LOG.add_message("Need a manager first.") if GAME_LOG else print("Need a manager first.")
                    elif player.active_tour_offer:
                        if input(f"Manager: \"We have the '{player.active_tour_offer['name']}' tour offer. Finalize it? (y/n)\"").lower() == 'y':
                            adv_min_staff = 30; tour_package_gigs = player.active_tour_offer['gigs']; tour_id = player.active_tour_offer['tour_id']
                            GAME_LOG.add_message("\nManager: \"Booking the tour...\"") if GAME_LOG else print("\nManager: \"Booking the tour...\""); scheduled_gigs_count=0
                            player.current_tour_id = tour_id
                            player.tour_ledgers[tour_id] = {"name": player.active_tour_offer['name'], "expenses":0, "income":0, "status":"ongoing", "gigs_details":[]}
                            current_tour_gig_details_list = []
                            for gig_data in tour_package_gigs:
                                venue = get_poi_or_venue_by_id(gig_data['venue_id'])
                                if not venue or not isinstance(venue, Venue): GAME_LOG.add_message(f"Skipping gig, bad venue: {gig_data['venue_id']}") if GAME_LOG else print(f"Skipping gig, bad venue: {gig_data['venue_id']}"); continue
                                gig_event_type = gig_data['event_type']
                                gig_skills = gig_data.get('required_skills_override', Event.EVENT_TYPES.get(gig_event_type,{}).get('required_skills', {"vocals":1,"guitar":1}))
                                new_event = Event(name=f"Tour: {player.name} at {venue.name}", location=venue, event_type=gig_event_type, required_skills=gig_skills, description=f"Tour stop in {gig_data['city_name']}", specific_payout=gig_data['estimated_payout'], is_tour_gig=True)
                                gig_start_time = current_game_time.copy(); gig_start_time.advance_time(minutes=gig_data['days_offset'] * 24 * 60)
                                gig_start_time.hour = 20; gig_start_time.minute = 0
                                gig_end_time = gig_start_time.copy(); gig_end_time.advance_time(minutes=3*60)
                                venue.add_event(new_event)
                                player.schedule.add_event(gig_start_time, gig_end_time, new_event.name, "Tour Gig", details={"venue_id":venue.venue_id, "event_id":new_event.name, "tour_id": tour_id})
                                current_tour_gig_details_list.append({"venue_id": venue.venue_id, "city_name": gig_data['city_name'], "scheduled_date_str": gig_start_time.get_time_string_for_schedule(), "event_name": new_event.name, "performed": False})
                                GAME_LOG.add_message(f"Booked: {new_event.name} in {gig_data['city_name']} on {gig_start_time.get_time_string_for_schedule()}") if GAME_LOG else print(f"Booked: {new_event.name} in {gig_data['city_name']} on {gig_start_time.get_time_string_for_schedule()}")
                                scheduled_gigs_count+=1
                            player.tour_ledgers[tour_id]["gigs_details"] = current_tour_gig_details_list
                            if scheduled_gigs_count > 0: GAME_LOG.add_message(f"Manager: \"Tour '{player.tour_ledgers[tour_id]['name']}' booked!\"") if GAME_LOG else print(f"Manager: \"Tour '{player.tour_ledgers[tour_id]['name']}' booked!\"")
                            else: GAME_LOG.add_message("Manager: \"Couldn't book any gigs for that tour.\"") if GAME_LOG else print("Manager: \"Couldn't book any gigs for that tour.\""); del player.tour_ledgers[tour_id]; player.current_tour_id = None
                            player.active_tour_offer = None
                            if scheduled_gigs_count > 0 and tour_id not in player.completed_tour_ids : player.completed_tour_ids.append(tour_id)
                        else: GAME_LOG.add_message("Manager: \"Okay, offer stands.\"") if GAME_LOG else print("Manager: \"Okay, offer stands.\""); adv_min_staff=5
                    else:
                        GAME_LOG.add_message("Manager: \"Let me see what tours I can cook up...\"") if GAME_LOG else print("Manager: \"Let me see what tours I can cook up...\""); adv_min_staff = 20
                        tours_json_path_local = os.path.join(SCRIPT_DIR, "game_data", "tours.json")
                        try:
                            with open(tours_json_path_local, 'r') as f: all_tour_templates = json.load(f)
                        except Exception as e: GAME_LOG.add_message(f"Manager: \"Tour planner error: {e}\"") if GAME_LOG else print(f"Manager: \"Tour planner error: {e}\""); all_tour_templates = []
                        eligible_tours = [t for t in all_tour_templates if t['min_fame'] <= player.fame <= t['max_fame'] and t['tour_id'] not in player.completed_tour_ids]
                        if not eligible_tours: GAME_LOG.add_message("Manager: \"Nothing quite right for you now.\"") if GAME_LOG else print("Manager: \"Nothing quite right for you now.\"")
                        else:
                            tour_template = random.choice(eligible_tours)
                            GAME_LOG.add_message(f"\nManager: \"How about this: '{tour_template['name']}'. {tour_template['description']}\"") if GAME_LOG else print(f"\nManager: \"How about this: '{tour_template['name']}'. {tour_template['description']}\"")
                            fleshed_gigs = []; possible_to_book = True; cumulative_day_offset_for_proposal = 0
                            for leg, gig_tmpl in enumerate(tour_template['gig_templates']):
                                city = random.choice(gig_tmpl['city_options'])
                                venues_in_city = [v for v in WORLD_MAP[city].venues if v.venue_type in gig_tmpl['venue_type_options']] if WORLD_MAP.get(city) else []
                                if not venues_in_city: possible_to_book = False; break
                                venue = random.choice(venues_in_city)
                                cumulative_day_offset_for_proposal += random.randint(gig_tmpl['days_offset_min'], gig_tmpl['days_offset_max'])
                                fleshed_gigs.append({'venue_id': venue.venue_id, 'venue_name': venue.name, 'event_type': gig_tmpl['event_type'], 'days_offset': cumulative_day_offset_for_proposal, 'city_name': city, 'estimated_payout': gig_tmpl['base_payout_estimate'], 'required_skills_override': gig_tmpl.get('required_skills_override')})
                            if possible_to_book and fleshed_gigs:
                                GAME_LOG.add_message("Proposed Itinerary:") if GAME_LOG else print("Proposed Itinerary:")
                                est_total_pay = sum(g['estimated_payout'] for g in fleshed_gigs)
                                for i,g in enumerate(fleshed_gigs): GAME_LOG.add_message(f"  Gig {i+1}: {g['event_type']} at {g['venue_name']} in {g['city_name']} (~{g['days_offset']} days). Est. ${g['estimated_payout']}") if GAME_LOG else print(f"  Gig {i+1}: {g['event_type']} at {g['venue_name']} in {g['city_name']} (~{g['days_offset']} days). Est. ${g['estimated_payout']}")
                                GAME_LOG.add_message(f"Total est. payout: ${est_total_pay}. Expenses on you.") if GAME_LOG else print(f"Total est. payout: ${est_total_pay}. Expenses on you.")
                                if present_choices({"1":"Accept offer","2":"Decline"},"Accept tour?") == "1":
                                    player.active_tour_offer = {"tour_id":tour_template['tour_id'], "name":tour_template['name'], "gigs":fleshed_gigs}
                                    GAME_LOG.add_message("Manager: \"Great! Confirm with me again to finalize bookings.\"") if GAME_LOG else print("Manager: \"Great! Confirm with me again to finalize bookings.\""); adv_min_staff+=10
                                else: player.active_tour_offer=None; GAME_LOG.add_message("Manager: \"Okay, maybe next time.\"") if GAME_LOG else print("Manager: \"Okay, maybe next time.\""); adv_min_staff+=5
                            else: GAME_LOG.add_message("Manager: \"Couldn't work out a solid itinerary for that one.\"") if GAME_LOG else print("Manager: \"Couldn't work out a solid itinerary for that one.\"")
                elif action_text == "Review Past Tours":
                    GAME_LOG.add_message("\n--- Past Tour Review ---") if GAME_LOG else print("\n--- Past Tour Review ---")
                    completed_tours = {tid: tdata for tid, tdata in player.tour_ledgers.items() if tdata.get("status") == "completed"}
                    if not completed_tours: GAME_LOG.add_message("Manager: \"You haven't completed any tours for us to review yet.\"") if GAME_LOG else print("Manager: \"You haven't completed any tours for us to review yet.\"")
                    else:
                        tour_choices_dict = {str(i+1): tid for i, tid in enumerate(completed_tours.keys())}
                        ordered_tour_display_list = []
                        for key_idx_str in sorted(tour_choices_dict.keys(), key=int):
                            tid_val = tour_choices_dict[key_idx_str]
                            ordered_tour_display_list.append(f"{completed_tours[tid_val]['name']} (ID: {tid_val})")
                        tour_key_display_idx = present_choices(ordered_tour_display_list, "Which tour to review? (0 to cancel)")
                        if tour_key_display_idx and tour_key_display_idx != "0":
                            actual_tour_id_key = sorted(tour_choices_dict.keys(), key=int)[int(tour_key_display_idx)-1]
                            chosen_tour_id = tour_choices_dict[actual_tour_id_key]
                            ledger = player.tour_ledgers[chosen_tour_id]; net_profit = ledger['income'] - ledger['expenses']
                            GAME_LOG.add_message(f"\nSummary for Tour: '{ledger['name']}'") if GAME_LOG else print(f"\nSummary for Tour: '{ledger['name']}'")
                            GAME_LOG.add_message(f"  Total Income: ${ledger['income']}") if GAME_LOG else print(f"  Total Income: ${ledger['income']}")
                            GAME_LOG.add_message(f"  Total Expenses: ${ledger['expenses']}") if GAME_LOG else print(f"  Total Expenses: ${ledger['expenses']}")
                            GAME_LOG.add_message(f"  Net Profit/Loss: ${net_profit}") if GAME_LOG else print(f"  Net Profit/Loss: ${net_profit}")
                            GAME_LOG.add_message("  Gigs Performed:") if GAME_LOG else print("  Gigs Performed:")
                            for gig_d in ledger.get("gigs_details",[]):
                                if gig_d.get("performed"): GAME_LOG.add_message(f"    - {gig_d['event_name']} in {gig_d['city_name']}") if GAME_LOG else print(f"    - {gig_d['event_name']} in {gig_d['city_name']}")
                        elif tour_key_display_idx == "0": GAME_LOG.add_message("Cancelled review.") if GAME_LOG else print("Cancelled review.")
                        else: GAME_LOG.add_message("Invalid selection for tour review.") if GAME_LOG else print("Invalid selection for tour review.")
                    adv_min_staff = 10
                elif action_text == "Check PR Opportunities":
                    GAME_LOG.add_message("Checking with PR Manager...") if GAME_LOG else print("Checking with PR Manager..."); adv_min_staff=30
                    chron_key="interview_city_chronicle"; chron_fame_req=player.OPPORTUNITY_FAME_THRESHOLDS.get(chron_key,float('inf'))
                    op_status=player.active_opportunities.get(chron_key)
                    if op_status=="completed": GAME_LOG.add_message("PR: 'Chronicle interview done!'") if GAME_LOG else print("PR: 'Chronicle interview done!'")
                    elif op_status=="pending_player_action": GAME_LOG.add_message("PR: 'Chronicle interview ready when you are.'") if GAME_LOG else print("PR: 'Chronicle interview ready when you are.'")
                    elif player.fame>=chron_fame_req: player.active_opportunities[chron_key]="pending_player_action"; GAME_LOG.add_message("PR: 'Good news! Chronicle interview lined up!'") if GAME_LOG else print("PR: 'Good news! Chronicle interview lined up!'")
                    else: GAME_LOG.add_message(f"PR: 'Quiet on press front. Need ~{chron_fame_req} fame for Chronicle.'") if GAME_LOG else print(f"PR: 'Quiet on press front. Need ~{chron_fame_req} fame for Chronicle.'")
                elif action_text == "Back to Main Menu": adv_min_staff=0
                else: GAME_LOG.add_message("Invalid staff action.") if GAME_LOG else print("Invalid staff action.")
                if adv_min_staff > 0: adv_time_general = adv_min_staff
        elif choice == "00": adv_time_general = 60
        elif choice == "0": GAME_LOG.add_message("Thanks for playing!") if GAME_LOG else print("Thanks for playing!"); break
        else: GAME_LOG.add_message("Invalid choice.") if GAME_LOG else print("Invalid choice.")

        if adv_time_general > 0: advance_game_time(adv_time_general); update_npc_locations(current_game_time); process_time_based_player_needs(player, adv_time_general)
        GAME_LOG.add_message(f"\n--- {get_current_time_str()} ---") if GAME_LOG else print(f"\n--- {get_current_time_str()} ---")
        if choice in ["1","3","4","5","7","10","11","00"] and not ("LLM Error" in locals().get('npc_response','')):
            event_outcome = check_for_random_event(player, player.current_poi.name if player.current_poi else player.current_location.name)
            if event_outcome.get("event_triggered"):
                ev_mins = event_outcome.get("minutes_passed",15)
                if ev_mins > 0: advance_game_time(ev_mins); update_npc_locations(current_game_time); process_time_based_player_needs(player,ev_mins)
                player.check_and_unlock_staff()

if __name__ == "__main__":
    pygame_main()


