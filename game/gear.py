class GearItem:
    def __init__(self, item_id, name, description, gear_type, size=1, cost=0, base_sell_price=0, properties=None):
        self.item_id = item_id
        self.name = name
        self.description = description
        self.gear_type = gear_type
        self.size = size
        self.cost = cost # This is player's buy_cost for merch
        self.base_sell_price = base_sell_price # Player's sell_price to fans for merch

        self.properties = properties if properties else {}

    def __str__(self):
        display_string = f"{self.name} (Type: {self.gear_type}, Size: {self.size}, Cost: ${self.cost}"
        if self.gear_type == "MERCHANDISE":
            display_string += f", Sells for: ${self.base_sell_price}"
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
    assert guitar_strings.item_id == "strings_basic"
    assert guitar_strings.name == "Basic Guitar Strings"
    assert guitar_strings.size == 1
    assert guitar_strings.cost == 10
    assert str(guitar_strings) == "Basic Guitar Strings (Type: ACCESSORY, Size: 1, Cost: $10)"
    assert guitar_strings.base_sell_price == 0 # Default

    acoustic_guitar = GearItem(
        item_id="acoustic_std",
        name="Standard Acoustic Guitar",
        description="A decent quality acoustic guitar, good for practice and small gigs.",
        gear_type="INSTRUMENT",
        size=5,
        cost=200,
        properties={"performance_quality_bonus": 0.5, "type_played": "acoustic"}
    )
    assert acoustic_guitar.gear_type == "INSTRUMENT"
    assert acoustic_guitar.size == 5
    assert acoustic_guitar.get_property("performance_quality_bonus") == 0.5
    assert acoustic_guitar.get_property("type_played") == "acoustic"
    assert acoustic_guitar.get_property("non_existent_prop") is None
    assert "Sells for" not in str(acoustic_guitar) # Not merchandise

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
    assert str(merch_shirt) == "Band Logo T-Shirt (Type: MERCHANDISE, Size: 1, Cost: $7, Sells for: $20)"

    print("GearItem class basic tests passed.")
