class Player:
    def __init__(self, name):
        self.name = name
        self.location = None  # Will be a Location object
        self.skills = {}  # e.g., {"guitar": 10, "vocals": 5}
        self.fame = 0
        self.money = 500 # Starting money
        self.inventory = [] # Items
        self.has_manager = False
        self.manager_unlocked_fame_threshold = 200 # Fame needed to get a manager

    def practice_skill(self, skill_name, hours):
        if skill_name not in self.skills:
            self.skills[skill_name] = 0
        # Arbitrary skill gain formula, can be refined
        self.skills[skill_name] += hours * 0.1
        print(f"{self.name} practiced {skill_name} for {hours} hours. Skill level is now {self.skills[skill_name]:.1f}.")

    def travel(self, destination_location, travel_time):
        print(f"{self.name} is travelling from {self.location.name if self.location else 'Unknown'} to {destination_location.name}...")
        # Simulate time passing
        print(f"Travel took {travel_time} hours.")
        self.location = destination_location
        print(f"{self.name} has arrived at {destination_location.name}.")

    def check_for_manager_unlock(self):
        if not self.has_manager and self.fame >= self.manager_unlocked_fame_threshold:
            self.has_manager = True
            print("\n*** Congratulations! Your fame has grown significantly! ***")
            print("*** You've attracted the attention of a professional artist manager! ***")
            print("*** This will unlock new opportunities. (Manager interactions to be implemented further) ***\n")
            # Future: Trigger an event, introduce the manager NPC, etc.

    def __str__(self):
        status = f"Player: {self.name}, Location: {self.location.name if self.location else 'N/A'}, Fame: {self.fame}, Money: ${self.money}, Skills: {self.skills}"
        if self.has_manager:
            status += ", Manager: Yes"
        else:
            status += f", Manager: No (Unlock at {self.manager_unlocked_fame_threshold} fame)"
        return status

if __name__ == '__main__':
    # Basic tests for Player class
    p = Player("Test Dummy")
    assert p.name == "Test Dummy"
    assert p.money == 500
    assert p.fame == 0
    assert not p.has_manager

    p.practice_skill("guitar", 2)
    assert p.skills["guitar"] == 0.2
    p.practice_skill("guitar", 3)
    assert p.skills["guitar"] == 0.5
    p.practice_skill("vocals", 5)
    assert p.skills["vocals"] == 0.5

    p.fame = 200
    p.check_for_manager_unlock()
    assert p.has_manager

    # Mock location for travel test
    class MockLocation:
        def __init__(self, name):
            self.name = name

    loc1 = MockLocation("Home")
    loc2 = MockLocation("City")
    p.location = loc1
    p.travel(loc2, 5)
    assert p.location == loc2

    print("Player class basic tests passed.")
