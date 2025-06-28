# poi.py (Point Of Interest)

class PointOfInterest:
    def __init__(self, poi_id, name, description, category="GENERAL", interaction_options=None, parent_location_id=None):
        self.poi_id = poi_id # Unique identifier, e.g., "hometown_music_shop"
        self.name = name
        self.description = description
        # Replacing poi_type with category for broader classification
        self.category = category # e.g., "HOME", "VENUE_CLUB", "SHOP_MUSIC", "TRANSPORT_AIRPORT", "CIVIC_COURTHOUSE"

        self.interaction_options = interaction_options if interaction_options else []
        self.owner_npc_id = None # Optional: store the ID of the NPC who owns/manages this POI
        self.parent_location_id = parent_location_id # ID of the city (Location object) this POI belongs to

        # For intra-city travel, connections could be stored here or centrally in the City(Location)
        # self.intra_city_connections = {} # poi_id: {"walk_time": X, "bike_time": Y ...}

    def __str__(self):
        return f"{self.name} ({self.category}) - {self.description}"

    def get_interactions(self):
        return self.interaction_options

# Example POI types and their specific interactions could be expanded later.
# e.g., a Music Store POI might have a method to generate an inventory of items to buy.
# A Rehearsal Studio might have a method to book time, costing money and allowing skill practice.
# For now, they are primarily informational.

if __name__ == "__main__":
    poi1 = PointOfInterest(
        poi_id="shop_music_mainst",
        name="Main Street Music",
        description="Sells instruments and accessories.",
        category="SHOP_MUSIC",
        interaction_options=["Browse Guitars", "Buy Strings"],
        parent_location_id="hometown"
    )
    assert poi1.poi_id == "shop_music_mainst"
    assert poi1.name == "Main Street Music"
    assert poi1.category == "SHOP_MUSIC"
    assert poi1.parent_location_id == "hometown"
    assert "Browse Guitars" in poi1.get_interactions()
    print(poi1)

    poi2 = PointOfInterest(
        poi_id="home_player_apt",
        name="Player's Apartment",
        description="A modest starting apartment.",
        category="HOME"
    )
    assert poi2.category == "HOME"
    assert poi2.owner_npc_id is None # owner_npc_id is optional
    print(poi2)

    print("PointOfInterest class basic tests passed.")
