from game.player import Player
from game.player import Player
from game.location import Location
from game.venue import Venue
from game.poi import PointOfInterest
from game.event import Event
from game.game_time import current_game_time, advance_game_time, get_current_time_str
from game.dialogue import generate_npc_response, NPC_PERSONALITIES # Removed reset_dialogue_history
from game.random_events import check_for_random_event, check_for_post_gig_random_event

# --- Game World Setup ---
from game.npc import NPC # Import NPC class

# Global dictionary to hold all location objects, keyed by name for easy lookup
WORLD_MAP = {}
# Global dictionary to hold all NPC objects, keyed by npc_id
NPC_REGISTRY = {}

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
        parent_location_id=home_town.name
    )
    home_town.add_venue(community_hall)

    # Hometown POIs
    music_shop_home = PointOfInterest(
        poi_id="hometown_music_shop_oldtimers",
        name="Old Timer's Music Shop",
        description="Sells basic gear and instruments.",
        category="SHOP_MUSIC",
        interaction_options=["Browse Gear", "Talk to Owner (Old Timer Joe)"],
        parent_location_id=home_town.name
    )
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
        parent_location_id=city_center.name
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
        parent_location_id=city_center.name
    )
    city_center.add_venue(grande_theater)

    # City Center POIs
    pro_music_store = PointOfInterest(
        poi_id="citycenter_proaudio",
        name="Pro Audio Central",
        description="High-end instruments and recording gear.",
        category="SHOP_MUSIC",
        interaction_options=["Browse Instruments", "Buy Pro Gear", "Talk to Sales Rep"],
        parent_location_id=city_center.name
    )
    city_center.add_poi(pro_music_store)
    record_label_office = PointOfInterest(
        poi_id="citycenter_indiehits_records",
        name="Indie Hits Records",
        description="A small but ambitious record label.",
        category="OFFICE_RECORD_LABEL", # More specific category
        interaction_options=["Submit Demo (requires 500 fame)", "Talk to A&R Rep (requires Manager)"],
        parent_location_id=city_center.name
    )
    city_center.add_poi(record_label_office)
    downtown_cafe = PointOfInterest(
        poi_id="citycenter_dailygrind_cafe",
        name="The Daily Grind Cafe",
        description="Popular hangout, good coffee, free Wi-Fi.",
        category="POI_CAFE", # POI prefix for generic points of interest
        interaction_options=["Grab Coffee ($5)", "People Watch", "Look for Local Flyers"],
        parent_location_id=city_center.name
    )
    city_center.add_poi(downtown_cafe)

    # --- Define New Key POIs for Intra-City Travel & Player Start ---
    # Your Hometown
    player_home = PointOfInterest(
        poi_id="hometown_player_home",
        name="Your Apartment",
        description="Your starting digs. A bit small, but it's home.",
        category="HOME",
        interaction_options=["Rest (advance 8 hours)", "Practice (at home, less effective?)"], # Example interactions
        parent_location_id=home_town.name
    )
    home_town.add_poi(player_home)

    bus_stop_hometown = PointOfInterest(
        poi_id="hometown_bus_stop",
        name="Hometown Bus Stop",
        description="A dusty bus stop for regional travel to City Center.",
        category="TRANSPORT_BUS",
        interaction_options=["Check Bus Schedule", "Buy Bus Ticket to City Center"],
        parent_location_id=home_town.name
    )
    home_town.add_poi(bus_stop_hometown)

    # City Center
    city_airport = PointOfInterest(
        poi_id="citycenter_airport",
        name="City Center International Airport",
        description="Flights to other major cities (when you can afford them).",
        category="TRANSPORT_AIRPORT",
        interaction_options=["Check Flight Departures", "Buy Plane Ticket"],
        parent_location_id=city_center.name
    )
    city_center.add_poi(city_airport)

    city_bus_station = PointOfInterest(
        poi_id="citycenter_bus_station",
        name="Main Bus Terminal (City Center)",
        description="Regional and long-haul bus services.",
        category="TRANSPORT_BUS",
        interaction_options=["Check Bus Schedule", "Buy Bus Ticket"],
        parent_location_id=city_center.name
    )
    city_center.add_poi(city_bus_station)

    crash_pad_motel = PointOfInterest(
        poi_id="citycenter_motel_cheap",
        name="Sleep EZ Motel",
        description="A cheap, somewhat clean room for the night. Better than the streets.",
        category="ACCOMMODATION_CHEAP",
        interaction_options=["Rent Room ($50/night)", "Sleep (if rented)"],
        parent_location_id=city_center.name
    )
    city_center.add_poi(crash_pad_motel)


    # Define Travel Connections (Location Name -> {cost, time})
    home_town.add_travel_connection(city_center.name, cost=20, time_hours=2)
    city_center.add_travel_connection(home_town.name, cost=20, time_hours=2)

    # Events (now primarily associated with Venues)
    open_mic_event = Event(
        name="Open Mic Night",
        event_type="OPEN_MIC",
        location=community_hall, # Assign to venue
        required_skills={"vocals": 1, "guitar": 1},
        description="A chance to show your skills at the local Community Hall."
    )
    community_hall.add_event(open_mic_event)

    first_club_gig_event = Event(
        name="Debut at 'The Rusty Mug'",
        event_type="CLUB_GIG",
        location=rusty_mug_club, # Assign to venue
        required_skills={"vocals": 5, "guitar": 5, "stage_presence": 3},
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
        "weekday_morning": music_shop_home,
        "weekday_afternoon": music_shop_home,
        "saturday_morning": music_shop_home,
        "sunday_evening": community_hall
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
        "weekday_afternoon": rusty_mug_club,
        "weekday_evening": rusty_mug_club,
        "weekend_evening": rusty_mug_club,
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
            advance_game_time(hours=1)
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
            advance_game_time(hours=1) # Still consumes some time
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


    print(f"\n--- {get_current_time_str()} ---")
    print(player) # Player's __str__ should now show POI
    # print(f"Current Location: {player.current_location.name if player.current_location else 'N/A'}") # Old way
    # print(f"Current POI: {player.current_poi.name if player.current_poi else 'N/A'}") # For direct check

    # Game Loop
    while True:
        clear_screen_ish()
        print(f"--- Current Location: {player.location.name} ---")
        print(f"--- {get_current_time_str()} ---")
        print(f"--- Player: {player.name} | Fame: {player.fame} | Money: ${player.money} ---")

        main_menu_options = {
            "1": "Practice a skill",
            "2": "Travel to another location",
            "3": "Explore current location (View Venues & POIs)",
            "4": "Check available gigs at current location",
            "5": "Prepare for a gig",
            "6": "Attempt a gig",
            "7": "View detailed player stats",
            "8": "Talk to someone",
            "9": "Advance time by 1 hour (debug)",
            "0": "Quit game"
        }
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
                advance_game_time(hours=hours_to_practice)
                update_npc_locations(current_game_time) # Update NPC locations after time passes
            except ValueError:
                print("Invalid number of hours.")

        elif choice == "2": # Travel
            print("\n--- Travel ---")
            connections = player.location.travel_connections
            if not connections:
                print("There are no travel connections from your current location.")
            else:
                dest_options_list = []
                dest_map = {} # To map simple 1,2,3 choice back to dest_name
                for i, dest_name in enumerate(connections.keys()):
                    details = connections[dest_name]
                    option_text = f"{dest_name} (Cost: ${details['cost']}, Time: {details['time_hours']} hours)"
                    dest_options_list.append(option_text)
                    dest_map[str(i+1)] = dest_name

                travel_choice_key = present_choices(dest_options_list, "Travel to which location?")

                if travel_choice_key and travel_choice_key in dest_map:
                    chosen_dest_name = dest_map[travel_choice_key]
                    travel_details = connections[chosen_dest_name]

                    if player.money >= travel_details['cost']:
                        player.money -= travel_details['cost']
                        destination_location = WORLD_MAP.get(chosen_dest_name)
                        if destination_location:
                            player.travel(destination_location, travel_details['time_hours'])
                            advance_game_time(hours=travel_details['time_hours'])
                                update_npc_locations(current_game_time) # Update NPC locations
                            print(f"Paid ${travel_details['cost']} for travel. Remaining money: ${player.money}")
                        else:
                            print(f"Error: Destination '{chosen_dest_name}' not found in world map.")
                    else:
                        print(f"Not enough money to travel to {chosen_dest_name}. Need ${travel_details['cost']}, have ${player.money}.")
            print("--------------------")

        elif choice == "3": # Explore Location
            print(f"\n--- Exploring {player.location.name} ---")
            print(f"Description: {player.location.description}")

            if player.location.venues:
                print("\nVenues:")
                for i, venue in enumerate(player.location.venues):
                    print(f"  {i+1}. {venue.name} ({venue.venue_type}) - {venue.description}")
                    # Potential future: list events at this venue here, or offer to enter venue
            else:
                print("\nNo notable venues here.")

            if player.location.points_of_interest:
                print("\nPoints of Interest:")
                for i, poi in enumerate(player.location.points_of_interest):
                    print(f"  {i+1}. {poi.name} ({poi.poi_type}) - {poi.description}")
                    if poi.interaction_options:
                        print(f"     Interact: {', '.join(poi.interaction_options)}")
                    # Potential future: allow selecting POI to interact
            else:
                print("\nNothing else of interest here.")
            advance_game_time(hours=1) # Exploring takes time
            update_npc_locations(current_game_time) # Update NPC locations
            print("--------------------")

        elif choice == "4": # Check available gigs
            print(f"\n--- Gigs at {player.location.name} ---")
            all_gigs_at_location = player.location.get_all_events_at_location()
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

        elif choice == "5": # Prepare for a gig
            print(f"\n--- Prepare for a Gig ---")
            all_gigs_at_location = player.location.get_all_events_at_location()
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
                            advance_game_time(hours=2) # Generic time for a prep task
                            update_npc_locations(current_game_time) # Update NPC locations
            print("--------------------")


        elif choice == "6": # Attempt a gig (was 5)
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
                            advance_game_time(hours=1)
                            update_npc_locations(current_game_time)
                        elif chosen_event.perform_event(player):
                            advance_game_time(hours=3)
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
                            advance_game_time(hours=1)
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

        elif choice == "7": # View player stats (was 6)
            print("\n--- Player Stats ---")
            print(player)
            print(get_current_time_str())
            print("--------------------")

        elif choice == "8": # Talk to NPC
            print("--- Talk to Someone ---")
            npcs_at_location = []
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
            advance_game_time(hours=1)
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
