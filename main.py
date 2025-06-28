from game.player import Player
from game.player import Player
from game.location import Location
from game.venue import Venue
from game.poi import PointOfInterest
from game.event import Event
from game.game_time import current_game_time, advance_game_time, get_current_time_str
from game.dialogue import generate_npc_response, NPC_PERSONALITIES
from game.random_events import check_for_random_event, check_for_post_gig_random_event
from game.song import Song # Import Song class
import random # For songwriting inspiration

from game_data.gear_catalog import GEAR_CATALOG

# --- Game World Setup ---
from game.npc import NPC # Import NPC class

# Global dictionary to hold all location objects, keyed by name for easy lookup
WORLD_MAP = {}
# Global dictionary to hold all NPC objects, keyed by npc_id
NPC_REGISTRY = {}

# Global Player Home POI ID (set after setup_world in main())
PLAYER_HOME_POI_ID_GLOBAL = None

# --- Player Needs Update Function ---
def process_time_based_player_needs(player, minutes_just_passed):
    if minutes_just_passed <= 0:
        return

    hours_passed_float = minutes_just_passed / 60.0

    # 1. Comfort update based on current POI's hourly modifier
    if player.current_poi and hasattr(player.current_poi, 'comfort_modifier_hourly'):
        comfort_change = hours_passed_float * player.current_poi.comfort_modifier_hourly
        player.comfort = min(100, max(0, player.comfort + comfort_change))
        player.comfort = int(round(player.comfort))

    # 2. Homesickness update
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

    # 3. Stress impact from high homesickness
    if player.homesickness > 75:
        stress_increase_rate_from_homesickness = ((player.homesickness - 75) / 25.0) * 1.0
        player.stress = min(100, player.stress + (hours_passed_float * stress_increase_rate_from_homesickness))
        player.stress = int(round(player.stress))

def setup_world():
    global WORLD_MAP, NPC_REGISTRY
    # Create Locations
    home_town = Location("Your Hometown", "A quiet place, good for starting out.")
    city_center = Location("City Center", "A bustling hub with more opportunities.")
    # Add more locations if desired (e.g., "The Suburbs", "University District")

    WORLD_MAP = {
        home_town.name: home_town,
        city_center.name: city_center,
    }

    # Define Venues and POIs
    # Hometown Venues
    community_hall = Venue(
        venue_id="hometown_community_hall",
        name="Community Hall",
        description="Hosts local events.",
        venue_type="HALL",
        category="VENUE_HALL",
        capacity=50,
        prestige=1,
        parent_location_id=home_town.name,
        can_rent_gear=False # Community hall doesn't rent gear
    )
    home_town.add_venue(community_hall)

    # Hometown POIs
    music_shop_home = PointOfInterest(
        poi_id="hometown_music_shop_oldtimers",
        name="Old Timer's Music Shop",
        description="Sells basic gear and instruments.",
        category="SHOP_MUSIC",
        interaction_options=["Browse items for sale", "Talk to Old Timer Joe"], # Updated interaction
        parent_location_id=home_town.name
    )
    music_shop_home.shop_inventory_item_ids = [
        "worn_acoustic_guitar",
        "guitar_strings_basic",
        "guitar_picks_assorted"
    ]
    home_town.add_poi(music_shop_home)
    rehearsal_space_home = PointOfInterest(
        poi_id="hometown_rehearsal_garage",
        name="Garage Rehearsal Space",
        description="A bit rough but it's cheap.",
        category="REHEARSAL_STUDIO",
        interaction_options=["Book Rehearsal Time (1 hour, $10)"],
        parent_location_id=home_town.name
    )
    home_town.add_poi(rehearsal_space_home)

    # City Center Venues
    rusty_mug_club = Venue(
        venue_id="citycenter_rustymug",
        name="The Rusty Mug",
        description="A well-known club for upcoming bands.",
        venue_type="CLUB",
        category="VENUE_CLUB",
        capacity=150,
        prestige=4,
        parent_location_id=city_center.name,
        can_rent_gear=True,
        gear_rental_fee=30, # Cost to rent at Rusty Mug
        available_rental_gear_ids=["basic_electric_guitar", "practice_amp_small"] # What they offer
    )
    city_center.add_venue(rusty_mug_club)
    grande_theater = Venue(
        venue_id="citycenter_grandetheater",
        name="Grande Concert Hall",
        description="A prestigious venue for established artists.",
        venue_type="CONCERT_HALL",
        category="VENUE_THEATER",
        capacity=1000,
        prestige=8,
        parent_location_id=city_center.name,
        can_rent_gear=True, # High-end venues often have backline
        gear_rental_fee=100,
        available_rental_gear_ids=["pro_electric_guitar", "pro_bass_guitar", "pro_amp_large", "pro_drum_kit"] # Example pro gear
    )
    city_center.add_venue(grande_theater)

    # City Center POIs
    pro_music_store = PointOfInterest(
        poi_id="citycenter_proaudio",
        name="Pro Audio Central",
        description="High-end instruments and recording gear.",
        category="SHOP_MUSIC",
        interaction_options=["Browse items for sale", "Talk to Sales Rep"], # Updated interaction
        parent_location_id=city_center.name
    )
    pro_music_store.shop_inventory_item_ids = [
        "basic_electric_guitar",
        "practice_amp_small",
        "guitar_strings_basic",
        "guitar_picks_assorted"
        # Can add more expensive/pro items from catalog here later
    ]
    city_center.add_poi(pro_music_store)
    record_label_office = PointOfInterest(
        poi_id="citycenter_indiehits_records",
        name="Indie Hits Records",
        description="A small but ambitious record label. They seem to like fresh sounds.",
        category="OFFICE_RECORD_LABEL",
        interaction_options=[], # Will be dynamically generated or set based on fame
        parent_location_id=city_center.name,
        min_fame_to_submit=75, # Lowered for easier early testing
        genres_preferred=["Indie", "Pop", "Rock", "Electronic"]
    )
    # Dynamically create interaction option text based on min_fame_to_submit
    record_label_office.interaction_options = [
        f"Submit Demo (requires {record_label_office.min_fame_to_submit} fame)",
        "Talk to A&R Rep (requires Manager)" # Placeholder for now
    ]
    city_center.add_poi(record_label_office)
    downtown_cafe = PointOfInterest(
        poi_id="citycenter_dailygrind_cafe",
        name="The Daily Grind Cafe",
        description="Popular hangout, good coffee, free Wi-Fi.",
        category="POI_CAFE",
        interaction_options=["Grab Coffee ($5)", "People Watch", "Look for Local Flyers"],
        parent_location_id=city_center.name,
        comfort_modifier_hourly=1 # Slightly comforting to be in a cafe
    )
    city_center.add_poi(downtown_cafe)

    # --- Define New Key POIs for Intra-City Travel & Player Start ---
    # Your Hometown
    player_home = PointOfInterest(
        poi_id="hometown_player_home",
        name="Your Apartment",
        description="Your starting digs. A bit small, but it's home.",
        category="HOME",
        interaction_options=["Rest (8 hours)", "Practice guitar (at home)", "Write a new song", "Relax at home (2 hours)"],
        parent_location_id=home_town.name,
        rest_quality=0.8,
        stress_modifier_hourly=-10,
        comfort_modifier_hourly=5 # Home is very comforting
    )
    home_town.add_poi(player_home)

    bus_stop_hometown = PointOfInterest(
        poi_id="hometown_bus_stop",
        name="Hometown Bus Stop",
        description="A dusty bus stop for regional travel to City Center.",
        category="TRANSPORT_BUS",
        interaction_options=["View Departures & Buy Tickets"], # Standardized option
        parent_location_id=home_town.name
    )
    home_town.add_poi(bus_stop_hometown)

    # City Center
    city_airport = PointOfInterest(
        poi_id="citycenter_airport",
        name="City Center International Airport",
        description="Flights to other major cities (when you can afford them).",
        category="TRANSPORT_AIRPORT",
        interaction_options=["View Departures & Buy Tickets"], # Standardized option
        parent_location_id=city_center.name
    )
    city_center.add_poi(city_airport)

    city_bus_station = PointOfInterest(
        poi_id="citycenter_bus_station",
        name="Main Bus Terminal (City Center)",
        description="Regional and long-haul bus services.",
        category="TRANSPORT_BUS",
        interaction_options=["View Departures & Buy Tickets"], # Standardized option
        parent_location_id=city_center.name
    )
    city_center.add_poi(city_bus_station)

    crash_pad_motel = PointOfInterest(
        poi_id="citycenter_motel_cheap",
        name="Sleep EZ Motel",
        description="A cheap, somewhat clean room for the night. Better than the streets.",
        category="ACCOMMODATION_CHEAP",
        interaction_options=["Rent Room ($50/night)", "Sleep (8 hours, if rented)"],
        parent_location_id=city_center.name,
        rest_quality=0.4,
        stress_modifier_hourly=-2,
        comfort_modifier_hourly=-3 # Grim places can reduce comfort
    )
    city_center.add_poi(crash_pad_motel)

    starlight_studio = PointOfInterest(
        poi_id="citycenter_starlight_studio",
        name="Starlight Recording Studio",
        description="A decent local recording studio. Sessions can be booked by the hour.",
        category="STUDIO_RECORDING",
        interaction_options=["Book recording session", "Talk to Sound Engineer (if available)"],
        parent_location_id=city_center.name,
        studio_quality=0.6, # Mid-tier studio
        hourly_rate=50      # $50 per hour
    )
    city_center.add_poi(starlight_studio)


    # Define Travel Connections (Location Name -> {cost, time}) # INTER-CITY
    home_town.add_travel_connection(city_center.name, cost=20, time_hours=2)
    city_center.add_travel_connection(home_town.name, cost=20, time_hours=2)

    # --- Define Intra-City POI Connections ---
    # Your Hometown Connections
    home_town.intra_city_poi_connections[frozenset({player_home.poi_id, music_shop_home.poi_id})] = {
        "walk": {"time": 15, "cost": 0},
        "bike": {"time": 5, "cost": 0, "requires_bike": True},
        "taxi": {"time": 3, "cost": 8}
    }
    home_town.intra_city_poi_connections[frozenset({player_home.poi_id, community_hall.venue_id})] = {
        "walk": {"time": 10, "cost": 0},
        "bike": {"time": 3, "cost": 0, "requires_bike": True},
        "taxi": {"time": 2, "cost": 6}
    }
    home_town.intra_city_poi_connections[frozenset({player_home.poi_id, bus_stop_hometown.poi_id})] = {
        "walk": {"time": 20, "cost": 0},
        "bike": {"time": 7, "cost": 0, "requires_bike": True},
        "taxi": {"time": 5, "cost": 10}
    }
    home_town.intra_city_poi_connections[frozenset({music_shop_home.poi_id, community_hall.venue_id})] = {
        "walk": {"time": 5, "cost": 0},
        "bike": {"time": 2, "cost": 0, "requires_bike": True},
        # No direct taxi, too short / must walk from player_home
    }
    # City Center Connections (Example - can be expanded)
    # Assuming city_bus_station, rusty_mug_club, pro_music_store, downtown_cafe, city_airport, crash_pad_motel are defined POI/Venue objects
    city_center.intra_city_poi_connections[frozenset({city_bus_station.poi_id, rusty_mug_club.venue_id})] = {
        "walk": {"time": 25, "cost": 0},
        "bike": {"time": 10, "cost": 0, "requires_bike": True}, # Player might not have bike in new city initially
        "taxi": {"time": 7, "cost": 12}
    }
    city_center.intra_city_poi_connections[frozenset({rusty_mug_club.venue_id, pro_music_store.poi_id})] = {
        "walk": {"time": 10, "cost": 0},
        "bike": {"time": 4, "cost": 0, "requires_bike": True},
        "taxi": {"time": 3, "cost": 7}
    }
    city_center.intra_city_poi_connections[frozenset({downtown_cafe.poi_id, rusty_mug_club.venue_id})] = {
        "walk": {"time": 12, "cost": 0},
        "bike": {"time": 5, "cost": 0, "requires_bike": True},
        "taxi": {"time": 4, "cost": 9}
    }
    city_center.intra_city_poi_connections[frozenset({city_bus_station.poi_id, city_airport.poi_id})] = {
        "walk": {"time": 60, "cost": 0}, # Long walk
        # "bike": {"time": 25, "cost": 0, "requires_bike": True}, # Maybe not bikeable easily
        "taxi": {"time": 15, "cost": 25} # Airport taxi usually more
    }

    # Events (now primarily associated with Venues)
    open_mic_event = Event(
        name="Open Mic Night",
        event_type="OPEN_MIC",
        location=community_hall,
        required_skills={"vocals": 1, "guitar": 1},
        required_gear_types=["INSTRUMENT_ACOUSTIC"], # Open mic often acoustic
        description="A chance to show your skills at the local Community Hall."
    )
    community_hall.add_event(open_mic_event)

    first_club_gig_event = Event(
        name="Debut at 'The Rusty Mug'",
        event_type="CLUB_GIG",
        location=rusty_mug_club,
        required_skills={"vocals": 5, "guitar": 5, "stage_presence": 3},
        required_gear_types=["INSTRUMENT_ELECTRIC", "AMPLIFIER"], # Electric gig
        description="Your first real club gig! Make it count.",
    )
    first_club_gig_event.preparation_tasks_required = {
        "Write Setlist (3 songs)": False,
        "Rehearse Set (2 hours)": False,
        "Promote Gig Locally (social media post)": False
    }
    rusty_mug_club.add_event(first_club_gig_event)

    # Example of a higher tier event (player likely won't qualify for a while)
    opening_act_concert = Event(
        name="Opening Act for Major Band",
        event_type="CONCERT",
        location=grande_theater,
        required_skills={"vocals": 15, "guitar": 15, "stage_presence": 10, "songwriting": 10},
        required_gear_types=["INSTRUMENT_ELECTRIC", "AMPLIFIER", "INSTRUMENT_BASS", "INSTRUMENT_DRUMS"], # Full band setup
        description="A huge opportunity to open for a touring band at the Grande Concert Hall!",
    )
    opening_act_concert.preparation_tasks_required = {
        "Finalize Setlist (5 songs, original material preferred)": False,
        "Intensive Rehearsal Week (10 hours)": False,
        "Coordinate with Main Act's Team": False,
        "Sound Check (2 hours, day of show)": False,
    }
    # This event might only be added if player has a manager or high fame
    # For now, add it so it's visible if player gets to City Center.
    grande_theater.add_event(opening_act_concert)

    # --- Instantiate NPCs ---
    # Old Timer Joe at his music shop in Hometown
    # For schedule, using object references directly instead of names for now for simplicity
    joe = NPC(npc_id="joe001", name="Old Timer Joe", personality_key="old_timer_joe", home_location=music_shop_home)
    joe.current_location = music_shop_home
    joe.schedule = {
        "Weekday_Morning": music_shop_home,
        "Weekday_Afternoon": music_shop_home,
        "Weekend_Morning": music_shop_home, # Covers Saturday and Sunday morning
        "Weekend_Evening": community_hall  # Covers Sunday evening (and Saturday if no other rule overrides)
    }
    NPC_REGISTRY[joe.npc_id] = joe
    music_shop_home.owner_npc_id = joe.npc_id

    # Sarah the Fan, often found where music is, especially in Hometown
    sarah = NPC(npc_id="sarah001", name="Sarah the Fan", personality_key="adoring_fan", home_location=WORLD_MAP["Your Hometown"])
    sarah.current_location = WORLD_MAP["Your Hometown"]
    sarah.schedule = {
        "open_mic_night_at_community_hall": community_hall
    }
    NPC_REGISTRY[sarah.npc_id] = sarah

    # Vic Vega, owner of The Rusty Mug in City Center
    vic = NPC(npc_id="vic001", name="Vic Vega", personality_key="gruff_club_owner", home_location=rusty_mug_club)
    vic.current_location = rusty_mug_club
    vic.schedule = {
        "Weekday_Afternoon": rusty_mug_club,
        "Weekday_Evening": rusty_mug_club,
        "Weekend_Evening": rusty_mug_club, # Covers Sat/Sun evenings
    }
    NPC_REGISTRY[vic.npc_id] = vic
    rusty_mug_club.owner_npc_id = vic.npc_id

    # Potential Bandmate - Alex Miles
    alex = NPC(npc_id="alex001", name="Alex 'Shredder' Miles", personality_key="potential_bandmate_guitarist", home_location=pro_music_store)
    alex.current_location = pro_music_store # Starts at the pro music store
    # alex.skills = {"guitar": 18, "songwriting": 7} # Store skills if NPC class supports it, or for dev reference
    alex.schedule = {
        "Weekday_Afternoon": pro_music_store, # Using keys from get_time_slot_key
        "Weekday_Evening": rusty_mug_club,
        "Weekend_Afternoon": pro_music_store, # Assuming Weekend maps to Saturday/Sunday
        "Weekend_Evening": rusty_mug_club,
    }
    NPC_REGISTRY[alex.npc_id] = alex

    # Music Blogger - Casey Jones
    casey = NPC(npc_id="casey001", name="Casey 'The Cynic' Jones", personality_key="music_blogger_critical", home_location=downtown_cafe) # Home is the cafe
    casey.current_location = downtown_cafe # Starts at the cafe
    casey.schedule = {
        "Weekday_Morning": downtown_cafe,
        "Weekday_Afternoon": downtown_cafe,
        "Weekday_Evening": rusty_mug_club, # Checks out gigs at Rusty Mug
        "Weekend_Evening": grande_theater, # Might check out bigger shows at Grande Theater too
    }
    NPC_REGISTRY[casey.npc_id] = casey


