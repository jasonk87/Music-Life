import random
from game.dialogue import generate_npc_response, reset_npc_dialogue_history # Updated import
from game.npc import NPC # Import the NPC class

class RandomEvent:
    def __init__(self, name, description_template, fame_threshold_min=0, fame_threshold_max=float('inf'), actions=None, npc_interaction=None):
        self.name = name
        self.description_template = description_template # Can use {player_name}
        self.fame_threshold_min = fame_threshold_min
        self.fame_threshold_max = fame_threshold_max
        self.actions = actions if actions else [] # List of functions to call or descriptions of outcomes
        self.npc_interaction = npc_interaction # Optional: dict with {"npc_type": "key", "npc_name": "Name", "initial_message": "Dialog starter"}
        self.custom_interaction_fn_name = None # Placeholder, will be set in __init__ if provided
        # Need to add custom_interaction_fn_name to __init__ signature

    # Update __init__ to accept custom_interaction_fn_name
    def __init__(self, name, description_template, fame_threshold_min=0, fame_threshold_max=float('inf'),
                 actions=None, npc_interaction=None, custom_interaction_fn_name=None): # Added custom_interaction_fn_name
        self.name = name
        self.description_template = description_template
        self.fame_threshold_min = fame_threshold_min
        self.fame_threshold_max = fame_threshold_max
        self.actions = actions if actions else []
        self.npc_interaction = npc_interaction
        self.custom_interaction_fn_name = custom_interaction_fn_name # Store it

    def trigger(self, player, current_poi_name="an unknown place"): # Added current_poi_name
        default_event_time = 15 # Default minutes passed for simple events
        event_outcome_data = {"event_triggered": True, "minutes_passed": default_event_time}

        print("\n--- Random Event! ---")
        # Description template might not always be used if custom_interaction_fn handles its own intro
        # For custom interactions, the description_template might be more of a log message or internal identifier.

        if self.custom_interaction_fn_name:
            if self.custom_interaction_fn_name == "handle_autograph_interaction":
                from game.interactions import handle_autograph_interaction # Import here

                # Create the temporary fan NPC for the interaction
                fan_npc_personality = self.npc_interaction.get("npc_type", "adoring_fan") if self.npc_interaction else "adoring_fan"
                fan_npc_name = self.npc_interaction.get("npc_name", "A Fan") if self.npc_interaction else "A Fan"
                # Event description is now printed by handle_autograph_interaction if it wants to.
                # The self.description_template is available if needed:
                # print(self.description_template.format(player_name=player.name, poi_name=current_poi_name))


                temp_fan_npc = NPC(npc_id=f"event_npc_{fan_npc_personality}", name=fan_npc_name, personality_key=fan_npc_personality)
                interaction_result = handle_autograph_interaction(player, temp_fan_npc, interaction_context=self.name)

                event_outcome_data["minutes_passed"] = interaction_result.get("minutes_passed", 1)
                # Fame/stress etc. are handled by handle_autograph_interaction directly on player object
            else:
                print(f"Warning: Unknown custom_interaction_fn_name: {self.custom_interaction_fn_name}")
                # Fallback to default description if custom function not found or fails?
                print(self.description_template.format(player_name=player.name, poi_name=current_poi_name))


        elif self.npc_interaction: # Standard NPC interaction (old style)
            print(self.description_template.format(player_name=player.name, poi_name=current_poi_name))
            npc_type = self.npc_interaction["npc_type"]
            npc_name = self.npc_interaction["npc_name"]
            initial_message = self.npc_interaction["initial_message"].format(player_name=player.name)

            print(f"\n{npc_name} approaches you!")
            temp_npc_id = f"event_npc_{npc_type}"
            temp_npc = NPC(npc_id=temp_npc_id, name=npc_name, personality_key=npc_type)
            print(f"{temp_npc.name}: \"{initial_message}\"")

            chat_turns = 0
            max_chat_turns = 2 # Limit turns for generic event
            while chat_turns < max_chat_turns:
                player_input = input(f"{player.name} (to {temp_npc.name}, type 'end' to disengage): ")
                if player_input.lower() == 'end':
                    print(f"{player.name} ends the conversation with {temp_npc.name}.")
                    break
                if not player_input.strip():
                    continue

                npc_response = generate_npc_response(player_input, temp_npc, player_name=player.name)
                print(f"{temp_npc.name}: {npc_response}")
                chat_turns += 1
                if "LLM Error" in npc_response or "An unexpected error occurred" in npc_response:
                    break

            if temp_npc.personality_key == "adoring_fan" or temp_npc.personality_key == "friendly_fan":
                print(f"{temp_npc.name} seems thrilled by the interaction!")
                player.fame += 5
                print(f"You gained 5 fame from the positive fan interaction. Current fame: {player.fame}")
            event_outcome_data["minutes_passed"] = 20 # Generic chat takes a bit longer

        else: # Simple event, no complex interaction
            print(self.description_template.format(player_name=player.name, poi_name=current_poi_name))


        # Common actions for non-custom events (or if custom event doesn't handle them)
        if not self.custom_interaction_fn_name:
            for action_desc in self.actions:
                print(action_desc)
                if "fame_boost_small" in action_desc:
                    player.fame += 10
                    print(f"Your fame increased by 10! Current fame: {player.fame}")

        print("--------------------")
        return event_outcome_data

