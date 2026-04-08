from game.venue import Venue # Assuming Venue class is in venue.py
from game.poi import PointOfInterest # Assuming PointOfInterest class is in poi.py

class Location:
    def __init__(self, name, description="A place in the world.", travel_connections=None):
        self.name = name
        self.description = description

        # Instead of generic events_available, locations now have venues, and venues host events.
        # However, some events might be location-wide (e.g. a street festival not tied to a specific venue)
        # For now, let's keep events_available for such cases, or for simpler, non-venue specific events.
        self.events_available = [] # For location-wide or non-venue specific events

        self.venues = [] # List of Venue objects in this location
        self.points_of_interest = [] # List of PointOfInterest objects

        # travel_connections: dict mapping Location object or name to details like {"cost": 50, "time_hours": 2} (Inter-city)
        self.travel_connections = travel_connections if travel_connections else {}

        # Intra-city connections: dict mapping frozenset({poi_id1, poi_id2}) to travel mode details
        self.intra_city_poi_connections = {}

    def add_venue(self, venue):
        if isinstance(venue, Venue) and venue not in self.venues:
            self.venues.append(venue)
            print(f"Venue '{venue.name}' added to {self.name}.")
        else:
            print(f"Could not add venue to {self.name}. Invalid venue object or already exists.")

    def add_poi(self, poi):
        if isinstance(poi, PointOfInterest) and poi not in self.points_of_interest:
            self.points_of_interest.append(poi)
            print(f"Point of Interest '{poi.name}' added to {self.name}.")
        else:
            print(f"Could not add POI to {self.name}. Invalid POI object or already exists.")

    def add_location_event(self, event): # For events not tied to a specific venue
        self.events_available.append(event)

    def remove_location_event(self, event): # For events not tied to a specific venue
        if event in self.events_available:
            self.events_available.remove(event)

    def get_all_events_at_location(self):
        """Returns a list of all events, from venues and location-wide."""
        all_events = list(self.events_available) # Start with location-wide events
        for venue in self.venues:
            all_events.extend(venue.events_hosted)
        return all_events

    def ensure_intra_city_connectivity(self):
        """
        Ensures that every POI and Venue in this location has at least a fallback
        intra-city travel connection to every other POI and Venue.
        If a connection already exists, it is preserved.
        """
        all_targets = self.points_of_interest + self.venues
        for i in range(len(all_targets)):
            for j in range(i + 1, len(all_targets)):
                target1 = all_targets[i]
                target2 = all_targets[j]

                id1 = getattr(target1, 'poi_id', getattr(target1, 'venue_id', None))
                id2 = getattr(target2, 'poi_id', getattr(target2, 'venue_id', None))

                if not id1 or not id2:
                    continue

                connection_key = frozenset((id1, id2))
                if connection_key not in self.intra_city_poi_connections:
                    # Create a default fallback connection
                    self.intra_city_poi_connections[connection_key] = {
                        "walk": {"time": 20, "cost": 0},
                        "taxi": {"time": 5, "cost": 15},
                        "bike": {"time": 8, "cost": 0, "requires_bike": True}
                    }

    def add_travel_connection(self, destination_location_name, cost, time_hours, method=None):
        # In a fuller system, destination_location_name might be resolved to an object.
        # For now, just store by name.
        connection = {"cost": cost, "time_hours": time_hours}
        if method:
            connection["method"] = method
        self.travel_connections[destination_location_name] = connection

    def get_travel_details(self, destination_location_name):
        return self.travel_connections.get(destination_location_name)

    def __str__(self):
        return f"Location: {self.name} ({self.description})"

if __name__ == '__main__':
    # Basic tests for Location class

    class MockEvent:
        def __init__(self, name):
            self.name = name

    loc = Location("Testville", "A place for testing.")
    assert loc.name == "Testville"

    venue1 = Venue(venue_id="test_venue", name="The Test Tent")
    poi1 = PointOfInterest(poi_id="test_poi", name="Test Statue", description="A statue for testing.")

    loc.add_venue(venue1)
    assert venue1 in loc.venues

    loc.add_poi(poi1)
    assert poi1 in loc.points_of_interest

    event_loc = MockEvent("Town Fair")
    loc.add_location_event(event_loc)
    assert event_loc in loc.events_available

    event_venue = MockEvent("Tent Concert")
    # In real use, venue.add_event would also set event.location to the venue
    # Here, we are testing get_all_events_at_location, so we add directly to venue's list
    venue1.add_event(event_venue)

    all_events = loc.get_all_events_at_location()
    assert event_loc in all_events
    assert event_venue in all_events
    assert len(all_events) == 2

    loc.add_travel_connection("Cityburg", cost=10, time_hours=1)
    conn_details = loc.get_travel_details("Cityburg")
    assert conn_details["cost"] == 10
    assert conn_details["time_hours"] == 1

    loc.remove_location_event(event_loc)
    assert event_loc not in loc.events_available

    print("Location class basic tests passed.")
