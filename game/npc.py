from enum import Enum

class RelationshipStatus(Enum):
    HOSTILE = -2
    UNFRIENDLY = -1
    NEUTRAL = 0
    FRIENDLY = 1
    ALLY = 2 # or FAN for certain types

class NPC:
    def __init__(self, npc_id, name, personality_key, home_location=None, current_location=None, schedule=None):
        self.npc_id = npc_id # Unique identifier for this NPC
        self.name = name
        self.personality_key = personality_key # Links to NPC_PERSONALITIES for LLM style

        self.current_location = current_location # Will be a Location, Venue, or POI object
        self.home_location = home_location # Typically a Venue or POI where they work/live

        # Schedule: Dict mapping DayOfWeek_TimeSlot (e.g., "Monday_Morning") to location_name or activity
        # For now, location_name will be key to a Location/Venue/POI object later
        self.schedule = schedule if schedule else {}

        self.relationship_with_player = RelationshipStatus.NEUTRAL
        self.relationship_score = 0 # More granular score, -100 to 100

        self.memories = [] # List of strings summarizing key interactions/facts
        self.dialogue_history = [] # Specific to this NPC instance
        self.skills = {} # e.g., {"guitar": 10, "vocals": 5}

    def __str__(self):
        return f"NPC: {self.name} (ID: {self.npc_id}, Personality: {self.personality_key}, Relationship: {self.relationship_with_player.name} ({self.relationship_score}))"

    def add_memory(self, memory_string):
        self.memories.append(memory_string)
        # Optional: Limit memory size, e.g., self.memories = self.memories[-20:]
        print(f"Memory added for {self.name}: '{memory_string}'")

    def update_relationship(self, points):
        new_score = self.relationship_score + points
        self.relationship_score = max(-100, min(100, new_score)) # Clamp between -100 and 100

        # Update descriptive status based on score
        if self.relationship_score <= -50:
            self.relationship_with_player = RelationshipStatus.HOSTILE
        elif self.relationship_score <= -10:
            self.relationship_with_player = RelationshipStatus.UNFRIENDLY
        elif self.relationship_score < 10:
            self.relationship_with_player = RelationshipStatus.NEUTRAL
        elif self.relationship_score < 50:
            self.relationship_with_player = RelationshipStatus.FRIENDLY
        else:
            self.relationship_with_player = RelationshipStatus.ALLY

        print(f"Relationship with {self.name} changed by {points}. New score: {self.relationship_score} ({self.relationship_with_player.name})")

    def get_full_dialogue_context(self, player_name="Player"):
        """
        Prepares the full message list for Ollama, including system prompt,
        memories (if any), relationship status, and dialogue history.
        """
        # This will require access to NPC_PERSONALITIES from dialogue.py
        # For now, let's assume it's passed in or accessed globally (will refine in dialogue.py modification step)

        # Placeholder - actual implementation will be part of dialogue.py changes
        # to incorporate memories and relationship into the prompt.

        # The dialogue history here is specific to THIS NPC instance.
        # The system prompt will come from NPC_PERSONALITIES[self.personality_key]

        # Example structure (to be refined when generate_npc_response is updated):
        # messages = [
        #     {"role": "system", "content": f"{system_prompt_base} You are talking to {player_name}. Your current relationship is {self.relationship_with_player.name}."},
        # ]
        # if self.memories:
        #     messages.append({"role": "system", "content": f"Key memories concerning {player_name}: {'; '.join(self.memories[-3:])}"}) # Last 3 memories
        # messages.extend(self.dialogue_history)
        return self.dialogue_history # Temporary, will be more complex

# Example Usage (for testing this file directly)
if __name__ == "__main__":
    npc1 = NPC(npc_id="joe001", name="Old Timer Joe", personality_key="gruff_club_owner") # Using existing key for test
    print(npc1)
    npc1.add_memory("Player asked about vintage guitars.")
    npc1.update_relationship(15) # Player was nice
    print(npc1)
    assert npc1.relationship_score == 15
    assert npc1.relationship_with_player == RelationshipStatus.FRIENDLY

    npc1.update_relationship(-30) # Player insulted his prize banjo
    print(npc1)
    assert npc1.relationship_score == -15
    assert npc1.relationship_with_player == RelationshipStatus.UNFRIENDLY

    npc1.dialogue_history.append({"role": "user", "content": "Hello Joe."})
    npc1.dialogue_history.append({"role": "assistant", "content": "Hmph. What d'ya want?"})
    assert len(npc1.dialogue_history) == 2

    print("\nNPC class basic tests passed.")
