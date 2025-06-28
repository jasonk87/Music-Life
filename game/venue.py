class Venue:
    def __init__(self, venue_id, name, description="A place to perform or hang out.", venue_type="CLUB", category="VENUE_GENERAL", capacity=100, prestige=1, parent_location_id=None):
        self.venue_id = venue_id # Unique identifier, e.g., "city_center_rusty_mug"
        self.name = name
        self.description = description
        self.venue_type = venue_type # Specific type like "CLUB", "CAFE", "ARENA", "FESTIVAL_GROUND"
        self.category = category # Broader category, e.g., "VENUE_CLUB", "VENUE_THEATER"
                                 # Often derived from venue_type, but explicit for consistency with POI
        self.capacity = capacity
        self.prestige = prestige
        self.events_hosted = []
        self.owner_npc_id = None
        self.parent_location_id = parent_location_id # ID of the city this venue is in

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
        return f"{self.name} (ID: {self.venue_id}, Type: {self.venue_type}, Category: {self.category}, Capacity: {self.capacity}, Prestige: {self.prestige})"

if __name__ == '__main__':
    # Basic tests for Venue class
    class MockEvent:
        def __init__(self, name):
            self.name = name
            self.location = None # Will be set by venue.add_event

    venue1 = Venue(
        venue_id="club_rusty_mug",
        name="The Rusty Mug",
        description="A well-known club.",
        venue_type="CLUB",
        category="VENUE_CLUB",
        capacity=150,
        prestige=4,
        parent_location_id="city_center"
        )
    assert venue1.venue_id == "club_rusty_mug"
    assert venue1.name == "The Rusty Mug"
    assert venue1.category == "VENUE_CLUB"
    assert venue1.parent_location_id == "city_center"
    assert venue1.capacity == 150
    print(venue1)

    event1_test = MockEvent("Band Night Test 1") # Renamed to avoid confusion
    event2_test = MockEvent("Band Night Test 2")

    venue1.add_event(event1_test)
    assert event1_test in venue1.events_hosted
    assert event1_test.location == venue1 # Check if event location is updated

    venue1.add_event(event2_test)
    assert event2_test in venue1.events_hosted
    assert len(venue1.events_hosted) == 2

    venue1.remove_event(event1_test)
    assert event1_test not in venue1.events_hosted
    assert len(venue1.events_hosted) == 1

    # Try removing an event not in list (should not error)
    venue1.remove_event(event1_test)
    assert len(venue1.events_hosted) == 1

    print("Venue class basic tests passed.")
