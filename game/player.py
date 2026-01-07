from game.gear import GearItem
from game.player_schedule import PlayerSchedule # Import PlayerSchedule
from game.game_time import current_game_time # Import global game time for start_date
from game.vehicle import Vehicle
from game.band import Band
from game.traits import TRAIT_CATALOG

class Player:
    def __init__(self, name):
        self.name = name
        self.current_location = None  # City/Location object
        self.current_poi = None       # PointOfInterest object within current_location

        self.skills = {"songwriting": 5, "guitar": 2, "vocals": 1, "stage_presence": 1, "electronic": 1} # Start with some basic skills
        self.fame = 0
        self.money = 500 # Starting money

        self.gear_inventory = [] # List of GearItem objects
        self.vehicles = []
        self.base_gear_capacity = 10 # Base capacity, actual capacity can vary
        self.has_bike = False # Player starts without a bike

        self.energy = 100
        self.stress = 0
        self.homesickness = 0
        self.comfort = 70
        self.hunger = 0 # 0-100, 0 is full, 100 is starving

        self.songs_written = []
        self.band = None

        self.has_manager = False
        self.manager_unlocked_fame_threshold = 200
        self.has_pr_manager = False
        self.pr_manager_fame_requirement_to_hire = 60 # Renamed for clarity with active hiring
        self.has_bodyguard = False
        self.bodyguard_cost = 100

        self.traits = [] # List of Trait objects
        self.inspiration = 0 # 0-100

        self.rented_accommodation_info = None # Stores {"poi_id": str, "checkout_time_obj": GameTime}

        # Opportunities - this will store various types of opportunities
        # For interviews, the key could be like "interview_city_chronicle"
        # Value could be "available", "pending_player_action", "completed"
        self.active_opportunities = {
            # Example: "interview_city_chronicle": "available"
        }

        self.schedule = PlayerSchedule() # Initialize schedule
        self.contacts = [] # List of dictionaries: {'npc_id': 'id', 'name': 'NPC Name', 'notes': 'Optional notes'}

        # HUD Related Attributes
        self.age = 18 # Starting age (this will be the initial_age for calculation)
        self.hair_length = 3 # Numerical: 0 (Bald/Shaved) to 10 (Very Long)
        self.beard_length = 0 # Numerical: 0 (Clean-shaven) to 10 (Very Long Beard)
        self.start_date = current_game_time.copy() # Set player's start date to current game time

        self.hair_growth_progress = 0.0 # Accumulates points towards next length level
        self.beard_growth_progress = 0.0 # Accumulates points towards next length level

        self.active_tour_offer = None # Stores details of a tour package offered by manager
        self.completed_tour_ids = [] # List of tour_ids the player has completed
        self.current_tour_id = None   # ID of the currently active tour
        self.tour_ledgers = {}        # Dict to store financial details of tours: tour_id -> {"name": "Tour Name", "expenses": 0, "income": 0, "status": "ongoing/completed", "gigs_details": []}

        # Constants for growth mechanics (can be tuned)
        self.HAIR_POINTS_PER_LENGTH_LEVEL = 100.0 # How many progress points to gain one length level for hair
        self.BEARD_POINTS_PER_LENGTH_LEVEL = 80.0 # How many progress points to gain one length level for beard
        self.MAX_HAIR_LENGTH = 10
        self.MAX_BEARD_LENGTH = 10

        self.feedback_received = [] # List to store feedback/review dictionaries

        # Music income tracking
        self.last_week_music_income = 0
        self.total_music_income_to_date = 0

        # Label deal tracking
        self.pending_contracts = []
        self.signed_label_deal = None # Stores details of the accepted contract
        self.label_history = [] # List to store past (fulfilled, breached, dropped) contracts


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

    def consume_item(self, item):
        if item not in self.gear_inventory:
            return False, "Item not in inventory."

        if item.gear_type != "FOOD":
            return False, "You can't eat that!"

        self.gear_inventory.remove(item)

        # Apply effects
        old_hunger = self.hunger
        old_energy = self.energy

        self.hunger = max(0, self.hunger - item.hunger_reduction)
        self.energy = min(100, self.energy + item.energy_boost)

        # Apply comfort if present
        comfort_effect = item.properties.get("comfort_effect", 0)
        self.comfort = max(0, min(100, self.comfort + comfort_effect))

        msg = f"You ate {item.name}. (Hunger -{old_hunger - self.hunger}, Energy +{self.energy - old_energy})"
        return True, msg

    def add_vehicle(self, vehicle):
        if not isinstance(vehicle, Vehicle):
            print(f"Error: Cannot add '{vehicle}'. Not a valid Vehicle.")
            return False
        # Create a new instance to ensure player's vehicle has its own state (e.g. fuel)
        new_vehicle = Vehicle(vehicle.name, vehicle.cost, vehicle.speed, vehicle.fuel_capacity, vehicle.fuel_efficiency)
        self.vehicles.append(new_vehicle)
        print(f"{new_vehicle.name} added to your garage.")
        return True

    def has_trait(self, trait_id):
        return any(t.id == trait_id for t in self.traits)

    def get_trait_multiplier(self, effect_type, default=1.0):
        mult = default
        for t in self.traits:
            if t.effect_type == effect_type:
                mult *= t.effect_value
        return mult

    def practice_skill(self, skill_name, hours):
        if skill_name not in self.skills:
            self.skills[skill_name] = 0

        # Apply Trait Multiplier
        gain_mult = self.get_trait_multiplier("skill_gain_mult")

        # Arbitrary skill gain formula, can be refined
        self.skills[skill_name] += hours * 0.1 * gain_mult
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

    def check_and_unlock_staff(self):
        """Checks and unlocks staff members like general manager or PR manager based on fame."""
        # Artist Manager
        if not self.has_manager and self.fame >= self.manager_unlocked_fame_threshold:
            self.has_manager = True
            print("\n*** Congratulations! Your fame has grown significantly! ***")
            print("*** You've attracted the attention of a professional Artist Manager! ***")
            print("*** They can help guide your career and open new doors. (Manager interactions to be implemented further) ***\n")

        # PR Manager - This automatic unlock is removed. Hiring is now an active player choice.
        # if not self.has_pr_manager and self.fame >= self.pr_manager_unlock_fame_threshold:
        #     self.has_pr_manager = True
        #     print("\n*** Your Buzz is Growing! ***")
        #     print("A specialist PR Manager has taken notice and offered their services!")
        #     print("They can help you find media opportunities like interviews. Check in with them via 'Staff Actions'.\n")
        pass # Placeholder if other staff types are added here later for auto-unlock

    # Removed old check_for_interview_opportunities as it's now PR manager driven / active hiring.

    def __str__(self):
        location_str = self.current_location.name if self.current_location else "Nowhere"
        poi_str = f" (at {self.current_poi.name})" if self.current_poi else ""
        status = f"Player: {self.name}\n"
        status += f"Location: {location_str}{poi_str}\n"
        status += f"Fame: {self.fame}, Money: ${self.money}\n"
        status += f"Energy: {self.energy}/100, Stress: {self.stress}/100, Hunger: {self.hunger}/100\n"
        status += f"Comfort: {self.comfort}/100, Homesickness: {self.homesickness}/100\n"
        status += f"Skills: {self.skills}\n"
        status += f"Songs Written: {len(self.songs_written)}\n"
        status += f"Gear: {len(self.gear_inventory)} items (Load: {self.get_current_gear_load()}/{self.get_current_gear_capacity()})\n"
        status += f"Vehicles: {', '.join([v.name for v in self.vehicles]) if self.vehicles else 'None'}\n"
        status += f"Has Bike: {'Yes' if self.has_bike else 'No'}\n"

        if self.has_manager:
            status += "\nArtist Manager: Yes"
        else:
            status += f"\nArtist Manager: No (Unlock at {self.manager_unlocked_fame_threshold} fame)"

        if self.has_pr_manager:
            status += "\nPR Manager: Yes"
        else:
            status += f"\nPR Manager: No (Requires ~{self.pr_manager_fame_requirement_to_hire} Fame to hire)" # Corrected attribute

        # Could add a count of upcoming scheduled items if desired
        # status += f"\nUpcoming Scheduled Items: {len(self.schedule.get_upcoming_events(current_game_time_needs_to_be_passed_or_imported))}"
        return status

