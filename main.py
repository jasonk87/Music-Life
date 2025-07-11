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
from game.feedback_generator import generate_feedback_for_song, SOURCES # Import feedback generator and SOURCES

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
            props = poi_data.get("properties", {}).copy() # Use a copy to safely pop items

            # Extract known properties that are not direct __init__ args but are handled post-init
            shop_inventory_ids = props.pop("shop_inventory_item_ids", None)
            menu_items_data = props.pop("menu_items", None)
            owner_npc_id_temp = props.pop("owner_npc_id", None) # Pop owner_npc_id, store temporarily if needed for later assignment
            # Any other similar properties from JSON that POI handles specially can be popped here.

            # Now, props only contains arguments that PointOfInterest.__init__ expects
            poi = PointOfInterest(poi_id=poi_data["poi_id"], name=poi_data["name"], description=poi_data["description"],
                                  category=poi_data["category"], interaction_options=list(poi_data.get("interaction_options", [])),
                                  parent_location_id=location_obj.name, **props)

            if shop_inventory_ids is not None: # Use the popped variable
                poi.shop_inventory_item_ids = list(shop_inventory_ids)

            if menu_items_data is not None: # Use the popped variable
                poi.menu_items = list(menu_items_data)
                if poi.category == "FOOD_FASTFOOD" and not poi.interaction_options: poi.interaction_options = [item["display_text"] for item in poi.menu_items]
            if poi.poi_id == "citycenter_indiehits_records":
                poi.interaction_options = [
                    f"Submit Demo (requires {poi.min_fame_to_submit} fame)",
                    "Talk to A&R Rep (requires Manager)"
                    # "Meet with A&R Representative" will be added dynamically if signed
                    # "Propose Album to Label" will be added dynamically if signed
                ]
            location_obj.add_poi(poi)
        for venue_data in city_def_data.get("venues", []):
            props = venue_data.get("properties", {}).copy() # Use a copy to safely pop items

            # Extract known properties that are not direct __init__ args but are handled post-init
            # For Venues, 'owner_npc_id' is one such property if it exists in JSON.
            # Other venue-specific JSON properties not in __init__ could be popped here too.
            owner_npc_id_temp_venue = props.pop("owner_npc_id", None)
            booking_fee_prop = props.pop("booking_fee", 50) # Pop booking_fee as it's handled separately
            allows_player_booking_prop = props.pop("allows_player_booking", True) # Pop allows_player_booking

            venue = Venue(venue_id=venue_data["venue_id"], name=venue_data["name"], description=venue_data["description"],
                          venue_type=venue_data["venue_type"], category=venue_data["category"],
                          capacity=venue_data["capacity"], prestige=venue_data["prestige"],
                          parent_location_id=location_obj.name, **props) # Remaining props passed

            venue.events_hosted_ids_from_json = list(venue_data.get("events_hosted_ids", []))
            venue.booking_fee = booking_fee_prop
            venue.allows_player_booking = props.get("allows_player_booking", True)
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

    ACTIVE_CHARTS.clear()
    hometown_chart = Chart(name="Hometown Local Hits", max_size=10, chart_genre_preference="Indie")
    city_chart = Chart(name="City Center Top Tracks", max_size=20)
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
    if val == 0:
        return "Bald"
    elif val <= 2:
        return "Very Short"
    elif val <= 4:
        return "Short"
    elif val <= 6:
        return "Medium"
    elif val <= 8:
        return "Long"
    else:
        return "Very Long"

