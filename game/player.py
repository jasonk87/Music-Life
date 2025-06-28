class Player:
    def __init__(self, name):
        self.name = name
from game.gear import GearItem # Assuming GearItem is in game/gear.py

class Player:
    def __init__(self, name):
        self.name = name
        self.current_location = None  # City/Location object
        self.current_poi = None       # PointOfInterest object within current_location

        self.skills = {}  # e.g., {"guitar": 10, "vocals": 5}
        self.fame = 0
        self.money = 500 # Starting money

        self.gear_inventory = [] # List of GearItem objects
        self.gear_capacity = 10  # Max total size of gear player can carry

        self.has_manager = False
        self.manager_unlocked_fame_threshold = 200

    def get_current_gear_load(self):
        """Calculates the total size of all gear in the inventory."""
        return sum(item.size for item in self.gear_inventory)

    def can_carry_gear(self, gear_item_or_size):
        """Checks if adding a new item (or a specific size) exceeds capacity."""
        load_to_add = gear_item_or_size.size if isinstance(gear_item_or_size, GearItem) else gear_item_or_size
        return (self.get_current_gear_load() + load_to_add) <= self.gear_capacity

    def add_gear(self, gear_item):
        if not isinstance(gear_item, GearItem):
            print(f"Error: Cannot add '{gear_item}'. Not a valid GearItem.")
            return False
        if self.can_carry_gear(gear_item):
            self.gear_inventory.append(gear_item)
            print(f"{gear_item.name} added to inventory.")
            return True
        else:
            print(f"Cannot carry {gear_item.name}. Not enough capacity. (Load: {self.get_current_gear_load()}/{self.gear_capacity}, Item size: {gear_item.size})")
            return False

    def remove_gear(self, item_id_or_instance):
        item_to_remove = None
        if isinstance(item_id_or_instance, GearItem):
            if item_id_or_instance in self.gear_inventory:
                item_to_remove = item_id_or_instance
        else: # Assume it's an item_id string
            for item in self.gear_inventory:
                if item.item_id == item_id_or_instance:
                    item_to_remove = item
                    break

        if item_to_remove:
            self.gear_inventory.remove(item_to_remove)
            print(f"{item_to_remove.name} removed from inventory.")
            return True
        else:
            print(f"Item '{str(item_id_or_instance)}' not found in inventory.")
            return False

    def practice_skill(self, skill_name, hours):
        if skill_name not in self.skills:
            self.skills[skill_name] = 0
        # Arbitrary skill gain formula, can be refined
        self.skills[skill_name] += hours * 0.1
        print(f"{self.name} practiced {skill_name} for {hours} hours. Skill level is now {self.skills[skill_name]:.1f}.")

    def travel(self, destination_location, travel_time): # This is for inter-city travel
        print(f"{self.name} is travelling from {self.current_location.name if self.current_location else 'Unknown'} to {destination_location.name}...")
        # Simulate time passing
        print(f"Travel took {travel_time} hours.")
        self.current_location = destination_location
        self.current_poi = None # Arriving in a new city, not at a specific POI yet (or maybe at an entry POI like airport/station later)
        print(f"{self.name} has arrived at {destination_location.name}.")

    def travel_within_city(self, destination_poi, time_taken): # New method for intra-city
        if not self.current_location:
            print("Error: Cannot travel within city if not in a city location.")
            return
        print(f"{self.name} is travelling from {self.current_poi.name if self.current_poi else self.current_location.name} to {destination_poi.name} within {self.current_location.name}...")
        print(f"Travel took {time_taken} minutes/hours.") # time_taken unit needs to be consistent
        self.current_poi = destination_poi
        print(f"{self.name} has arrived at {destination_poi.name}.")


    def check_for_manager_unlock(self):
        if not self.has_manager and self.fame >= self.manager_unlocked_fame_threshold:
            self.has_manager = True
            print("\n*** Congratulations! Your fame has grown significantly! ***")
            print("*** You've attracted the attention of a professional artist manager! ***")
            print("*** This will unlock new opportunities. (Manager interactions to be implemented further) ***\n")
            # Future: Trigger an event, introduce the manager NPC, etc.

    def __str__(self):
        location_str = self.current_location.name if self.current_location else "Nowhere"
        poi_str = f" (at {self.current_poi.name})" if self.current_poi else ""
        status = f"Player: {self.name}\n"
        status += f"Location: {location_str}{poi_str}\n"
        status += f"Fame: {self.fame}, Money: ${self.money}\n"
        status += f"Skills: {self.skills}\n"
        status += f"Gear: {len(self.gear_inventory)} items (Load: {self.get_current_gear_load()}/{self.gear_capacity})\n"

        if self.has_manager:
            status += "Manager: Yes"
        else:
            status += f"Manager: No (Unlock at {self.manager_unlocked_fame_threshold} fame)"
        return status

if __name__ == '__main__':
    from game.gear import GearItem # Ensure GearItem is available for tests
    # Basic tests for Player class
    p = Player("Test Dummy")
    assert p.name == "Test Dummy"
    assert p.money == 500
    assert p.fame == 0
    assert not p.has_manager

    p.practice_skill("guitar", 2)
    assert p.skills["guitar"] == 0.2
    p.practice_skill("guitar", 3)
    assert p.skills["guitar"] == 0.5
    p.practice_skill("vocals", 5)
    assert p.skills["vocals"] == 0.5

    p.fame = 200
    p.check_for_manager_unlock()
    assert p.has_manager

    # Mock location and POI for travel test
    class MockLocation: # Represents a City
        def __init__(self, name):
            self.name = name

    class MockPOI: # Represents a Point of Interest
        def __init__(self, name):
            self.name = name

    hometown = MockLocation("Hometown")
    citycenter = MockLocation("City Center")
    p.current_location = hometown
    p.travel(citycenter, 5) # Inter-city travel
    assert p.current_location == citycenter
    assert p.current_poi is None

    home_poi = MockPOI("Player's Apartment")
    shop_poi = MockPOI("Music Shop")
    p.current_poi = home_poi # Set initial POI
    p.travel_within_city(shop_poi, 30) # Intra-city travel
    assert p.current_poi == shop_poi

    # Test Gear Inventory
    assert p.get_current_gear_load() == 0
    assert p.gear_capacity == 10

    strings = GearItem("s001", "Strings", "Guitar strings", "ACCESSORY", 1, 10)
    guitar = GearItem("g001", "Basic Guitar", "An acoustic guitar", "INSTRUMENT", 5, 100)
    amp = GearItem("a001", "Small Amp", "A practice amp", "AMPLIFIER", 7, 150)

    assert p.add_gear(strings)
    assert p.get_current_gear_load() == 1
    assert strings in p.gear_inventory

    assert p.add_gear(guitar)
    assert p.get_current_gear_load() == 6

    assert not p.add_gear(amp) # Should fail, 6 + 7 > 10
    assert p.get_current_gear_load() == 6 # Amp not added
    assert amp not in p.gear_inventory

    p.gear_capacity = 15 # Increase capacity
    assert p.add_gear(amp)
    assert p.get_current_gear_load() == 13

    assert p.remove_gear("g001")
    assert p.get_current_gear_load() == 8
    assert guitar not in p.gear_inventory

    assert not p.remove_gear("non_existent_id")

    print(p) # Check __str__ output
    print("Player class basic tests passed.")
