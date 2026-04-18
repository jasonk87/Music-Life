class GearItem:
    def __init__(self, item_id, name, description, gear_type,
                 size=1, cost=0, base_sell_price=0,
                 hunger_reduction=0, energy_boost=0, # Direct params for food
                 properties=None):
        self.item_id = item_id
        self.name = name
        self.description = description
        self.gear_type = gear_type
        self.size = size
        self.cost = cost
        self.base_sell_price = base_sell_price

        self.durability = 100
        self.is_broken = False

        # Food-specific properties
        self.hunger_reduction = hunger_reduction if gear_type == "FOOD" else 0
        self.energy_boost = energy_boost if gear_type == "FOOD" else 0
        # Comfort effect from food could also be a property if desired

        self.properties = properties if properties else {}
        if 'genre_suitability' not in self.properties:
            self.properties['genre_suitability'] = []

        # Store these also in properties dict for consistency if needed by other systems,
        # or if we want to allow defining them via properties dict as a fallback.
        if self.gear_type == "FOOD":
            self.properties['hunger_reduction'] = self.hunger_reduction
            self.properties['energy_boost'] = self.energy_boost

    def get_genre_boost(self, genre):
        """Returns the tone/quality boost this gear provides for a specific genre."""
        if self.is_broken:
            return 0.0
        return self.properties.get('genre_boosts', {}).get(genre, 0.0)

    def take_damage(self, amount: int):
        if self.is_broken: # Cannot damage already broken item further
            return

        self.durability -= amount
        if self.durability <= 0:
            self.durability = 0
            self.is_broken = True
            print(f"Oh no! Your {self.name} broke!")
        # else:
            # print(f"{self.name} took {amount} damage, durability now {self.durability}.") # Optional feedback

    def repair(self):
        self.durability = 100
        self.is_broken = False
        print(f"{self.name} has been repaired to full durability.")

    def condition_description(self):
        if self.is_broken:
            return "Broken"
        if self.durability > 90:
            return "Pristine"
        elif self.durability > 70:
            return "Good"
        elif self.durability > 40:
            return "Worn"
        elif self.durability > 0:
            return "Damaged"
        return "Broken" # Should be caught by is_broken, but as a fallback

    def __str__(self):
        status_part = f"(Dur: {self.durability}/100)"
        if self.is_broken:
            status_part = "(BROKEN)"

        display_string = f"{self.name} {status_part} (Type: {self.gear_type}, Size: {self.size}, Cost: ${self.cost}"
        if self.gear_type == "MERCHANDISE":
            display_string += f", Sells for: ${self.base_sell_price}"
        elif self.gear_type == "FOOD":
            display_string += f", Hunger Red: {self.hunger_reduction}, Energy: +{self.energy_boost}"
        display_string += ")"
        return display_string

    def get_property(self, prop_name):
        return self.properties.get(prop_name)

if __name__ == '__main__':
    # Basic tests for GearItem class
    guitar_strings = GearItem(
        item_id="strings_basic",
        name="Basic Guitar Strings",
        description="A fresh set of steel strings.",
        gear_type="ACCESSORY",
        size=1,
        cost=10
    )
    assert guitar_strings.durability == 100
    assert not guitar_strings.is_broken
    assert str(guitar_strings) == "Basic Guitar Strings (Dur: 100/100) (Type: ACCESSORY, Size: 1, Cost: $10)"
    guitar_strings.take_damage(110)
    assert guitar_strings.is_broken
    assert guitar_strings.durability == 0
    assert "BROKEN" in str(guitar_strings)
    guitar_strings.repair()
    assert not guitar_strings.is_broken
    assert guitar_strings.durability == 100


    acoustic_guitar = GearItem(
        item_id="acoustic_std",
        name="Standard Acoustic Guitar",
        description="A decent quality acoustic guitar, good for practice and small gigs.",
        gear_type="INSTRUMENT_ACOUSTIC", # Updated type
        size=5,
        cost=200,
        properties={"performance_quality_bonus": 0.5, "genre_suitability": ["Folk", "Pop"]}
    )
    assert acoustic_guitar.gear_type == "INSTRUMENT_ACOUSTIC"
    assert "Folk" in acoustic_guitar.get_property("genre_suitability")
    assert "Sells for" not in str(acoustic_guitar)
    acoustic_guitar.take_damage(30)
    assert acoustic_guitar.condition_description() == "Good"
    acoustic_guitar.take_damage(30) # Dur 40
    assert acoustic_guitar.condition_description() == "Worn" # Should be Worn (40 is not > 40)
    acoustic_guitar.take_damage(30) # Dur 10
    assert acoustic_guitar.condition_description() == "Damaged"
    acoustic_guitar.take_damage(10) # Dur 0
    assert acoustic_guitar.condition_description() == "Broken"
    assert acoustic_guitar.is_broken


    merch_shirt = GearItem(
        item_id="merch_shirt_bandlogo",
        name="Band Logo T-Shirt",
        description="A cool black t-shirt with your band's logo.",
        gear_type="MERCHANDISE",
        size=1,
        cost=7, # Player's cost to buy stock
        base_sell_price=20 # Player's price to fans
    )
    assert merch_shirt.gear_type == "MERCHANDISE"
    assert merch_shirt.cost == 7
    assert merch_shirt.base_sell_price == 20
    assert str(merch_shirt) == "Band Logo T-Shirt (Dur: 100/100) (Type: MERCHANDISE, Size: 1, Cost: $7, Sells for: $20)"

    energy_bar = GearItem(
        item_id="food_energy_bar",
        name="Energy Bar",
        description="A compact bar for a quick boost.",
        gear_type="FOOD",
        size=0, cost=3,
        hunger_reduction=15, energy_boost=10
    )
    assert energy_bar.gear_type == "FOOD"
    assert energy_bar.hunger_reduction == 15
    assert energy_bar.energy_boost == 10
    assert str(energy_bar) == "Energy Bar (Dur: 100/100) (Type: FOOD, Size: 0, Cost: $3, Hunger Red: 15, Energy: +10)"

    print("GearItem class basic tests passed.")
