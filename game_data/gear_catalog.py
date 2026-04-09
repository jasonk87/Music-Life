from game.gear import GearItem # Assuming GearItem class is in game/gear.py

GEAR_CATALOG = {
    "worn_acoustic_guitar": GearItem(
        item_id="worn_acoustic_guitar",
        name="Worn Acoustic Guitar",
        description="An old, battered acoustic guitar. It has seen better days but still makes a sound. Good for practice or very humble beginnings.",
        gear_type="INSTRUMENT_ACOUSTIC",
        size=5,
        cost=50,
        properties={
            "acoustic": True,
            "quality": 0.3,
            "genre_suitability": ["Folk", "Pop", "Blues", "Indie"],
            "genre_boosts": {"Folk": 0.1, "Indie": 0.05}
        }
    ),
    "basic_electric_guitar": GearItem(
        item_id="basic_electric_guitar",
        name="Basic Electric Guitar",
        description="A simple but functional Stratocaster-style electric guitar. Needs an amp.",
        gear_type="INSTRUMENT_ELECTRIC",
        size=5,
        cost=150,
        properties={
            "electric": True,
            "quality": 0.5,
            "genre_suitability": ["Rock", "Pop", "Blues", "Indie", "Electronic"],
            "genre_boosts": {"Rock": 0.1, "Blues": 0.05}
        }
    ),
    "practice_amp_small": GearItem( # Amps don't have genre suitability directly, but instruments playing through them do.
        item_id="practice_amp_small",
        name="Small Practice Amp (5W)",
        description="A small, low-wattage amplifier. Good for bedroom practice, not loud enough for gigs with a drummer.",
        gear_type="AMPLIFIER",
        size=4,
        cost=100,
        properties={"wattage": 5, "quality": 0.4} # genre_suitability will be empty list by default from GearItem
    ),
    "guitar_strings_basic": GearItem(
        item_id="guitar_strings_basic",
        name="Basic Guitar Strings",
        description="A standard set of steel guitar strings.",
        gear_type="ACCESSORY",
        size=1, # Takes minimal space
        cost=10,
        properties={"material": "steel"}
    ),
    "guitar_picks_assorted": GearItem(
        item_id="guitar_picks_assorted",
        name="Assorted Guitar Picks (Pack of 5)",
        description="A pack of 5 celluloid guitar picks of various gauges.",
        gear_type="ACCESSORY",
        size=0, # Negligible size for inventory calculation
        cost=5,
        properties={"quantity": 5}
    ),
    "microphone_basic": GearItem(
        item_id="microphone_basic",
        name="Basic Vocal Microphone",
        description="A dependable starter microphone for rehearsals and small live sets.",
        gear_type="ACCESSORY",
        size=1,
        cost=40,
        properties={"quality": 0.4, "performance_quality_bonus": 0.05}
    ),
    "notebook_lyrics": GearItem(
        item_id="notebook_lyrics",
        name="Lyric Notebook",
        description="A beat-up notebook packed with lyric fragments and half-finished ideas.",
        gear_type="ACCESSORY",
        size=1,
        cost=12,
        properties={"songwriting_bonus": 0.05}
    ),
    "laptop_basic": GearItem(
        item_id="laptop_basic",
        name="Basic Production Laptop",
        description="A modest laptop with enough power for demos, edits, and electronic sketches.",
        gear_type="ACCESSORY",
        size=3,
        cost=350,
        properties={"quality": 0.5, "electronic_bonus": 0.08}
    ),
    "headphones_studio": GearItem(
        item_id="headphones_studio",
        name="Studio Headphones",
        description="Closed-back headphones that make it easier to hear details while recording or mixing.",
        gear_type="ACCESSORY",
        size=1,
        cost=90,
        properties={"quality": 0.5, "recording_bonus": 0.05}
    ),
    "pro_electric_guitar": GearItem(
        item_id="pro_electric_guitar",
        name="Professional Electric Guitar",
        description="A high-quality electric guitar, suitable for large stages.",
        gear_type="INSTRUMENT_ELECTRIC",
        size=5,
        cost=1200,
        properties={
            "electric": True,
            "quality": 0.9,
            "genre_suitability": ["Rock", "Pop", "Blues", "Indie", "Electronic", "Metal"],
            "genre_boosts": {"Rock": 0.25, "Metal": 0.2, "Blues": 0.15}
        }
    ),
    "pro_bass_guitar": GearItem(
        item_id="pro_bass_guitar",
        name="Professional Bass Guitar",
        description="A top-tier bass guitar for a solid low end.",
        gear_type="INSTRUMENT_BASS",
        size=6,
        cost=1000,
        properties={
            "electric": True,
            "quality": 0.85,
            "genre_suitability": ["Rock", "Pop", "Blues", "Indie", "Electronic", "Metal", "Funk"],
            "genre_boosts": {"Funk": 0.25, "Rock": 0.15}
        }
    ),
    "pro_amp_large": GearItem(
        item_id="pro_amp_large",
        name="Large Stage Amp (100W)",
        description="A powerful amplifier for large venues.",
        gear_type="AMPLIFIER",
        size=10,
        cost=800,
        properties={"wattage": 100, "quality": 0.9} # No direct genre_suitability for amps
    ),
    "pro_drum_kit": GearItem(
        item_id="pro_drum_kit",
        name="Professional Drum Kit",
        description="A full 5-piece drum kit with cymbals.",
        gear_type="INSTRUMENT_DRUMS",
        size=20,
        cost=1500,
        properties={"quality": 0.8, "genre_suitability": ["Rock", "Pop", "Blues", "Indie", "Metal", "Funk", "Electronic"]} # Drums are versatile
    ),
    # Merchandise Items
    "merch_tshirt_basic": GearItem(
        item_id="merch_tshirt_basic",
        name="Basic Band T-Shirt",
        description="A simple black t-shirt with your band's current name/logo.",
        gear_type="MERCHANDISE",
        size=1, # Each shirt takes up a small amount of space
        cost=7, # Player's cost to order/buy stock
        base_sell_price=15 # Player's price to fans at gigs
    ),
    "merch_poster_small": GearItem(
        item_id="merch_poster_small",
        name="Small Gig Poster",
        description="A glossy 11x17 poster from your recent local gig.",
        gear_type="MERCHANDISE",
        size=0, # Assume they roll up small, negligible for a few
        cost=2,
        base_sell_price=5
    ),
    "merch_cd_demo": GearItem(
        item_id="merch_cd_demo",
        name="Demo CD (Home Burned)",
        description="A CD-R with a few of your latest demo tracks. DIY packaging.",
        gear_type="MERCHANDISE",
        size=0, # Negligible
        cost=1, # Cost of blank CD and case
        base_sell_price=5
    ),
    # Food Items
    "food_energy_bar": GearItem(
        item_id="food_energy_bar",
        name="Energy Bar",
        description="A dense, chewy bar packed with calories. Good for a quick energy spike.",
        gear_type="FOOD",
        size=0, # Consumable, negligible inventory space for one or two
        cost=3,
        hunger_reduction=15,
        energy_boost=20 # More energy than general comfort food
    ),
    "food_cheap_burger": GearItem( # This might be for fast food "menus" rather than inventory
        item_id="food_cheap_burger",
        name="Cheap Greasy Burger",
        description="Questionable meat, soggy bun, but it fills a hole.",
        gear_type="FOOD", # Consumed on site, so size 0 for inventory if we ever let player take away
        size=0,
        cost=5, # Price at a fast food joint
        hunger_reduction=35,
        energy_boost=10,
        properties={"comfort_effect": -2}
        # Could add a property: {"comfort_effect": -2}
    ),
    "food_grocery_bag": GearItem(
        item_id="food_grocery_bag",
        name="Bag of Groceries",
        description="A bag of basic groceries - enough for a decent meal or two at home.",
        gear_type="FOOD", # Represents multiple meal components
        size=3, # Takes some inventory space
        cost=20,
        hunger_reduction=70,
        energy_boost=25
    ),
    # --- New Food Items for Fast Food POIs ---
    "food_greasy_breakfast": GearItem(
        item_id="food_greasy_breakfast", name="Greasy Breakfast Special", gear_type="FOOD", size=0, cost=8, # Cost here is default, can be overridden by POI menu
        description="Eggs, bacon (or sausage substitute), hash browns, and toast. Fills you up.",
        hunger_reduction=50, energy_boost=15, properties={"comfort_effect": 1}
    ),
    "food_blast_burger": GearItem(
        item_id="food_blast_burger", name="Blast Burger", gear_type="FOOD", size=0, cost=7,
        description="The signature burger from Burger Blast. Comes with fries.",
        hunger_reduction=40, energy_boost=10, properties={"comfort_effect": 0}
    ),
    "food_value_meal": GearItem(
        item_id="food_value_meal", name="Value Meal", gear_type="FOOD", size=0, cost=10,
        description="A burger, fries, and a large soda. A lot of food for the price.",
        hunger_reduction=60, energy_boost=15, properties={"comfort_effect": -1} # Slightly uncomfortable from overeating
    ),
    "food_soda": GearItem(
        item_id="food_soda", name="Fizzy Soda", gear_type="FOOD", size=0, cost=2,
        description="A cup of sugary, fizzy soda.",
        hunger_reduction=5, energy_boost=5, properties={"comfort_effect": 0} # Not really food, mostly sugar
    ),
    "food_water": GearItem(
        item_id="food_water", name="Cup of Water", gear_type="FOOD", size=0, cost=0,
        description="A simple cup of tap water.",
        hunger_reduction=0, energy_boost=1 # Slight refreshment
    ),
}

if __name__ == '__main__':
    # Test that all items can be created and accessed
    # Original 15 items + 5 distinct food items + 4 starter/background items
    expected_items = 15 + 5 + 4
    assert len(GEAR_CATALOG) == expected_items, f"Expected {expected_items} items, found {len(GEAR_CATALOG)}"
    assert GEAR_CATALOG["worn_acoustic_guitar"].name == "Worn Acoustic Guitar"
    assert GEAR_CATALOG["food_energy_bar"].cost == 3
    assert GEAR_CATALOG["merch_tshirt_basic"].base_sell_price == 15
    assert GEAR_CATALOG["merch_poster_small"].size == 0
    assert GEAR_CATALOG["guitar_picks_assorted"].size == 0
    assert GEAR_CATALOG["food_greasy_breakfast"].hunger_reduction == 50
    assert GEAR_CATALOG["food_water"].cost == 0
    assert GEAR_CATALOG["food_cheap_burger"].name == "Cheap Greasy Burger"
    print(f"{len(GEAR_CATALOG)} gear items loaded from catalog.")
    for item_id, item in GEAR_CATALOG.items():
        print(f"- {item_id}: {item.name} (Cost: ${item.cost}, Size: {item.size})")
    print("Gear Catalog basic tests passed.")