def get_beard_length_description(val):
    if val == 0:
        return "Clean-shaven"
    elif val <= 2:
        return "Stubble"
    elif val <= 4:
        return "Short Beard"
    elif val <= 6:
        return "Medium Beard"
    elif val <= 8:
        return "Long Beard"
    else:
        return "Wizard Beard"

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
            unread_feedback_count = sum(1 for f_item in player.feedback_received if not f_item.get("read", False))
            pending_offers_count = sum(1 for offer in player.active_label_offers if offer.get("status") == "pending_player_decision")

            music_opts = {
                "1": "Self-Release Song",
                "2": "Promote Released Song",
                "3": "Plan a Local Gig",
                "4": f"Check Reviews/Fan Mail{' (NEW)' if unread_feedback_count > 0 else ''}",
                "5": "View Charts",
                "6": f"View Label Offers{' (NEW)' if pending_offers_count > 0 else ''}",
                "7": "View Released Songs",
            }
            if player.signed_label_deal:
                music_opts["8"] = "View Current Label Deal"
            music_opts["0"] = "Back"


            music_choice = present_choices(music_opts, "Music Management Options:")
            adv_time_music_mgmt = 5 # Base time for accessing this menu, can be overridden by actions

            if music_choice == "1": # Self-Release Song
                recorded_unreleased_songs = [s for s in player.songs_written if s.is_recorded and not s.is_released]
                if not recorded_unreleased_songs:
                    print("You have no recorded songs ready for release.")
                else:
                    print("Select a song to self-release:")
                    song_select_map = {str(i+1): song for i, song in enumerate(recorded_unreleased_songs)}
                    song_display_list = [str(song) for song in recorded_unreleased_songs]

                    chosen_song_key = present_choices(song_display_list, "Choose song to release (0 to cancel):")

                    if chosen_song_key and chosen_song_key != "0" and chosen_song_key in song_select_map:
                        song_to_release = song_select_map[chosen_song_key]
                        release_cost = 100
                        if player.money >= release_cost:
                            if input(f"Self-release '{song_to_release.title}' for ${release_cost}? (y/n) > ").lower() == 'y':
                                player.money -= release_cost
                                release_method_success = False
                                released_via_label_id = None

                                if player.signed_label_deal and player.signed_label_deal.get('songs_remaining_on_contract', 0) > 0:
                                    release_choice_opts = {
                                        "1": f"Release via {player.signed_label_deal['label_name']} (No cost, uses contract slot)",
                                        "2": f"Self-Release Independently (Cost: ${release_cost})"
                                    }
                                    release_decision = present_choices(release_choice_opts, f"How to release '{song_to_release.title}'?")

                                    if release_decision == "1":
                                        player.money += release_cost
                                        release_cost = 0
                                        released_via_label_id = player.signed_label_deal['label_poi_id']
                                        player.signed_label_deal['songs_remaining_on_contract'] -= 1
                                        print(f"Releasing '{song_to_release.title}' via {player.signed_label_deal['label_name']}. Songs remaining on contract: {player.signed_label_deal['songs_remaining_on_contract']}.")
                                        release_method_success = song_to_release.mark_as_released(current_game_time.copy(), released_by_label_id=released_via_label_id)
                                    elif release_decision == "2":
                                        print(f"Proceeding with self-release for ${release_cost}.")
                                        release_method_success = song_to_release.mark_as_released(current_game_time.copy())
                                    else:
                                        player.money += release_cost
                                        print("Release decision cancelled.")
                                else:
                                    release_method_success = song_to_release.mark_as_released(current_game_time.copy())

                                if release_method_success:
                                    print(f"Successfully released '{song_to_release.title}'. Money: ${player.money}")
                                    buzz_feedback = generate_feedback_for_song(song_to_release, player, feedback_type="general_release")
                                    if buzz_feedback:
                                        player.feedback_received.append(buzz_feedback)
                                        if buzz_feedback.get("impact", {}).get("fame", 0) > 0: player.fame += buzz_feedback["impact"]["fame"]
                                        if buzz_feedback.get("impact", {}).get("stress", 0) != 0: player.stress = max(0,min(100, player.stress + buzz_feedback["impact"]["stress"]))
                                        print(f"News: {buzz_feedback['source']} commented on '{song_to_release.title}'!")
                                    player.fame += 2
                                    adv_time_music_mgmt += 60
                                else:
                                    print(f"Failed to release '{song_to_release.title}'.")
                                    player.money += release_cost
                            else:
                                print("Release cancelled.")
                        else:
                            print(f"Not enough money to release. Need ${release_cost}.")
                    elif chosen_song_key == "0":
                        print("Release process cancelled.")
                    else:
                        print("Invalid song selection for release.")
            elif music_choice == "2": # Promote Released Song
                print("\n--- Promote Released Song ---")
                released_songs = [s for s in player.songs_written if s.is_released]
                if not released_songs:
                    print("You have no songs released to promote.")
                else:
                    print("Select a song to promote:")
                    song_promo_map = {str(i+1): song for i, song in enumerate(released_songs)}
                    song_promo_display = [f"{str(s)} (Buzz: {s.buzz_score:.1f})" for s in released_songs]

                    chosen_song_key = present_choices(song_promo_display, "Choose song to promote (0 to cancel):")

                    if chosen_song_key and chosen_song_key != "0" and chosen_song_key in song_promo_map:
                        song_to_promote = song_promo_map[chosen_song_key]
                        print(f"\nPromoting '{song_to_promote.title}' (Current Buzz: {song_to_promote.buzz_score:.1f})")
                        promo_action_opts = {
                            "1": "Run Social Media Campaign ($50, 2 hrs)",
                            "2": "Print Flyers/Posters Locally ($20, 4 hrs)",
                            "3": "Contact Local Radio Stations (TBD)",
                            "0": "Cancel Promotion"
                        }
                        promo_choice = present_choices(promo_action_opts, "Choose promotion type:")

                        cost = 0; time_hrs = 0; buzz_gain_range = (0,0)
                        action_msg = ""

                        if promo_choice == "1":
                            cost, time_hrs, buzz_gain_range = 50, 2, (5, 15)
                            action_msg = "social media campaign"
                        elif promo_choice == "2":
                            cost, time_hrs, buzz_gain_range = 20, 4, (2, 8)
                            action_msg = "flyers/posters"
                        elif promo_choice == "3":
                            print("Contacting local radio stations... (Feature TBD - No effect yet)")
                            adv_time_music_mgmt += 60
                        elif promo_choice == "0":
                            print("Promotion cancelled.")
                        else:
                            print("Invalid promotion type.")

                        if cost > 0 :
                            if player.money >= cost:
                                player.money -= cost
                                adv_time_music_mgmt += time_hrs * 60
                                buzz_increase = round(random.uniform(buzz_gain_range[0], buzz_gain_range[1]), 1)
                                song_to_promote.buzz_score = min(100, song_to_promote.buzz_score + buzz_increase)
                                print(f"Launched {action_msg} for '{song_to_promote.title}'.")
                                print(f"Cost: ${cost}, Time: {time_hrs} hrs. Buzz increased by {buzz_increase:.1f} to {song_to_promote.buzz_score:.1f}.")
                                print(f"Player money: ${player.money}")
                            else:
                                print(f"Not enough money for {action_msg}. Need ${cost}.")
                    elif chosen_song_key == "0":
                        print("Song promotion cancelled.")
                    else:
                        print("Invalid song selection.")
                adv_time_music_mgmt += 5
            elif music_choice == "3": # Plan a Local Gig
                print("\n--- Plan a Local Gig ---")
                adv_time_gig_planning = 5
                if not player.current_location or not hasattr(player.current_location, 'venues') or not player.current_location.venues:
                    print("No venues available in your current location to plan a gig.")
                else:
                    suitable_venues = [
                        v for v in player.current_location.venues
                        if v.category in ["CLUB_SMALL", "CAFE", "VENUE_BAR", "COMMUNITY_HALL"]
                           and getattr(v, 'allows_player_booking', True)
                    ]
                    if not suitable_venues:
                        print(f"No suitable small/medium venues found in {player.current_location.name} that allow direct booking at your current level.")
                    else:
                        print("Select a venue to try and book:")
                        venue_map = {str(i+1): v for i, v in enumerate(suitable_venues)}
                        venue_display = [f"{v.name} (Type: {v.venue_type}, Prestige: {getattr(v, 'prestige', 'N/A')}, Fee: ${getattr(v, 'booking_fee', 50)})" for v in suitable_venues]

                        chosen_venue_key = present_choices(venue_display, "Choose venue (0 to cancel):")

                        if chosen_venue_key and chosen_venue_key != "0" and chosen_venue_key in venue_map:
                            selected_venue = venue_map[chosen_venue_key]
                            booking_fee = getattr(selected_venue, 'booking_fee', 50)

                            print(f"Attempting to book {selected_venue.name}. Booking fee: ${booking_fee}")
                            if player.money < booking_fee:
                                print(f"Not enough money. You need ${booking_fee} to book this venue.")
                            else:
                                try:
                                    days_in_advance_str = input("How many days from now to book the gig (7-28)? > ")
                                    days_in_advance = int(days_in_advance_str)
                                    if not (7 <= days_in_advance <= 28):
                                        raise ValueError("Gig must be booked between 7 and 28 days in advance.")

                                    num_songs_str = input(f"How many songs for the setlist (1-7, you have {len(player.songs_written)})? > ")
                                    num_songs = int(num_songs_str)
                                    if not (1 <= num_songs <= 7):
                                        raise ValueError("Setlist must be between 1 and 7 songs.")
                                    if len(player.songs_written) < num_songs:
                                        raise ValueError(f"Not enough songs written ({len(player.songs_written)}) for a {num_songs}-song setlist.")

                                    player.money -= booking_fee
                                    adv_time_gig_planning += 15

                                    gig_date = current_game_time.copy()
                                    gig_date.advance_time(minutes=days_in_advance * 24 * 60)
                                    gig_date.hour = 20
                                    gig_date.minute = 0

                                    event_name = f"{player.name} Live at {selected_venue.name}"
                                    req_skills = {"vocals": 1, "stage_presence": 1}
                                    if any(g.gear_type.startswith("INSTRUMENT") and "guitar" in g.gear_type.lower() for g in player.gear_inventory if not g.is_broken) or "guitar" in player.skills:
                                        req_skills["guitar"] = 1

                                    new_gig_event = Event(
                                        name=event_name, location=selected_venue, event_type="PLAYER_BOOKED_GIG",
                                        required_skills=req_skills, description=f"A self-organized gig by {player.name}.",
                                        is_player_organized=True, specific_payout=0, specific_fame_reward=0
                                    )
                                    new_gig_event.songs_required_count = num_songs

                                    selected_venue.add_event(new_gig_event)

                                    gig_end_time = gig_date.copy()
                                    gig_end_time.advance_time(minutes=(num_songs * 10) + 30)
                                    player.schedule.add_event(
                                        start_time=gig_date, end_time=gig_end_time, description=event_name,
                                        category="Gig (Self-Booked)", details={"venue_id": selected_venue.venue_id, "event_id": new_gig_event.name}
                                    )
                                    print(f"Successfully booked '{event_name}' at {selected_venue.name} for {gig_date.get_time_string_for_schedule()}!")
                                    print(f"Paid ${booking_fee} booking fee. Remaining money: ${player.money}")
                                    print("Remember to promote your gig to get people to show up!")

                                except ValueError as e:
                                    print(f"Booking cancelled: {e}")
                                    if 'booking_fee' in locals() and player.money + booking_fee >= 0 : player.money += booking_fee
                                except Exception as e:
                                    print(f"An unexpected error occurred during booking: {e}")
                                    if 'booking_fee' in locals() and player.money + booking_fee >= 0 : player.money += booking_fee
                        elif chosen_venue_key == "0":
                            print("Gig planning cancelled.")
                        else:
                            print("Invalid venue selection.")
                adv_time = adv_time_gig_planning

            elif music_choice == "4": # Check Reviews/Fan Mail
                print("\n--- Reviews & Fan Mail ---")
                if not player.feedback_received:
                    print("No feedback received yet.")
                else:
                    for i, fb_item in enumerate(reversed(player.feedback_received)):
                        print(f"\n{i+1}. {'[UNREAD] ' if not fb_item.get('read') else ''}From: {fb_item['source']} (Song: '{fb_item['song_title']}')")
                        print(f"   Date: {fb_item['date_generated'].get_time_string_for_schedule()}")
                        print(f"   Quote: \"{fb_item['quote']}\"")
                        if fb_item.get('impact'):
                            print(f"   Impact: {fb_item['impact']}")
                        if not fb_item.get('read'):
                            fb_item['read'] = True
                    input("Press Enter to continue...")
                adv_time_music_mgmt += 10

            elif music_choice == "5": # View Charts
                print("\n--- Current Music Charts ---")
                if not ACTIVE_CHARTS:
                    print("No music charts available at the moment.")
                else:
                    for i, chart_obj in enumerate(ACTIVE_CHARTS):
                        print(f"\n{i+1}. {chart_obj.name}")
                        print(chart_obj)
                input("Press Enter to continue...")
                adv_time_music_mgmt += 5
            elif music_choice == "6": # View Label Offers
                print("\n--- Record Label Offers ---")
                pending_offers = [offer for offer in player.active_label_offers if offer.get("status") == "pending_player_decision"]

                for offer in pending_offers[:]:
                    if current_game_time >= offer["expiry_date_obj"]:
                        offer["status"] = "expired"
                        print(f"Offer from {offer['label_name']} has expired.")

                pending_offers = [offer for offer in player.active_label_offers if offer.get("status") == "pending_player_decision"]

                if not pending_offers:
                    print("No active label offers at the moment.")
                else:
                    offer_display_map = {}
                    print("You have the following contract offers:")
                    for i, offer in enumerate(pending_offers):
                        offer_summary = (f"{i+1}. From: {offer['label_name']} ({offer['offer_type']})\n"
                                         f"     Advance: ${offer['advance_payment']:,}, Royalty: {offer['royalty_rate_player']*100:.0f}%, "
                                         f"Albums: {offer.get('album_commitment', 'N/A')}, Duration: {offer.get('contract_duration_years', 'N/A')} yrs\n"
                                         f"     Creative Control: {offer.get('creative_control_level', 'N/A')}\n"
                                         f"     Expires: {offer['expiry_date_obj'].get_time_string_for_schedule()}")
                        print(offer_summary)
                        offer_display_map[str(i+1)] = offer

                    print("\nSelect an offer number to view details and respond, or 0 to go back.")
                    offer_choice_key = input("> ")

                    if offer_choice_key.isdigit() and offer_choice_key in offer_display_map:
                        chosen_offer = offer_display_map[offer_choice_key]
                        print(f"\n--- Offer Details: {chosen_offer['label_name']} ---")
                        print(f"Type: {chosen_offer['offer_type']}")
                        print(f"Advance: ${chosen_offer['advance_payment']:,}")
                        print(f"Your Royalty: {chosen_offer['royalty_rate_player']*100:.0f}%")
                        print(f"Marketing Support Multiplier: {chosen_offer['marketing_support_bonus']:.2f}x")
                        # print(f"Songs on Contract: {chosen_offer['songs_on_contract']}") # Superseded by album commitment
                        print(f"Album Commitment: {chosen_offer.get('album_commitment', 'N/A')} album(s)")
                        print(f"Contract Duration: {chosen_offer.get('contract_duration_years', 'N/A')} year(s)")
                        print(f"Creative Control: {chosen_offer.get('creative_control_level', 'N/A')}")
                        print(f"Tour Support (Label Pays % of your tour costs): {chosen_offer.get('tour_support_budget_percentage', 0)*100:.0f}%")
                        print(f"Music Video Budget (for one single): ${chosen_offer.get('music_video_budget_single', 0):,}")
                        print(f"Offered on: {chosen_offer['offer_date'].get_time_string_for_schedule()}")
                        print(f"Expires on: {chosen_offer['expiry_date_obj'].get_time_string_for_schedule()}")

                        response_options = {"1": "Accept Offer", "2": "Decline Offer", "0": "Decide Later"}
                        response_key = present_choices(response_options, "Your decision?")

                        if response_key == "1":
                            # If accepting a renewal, the old deal in history needs to be closed out.
                            if chosen_offer.get("offer_type") == "Contract Renewal" and player.signed_label_deal:
                                old_deal_label_name = player.signed_label_deal.get("label_name")
                                old_deal_start_date = player.signed_label_deal.get("contract_start_date_obj")
                                for hist_item in player.label_history:
                                    if hist_item.get("label_name") == old_deal_label_name and \
                                       hist_item.get("status") == "active" and \
                                       hist_item.get("signed_date") == old_deal_start_date: # Match specific contract period
                                        hist_item["status"] = "ended"
                                        hist_item["end_date"] = current_game_time.copy() # Ends now as new one starts
                                        hist_item["reason_for_ending"] = "Superseded by Renewal"
                                        print(f"DEBUG: Previous contract with {old_deal_label_name} marked as superseded in history.")
                                        break

                            player.signed_label_deal = chosen_offer.copy()
                            player.signed_label_deal['contract_start_date_obj'] = current_game_time.copy() # Set start date for the new/renewed deal

                            # Generate and store initial objectives (also for renewals)
                            initial_objectives = generate_initial_label_objectives(player, player.signed_label_deal, current_game_time)
                            player.signed_label_deal['objectives'] = initial_objectives
                            # Reset renewal processed flag for the new deal term
                            player.signed_label_deal['renewal_processed_this_term_flag'] = False
                            player.signed_label_deal['renewal_decision_made_this_term'] = None

                            player.money += chosen_offer['advance_payment']
                            chosen_offer['status'] = "accepted" # Mark the offer in active_label_offers as accepted

                            # Add the NEW active deal to history
                            player.label_history.append({
                                "label_name": player.signed_label_deal['label_name'], # Use from the newly signed deal
                                "deal_type": player.signed_label_deal['offer_type'],
                                "signed_date": player.signed_label_deal['contract_start_date_obj'],
                                "status": "active",
                                "end_date": None,
                                "reason_for_ending": None
                            })

                            # Void other pending offers
                            for other_offer in player.active_label_offers:
                                if other_offer['offer_id'] != chosen_offer['offer_id'] and other_offer['status'] == "pending_player_decision":
                                    other_offer['status'] = "voided_by_player_signing"

                            if chosen_offer.get("offer_type") == "Contract Renewal":
                                print(f"Successfully renewed your contract with {chosen_offer['label_name']}!")
                            else:
                                print(f"Congratulations! You've signed with {chosen_offer['label_name']}!")
                            print(f"You received an advance of ${chosen_offer['advance_payment']:,}. Your current money: ${player.money}")
                            print(f"Your current money: ${player.money}")
                            adv_time_music_mgmt += 30
                        elif response_key == "2": # Player declines offer
                            chosen_offer['status'] = "declined_by_player"
                            label_poi_ref = get_poi_or_venue_by_id(chosen_offer['label_poi_id'])
                            if label_poi_ref and hasattr(label_poi_ref, 'player_interest_score'):
                                label_poi_ref.player_interest_score = max(0, label_poi_ref.player_interest_score - 20)
                                print(f"(Your relationship with {chosen_offer['label_name']} has cooled slightly.)")

                            if chosen_offer.get("offer_type") == "Contract Renewal":
                                print(f"You have declined the renewal offer from {chosen_offer['label_name']}. Your current contract remains active until its expiry.")
                                if player.signed_label_deal and player.signed_label_deal.get("label_poi_id") == chosen_offer.get("label_poi_id"):
                                    player.signed_label_deal["renewal_offer_player_response"] = "declined"
                                    # Also ensure renewal_processed_this_term_flag is set so another isn't immediately generated
                                    player.signed_label_deal["renewal_processed_this_term_flag"] = True
                                    player.signed_label_deal["renewal_decision_made_this_term"] = "player_declined_renewal"


                            else:
                                print(f"You have declined the offer from {chosen_offer['label_name']}.")
                            adv_time_music_mgmt += 15
                        else:
                            print("You decide to think it over.")
                            adv_time_music_mgmt += 5
                    elif offer_choice_key == "0":
                        print("Returning to Music Management menu.")
                    else:
                        print("Invalid selection.")
                adv_time_music_mgmt += 5
            elif music_choice == "7": # View Released Songs
                print("\n--- Your Released Music ---")
                released_songs = [s for s in player.songs_written if s.is_released]
                if not released_songs:
                    print("You haven't released any music yet.")
                else:
                    for i, song_obj in enumerate(released_songs):
                        print(f"\n{i+1}. {str(song_obj)}")
                        charted_on = []
                        for chart in ACTIVE_CHARTS:
                            for entry in chart.entries:
                                if entry['song_id'] == song_obj.song_id:
                                    charted_on.append(f"  - On '{chart.name}': Pos #{entry['current_position']} (Peak: #{entry['peak_position']}, Weeks: {entry['weeks_on_chart']})")
                                    break
                        if charted_on:
                            print("  Chart Performance:")
                            for line in charted_on: print(line)
                        else:
                            print("  Not currently on any major charts.")
                input("Press Enter to continue...")
                adv_time_music_mgmt += 10
            elif music_choice == "8": # View Current Label Deal
                if player.signed_label_deal:
                    deal = player.signed_label_deal
                    print(f"\n--- Current Deal with: {deal['label_name']} ---")
                    print(f"Type: {deal['offer_type']}")
                    print(f"Signed On: {deal['contract_start_date_obj'].get_time_string_for_schedule() if deal.get('contract_start_date_obj') else 'N/A'}")
                    print(f"Duration: {deal.get('contract_duration_years', 'N/A')} year(s)")

                    # Calculate contract end date if possible
                    if deal.get('contract_start_date_obj') and deal.get('contract_duration_years'):
                        end_date_calc = deal['contract_start_date_obj'].copy()
                        # Simple year addition for now, might need more robust date math if months/days matter
                        end_date_calc.year += deal['contract_duration_years']
                        print(f"Expected End Date: {end_date_calc.year}-{end_date_calc.month:02d}-{end_date_calc.day:02d}")

                    print(f"Advance Received: ${deal['advance_payment']:,}")
                    print(f"Player Royalty: {deal['royalty_rate_player']*100:.0f}%")
                    print(f"Album Commitment: {deal.get('album_commitment', 'N/A')} album(s)")
                    print(f"Albums Remaining: {deal.get('albums_remaining_on_commitment', 'N/A')}")
                    # print(f"Songs on Contract (Legacy): {deal.get('songs_on_contract', 'N/A')}") # Might be confusing with albums
                    # print(f"Songs Remaining (Legacy): {deal.get('songs_remaining_on_contract', 'N/A')}")
                    print(f"Creative Control: {deal.get('creative_control_level', 'N/A')}")
                    print(f"Marketing Support Multiplier: {deal.get('marketing_support_bonus', 1.0):.2f}x")
                    print(f"Tour Support (Label Covers %): {deal.get('tour_support_budget_percentage', 0)*100:.0f}%")
                    print(f"Music Video Budget (per eligible single): ${deal.get('music_video_budget_single', 0):,}")
                    print(f"Current Relationship with Label: {deal.get('label_relationship_score', 'N/A')}/100")

                    if deal.get('objectives'):
                        print("\nCurrent Label Objectives:")
                        for i, obj_item in enumerate(deal['objectives']):
                             # Assuming objective is a string for now. Could be a dict later.
                            print(f"  {i+1}. {obj_item}")
                    else:
                        print("\nNo specific objectives assigned by label currently.")

                    input("\nPress Enter to continue...")
                    adv_time_music_mgmt += 10
                else:
                    print("You are not currently signed to a record label.")
                adv_time_music_mgmt += 5

            adv_time = adv_time_music_mgmt # Use the accumulated time from music management actions

        elif choice == "0": print("Putting phone away."); adv_time=1; break
        else: print("Invalid phone option.")
        if adv_time > 0: advance_game_time(adv_time); update_npc_locations(current_game_time); process_time_based_player_needs(player, adv_time)
        # Corrected the condition for continuing phone usage to include the new max option number "8"
        if choice in ["1","2","3", "4", "5", "6", "7", "8"] and present_choices({"1":"Continue phone","0":"Put away"},"Done?")=="0": print("Putting phone away."); break
    print("--------------------")

