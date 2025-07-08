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

from game_data.gear_catalog import GEAR_CATALOG
from game.npc import NPC
from game.chart import Chart # Import the new Chart class

WORLD_MAP = {}
NPC_REGISTRY = {}
PLAYER_HOME_POI_ID_GLOBAL = None
ACTIVE_CHARTS = [] # Global list to hold active chart objects
LAST_CHART_UPDATE_DAY = -1 # Stores the game day number of the last chart update

# --- Player Needs Update Function ---
def process_time_based_player_needs(player, minutes_just_passed):
    if minutes_just_passed <= 0:
        return
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

    POINTS_PER_DAY_HAIR = 10.0
    POINTS_PER_DAY_BEARD = 12.5
    hair_growth_to_add = (minutes_just_passed / (24.0 * 60.0)) * POINTS_PER_DAY_HAIR
    player.hair_growth_progress += hair_growth_to_add
    beard_growth_to_add = (minutes_just_passed / (24.0 * 60.0)) * POINTS_PER_DAY_BEARD
    player.beard_growth_progress += beard_growth_to_add

    if player.hair_growth_progress >= player.HAIR_POINTS_PER_LENGTH_LEVEL:
        levels_gained = int(player.hair_growth_progress // player.HAIR_POINTS_PER_LENGTH_LEVEL)
        player.hair_length = min(player.MAX_HAIR_LENGTH, player.hair_length + levels_gained)
        player.hair_growth_progress %= player.HAIR_POINTS_PER_LENGTH_LEVEL
        if levels_gained > 0: print(f"DEBUG: Your hair grew! New length: {player.hair_length}/{player.MAX_HAIR_LENGTH}")

    if player.beard_growth_progress >= player.BEARD_POINTS_PER_LENGTH_LEVEL:
        levels_gained = int(player.beard_growth_progress // player.BEARD_POINTS_PER_LENGTH_LEVEL)
        player.beard_length = min(player.MAX_BEARD_LENGTH, player.beard_length + levels_gained)
        player.beard_growth_progress %= player.BEARD_POINTS_PER_LENGTH_LEVEL
        if levels_gained > 0: print(f"DEBUG: Your beard grew! New length: {player.beard_length}/{player.MAX_BEARD_LENGTH}")

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
    try:
        with open("game_data/world/locations.json", 'r') as f: locations_data = json.load(f)
    except Exception as e: print(f"FATAL ERROR loading locations.json: {e}"); return False
    temp_location_id_map = {}
    for loc_data in locations_data:
        location = Location(loc_data["name"], loc_data["description"]); location.id = loc_data["id"]
        WORLD_MAP[location.name] = location; temp_location_id_map[location.id] = location
    for loc_id_from_json, location_obj in temp_location_id_map.items():
        poi_file_name = next((ld["poi_definition_file"] for ld in locations_data if ld["id"] == loc_id_from_json), None)
        if not poi_file_name: print(f"Warning: No POI file for {location_obj.name}."); continue
        poi_file_path = f"game_data/world/city_definitions/{poi_file_name}"
        try:
            with open(poi_file_path, 'r') as f: city_def_data = json.load(f)
        except Exception as e: print(f"ERROR loading {poi_file_path}: {e}"); continue
        for poi_data in city_def_data.get("points_of_interest", []):
            props = poi_data.get("properties", {})
            poi = PointOfInterest(poi_id=poi_data["poi_id"], name=poi_data["name"], description=poi_data["description"],
                                  category=poi_data["category"], interaction_options=list(poi_data.get("interaction_options", [])),
                                  parent_location_id=location_obj.name, **props)
            if "shop_inventory_item_ids" in props: poi.shop_inventory_item_ids = list(props["shop_inventory_item_ids"])
            if "menu_items" in props:
                poi.menu_items = list(props["menu_items"])
                if poi.category == "FOOD_FASTFOOD" and not poi.interaction_options: poi.interaction_options = [item["display_text"] for item in poi.menu_items]
            if poi.poi_id == "citycenter_indiehits_records": poi.interaction_options = [f"Submit Demo (requires {poi.min_fame_to_submit} fame)", "Talk to A&R Rep (requires Manager)"]
            location_obj.add_poi(poi)
        for venue_data in city_def_data.get("venues", []):
            props = venue_data.get("properties", {})
            venue = Venue(venue_id=venue_data["venue_id"], name=venue_data["name"], description=venue_data["description"],
                          venue_type=venue_data["venue_type"], category=venue_data["category"],
                          capacity=venue_data["capacity"], prestige=venue_data["prestige"],
                          parent_location_id=location_obj.name, **props)
            venue.events_hosted_ids_from_json = list(venue_data.get("events_hosted_ids", []))
            location_obj.add_venue(venue)
        for conn_data in city_def_data.get("intra_city_poi_connections", []):
            poi_ids_tuple = tuple(sorted(conn_data["pois"]))
            if len(poi_ids_tuple) == 2: location_obj.intra_city_poi_connections[frozenset(poi_ids_tuple)] = {k: v for k, v in conn_data.items() if k != "pois"}
    _build_poi_venue_id_map()
    try:
        with open("game_data/world/npcs.json", 'r') as f: npcs_data = json.load(f)
    except Exception as e: print(f"ERROR loading npcs.json: {e}"); return False
    for npc_data in npcs_data:
        home_loc_obj = get_poi_or_venue_by_id(npc_data.get("home_location_poi_id")) or WORLD_MAP.get(npc_data.get("home_location_location_id"))
        current_loc_obj = get_poi_or_venue_by_id(npc_data.get("initial_current_location_poi_id")) or WORLD_MAP.get(npc_data.get("initial_current_location_location_id"))
        if not home_loc_obj and npc_data.get("schedule"): home_loc_obj = get_poi_or_venue_by_id(list(npc_data["schedule"].values())[0])
        if not current_loc_obj: current_loc_obj = home_loc_obj
        if not home_loc_obj: print(f"Warning: No home location for NPC {npc_data['name']}.")
        if not current_loc_obj: print(f"Warning: No current location for NPC {npc_data['name']}.")
        npc = NPC(npc_id=npc_data["npc_id"], name=npc_data["name"], personality_key=npc_data["personality_key"], home_location=home_loc_obj, current_location=current_loc_obj)
        for time_slot, loc_id_str in npc_data.get("schedule", {}).items():
            scheduled_loc_obj = get_poi_or_venue_by_id(loc_id_str)
            if scheduled_loc_obj: npc.schedule[time_slot] = scheduled_loc_obj
            else: print(f"Warning: Scheduled POI/Venue ID '{loc_id_str}' not found for {npc.name}'s schedule.")
        NPC_REGISTRY[npc.npc_id] = npc
    for loc in WORLD_MAP.values():
        for item_list in [loc.points_of_interest, loc.venues]:
            for item in item_list:
                if hasattr(item, 'owner_npc_id') and isinstance(item.owner_npc_id, str):
                    owner_npc = NPC_REGISTRY.get(item.owner_npc_id)
                    if owner_npc: item.owner_npc_id = owner_npc
                    else: print(f"Warning: Owner NPC ID '{item.owner_npc_id}' not found for '{item.name}'."); item.owner_npc_id = None
    for loc_data in locations_data:
        curr_loc_obj = temp_location_id_map.get(loc_data["id"])
        if not curr_loc_obj: continue
        for conn_data in loc_data.get("travel_connections", []):
            target_loc_obj = temp_location_id_map.get(conn_data["to_location_id"])
            if target_loc_obj: curr_loc_obj.add_travel_connection(target_loc_obj.name, cost=conn_data["cost"], time_hours=conn_data["time_hours"])
            else: print(f"Warning: Target location ID '{conn_data['to_location_id']}' for travel from '{curr_loc_obj.name}' not found.")
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
        else: print(f"Warning: Venue ID '{ed['venue_id']}' for event '{ed['name']}' not found or not a Venue.")
    player_home_obj = get_poi_or_venue_by_id("hometown_player_home")
    if player_home_obj: PLAYER_HOME_POI_ID_GLOBAL = player_home_obj.poi_id
    else: print("CRITICAL ERROR: Player home POI 'hometown_player_home' not found.")

    # Initialize ACTIVE_CHARTS
    ACTIVE_CHARTS.clear()
    hometown_chart = Chart(name="Hometown Local Hits", max_size=10, chart_genre_preference="Indie") # Example
    city_chart = Chart(name="City Center Top Tracks", max_size=20) # Example
    ACTIVE_CHARTS.append(hometown_chart)
    ACTIVE_CHARTS.append(city_chart)
    print(f"Initialized {len(ACTIVE_CHARTS)} charts.")

    print(f"World setup complete. Loaded {len(WORLD_MAP)} locations and {len(NPC_REGISTRY)} NPCs.")
    return True

def get_day_of_week_name(day_number_in_month):
    return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][(day_number_in_month - 1) % 7]

def get_time_slot_key(gt_obj):
    day_name = get_day_of_week_name(gt_obj.day)
    hour = gt_obj.hour
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
        if isinstance(dest_ref, (PointOfInterest, Venue, Location)):
            dest = dest_ref
        elif isinstance(dest_ref, str):
            dest = get_poi_or_venue_by_id(dest_ref) or WORLD_MAP.get(dest_ref)

        if dest is None : dest = npc.home_location

        if npc.npc_id == "sarah001":
            comm_hall = get_poi_or_venue_by_id("hometown_community_hall")
            if comm_hall and any(e.name == "Open Mic Night" and e.is_active for e in getattr(comm_hall, 'events_hosted', [])):
                scheduled_loc_for_open_mic = npc.schedule.get("open_mic_night_at_community_hall")
                if isinstance(scheduled_loc_for_open_mic, str): scheduled_loc_for_open_mic = get_poi_or_venue_by_id(scheduled_loc_for_open_mic)
                if scheduled_loc_for_open_mic == comm_hall: dest = comm_hall
        if npc.current_location != dest: npc.current_location = dest

def clear_screen_ish(): print("\n" * 30)

def present_choices(options, title="Choose an option:"):
    print(f"\n--- {title} ---")
    if isinstance(options, list): [print(f"{i+1}. {opt}") for i, opt in enumerate(options)]
    elif isinstance(options, dict): [print(f"{k}. {v}") for k, v in options.items()]
    else: print("Error: Invalid options for present_choices."); return None
    for _ in range(3):
        choice = input("> ")
        if isinstance(options, list) and choice.isdigit() and 1 <= int(choice) <= len(options): return str(int(choice))
        if isinstance(options, dict) and choice in options: return choice
        print("Invalid choice. Try again.")
    print("Too many invalid attempts."); return None

def display_hud(player, gt_obj):
    age = calculate_player_age(player.start_date, gt_obj, player.age)
    loc = player.current_location.name if player.current_location else 'N/A'
    poi = player.current_poi.name if player.current_poi else 'N/A'
    hair = f"{get_hair_length_description(player.hair_length)} ({player.hair_length}/{player.MAX_HAIR_LENGTH})"
    beard = f"{get_beard_length_description(player.beard_length)} ({player.beard_length}/{player.MAX_BEARD_LENGTH})"
    date_str = get_current_time_str(date_only=True); time_str = f"{gt_obj.hour:02d}:{gt_obj.minute:02d}"
    print("="*79 + f"\n| {player.name} | Age: {age} | Fame: {player.fame} | Money: ${player.money}\n" +
          f"| Location: {loc} / {poi}\n| Hair: {hair} | Beard: {beard}\n" +
          f"| Date: {date_str} | Time: {time_str}\n" + "="*79)

def get_hair_length_description(val):
    if val == 0: return "Bald"; elif val <= 2: return "Very Short"; elif val <= 4: return "Short";
    elif val <= 6: return "Medium"; elif val <= 8: return "Long"; else: return "Very Long"

def get_beard_length_description(val):
    if val == 0: return "Clean-shaven"; elif val <= 2: return "Stubble"; elif val <= 4: return "Short Beard";
    elif val <= 6: return "Medium Beard"; elif val <= 8: return "Long Beard"; else: return "Wizard Beard"

def talk_to_npc_instance(player, npc):
    if not npc: print("No one specific to talk to."); return
    print(f"\n--- Talking to {npc.name} ---\nType 'bye' to end.")
    talk_duration_minutes = 0
    while True:
        p_input = input(f"{player.name}: ")
        talk_duration_minutes += 5
        if p_input.lower() == 'bye':
            print(f"{npc.name} nods."); npc.add_memory(f"Ended chat with {player.name}.")
            break
        if not p_input.strip(): continue
        response = generate_npc_response(p_input, npc, player_name=player.name)
        print(f"{npc.name}: {response}")
        if "LLM Error" in response or "unexpected error" in response:
            npc.add_memory(f"LLM error with {player.name}.")
            talk_duration_minutes = max(15, talk_duration_minutes)
            break
        clar_opts = {"1": "Friendly", "2": "Neutral", "3": "Unfriendly", "0": "Continue"}
        intent_choice = present_choices(clar_opts, "Your intent:")
        pts = 0; mem_detail = ""
        if intent_choice == "1": pts = 5; mem_detail = f"Player friendly: '{p_input}'"
        elif intent_choice == "3": pts = -5; mem_detail = f"Player unfriendly: '{p_input}'"
        if pts != 0: npc.update_relationship(pts); npc.add_memory(mem_detail); print(f"(Rel with {npc.name} by {pts})")

        is_contact = any(c['npc_id'] == npc.npc_id for c in player.contacts)
        if not is_contact and npc.relationship_score >= 30:
            if present_choices({"1":"Continue","2":f"Ask {npc.name} for number"},"Deepen connection?")=="2":
                agrees = (npc.relationship_score >= 70 and random.random()<0.95) or \
                         (npc.relationship_score >= 50 and random.random()<0.75) or (random.random()<0.50)
                if agrees:
                    player.contacts.append({'npc_id':npc.npc_id, 'name':npc.name, 'notes':f"Met at {player.current_poi.name if player.current_poi else player.current_location.name}, {get_current_time_str(True)}. Rel: {npc.relationship_score}"})
                    print(f"Exchanged numbers with {npc.name}!"); npc.add_memory(f"Exchanged numbers with {player.name}."); npc.update_relationship(10)
                else: print(f"{npc.name} politely declines."); npc.add_memory(f"Declined number exchange with {player.name}."); npc.update_relationship(-2)
                talk_duration_minutes += 5

    final_talk_time = max(15, talk_duration_minutes)
    advance_game_time(final_talk_time); update_npc_locations(current_game_time); process_time_based_player_needs(player, final_talk_time)

def handle_phone_menu(player):
    while True:
        clear_screen_ish(); print(f"\n--- Phone --- ({player.name}) ---\n--- {get_current_time_str()} ---")
        opts = {"1":"Check Schedule", "2":"Local News", "3":"Contacts", "4":"Music Management", "0":"Put Phone Away"}
        choice = present_choices(opts, "Phone Options:")
        adv_time = 1
        if choice == "1":
            sched_opts = {"1":"Today", "2":"Tomorrow", "3":"This Week", "0":"Back"}
            view_choice = present_choices(sched_opts, "Select schedule view:")
            if view_choice == "0": continue
            target_time = current_game_time.copy()
            if view_choice == "2": target_time.advance_time(24*60)
            items = []; title_str = ""
            if view_choice in ["1","2"]: items=player.schedule.get_events_for_day(target_time.year,target_time.month,target_time.day); title_str=f"{sched_opts[view_choice]}'s Schedule"
            elif view_choice == "3": items=player.schedule.get_events_for_week(target_time.year,target_time.month,target_time.day); title_str="This Week's Schedule"
            print(f"\n--- {title_str} ({target_time.year}-{target_time.month:02d}-{target_time.day:02d}) ---")
            if not items: print("Nothing scheduled.")
            else: [print(item) for item in items]
            adv_time = 10
        elif choice == "2": print("\n--- Local News ---\n(Feature TBD)"); adv_time = 5
        elif choice == "3":
            print("\n--- Contacts ---")
            if not player.contacts: print("Contact list empty."); adv_time=1
            else:
                c_opts = {str(i+1):f"{c['name']} (Notes: {c.get('notes','N/A')})" for i,c in enumerate(player.contacts)}; c_opts["0"]="Back"
                sel_c_key = present_choices(c_opts, "Select contact:")
                if sel_c_key != "0" and sel_c_key in c_opts:
                    contact = player.contacts[int(sel_c_key)-1]; print(f"\nCalling {contact['name']}...")
                    call_mins = random.randint(2,5); adv_time += call_mins
                    npc_obj = NPC_REGISTRY.get(contact['npc_id'])
                    responses = [f"{contact['name']} doesn't pick up. Voicemail.", f"{contact['name']} is busy. Try later."]
                    if npc_obj: npc_obj.add_memory(f"Call attempt from {player.name} (voicemail/busy).")
                    print(random.choice(responses))
        elif choice == "4": # Music Management
            print("\n--- Music Management ---")
            music_opts = {"1": "Self-Release Song", "2": "View Released Songs (TBD)", "3": "View Charts", "0": "Back"}
            music_choice = present_choices(music_opts, "Music Management Options:")
            adv_time = 5 # Base time for accessing this menu

            if music_choice == "1": # Self-Release Song
                recorded_unreleased_songs = [s for s in player.songs_written if s.is_recorded and not s.is_released]
                if not recorded_unreleased_songs:
                    print("You have no recorded songs ready for release.")
                else:
                    print("Select a song to self-release:")
                    song_select_map = {str(i+1): song for i, song in enumerate(recorded_unreleased_songs)}
                    song_display_list = [str(song) for song in recorded_unreleased_songs] # Uses Song.__str__

                    chosen_song_key = present_choices(song_display_list, "Choose song to release (0 to cancel):")

                    if chosen_song_key and chosen_song_key != "0" and chosen_song_key in song_select_map:
                        song_to_release = song_select_map[chosen_song_key]
                        release_cost = 100 # Cost for self-distribution
                        if player.money >= release_cost:
                            if input(f"Self-release '{song_to_release.title}' for ${release_cost}? (y/n) > ").lower() == 'y':
                                player.money -= release_cost
                                if song_to_release.mark_as_released(current_game_time.copy()): # Pass a copy
                                    print(f"Successfully self-released '{song_to_release.title}'. Money: ${player.money}")
                                    # Future: Add to local chart processing queue, generate initial buzz, etc.
                                    player.fame += 5 # Small fame boost for releasing
                                    adv_time += 60 # Releasing takes some time
                                else:
                                    print(f"Failed to release '{song_to_release.title}'.") # Should already be handled by mark_as_released
                                    player.money += release_cost # Refund if release failed internally
                            else:
                                print("Release cancelled.")
                        else:
                            print(f"Not enough money to release. Need ${release_cost}.")
                    elif chosen_song_key == "0":
                        print("Release process cancelled.")
                    else:
                        print("Invalid song selection for release.")
            elif music_choice == "2":
                print("Viewing released songs... (TBD)")
                # Future: List released songs, their stats, chart positions etc.
            elif music_choice == "3": # View Charts
                print("\n--- Current Music Charts ---")
                if not ACTIVE_CHARTS:
                    print("No music charts available at the moment.")
                else:
                    for i, chart_obj in enumerate(ACTIVE_CHARTS):
                        print(f"\n{i+1}. {chart_obj.name}")
                        print(chart_obj) # Relies on Chart.__str__
                input("Press Enter to continue...") # Pause to read charts
                adv_time += 5 # Time for checking charts
            # choice "0" (Back) is handled by falling through
            adv_time = max(1, adv_time) # Ensure some time passes if only browsing menus

        elif choice == "0": print("Putting phone away."); adv_time=1; break
        else: print("Invalid phone option.")
        if adv_time > 0: advance_game_time(adv_time); update_npc_locations(current_game_time); process_time_based_player_needs(player, adv_time)
        if choice in ["1","2","3", "4"] and present_choices({"1":"Continue phone","0":"Put away"},"Done?")=="0": print("Putting phone away."); break
    print("--------------------")

# --- Chart Update Function ---
def update_all_charts(player_obj, current_game_time_obj):
    """Iterates through all active charts and calls their weekly update."""
    if not hasattr(player_obj, 'songs_written') or not hasattr(player_obj, 'name') or not hasattr(player_obj, 'fame'):
        print("Error: Player object is not correctly initialized for chart updates.")
        return

    print("\n--- Weekly Chart Updates Processing ---")
    for chart in ACTIVE_CHARTS:
        chart.update_weekly(
            all_player_songs=player_obj.songs_written,
            player_name=player_obj.name,
            player_fame=player_obj.fame,
            current_game_time_obj=current_game_time_obj
        )
    print("--- Weekly Chart Updates Finished ---\n")


def handle_travel_menu(player):
    while True:
        clear_screen_ish(); city_name = player.current_location.name if player.current_location else 'N/A'
        print(f"\n--- Travel Options --- (In {city_name})\n--- {get_current_time_str()} ---")
        travel_opts = {"1":f"Travel within {city_name}", "2":"Travel to another City", "0":"Back"}
        choice = present_choices(travel_opts, "Travel Where?")
        adv_time_local = 1

        if choice == "1":
            if not player.current_poi: print("Not at a POI. Explore first."); continue
            city_obj = player.current_location
            all_city_targets = city_obj.points_of_interest + city_obj.venues
            dest_opts_list = [t for t in all_city_targets if t != player.current_poi]
            if not dest_opts_list: print("No other POIs here."); continue

            dest_disp_dict = {str(i+1): f"{t.name} ({t.category if hasattr(t,'category') else t.venue_type})" for i, t in enumerate(dest_opts_list)}
            dest_idx_key = present_choices(dest_disp_dict, "Choose destination POI:")

            if dest_idx_key and dest_idx_key in dest_disp_dict:
                chosen_dest_poi = dest_opts_list[int(dest_idx_key)-1]
                orig_id = player.current_poi.poi_id if hasattr(player.current_poi,'poi_id') else getattr(player.current_poi,'venue_id',None)
                dest_id = chosen_dest_poi.poi_id if hasattr(chosen_dest_poi,'poi_id') else getattr(chosen_dest_poi,'venue_id',None)
                if not orig_id or not dest_id: print("Error with route IDs."); continue

                conn_key = frozenset({orig_id, dest_id})
                modes_data = city_obj.intra_city_poi_connections.get(conn_key)
                if not modes_data: print(f"No direct route between {player.current_poi.name} and {chosen_dest_poi.name}."); continue

                avail_modes_choice={}; mode_map={}; c_num=1
                for mode_name, mode_info in modes_data.items():
                    if mode_name=="bike" and not player.has_bike: continue
                    avail_modes_choice[str(c_num)] = f"{mode_name.capitalize()}: {mode_info['time']} mins, ${mode_info['cost']}"
                    mode_map[str(c_num)] = (mode_name, mode_info); c_num+=1

                if not avail_modes_choice: print("No travel modes available."); continue
                mode_key = present_choices(avail_modes_choice, "Choose travel mode:")
                if mode_key and mode_key in mode_map:
                    mode_n, mode_d = mode_map[mode_key]
                    if player.money < mode_d['cost']: print("Not enough money."); continue
                    if player.get_current_gear_load() > player.get_current_gear_capacity(mode_n): print(f"Too much gear for {mode_n}."); continue

                    player.money -= mode_d['cost']; print(f"Paid ${mode_d['cost']} for {mode_n}.")
                    player.travel_within_city(chosen_dest_poi, mode_d['time'])
                    adv_time_local = mode_d['time']
                    advance_game_time(adv_time_local); update_npc_locations(current_game_time); process_time_based_player_needs(player, adv_time_local)
                    print("--------------------"); return

        elif choice == "2":
            if not player.current_poi or player.current_poi.category not in ["TRANSPORT_BUS", "TRANSPORT_AIRPORT"]:
                print("Need to be at a Bus Station or Airport. Use 'Explore current POI/Area' at a hub to buy tickets."); continue
            print("Use 'Explore current POI/Area' option from the main menu at the transport hub to find departures and buy tickets.")

        elif choice == "0": break
        else: print("Invalid travel option.")

        if adv_time_local > 0 and choice != "1":
             advance_game_time(adv_time_local); update_npc_locations(current_game_time); process_time_based_player_needs(player, adv_time_local)
    print("--------------------")

def main():
    if not setup_world(): print("World setup failed. Exiting."); return
    print("Welcome to Music-Life Sim!\nOllama for NPCs: ensure it's running & model pulled (e.g., llama3).")
    player = Player(input("Enter character's name: "))
    hometown_loc = WORLD_MAP.get("Your Hometown")
    player_home_obj = get_poi_or_venue_by_id(PLAYER_HOME_POI_ID_GLOBAL) if PLAYER_HOME_POI_ID_GLOBAL else None
    if hometown_loc and player_home_obj: player.current_location = hometown_loc; player.current_poi = player_home_obj
    else: print("Error setting start home. Defaulting...");
    update_npc_locations(current_game_time); process_time_based_player_needs(player,0)
    if GEAR_CATALOG.get("worn_acoustic_guitar"): player.add_gear(GEAR_CATALOG["worn_acoustic_guitar"])
    if GEAR_CATALOG.get("guitar_picks_assorted"): player.add_gear(GEAR_CATALOG["guitar_picks_assorted"])
    print(f"\n--- {get_current_time_str()} ---"); print(player)

    global LAST_CHART_UPDATE_DAY
    LAST_CHART_UPDATE_DAY = current_game_time.day # Initialize to current day to prevent immediate update

    while True:
        # Check for weekly chart update
        # Trigger if it's a new week (e.g. current day is a Sunday-equivalent like 7, 14, 21, 28)
        # and we haven't updated for this specific day yet.
        # Using (day % 7 == 1) to make it Monday-like, assuming day 1 is Monday.
        if (current_game_time.day % 7 == 1) and (current_game_time.day != LAST_CHART_UPDATE_DAY):
            update_all_charts(player, current_game_time.copy())
            LAST_CHART_UPDATE_DAY = current_game_time.day
            # Potentially save game or specific chart data here if needed in future

        display_hud(player, current_game_time)
        main_menu_opts = {"1":"Practice skill", "2":"Travel", "3":"Explore POI/Area", "4":"Check Gigs (City)",
                          "5":"Prep Gig", "6":"Attempt Gig", "7":"Player Stats", "8":"Talk", "9":"Eat Food", "10":"Phone"}
        if player.has_manager or player.has_pr_manager: main_menu_opts["11"]="Staff Actions"
        main_menu_opts["00"]="Adv Time (1hr)"; main_menu_opts["0"]="Quit"
        choice = present_choices(main_menu_opts, f"What would {player.name} like to do?")
        if choice is None: continue
        clear_screen_ish()
        adv_time_general = 0

        if choice == "1":
            skill = input("Skill to practice (vocals, guitar, stage_presence, songwriting)? ").lower()
            try: hrs = int(input(f"Hours for {skill}? ")); assert hrs > 0
            except: print("Invalid hours."); continue
            player.practice_skill(skill, hrs); adv_time_general = hrs*60
        elif choice == "2": handle_travel_menu(player); continue
        elif choice == "3":
            poi = player.current_poi; loc = player.current_location
            print(f"\n--- Exploring {poi.name if poi else loc.name} ---\nDesc: {poi.description if poi else loc.description}")
            if poi:
                interactions = list(poi.interaction_options)
                if isinstance(poi, Venue) and any(e.is_active and (e.are_preparations_complete() or not e.preparation_tasks_required) and 16 <= current_game_time.hour <= 19 for e in poi.events_hosted):
                    if "Hold Pre-Show Autograph Signing (1 hour)" not in interactions: interactions.append("Hold Pre-Show Autograph Signing (1 hour)")
                if poi.category == "OFFICE_NEWS_AGENCY" and player.active_opportunities.get("interview_city_chronicle") == "pending_player_action":
                    if "Attend Scheduled Interview" not in interactions: interactions.append("Attend Scheduled Interview")
                if interactions:
                    idx_choice_str = present_choices(interactions, f"Actions at {poi.name}:")
                    if idx_choice_str and idx_choice_str.isdigit():
                        chosen_text = interactions[int(idx_choice_str)-1]; print(f"Chose: {chosen_text}")
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
                                if not display: print("Out of stock.")
                                else:
                                    buy_key = present_choices(display, f"Items at {poi.name}: (0 to cancel)")
                                    if buy_key and buy_key!="0" and buy_key in item_map:
                                        sel_item=item_map[buy_key]
                                        if player.money>=sel_item.cost:
                                            if player.can_carry_gear(sel_item): player.money-=sel_item.cost; player.add_gear(sel_item); print(f"Money: ${player.money}")
                                            else: print(f"Can't carry {sel_item.name}.")
                                        else: print(f"Not enough money for {sel_item.name}.")
                                    elif buy_key=="0": print("Cancelled purchase.")
                            else: print("Nothing for sale currently.")
                            adv_time_general = 15; action_taken_custom_time = True
                        elif poi.category in ["TRANSPORT_BUS", "TRANSPORT_AIRPORT"] and chosen_text == "View Departures & Buy Tickets":
                            connections = loc.travel_connections
                            if not connections: print(f"No inter-city routes from {loc.name}.")
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

                                            # --- Track Tour Expenses ---
                                            if player.current_tour_id and player.current_tour_id in player.tour_ledgers:
                                                tour_ledger = player.tour_ledgers[player.current_tour_id]
                                                if tour_ledger["status"] == "ongoing":
                                                    next_tour_gig_city = None
                                                    for gig_detail_item in tour_ledger.get("gigs_details", []):
                                                        if not gig_detail_item.get("performed", False):
                                                            if gig_detail_item["city_name"] == chosen_dest_name_from_menu:
                                                                next_tour_gig_city = gig_detail_item["city_name"]
                                                                break
                                                    if next_tour_gig_city:
                                                        tour_ledger["expenses"] += cost_of_travel
                                                        print(f"LOG: Travel cost ${cost_of_travel} for '{chosen_dest_name_from_menu}' added to expenses for tour '{tour_ledger['name']}'.")
                                            # --- End Track Tour Expenses ---

                                            dest_loc_obj = WORLD_MAP.get(chosen_dest_name_from_menu)
                                            if dest_loc_obj:
                                                travel_duration_hours = chosen_travel_details['time_hours']
                                                travel_duration_minutes = travel_duration_hours * 60
                                                travel_start_time = current_game_time.copy()
                                                travel_end_time = current_game_time.copy(); travel_end_time.advance_time(travel_duration_minutes)
                                                player.schedule.add_event(start_time=travel_start_time, end_time=travel_end_time, description=f"Travel: {loc.name} to {chosen_dest_name_from_menu}", category="Travel", details={"from_city_id": loc.id if hasattr(loc,'id') else loc.name, "to_city_id": dest_loc_obj.id if hasattr(dest_loc_obj,'id') else dest_loc_obj.name, "transport_poi_id": poi.poi_id})
                                                player.travel(dest_loc_obj, travel_duration_hours)
                                                adv_time_general = travel_duration_minutes; action_taken_custom_time = True
                                                print(f"Ticket bought. Travelled to {chosen_dest_name_from_menu}.")
                                            else: print(f"Error: Dest city '{chosen_dest_name_from_menu}' not found."); player.money += cost_of_travel
                                        else: print(f"Not enough money. Need ${chosen_travel_details['cost']}.")
                                    else: print("Travel cancelled.")
                            adv_time_general = 20 if not action_taken_custom_time else adv_time_general; action_taken_custom_time=True
                        elif (poi.category == "HOME" and chosen_text == "Rest (8 hours)") or \
                             (poi.category == "ACCOMMODATION_CHEAP" and chosen_text.startswith("Sleep")):
                            hours_to_rest = 8; can_sleep_here = False
                            if poi.category == "HOME": can_sleep_here = True
                            elif poi.category == "ACCOMMODATION_CHEAP":
                                if player.rented_accommodation_info and player.rented_accommodation_info["poi_id"] == poi.poi_id: can_sleep_here = True
                                else: print("You haven't rented a room here or it expired.")
                            if can_sleep_here:
                                comfort_eff=0; hunger_eff=0
                                if player.comfort < 25: comfort_eff=-0.2; elif player.comfort < 50: comfort_eff=-0.1
                                if player.hunger > 75: hunger_eff=-0.2; elif player.hunger > 50: hunger_eff=-0.1
                                eff_rest_q = max(0.05, poi.rest_quality + comfort_eff + hunger_eff)
                                energy_g = int(hours_to_rest*10*eff_rest_q); stress_chg = int(hours_to_rest*poi.stress_modifier_hourly)
                                if poi.category == "HOME": player.homesickness=max(0,player.homesickness-(hours_to_rest*10)); player.comfort=min(100,player.comfort+(hours_to_rest*2))
                                player.energy=min(100,player.energy+energy_g); player.stress=max(0,player.stress+stress_chg)
                                print(f"Rested for {hours_to_rest}h. Energy: {player.energy}, Stress: {player.stress}.")
                                if poi.category == "ACCOMMODATION_CHEAP": player.rented_accommodation_info = None
                                adv_time_general = hours_to_rest*60; action_taken_custom_time = True
                        elif poi.category == "ACCOMMODATION_CHEAP" and chosen_text.startswith("Rent Room"):
                            try:
                                rent_cost = int(chosen_text.split('$')[1].split('/')[0])
                                if player.money>=rent_cost:
                                    player.money-=rent_cost;
                                    co_time=current_game_time.copy(); co_time.advance_time(24*60)
                                    player.rented_accommodation_info = {"poi_id":poi.poi_id, "checkout_time_obj":co_time}
                                    print(f"Rented room for ${rent_cost} until {co_time}. Money: ${player.money}.")
                                else: print(f"Not enough money. Need ${rent_cost}.")
                            except: print("Error parsing rent cost.")
                            adv_time_general = 10; action_taken_custom_time = True
                        elif poi.category == "HOME" and chosen_text == "Write a new song":
                            print("\n--- Write a New Song ---")
                            song_title = input("Enter a title for your new song: ")
                            if not song_title.strip():
                                print("Songwriting cancelled. You need a title.")
                                adv_time_general = 5 # Small time for cancelling
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
                                print("\nChoose a genre for your song:")
                                genre_choice_key = present_choices(genre_choices, "Select Genre:")
                                song_genre = "Indie"
                                if genre_choice_key and genre_choice_key != "0" and genre_choice_key in genre_choices:
                                    song_genre = genre_choices[genre_choice_key]
                                elif genre_choice_key == "0": print("Defaulting genre to Indie.")
                                else: print("Invalid genre choice, defaulting to Indie.")

                                new_song = Song(title=song_title, author=player.name, genre=song_genre, originality=originality, catchiness=catchiness, lyrical_depth=lyrical_depth, music_complexity=music_complexity)
                                player.songs_written.append(new_song)
                                songwriting_time_minutes = random.randint(120, 300)
                                skill_gain_factor = songwriting_time_minutes / 60.0
                                player.skills["songwriting"] = round(player.skills.get("songwriting", 0) + (0.15 * skill_gain_factor) + (new_song.song_quality * 0.1), 2)
                                player.energy = max(0, player.energy - random.randint(20, 40))
                                player.stress = max(0, player.stress - random.randint(0,10) + int(5 * (1-new_song.song_quality)))
                                player.comfort = min(100, player.comfort + random.randint(0,10))
                                print(f"\nYou finished writing a new song:\n  {new_song}")
                                print(f"It took you {songwriting_time_minutes // 60}h {songwriting_time_minutes % 60}m. Your songwriting skill is now {player.skills['songwriting']:.2f}.")
                                print(f"Energy: {player.energy}, Stress: {player.stress}, Comfort: {player.comfort}")
                                adv_time_general = songwriting_time_minutes
                            action_taken_custom_time = True
                        elif poi.category == "STUDIO_RECORDING" and chosen_text == "Book recording session":
                            studio_hourly_rate = getattr(poi, 'hourly_rate', 50)
                            studio_quality = getattr(poi, 'studio_quality', 0.5)
                            unrecorded_songs = [s for s in player.songs_written if not s.is_recorded]
                            if not unrecorded_songs:
                                print("You have no unrecorded songs to work on!"); adv_time_general = 5
                            else:
                                print("Which song to record?"); song_to_record_choices = {str(i+1): s for i,s in enumerate(unrecorded_songs)}
                                song_to_record_display = [f"{s.title} (Q: {s.song_quality:.2f})" for s in unrecorded_songs]
                                song_key = present_choices(song_to_record_display, "Choose song (0 to cancel):")
                                if song_key and song_key != "0" and song_key in song_to_record_choices:
                                    song_to_record = song_to_record_choices[song_key]
                                    try:
                                        rec_hours_input = input(f"Hours for '{song_to_record.title}'? (${studio_hourly_rate}/hr, StudioQ: {studio_quality*100:.0f}%): ")
                                        if not rec_hours_input.isdigit() or int(rec_hours_input) <=0: print("Invalid hours."); raise ValueError
                                        rec_hours = int(rec_hours_input)
                                        rec_cost = rec_hours * studio_hourly_rate
                                        if player.money >= rec_cost:
                                            player.money -= rec_cost; rec_mins = rec_hours*60
                                            rec_start = current_game_time.copy(); rec_end = rec_start.copy(); rec_end.advance_time(rec_mins)
                                            player.schedule.add_event(rec_start,rec_end,f"Recording '{song_to_record.title}' at {poi.name}","Recording",details={"poi_id":poi.poi_id,"song_id":song_to_record.song_id,"cost":rec_cost,"hours":rec_hours})

                                            # Determine recording quality
                                            base_rec_q = studio_quality * 0.6 # Studio is a major factor
                                            # Skill factor - average of relevant skills (e.g. vocals, primary instrument for song's genre)
                                            # This is simplified; a real system would check which instruments are on the song.
                                            perf_skill_avg = (player.skills.get("vocals",0) + player.skills.get("guitar",0)) / 20.0 # Assuming skills 0-10, map to 0-0.5
                                            base_rec_q += perf_skill_avg * 0.3 # Skills add up to 30% of quality
                                            base_rec_q += random.uniform(-0.1, 0.1) # Randomness
                                            final_rec_quality = round(max(0.1, min(1.0, base_rec_q + (song_to_record.song_quality * 0.1))), 2) # Song quality slight boost

                                            song_to_record.mark_as_recorded(final_rec_quality)
                                            print(f"Recorded '{song_to_record.title}' (RecQ: {final_rec_quality:.2f}). Cost ${rec_cost}. Money: ${player.money}")
                                            adv_time_general = rec_mins
                                        else: print(f"Not enough money. Need ${rec_cost}.")
                                    except ValueError: print("Recording cancelled.")
                                else: print("Recording cancelled.")
                            action_taken_custom_time = True
                        elif poi.category == "REHEARSAL_STUDIO" and chosen_text.startswith("Book Rehearsal Slot"):
                            action_taken_custom_time = True # Already handles its own time
                        elif poi.category == "OFFICE_RECORD_LABEL" and chosen_text.startswith("Submit Demo"):
                            print("\n--- Submit Demo to Record Label ---")
                            adv_time_general = 10; action_taken_custom_time = True # Base time for interaction
                            if player.fame < getattr(poi, 'min_fame_to_submit', 0):
                                print(f"{poi.name} isn't interested in demos from artists at your current level of fame (Need {getattr(poi, 'min_fame_to_submit', 0)} fame).")
                            elif not player.songs_written:
                                print("You have no songs to create a demo from!")
                            else:
                                recorded_songs = [s for s in player.songs_written if s.is_recorded]
                                if not recorded_songs:
                                    print("You have songs, but none are recorded. A demo needs a recording.")
                                else:
                                    print("Select a recorded song for your demo:")
                                    song_choices_dict = {str(i+1): song for i, song in enumerate(recorded_songs)}
                                    song_display_list = [f"{s.title} (Genre: {s.genre}, CompQ: {s.song_quality:.2f}, RecQ: {s.recording_quality:.2f})" for s in recorded_songs]

                                    chosen_song_key = present_choices(song_display_list, "Choose song for demo (0 to cancel):")

                                    if chosen_song_key and chosen_song_key != "0": # present_choices returns 1-based string index
                                        chosen_song_idx = int(chosen_song_key) -1
                                        if 0 <= chosen_song_idx < len(recorded_songs):
                                            chosen_song = recorded_songs[chosen_song_idx]
                                            label_poi = poi

                                            print(f"You submit your demo of '{chosen_song.title}' to {label_poi.name}.")
                                            adv_time_general = 60

                                            success_score = 0
                                            success_score += chosen_song.song_quality * 35  # Max 35
                                            success_score += chosen_song.recording_quality * 35 # Max 35
                                            success_score += min(30, player.fame / 5) # Max 30 for fame up to 150

                                            if label_poi.genres_preferred and chosen_song.genre in label_poi.genres_preferred: success_score += 20
                                            elif not label_poi.genres_preferred: success_score += 5

                                            outcome_roll = random.randint(0, 100)

                                            print(f"(Debug: Demo Score: {success_score:.0f}, Label Roll: {outcome_roll})")

                                            if success_score > outcome_roll + 50 :
                                                print(f"{label_poi.name} is very impressed! \"This is great stuff, {player.name}! We need to talk. My office, tomorrow?\"")
                                                player.fame += 25
                                                # Future: schedule a meeting event, potential record deal
                                            elif success_score > outcome_roll + 20:
                                                print(f"{label_poi.name} likes what they hear. \"Interesting... we'll be in touch if something opens up.\"")
                                                player.fame += 10
                                            elif success_score > outcome_roll - 20:
                                                 print(f"{label_poi.name} listens politely. \"Thanks for the submission. We'll keep it on file.\"")
                                                 player.fame += 2
                                            else:
                                                print(f"{label_poi.name} doesn't seem too interested. \"Uh, yeah, thanks. We get a lot of these.\"")
                                        else: print("Invalid song selection for demo.")
                                    else: print("Demo submission cancelled.")
                            action_taken_custom_time = True
                        elif poi.category == "SHOP_MUSIC" and chosen_text == "Repair Gear": print("Repair Gear logic TBD."); adv_time_general = 45; action_taken_custom_time = True
                        elif poi.category == "SHOP_FOOD" and chosen_text == "Buy Food Items": print("Buy Food (Grocery) logic TBD."); adv_time_general = 10; action_taken_custom_time = True
                        elif poi.category == "FOOD_FASTFOOD":
                            selected_menu_item_data=None
                            for mi in poi.menu_items:
                                if mi["display_text"] == chosen_text: selected_menu_item_data=mi; break
                            if selected_menu_item_data:
                                cost=selected_menu_item_data["cost"]; eff=selected_menu_item_data["effects"]
                                if player.money>=cost:
                                    player.money-=cost; player.hunger=max(0,player.hunger+eff.get("hunger",0)); player.energy=min(100,player.energy+eff.get("energy",0)); player.comfort=min(100,max(0,player.comfort+eff.get("comfort",0)))
                                    print(f"Consumed {GEAR_CATALOG.get(selected_menu_item_data['item_id']).name if GEAR_CATALOG.get(selected_menu_item_data['item_id']) else 'food'}. Stats updated.")
                                else: print(f"Not enough money for {chosen_text}.")
                            else: print(f"Action '{chosen_text}' unclear at fast food.")
                            adv_time_general = 20; action_taken_custom_time = True
                        elif poi.category == "OFFICE_NEWS_AGENCY" and chosen_text == "Attend Scheduled Interview": action_taken_custom_time = True
                        elif poi.category == "OFFICE_PR_AGENCY" and chosen_text == "Inquire about PR representation": action_taken_custom_time = True
                        elif poi.category == "SHOP_BARBER": action_taken_custom_time = True

                        if not action_taken_custom_time: adv_time_general = 15
                else: print("Not much to do here specifically."); adv_time_general = 10
            else:
                if loc.venues: print("\nVenues:"); [print(f"  - {v.name}") for v in loc.venues]
                if loc.points_of_interest: print("\nPOIs:"); [print(f"  - {p.name}") for p in loc.points_of_interest]
                adv_time_general = 15
        elif choice == "4":
            print(f"\n--- Gigs in {player.current_location.name} ---")
            gigs = [e for e in player.current_location.get_all_events_at_location() if e.is_active]
            if not gigs: print("No gigs now.")
            else: [print(f"\n{i+1}. {g.name} ({g.event_type}) at {g.location.name}\n   Desc: {g.description}\n   Reqs: {g.required_skills}\n   Fame: {g.fame_reward}, Payout: ${g.payout}" + (f"\n   Prep: {', '.join([t for t,d in g.preparation_tasks_required.items() if not d]) if any(not d for d in g.preparation_tasks_required.values()) else ' Prep Complete!'}" if g.preparation_tasks_required else "")) for i,g in enumerate(gigs)]
            adv_time_general = 5
        elif choice == "5":
            all_gigs_prep = player.current_location.get_all_events_at_location()
            preparable = [e for e in all_gigs_prep if e.is_active and e.preparation_tasks_required and not e.are_preparations_complete()]
            if not preparable: print("No gigs need prep or all preps done.")
            else:
                opts_prep={str(i+1):e for i,e in enumerate(preparable)}; disp_prep=[f"{e.name} (at {e.location.name}) - Pending: {', '.join([t for t,d in e.preparation_tasks_required.items() if not d])}" for e in preparable]
                gig_key_prep = present_choices(disp_prep, "Prepare for which gig?")
                if gig_key_prep and gig_key_prep in opts_prep:
                    event_prep=opts_prep[gig_key_prep]; tasks_pending_prep={str(i+1):task for i,(task,done) in enumerate(event_prep.preparation_tasks_required.items()) if not done}
                    if not tasks_pending_prep: print(f"All preps for {event_prep.name} done."); continue
                    task_disp_prep = [name for name in tasks_pending_prep.values()]
                    task_key_prep = present_choices(task_disp_prep, f"Task for {event_prep.name}?")
                    if task_key_prep and task_key_prep in tasks_pending_prep:
                        task_to_do_prep = tasks_pending_prep[task_key_prep]; print(f"Completing: {task_to_do_prep}..."); event_prep.complete_preparation_task(task_to_do_prep)
                        adv_time_general = 120
        elif choice == "6":
            all_gigs_perform = player.current_location.get_all_events_at_location()
            performable = [e for e in all_gigs_perform if e.is_active and (not e.preparation_tasks_required or e.are_preparations_complete())]
            if not performable: print("No gigs ready to perform here.")
            else:
                opts_gig={str(i+1):e for i,e in enumerate(performable)}; disp_gig=[f"{e.name} (at {e.location.name})" for e in performable]
                gig_key_perform = present_choices(disp_gig, "Attempt which gig?")
                if gig_key_perform and gig_key_perform in opts_gig:
                    event_perform = opts_gig[gig_key_perform]
                    can_perform_bool, message_str, _ = event_perform.can_perform(player)
                    if not can_perform_bool: print(f"Cannot perform {event_perform.name}: {message_str}"); adv_time_general = 60
                    else:
                        print(f"\n--- Select Setlist for {event_perform.name} --- \nRequires {event_perform.songs_required_count} song(s).")
                        if not player.songs_written or len(player.songs_written) < event_perform.songs_required_count:
                            print("You don't have enough songs for this event!"); continue

                        songs_disp = [str(s) for s in player.songs_written] # Use Song.__str__ for detailed display
                        chosen_setlist = []
                        for i in range(event_perform.songs_required_count):
                            song_idx_str = present_choices(songs_disp, f"Choose song {i+1}/{event_perform.songs_required_count} (0 to cancel):")
                            if not song_idx_str or song_idx_str == "0": chosen_setlist = []; break
                            try:
                                chosen_song_idx = int(song_idx_str)-1
                                if 0 <= chosen_song_idx < len(player.songs_written): chosen_setlist.append(player.songs_written[chosen_song_idx])
                                else: print("Invalid song."); chosen_setlist = []; break
                            except ValueError: print("Invalid input."); chosen_setlist = []; break

                        if len(chosen_setlist) == event_perform.songs_required_count:
                            print("\nSetlist finalized."); [print(f" {j+1}. {s.title}") for j,s in enumerate(chosen_setlist)]
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
                                        print(f"\n--- Tour '{tour_ledger['name']}' Concluded! ---")
                                        print(f"Total Income: ${tour_ledger['income']}")
                                        print(f"Total Expenses: ${tour_ledger['expenses']}")
                                        print(f"Net Profit/Loss: ${net_profit}")
                                        tour_ledger["status"] = "completed"
                                        player.current_tour_id = None
                                        player.tour_fatigue = max(0, player.tour_fatigue - 25)
                                        print(f"You can finally rest a bit! Tour fatigue reduced to {player.tour_fatigue}.")
                            else:
                                adv_time_general = 60
                                owner = getattr(event_perform.location,'owner_npc_id',None)
                                if owner and isinstance(owner, NPC): owner.update_relationship(-10); owner.add_memory(f"{player.name} failed gig '{event_perform.name}'.")
                        else: print("Gig cancelled due to setlist."); adv_time_general = 15
        elif choice == "7": print("\n--- Player Stats ---"); print(player); print(get_current_time_str()); adv_time_general = 1
        elif choice == "8":
            npcs_here = [n for n in NPC_REGISTRY.values() if n.current_location == player.current_poi or n.current_location == player.current_location]
            if not npcs_here: print("No one around.")
            else:
                npc_choices = {str(i+1):n for i,n in enumerate(npcs_here)}; npc_disp = [f"{n.name}" for n in npcs_here]
                npc_key = present_choices(npc_disp, "Talk to whom?")
                if npc_key and npc_key in npc_choices: talk_to_npc_instance(player, npc_choices[npc_key])
        elif choice == "9":
            food_items = [item for item in player.gear_inventory if item.gear_type == "FOOD"]
            if not food_items: print("No food in inventory.")
            else:
                food_opts={str(i+1):item for i,item in enumerate(food_items)}
                food_disp=[f"{item.name} (Hunger: -{item.hunger_reduction}, Energy: +{item.energy_boost})" + (f", Comfort: {item.get_property('comfort_effect'):+}" if item.get_property("comfort_effect") else "") for item in food_items]
                food_key = present_choices(food_disp, "Eat which item? (0 to cancel)")
                if food_key and food_key!="0" and food_key in food_opts:
                    item=food_opts[food_key]; player.hunger=max(0,player.hunger-item.hunger_reduction); player.energy=min(100,player.energy+item.energy_boost)
                    player.comfort=min(100,max(0,player.comfort+(item.get_property("comfort_effect") or 0)))
                    player.remove_gear(item); adv_time_general=15
                    print(f"Ate {item.name}. Hunger: {player.hunger}, Energy: {player.energy}, Comfort: {player.comfort}")
                elif food_key=="0": print("Cancelled eating.")
        elif choice == "10": handle_phone_menu(player)
        elif choice == "11":
            if not (player.has_manager or player.has_pr_manager): print("No staff yet.")
            else:
                print("\n--- Staff Actions ---"); staff_opts = {}; idx = 1
                if player.has_manager:
                    staff_opts[str(idx)]="Talk to Artist Manager"; idx+=1
                    staff_opts[str(idx)]="Discuss Tour Opportunities"; idx+=1
                    staff_opts[str(idx)]="Review Past Tours"; idx+=1
                if player.has_pr_manager: staff_opts[str(idx)]="Check PR Opportunities"; idx+=1
                staff_opts["0"]="Back"
                sub_choice = present_choices(staff_opts, "Staff action:")
                action_text = staff_opts.get(sub_choice); adv_min_staff = 0
                if action_text == "Talk to Artist Manager": print("Discussing strategy... (TBD)"); adv_min_staff=30
                elif action_text == "Discuss Tour Opportunities":
                    adv_min_staff = 0
                    if not player.has_manager: print("Need a manager first.")
                    elif player.active_tour_offer:
                        if input(f"Manager: \"We have the '{player.active_tour_offer['name']}' tour offer. Finalize it? (y/n)\"").lower() == 'y':
                            adv_min_staff = 30; tour_package_gigs = player.active_tour_offer['gigs']; tour_id = player.active_tour_offer['tour_id']
                            print("\nManager: \"Booking the tour...\""); scheduled_gigs_count=0
                            player.current_tour_id = tour_id
                            player.tour_ledgers[tour_id] = {"name": player.active_tour_offer['name'], "expenses":0, "income":0, "status":"ongoing", "gigs_details":[]}

                            current_tour_gig_details_list = []
                            for gig_data in tour_package_gigs:
                                venue = get_poi_or_venue_by_id(gig_data['venue_id'])
                                if not venue or not isinstance(venue, Venue): print(f"Skipping gig, bad venue: {gig_data['venue_id']}"); continue
                                gig_event_type = gig_data['event_type']
                                gig_skills = gig_data.get('required_skills_override', Event.EVENT_TYPES.get(gig_event_type,{}).get('required_skills', {"vocals":1,"guitar":1}))
                                new_event = Event(name=f"Tour: {player.name} at {venue.name}", location=venue, event_type=gig_event_type, required_skills=gig_skills, description=f"Tour stop in {gig_data['city_name']}", specific_payout=gig_data['estimated_payout'], is_tour_gig=True)

                                gig_start_time = current_game_time.copy()
                                gig_start_time.advance_time(minutes=gig_data['days_offset'] * 24 * 60)
                                gig_start_time.hour = 20; gig_start_time.minute = 0
                                gig_end_time = gig_start_time.copy(); gig_end_time.advance_time(minutes=3*60)

                                venue.add_event(new_event)
                                player.schedule.add_event(gig_start_time, gig_end_time, new_event.name, "Tour Gig", details={"venue_id":venue.venue_id, "event_id":new_event.name, "tour_id": tour_id})
                                current_tour_gig_details_list.append({"venue_id": venue.venue_id, "city_name": gig_data['city_name'], "scheduled_date_str": gig_start_time.get_time_string_for_schedule(), "event_name": new_event.name, "performed": False})
                                print(f"Booked: {new_event.name} in {gig_data['city_name']} on {gig_start_time.get_time_string_for_schedule()}")
                                scheduled_gigs_count+=1
                            player.tour_ledgers[tour_id]["gigs_details"] = current_tour_gig_details_list
                            if scheduled_gigs_count > 0: print(f"Manager: \"Tour '{player.tour_ledgers[tour_id]['name']}' booked!\"")
                            else: print("Manager: \"Couldn't book any gigs for that tour.\""); del player.tour_ledgers[tour_id]; player.current_tour_id = None
                            player.active_tour_offer = None
                            if scheduled_gigs_count > 0 and tour_id not in player.completed_tour_ids : player.completed_tour_ids.append(tour_id)
                        else: print("Manager: \"Okay, offer stands.\""); adv_min_staff=5
                    else:
                        print("Manager: \"Let me see what tours I can cook up...\""); adv_min_staff = 20
                        try:
                            with open("game_data/tours.json", 'r') as f: all_tour_templates = json.load(f)
                        except Exception as e: print(f"Manager: \"Tour planner error: {e}\""); all_tour_templates = []
                        eligible_tours = [t for t in all_tour_templates if t['min_fame'] <= player.fame <= t['max_fame'] and t['tour_id'] not in player.completed_tour_ids]
                        if not eligible_tours: print("Manager: \"Nothing quite right for you now.\"")
                        else:
                            tour_template = random.choice(eligible_tours)
                            print(f"\nManager: \"How about this: '{tour_template['name']}'. {tour_template['description']}\"")
                            fleshed_gigs = []; possible_to_book = True; cumulative_day_offset_for_proposal = 0
                            for leg, gig_tmpl in enumerate(tour_template['gig_templates']):
                                city = random.choice(gig_tmpl['city_options'])
                                venues_in_city = [v for v in WORLD_MAP[city].venues if v.venue_type in gig_tmpl['venue_type_options']] if WORLD_MAP.get(city) else []
                                if not venues_in_city: possible_to_book = False; break
                                venue = random.choice(venues_in_city)
                                cumulative_day_offset_for_proposal += random.randint(gig_tmpl['days_offset_min'], gig_tmpl['days_offset_max'])
                                fleshed_gigs.append({'venue_id': venue.venue_id, 'venue_name': venue.name, 'event_type': gig_tmpl['event_type'], 'days_offset': cumulative_day_offset_for_proposal, 'city_name': city, 'estimated_payout': gig_tmpl['base_payout_estimate'], 'required_skills_override': gig_tmpl.get('required_skills_override')})
                            if possible_to_book and fleshed_gigs:
                                print("Proposed Itinerary:")
                                est_total_pay = sum(g['estimated_payout'] for g in fleshed_gigs)
                                for i,g in enumerate(fleshed_gigs): print(f"  Gig {i+1}: {g['event_type']} at {g['venue_name']} in {g['city_name']} (~{g['days_offset']} days). Est. ${g['estimated_payout']}")
                                print(f"Total est. payout: ${est_total_pay}. Expenses on you.")
                                if present_choices({"1":"Accept offer","2":"Decline"},"Accept tour?") == "1":
                                    player.active_tour_offer = {"tour_id":tour_template['tour_id'], "name":tour_template['name'], "gigs":fleshed_gigs}
                                    print("Manager: \"Great! Confirm with me again to finalize bookings.\""); adv_min_staff+=10
                                else: player.active_tour_offer=None; print("Manager: \"Okay, maybe next time.\""); adv_min_staff+=5
                            else: print("Manager: \"Couldn't work out a solid itinerary for that one.\"")
                elif action_text == "Review Past Tours":
                    print("\n--- Past Tour Review ---")
                    completed_tours = {tid: tdata for tid, tdata in player.tour_ledgers.items() if tdata.get("status") == "completed"}
                    if not completed_tours:
                        print("Manager: \"You haven't completed any tours for us to review yet.\"")
                    else:
                        tour_choices_dict = {str(i+1): tid for i, tid in enumerate(completed_tours.keys())}
                        # Corrected display list generation
                        ordered_tour_display_list = []
                        for key_idx_str in sorted(tour_choices_dict.keys(), key=int): # Sort keys numerically
                            tid_val = tour_choices_dict[key_idx_str]
                            ordered_tour_display_list.append(f"{completed_tours[tid_val]['name']} (ID: {tid_val})")

                        tour_key_display_idx = present_choices(ordered_tour_display_list, "Which tour to review? (0 to cancel)")

                        if tour_key_display_idx and tour_key_display_idx != "0":
                            # Convert display index back to actual tour_id from the sorted list of keys
                            actual_tour_id_key = sorted(tour_choices_dict.keys(), key=int)[int(tour_key_display_idx)-1]
                            chosen_tour_id = tour_choices_dict[actual_tour_id_key]

                            ledger = player.tour_ledgers[chosen_tour_id]
                            net_profit = ledger['income'] - ledger['expenses']
                            print(f"\nSummary for Tour: '{ledger['name']}'")
                            print(f"  Total Income: ${ledger['income']}")
                            print(f"  Total Expenses: ${ledger['expenses']}")
                            print(f"  Net Profit/Loss: ${net_profit}")
                            print("  Gigs Performed:")
                            for gig_d in ledger.get("gigs_details",[]):
                                if gig_d.get("performed"):
                                    print(f"    - {gig_d['event_name']} in {gig_d['city_name']}")
                        elif tour_key_display_idx == "0": print("Cancelled review.")
                        else: print("Invalid selection for tour review.")
                    adv_min_staff = 10
                elif action_text == "Check PR Opportunities":
                    print("Checking with PR Manager..."); adv_min_staff=30
                    chron_key="interview_city_chronicle"; chron_fame_req=player.OPPORTUNITY_FAME_THRESHOLDS.get(chron_key,float('inf'))
                    op_status=player.active_opportunities.get(chron_key)
                    if op_status=="completed": print("PR: 'Chronicle interview done!'")
                    elif op_status=="pending_player_action": print("PR: 'Chronicle interview ready when you are.'")
                    elif player.fame>=chron_fame_req: player.active_opportunities[chron_key]="pending_player_action"; print("PR: 'Good news! Chronicle interview lined up!'")
                    else: print(f"PR: 'Quiet on press front. Need ~{chron_fame_req} fame for Chronicle.'")
                elif action_text == "Back to Main Menu": adv_min_staff=0
                else: print("Invalid staff action.")
                if adv_min_staff > 0: adv_time_general = adv_min_staff
        elif choice == "00": adv_time_general = 60
        elif choice == "0": print("Thanks for playing!"); break
        else: print("Invalid choice.")

        if adv_time_general > 0: advance_game_time(adv_time_general); update_npc_locations(current_game_time); process_time_based_player_needs(player, adv_time_general)
        print(f"\n--- {get_current_time_str()} ---")
        if choice in ["1","3","4","5","7","10","11","00"] and not ("LLM Error" in locals().get('npc_response','')):
            event_outcome = check_for_random_event(player, player.current_poi.name if player.current_poi else player.current_location.name)
            if event_outcome.get("event_triggered"):
                ev_mins = event_outcome.get("minutes_passed",15)
                if ev_mins > 0: advance_game_time(ev_mins); update_npc_locations(current_game_time); process_time_based_player_needs(player,ev_mins)
                player.check_and_unlock_staff()

if __name__ == "__main__":
    main()

[end of main.py]