# Define some random events
RANDOM_EVENTS = [
    RandomEvent(
        name="Fan Recognizes You (Generic Chat)",
        description_template="{player_name} is exploring {poi_name} when someone looks surprised...", # Updated template
        fame_threshold_min=20,
        fame_threshold_max=100,
        npc_interaction={ # This will use the old-style generic chat
            "npc_type": "friendly_fan",
            "npc_name": "Excited Fan",
            "initial_message": "Oh my gosh! Are you {player_name}? I love your music!"
        }
    ),
    RandomEvent( # New event using the custom autograph handler
        name="Spontaneous Autograph Request",
        description_template="While {player_name} is at {poi_name}, someone approaches looking star-struck!", # General description
        fame_threshold_min=30, # Slightly higher fame, as it's more specific
        custom_interaction_fn_name="handle_autograph_interaction",
        npc_interaction={ # Still useful for defining the fan's properties for the handler
            "npc_type": "adoring_fan",
            "npc_name": "A Star-struck Fan"
            # initial_message is not used by handle_autograph_interaction directly, it has its own flow
        }
    ),
    RandomEvent(
        name="Adoring Fan Encounter (Generic Chat)",
        description_template="A particularly enthusiastic fan spots {player_name} at {poi_name}!", # Updated template
        fame_threshold_min=50,
        npc_interaction={
            "npc_type": "adoring_fan",
            "npc_name": "Super Adoring Fan", # Made name more distinct
            "initial_message": "{player_name}! I can't believe it's really you! You're my biggest inspiration!"
        }
    ),
    RandomEvent(
        name="Local Blogger Mention",
        description_template="A local music blogger wrote a small piece mentioning {player_name}'s recent gig at {poi_name}!", # Updated template
        fame_threshold_min=30,
        fame_threshold_max=150,
        actions=["Your name is getting out there! fame_boost_small"]
    ),
    RandomEvent(
        name="Quiet Day",
        description_template="It's a quiet day for {player_name} while at {poi_name}. Nothing much happens.", # Updated template
        fame_threshold_min=0
    ),
    RandomEvent( # This will be the one used for post-gig autographs
        name="Post-Gig Autograph Opportunity",
        description_template="After a great show, a fan catches {player_name} backstage at {poi_name}!", # Updated template
        fame_threshold_min=25, # Lowered threshold a bit, as gigs imply some recognition
        custom_interaction_fn_name="handle_autograph_interaction",
        npc_interaction={
            "npc_type": "grateful_fan", # Could define a new personality, or use adoring_fan
            "npc_name": "An Appreciative Fan"
        }
    )
]

POST_GIG_EVENTS = [
    event for event in RANDOM_EVENTS if event.name == "Post-Gig Autograph Opportunity"
]
# Fallback if the specific event isn't found (e.g., due to typo in name)
if not POST_GIG_EVENTS and RANDOM_EVENTS:
    POST_GIG_EVENTS.append(RANDOM_EVENTS[-1])


def check_for_random_event(player, current_poi_name="an unknown place", chance=0.25, event_pool=None):
    """
    Checks if a random event should occur based on chance and player's fame.
    Returns a dictionary: {"event_triggered": True/False, "minutes_passed": int}
    """
    if event_pool is None:
        event_pool = RANDOM_EVENTS

    event_result = {"event_triggered": False, "minutes_passed": 0}

    if random.random() < chance:
        eligible_events = [
            event for event in event_pool
            if player.fame >= event.fame_threshold_min and player.fame <= event.fame_threshold_max
        ]
        if eligible_events:
            event_to_trigger = random.choice(eligible_events)
            # Pass current_poi_name to the trigger method
            event_result = event_to_trigger.trigger(player, current_poi_name=current_poi_name)
            event_result["event_triggered"] = True # Ensure this is set
    return event_result

def check_for_post_gig_random_event(player, performed_event_type, venue_name="the venue", chance=0.5):
    """
    Specific check for events that can happen after a gig.
    Chance might depend on the type of gig performed.
    """
    actual_chance = chance
    if performed_event_type == "CONCERT" or performed_event_type == "FESTIVAL_SLOT":
        actual_chance = 0.8
    elif performed_event_type == "CLUB_GIG":
        actual_chance = 0.6

    return check_for_random_event(player, current_poi_name=venue_name, chance=actual_chance, event_pool=POST_GIG_EVENTS)

# Need to add 'adoring_fan' & 'grateful_fan' to dialogue personalities (in game/dialogue.py)
def update_dialogue_personalities():
# The 'adoring_fan' personality is now defined directly in game/dialogue.py.
# No need for the dynamic update here anymore.