# --- Label Objectives Function ---
def generate_initial_label_objectives(player_obj, deal_details, current_time):
    """Generates a list of initial objectives for the player based on the signed deal."""
    objectives = []
    num_albums = deal_details.get('album_commitment', 1)
    duration_years = deal_details.get('contract_duration_years', 1)

    # Objective 1: Record songs for the first album
    songs_for_first_album = random.randint(max(1, 8 - num_albums*2), 10) # Fewer songs if multiple albums
    first_album_deadline_months = max(6, duration_years * 12 // (num_albums + 1) - random.randint(0,2)) # Spread out deadlines

    deadline_date_album1 = current_time.copy()
    deadline_date_album1.advance_time(minutes=first_album_deadline_months * 30 * 24 * 60) # Approximate months
    objectives.append(
        f"Record {songs_for_first_album} new songs for your first album with {deal_details['label_name']} by {deadline_date_album1.year}-{deadline_date_album1.month:02d}-{deadline_date_album1.day:02d}."
    )

    # Objective 2: Achieve some chart presence
    # Find a local chart if possible
    local_chart_name = "a local chart"
    if ACTIVE_CHARTS:
        local_chart_name = ACTIVE_CHARTS[0].name # Default to the first chart in the list
        # Potentially pick one more relevant to the player's home or label's city later

    chart_target_position = random.choice([10, 20, 30]) # Top 10, 20, or 30
    chart_deadline_months = random.randint(3, 6)
    deadline_date_chart = current_time.copy()
    deadline_date_chart.advance_time(minutes=chart_deadline_months * 30 * 24 * 60)
    objectives.append(
        f"Achieve a Top {chart_target_position} single on the '{local_chart_name}' chart by {deadline_date_chart.year}-{deadline_date_chart.month:02d}-{deadline_date_chart.day:02d}."
    )

    # Objective 3: Maintain good relationship (implied, but can be stated)
    objectives.append(f"Maintain a positive working relationship with {deal_details['label_name']}.")

    # Objective 4 (Optional): Initial tour if tour support is decent
    if deal_details.get('tour_support_budget_percentage', 0) >= 0.15 and player_obj.fame > 15:
        tour_objective_deadline_months = random.randint(6,9)
        deadline_date_tour = current_time.copy()
        deadline_date_tour.advance_time(minutes=tour_objective_deadline_months * 30 * 24 * 60)
        objectives.append(
            f"Undertake a promotional tour (at least 3 dates) with support from {deal_details['label_name']} by {deadline_date_tour.year}-{deadline_date_tour.month:02d}-{deadline_date_tour.day:02d}."
        )

    print(f"DEBUG: Generated objectives for {player_obj.name} with {deal_details['label_name']}: {objectives}")
    return objectives


# --- Chart Update Function ---
def update_all_charts(player_obj, current_game_time_obj):
    """Iterates through all active charts and calls their weekly update."""
    if not hasattr(player_obj, 'songs_written') or not hasattr(player_obj, 'name') or not hasattr(player_obj, 'fame'):
        print("Error: Player object is not correctly initialized for chart updates.")
        return

    if hasattr(player_obj, 'songs_written'):
        for song_item in player_obj.songs_written:
            if hasattr(song_item, 'buzz_score'):
                song_item.buzz_score = round(max(0, song_item.buzz_score * 0.7), 1)
                if song_item.buzz_score < 0.1 : song_item.buzz_score = 0.0

    print("\n--- Weekly Chart Updates Processing ---")
    for chart in ACTIVE_CHARTS:
        feedback_events = chart.update_weekly(
            all_player_songs=player_obj.songs_written,
            player_obj=player_obj,
            current_game_time_obj=current_game_time_obj
        )
        if feedback_events:
            for event_data in feedback_events:
                song_for_feedback = event_data.get("song_obj")
                if not song_for_feedback:
                    song_for_feedback = next((s for s in player_obj.songs_written if s.song_id == event_data["song_id"]), None)

                if song_for_feedback:
                    chart_feedback = generate_feedback_for_song(
                        song_obj=song_for_feedback,
                        player_obj=player_obj,
                        chart_entry_details=event_data.get("chart_details"),
                        feedback_type=event_data.get("type", "general_chart_event")
                    )
                    if chart_feedback:
                        player_obj.feedback_received.append(chart_feedback)
                        if chart_feedback.get("impact", {}).get("fame", 0) > 0: player_obj.fame += chart_feedback["impact"]["fame"]
                        if chart_feedback.get("impact", {}).get("stress", 0) != 0: player_obj.stress = max(0,min(100, player_obj.stress + chart_feedback["impact"]["stress"]))
                        print(f"Chart News ({chart.name}): {chart_feedback['source']} on '{song_for_feedback.title}': \"{chart_feedback['quote'][:50]}...\"")

                        if (chart_feedback['source'] in SOURCES["pro_critics"] and song_for_feedback.song_quality >= 0.7) or \
                           (song_for_feedback.song_quality >= 0.85) :
                            review_interest_boost = 0.5
                            if chart_feedback['source'] in SOURCES["pro_critics"]:
                                review_interest_boost = 1.0

                            for location_obj_for_label in WORLD_MAP.values():
                                all_pois_in_loc = location_obj_for_label.points_of_interest + location_obj_for_label.venues
                                for poi_label_candidate in all_pois_in_loc:
                                    if hasattr(poi_label_candidate, 'category') and poi_label_candidate.category == "OFFICE_RECORD_LABEL":
                                        current_boost = review_interest_boost
                                        if poi_label_candidate.genres_preferred and song_for_feedback.genre in poi_label_candidate.genres_preferred:
                                            current_boost *= 1.2
                                        elif not poi_label_candidate.genres_preferred:
                                            current_boost *= 1.05

                                        poi_label_candidate.player_interest_score = min(100, poi_label_candidate.player_interest_score + current_boost)
                else:
                    print(f"Warning: Could not find song with ID {event_data.get('song_id')} for feedback generation.")

    process_weekly_music_income(player_obj)
    check_and_generate_label_offers(player_obj, current_game_time_obj)
    check_contract_expirations(player_obj, current_game_time_obj) # New call
    print("--- Weekly Chart Updates Finished ---\n")

def check_contract_expirations(player_obj, current_time_obj):
    """Checks if the player's current label contract is expiring and handles renewal/ending."""
    if not player_obj.signed_label_deal:
        return

    deal = player_obj.signed_label_deal
    contract_start_time = deal.get('contract_start_date_obj')
    contract_duration_years = deal.get('contract_duration_years')

    if not contract_start_time or not contract_duration_years:
        # This should not happen with a properly formed deal
        return

    # Calculate the actual date the contract becomes inactive
    # e.g., if start is 2024-01-15 for 1 year, it ends EOD 2025-01-14.
    # So, on 2025-01-15, it is finished.
    contract_becomes_inactive_date = contract_start_time.copy()
    contract_becomes_inactive_date.year += contract_duration_years

    is_contract_term_finished = current_time_obj >= contract_becomes_inactive_date

    # If renewal logic has already been processed for this contract term and it's not yet finished, skip.
    if deal.get('renewal_processed_this_term_flag', False) and not is_contract_term_finished:
        return

    days_until_actual_end = -1 # Default to indicate past or error
    if not is_contract_term_finished:
        # Calculate days from current_time_obj up to (but not including) contract_becomes_inactive_date
        # This is a bit complex with simplified date math. GameTime.days_difference is absolute.
        # We need days *remaining*.
        if contract_becomes_inactive_date > current_time_obj:
            # Approximate remaining days
            years_diff = contract_becomes_inactive_date.year - current_time_obj.year
            months_diff = contract_becomes_inactive_date.month - current_time_obj.month
            days_diff = contract_becomes_inactive_date.day - current_time_obj.day
            days_until_actual_end = (years_diff * 360) + (months_diff * 30) + days_diff
        else: # current_time_obj is on or after the inactive date, should be caught by is_contract_term_finished
            days_until_actual_end = 0

    RENEWAL_WINDOW_DAYS = 60 # Process renewal if within 60 days of contract_becomes_inactive_date

    # Check if we are in the renewal window (but not yet finished)
    if not is_contract_term_finished and days_until_actual_end >= 0 and days_until_actual_end <= RENEWAL_WINDOW_DAYS:
        # Added check for days_until_actual_end >=0 to ensure it's not past due to approximation issues
        if deal.get('renewal_processed_this_term_flag', False): # Double check flag
             return

        print(f"\n--- Contract Renewal Window with {deal['label_name']} (Expires in approx {days_until_actual_end} days) ---")
        deal['renewal_processed_this_term_flag'] = True

        renewal_score = deal.get('label_relationship_score', 50) + (player_obj.fame / 4)
        albums_total_commitment = deal.get('album_commitment', 0)
        albums_remaining = deal.get('albums_remaining_on_commitment', albums_total_commitment)
        albums_completed = albums_total_commitment - albums_remaining

        if albums_total_commitment > 0: renewal_score += (albums_completed / albums_total_commitment) * 30
        else: renewal_score += 5

        print(f"DEBUG: Renewal score for {deal['label_name']}: {renewal_score:.1f}")

        if renewal_score >= 80:
            print(f"{deal['label_name']} is very interested in renewing your contract!")
            base_adv = deal.get('advance_payment',1000); base_roy = deal.get('royalty_rate_player',0.1)
            factor = 1.0 + ( (renewal_score - 80) / 40.0 )

            new_advance = base_adv * random.uniform(0.8, 1.2) * factor
            new_royalty = base_roy * random.uniform(0.9, 1.1) * factor
            new_royalty = round(min(0.35, max(0.05, new_royalty)), 2)
            new_duration = random.randint(max(1,deal.get('contract_duration_years',1)-1), deal.get('contract_duration_years',1)+1)
            new_albums = random.randint(max(1,deal.get('album_commitment',1)-1), deal.get('album_commitment',1)+1)
            new_albums = min(new_albums, new_duration * 2)

            renewal_offer_details = {
                "offer_id": f"renewal_{deal['label_poi_id']}_{current_time_obj.year}{current_time_obj.month}{current_time_obj.day}",
                "label_poi_id": deal['label_poi_id'], "label_name": deal['label_name'],
                "offer_type": "Contract Renewal",
                "advance_payment": int(new_advance), "royalty_rate_player": new_royalty,
                "marketing_support_bonus": round(deal.get('marketing_support_bonus',1.0) * random.uniform(0.9, 1.1) * factor, 2),
                "album_commitment": new_albums, "albums_remaining_on_commitment": new_albums,
                "contract_duration_years": new_duration,
                "creative_control_level": deal.get('creative_control_level', "Shared Control"),
                "tour_support_budget_percentage": round(deal.get('tour_support_budget_percentage',0) * random.uniform(0.8,1.2) * factor, 2),
                "music_video_budget_single": int(deal.get('music_video_budget_single',0) * random.uniform(0.7,1.3) * factor if random.random() < 0.7 else 0),
                "music_video_produced_for_deal": False,
                "label_relationship_score": deal.get('label_relationship_score', 50),
                "objectives": [], "status": "pending_player_decision",
                "offer_date": current_time_obj.copy(),
                "expiry_date_obj": current_time_obj.copy()
            }
            renewal_offer_details["expiry_date_obj"].advance_time(minutes=21 * 24 * 60)

            already_has_pending_renewal = any(
                o.get("label_poi_id") == deal['label_poi_id'] and o.get("offer_type") == "Contract Renewal" and o.get("status") == "pending_player_decision"
                for o in player_obj.active_label_offers)
            if not already_has_pending_renewal:
                player_obj.active_label_offers.append(renewal_offer_details)
                print(f"They've sent you a renewal offer. Check phone.")
                print(f"(Offer: ${renewal_offer_details['advance_payment']:,} adv, {renewal_offer_details['royalty_rate_player']*100:.0f}% royalty)")
            else: print(f"{deal['label_name']} was considering a renewal, but one is already pending.")
        else:
            print(f"{deal['label_name']} has decided not to offer you a contract renewal. (Score: {renewal_score:.1f})")
            deal["renewal_decision_made_this_term"] = "not_offered"

    elif is_contract_term_finished:
        print(f"\n--- Contract with {deal['label_name']} Has Officially Ended ({contract_becomes_inactive_date.year}-{contract_becomes_inactive_date.month:02d}-{contract_becomes_inactive_date.day:02d}) ---")

        ended_reason = "Contract Term Completed" # Default reason
        if deal.get("renewal_decision_made_this_term") == "player_declined_renewal":
            ended_reason = "Ended - Player Declined Renewal Offer"
        elif deal.get("renewal_decision_made_this_term") == "not_offered":
            ended_reason = "Ended - Label Did Not Offer Renewal"

        updated_history = False
        for hist_deal in player_obj.label_history:
            # Ensure contract_start_time (from the current deal being ended) is used for matching the history item's signed_date
            if hist_deal.get("label_name") == deal["label_name"] and \
               hist_deal.get("status") == "active" and \
               hasattr(hist_deal.get("signed_date"), 'year') and \
               hist_deal.get("signed_date").year == contract_start_time.year and \
               hist_deal.get("signed_date").month == contract_start_time.month and \
               hist_deal.get("signed_date").day == contract_start_time.day :
                hist_deal["status"] = "ended"
                hist_deal["end_date"] = contract_becomes_inactive_date.copy() # Correct variable name
                hist_deal["reason_for_ending"] = ended_reason
                updated_history = True
                break

        if not updated_history:
            # Fallback: If exact start date match fails, try to find any active deal with the same label.
            # This is less precise but can catch cases if start dates were slightly off or not perfectly matched.
            for hist_deal in player_obj.label_history:
                 if hist_deal.get("label_name") == deal["label_name"] and hist_deal.get("status") == "active":
                    hist_deal["status"] = "ended"
                    hist_deal["end_date"] = contract_becomes_inactive_date.copy()
                    hist_deal["reason_for_ending"] = ended_reason
                    updated_history = True
                    print(f"DEBUG: Used fallback history update for ended contract with {deal['label_name']}.")
                    break
            if not updated_history:
                 print(f"DEBUG: CRITICAL - Could not find matching active history entry for deal with {deal['label_name']} signed around {contract_start_time.get_time_string_for_schedule()} to mark as ended.")

        player_obj.signed_label_deal = None
        print(f"You are now an independent artist again.")
        player_obj.stress = min(100, player_obj.stress + random.randint(10,20))
        player_obj.fame = max(0, player_obj.fame - random.randint(2,8))

        for offer in player_obj.active_label_offers[:]:
            if offer.get("label_poi_id") == deal["label_poi_id"] and offer.get("offer_type") == "Contract Renewal":
                if offer["status"] == "pending_player_decision":
                    offer["status"] = "voided_contract_expired"
                    print(f"Pending renewal from {deal['label_name']} voided.")

def check_and_generate_label_offers(player_obj, current_time): # Parameter name is current_time
    # Logic to prevent new offers if player is signed and not in a valid state for them
    if player_obj.signed_label_deal:
        current_deal = player_obj.signed_label_deal
        # 1. Check for pending RENEWAL offer from the CURRENT label
        has_pending_renewal_from_current = any(
            offer.get("label_poi_id") == current_deal.get("label_poi_id") and \
            offer.get("offer_type") == "Contract Renewal" and \
            offer.get("status") == "pending_player_decision"
            for offer in player_obj.active_label_offers
        )
        if has_pending_renewal_from_current:
            # If player is considering a renewal from their current label, no other label should make an offer.
            return

        # 2. If not in renewal window with current label, no offers from other labels either.
        contract_start = current_deal.get('contract_start_date_obj')
        contract_years = current_deal.get('contract_duration_years')
        if contract_start and contract_years:
            contract_becomes_inactive_date = contract_start.copy()
            contract_becomes_inactive_date.year += contract_years

            if current_time < contract_becomes_inactive_date: # Contract is still active
                days_remaining_approx = -1
                # Calculate approximate days remaining until contract_becomes_inactive_date
                if contract_becomes_inactive_date > current_time:
                    years_diff = contract_becomes_inactive_date.year - current_time.year
                    months_diff = contract_becomes_inactive_date.month - current_time.month
                    day_diff = contract_becomes_inactive_date.day - current_time.day
                    days_remaining_approx = (years_diff * 360) + (months_diff * 30) + day_diff

                RENEWAL_WINDOW_DAYS = 60
                # If days_remaining_approx is negative, it implies current_time is past or very close to expiry,
                # which should be handled by check_contract_expirations setting signed_label_deal to None.
                # So, if significantly more than RENEWAL_WINDOW_DAYS are left, block other offers.
                if days_remaining_approx > RENEWAL_WINDOW_DAYS:
                    return

    # If player is NOT signed, OR IS in renewal window (and no pending renewal from current label), proceed.
    offer_threshold = 80
    for location in WORLD_MAP.values():
        all_pois = location.points_of_interest + location.venues
        for label_poi in all_pois:
            # 3. Skip if this POI is the player's currently signed label for a "Basic Indie Deal"
            # Renewal offers are generated by check_contract_expirations.
            if player_obj.signed_label_deal and label_poi.poi_id == player_obj.signed_label_deal.get('label_poi_id'):
                continue

            if not (hasattr(label_poi, 'category') and label_poi.category == "OFFICE_RECORD_LABEL"):
                continue
            has_pending_offer_from_this_label = any(
                offer['label_poi_id'] == label_poi.poi_id and offer['status'] == "pending_player_decision"
                for offer in player_obj.active_label_offers
            )
            if has_pending_offer_from_this_label:
                continue
            if getattr(label_poi, 'player_interest_score', 0) >= offer_threshold:
                print(f"DEBUG: Label '{label_poi.name}' has high interest ({label_poi.player_interest_score:.1f}) in {player_obj.name}.")
                advance = random.randint(500, 2500) + int(player_obj.fame * 5)
                royalty = round(random.uniform(0.08, 0.15), 2) + round(getattr(label_poi, 'player_interest_score', 0)/2000,2)
                royalty = round(min(0.25, royalty),2)
                marketing_bonus = 1.1 + round(getattr(label_poi, 'player_interest_score', 0)/500,2)
                marketing_bonus = round(min(1.5, marketing_bonus),2)
                songs_on_contract = random.randint(2,4) # Potentially phase out or make secondary to album_commitment
                offer_expiry_time = current_time.copy()
                offer_expiry_time.advance_time(minutes=14 * 24 * 60)

                # Phase 8: Expanded Deal Terms
                album_commitment = random.randint(1, 2) # Number of albums
                contract_duration_years = random.randint(1, 3) # Years
                creative_control_options = ["Player Friendly", "Shared Control", "Label Priority"]
                creative_control_level = random.choice(creative_control_options)
                tour_support_budget_percentage = round(random.uniform(0.05, 0.25), 2) # e.g., 5% to 25% of tour costs
                music_video_budget_single = random.choice([0, random.randint(500, 3000) if player_obj.fame > 30 else 0]) # Chance of a small video budget

                new_offer = {
                    "offer_id": str(random.randint(10000,99999)),
                    "label_poi_id": label_poi.poi_id, "label_name": label_poi.name,
                    "offer_type": "Basic Indie Deal",
                    "advance_payment": advance, "royalty_rate_player": royalty,
                    "marketing_support_bonus": marketing_bonus,
                    "songs_on_contract": songs_on_contract,
                    "songs_remaining_on_contract": songs_on_contract,
                    "status": "pending_player_decision",
                    "offer_date": current_time.copy(),
                    "expiry_date_obj": offer_expiry_time,
                    # New Terms (Phase 8)
                    "album_commitment": album_commitment,
                    "albums_remaining_on_commitment": album_commitment, # Initialize this
                    "contract_duration_years": contract_duration_years,
                    "contract_start_date_obj": None, # Will be set upon signing
                    "creative_control_level": creative_control_level,
                    "tour_support_budget_percentage": tour_support_budget_percentage,
                    "music_video_budget_single": music_video_budget_single,
                    "music_video_produced_for_deal": False, # New flag
                    "label_relationship_score": 50, # Initial relationship score with the label
                    "objectives": [] # To store label-given objectives
                }
                player_obj.active_label_offers.append(new_offer)
                label_poi.player_interest_score *= 0.7
                print(f"*** URGENT MESSAGE for {player_obj.name}! ***")
                print(f"'{label_poi.name}' has sent you a contract offer! Check Phone > Music Management > View Label Offers.")
                print(f"(Offer: ${advance:,} advance, {royalty*100:.0f}% royalty, {album_commitment} album(s) over {contract_duration_years} year(s). Expires: {offer_expiry_time.get_time_string_for_schedule()})")

def process_weekly_music_income(player_obj):
    current_week_total_chart_income = 0
    current_week_streaming_income = 0
    player_charted_song_ids_this_week = set()
    for chart in ACTIVE_CHARTS:
        for entry in chart.entries:
            if entry.get('artist_name') == player_obj.name and entry.get('song_obj'):
                song = entry['song_obj']
                player_charted_song_ids_this_week.add(song.song_id)
                base_income_per_song = 10
                position_factor = (chart.max_size - entry['current_position'] + 1)
                quality_factor = song.song_quality * song.recording_quality
                fame_factor = 1 + (player_obj.fame / 200.0)
                raw_song_income_on_chart = base_income_per_song * (position_factor / float(chart.max_size)) * quality_factor * fame_factor
                player_share_of_income = raw_song_income_on_chart
                if song.released_by_label_id and player_obj.signed_label_deal and \
                   player_obj.signed_label_deal['label_poi_id'] == song.released_by_label_id:
                    player_share_of_income *= player_obj.signed_label_deal['royalty_rate_player']
                current_week_total_chart_income += player_share_of_income
                for location in WORLD_MAP.values():
                    all_pois_in_location = location.points_of_interest + location.venues
                    for poi_candidate in all_pois_in_location:
                        if hasattr(poi_candidate, 'category') and poi_candidate.category == "OFFICE_RECORD_LABEL":
                            interest_gain = (song.song_quality * position_factor * 0.05)
                            if poi_candidate.genres_preferred and song.genre in poi_candidate.genres_preferred:
                                interest_gain *= 1.5
                            elif not poi_candidate.genres_preferred:
                                interest_gain *= 1.1
                            poi_candidate.player_interest_score = min(100, poi_candidate.player_interest_score + interest_gain)
    streaming_base = 1
    for song in player_obj.songs_written:
        if song.is_released and song.song_id not in player_charted_song_ids_this_week:
            quality_factor = song.song_quality
            fame_factor = 1 + (player_obj.fame / 1000.0)
            raw_streaming_income_for_song = streaming_base * quality_factor * fame_factor
            player_share_streaming_income = raw_streaming_income_for_song
            if song.released_by_label_id and player_obj.signed_label_deal and \
               player_obj.signed_label_deal['label_poi_id'] == song.released_by_label_id:
                player_share_streaming_income *= player_obj.signed_label_deal['royalty_rate_player']
            current_week_streaming_income += player_share_streaming_income
    current_week_total_chart_income = round(current_week_total_chart_income)
    current_week_streaming_income = round(current_week_streaming_income)
    total_weekly_income = current_week_total_chart_income + current_week_streaming_income
    player_obj.last_week_music_income = total_weekly_income
    player_obj.money += total_weekly_income
    player_obj.total_music_income_to_date += total_weekly_income
    if total_weekly_income > 0:
        print(f"\n--- Music Income Report ---")
        print(f"Earnings from songs on charts: ${current_week_total_chart_income:.0f}")
        print(f"Earnings from other released songs (streaming): ${current_week_streaming_income:.0f}")
        print(f"Total music income this week: ${total_weekly_income:.0f}")
        print(f"Your music has earned a total of ${player_obj.total_music_income_to_date:.0f} to date.")
        print(f"Current Money: ${player_obj.money:.0f}")
        print("---------------------------\n")

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

                # Dynamic interactions for Record Label if signed
                if player.signed_label_deal and hasattr(poi, 'poi_id') and player.signed_label_deal.get('label_poi_id') == poi.poi_id:
                    deal = player.signed_label_deal # Define deal here for local scope
                    if "Meet with A&R Representative" not in interactions:
                        interactions.append("Meet with A&R Representative")
                    # "Propose Album to Label" was removed as a static option earlier, it's fully dynamic now.
                    # The "Discuss Album Release with Label" is the more appropriate term used below.

                    # Show "Discuss Music Video Production" if budget available and not yet used in this deal
                    if deal.get("music_video_budget_single", 0) > 0 and not deal.get("music_video_produced_for_deal", False):
                        if "Discuss Music Video Production" not in interactions:
                            interactions.append(f"Discuss Music Video Production (Budget: ${deal['music_video_budget_single']:,})")

                    # Show "Discuss Album Release with Label" if albums are remaining on commitment
                    if deal.get("albums_remaining_on_commitment", 0) > 0:
                        if "Discuss Album Release with Label" not in interactions:
                            interactions.append("Discuss Album Release with Label")

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
                                if player.comfort < 25:
                                    comfort_eff=-0.2
                                elif player.comfort < 50:
                                    comfort_eff=-0.1
                                if player.hunger > 75:
                                    hunger_eff=-0.2
                                elif player.hunger > 50:
                                    hunger_eff=-0.1
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

                                            base_rec_q = studio_quality * 0.6
                                            perf_skill_avg = (player.skills.get("vocals",0) + player.skills.get("guitar",0)) / 20.0
                                            base_rec_q += perf_skill_avg * 0.3
                                            base_rec_q += random.uniform(-0.1, 0.1)
                                            final_rec_quality = round(max(0.1, min(1.0, base_rec_q + (song_to_record.song_quality * 0.1))), 2)

                                            song_to_record.mark_as_recorded(final_rec_quality)
                                            print(f"Recorded '{song_to_record.title}' (RecQ: {final_rec_quality:.2f}). Cost ${rec_cost}. Money: ${player.money}")
                                            adv_time_general = rec_mins
                                        else: print(f"Not enough money. Need ${rec_cost}.")
                                    except ValueError: print("Recording cancelled.")
                                else: print("Recording cancelled.")
                            action_taken_custom_time = True
                        elif poi.category == "REHEARSAL_STUDIO" and chosen_text.startswith("Book Rehearsal Slot"):
                            action_taken_custom_time = True
                        elif poi.category == "OFFICE_RECORD_LABEL" and chosen_text.startswith("Submit Demo"):
                            print("\n--- Submit Demo to Record Label ---")
                            adv_time_general = 10; action_taken_custom_time = True
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

                                    if chosen_song_key and chosen_song_key != "0":
                                        chosen_song_idx = int(chosen_song_key) -1
                                        if 0 <= chosen_song_idx < len(recorded_songs):
                                            chosen_song = recorded_songs[chosen_song_idx]
                                            label_poi = poi

                                            print(f"You submit your demo of '{chosen_song.title}' to {label_poi.name}.")
                                            adv_time_general = 60

                                            success_score = 0
                                            success_score += chosen_song.song_quality * 35
                                            success_score += chosen_song.recording_quality * 35
                                            success_score += min(30, player.fame / 5)

                                            label_interest_bonus = getattr(label_poi, 'player_interest_score', 0.0) * 0.25
                                            success_score += label_interest_bonus

                                            genre_match_bonus = 0
                                            if label_poi.genres_preferred and chosen_song.genre in label_poi.genres_preferred: genre_match_bonus = 20
                                            elif not label_poi.genres_preferred: genre_match_bonus = 5
                                            success_score += genre_match_bonus

                                            outcome_roll = random.randint(0, 100)

                                            print(f"(Debug: SongQual: {chosen_song.song_quality*35:.1f}, RecQual: {chosen_song.recording_quality*35:.1f}, FameBonus: {min(30, player.fame / 5):.1f}, LabelInterest: {label_interest_bonus:.1f}, GenreBonus: {genre_match_bonus:.1f} -> Total Score: {success_score:.1f}, Label Roll: {outcome_roll})")

                                            if success_score > outcome_roll + 50 :
                                                print(f"{label_poi.name} is very impressed! \"This is great stuff, {player.name}! We need to talk. My office, tomorrow?\"")
                                                player.fame += 25
                                                if hasattr(label_poi, 'player_interest_score'):
                                                    label_poi.player_interest_score = min(100, label_poi.player_interest_score + 10)
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
                        elif chosen_text == "Propose Album to Label": # Should only appear if at correct, signed label POI
                            print("\n--- Propose Album to Label ---")
                            if player.signed_label_deal and player.signed_label_deal.get('label_poi_id') == poi.poi_id:
                                print(f"You discuss your upcoming album plans with {player.signed_label_deal['label_name']}.")
                                # Basic placeholder feedback
                                relationship_score = player.signed_label_deal.get('label_relationship_score', 50)
                                if relationship_score > 70:
                                    print("They seem enthusiastic and offer some minor positive suggestions.")
                                elif relationship_score > 40:
                                    print("They listen and nod, saying they'll consider your ideas for the album direction.")
                                else:
                                    print("They seem a bit skeptical but agree to review any material you submit.")
                                print("(Detailed album proposal mechanics and song review to be implemented later.)")
                                adv_time_general = 60
                            else:
                                print("You need to be signed to this label to propose an album.") # Should not happen due to dynamic menu
                                adv_time_general = 5
                            action_taken_custom_time = True
                        elif chosen_text == "Meet with A&R Representative": # Should only appear if at correct, signed label POI
                            print("\n--- Meet with A&R Representative ---")
                            if player.signed_label_deal and player.signed_label_deal.get('label_poi_id') == poi.poi_id:
                                deal = player.signed_label_deal
                                print(f"You sit down with an A&R representative from {deal['label_name']}.")
                                adv_time_general = 45
                                action_taken_custom_time = True

                                print("\nTopics of Discussion:")
                                meeting_options = {
                                    "1": "Discuss progress on current objectives",
                                    "2": "Discuss general label relationship",
                                    # "3": "Negotiate for more support (TBD)", # Future
                                    "0": "End meeting"
                                }

                                while True:
                                    meeting_choice = present_choices(meeting_options, "What to discuss?")
                                    if meeting_choice == "0":
                                        print("You conclude the meeting."); break

                                    if meeting_choice == "1": # Discuss progress on objectives
                                        print("\n--- Current Label Objectives ---")
                                        if deal.get('objectives'):
                                            for i, obj_item in enumerate(deal['objectives']):
                                                print(f"  {i+1}. {obj_item}")
                                            print("(Objective tracking and completion status TBD)")
                                        else:
                                            print("No specific objectives currently assigned.")
                                        # Simulate some discussion impact
                                        if deal['label_relationship_score'] < 40 :
                                            print("The rep seems concerned about progress.")
                                            deal['label_relationship_score'] = max(0, deal['label_relationship_score'] - 2)
                                        elif deal['label_relationship_score'] > 70:
                                            print("The rep is pleased with your proactive approach.")
                                            deal['label_relationship_score'] = min(100, deal['label_relationship_score'] + 2)
                                        else:
                                            print("The rep nods and takes notes.")
                                        adv_time_general += 15

                                    elif meeting_choice == "2": # Discuss general label relationship
                                        print("\n--- Label Relationship ---")
                                        print(f"Your current standing with the label is: {deal['label_relationship_score']}/100.")
                                        if deal['label_relationship_score'] > 80:
                                            print("They praise your recent work and commitment. Things are excellent!")
                                            deal['label_relationship_score'] = min(100, deal['label_relationship_score'] + 3)
                                        elif deal['label_relationship_score'] > 60:
                                            print("The relationship is positive. They appreciate your efforts.")
                                            deal['label_relationship_score'] = min(100, deal['label_relationship_score'] + 1)
                                        elif deal['label_relationship_score'] > 40:
                                            print("Things are okay. They expect continued dedication.")
                                        elif deal['label_relationship_score'] > 20:
                                            print("There's some tension. They remind you of their expectations.")
                                            deal['label_relationship_score'] = max(0, deal['label_relationship_score'] - 3)
                                        else:
                                            print("The relationship is strained. The rep expresses clear disappointment.")
                                            deal['label_relationship_score'] = max(0, deal['label_relationship_score'] - 5)
                                        print(f"New relationship score: {deal['label_relationship_score']}/100.")
                                        adv_time_general += 15

                                    # Add more topics later
                                    if adv_time_general >= 120: # Cap meeting time
                                        print("The A&R rep indicates the meeting needs to wrap up.")
                                        break
                            else:
                                print("You need to be signed to this label for a formal meeting.") # Should not happen
                                adv_time_general = 5
                            action_taken_custom_time = True
                        elif chosen_text.startswith("Discuss Music Video Production"):
                            print("\n--- Music Video Production ---")
                            if player.signed_label_deal and \
                               player.signed_label_deal.get('label_poi_id') == poi.poi_id and \
                               player.signed_label_deal.get("music_video_budget_single", 0) > 0 and \
                               player.signed_label_deal.get("music_video_produced_for_deal", False) is False:

                                deal = player.signed_label_deal
                                budget = deal['music_video_budget_single']
                                print(f"The label, {deal['label_name']}, is ready to fund a music video with a budget of ${budget:,}.")

                                released_songs = [s for s in player.songs_written if s.is_released and not s.has_music_video]
                                if not released_songs:
                                    print("You have no released songs that don't already have a music video.")
                                    adv_time_general = 10
                                else:
                                    print("Select a song for the music video:")
                                    song_choices_dict = {str(i+1): song for i, song in enumerate(released_songs)}
                                    song_display_list = [f"{s.title} (Quality: {s.song_quality:.2f}, Buzz: {s.buzz_score:.1f})" for s in released_songs]

                                    chosen_song_key = present_choices(song_display_list, "Choose song (0 to cancel):")

                                    if chosen_song_key and chosen_song_key != "0" and chosen_song_key in song_choices_dict:
                                        selected_song = song_choices_dict[chosen_song_key]

                                        if input(f"Produce music video for '{selected_song.title}' using the full budget of ${budget:,}? (This will take ~2 weeks) (y/n) > ").lower() == 'y':
                                            adv_time_general = 14 * 24 * 60 # 2 weeks
                                            action_taken_custom_time = True

                                            # Calculate video quality
                                            base_quality = 0.2
                                            base_quality += (budget / 10000) * 0.3 # Max 0.3 from budget up to 10k
                                            base_quality += (player.fame / 200) * 0.2 # Max 0.2 from fame up to 200
                                            base_quality += selected_song.song_quality * 0.3 # Max 0.3 from song quality

                                            video_quality = round(max(0.1, min(1.0, base_quality + random.uniform(-0.1, 0.1))), 2)

                                            selected_song.has_music_video = True
                                            selected_song.music_video_quality = video_quality

                                            buzz_increase = video_quality * random.randint(30, 60) # Significant buzz
                                            selected_song.buzz_score = min(100, selected_song.buzz_score + buzz_increase)

                                            player.signed_label_deal["music_video_produced_for_deal"] = True
                                            player.signed_label_deal["music_video_budget_single"] = 0 # Budget is used up

                                            print(f"\nMusic video for '{selected_song.title}' is complete!")
                                            print(f"  Video Quality: {video_quality*100:.0f}/100")
                                            print(f"  Song Buzz increased by {buzz_increase:.1f} to {selected_song.buzz_score:.1f}!")
                                            print(f"This project took significant time and effort.")
                                            player.energy = max(0, player.energy - 30)
                                            player.stress = min(100, player.stress + 15)
                                            deal['label_relationship_score'] = min(100, deal['label_relationship_score'] + 5)
                                            print(f"Your relationship with {deal['label_name']} improved slightly (+5).")

                                        else:
                                            print("Music video production cancelled.")
                                            adv_time_general = 10
                                    else:
                                        print("No song selected or production cancelled.")
                                        adv_time_general = 10
                            else:
                                print("Conditions not met for music video production discussion (e.g., no budget, already produced, or not at your label's office).")
                                adv_time_general = 5
                            action_taken_custom_time = True
                        elif chosen_text == "Discuss Album Release with Label":
                            print("\n--- Discuss Album Release ---")
                            adv_time_general = 15 # Base time for discussion
                            action_taken_custom_time = True
                            if player.signed_label_deal and \
                               player.signed_label_deal.get('label_poi_id') == poi.poi_id and \
                               player.signed_label_deal.get("albums_remaining_on_commitment", 0) > 0:

                                deal = player.signed_label_deal
                                label_id = deal['label_poi_id']
                                MIN_SONGS_FOR_ALBUM = random.randint(6,8) # Label might want 6-8 songs for a release

                                eligible_songs_for_album = [
                                    s for s in player.songs_written
                                    if s.is_recorded and s.is_released and
                                    (s.considered_for_album_with_label_id is None or s.considered_for_album_with_label_id != label_id)
                                ]
                                # Also consider songs released via this label specifically, even if not marked by considered_for_album_with_label_id yet
                                # This logic might need refinement if a song can be on multiple indie albums then a label album

                                if len(eligible_songs_for_album) < MIN_SONGS_FOR_ALBUM:
                                    print(f"{deal['label_name']} feels you don't have enough new, unreleased (on an album with them) material. Need at least {MIN_SONGS_FOR_ALBUM} suitable songs. You have {len(eligible_songs_for_album)}.")
                                else:
                                    print(f"You propose releasing an album with {deal['label_name']}. You have {len(eligible_songs_for_album)} potentially suitable recorded songs.")
                                    avg_quality = sum(s.song_quality for s in eligible_songs_for_album) / len(eligible_songs_for_album) if eligible_songs_for_album else 0
                                    avg_rec_quality = sum(s.recording_quality for s in eligible_songs_for_album) / len(eligible_songs_for_album) if eligible_songs_for_album else 0

                                    approval_chance = deal.get('label_relationship_score', 50)
                                    approval_chance += (avg_quality * 50) # Max 50 from song quality
                                    approval_chance += (avg_rec_quality * 25) # Max 25 from recording quality
                                    approval_chance -= (MIN_SONGS_FOR_ALBUM - len(eligible_songs_for_album)) * 5 # Penalty if just at min

                                    print(f"(Debug: Album Approval Score Base: {deal.get('label_relationship_score', 50)}, AvgSongQBonus: {avg_quality*50:.1f}, AvgRecQBonus: {avg_rec_quality*25:.1f} -> Total: {approval_chance:.1f})")

                                    if approval_chance >= 65 : # Needs decent score and songs
                                        print(f"{deal['label_name']} is excited! \"This sounds like a strong collection, {player.name}! Let's do it.\"")

                                        album_songs_to_release = sorted(eligible_songs_for_album, key=lambda x: x.song_quality, reverse=True)[:random.randint(MIN_SONGS_FOR_ALBUM, MIN_SONGS_FOR_ALBUM + 2)] # Take best N songs

                                        print("\nThe following songs will be featured on the album:")
                                        for s_idx, s_obj in enumerate(album_songs_to_release):
                                            print(f"  {s_idx+1}. {s_obj.title}")

                                        if input(f"Proceed with releasing these {len(album_songs_to_release)} songs as an album? (This will take 4-8 weeks) (y/n) > ").lower() == 'y':
                                            release_time_weeks = random.randint(4, 8)
                                            adv_time_general += (release_time_weeks * 7 * 24 * 60) - 15 # Subtract base time already added

                                            player.fame += random.randint(15, 30) + int(avg_quality * 10)
                                            deal["albums_remaining_on_commitment"] = max(0, deal["albums_remaining_on_commitment"] - 1)

                                            for song_item in album_songs_to_release:
                                                song_item.considered_for_album_with_label_id = label_id
                                                # Potentially boost buzz for album tracks
                                                song_item.buzz_score = min(100, song_item.buzz_score + random.uniform(5,15) * song_item.song_quality)

                                            print(f"\nYour new album has been released through {deal['label_name']}!")
                                            print(f"Fame increased. Albums remaining on contract: {deal['albums_remaining_on_commitment']}.")
                                            print("The critics and fans are starting to react...")

                                            album_review = generate_feedback_for_album(player, album_songs_to_release, deal['label_name'], current_game_time)
                                            if album_review:
                                                player.feedback_received.append(album_review)
                                                print(f"Review from {album_review['source']}: \"{album_review['quote'][:100]}...\"")
                                                if 'fame' in album_review['impact']:
                                                    player.fame = max(0, player.fame + album_review['impact']['fame'])
                                                if 'stress' in album_review['impact']:
                                                    player.stress = min(100, max(0, player.stress + album_review['impact']['stress']))
                                                if 'label_relationship' in album_review['impact']:
                                                    deal['label_relationship_score'] = min(100, max(0, deal['label_relationship_score'] + album_review['impact']['label_relationship']))
                                                print(f"(Fame: {player.fame}, Stress: {player.stress}, Label Rel: {deal['label_relationship_score']})")

                                            deal['label_relationship_score'] = min(100, max(0,deal['label_relationship_score'] + 10 + int(avg_quality*10))) # General boost for releasing
                                            player.stress = max(0, player.stress - random.randint(5,15)) # Release is good
                                            player.energy = max(0, player.energy - 20)
                                        else:
                                            print("Album release cancelled by player.")
                                    elif approval_chance >= 40:
                                        print(f"{deal['label_name']} is hesitant. \"Hmm, it's promising, but maybe not quite there yet. Work on a few more stronger tracks.\"")
                                        deal['label_relationship_score'] = max(0, deal['label_relationship_score'] - 2)
                                    else:
                                        print(f"{deal['label_name']} doesn't think this collection is ready. \"This isn't what we're looking for right now, {player.name}.\"")
                                        deal['label_relationship_score'] = max(0, deal['label_relationship_score'] - 5)
                                        player.stress = min(100, player.stress + 5)
                            else:
                                print("Cannot discuss album release. Not signed, or no albums left on commitment with this label.")

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

                        songs_disp = [str(s) for s in player.songs_written]
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
