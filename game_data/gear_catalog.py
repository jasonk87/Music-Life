from game.gear import GearItem # Assuming GearItem class is in game/gear.py

GEAR_CATALOG = {
    "worn_acoustic_guitar": GearItem(
        item_id="worn_acoustic_guitar",
        name="Worn Acoustic Guitar",
        description="An old, battered acoustic guitar. It has seen better days but still makes a sound. Good for practice or very humble beginnings.",
        gear_type="INSTRUMENT",
        size=5, # Standard guitar size
        cost=50,
        properties={"acoustic": True, "quality": 0.3} # Quality 0-1 scale
    ),
    "basic_electric_guitar": GearItem(
        item_id="basic_electric_guitar",
        name="Basic Electric Guitar",
        description="A simple but functional Stratocaster-style electric guitar. Needs an amp.",
        gear_type="INSTRUMENT",
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
    # Future items could include:
    # "decent_acoustic_guitar", "pro_electric_guitar", "gig_amp_50w",
    # "effect_pedal_distortion", "effect_pedal_delay", "microphone_basic",
    # "drum_sticks", "keyboard_portable"
}

if __name__ == '__main__':
    # Test that all items can be created and accessed
    assert len(GEAR_CATALOG) == 5
    assert GEAR_CATALOG["worn_acoustic_guitar"].name == "Worn Acoustic Guitar"
    assert GEAR_CATALOG["practice_amp_small"].cost == 100
    assert GEAR_CATALOG["guitar_picks_assorted"].size == 0
    print(f"{len(GEAR_CATALOG)} gear items loaded from catalog.")
    for item_id, item in GEAR_CATALOG.items():
        print(f"- {item_id}: {item.name} (Cost: ${item.cost}, Size: {item.size})")
    print("Gear Catalog basic tests passed.")
