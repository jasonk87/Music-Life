from game.player import Player
from game.player import Player
from game.location import Location
from game.venue import Venue
from game.poi import PointOfInterest
from game.event import Event
from game.game_time import current_game_time, advance_game_time, get_current_time_str
from game.dialogue import generate_npc_response, reset_dialogue_history, NPC_PERSONALITIES
from game.random_events import check_for_random_event, check_for_post_gig_random_event

# --- Game World Setup ---
# Global dictionary to hold all location objects, keyed by name for easy lookup
WORLD_MAP = {}

def setup_world():
    global WORLD_MAP
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
    community_hall = Venue("Community Hall", "Hosts local events.", venue_type="HALL", capacity=50, prestige=1)
    home_town.add_venue(community_hall)

    # Hometown POIs
    music_shop_home = PointOfInterest("Old Timer's Music Shop", "Sells basic gear and instruments.", poi_type="MUSIC_STORE",
                                   interaction_options=["Browse Gear", "Talk to Owner (Old Timer Joe)"])
    home_town.add_poi(music_shop_home)
    rehearsal_space_home = PointOfInterest("Garage Rehearsal Space", "A bit rough but it's cheap.", poi_type="REHEARSAL_STUDIO",
                                           interaction_options=["Book Rehearsal Time (1 hour, $10)"])
    home_town.add_poi(rehearsal_space_home)

    # City Center Venues
    rusty_mug_club = Venue("The Rusty Mug", "A well-known club for upcoming bands.", venue_type="CLUB", capacity=150, prestige=4)
    city_center.add_venue(rusty_mug_club)
    grande_theater = Venue("Grande Concert Hall", "A prestigious venue for established artists.", venue_type="CONCERT_HALL", capacity=1000, prestige=8)
    city_center.add_venue(grande_theater)

    # City Center POIs
    pro_music_store = PointOfInterest("Pro Audio Central", "High-end instruments and recording gear.", poi_type="MUSIC_STORE",
                                     interaction_options=["Browse Instruments", "Buy Pro Gear", "Talk to Sales Rep"])
    city_center.add_poi(pro_music_store)
    record_label_office = PointOfInterest("Indie Hits Records", "A small but ambitious record label.", poi_type="RECORD_LABEL",
                                           interaction_options=["Submit Demo (requires 500 fame)", "Talk to A&R Rep (requires Manager)"])
    city_center.add_poi(record_label_office)


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
def talk_to_npc(player, npc_type_key, npc_name): # Added player
    """Handles the conversation loop with an NPC."""
    print(f"\n--- Talking to {npc_name} ---")
    print(f"({NPC_PERSONALITIES[npc_type_key]['system_prompt']})") # Show personality for debugging/clarity
    print(f"Type 'bye' to end the conversation.")

    # Reset history for this specific NPC type at the start of a new conversation session
    reset_dialogue_history(npc_type_key)

    while True:
        player_input = input(f"{player.name}: ")
        if player_input.lower() == 'bye':
            print(f"{npc_name} waves goodbye.")
            advance_game_time(hours=1) # Talking takes some time
            break

        if not player_input.strip():
            print("Say something!")
            continue

        npc_response = generate_npc_response(player_input, npc_type_key)
        print(f"{npc_name}: {npc_response}")

        # Check for LLM errors that should stop the conversation
        if "LLM Error" in npc_response or "An unexpected error occurred" in npc_response:
            print("It seems there's an issue with the connection or the LLM service.")
            advance_game_time(hours=1)
            break


def main():
    setup_world() # Initialize locations, venues, POIs, events

    print("Welcome to the Text-Based Music Career Simulator!")
    print("IMPORTANT: This game uses Ollama for NPC conversations.")
    print("Please ensure Ollama is installed, running, and you have pulled the required model (e.g., `ollama pull llama3`).")

    player_name = input("Enter your character's name: ")
    player = Player(player_name)
    player.location = WORLD_MAP["Your Hometown"] # Start player at hometown from WORLD_MAP

    print(f"\n--- {get_current_time_str()} ---")
    print(player)
    print(f"Current Location: {player.location}")

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
                        elif chosen_event.perform_event(player):
                            advance_game_time(hours=3)
                            player.check_for_manager_unlock()

                            post_gig_event_triggered = check_for_post_gig_random_event(player, chosen_event.event_type)
                            if post_gig_event_triggered:
                                player.check_for_manager_unlock()

                            if not chosen_event.is_active:
                                # Remove event from its venue or location's direct list
                                if hasattr(chosen_event.location, 'remove_event'): # If it's a Venue
                                    chosen_event.location.remove_event(chosen_event)
                                elif chosen_event in player.location.events_available: # If it's a location-wide event
                                    player.location.remove_location_event(chosen_event)
                        else:
                            advance_game_time(hours=1)
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

        elif choice == "8": # Talk to NPC (was 7)
            # For now, generic NPCs. Future: list NPCs at player.location.venues or player.location.points_of_interest
            npc_options = {
                "1": "Friendly Fan (Generic)",
                "2": "Gruff Club Owner (Generic)",
                # Could dynamically add NPCs here based on location context
            }
            npc_choice_key = present_choices(npc_options, "Who would you like to talk to?")

            if npc_choice_key == "1":
                talk_to_npc(player, "friendly_fan", "Friendly Fan")
            elif npc_choice_key == "2":
                talk_to_npc(player, "gruff_club_owner", "Gruff Club Owner")
            # else: (present_choices handles invalid input message)

        elif choice == "9": # Debug: Advance time by 1 hour (was 8)
            advance_game_time(hours=1)

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
