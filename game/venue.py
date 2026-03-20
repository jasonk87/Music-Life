class Venue:
    def __init__(self, venue_id, name, description="A place to perform or hang out.",
                 venue_type="CLUB", category="VENUE_GENERAL",
                 capacity=100, prestige=1, parent_location_id=None,
                 can_rent_gear=False, gear_rental_fee=0, available_rental_gear_ids=None,
                 interaction_options=None, genre_bias=None):
        self.venue_id = venue_id
        self.name = name
        self.description = description
        self.venue_type = venue_type
        self.category = category
        self.capacity = capacity
        self.prestige = prestige
        self.events_hosted = []
        self.owner_npc_id = None
        self.interaction_options = interaction_options if interaction_options is not None else []
        self.parent_location_id = parent_location_id

        self.can_rent_gear = can_rent_gear
        self.gear_rental_fee = gear_rental_fee
        self.available_rental_gear_ids = available_rental_gear_ids if available_rental_gear_ids else []

        self.genre_bias = genre_bias if genre_bias else {} # e.g. {"Rock": 1.2, "Pop": 0.8}

    def add_event(self, event):
        if event not in self.events_hosted:
            self.events_hosted.append(event)
            event.location = self # Override event's generic location with specific venue if needed
            print(f"Event '{event.name}' added to venue '{self.name}'.")

    def remove_event(self, event):
        if event in self.events_hosted:
            self.events_hosted.remove(event)
            print(f"Event '{event.name}' removed from venue '{self.name}'.")

    def get_interactions(self):
        return self.interaction_options

    def __str__(self):
        base_str = f"{self.name} (ID: {self.venue_id}, Type: {self.venue_type}, Category: {self.category}, Capacity: {self.capacity}, Prestige: {self.prestige})"
        if self.can_rent_gear:
            base_str += f" [Gear Rental: Yes, Fee: ${self.gear_rental_fee}, Items: {len(self.available_rental_gear_ids)} types]"
        else:
            base_str += " [Gear Rental: No]"
        return base_str

if __name__ == '__main__':
    # Basic tests for Venue class
    class MockEvent:
        def __init__(self, name):
            self.name = name
            self.location = None # Will be set by venue.add_event

    venue1 = Venue(
        venue_id="club_rusty_mug", name="The Rusty Mug",
        description="A well-known club.", venue_type="CLUB", category="VENUE_CLUB",
        capacity=150, prestige=4, parent_location_id="city_center",
        can_rent_gear=True, gear_rental_fee=25, available_rental_gear_ids=["amp_basic", "drum_kit_basic"]
    )
    assert venue1.venue_id == "club_rusty_mug"
    assert venue1.can_rent_gear
    assert venue1.gear_rental_fee == 25
    assert "amp_basic" in venue1.available_rental_gear_ids
    print(venue1)
    assert "[Gear Rental: Yes, Fee: $25, Items: 2 types]" in str(venue1)


    venue2 = Venue(
        venue_id="hall_community", name="Community Hall",
        description="Local events.", venue_type="HALL", category="VENUE_HALL",
        capacity=50, prestige=1, parent_location_id="hometown",
        can_rent_gear=False # This one cannot rent gear
    )
    assert not venue2.can_rent_gear
    print(venue2)
    assert "[Gear Rental: No]" in str(venue2)

    event1_test = MockEvent("Band Night Test 1")
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