# --- Time and Scheduling Helpers ---
def get_day_of_week_name(day_number_in_month):
    """ Returns a conceptual day of the week based on a 1-30 day month.
        0=Sun, 1=Mon, ..., 6=Sat (repeats).
    """
    # Simple modulo 7 for a repeating weekly cycle.
    # (day_number_in_month - 1) to make day 1 be the first day of the cycle.
    day_index = (day_number_in_month - 1) % 7
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] # Day 1 is Monday
    return days[day_index]

def get_time_slot_key(game_time_obj):
    """
    Converts the current game_time object into a descriptive key for NPC scheduling.
    e.g., "Weekday_Morning", "Saturday_Evening", "Sunday_Night"
    """
    day_name = get_day_of_week_name(game_time_obj.day)
    hour = game_time_obj.hour

    day_type = "Weekend" if day_name in ["Saturday", "Sunday"] else "Weekday"

    time_period = "Night" # Default
    if 6 <= hour <= 11:
        time_period = "Morning"
    elif 12 <= hour <= 17:
        time_period = "Afternoon"
    elif 18 <= hour <= 23: # Evening includes up to 11 PM
        time_period = "Evening"
    # Hours 0-5 remain "Night"

    return f"{day_type}_{time_period}" # e.g. Weekday_Morning

