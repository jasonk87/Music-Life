from game.gear import GearItem # Assuming GearItem class is in game/gear.py

GEAR_CATALOG = {
    "worn_acoustic_guitar": GearItem(
        item_id="worn_acoustic_guitar",
        name="Worn Acoustic Guitar",
        description="An old, battered acoustic guitar. It has seen better days but still makes a sound. Good for practice or very humble beginnings.",
        gear_type="INSTRUMENT_ACOUSTIC", # More specific
        size=5, # Standard guitar size
        cost=50,
        properties={"acoustic": True, "quality": 0.3} # Quality 0-1 scale
    ),
    "basic_electric_guitar": GearItem(
        item_id="basic_electric_guitar",
        name="Basic Electric Guitar",
        description="A simple but functional Stratocaster-style electric guitar. Needs an amp.",
        gear_type="INSTRUMENT_ELECTRIC", # More specific
        size=5,
        cost=150,
        properties={"electric": True, "quality": 0.5}
    ),
    "practice_amp_small": GearItem(
        item_id="practice_amp_small",
        name="Small Practice Amp (5W)",
        description="A small, low-wattage amplifier. Good for bedroom practice, not loud enough for gigs with a drummer.",
        gear_type="AMPLIFIER",
        size=4, # Smaller than a gig amp
        cost=100,
        properties={"wattage": 5, "quality": 0.4}
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
    "pro_electric_guitar": GearItem(
        item_id="pro_electric_guitar",
        name="Professional Electric Guitar",
        description="A high-quality electric guitar, suitable for large stages.",
        gear_type="INSTRUMENT_ELECTRIC", # More specific type
        size=5,
        cost=1200, # Not buyable yet, but for reference
        properties={"electric": True, "quality": 0.9}
    ),
    "pro_bass_guitar": GearItem(
        item_id="pro_bass_guitar",
        name="Professional Bass Guitar",
        description="A top-tier bass guitar for a solid low end.",
        gear_type="INSTRUMENT_BASS", # New type
        size=6, # Basses can be a bit bigger
        cost=1000,
        properties={"electric": True, "quality": 0.85}
    ),
    "pro_amp_large": GearItem(
        item_id="pro_amp_large",
        name="Large Stage Amp (100W)",
        description="A powerful amplifier for large venues.",
        gear_type="AMPLIFIER",
        size=10,
        cost=800,
        properties={"wattage": 100, "quality": 0.9}
    ),
    "pro_drum_kit": GearItem(
        item_id="pro_drum_kit",
        name="Professional Drum Kit",
        description="A full 5-piece drum kit with cymbals.",
        gear_type="INSTRUMENT_DRUMS", # New type
        size=20, # Very large, player likely won't carry this
        cost=1500,
        properties={"quality": 0.8}
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
        base_sell_price=5 # Sell for a bit more
    ),
}

if __name__ == '__main__':
    # Test that all items can be created and accessed
    assert len(GEAR_CATALOG) == 12 # Updated count (9 + 3 new merch)
    assert GEAR_CATALOG["worn_acoustic_guitar"].name == "Worn Acoustic Guitar"
    assert GEAR_CATALOG["merch_tshirt_basic"].cost == 7
    assert GEAR_CATALOG["merch_tshirt_basic"].base_sell_price == 15
    assert GEAR_CATALOG["merch_poster_small"].size == 0
    assert GEAR_CATALOG["guitar_picks_assorted"].size == 0
    print(f"{len(GEAR_CATALOG)} gear items loaded from catalog.")
    for item_id, item in GEAR_CATALOG.items():
        print(f"- {item_id}: {item.name} (Cost: ${item.cost}, Size: {item.size})")
    print("Gear Catalog basic tests passed.")
