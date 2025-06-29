# game/interactions.py

from game.player import Player
from game.npc import NPC
from game.dialogue import generate_npc_response # Assuming this can be imported
# from game.game_time import advance_game_time # Best to return time_passed and let caller advance
# from main import present_choices # Avoid direct import from main.py for now

# Simplified local version of present_choices to avoid circular dependency
def _present_interaction_choices(options, title="Choose an action:"):
    """
    Presents a numbered list of choices to the player and gets valid input.
    Args:
        options (list): A list of strings.
        title (str): The title to display before the options.
    Returns:
        str: The chosen option index as a string (1-based), or None.
    """
    print(f"\n--- {title} ---")
    for i, option_text in enumerate(options):
        print(f"{i+1}. {option_text}")

    max_attempts = 3
    for attempt in range(max_attempts):
        choice = input("> ")
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return str(int(choice))
        print(f"Invalid choice. Please enter a valid number. ({max_attempts - 1 - attempt} attempts left)")
    print("Too many invalid attempts.")
    return None


def handle_autograph_interaction(player: Player, fan_npc: NPC, interaction_context: str = "random_encounter"):
    """
    Handles the interaction logic for an autograph signing encounter.

    Args:
        player: The player object.
        fan_npc: The NPC fan object.
        interaction_context: String describing the context (e.g., "random_encounter", "pre_gig_signing").

    Returns:
        A dictionary containing:
            - "outcome": str (e.g., "signed_chatted", "signed_quickly", "refused", "no_choice")
            - "minutes_passed": int
            - "fame_gained": int (optional)
            - "stress_change": int (optional)
            - "comfort_change": int (optional)
    """
    print(f"\nEncounter context: {interaction_context.replace('_', ' ').capitalize()}")
    print(f"{fan_npc.name} approaches you, looking excited!")
    # Potentially, fan_npc could have a pre-scripted line here based on their personality or context
    # For example: fan_npc.say_line("generic_autograph_request")

    interaction_options = [
        "Sign autograph and chat for a moment.",
        "Sign autograph quickly.",
        "Politely refuse."
    ]

    choice_key = _present_interaction_choices(interaction_options, title=f"What do you do with {fan_npc.name}?")

    outcome_data = {
        "outcome": "no_choice",
        "minutes_passed": 0,
        "fame_gained": 0,
        "stress_change": 0,
        "comfort_change": 0
    }

    if choice_key == "1": # Sign & Chat
        print(f"\nYou take a moment to sign an autograph for {fan_npc.name} and chat.")
        # Simulate signing

        # LLM Chat
        player_chat_input = input(f"You to {fan_npc.name} (or type 'done' to finish chat): ")
        if player_chat_input.lower() != 'done':
            # For simplicity, one exchange. Could be a loop for more.
            npc_response = generate_npc_response(player_chat_input, fan_npc, player.name)
            print(f"{fan_npc.name}: {npc_response}")
            if "LLM Error" not in npc_response and "unexpected error" not in npc_response:
                 fan_npc.add_memory(f"Player {player.name} chatted with me: '{player_chat_input}'. I said: '{npc_response}'")
                 fan_npc.update_relationship(5) # Small relationship boost from chat

        player.fame += 2
        player.stress = max(0, player.stress - 5)
        player.comfort = min(100, player.comfort + 3)

        outcome_data["outcome"] = "signed_chatted"
        outcome_data["minutes_passed"] = 10
        outcome_data["fame_gained"] = 2
        outcome_data["stress_change"] = -5
        outcome_data["comfort_change"] = 3
        print(f"Fame increased by 2. Stress reduced by 5. Comfort increased by 3.")

    elif choice_key == "2": # Sign Quickly
        print(f"\nYou quickly sign an autograph for {fan_npc.name}.")
        player.fame += 1

        outcome_data["outcome"] = "signed_quickly"
        outcome_data["minutes_passed"] = 2
        outcome_data["fame_gained"] = 1
        print(f"Fame increased by 1.")

    elif choice_key == "3": # Refuse
        print(f"\nYou politely decline to sign an autograph at this time.")
        player.stress = min(100, player.stress + 2)
        fan_npc.update_relationship(-3) # Slight negative impact for refusal
        fan_npc.add_memory(f"Player {player.name} refused to give me an autograph.")

        outcome_data["outcome"] = "refused"
        outcome_data["minutes_passed"] = 1
        outcome_data["stress_change"] = 2
        print(f"Stress increased slightly.")

    else: # No valid choice made
        print("You hesitate and the moment passes...")
        outcome_data["minutes_passed"] = 1

    # The calling function will be responsible for:
    # 1. Advancing game time using outcome_data["minutes_passed"]
    # 2. Calling update_npc_locations(current_game_time)
    # 3. Calling process_time_based_player_needs(player, minutes_passed)

    return outcome_data