if __name__ == '__main__':
    from game.gear import GearItem # Ensure GearItem is available for tests
    from game.game_time import GameTime # For schedule testing
    # Basic tests for Player class
    p = Player("Test Dummy")
    assert p.name == "Test Dummy"
    assert p.money == 500
    assert p.fame == 0
    assert p.energy == 100
    assert p.stress == 0
    assert p.homesickness == 0
    assert p.comfort == 70
    assert p.hunger == 0
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
    assert p.get_current_gear_load() == 6 # Load: strings (1) + guitar (5) = 6

    # Current default capacity is base_gear_capacity * 2 = 10 * 2 = 20
    # Adding amp (size 7): 6 + 7 = 13. 13 <= 20, so this should succeed.
    assert p.add_gear(amp)
    assert p.get_current_gear_load() == 13 # Load: 6 + amp (7) = 13
    assert amp in p.gear_inventory

    # The following lines from the original test are now redundant or incorporated above.
    # # Test adding when capacity is based on default (travel_mode=None, capacity = 20)
    # p.base_gear_capacity = 10 # Reset for clarity, default capacity is 20
    # p.gear_inventory = [strings, guitar] # Load is 1+5=6
    # assert p.get_current_gear_load() == 6
    #
    # # Amp size is 7. 6 + 7 = 13. Default capacity is 20. So this should pass.
    # assert p.add_gear(amp)
    # assert p.get_current_gear_load() == 13
    # assert amp in p.gear_inventory

    # Another amp (size 7) would make load 13 + 7 = 20. Should pass.
    amp2 = GearItem("a002", "Second Amp", "Another practice amp", "AMPLIFIER", 7, 150)
    assert p.add_gear(amp2)
    assert p.get_current_gear_load() == 20

    # One more small item (size 1) should fail (20+1 > 20)
    extra_strings = GearItem("s002", "Extra Strings", "More strings", "ACCESSORY", 1, 10)
    assert not p.add_gear(extra_strings)
    assert p.get_current_gear_load() == 20


    assert p.remove_gear("g001") # Removes guitar (size 5). Load was 20. New load = 20 - 5 = 15.
    assert p.get_current_gear_load() == 15
    assert guitar not in p.gear_inventory

    assert not p.remove_gear("non_existent_id")

    # Test PlayerSchedule initialization
    assert isinstance(p.schedule, PlayerSchedule)
    assert len(p.schedule.scheduled_items) == 0
    # Add a test event to schedule
    test_start_time = GameTime(2024, 1, 1, 10, 0)
    test_end_time = GameTime(2024, 1, 1, 12, 0)
    p.schedule.add_event(test_start_time, test_end_time, "Test Event", "Test")
    assert len(p.schedule.scheduled_items) == 1
    assert p.schedule.scheduled_items[0].description == "Test Event"
    print("\nPlayer Schedule Test:")
    for item in p.schedule.scheduled_items:
        print(item)


    print(p) # Check __str__ output
    assert "PR Manager: No" in str(p) # Verify new __str__ components
    print("Player class basic tests passed.")