# --- NPC Scheduling and Movement ---
def update_npc_locations(game_time_obj):
    """
    Updates NPCs' current_location based on their schedule and the current game time.
    This is a basic implementation. More complex logic for event attendance or specific
    conditions could be added.
    """
    current_time_slot_key = get_time_slot_key(game_time_obj)
    # print(f"DEBUG: Updating NPC locations for time slot: {current_time_slot_key}") # Debug

    for npc in NPC_REGISTRY.values():
        # Default to home location if no specific schedule matches
        scheduled_destination = npc.home_location

        # Check general time slot first (e.g., "Weekday_Morning")
        if current_time_slot_key in npc.schedule:
            scheduled_destination_ref = npc.schedule[current_time_slot_key]
            # Ensure the reference is an object, not just a name string if we used names in schedule
            if isinstance(scheduled_destination_ref, str): # If schedule stores names
                 # This part needs WORLD_MAP to resolve names to objects,
                 # or schedule should store direct object references.
                 # For now, assuming schedule stores direct object references as per NPC instantiation.
                 print(f"Warning: NPC {npc.name} schedule might be using names. Ensure object references.")
                 # Attempt to resolve, but this is brittle.
                 # It's better if schedule values are already location/venue/poi objects.
                 resolved_loc = WORLD_MAP.get(scheduled_destination_ref)
                 if resolved_loc: scheduled_destination = resolved_loc
                 # Could also check venues within WORLD_MAP locations, and POIs. More complex.
            else: # Assuming it's already an object
                scheduled_destination = scheduled_destination_ref

        # Add more sophisticated schedule checks here, e.g., for specific event flags
        # For "Sarah the Fan" and her "open_mic_night_at_community_hall":
        if npc.npc_id == "sarah001": # Specific logic for Sarah
            # Check if an open mic event is active at the community hall
            community_hall_obj = WORLD_MAP["Your Hometown"].venues[0] # Assuming it's the first venue
            open_mic_active = any(event.name == "Open Mic Night" and event.is_active for event in community_hall_obj.events_hosted)
            if "open_mic_night_at_community_hall" in npc.schedule and open_mic_active:
                if npc.schedule["open_mic_night_at_community_hall"] == community_hall_obj : # Check if her schedule points to the right place
                     scheduled_destination = community_hall_obj

        if npc.current_location != scheduled_destination:
            # print(f"DEBUG: Moving {npc.name} from {npc.current_location.name if npc.current_location else 'Unknown'} to {scheduled_destination.name if scheduled_destination else 'Unknown Home'}")
            npc.current_location = scheduled_destination
            # In a more complex system, this could trigger travel time for the NPC,
            # or they might only "arrive" after a certain delay. For now, it's instant.

# --- UI Helper Functions ---
def clear_screen_ish():
    """Prints newlines to simulate clearing the screen."""
    print("\n" * 30) # Adjust number of newlines as needed

def present_choices(options, title="Choose an option:"):
    """
    Presents a numbered list of choices to the player and gets valid input.
    Args:
        options (list or dict): A list of strings, or a dict where keys are choice numbers (str)
                                and values are descriptions.
        title (str): The title to display before the options.
    Returns:
        str: The chosen option key/index as a string, or None if input is invalid after attempts.
    """
    print(f"\n--- {title} ---")
    if isinstance(options, list):
        for i, option_text in enumerate(options):
            print(f"{i+1}. {option_text}")
    elif isinstance(options, dict):
        for key, text in options.items():
            print(f"{key}. {text}")
    else:
        print("Error: Invalid options type for present_choices.")
        return None

    max_attempts = 3
    for attempt in range(max_attempts):
        choice = input("> ")
        if isinstance(options, list):
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                return str(int(choice)) # Return as string to match dict keys if used elsewhere
        elif isinstance(options, dict):
            if choice in options:
                return choice

        print(f"Invalid choice. Please enter a valid number/key. ({max_attempts - 1 - attempt} attempts left)")

    print("Too many invalid attempts.")
    return None


# --- Helper for NPC Interaction ---
# This function is now designed to take an NPC *instance*.
def talk_to_npc_instance(player, npc_instance):
    """Handles the conversation loop with a specific NPC instance."""
    if not npc_instance:
        print("No one specific to talk to here.") # Should be caught by calling logic ideally
        return

    print(f"\n--- Talking to {npc_instance.name} ---")
    # System prompt is now incorporated directly into generate_npc_response
    # We could print npc_instance.personality_key for debug/player info if desired.
    # print(f"DEBUG: NPC Personality Key: {npc_instance.personality_key}, Relationship: {npc_instance.relationship_with_player.name} ({npc_instance.relationship_score})")
    # print(f"DEBUG: NPC Memories: {npc_instance.memories}")
    print(f"Type 'bye' to end the conversation.")

    # Dialogue history is persistent per NPC instance now.
    # reset_npc_dialogue_history(npc_instance) # Uncomment if you want to reset history each time a conversation starts

    while True:
        player_input = input(f"{player.name}: ")
        if player_input.lower() == 'bye':
            print(f"{npc_instance.name} nods or waves goodbye.")
            npc_instance.add_memory(f"Had a conversation with {player.name} that ended.") # Generic memory
            # Future: Small relationship impact based on how convo ended or overall sentiment.
            advance_game_time(minutes=60) # 1 hour
            update_npc_locations(current_game_time)
            break

        if not player_input.strip():
            # print("Say something!") # Or just ignore empty input
            continue

        npc_response = generate_npc_response(player_input, npc_instance, player_name=player.name)
        print(f"{npc_instance.name}: {npc_response}")

        if "LLM Error" in npc_response or "An unexpected error occurred" in npc_response:
            print("It seems there's an issue with the LLM service for this conversation.")
            npc_instance.add_memory(f"Had a communication problem while talking to {player.name}.")
            advance_game_time(minutes=60) # Still consumes some time (1 hour)
            update_npc_locations(current_game_time)
            break

        # Potential post-dialogue actions after each exchange:
        # Ask player to clarify intent for relationship impact
        clarification_options = {
            "1": "Friendly",
            "2": "Neutral",
            "3": "Unfriendly",
            "0": "No specific impact / Continue"
        }
        # Only ask if the conversation is ongoing (no LLM error)
        if not ("LLM Error" in npc_response or "An unexpected error occurred" in npc_response):
            print(f"\nHow should {npc_instance.name} interpret your last statement?")
            intent_choice = present_choices(clarification_options, title="Your intent:")

            relationship_points = 0
            memory_detail = ""

            if intent_choice == "1": # Friendly
                relationship_points = 5
                memory_detail = f"Player ({player.name}) said something friendly: '{player_input}'"
            elif intent_choice == "3": # Unfriendly
                relationship_points = -5
                memory_detail = f"Player ({player.name}) said something unfriendly: '{player_input}'"
            # Neutral or "No impact" (choice "2" or "0" or None) results in 0 points.

            if relationship_points != 0:
                npc_instance.update_relationship(relationship_points)
                npc_instance.add_memory(memory_detail)
                print(f"(Relationship with {npc_instance.name} updated by {relationship_points})")


