# poi.py (Point Of Interest)

class PointOfInterest:
    def __init__(self, poi_id, name, description, category="GENERAL",
                 interaction_options=None, parent_location_id=None,
                 rest_quality=0.0, stress_modifier_hourly=0):
        self.poi_id = poi_id
        self.name = name
        self.description = description
        self.category = category

        self.interaction_options = interaction_options if interaction_options else []
        self.owner_npc_id = None
        self.parent_location_id = parent_location_id

        self.shop_inventory_item_ids = None

        # Attributes for accommodation/rest POIs
        self.rest_quality = rest_quality
        self.stress_modifier_hourly = stress_modifier_hourly

        # For intra-city travel, connections could be stored here or centrally in the City(Location)
        # self.intra_city_connections = {} # poi_id: {"walk_time": X, "bike_time": Y ...}

    def __str__(self):
        details = f"{self.name} (ID: {self.poi_id}, Category: {self.category})"
        if self.shop_inventory_item_ids is not None:
            details += f" [Shop with {len(self.shop_inventory_item_ids)} item types]"
        if self.category == "HOME" or self.category.startswith("ACCOMMODATION"):
            details += f" [RestQ: {self.rest_quality}, StressMod/hr: {self.stress_modifier_hourly}]"
        return details + f" - {self.description}"

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
    poi1.shop_inventory_item_ids = ["item1", "item2"] # Simulate a shop
    print(poi1)
    assert "[Shop with 2 item types]" in str(poi1)
    assert "[RestQ: 0.0, StressMod/hr: 0]" not in str(poi1) # Not an accommodation

    poi2 = PointOfInterest(
        poi_id="home_player_apt",
        name="Player's Apartment",
        description="A modest starting apartment.",
        category="HOME",
        rest_quality=0.8,
        stress_modifier_hourly=-10
    )
    assert poi2.category == "HOME"
    assert poi2.rest_quality == 0.8
    assert poi2.stress_modifier_hourly == -10
    assert poi2.shop_inventory_item_ids is None # Not a shop
    print(poi2)
    assert "[Shop with" not in str(poi2)
    assert "[RestQ: 0.8, StressMod/hr: -10]" in str(poi2)

    print("PointOfInterest class basic tests passed.")
