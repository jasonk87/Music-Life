import ollama

# --- LLM Interaction Configuration ---
# This is the model we'll use for NPC dialogues.
# IMPORTANT: The user running this game MUST have Ollama installed
# and this model pulled (e.g., via `ollama pull llama3`).
LLM_MODEL = 'llama3'

# --- Pre-defined NPC Personality Templates ---
# These store the base system prompt for an NPC's personality type.
# Dialogue history is now managed per NPC instance.
NPC_PERSONALITIES = {
    "friendly_fan": {
        "system_prompt": "You are a friendly and enthusiastic fan of an up-and-coming musician. You are very supportive and a little star-struck. Keep your responses relatively short and positive."
    },
    "gruff_club_owner": {
        "system_prompt": "You are Vic Vega, the busy, no-nonsense owner of 'The Rusty Mug' club. You're a bit gruff on the surface, seen too many hopefuls come and go, but you're ultimately fair and have a keen ear for genuine talent and professionalism. You value reliability and musicians who can actually draw a crowd. Keep responses concise, business-like, but occasionally let slip a hint of your own past in the music scene or a rare piece of encouragement if truly impressed."
    },
    "adoring_fan": { # Used for Sarah the Fan
        "system_prompt": "You are Sarah, a die-hard supporter of local music in Your Hometown and one of the player's earliest and most enthusiastic fans. You are extremely excited, positive, and a bit overwhelmed to meet them. You heap praise and might ask for an autograph or photo. Keep responses enthusiastic and star-struck, often referencing their local performances."
    },
    "old_timer_joe": {
        "system_prompt": "You are Old Timer Joe, owner of a dusty but cherished music shop. You've seen it all in the music world. You are a bit grumpy, nostalgic, but have a soft spot for genuine talent and hard workers. You often speak in folksy idioms."
    },
    "potential_bandmate_guitarist": {
        "system_prompt": "You are a skilled guitarist, currently without a band but always on the lookout for a serious project with talented musicians. You can be a bit critical of others' skills but respect dedication and originality. You're not overly chatty but will talk shop about gear, music theory, or potential collaborations if impressed."
    },
    "music_blogger_critical": {
        "system_prompt": "You are a local music blogger known for your sharp, often cynical, but fair reviews. You frequent various venues, always observing. You're unimpressed by hype and look for genuine talent, originality, and effort. You might offer cryptic hints or direct feedback if you think someone has potential or is completely missing the mark."
    },
    "grateful_fan": {
        "system_prompt": "You are a grateful fan who just saw the player perform. You are very appreciative of their talent and the show they just put on. You are excited but polite, and primarily want to express your thanks and admiration for the specific performance or a favorite song they played."
    },
    "interviewer_professional": {
        "system_prompt": "You are Brenda Reporter, a professional journalist for the City Center Chronicle. You are conducting an interview with an up-and-coming musician. Your tone is inquisitive, fair, and focused on their career, music, recent activities, and future plans. Ask insightful questions. You might start by welcoming them and then move into questions about their journey, their music, a recent successful gig, or what they're working on next. Keep the interview to about 3-4 main questions from your side, allowing the musician to elaborate."
    },
    "default": {
        "system_prompt": "You are a helpful assistant." # Default placeholder
    }
}

def generate_npc_response(player_message, npc_instance, player_name="The Musician"):
    """
    Generates a response from an NPC using the Ollama LLM, considering the NPC's personality,
    memories, relationship with the player, and dialogue history.

    Args:
        player_message (str): The message from the player to the NPC.
        npc_instance (NPC): The specific NPC object instance anwering.
        player_name (str): The player's character name, for context.

    Returns:
        str: The NPC's response, or an error message if something goes wrong.
    """
    if not npc_instance or not hasattr(npc_instance, 'personality_key'):
        return "Error: Invalid NPC instance provided."

    personality_key = npc_instance.personality_key
    if personality_key not in NPC_PERSONALITIES:
        return f"Error: NPC personality key '{personality_key}' not found in templates."

    base_system_prompt = NPC_PERSONALITIES[personality_key]["system_prompt"]

    # Construct the full system prompt with context
    contextual_system_prompt = f"{base_system_prompt}\n"
    contextual_system_prompt += f"You are talking to {player_name}.\n"
    contextual_system_prompt += f"Your current disposition towards {player_name} is: {npc_instance.relationship_with_player.name} (Score: {npc_instance.relationship_score}).\n"

    if npc_instance.memories:
        # Include a few recent/relevant memories
        memory_summary = "; ".join(npc_instance.memories[-3:]) # Last 3 memories
        contextual_system_prompt += f"Key things you remember concerning {player_name}: {memory_summary}\n"

    messages = [{"role": "system", "content": contextual_system_prompt}]

    # Add dialogue history (e.g., last 6 messages, 3 pairs of user/assistant)
    history_to_include = npc_instance.dialogue_history[-6:]
    messages.extend(history_to_include)
    messages.append({"role": "user", "content": player_message})

    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=messages
        )
        npc_response_content = response['message']['content']

        # Store the interaction in the NPC's instance history
        npc_instance.dialogue_history.append({"role": "user", "content": player_message})
        npc_instance.dialogue_history.append({"role": "assistant", "content": npc_response_content})

        # Keep history from getting too long (e.g., last 10-20 messages)
        npc_instance.dialogue_history = npc_instance.dialogue_history[-20:]

        return npc_response_content
    except ollama.ResponseError as e:
        error_message = f"LLM Error: {e.error}"
        if e.status_code == 404:
            error_message += f"\nModel '{LLM_MODEL}' not found. Please make sure Ollama is running and the model is pulled (e.g., `ollama pull {LLM_MODEL}`)."
        return error_message
    except Exception as e:
        return f"An unexpected error occurred with the LLM: {str(e)}"