def main():
    setup_world() # Initialize locations, venues, POIs, events, and NPCs (NPCs will be added next)

    print("Welcome to the Text-Based Music Career Simulator!")
    print("IMPORTANT: This game uses Ollama for NPC conversations.")
    print("Please ensure Ollama is installed, running, and you have pulled the required model (e.g., `ollama pull llama3`).")

    player_name = input("Enter your character's name: ")
    player = Player(player_name)

    # Set player's starting location and POI
    hometown_location = WORLD_MAP.get("Your Hometown")
    player_home_poi = None
    if hometown_location:
        for poi in hometown_location.points_of_interest:
            if poi.poi_id == "hometown_player_home":
                player_home_poi = poi
                break

    if hometown_location and player_home_poi:
        player.current_location = hometown_location
        player.current_poi = player_home_poi
    else:
        # Fallback if something went wrong in setup, though it shouldn't
        print("Error: Could not set player's starting home. Defaulting to Hometown general.")
        player.current_location = hometown_location if hometown_location else list(WORLD_MAP.values())[0] # First available city
        player.current_poi = None

    # Initial NPC location update based on game start time
    update_npc_locations(current_game_time)
    # Initial player needs update based on starting POI (Home) comfort, for 0 time passed.
    # This ensures comfort from home is applied even before first action.
    # Or, simply rely on the first action's time passage to trigger it.
    # Let's do it explicitly here for 0 minutes to set initial comfort from home.
    process_time_based_player_needs(player, 0)


    # Give player starting gear
    starting_guitar = GEAR_CATALOG.get("worn_acoustic_guitar")
    if starting_guitar:
        player.add_gear(starting_guitar)
    starting_picks = GEAR_CATALOG.get("guitar_picks_assorted")
    if starting_picks:
        player.add_gear(starting_picks)
    # No amp to start, player will need to buy or rent for electric gigs.


    print(f"\n--- {get_current_time_str()} ---")
    print(player) # Player's __str__ should now show POI and gear
    # print(f"Current Location: {player.current_location.name if player.current_location else 'N/A'}") # Old way
    # print(f"Current POI: {player.current_poi.name if player.current_poi else 'N/A'}") # For direct check

    # Game Loop
    while True:
        clear_screen_ish()
        print(f"--- Current Location: {player.current_location.name} ---") # Was player.location, fixed to current_location
        print(f"--- {get_current_time_str()} ---")
        print(f"--- Player: {player.name} | Fame: {player.fame} | Money: ${player.money} | Energy: {player.energy}/100 | Stress: {player.stress}/100 ---")
        print(f"--- Currently at: {player.current_poi.name if player.current_poi else player.current_location.name} ---")


        main_menu_options = {
            "1": "Practice a skill",
            "2": "Travel to another City", # Renamed for clarity
            "3": "Travel within this City (to another POI)", # New option
            "4": "Explore current POI/Area", # Renamed/Refocused
            "5": "Check available gigs (at current City)", # Clarified scope
            "6": "Prepare for a gig",
            "7": "Attempt a gig",
            "8": "View detailed player stats",
            "9": "Talk to someone (at current POI/Area)", # Clarified scope
            "00": "Advance time by 1 hour (debug)", # Changed to 00 to avoid conflict if we have 10+ options
            "0": "Quit game"
        }
        # Adjust numbering for subsequent elif blocks
        choice = present_choices(main_menu_options, title=f"What would {player.name} like to do?")

        if choice is None: # Invalid input after multiple tries
            continue

        clear_screen_ish() # Clear screen after choice, before showing action result

        if choice == "1": # Practice a skill
            print("--- Practice a Skill ---")
            skill_to_practice = input("Which skill to practice (e.g., vocals, guitar, stage_presence)? ").lower()
            try:
                hours_to_practice = int(input(f"How many hours to practice {skill_to_practice}? "))
                if hours_to_practice <= 0:
                    print("Practice time must be positive.")
                    continue
                player.practice_skill(skill_to_practice, hours_to_practice)
                minutes_passed = hours_to_practice*60
                advance_game_time(minutes=minutes_passed)
                update_npc_locations(current_game_time)
                process_time_based_player_needs(player, minutes_passed)
            except ValueError:
                print("Invalid number of hours.")

        elif choice == "2": # Go to Transport Hub for Inter-City Travel
            print("\n--- Inter-City Travel Information ---")
            current_city = player.current_location
            transport_hubs_in_city = []
            for poi in current_city.points_of_interest + current_city.venues: # Venues can sometimes be hubs (e.g. a port, though not used yet)
                if hasattr(poi, 'category') and poi.category in ["TRANSPORT_BUS", "TRANSPORT_AIRPORT"]:
                    transport_hubs_in_city.append(poi)

            if not transport_hubs_in_city:
                print(f"{current_city.name} doesn't seem to have any major bus stations or airports defined for inter-city travel.")
            elif player.current_poi and player.current_poi.category in ["TRANSPORT_BUS", "TRANSPORT_AIRPORT"]:
                print(f"You are currently at {player.current_poi.name}.")
                print(f"Please use option '4. Explore current POI/Area' to find departures and buy tickets.")
            else:
                print(f"To travel to another city, you first need to go to a transport hub (bus station or airport).")
                if player.current_poi:
                    print(f"You are currently at: {player.current_poi.name}.")
                else:
                    print(f"You are currently in the general area of {current_city.name}.")
                print(f"\nAvailable transport hubs in {current_city.name}:")

                hub_display_list = [f"{hub.name} ({hub.category})" for hub in transport_hubs_in_city]
                # Add an option to not travel to a hub now
                hub_display_list.append("Nevermind / Stay in current area")

                hub_choice_idx_str = present_choices(hub_display_list, "Go to which transport hub? (Or select 'Nevermind')")

                if hub_choice_idx_str:
                    choice_idx = int(hub_choice_idx_str) -1
                    if 0 <= choice_idx < len(transport_hubs_in_city): # Check if a hub was chosen
                        chosen_hub_poi = transport_hubs_in_city[choice_idx]
                        print(f"\nOkay, to get to {chosen_hub_poi.name}, please use option '3. Travel within this City'.")
                        print(f"Once at {chosen_hub_poi.name}, use option '4. Explore current POI/Area' to arrange inter-city travel.")
                    # Else (if "Nevermind" or invalid), just fall through to end of this action.
            print("--------------------")

        elif choice == "3": # Travel within this City
            print(f"\n--- Travel within {player.current_location.name} ---")
            if not player.current_poi:
                print("You are at a general city location, not a specific Point of Interest. Explore first or select a POI.")
                # Or, list all POIs in the city as if player is at a "city entrance" POI.
                # For now, require player to be at a POI to travel from it.
                # This could be improved by having a "current_general_area" if current_poi is None.
                # Or if current_poi is None, they are at the "city entrance" POI (e.g. bus station if they just arrived).
                # Let's assume for now player.current_poi must be set to use this.
                # A good first action after arriving in a city would be to travel from the arrival POI (e.g. bus station).
                # If player.current_poi is None when arriving in a new city, they should be placed at a default entry POI.
                # This is handled by player.travel() setting current_poi to None.
                # The game loop or "Explore POI/Area" should then guide them.
                # For now, if current_poi is None, let's allow travel from "city entrance" conceptually
                # by listing all POIs as destinations.

            current_city_object = player.current_location
            dest_poi_options = []
            # Gather all POIs and Venues in the current city
            all_city_pois_and_venues = current_city_object.points_of_interest + current_city_object.venues

            for poi_obj in all_city_pois_and_venues:
                if poi_obj != player.current_poi: # Don't list current POI as destination
                    dest_poi_options.append(poi_obj)

            if not dest_poi_options:
                print("No other specific points of interest to travel to in this city.")
            else:
                print("Where would you like to go in the city?")
                dest_display_list = [f"{poi.name} ({poi.category if hasattr(poi,'category') else poi.venue_type})" for poi in dest_poi_options]
                dest_choice_idx_str = present_choices(dest_display_list, "Choose destination POI:")

                if dest_choice_idx_str:
                    chosen_destination_poi = dest_poi_options[int(dest_choice_idx_str) - 1]

                    # Determine origin POI ID (can be tricky if player.current_poi is None)
                    # For now, let's assume if player.current_poi is None, they are at a conceptual "city_entrance"
                    # and we need connections FROM that entrance, or we just use a default travel time.
                    # This part of the design needs refinement if player.current_poi can be None often.
                    # For this iteration, we will assume player.current_poi is usually set.
                    # If not, this travel option might not work perfectly or offer limited modes.

                    origin_poi_id = player.current_poi.poi_id if hasattr(player.current_poi, 'poi_id') else \
                                    (player.current_poi.venue_id if hasattr(player.current_poi, 'venue_id') else None)

                    dest_poi_id = chosen_destination_poi.poi_id if hasattr(chosen_destination_poi, 'poi_id') else \
                                  chosen_destination_poi.venue_id

                    if not origin_poi_id:
                        print("Cannot determine your precise starting point for intra-city travel. Try exploring first.")
                        # Or provide default "from city edge" travel times
                    else:
                        connection_key = frozenset({origin_poi_id, dest_poi_id})
                        travel_modes_data = current_city_object.intra_city_poi_connections.get(connection_key)

                        if not travel_modes_data:
                            print(f"No direct travel route defined between {player.current_poi.name} and {chosen_destination_poi.name}. You might need to find another way or this is an oversight in city planning!")
                        else:
                            print(f"Travel modes to {chosen_destination_poi.name}:")
                            available_modes_for_choice = {}
                            mode_map = {}
                            choice_num = 1

                            if "walk" in travel_modes_data:
                                mode_info = travel_modes_data["walk"]
                                available_modes_for_choice[str(choice_num)] = f"Walk: {mode_info['time']} mins, Cost: ${mode_info['cost']}"
                                mode_map[str(choice_num)] = ("walk", mode_info)
                                choice_num += 1
                            if player.has_bike and "bike" in travel_modes_data:
                                mode_info = travel_modes_data["bike"]
                                available_modes_for_choice[str(choice_num)] = f"Bike: {mode_info['time']} mins, Cost: ${mode_info['cost']}"
                                mode_map[str(choice_num)] = ("bike", mode_info)
                                choice_num += 1
                            if "taxi" in travel_modes_data:
                                mode_info = travel_modes_data["taxi"]
                                available_modes_for_choice[str(choice_num)] = f"Taxi: {mode_info['time']} mins, Cost: ${mode_info['cost']}"
                                mode_map[str(choice_num)] = ("taxi", mode_info)
                                choice_num += 1

                            if not available_modes_for_choice:
                                print("No travel modes available for this route (this shouldn't happen if data exists).")
                            else:
                                mode_choice_key = present_choices(available_modes_for_choice, "Choose travel mode:")
                                if mode_choice_key and mode_choice_key in mode_map:
                                    chosen_mode_name, chosen_mode_details = mode_map[mode_choice_key]

                                    # Check affordability for taxi
                                    if chosen_mode_name == "taxi" and player.money < chosen_mode_details['cost']:
                                        print(f"Not enough money for a taxi. Need ${chosen_mode_details['cost']}.")
                                    # Check gear capacity
                                    elif player.get_current_gear_load() > player.get_current_gear_capacity(chosen_mode_name):
                                        print(f"Too much gear to travel by {chosen_mode_name}. Your load: {player.get_current_gear_load()}, Capacity for {chosen_mode_name}: {player.get_current_gear_capacity(chosen_mode_name)}.")
                                    else:
                                        if chosen_mode_name == "taxi":
                                            player.money -= chosen_mode_details['cost']
                                            print(f"Paid ${chosen_mode_details['cost']} for the taxi.")

                                        player.travel_within_city(chosen_destination_poi, chosen_mode_details['time'])
                                        advance_game_time(minutes=chosen_mode_details['time'])
                                        update_npc_locations(current_game_time)
            print("--------------------")


        elif choice == "4": # Explore current POI/Area (was 3)
            print(f"\n--- Exploring {player.current_poi.name if player.current_poi else player.current_location.name} ---")
            if player.current_poi:
                print(f"Description: {player.current_poi.description}")
                if player.current_poi.interaction_options:
                    # Let player choose an interaction from the POI's list
                    interaction_choice_key = present_choices(
                        player.current_poi.interaction_options,
                        title=f"Actions at {player.current_poi.name}:"
                    )

                    if interaction_choice_key:
                        chosen_interaction_text = player.current_poi.interaction_options[int(interaction_choice_key) -1]
                        print(f"You chose to: {chosen_interaction_text}")

                        # --- SHOPPING LOGIC ---
                        if player.current_poi.category == "SHOP_MUSIC" and chosen_interaction_text == "Browse items for sale":
                            if player.current_poi.shop_inventory_item_ids:
                                shop_stock_display = []
                                item_map = {} # Maps display index to actual GearItem object
                                current_item_idx = 1
                                for item_id in player.current_poi.shop_inventory_item_ids:
                                    item = GEAR_CATALOG.get(item_id)
                                    if item:
                                        shop_stock_display.append(f"{item.name} - ${item.cost} (Size: {item.size}) - {item.description}")
                                        item_map[str(current_item_idx)] = item
                                        current_item_idx +=1

                                if not shop_stock_display:
                                    print(f"{player.current_poi.name} seems to be out of stock right now.")
                                else:
                                    item_to_buy_key = present_choices(shop_stock_display, title=f"Items for sale at {player.current_poi.name}: (0 to cancel)")

                                    if item_to_buy_key and item_to_buy_key != "0" and item_to_buy_key in item_map:
                                        selected_item = item_map[item_to_buy_key]
                                        print(f"You selected: {selected_item.name}")

                                        if player.money >= selected_item.cost:
                                            if player.can_carry_gear(selected_item): # Checks default capacity
                                                player.money -= selected_item.cost
                                                player.add_gear(selected_item) # This already prints success
                                                print(f"Remaining money: ${player.money}")
                                            else:
                                                # add_gear prints its own capacity error, but we can add context
                                                print(f"You can't carry {selected_item.name} right now.")
                                        else:
                                            print(f"Not enough money to buy {selected_item.name}. Need ${selected_item.cost}, have ${player.money}.")
                                    elif item_to_buy_key == "0":
                                        print("Cancelled shopping.")
                                    # else: present_choices handles invalid input from item list
                            else:
                                print(f"{player.current_poi.name} has nothing for sale right now.")
                        # --- END SHOPPING LOGIC ---

                        # TODO: Implement other POI interactions here based on chosen_interaction_text

                        # --- INTER-CITY TRAVEL BOOKING LOGIC ---
                        elif (player.current_poi.category in ["TRANSPORT_BUS", "TRANSPORT_AIRPORT"] and
                              chosen_interaction_text == "View Departures & Buy Tickets"):

                            connections = player.current_location.travel_connections
                            if not connections:
                                print(f"No inter-city travel routes currently available from {player.current_location.name}.")
                            else:
                                print(f"\n--- Inter-City Departures from {player.current_poi.name} ---")
                                dest_options_list = []
                                dest_map = {} # Maps display index to (dest_name, details_dict)

                                for i, (dest_name, details) in enumerate(connections.items()):
                                    # Implicitly, bus station connects to bus routes, airport to flights.
                                    # For now, all connections from a city are available at any of its hubs.
                                    # Future: Filter by hub type (bus station POI only shows bus routes etc.)
                                    travel_mode_implicit = "Bus" if player.current_poi.category == "TRANSPORT_BUS" else "Plane"
                                    option_text = f"To {dest_name} by {travel_mode_implicit} (Cost: ${details['cost']}, Time: {details['time_hours']} hours)"
                                    dest_options_list.append(option_text)
                                    dest_map[str(i+1)] = (dest_name, details)

                                if not dest_options_list:
                                     print(f"No departures listed from {player.current_poi.name} right now.")
                                else:
                                    dest_choice_key = present_choices(dest_options_list, title="Select destination: (0 to cancel)")
                                    if dest_choice_key and dest_choice_key != "0" and dest_choice_key in dest_map:
                                        chosen_dest_name, travel_details = dest_map[dest_choice_key]

                                        confirm_prompt = f"Travel to {chosen_dest_name} for ${travel_details['cost']} and {travel_details['time_hours']} hours. Confirm? (y/n)"
                                        confirm_choice = input(f"{confirm_prompt} > ").lower()

                                        if confirm_choice == 'y':
                                            if player.money >= travel_details['cost']:
                                                player.money -= travel_details['cost']
                                                destination_location_obj = WORLD_MAP.get(chosen_dest_name)

                                                if destination_location_obj:
                                                    # player.travel already handles setting new current_location and arrival POI
                                                    player.travel(destination_location_obj, travel_details['time_hours'])
                                                    advance_game_time(minutes=travel_details['time_hours']*60)
                                                    update_npc_locations(current_game_time)
                                                    print(f"Ticket purchased. Paid ${travel_details['cost']}. You are now heading to {chosen_dest_name}.")
                                                    # Break from POI interaction loop as player has moved.
                                                    # The main game loop will then pick up at the new location.
                                                    # We need a way to signal the main loop to effectively 'refresh' or skip to next turn.
                                                    # For now, the next iteration of the main loop will show the new city.
                                                else:
                                                    print(f"Error: Destination city '{chosen_dest_name}' not found in world map. Ticket not booked.")
                                                    player.money += travel_details['cost'] # Refund
                                            else:
                                                print(f"Not enough money for this ticket. Need ${travel_details['cost']}.")
                                        else:
                                            print("Travel cancelled.")
                        # --- END INTER-CITY TRAVEL BOOKING LOGIC ---

                        # --- REST/SLEEP LOGIC ---
                        elif player.current_poi.category == "HOME" and chosen_interaction_text == "Rest (8 hours)":
                            hours_to_rest = 8

                            # Comfort effect on rest quality
                            comfort_effect_on_rest = 0.0
                            if player.comfort < 25: comfort_effect_on_rest = -0.2
                            elif player.comfort < 50: comfort_effect_on_rest = -0.1
                            effective_rest_quality = max(0.1, player.current_poi.rest_quality + comfort_effect_on_rest)

                            energy_gained = int(hours_to_rest * 10 * effective_rest_quality)
                            stress_change = int(hours_to_rest * player.current_poi.stress_modifier_hourly)

                            # Resting at home also greatly reduces homesickness and boosts comfort directly
                            player.homesickness = max(0, player.homesickness - (hours_to_rest * 10)) # Strong reduction
                            player.comfort = min(100, player.comfort + (hours_to_rest * 2)) # Boost comfort too

                            player.energy = min(100, player.energy + energy_gained)
                            player.stress = max(0, player.stress + stress_change)

                            advance_game_time(minutes=hours_to_rest * 60)
                            update_npc_locations(current_game_time)
                            print(f"You rest for {hours_to_rest} hours at {player.current_poi.name}.")
                            print(f"Energy restored to {player.energy}/100. Stress changed to {player.stress}/100.")

                        elif player.current_poi.category == "ACCOMMODATION_CHEAP" and chosen_interaction_text.startswith("Rent Room"):
                            # Example: "Rent Room ($50/night)"
                            try:
                                cost_str = chosen_interaction_text.split('$')[1].split('/')[0]
                                rent_cost = int(cost_str)
                                if player.money >= rent_cost:
                                    player.money -= rent_cost
                                    # Simple rental: lasts until next morning (e.g. 6 AM) or for 1 sleep.
                                    # For now, let's make it allow one sleep.
                                    # A more robust way: store checkout time.
                                    from game.game_time import GameTime # For creating new GameTime obj for checkout
                                    checkout_time = GameTime(year=current_game_time.year, month=current_game_time.month, day=current_game_time.day, hour=current_game_time.hour, minute=current_game_time.minute)
                                    checkout_time.advance_time(minutes=24*60) # Valid for 24 hours from now (simplification)

                                    player.rented_accommodation_info = {
                                        "poi_id": player.current_poi.poi_id,
                                        "checkout_time_obj": checkout_time
                                    }
                                    print(f"You rented a room at {player.current_poi.name} for ${rent_cost}. It's yours until {checkout_time}.")
                                    print(f"Remaining money: ${player.money}")
                                else:
                                    print(f"Not enough money to rent a room. Need ${rent_cost}.")
                            except (IndexError, ValueError):
                                print("Error parsing rent cost from interaction text.")

                        elif player.current_poi.category == "ACCOMMODATION_CHEAP" and chosen_interaction_text.startswith("Sleep"):
                            can_sleep = False
                            if player.rented_accommodation_info and \
                               player.rented_accommodation_info["poi_id"] == player.current_poi.poi_id:
                                # Simple check: if current time is before checkout time.
                                # This needs GameTime comparison logic if we get more complex.
                                # For now, just assume if they have info, they can sleep once.
                                can_sleep = True

                            if can_sleep:
                                hours_to_sleep = 8

                                # Comfort effect on rest quality
                                comfort_effect_on_rest = 0.0
                                if player.comfort < 25: comfort_effect_on_rest = -0.2
                                elif player.comfort < 50: comfort_effect_on_rest = -0.1
                                effective_rest_quality = max(0.1, player.current_poi.rest_quality + comfort_effect_on_rest)

                                energy_gained = int(hours_to_sleep * 10 * effective_rest_quality)
                                stress_change = int(hours_to_sleep * player.current_poi.stress_modifier_hourly)

                                player.energy = min(100, player.energy + energy_gained)
                                player.stress = max(0, player.stress + stress_change)

                                advance_game_time(minutes=hours_to_sleep * 60)
                                update_npc_locations(current_game_time)
                                print(f"You sleep for {hours_to_sleep} hours at {player.current_poi.name}.")
                                print(f"Energy restored to {player.energy}/100. Stress changed to {player.stress}/100.")
                                player.rented_accommodation_info = None # Slept, rental used up for this simple model
                            else:
                                print(f"You haven't rented a room here, or your rental has expired.")
                        # --- END REST/SLEEP LOGIC ---

                        # --- ORDER MERCHANDISE STOCK LOGIC ---
                        elif player.current_poi.category == "HOME" and chosen_interaction_text == "Order Merchandise Stock":
                            print("\n--- Order Merchandise Stock ---")
                            available_merch_to_order = {
                                item_id: item for item_id, item in GEAR_CATALOG.items()
                                if item.gear_type == "MERCHANDISE"
                            }
                            if not available_merch_to_order:
                                print("No merchandise designs are currently available to order.")
                            else:
                                merch_display_list = []
                                merch_map = {} # Maps display index to item_id
                                for i, (item_id, item) in enumerate(available_merch_to_order.items()):
                                    merch_display_list.append(f"{item.name} (Cost: ${item.cost}/unit, Size: {item.size}/unit)")
                                    merch_map[str(i+1)] = item_id

                                merch_choice_key = present_choices(merch_display_list, "Which merchandise to order? (0 to cancel)")
                                if merch_choice_key and merch_choice_key != "0" and merch_choice_key in merch_map:
                                    chosen_item_id = merch_map[merch_choice_key]
                                    chosen_merch_item_template = available_merch_to_order[chosen_item_id]

                                    try:
                                        quantity_str = input(f"How many units of '{chosen_merch_item_template.name}' to order? (e.g., 10, 25, 50) > ")
                                        quantity = int(quantity_str)
                                        if quantity <= 0:
                                            print("Order quantity must be positive.")
                                        else:
                                            total_cost = quantity * chosen_merch_item_template.cost
                                            total_size = quantity * chosen_merch_item_template.size # Assuming size is per unit

                                            print(f"Ordering {quantity} x '{chosen_merch_item_template.name}' will cost ${total_cost} and require {total_size} capacity.")

                                            if player.money >= total_cost:
                                                # Check capacity for adding all these items
                                                # Player.can_carry_gear currently checks for one item.
                                                # We need a check for total additional load.
                                                if (player.get_current_gear_load() + total_size) <= player.get_current_gear_capacity():
                                                    confirm_order = input("Confirm order? (y/n) > ").lower()
                                                    if confirm_order == 'y':
                                                        player.money -= total_cost
                                                        for _ in range(quantity):
                                                            # Create new instances for each unit if not stackable by design
                                                            # For now, GearItem is not stackable, so add multiple instances
                                                            # This means item_id in inventory might not be unique
                                                            player.add_gear(GearItem( # Create new instance from template
                                                                item_id=chosen_merch_item_template.item_id, # Could make this unique per instance later
                                                                name=chosen_merch_item_template.name,
                                                                description=chosen_merch_item_template.description,
                                                                gear_type=chosen_merch_item_template.gear_type,
                                                                size=chosen_merch_item_template.size,
                                                                cost=chosen_merch_item_template.cost, # Store its original buy cost
                                                                base_sell_price=chosen_merch_item_template.base_sell_price,
                                                                properties=chosen_merch_item_template.properties.copy()
                                                            ))
                                                        print(f"Successfully ordered {quantity} of {chosen_merch_item_template.name}.")
                                                        print(f"Money remaining: ${player.money}. Current gear load: {player.get_current_gear_load()}/{player.get_current_gear_capacity()}")
                                                        advance_game_time(minutes=60) # Ordering takes some time (e.g., online, phone call)
                                                        update_npc_locations(current_game_time)
                                                    else:
                                                        print("Order cancelled.")
                                                else:
                                                    print(f"Not enough inventory capacity for {quantity} units. Need {total_size}, have {player.get_current_gear_capacity() - player.get_current_gear_load()} available.")
                                            else:
                                                print(f"Not enough money. Need ${total_cost}, have ${player.money}.")
                                    except ValueError:
                                        print("Invalid quantity entered.")
                        # --- END ORDER MERCHANDISE STOCK LOGIC ---

                        # --- WRITE SONG LOGIC ---
                        elif player.current_poi.category == "HOME" and chosen_interaction_text == "Write a new song":
                            print("\n--- Write a New Song ---")
                            try:
                                hours_str = input("How many hours to dedicate to songwriting (e.g., 2, 4, 8)? > ")
                                hours_spent = int(hours_str)
                                if hours_spent <= 0:
                                    print("Songwriting time must be positive.")
                                else:
                                    song_title = input("Enter a title for your new song: > ").strip()
                                    if not song_title:
                                        song_title = f"Untitled Ballad #{len(player.songs_written) + 1}"
                                        print(f"No title entered, defaulting to '{song_title}'.")

                                    # Genre selection
                                    genres = ["Rock", "Pop", "Blues", "Folk", "Indie", "Electronic"]
                                    genre_choice_key = present_choices(genres, "Choose a genre for your song:")
                                    if genre_choice_key:
                                        chosen_genre = genres[int(genre_choice_key) -1]

                                        # Song Quality Calculation (Basic)
                                        songwriting_skill = player.skills.get("songwriting", 0)
                                        base_quality = (songwriting_skill / 20.0) # Max skill 20 for base 1.0
                                        time_factor = min(0.5, (hours_spent / 8.0) * 0.5) # Max 0.5 bonus for 8+ hours
                                        random_inspiration = random.uniform(-0.15, 0.15) # Increased inspiration range slightly

                                        final_song_quality = min(1.0, max(0.05, base_quality + time_factor + random_inspiration)) # Ensure min quality of 0.05

                                        # For now, complexity is just random small values, can be tied to skill/genre later
                                        lyrics_c = round(random.uniform(0.1, 0.3) + (songwriting_skill / 50.0), 2)
                                        music_c = round(random.uniform(0.1, 0.3) + (player.skills.get("guitar",0)/40.0 + player.skills.get("piano",0)/40.0), 2) # Example using instrument skills

                                        new_song = Song(
                                            title=song_title,
                                            author=player.name,
                                            genre=chosen_genre,
                                            song_quality=final_song_quality,
                                            lyrics_complexity=lyrics_c,
                                            music_complexity=music_c
                                        )
                                        player.songs_written.append(new_song)

                                        advance_game_time(minutes=hours_spent * 60)
                                        update_npc_locations(current_game_time)
                                        # Songwriting also affects energy/stress
                                        player.energy = max(0, player.energy - (hours_spent * 5)) # -5 energy per hour
                                        player.stress = min(100, player.stress + (hours_spent * 2)) # +2 stress per hour

                                        print(f"\nYou spent {hours_spent} hours writing '{new_song.title}' [{new_song.genre}].")
                                        print(f"It feels like it has a compositional quality of {new_song.song_quality:.2f}/1.0.")
                                        print(f"Energy: {player.energy}/100, Stress: {player.stress}/100")
                                    else:
                                        print("Songwriting cancelled (no genre selected).")
                            except ValueError:
                                print("Invalid number of hours entered.")
                        # --- END WRITE SONG LOGIC ---

                        # --- BOOK RECORDING SESSION LOGIC ---
                        elif player.current_poi.category == "STUDIO_RECORDING" and chosen_interaction_text == "Book recording session":
                            print(f"\n--- Book Recording Session at {player.current_poi.name} ---")
                            studio = player.current_poi
                            print(f"Studio Quality: {studio.studio_quality:.2f}/1.0, Hourly Rate: ${studio.hourly_rate}")

                            if not player.songs_written:
                                print("You have no original songs written to record!")
                            else:
                                unrecorded_songs = [song for song in player.songs_written if not song.is_recorded]
                                if not unrecorded_songs:
                                    print("All your current songs have already been recorded.")
                                else:
                                    print("Which song would you like to record?")
                                    song_display_list = [f"{song.title} (Quality: {song.song_quality:.2f})" for song in unrecorded_songs]
                                    song_choice_key = present_choices(song_display_list, "Choose a song: (0 to cancel)")

                                    if song_choice_key and song_choice_key != "0":
                                        song_to_record = unrecorded_songs[int(song_choice_key) - 1]

                                        try:
                                            hours_str = input(f"How many hours to book for '{song_to_record.title}' (e.g., 2, 4, 8)? > ")
                                            hours_booked = int(hours_str)
                                            if hours_booked <= 0:
                                                print("Booking time must be positive.")
                                            else:
                                                total_booking_cost = hours_booked * studio.hourly_rate
                                                print(f"Booking {hours_booked} hours will cost ${total_booking_cost}.")
                                                if player.money >= total_booking_cost:
                                                    confirm_booking = input("Confirm booking? (y/n) > ").lower()
                                                    if confirm_booking == 'y':
                                                        player.money -= total_booking_cost

                                                        # Recording Quality Calculation
                                                        base_rq = song_to_record.song_quality * 0.5
                                                        # Assuming primary skill for recording is the highest instrument skill or vocals if higher
                                                        # This is a simplification. A better system would know song instrumentation.
                                                        primary_perf_skill = max(player.skills.get("guitar",0), player.skills.get("vocals",0), player.skills.get("drums",0), player.skills.get("bass",0), player.skills.get("piano",0), 0)
                                                        skill_factor = (primary_perf_skill / 20.0) * 0.25 # Max 0.25 from performance skill
                                                        studio_factor = studio.studio_quality * 0.3 # Max 0.3 from studio
                                                        time_factor = min(0.20, (hours_booked / 8.0) * 0.20) # Max 0.2 for 8+ hours
                                                        energy_factor = -0.15 if player.energy < 30 else (0.05 if player.energy > 80 else 0)
                                                        stress_factor = -0.15 if player.stress > 70 else (0.05 if player.stress < 20 else 0)
                                                        random_element = random.uniform(-0.05, 0.05)

                                                        final_recording_quality = min(1.0, max(0.05, base_rq + skill_factor + studio_factor + time_factor + energy_factor + stress_factor + random_element))

                                                        song_to_record.mark_as_recorded(final_recording_quality)

                                                        advance_game_time(minutes=hours_booked * 60)
                                                        update_npc_locations(current_game_time)

                                                        player.energy = max(0, player.energy - (hours_booked * 7)) # Recording is tiring
                                                        player.stress = min(100, player.stress + (hours_booked * 4)) # And stressful

                                                        print(f"\nPaid ${total_booking_cost}. You spent {hours_booked} hours recording '{song_to_record.title}'.")
                                                        print(f"Achieved recording quality: {song_to_record.recording_quality:.2f}/1.0.")
                                                        print(f"Energy: {player.energy}/100, Stress: {player.stress}/100. Money: ${player.money}")
                                                    else:
                                                        print("Booking cancelled.")
                                                else:
                                                    print(f"Not enough money. Need ${total_booking_cost}, have ${player.money}.")
                                        except ValueError:
                                            print("Invalid number of hours.")
                        # --- END BOOK RECORDING SESSION LOGIC ---

                        # --- SUBMIT DEMO TO RECORD LABEL LOGIC ---
                        elif player.current_poi.category == "OFFICE_RECORD_LABEL" and chosen_interaction_text.startswith("Submit Demo"):
                            label_poi = player.current_poi
                            print(f"\n--- Submit Demo to {label_poi.name} ---")

                            if player.fame < label_poi.min_fame_to_submit:
                                print(f"Your fame ({player.fame}) is too low. {label_poi.name} requires at least {label_poi.min_fame_to_submit} fame to consider demos.")
                            else:
                                recorded_songs = [song for song in player.songs_written if song.is_recorded]
                                if not recorded_songs:
                                    print("You have no recorded demos to submit. Go record some tracks!")
                                else:
                                    print("Which recorded song would you like to submit as a demo?")
                                    song_display_list = [f"'{song.title}' (Genre: {song.genre}, RecQ: {song.recording_quality:.2f})" for song in recorded_songs]
                                    song_choice_key = present_choices(song_display_list, "Choose a demo: (0 to cancel)")

                                    if song_choice_key and song_choice_key != "0":
                                        chosen_song_to_submit = recorded_songs[int(song_choice_key) - 1]

                                        # Basic submission outcome
                                        print(f"\nYou hand over a copy of '{chosen_song_to_submit.title}' to the A&R rep at {label_poi.name}.")
                                        print("They nod, saying, 'Thanks, we'll give it a listen. Don't call us, we'll call you... maybe.'")

                                        # Conceptual: Mark song as submitted to this label to prevent re-submission?
                                        # chosen_song_to_submit.submitted_to_labels.append(label_poi.poi_id) # Needs new Song attribute

                                        # Add memory to a relevant NPC if one is defined for this label and present
                                        # For now, this is just a conceptual step.
                                        # Example: if label_poi.owner_npc_id and label_poi.owner_npc_id in NPC_REGISTRY:
                                        #     label_npc = NPC_REGISTRY[label_poi.owner_npc_id]
                                        #     if label_npc.current_location == label_poi: # Check if NPC is actually there
                                        #         label_npc.add_memory(f"Player {player.name} submitted a demo: '{chosen_song_to_submit.title}'.")

                                        advance_game_time(minutes=120) # 2 hours for the meeting/submission
                                        player.energy = max(0, player.energy - 5)
                                        player.stress = min(100, player.stress + 5) # A bit stressful
                                        update_npc_locations(current_game_time)
                                        print(f"The meeting took a couple of hours. (Energy: {player.energy}, Stress: {player.stress})")
                                    else:
                                        print("Demo submission cancelled.")
                        # --- END SUBMIT DEMO LOGIC ---

                        # --- RELAX AT HOME LOGIC ---
                        elif player.current_poi.category == "HOME" and chosen_interaction_text == "Relax at home (2 hours)":
                            hours_relaxed = 2
                            # Relaxing primarily affects homesickness, comfort, and stress. Minor energy impact.
                            homesickness_reduction = 30
                            comfort_increase = 15
                            stress_reduction = 10
                            energy_cost = 5 # Small energy cost or slight gain if very relaxed

                            player.homesickness = max(0, player.homesickness - homesickness_reduction)
                            player.comfort = min(100, player.comfort + comfort_increase)
                            player.stress = max(0, player.stress - stress_reduction)
                            player.energy = max(0, player.energy - energy_cost) # Small cost

                            advance_game_time(minutes=hours_relaxed * 60)
                            # process_time_based_player_needs is called after time advance by main loop,
                            # which will apply home's hourly comfort/homesickness benefits on top.
                            # No need to call it explicitly here if the main loop handles it post-action.
                            # However, the specific action effects are immediate.
                            update_npc_locations(current_game_time)
                            # We will call process_time_based_player_needs after this block if time advanced.

                            print(f"You spend {hours_relaxed} hours relaxing at home.")
                            print(f"Comfort: {player.comfort}/100, Homesickness: {player.homesickness}/100, Stress: {player.stress}/100, Energy: {player.energy}/100.")
                        # --- END RELAX AT HOME LOGIC ---
                        else:
                             print(f"(Action '{chosen_interaction_text}' not fully implemented yet.)")

                else: # No interaction options defined for the POI or player cancelled choosing an interaction
                    print("There's not much to do here specifically.")
            else: # Exploring general city location if no specific POI
                print(f"Description: {player.current_location.description}")
                if player.current_location.venues:
                    print("\nVenues in this city:")
                    for i, venue_obj in enumerate(player.current_location.venues): # Renamed venue to venue_obj
                        print(f"  {i+1}. {venue_obj.name} ({venue_obj.venue_type}) - {venue_obj.description}")
                if player.current_location.points_of_interest: # This will list ALL POIs, including player_home etc.
                    print("\nOther Points of Interest in this city:")
                    for i, poi_obj in enumerate(player.current_location.points_of_interest): # Renamed poi to poi_obj
                        print(f"  {i+1}. {poi_obj.name} ({poi_obj.category}) - {poi_obj.description}")

            advance_game_time(minutes=30) # Exploring takes some time (reduced from 60)
            update_npc_locations(current_game_time)
            print("--------------------")

        elif choice == "5": # Check available gigs (was 4)
            print(f"\n--- Gigs available in {player.current_location.name} ---") # Title updated
            all_gigs_at_location = player.current_location.get_all_events_at_location() # Use current_location
            active_gigs = [event for event in all_gigs_at_location if event.is_active]

            if not active_gigs:
                print("No gigs available here at the moment.")
            else:
                for i, event in enumerate(active_gigs):
                    venue_display_name = player.location.name # Default for location-wide events
                    if hasattr(event.location, 'venue_type'): # If event.location is a Venue object
                        venue_display_name = event.location.name

                    print(f"\n{i+1}. {event.name} ({event.event_type}) at {venue_display_name}")
                    print(f"   Description: {event.description}")
                    print(f"   Requires: {event.required_skills}")
                    print(f"   Fame Reward: {event.fame_reward}, Payout: ${event.payout}")
                    if event.preparation_tasks_required:
                        pending_tasks = [task for task, completed in event.preparation_tasks_required.items() if not completed]
                        if pending_tasks:
                            print(f"   Preparation Needed: {', '.join(pending_tasks)}")
                        else:
                            print("   Preparation: Complete!")
                    else:
                        print("   Preparation: Not Required.")
            print("--------------------")

        elif choice == "6": # Prepare for a gig (was 5)
            print(f"\n--- Prepare for a Gig ---")
            all_gigs_at_location = player.current_location.get_all_events_at_location()
            preparable_gigs = [e for e in all_gigs_at_location if e.is_active and e.preparation_tasks_required and not e.are_preparations_complete()]
            if not preparable_gigs:
                print("No gigs available here that require further preparation or all preparations are done.")
            else:
                gig_options_list = []
                gig_map = {} # Map choice number to event object
                for i, event in enumerate(preparable_gigs):
                    venue_name = event.location.name if hasattr(event.location, 'venue_type') else "Unknown"
                    option_text = f"{event.name} (at {venue_name})"
                    pending_tasks_display = [task for task, completed in event.preparation_tasks_required.items() if not completed]
                    option_text += f" - Pending: {', '.join(pending_tasks_display)}"
                    gig_options_list.append(option_text)
                    gig_map[str(i+1)] = event

                gig_choice_key = present_choices(gig_options_list, "Prepare for which gig?")

                if gig_choice_key and gig_choice_key in gig_map:
                    chosen_event = gig_map[gig_choice_key]

                    pending_tasks_for_event_list = []
                    task_map = {} # Map choice num to task name
                    for i, (task_name, completed) in enumerate(chosen_event.preparation_tasks_required.items()):
                        if not completed:
                            pending_tasks_for_event_list.append(task_name)
                            task_map[str(len(pending_tasks_for_event_list))] = task_name # Use len for 1-based index

                    if not pending_tasks_for_event_list:
                        print(f"All preparations for {chosen_event.name} are already complete.")
                    else:
                        task_choice_key = present_choices(pending_tasks_for_event_list, f"Which task for {chosen_event.name}?")
                        if task_choice_key and task_choice_key in task_map:
                            task_to_complete = task_map[task_choice_key]
                            print(f"Completing task: {task_to_complete}...")
                            chosen_event.complete_preparation_task(task_to_complete)
                            advance_game_time(minutes=120) # Generic time for a prep task (2 hours)
                            update_npc_locations(current_game_time) # Update NPC locations
            print("--------------------")


        elif choice == "7": # Attempt a gig (was 6)
            print(f"\n--- Attempt a Gig ---")
            all_gigs_at_location = player.location.get_all_events_at_location()
            performable_gigs = [
                e for e in all_gigs_at_location
                if e.is_active and (not e.preparation_tasks_required or e.are_preparations_complete())
            ]
            if not performable_gigs:
                print("No gigs ready to perform at your current location. Some may require preparation or be at different venues.")
            else:
                gig_options_list = []
                gig_map = {} # Map choice number to event object
                for i, event in enumerate(performable_gigs):
                    venue_name = event.location.name if hasattr(event.location, 'venue_type') else "Unknown"
                    prepared_status = "Yes" if not event.preparation_tasks_required or event.are_preparations_complete() else "No"
                    option_text = f"{event.name} (at {venue_name}, Prepared: {prepared_status})"
                    gig_options_list.append(option_text)
                    gig_map[str(i+1)] = event

                gig_choice_key = present_choices(gig_options_list, "Attempt which gig?")

                if gig_choice_key and gig_choice_key in gig_map:
                    chosen_event = gig_map[gig_choice_key]
                    can_perform, message = chosen_event.can_perform(player)
                        if not can_perform:
                            print(f"Cannot perform {chosen_event.name}: {message}")
                            advance_game_time(minutes=60) # 1 hour
                            update_npc_locations(current_game_time)
                        elif chosen_event.perform_event(player):
                            advance_game_time(minutes=180) # 3 hours
                            update_npc_locations(current_game_time)
                            player.check_for_manager_unlock()

                            post_gig_event_triggered = check_for_post_gig_random_event(player, chosen_event.event_type)
                            if post_gig_event_triggered:
                                player.check_for_manager_unlock() # Manager check again if fame changed

                            # Relationship/Memory update with Venue Owner
                            venue_owner_npc_id = getattr(chosen_event.location, 'owner_npc_id', None)
                            if venue_owner_npc_id and venue_owner_npc_id in NPC_REGISTRY:
                                owner_npc = NPC_REGISTRY[venue_owner_npc_id]
                                owner_npc.update_relationship(15) # Successful gig is positive
                                owner_npc.add_memory(f"Player {player.name} had a successful gig ('{chosen_event.name}') at my venue.")
                                print(f"Your relationship with {owner_npc.name} improved.")

                            if not chosen_event.is_active:
                                if hasattr(chosen_event.location, 'remove_event'):
                                    chosen_event.location.remove_event(chosen_event)
                                elif chosen_event in player.location.events_available:
                                    player.location.remove_location_event(chosen_event)
                        else: # Failed performance
                            advance_game_time(minutes=60) # 1 hour
                            update_npc_locations(current_game_time)
                            # Relationship/Memory update with Venue Owner for failure
                            venue_owner_npc_id = getattr(chosen_event.location, 'owner_npc_id', None)
                            if venue_owner_npc_id and venue_owner_npc_id in NPC_REGISTRY:
                                owner_npc = NPC_REGISTRY[venue_owner_npc_id]
                                owner_npc.update_relationship(-10) # Failed gig is negative
                                owner_npc.add_memory(f"Player {player.name} failed their gig ('{chosen_event.name}') at my venue.")
                                print(f"Your relationship with {owner_npc.name} worsened due to the poor performance.")
                    else:
                        print("Invalid gig choice.")
                except ValueError:
                    print("Invalid input.")
            print("--------------------")

        elif choice == "8": # View player stats (was 7)
            print("\n--- Player Stats ---")
            print(player)
            print(get_current_time_str())
            print("--------------------")

        elif choice == "9": # Talk to someone (was 8)
            print("--- Talk to Someone ---")
            # Logic needs to find NPCs at player.current_poi or in player.current_location (if no POI)
            # For simplicity, let's find NPCs whose current_location is either the player's current_poi
            # or if player.current_poi is None, then whose current_location is player.current_location (the city).
            # Or, more accurately, NPCs whose current_location (which can be a POI/Venue) is *within* player.current_location (city).

            npcs_to_list = []
            target_area_name = player.current_poi.name if player.current_poi else player.current_location.name

            for npc_instance in NPC_REGISTRY.values():
                npc_is_at_player_poi = player.current_poi and npc_instance.current_location == player.current_poi

                # Check if NPC is at a POI/Venue that is within the player's current city.
                # And if player is at a general city level (no POI), then NPC must also be at that general city level OR at a POI/Venue in that city.
                # This logic ensures we list NPCs in the same "space" as the player.

                npc_general_location = None
                if hasattr(npc_instance.current_location, 'parent_location_id'): # if NPC is at a POI/Venue with a parent city
                    npc_general_location = WORLD_MAP.get(npc_instance.current_location.parent_location_id)
                elif isinstance(npc_instance.current_location, Location): # if NPC is at a general city location
                    npc_general_location = npc_instance.current_location

                if npc_is_at_player_poi:
                    npcs_to_list.append(npc_instance)
                # If player is at a general city level (current_poi is None)
                # OR if the NPC is at another POI/Venue within the same city as the player.
                elif (not player.current_poi and npc_general_location == player.current_location) or \
                     (player.current_poi and npc_general_location == player.current_location and npc_instance.current_location != player.current_poi) :
                     # The above line means: if player is at a POI, list other NPCs in the same city but not at the *exact* same POI,
                     # under the assumption "Talk to someone" might mean shout across the street or find someone nearby.
                     # This might be too broad. Let's simplify: only list NPCs at the player's *exact* POI.
                     # If player.current_poi is None, then list NPCs whose current_location is player.current_location (the city itself).
                     pass # Let's refine this.

            # Refined logic for listing NPCs:
            # List NPCs if their current_location (which can be a POI/Venue object)
            # is the same as player.current_poi OR
            # if player.current_poi is None, list NPCs whose current_location is player.current_location (the city)
            # OR NPCs whose current_location (a POI/Venue) has player.current_location as its parent.
            npcs_at_player_exact_poi = []
            npcs_at_player_city_general = []

            for npc in NPC_REGISTRY.values():
                if player.current_poi and npc.current_location == player.current_poi:
                    npcs_at_player_exact_poi.append(npc)
                elif not player.current_poi and npc.current_location == player.current_location: # Player at city level, NPC at city level
                     npcs_at_player_city_general.append(npc)
                # What if player is at city level, and NPC is at a POI in that city?
                # Or player is at POI X, and NPC is at POI Y (in same city)?
                # The "Talk to" menu should primarily list NPCs immediately available.
                # The previous logic was:
                # if npc.current_location == player.location: npcs_at_location.append(npc)
                # elif hasattr(npc.current_location, 'name') and hasattr(player.location, 'venues') and npc.current_location in player.location.venues: npcs_at_location.append(npc)
                # elif hasattr(npc.current_location, 'name') and hasattr(player.location, 'points_of_interest') and npc.current_location in player.location.points_of_interest: npcs_at_location.append(npc)
                # This needs to be adapted for player.current_poi.

            # Simpler approach: list NPCs at the player's current_poi.
            # If player.current_poi is None, it means they are at the general city level.
            # At general city level, who can they talk to? Perhaps no one specific, or only NPCs also at "general city level".
            # This makes "Explore POI/Area" more important to find where NPCs are.

            npcs_available_to_talk = []
            if player.current_poi:
                for npc in NPC_REGISTRY.values():
                    if npc.current_location == player.current_poi:
                        npcs_available_to_talk.append(npc)
            else: # Player is at general city level, not a specific POI
                # Only list NPCs also at general city level (e.g. Sarah Fan in Hometown if she's not at a specific POI)
                 for npc in NPC_REGISTRY.values():
                    if npc.current_location == player.current_location: # Both at general city level
                        npcs_available_to_talk.append(npc)

            if not npcs_available_to_talk:
                print(f"There's no one specific to talk to at {target_area_name} right now.")
                # Fallback to generic fan if desired
                if not player.current_poi : # Only offer generic fan at general city level for now
                    print("A passerby notices you, though...")
                    temp_fan_npc = NPC(npc_id="temp_event_fan", name="Passerby Fan", personality_key="friendly_fan")
                    initial_fan_message = "Hey, aren't you that musician, {player_name}?"
                    print(f"{temp_fan_npc.name}: \"{initial_fan_message.format(player_name=player.name)}\"")
                    talk_to_npc_instance(player, temp_fan_npc)
            else:
                npc_options_list = [f"{npc.name}" for npc in npcs_available_to_talk] # Simpler display now
                npc_map = {str(i+1): npc for i, npc in enumerate(npcs_available_to_talk)}

                chosen_npc_key = present_choices(npc_options_list, f"Who would you like to talk to at {target_area_name}?")
                if chosen_npc_key and chosen_npc_key in npc_map:
                    talk_to_npc_instance(player, npc_map[chosen_npc_key])

        elif choice == "00": # Debug: Advance time by 1 hour (was 9, then 8)
            advance_game_time(minutes=60) # 1 hour
            update_npc_locations(current_game_time) # Explicitly call after debug time advance

        elif choice == "0":
            print("Thanks for playing!")
            break
        else:
            print("Invalid choice. Please try again.")

        print(f"\n--- {get_current_time_str()} ---")

        # Check for random events after most actions or time advances
        # practice (1), travel city(2), travel POI(3), explore(4), prepare(6), perform(7), advance time (00)
        # Note: some actions (like POI interactions for rest/sleep, songwriting) already call advance_game_time
        # and will have process_time_based_player_needs called after them if they pass time.
        # This global check is for general random events.

        # We need to capture the minutes passed by the *last action* to feed into process_time_based_player_needs
        # This is tricky as minutes_passed is not consistently stored across all branches.
        # For now, process_time_based_player_needs is called *within* each block that calls advance_game_time.
        # This means the general random event check does not need to call it again.

        if choice in ["1", "2", "3", "4", "6", "7", "00"]: # Check which choices can trigger random world events
            if not ("LLM Error" in locals().get('npc_response', '') or "An unexpected error occurred" in locals().get('npc_response', '')):
                # Random events themselves don't usually pass large chunks of time that would trigger needs updates by default.
                # If a random event *does* pass significant time, it should handle its own needs update.
                event_triggered = check_for_random_event(player, chance=0.3)
                if event_triggered:
                    player.check_for_manager_unlock() # Fame might change from event


