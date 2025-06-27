class Event:
    EVENT_TYPES = {
        "OPEN_MIC": {"base_fame": 10, "base_payout": 50, "skill_multiplier": 1.0},
        "CLUB_GIG": {"base_fame": 50, "base_payout": 250, "skill_multiplier": 1.5},
        "CONCERT": {"base_fame": 200, "base_payout": 1000, "skill_multiplier": 2.0},
        "FESTIVAL_SLOT": {"base_fame": 500, "base_payout": 3000, "skill_multiplier": 2.5}
    }

    def __init__(self, name, location, event_type="OPEN_MIC", required_skills=None, description="", specific_fame_reward=None, specific_payout=None):
        self.name = name
        self.location = location # Location object
        self.event_type = event_type

        type_details = Event.EVENT_TYPES.get(event_type, Event.EVENT_TYPES["OPEN_MIC"])

        self.required_skills = required_skills if required_skills else {} # e.g., {"guitar": 5}
        # Adjust required skills based on event type, e.g. higher for concerts
        for skill in list(self.required_skills.keys()): # Iterate over a copy of keys
            self.required_skills[skill] = max(1, int(self.required_skills[skill] * type_details["skill_multiplier"]))

        self.fame_reward = specific_fame_reward if specific_fame_reward is not None else type_details["base_fame"]
        self.payout = specific_payout if specific_payout is not None else type_details["base_payout"] # Assuming we'll add money later

        self.description = description
        self.is_active = True
        self.preparation_tasks_required = {} # e.g., {"rehearse_setlist": False, "promote_show": False}
        self.preparation_complete = False # Player must complete tasks before performing

    def are_preparations_complete(self):
        if not self.preparation_tasks_required:
            return True
        return all(self.preparation_tasks_required.values())

    def complete_preparation_task(self, task_name):
        if task_name in self.preparation_tasks_required:
            self.preparation_tasks_required[task_name] = True
            print(f"Preparation task '{task_name}' for '{self.name}' completed.")
            if self.are_preparations_complete():
                self.preparation_complete = True
                print(f"All preparations for '{self.name}' are complete!")
            return True
        print(f"Task '{task_name}' not found or already completed for this event.")
        return False

    def can_perform(self, player):
        if not self.is_active:
            return False, "This event is no longer active."

        if not self.are_preparations_complete():
            pending_tasks = [task for task, completed in self.preparation_tasks_required.items() if not completed]
            return False, f"Event preparations are not complete. Pending: {', '.join(pending_tasks)}"

        for skill, required_level in self.required_skills.items():
            if player.skills.get(skill, 0) < required_level:
                return False, f"Player does not meet skill requirement for {skill} (needs {required_level}, has {player.skills.get(skill, 0)})."
        return True, "Player meets all requirements."

    def perform_event(self, player):
        can_perform, message = self.can_perform(player)
        if not can_perform:
            print(f"Cannot perform {self.name}: {message}")
            return False

        print(f"{player.name} is performing at {self.name} at {self.location.name}!")
        # Add more event logic here (e.g., minigame, skill checks for quality)
        print(f"The event was a success!")
        player.fame += self.fame_reward
        player.money += self.payout
        print(f"{player.name} gained {self.fame_reward} fame. Total fame: {player.fame}.")
        print(f"{player.name} earned ${self.payout}. Total money: ${player.money}.")
        self.is_active = False # Assuming events are one-time, can be changed
        return True

    def __str__(self):
        venue_name = self.location.name if hasattr(self.location, 'name') else "Unknown Venue"
        if hasattr(self.location, 'venue_type'): # If location is a Venue object
             venue_name = f"{self.location.name} ({self.location.venue_type})"
        return f"Event: {self.name} at {venue_name}, Requires: {self.required_skills}, Reward: {self.fame_reward} fame, Payout: ${self.payout}."

if __name__ == '__main__':
    # Basic tests for Event class
    # Need mock Player and Location/Venue for full testing
    class MockPlayer:
        def __init__(self):
            self.skills = {"guitar": 5, "vocals": 5}
            self.fame = 0
            self.money = 0

    class MockVenue:
        def __init__(self, name="Test Venue"):
            self.name = name
            self.venue_type = "CLUB"

    player = MockPlayer()
    venue = MockVenue()

    # Test basic event
    event1 = Event("Open Mic", venue, event_type="OPEN_MIC", required_skills={"guitar": 1})
    assert event1.name == "Open Mic"
    assert event1.fame_reward == Event.EVENT_TYPES["OPEN_MIC"]["base_fame"]
    can_perform, _ = event1.can_perform(player)
    assert can_perform

    # Test event with preparations
    event2 = Event("Big Show", venue, event_type="CONCERT", required_skills={"vocals": 10}) # Player vocals are 5
    event2.preparation_tasks_required = {"Rehearse": False, "Promote": False}

    can_perform, msg = event2.can_perform(player)
    assert not can_perform
    assert "preparations are not complete" in msg

    event2.complete_preparation_task("Rehearse")
    assert event2.preparation_tasks_required["Rehearse"]
    can_perform, msg = event2.can_perform(player)
    assert not can_perform # Still needs Promote, and also skill check will fail

    event2.complete_preparation_task("Promote")
    assert event2.are_preparations_complete()

    can_perform, msg = event2.can_perform(player) # Now prep is done, but skills are too low
    assert not can_perform
    assert "Player does not meet skill requirement for vocals" in msg

    player.skills["vocals"] = 10 # Meet skill req
    can_perform, msg = event2.can_perform(player)
    assert can_perform

    # Test performance
    initial_fame = player.fame
    initial_money = player.money
    event2.perform_event(player)
    assert player.fame == initial_fame + Event.EVENT_TYPES["CONCERT"]["base_fame"]
    assert player.money == initial_money + Event.EVENT_TYPES["CONCERT"]["base_payout"]
    assert not event2.is_active

    print("Event class basic tests passed.")
