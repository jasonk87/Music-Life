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
        self.base_gear_capacity = 10 # Base capacity, actual capacity can vary
        self.has_bike = False # Player starts without a bike

        self.energy = 100 # Max 100
        self.stress = 0   # Max 100 (lower is better)
        self.homesickness = 0 # 0-100, higher is worse
        self.comfort = 70     # 0-100, higher is better (start reasonably comfy at home)

        self.songs_written = [] # List of Song objects

        self.has_manager = False
        self.manager_unlocked_fame_threshold = 200

        self.rented_accommodation_info = None # Stores {"poi_id": str, "checkout_time_obj": GameTime}

    def get_current_gear_capacity(self, travel_mode=None):
        """Calculates current gear capacity based on situation or travel mode."""
        if travel_mode == "walk":
            return max(1, int(self.base_gear_capacity / 2)) # Walking reduces capacity, min 1
        elif travel_mode == "bike":
            if self.has_bike:
                return self.base_gear_capacity
            else: # Cannot use bike mode if no bike
                return 0 # Or handle error upstream
        elif travel_mode == "taxi": # Taxis can usually carry a good amount of gear
            return self.base_gear_capacity * 3
        # Default capacity when not specifically traveling or using high-capacity transport (e.g. at home, in a venue)
        # This could also be a very large number if we assume no limit when 'static'.
        # For now, let's assume default is like having access to your "stuff" nearby.
        return self.base_gear_capacity * 2


    def get_current_gear_load(self):
        """Calculates the total size of all gear in the inventory."""
        return sum(item.size for item in self.gear_inventory)

    def can_carry_gear(self, gear_item_or_size):
        """Checks if adding a new item (or a specific size) exceeds default/current non-travel capacity."""
        load_to_add = gear_item_or_size.size if isinstance(gear_item_or_size, GearItem) else gear_item_or_size
        # Use default capacity (travel_mode=None) for general inventory checks
        return (self.get_current_gear_load() + load_to_add) <= self.get_current_gear_capacity()

    def add_gear(self, gear_item):
        if not isinstance(gear_item, GearItem):
            print(f"Error: Cannot add '{gear_item}'. Not a valid GearItem.")
            return False
        if self.can_carry_gear(gear_item): # Checks against default capacity
            self.gear_inventory.append(gear_item)
            print(f"{gear_item.name} added to inventory.")
            return True
        else:
            default_capacity = self.get_current_gear_capacity()
            print(f"Cannot carry {gear_item.name}. Not enough capacity. (Load: {self.get_current_gear_load()}/{default_capacity}, Item size: {gear_item.size})")
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

        # Gear wear from practice
        # Determine relevant gear type for the skill
        instrument_type_for_skill = None
        if skill_name == "guitar": # This could map to multiple types if player has options
            # Prefer electric if owned and not broken, else acoustic for "guitar" skill.
            # This simplistic check means any owned non-broken guitar might wear.
            # A more complex system would have player "equip" an item for practice.
            if any(g.gear_type == "INSTRUMENT_ELECTRIC" and not g.is_broken for g in self.gear_inventory):
                instrument_type_for_skill = "INSTRUMENT_ELECTRIC"
            elif any(g.gear_type == "INSTRUMENT_ACOUSTIC" and not g.is_broken for g in self.gear_inventory):
                instrument_type_for_skill = "INSTRUMENT_ACOUSTIC"
        elif skill_name == "bass":
            instrument_type_for_skill = "INSTRUMENT_BASS"
        elif skill_name == "drums":
            instrument_type_for_skill = "INSTRUMENT_DRUMS"
        # Add other instrument skills here (piano, etc.)

        if instrument_type_for_skill:
            practiced_instrument = None
            for item in self.gear_inventory:
                if item.gear_type == instrument_type_for_skill and not item.is_broken:
                    practiced_instrument = item
                    break # Use the first available, non-broken instrument of the type

            if practiced_instrument:
                damage = hours * 1 # 1 durability damage per hour of practice
                practiced_instrument.take_damage(damage)
                print(f"Your {practiced_instrument.name} took some wear from practice. Durability: {practiced_instrument.durability}/100.")
                if practiced_instrument.is_broken:
                    print(f"Your {practiced_instrument.name} broke from intense practice!")
            else:
                print(f"You need a working {instrument_type_for_skill.lower().replace('_', ' ')} to practice {skill_name} effectively.")
                # Consider reducing skill gain effectiveness here in the future


    def travel(self, destination_location, travel_time): # This is for inter-city travel
        print(f"{self.name} is travelling from {self.current_location.name if self.current_location else 'Unknown'} to {destination_location.name}...")
        # Simulate time passing
        print(f"Travel took {travel_time} hours.")
        self.current_location = destination_location

        # Attempt to set current_poi to a relevant transport hub in the new city
        # This assumes inter-city travel implies arriving at such a hub.
        # The mode of travel isn't passed here, so we make a best guess.
        arrival_poi = None
        if destination_location and (hasattr(destination_location, 'points_of_interest') or hasattr(destination_location, 'venues')):
            all_pois_in_dest = destination_location.points_of_interest + destination_location.venues

            # Prioritize Airport if it exists, then Bus Station
            for poi_category_priority in ["TRANSPORT_AIRPORT", "TRANSPORT_BUS"]:
                for poi in all_pois_in_dest:
                    if hasattr(poi, 'category') and poi.category == poi_category_priority:
                        arrival_poi = poi
                        break
                if arrival_poi:
                    break

        self.current_poi = arrival_poi # Could be None if no suitable hub found

        # Update energy and stress due to travel
        # travel_time is in hours for inter-city
        stress_increase = travel_time * 2 # Example: +2 stress per hour
        energy_decrease = travel_time * 3 # Example: -3 energy per hour

        self.stress = min(100, self.stress + stress_increase)
        self.energy = max(0, self.energy - energy_decrease)

        arrival_poi_name = f"at {arrival_poi.name}" if arrival_poi else "at the city outskirts"
        print(f"{self.name} has arrived in {destination_location.name} ({arrival_poi_name}).")
        print(f"The journey was tiring. (Stress: +{stress_increase}, Energy: -{energy_decrease})")


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
        status += f"Energy: {self.energy}/100, Stress: {self.stress}/100\n"
        status += f"Comfort: {self.comfort}/100, Homesickness: {self.homesickness}/100\n"
        status += f"Skills: {self.skills}\n"
        status += f"Songs Written: {len(self.songs_written)}\n"
        status += f"Gear: {len(self.gear_inventory)} items (Load: {self.get_current_gear_load()}/{self.get_current_gear_capacity()})\n"
        status += f"Has Bike: {'Yes' if self.has_bike else 'No'}\n"

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
    assert p.energy == 100
    assert p.stress == 0
    assert p.homesickness == 0
    assert p.comfort == 70
    assert not p.has_manager
    assert len(p.songs_written) == 0

    p.practice_skill("guitar", 2)
    assert p.skills["guitar"] == 0.2
    p.practice_skill("songwriting", 5) # Practice new skill
    assert "songwriting" in p.skills
    assert p.skills["songwriting"] == 0.5

    # Add a mock song to test the list (actual song creation is elsewhere)
    class MockSong:
        def __init__(self, title):
            self.title = title
    p.songs_written.append(MockSong("Test Ballad"))
    assert len(p.songs_written) == 1
    assert "Songs Written: 1" in str(p)


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
    # Test default capacity (travel_mode=None gives base_gear_capacity * 2 = 20 for default base of 10)
    assert p.get_current_gear_capacity() == 20
    assert p.base_gear_capacity == 10 # Check base
    assert not p.has_bike

    # Test mode-specific capacities
    assert p.get_current_gear_capacity("walk") == 5 # base_gear_capacity / 2
    assert p.get_current_gear_capacity("bike") == 0 # No bike yet
    p.has_bike = True
    assert p.get_current_gear_capacity("bike") == 10 # With bike, it's base_gear_capacity
    assert p.get_current_gear_capacity("taxi") == 30 # base_gear_capacity * 3

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

    # Test adding when capacity is based on default (travel_mode=None, capacity = 20)
    p.base_gear_capacity = 10 # Reset for clarity, default capacity is 20
    p.gear_inventory = [strings, guitar] # Load is 1+5=6
    assert p.get_current_gear_load() == 6

    # Amp size is 7. 6 + 7 = 13. Default capacity is 20. So this should pass.
    assert p.add_gear(amp)
    assert p.get_current_gear_load() == 13
    assert amp in p.gear_inventory

    # Another amp would be 13 + 7 = 20. Should pass.
    amp2 = GearItem("a002", "Second Amp", "Another practice amp", "AMPLIFIER", 7, 150)
    assert p.add_gear(amp2)
    assert p.get_current_gear_load() == 20

    # One more small item (size 1) should fail (20+1 > 20)
    extra_strings = GearItem("s002", "Extra Strings", "More strings", "ACCESSORY", 1, 10)
    assert not p.add_gear(extra_strings)
    assert p.get_current_gear_load() == 20


    assert p.remove_gear("g001")
    assert p.get_current_gear_load() == 8
    assert guitar not in p.gear_inventory

    assert not p.remove_gear("non_existent_id")

    print(p) # Check __str__ output
    print("Player class basic tests passed.")