if __name__ == "__main__":
    main()
            # Check NPCs whose current_location is the player's general location,
            # or a venue/POI within that general location.
            for npc in NPC_REGISTRY.values():
                if npc.current_location == player.location:
                    npcs_at_location.append(npc)
                elif hasattr(npc.current_location, 'name') and hasattr(player.location, 'venues') and npc.current_location in player.location.venues:
                    npcs_at_location.append(npc)
                elif hasattr(npc.current_location, 'name') and hasattr(player.location, 'points_of_interest') and npc.current_location in player.location.points_of_interest:
                    npcs_at_location.append(npc)

            if not npcs_at_location:
                print("There's no one specific around to talk to right now.")
                # Fallback to generic fan if desired, or just do nothing.
                # For now, let's add a generic fan interaction if no specific NPCs.
                # This uses the old random event style temporary NPC.
                print("A passerby notices you, though...")
                temp_fan_npc = NPC(npc_id="temp_event_fan", name="Passerby Fan", personality_key="friendly_fan")
                # Manually trigger a small interaction
                initial_fan_message = "Hey, aren't you that musician, {player_name}?"
                print(f"{temp_fan_npc.name}: \"{initial_fan_message.format(player_name=player.name)}\"")
                talk_to_npc_instance(player, temp_fan_npc)

            else:
                npc_options_list = [f"{npc.name} (at {npc.current_location.name if hasattr(npc.current_location, 'name') else 'Unknown place'})" for npc in npcs_at_location]
                npc_map = {str(i+1): npc for i, npc in enumerate(npcs_at_location)}

                chosen_npc_key = present_choices(npc_options_list, "Who would you like to talk to?")
                if chosen_npc_key and chosen_npc_key in npc_map:
                    talk_to_npc_instance(player, npc_map[chosen_npc_key])

        elif choice == "9": # Debug: Advance time by 1 hour (was 8)
            advance_game_time(minutes=60) # 1 hour
            update_npc_locations(current_game_time) # Explicitly call after debug time advance

        elif choice == "0":
            print("Thanks for playing!")
            break
        else:
            print("Invalid choice. Please try again.")

        print(f"\n--- {get_current_time_str()} ---")

        # Check for random events after most actions or time advances
        # practice (1), travel (2), explore (3), prepare (5), perform (6), advance time (9)
        if choice in ["1", "2", "3", "5", "6", "9"]:
            if not ("LLM Error" in locals().get('npc_response', '') or "An unexpected error occurred" in locals().get('npc_response', '')):
                event_triggered = check_for_random_event(player, chance=0.3)
                if event_triggered:
                    player.check_for_manager_unlock()


if __name__ == "__main__":
    main()
