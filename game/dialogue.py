import ollama

# --- LLM Interaction Configuration ---
# This is the model we'll use for NPC dialogues.
# IMPORTANT: The user running this game MUST have Ollama installed
# and this model pulled (e.g., via `ollama pull llama3`).
LLM_MODEL = 'llama3'

# --- Pre-defined NPC Personalities/Roles ---
# These are system prompts that define the NPC's character.
NPC_PERSONALITIES = {
    "friendly_fan": {
        "system_prompt": "You are a friendly and enthusiastic fan of an up-and-coming musician. You are very supportive and a little star-struck. Keep your responses relatively short and positive.",
        "dialogue_history": [] # Each NPC could maintain its own history if needed, or a global one per interaction
    },
    "gruff_club_owner": {
        "system_prompt": "You are a busy, no-nonsense owner of a small music club. You are a bit gruff but fair. You care about good music and reliability. Keep responses concise and to the point.",
        "dialogue_history": []
    },
    "adoring_fan": {
        "system_prompt": "You are an adoring fan. You are extremely excited, positive, and a bit overwhelmed to meet the musician. You heap praise and ask for an autograph or photo. Keep responses enthusiastic and star-struck.",
        "dialogue_history": []
    },
    "default": {
        "system_prompt": "You are a helpful assistant.", # Default placeholder
        "dialogue_history": []
    }
}

def generate_npc_response(player_message, npc_personality_key="default"):
    """
    Generates a response from an NPC using the Ollama LLM.

    Args:
        player_message (str): The message from the player to the NPC.
        npc_personality_key (str): The key for the NPC's personality profile.

    Returns:
        str: The NPC's response, or an error message if something goes wrong.
    """
    if npc_personality_key not in NPC_PERSONALITIES:
        return "Error: NPC personality not found."

    personality = NPC_PERSONALITIES[npc_personality_key]
    system_prompt = personality["system_prompt"]

    # For now, let's keep a short history for the conversation context.
    # We'll just append to the personality's dialogue history.
    # A more sophisticated approach might be needed for longer conversations.

    messages = [{"role": "system", "content": system_prompt}]

    # Add recent history - let's say last 4 exchanges (system + user + assistant + user...)
    # This is a simple way to provide context.
    history_to_include = personality["dialogue_history"][-4:]
    messages.extend(history_to_include)
    messages.append({"role": "user", "content": player_message})

    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=messages
        )
        npc_response_content = response['message']['content']

        # Store the interaction in history
        personality["dialogue_history"].append({"role": "user", "content": player_message})
        personality["dialogue_history"].append({"role": "assistant", "content": npc_response_content})

        # Keep history from getting too long (e.g., last 10 messages)
        personality["dialogue_history"] = personality["dialogue_history"][-10:]

        return npc_response_content
    except ollama.ResponseError as e:
        error_message = f"LLM Error: {e.error}"
        if e.status_code == 404:
            error_message += f"\nModel '{LLM_MODEL}' not found. Please make sure Ollama is running and the model is pulled (e.g., `ollama pull {LLM_MODEL}`)."
        return error_message
    except Exception as e:
        return f"An unexpected error occurred with the LLM: {str(e)}"

def reset_dialogue_history(npc_personality_key="default"):
    """Resets the dialogue history for a given NPC personality."""
    if npc_personality_key in NPC_PERSONALITIES:
        NPC_PERSONALITIES[npc_personality_key]["dialogue_history"] = []
    elif npc_personality_key == "all":
        for key in NPC_PERSONALITIES:
            NPC_PERSONALITIES[key]["dialogue_history"] = []


# Example usage (can be run directly for testing if needed)
if __name__ == "__main__":
    print("Testing NPC dialogue generation...")
    print("Make sure Ollama is running and you have pulled the 'llama3' model.")

    # Test Friendly Fan
    reset_dialogue_history("all")
    print("\n--- Interacting with Friendly Fan ---")
    player_input = "Hey! Loved your last song!"
    print(f"Player: {player_input}")
    response = generate_npc_response(player_input, "friendly_fan")
    print(f"Fan: {response}")

    player_input = "Just practicing hard for my next gig."
    print(f"Player: {player_input}")
    response = generate_npc_response(player_input, "friendly_fan")
    print(f"Fan: {response}")

    # Test Gruff Club Owner
    reset_dialogue_history("all")
    print("\n--- Interacting with Gruff Club Owner ---")
    player_input = "I'm looking for a gig. I play guitar and sing."
    print(f"Player: {player_input}")
    response = generate_npc_response(player_input, "gruff_club_owner")
    print(f"Club Owner: {response}")

    player_input = "I'm reliable and always on time."
    print(f"Player: {player_input}")
    response = generate_npc_response(player_input, "gruff_club_owner")
    print(f"Club Owner: {response}")

    # Test model not found error (if you haven't pulled 'nonexistentmodel')
    # print("\n--- Testing Model Not Found ---")
    # LLM_MODEL = 'nonexistentmodel'
    # player_input = "Hello?"
    # print(f"Player: {player_input}")
    # response = generate_npc_response(player_input, "default")
    # print(f"NPC: {response}")
    # LLM_MODEL = 'llama3' # Reset for other tests or game
    print("\nTest complete. If you saw model errors, ensure Ollama is running and models are pulled.")
