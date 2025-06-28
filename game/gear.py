class GearItem:
    def __init__(self, item_id, name, description, gear_type, size=1, cost=0, properties=None):
        self.item_id = item_id        # Unique identifier, e.g., "acoustic_guitar_basic"
        self.name = name              # Player-facing name, e.g., "Basic Acoustic Guitar"
        self.description = description
        self.gear_type = gear_type    # String like "INSTRUMENT", "ACCESSORY", "AMPLIFIER"
        self.size = size              # Integer representing space/weight for inventory capacity
        self.cost = cost              # Purchase price

        # Properties: dict for special effects, e.g., {"skill_bonus": {"guitar": 1}}
        self.properties = properties if properties else {}

    def __str__(self):
        return f"{self.name} (Type: {self.gear_type}, Size: {self.size}, Cost: ${self.cost})"

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

    print("GearItem class basic tests passed.")
