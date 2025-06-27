import random
from game.dialogue import generate_npc_response, reset_dialogue_history

class RandomEvent:
    def __init__(self, name, description_template, fame_threshold_min=0, fame_threshold_max=float('inf'), actions=None, npc_interaction=None):
        self.name = name
        self.description_template = description_template # Can use {player_name}
        self.fame_threshold_min = fame_threshold_min
        self.fame_threshold_max = fame_threshold_max
        self.actions = actions if actions else [] # List of functions to call or descriptions of outcomes
        self.npc_interaction = npc_interaction # Optional: dict with {"npc_type": "key", "npc_name": "Name", "initial_message": "Dialog starter"}

    def trigger(self, player):
        print("\n--- Random Event! ---")
        print(self.description_template.format(player_name=player.name))

        if self.npc_interaction:
            npc_type = self.npc_interaction["npc_type"]
            npc_name = self.npc_interaction["npc_name"]
            initial_message = self.npc_interaction["initial_message"].format(player_name=player.name)

            print(f"\n{npc_name} approaches you!")
            print(f"{npc_name}: \"{initial_message}\"")

            reset_dialogue_history(npc_type) # Fresh conversation for the event

            # Get NPC's follow-up based on their initial line (simulates them starting)
            # This is a bit of a hack; ideally, the LLM would take the whole context.
            # For now, we prime it with the NPC's opening line as if it was said to the player.
            # Then player responds to that.

            # Let's assume the NPC's initial message is the first part of their dialogue.
            # The NPC's initial message is delivered. The player's next input will be the first "user" message in the LLM interaction for this event.
            while True:
                player_input = input(f"{player.name} (to {npc_name}, type 'end' to disengage): ")
                if player_input.lower() == 'end':
                    print(f"{player.name} ends the conversation with {npc_name}.")
                    break
                if not player_input.strip():
                    continue

                npc_response = generate_npc_response(player_input, npc_type)
                print(f"{npc_name}: {npc_response}")
                if "LLM Error" in npc_response or "An unexpected error occurred" in npc_response:
                    break

            # Simple outcome from fan interaction for now
            if npc_type == "adoring_fan":
                print(f"{npc_name} seems thrilled by the interaction!")
                player.fame += 5
                print(f"You gained 5 fame from the positive fan interaction. Current fame: {player.fame}")


        for action_desc in self.actions:
            # Later, actions could be functions: action(player)
            print(action_desc)
            if "fame_boost_small" in action_desc: # Example simple action
                player.fame += 10
                print(f"Your fame increased by 10! Current fame: {player.fame}")

        print("--------------------")
        return True # Event occurred

# Define some random events
RANDOM_EVENTS = [
    RandomEvent(
        name="Fan Recognizes You",
        description_template="{player_name} is walking down the street when someone looks surprised...",
        fame_threshold_min=20, # Only if fame is at least 20
        fame_threshold_max=100,
        npc_interaction={
            "npc_type": "friendly_fan", # Using existing personality
            "npc_name": "Excited Fan",
            "initial_message": "Oh my gosh! Are you {player_name}? I love your music!"
        }
    ),
    RandomEvent(
        name="Adoring Fan Encounter",
        description_template="A particularly enthusiastic fan spots {player_name}!",
        fame_threshold_min=50,
        npc_interaction={
            "npc_type": "adoring_fan", # We'll need to add this personality
            "npc_name": "Adoring Fan",
            "initial_message": "{player_name}! I can't believe it's really you! You're my biggest inspiration!"
        }
        # Fame gain handled within the trigger method for this specific interaction for now
    ),
    RandomEvent(
        name="Local Blogger Mention",
        description_template="A local music blogger wrote a small piece mentioning {player_name}'s recent gig!",
        fame_threshold_min=30,
        fame_threshold_max=150,
        actions=["Your name is getting out there! fame_boost_small"]
    ),
    RandomEvent(
        name="Quiet Day",
        description_template="It's a quiet day for {player_name}. Nothing much happens.",
        fame_threshold_min=0
        # No actions, no NPC
    ),
    RandomEvent(
        name="Post-Gig Autograph Request",
        description_template="After your successful performance, a fan approaches {player_name} excitedly!",
        fame_threshold_min=40, # Needs some fame
        # This event is special and should be triggered contextually (e.g., after a gig)
        # rather than purely randomly during general time advance.
        # The generic check_for_random_event might pick it up, or we can have a specific trigger.
        npc_interaction={
            "npc_type": "friendly_fan", # Re-use existing, or make a "grateful_fan"
            "npc_name": "Eager Fan",
            "initial_message": "That was an amazing show, {player_name}! Could I possibly get your autograph?"
        }
        # Action: Small fame boost, positive feeling.
        # Could add a mini-choice: sign graciously, be dismissive (affecting fame/fan reaction).
        # For now, positive interaction is assumed from the LLM.
    )
]

POST_GIG_EVENTS = [
    RANDOM_EVENTS[-1] # Assuming "Post-Gig Autograph Request" is the last one added
]


def check_for_random_event(player, chance=0.25, event_pool=None):
    """
    Checks if a random event should occur based on chance and player's fame.
    Returns True if an event was triggered, False otherwise.
    event_pool: Optional list of events to choose from. Defaults to RANDOM_EVENTS.
    """
    if event_pool is None:
        event_pool = RANDOM_EVENTS

    if random.random() < chance:
        eligible_events = [
            event for event in event_pool
            if player.fame >= event.fame_threshold_min and player.fame <= event.fame_threshold_max
        ]
        if eligible_events:
            event_to_trigger = random.choice(eligible_events)
            return event_to_trigger.trigger(player)
    return False

def check_for_post_gig_random_event(player, performed_event_type, chance=0.5):
    """
    Specific check for events that can happen after a gig.
    Chance might depend on the type of gig performed.
    """
    actual_chance = chance
    if performed_event_type == "CONCERT" or performed_event_type == "FESTIVAL_SLOT":
        actual_chance = 0.8 # Higher chance after big events
    elif performed_event_type == "CLUB_GIG":
        actual_chance = 0.6

    # For now, only use the specific Post-Gig Autograph event.
    # This could be expanded to a pool of post-gig events.
    return check_for_random_event(player, chance=actual_chance, event_pool=POST_GIG_EVENTS)

# Need to add 'adoring_fan' to dialogue personalities
def update_dialogue_personalities():
# The 'adoring_fan' personality is now defined directly in game/dialogue.py.
# No need for the dynamic update here anymore.
