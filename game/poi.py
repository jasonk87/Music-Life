# poi.py (Point Of Interest)

class PointOfInterest:
    def __init__(self, poi_id, name, description, category="GENERAL",
                 interaction_options=None, parent_location_id=None,
                 rest_quality=0.0, stress_modifier_hourly=0,
                 studio_quality=0.0, hourly_rate=0,
                 min_fame_to_submit=0, genres_preferred=None,
                 comfort_modifier_hourly=0): # New comfort param
        self.poi_id = poi_id
        self.name = name
        self.description = description
        self.category = category

        self.interaction_options = interaction_options if interaction_options else []
        self.owner_npc_id = None
        self.parent_location_id = parent_location_id

        self.shop_inventory_item_ids = None
        self.vehicle_inventory = []

        self.rest_quality = rest_quality
        self.stress_modifier_hourly = stress_modifier_hourly

        self.studio_quality = studio_quality
        self.hourly_rate = hourly_rate

        self.min_fame_to_submit = min_fame_to_submit
        self.genres_preferred = genres_preferred if genres_preferred else []

        self.comfort_modifier_hourly = comfort_modifier_hourly

        self.player_interest_score = 0.0 # For OFFICE_RECORD_LABEL, how interested they are in the player

        # Specific to FOOD_FASTFOOD POIs
        self.menu_items = [] # List of dicts: {"display_text": "Order X ($Y)", "item_id": "food_item_id_from_catalog", "cost": Y, "effects": {"hunger": -Z, "energy": +W}}
        if self.category == "FOOD_FASTFOOD":
            # Interaction options should ideally be generated from menu_items or vice-versa
            # For now, interaction_options are defined separately in setup_world
            pass


        # For intra-city travel, connections could be stored here or centrally in the City(Location)
        # self.intra_city_connections = {} # poi_id: {"walk_time": X, "bike_time": Y ...}

    def __str__(self):
        details = f"{self.name} (ID: {self.poi_id}, Category: {self.category})"
        if self.shop_inventory_item_ids is not None:
            details += f" [Shop with {len(self.shop_inventory_item_ids)} item types]"
        if self.vehicle_inventory:
            details += f" [Dealership with {len(self.vehicle_inventory)} vehicles]"
        if self.category == "HOME" or self.category.startswith("ACCOMMODATION"):
            details += f" [RestQ: {self.rest_quality}, StressMod/hr: {self.stress_modifier_hourly}, ComfortMod/hr: {self.comfort_modifier_hourly}]"
        elif self.category == "POI_CAFE": # Example for other POI types that might affect comfort
             details += f" [ComfortMod/hr: {self.comfort_modifier_hourly}]"
        if self.category == "STUDIO_RECORDING":
            details += f" [StudioQ: {self.studio_quality}, Rate: ${self.hourly_rate}/hr]"
        if self.category == "OFFICE_RECORD_LABEL":
            details += f" [MinFame: {self.min_fame_to_submit}, Prefers: {', '.join(self.genres_preferred) if self.genres_preferred else 'Any'}]"
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
    assert poi2.studio_quality == 0.0 # Default for non-studio
    assert poi2.hourly_rate == 0 # Default for non-studio
    print(poi2)
    assert "[Shop with" not in str(poi2)
    assert "[RestQ: 0.8, StressMod/hr: -10, ComfortMod/hr: 0]" in str(poi2) # Updated assertion
    assert "[StudioQ:" not in str(poi2)

    poi3 = PointOfInterest(
        poi_id="studio_starlight",
        name="Starlight Studio",
        description="A decent recording studio.",
        category="STUDIO_RECORDING",
        studio_quality=0.6,
        hourly_rate=50
    )
    assert poi3.category == "STUDIO_RECORDING"
    assert poi3.studio_quality == 0.6
    assert poi3.hourly_rate == 50
    print(poi3)
    assert "[StudioQ: 0.6, Rate: $50/hr]" in str(poi3)
    assert "[MinFame:" not in str(poi3)

    poi4 = PointOfInterest(
        poi_id="label_indiehits",
        name="Indie Hits Records",
        description="Looking for the next big thing.",
        category="OFFICE_RECORD_LABEL",
        min_fame_to_submit=100,
        genres_preferred=["Indie", "Pop"]
    )
    assert poi4.category == "OFFICE_RECORD_LABEL"
    assert poi4.min_fame_to_submit == 100
    assert "Indie" in poi4.genres_preferred
    print(poi4)
    assert "[MinFame: 100, Prefers: Indie, Pop]" in str(poi4)
    assert poi4.comfort_modifier_hourly == 0 # Default

    poi5 = PointOfInterest(
        poi_id="label_allgenres",
        name="Open Door Records",
        description="We listen to everything!",
        category="OFFICE_RECORD_LABEL",
        min_fame_to_submit=50,
        comfort_modifier_hourly = -1 # e.g. a stuffy office
    )
    print(poi5)
    assert "[MinFame: 50, Prefers: Any]" in str(poi5)
    assert poi5.comfort_modifier_hourly == -1
    # __str__ for OFFICE_RECORD_LABEL doesn't show comfort_modifier_hourly, which is fine.

    poi_cafe = PointOfInterest(
        poi_id="cafe_cosy",
        name="Cosy Cafe",
        description="Relaxing place.",
        category="POI_CAFE",
        comfort_modifier_hourly=2
    )
    print(poi_cafe)
    assert "[ComfortMod/hr: 2]" in str(poi_cafe)


    print("PointOfInterest class basic tests passed.")