if __name__ == '__main__':
    # Basic test setup
    print("--- Testing handle_autograph_interaction ---")
    player = Player("Test Musician")
    player.fame = 50
    player.stress = 10
    player.comfort = 60

    # Mock NPC and dialogue for testing without real LLM if needed
    # For now, assumes generate_npc_response can run or gracefully degrade
    from game.dialogue import NPC_PERSONALITIES
    if "test_fan" not in NPC_PERSONALITIES:
        NPC_PERSONALITIES["test_fan"] = {
            "system_prompt_template": "You are a friendly fan of {player_name}. You are very excited to meet them.",
            "dialogue_history": [] # Ensure it's a list for the function
        }

    fan = NPC(npc_id="fan001", name="Excited Eric", personality_key="test_fan")

    # Test case 1: Sign and Chat
    print("\n--- Test Case 1: Sign and Chat ---")
    # Simulate input "1" for Sign & Chat, then "Hello Eric!" for chat
    # This test needs interactive input or mocking of input() and generate_npc_response
    # For non-interactive test, we can't fully test the chat part here without mocking.
    # Let's assume we test the path by manually typing "1" and "Hello" when prompted.
    # To make it runnable:
    # import builtins
    # original_input = builtins.input
    # inputs = ["1", "Hello Eric!"]
    # def mock_input(prompt):
    #     print(prompt, end='')
    #     val = inputs.pop(0)
    #     print(val)
    #     return val
    # builtins.input = mock_input

    # result1 = handle_autograph_interaction(player, fan)
    # print(f"Test Case 1 Result: {result1}")
    # assert result1["outcome"] == "signed_chatted"
    # assert player.fame == 52
    # assert player.stress == 5
    # assert player.comfort == 63
    # assert result1["minutes_passed"] > 0
    # builtins.input = original_input # Restore
    print("Note: Interactive parts of 'Sign and Chat' need manual testing or input mocking.")


    # Test case 2: Sign Quickly (Input "2")
    # player.fame = 50; player.stress = 10; player.comfort = 60 # Reset
    # inputs = ["2"]
    # builtins.input = mock_input
    # result2 = handle_autograph_interaction(player, fan)
    # print(f"Test Case 2 Result: {result2}")
    # assert result2["outcome"] == "signed_quickly"
    # assert player.fame == 51
    # assert result2["minutes_passed"] > 0
    # builtins.input = original_input

    # Test case 3: Refuse (Input "3")
    # player.fame = 50; player.stress = 10; player.comfort = 60 # Reset
    # inputs = ["3"]
    # builtins.input = mock_input
    # result3 = handle_autograph_interaction(player, fan)
    # print(f"Test Case 3 Result: {result3}")
    # assert result3["outcome"] == "refused"
    # assert player.stress == 12
    # assert result3["minutes_passed"] > 0
    # builtins.input = original_input

    print("\nBasic structure of handle_autograph_interaction is set up.")
    print("Further testing requires running the game or mocking input/LLM calls.")
    print("To manually test, run this file and input choices.")

    # Example of a manual test call if you run `python -m game.interactions`
    if True: # Set to False to skip manual test during automated runs if problematic
        print("\n--- Manual Test Prompt ---")
        player_manual = Player("Manual Tester")
        player_manual.fame = 20
        player_manual.stress = 20
        fan_manual = NPC(npc_id="fan_manual", name="Interactive Fan", personality_key="test_fan")
        manual_result = handle_autograph_interaction(player_manual, fan_manual)
        print(f"Manual Test Result: {manual_result}")
        print(f"Player after manual test: Fame {player_manual.fame}, Stress {player_manual.stress}, Comfort {player_manual.comfort}")

# To make this runnable for basic check, ensure NPC_PERSONALITIES has 'test_fan'
# or modify the personality_key used in test.
# The generate_npc_response might also need Ollama running with a model.
# If Ollama is not running, it should gracefully handle it (as per its existing design).
