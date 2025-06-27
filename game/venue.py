class Venue:
    def __init__(self, name, description="A place to perform or hang out.", venue_type="CLUB", capacity=100, prestige=1):
        self.name = name
        self.description = description
        self.venue_type = venue_type # e.g., "CLUB", "CAFE", "ARENA", "FESTIVAL_GROUND"
        self.capacity = capacity   # Max audience size, could influence fame/payout
        self.prestige = prestige   # 1-10, influences event quality, payout, fame
        self.events_hosted = []    # List of Event objects currently at this venue
        self.owner_npc_type = None # Optional: link to an NPC personality for the owner/manager

    def add_event(self, event):
        if event not in self.events_hosted:
            self.events_hosted.append(event)
            event.location = self # Override event's generic location with specific venue if needed
            print(f"Event '{event.name}' added to venue '{self.name}'.")

    def remove_event(self, event):
        if event in self.events_hosted:
            self.events_hosted.remove(event)
            print(f"Event '{event.name}' removed from venue '{self.name}'.")

    def __str__(self):
        return f"{self.name} ({self.venue_type}) - Capacity: {self.capacity}, Prestige: {self.prestige}"

if __name__ == '__main__':
    # Basic tests for Venue class
    class MockEvent:
        def __init__(self, name):
            self.name = name
            self.location = None # Will be set by venue.add_event

    venue = Venue("The Stage Door", venue_type="THEATER", capacity=300, prestige=5)
    assert venue.name == "The Stage Door"
    assert venue.capacity == 300

    event1 = MockEvent("Play Rehearsal")
    event2 = MockEvent("Band Night")

    venue.add_event(event1)
    assert event1 in venue.events_hosted
    assert event1.location == venue # Check if event location is updated

    venue.add_event(event2)
    assert event2 in venue.events_hosted
    assert len(venue.events_hosted) == 2

    venue.remove_event(event1)
    assert event1 not in venue.events_hosted
    assert len(venue.events_hosted) == 1

    # Try removing an event not in list (should not error)
    venue.remove_event(event1)
    assert len(venue.events_hosted) == 1

    print("Venue class basic tests passed.")
