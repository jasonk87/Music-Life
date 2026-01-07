# game/interactions.py

from game.player import Player
from game.npc import NPC
from game.dialogue import generate_npc_response # Assuming this can be imported
# from game.game_time import advance_game_time # Best to return time_passed and let caller advance
# from main import present_choices # Avoid direct import from main.py for now

def handle_autograph_interaction(player: Player, fan_npc: NPC, interaction_context: str = "random_encounter", ui=None, logger=None):
    """
    Handles the interaction logic for an autograph signing encounter.

    Args:
        player: The player object.
        fan_npc: The NPC fan object.
        interaction_context: String describing the context.
        ui: The PygameUI instance.
        logger: The logger (usually game.GAME_LOG).

    Returns:
        A dictionary containing outcome data.
    """
    if logger:
        logger.add_log_message(f"Event: {interaction_context.replace('_', ' ').capitalize()}")
        logger.add_log_message(f"{fan_npc.name} approaches you, looking excited!")

    interaction_options = {
        "chat": "Sign autograph and chat for a moment.",
        "quick": "Sign autograph quickly.",
        "refuse": "Politely refuse."
    }

    if ui:
        choice_key = ui.present_choices(interaction_options, f"What do you do with {fan_npc.name}?")
    else:
        choice_key = "quick" # Default if no UI

    outcome_data = {
        "outcome": "no_choice",
        "minutes_passed": 0,
        "fame_gained": 0,
        "stress_change": 0,
        "comfort_change": 0
    }

    if choice_key == "chat": # Sign & Chat
        if logger: logger.add_log_message(f"You take a moment to sign an autograph for {fan_npc.name} and chat.")

        # Simple chat interaction
        if ui:
            player_chat_input = ui.get_text_input(f"Say something to {fan_npc.name}:")
        else:
            player_chat_input = "Thanks for the support!"

        if player_chat_input:
            npc_response = generate_npc_response(player_chat_input, fan_npc, player.name)
            if logger: logger.add_log_message(f"{fan_npc.name}: {npc_response}")

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
        if logger: logger.add_log_message("Fame +2, Stress -5, Comfort +3")

    elif choice_key == "quick": # Sign Quickly
        if logger: logger.add_log_message(f"You quickly sign an autograph for {fan_npc.name}.")
        player.fame += 1

        outcome_data["outcome"] = "signed_quickly"
        outcome_data["minutes_passed"] = 2
        outcome_data["fame_gained"] = 1
        if logger: logger.add_log_message("Fame +1")

    elif choice_key == "refuse": # Refuse
        if logger: logger.add_log_message(f"You politely decline to sign an autograph at this time.")
        player.stress = min(100, player.stress + 2)
        fan_npc.update_relationship(-3)
        fan_npc.add_memory(f"Player {player.name} refused to give me an autograph.")

        outcome_data["outcome"] = "refused"
        outcome_data["minutes_passed"] = 1
        outcome_data["stress_change"] = 2
        if logger: logger.add_log_message("Stress +2")

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