def reset_npc_dialogue_history(npc_instance):
    """
    Resets the dialogue history for a specific NPC instance.
    This function might be less relevant now that history is per-instance,
    but could be used to wipe an NPC's memory of a specific conversation.
    The old functionality of resetting based on personality_key is removed as it's misleading.
    """
    if npc_instance and hasattr(npc_instance, 'dialogue_history'):
        npc_instance.dialogue_history = []
        print(f"Dialogue history reset for NPC: {npc_instance.name}")
    # else:
        # Consider if there's a use case for resetting all NPCs or by personality,
        # but direct instance modification is cleaner.

# Example usage (can be run directly for testing if needed)
if __name__ == "__main__":
    # Need to import NPC class for this test now
    from game.npc import NPC, RelationshipStatus

    print("Testing NPC dialogue generation with persistent NPC instances...")
    print("Make sure Ollama is running and you have pulled the 'llama3' model (or the model specified in LLM_MODEL).")

    # Create a dummy player name for testing
    test_player_name = "Rockstar Randy"

    # Test with an NPC instance: Old Timer Joe
    joe = NPC(npc_id="joe001", name="Old Timer Joe", personality_key="old_timer_joe")
    joe.update_relationship(5) # Slightly friendly start
    joe.add_memory("Randy once asked for a discount.")

    print(f"\n--- Interacting with {joe.name} ({joe.personality_key}) ---")
    print(f"Initial state: {joe}")

    player_inputs_joe = [
        "Hey Joe, got any rare guitars in stock today?",
        "That's a bit pricey for me. How about a discount for a regular like me?",
        "Alright, alright. I'll think about it. What's the music scene like these days?"
    ]

    for pi in player_inputs_joe:
        print(f"\n{test_player_name}: {pi}")
        response = generate_npc_response(pi, joe, player_name=test_player_name)
        print(f"{joe.name}: {response}")
        if "LLM Error" in response:
            print("Stopping test due to LLM error.")
            break

    print(f"\nFinal state for {joe.name}: {joe}")
    print(f"Dialogue History for {joe.name}: {joe.dialogue_history}")
    print(f"Memories for {joe.name}: {joe.memories}")


    # Test with another NPC instance: Friendly Fan
    fan = NPC(npc_id="fan001", name="Excited Amy", personality_key="friendly_fan")
    fan.update_relationship(20) # Already a fan

    print(f"\n--- Interacting with {fan.name} ({fan.personality_key}) ---")
    print(f"Initial state: {fan}")

    player_inputs_fan = [
        "Hey there! Thanks for coming to my shows.",
        "I'm working on some new songs, actually!"
    ]
    for pi in player_inputs_fan:
        print(f"\n{test_player_name}: {pi}")
        response = generate_npc_response(pi, fan, player_name=test_player_name)
        print(f"{fan.name}: {response}")
        if "LLM Error" in response:
            print("Stopping test due to LLM error.")
            break

    print(f"\nFinal state for {fan.name}: {fan}")

    # Example of resetting dialogue history for a specific NPC
    # reset_dialogue_history(npc_instance=joe)
    # print(f"Joe's dialogue history after reset: {joe.dialogue_history}")

    print("\nDialogue generation test complete. If you saw model errors, ensure Ollama is running and models are pulled.")
