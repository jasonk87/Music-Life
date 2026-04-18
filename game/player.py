from game.gear import GearItem
from game.player_schedule import PlayerSchedule # Import PlayerSchedule
from game.game_time import current_game_time # Import global game time for start_date
from game.vehicle import Vehicle
from game.band import Band
from game.traits import TRAIT_CATALOG
from game.road_events import generate_road_event
from game.travel_manager import TravelManager
import math
import random

class Player:
    def __init__(self, name):
        self.name = name
        self.current_location = None  # City/Location object
        self.current_poi = None       # PointOfInterest object within current_location

        self.skills = {"songwriting": 5, "guitar": 2, "vocals": 1, "stage_presence": 1, "electronic": 1} # Start with some basic skills
        self.fame = 0
        self.money = 500 # Starting money

        self.gear_inventory = [] # List of GearItem objects
        self.home_storage = [] # List of GearItem objects stored at home
        self.vehicles = []
        self.staff = [] # List of StaffMember objects
        self.merch_stock = [] # List of MerchItem objects
        self.base_gear_capacity = 10 # Base capacity, actual capacity can vary
        self.has_bike = False # Player starts without a bike

        self.energy = 100
        self.stress = 0
        self.homesickness = 0
        self.comfort = 70
        self.hunger = 0 # 0-100, 0 is full, 100 is starving
        self.health = 100

        # Ailments and physical strain
        self.vocal_strain = 0 # 0-100
        self.wrist_strain = 0 # 0-100
        self.substance_dependency = 0 # 0-100

        self.alive = True
        self.cause_of_death = None

        self.songs_written = []
        self.albums_released = [] # List of Album objects
        self.band = None

        self.manager_unlocked_fame_threshold = 200
        self.has_pr_manager = False
        self.pr_manager_fame_requirement_to_hire = 35 # Renamed for clarity with active hiring
        self.has_bodyguard = False
        self.bodyguard_cost = 100

        self.traits = [] # List of Trait objects
        self.inspiration = 0 # 0-100

        self.rented_accommodation_info = None # Stores {"poi_id": str, "checkout_time_obj": GameTime}
        self.has_home = True

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
        self.unpaid_survival_weeks = 0
        self.grit = 0

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
        base_cap = self.base_gear_capacity

        # Roadie Bonus (Staff)
        roadie_bonus = 0
        for s in self.staff:
            if s.role == "Roadie":
                roadie_bonus += s.skill_level * 2 # e.g., Skill 10 -> +20 capacity

        if isinstance(travel_mode, Vehicle):
             return travel_mode.get_max_cargo() + roadie_bonus

        if travel_mode == "walk":
            return max(1, int(base_cap / 2) + int(roadie_bonus / 2)) # Walking reduces capacity, min 1
        elif travel_mode == "bike":
            if self.has_bike:
                return self.base_gear_capacity + int(roadie_bonus / 2)
            else: # Cannot use bike mode if no bike
                return 0 # Or handle error upstream
        elif travel_mode == "taxi": # Taxis can usually carry a good amount of gear
            return (self.base_gear_capacity * 3) + roadie_bonus
        # Default capacity when not specifically traveling or using high-capacity transport (e.g. at home, in a venue)
        # This could also be a very large number if we assume no limit when 'static'.
        # For now, let's assume default is like having access to your "stuff" nearby.
        return (self.base_gear_capacity * 2) + roadie_bonus


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

        # Apply health effect
        health_effect = item.properties.get("health_effect", 0)
        self.health = max(0, min(100, self.health + health_effect))

        # Apply stress effect
        stress_effect = item.properties.get("stress_effect", 0)
        self.stress = max(0, min(100, self.stress + stress_effect))

        # Apply substance dependency
        substance_dependency_effect = item.properties.get("substance_dependency_effect", 0)
        self.substance_dependency = max(0, min(100, self.substance_dependency + substance_dependency_effect))

        msg = f"You ate {item.name}. (Hunger -{old_hunger - self.hunger}, Energy +{self.energy - old_energy})"
        return True, msg

    def add_vehicle(self, vehicle):
        if not isinstance(vehicle, Vehicle):
            print(f"Error: Cannot add '{vehicle}'. Not a valid Vehicle.")
            return False
        # Create a new instance to ensure player's vehicle has its own state (e.g. fuel)
        if hasattr(vehicle, 'clone'):
            new_vehicle = vehicle.clone()
        else:
            # Fallback if clone not available (e.g. older definition loaded)
            new_vehicle = Vehicle(vehicle.name, vehicle.cost, vehicle.speed, vehicle.fuel_capacity, vehicle.fuel_efficiency, vehicle.cargo_capacity, vehicle.reliability, vehicle.condition)

        self.vehicles.append(new_vehicle)
        print(f"{new_vehicle.name} added to your garage.")
        return True

    def stash_item(self, item):
        if item in self.gear_inventory:
            self.gear_inventory.remove(item)
            self.home_storage.append(item)
            return True, f"Stashed {item.name}."
        return False, "Item not found."

    def retrieve_item(self, item):
        if item in self.home_storage:
            if self.can_carry_gear(item):
                self.home_storage.remove(item)
                self.gear_inventory.append(item)
                return True, f"Retrieved {item.name}."
            else:
                return False, "Cannot carry item."
        return False, "Item not in storage."

    def auto_pack(self):
        """Uses Roadies to pack best gear up to capacity."""
        if not any(s.role == "Roadie" for s in self.staff):
            return "You need a Roadie to auto-pack."

        # 1. Stash everything first to start clean (or keep what we have? Clean is safer to ensure optimality)
        # Actually, let's just try to retrieve valuable stuff from home that fits.
        # But if inv is full of junk, we might want to dump junk.
        # Let's dump all to home first.
        self.home_storage.extend(self.gear_inventory)
        self.gear_inventory.clear()

        # 2. Sort all items (now in home_storage) by value
        sorted_items = sorted(self.home_storage, key=lambda x: x.cost, reverse=True)

        # 3. Fill inventory
        cap = self.get_current_gear_capacity()
        current_load = 0
        to_move = []

        for item in sorted_items:
            if current_load + item.size <= cap:
                to_move.append(item)
                current_load += item.size

        for item in to_move:
            self.home_storage.remove(item)
            self.gear_inventory.append(item)

        return f"Roadie auto-packed {len(to_move)} items. Load: {current_load}/{cap}"

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
        # Apply Strain Penalties (practicing with injuries reduces gains)
        strain_penalty = 0.0
        if skill_name == "vocals" and self.vocal_strain > 50:
            strain_penalty = (self.vocal_strain - 50) / 100.0 # Up to 50% penalty
        elif skill_name in ["guitar", "bass", "drums", "keyboard", "electronic"] and self.wrist_strain > 50:
            strain_penalty = (self.wrist_strain - 50) / 100.0

        effective_gain_mult = max(0.1, gain_mult * (1.0 - strain_penalty))
        self.skills[skill_name] += hours * 0.1 * effective_gain_mult
        print(f"{self.name} practiced {skill_name} for {hours} hours. Skill level is now {self.skills[skill_name]:.1f}.")

        # Increase Strain
        if skill_name == "vocals":
            self.vocal_strain = min(100, self.vocal_strain + (hours * 2))
        elif skill_name in ["guitar", "bass", "drums"]:
            self.wrist_strain = min(100, self.wrist_strain + (hours * 1.5))

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


    def start_travel(self, destination_location, distance_km, transport_mode="bus", cost_override=None, ticket_class="economy"):
        """
        Initializes travel. Returns a TravelManager instance if successful, else None.
        """
        print(f"\n{self.name} is preparing to travel from {self.current_location.name if self.current_location else 'Unknown'} to {destination_location.name}...")

        # 1. Capacity Check
        capacity = self.get_current_gear_capacity(transport_mode)
        current_load = self.get_current_gear_load()

        if current_load > capacity:
            print(f"TRAVEL BLOCKED: Your gear load ({current_load}) exceeds the capacity of {transport_mode if isinstance(transport_mode, str) else transport_mode.name} ({capacity}).")
            return None

        # 2. Setup Travel Variables
        cost = 0
        vehicle = None

        # Class multipliers
        class_cost_mult = 1.0
        if ticket_class == "business": class_cost_mult = 2.0
        elif ticket_class == "first": class_cost_mult = 5.0

        if isinstance(transport_mode, Vehicle):
            # Check ownership
            owned_vehicle = None
            if transport_mode in self.vehicles:
                owned_vehicle = transport_mode
            else:
                for v in self.vehicles:
                    if v.name == transport_mode.name:
                        owned_vehicle = v
                        break

            if not owned_vehicle:
                print("Error: You don't own this vehicle.")
                return None

            vehicle = owned_vehicle
            print(f"Driving own vehicle: {vehicle.name}")

        elif transport_mode == "bus":
            cost = distance_km * 0.5 * class_cost_mult
        elif transport_mode == "train":
            cost = distance_km * 1.0 * class_cost_mult
        elif transport_mode == "plane":
            cost = distance_km * 5.0 * class_cost_mult

        if cost_override is not None and not isinstance(transport_mode, Vehicle):
            cost = cost_override * class_cost_mult

        if cost > self.money:
            print(f"TRAVEL BLOCKED: You cannot afford the ticket (${cost}).")
            return None

        self.money -= cost
        if cost > 0:
            print(f"Ticket purchased for ${cost} ({ticket_class}).")

        # Create Manager
        mode_str = transport_mode if isinstance(transport_mode, str) else "car"
        manager = TravelManager(self, destination_location, distance_km, mode_str, ticket_class, vehicle)
        return manager


    def travel_within_city(self, destination_poi, time_taken): # New method for intra-city
        if not self.current_location:
            print("Error: Cannot travel within city if not in a city location.")
            return
        print(f"{self.name} is travelling from {self.current_poi.name if self.current_poi else self.current_location.name} to {destination_poi.name} within {self.current_location.name}...")
        print(f"Travel took {time_taken} minutes/hours.") # time_taken unit needs to be consistent
        self.current_poi = destination_poi
        print(f"{self.name} has arrived at {destination_poi.name}.")


    @property
    def has_manager(self):
        return any(staff.role == "Manager" for staff in self.staff)

    def check_for_manager_unlock(self):
        if not self.has_manager and self.fame >= self.manager_unlocked_fame_threshold:
            from game.staff import StaffMember
            self.staff.append(StaffMember(f"Manager #{len(self.staff)+1}", "Manager", 500, 1))
            print("\n*** Congratulations! Your fame has grown significantly! ***")
            print("*** You've attracted the attention of a professional artist manager! ***")
            print("*** This will unlock new opportunities. (Manager interactions to be implemented further) ***\n")
            # Future: Trigger an event, introduce the manager NPC, etc.

    def check_and_unlock_staff(self):
        """Checks and unlocks staff members like general manager or PR manager based on fame."""
        # Artist Manager
        if not self.has_manager and self.fame >= self.manager_unlocked_fame_threshold:
            from game.staff import StaffMember
            self.staff.append(StaffMember(f"Manager #{len(self.staff)+1}", "Manager", 500, 1))
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
        status += f"Comfort: {self.comfort}/100, Health: {self.health}/100, Homesickness: {self.homesickness}/100\n"
        status += f"Vocal Strain: {self.vocal_strain}/100, Wrist Strain: {self.wrist_strain}/100, Substance Dep: {self.substance_dependency}/100\n"
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
    assert round(p.skills["guitar"], 1) == 2.2
    p.practice_skill("songwriting", 5) # Practice new skill
    assert "songwriting" in p.skills
    assert round(p.skills["songwriting"], 1) == 5.5

    # Add a mock song to test the list (actual song creation is elsewhere)
    class MockSong:
        def __init__(self, title):
            self.title = title
    p.songs_written.append(MockSong("Test Ballad"))
    assert len(p.songs_written) == 1
    assert "Songs Written: 1" in str(p)


    p.practice_skill("guitar", 3)
    assert round(p.skills["guitar"], 1) == 2.5
    p.practice_skill("vocals", 5)
    assert round(p.skills["vocals"], 1) == 1.5

    p.fame = 200
    p.check_for_manager_unlock()
    assert p.has_manager

    # Mock location and POI for travel test
    class MockLocation: # Represents a City
        def __init__(self, name):
            self.name = name
            self.points_of_interest = []
            self.venues = []

    class MockPOI: # Represents a Point of Interest
        def __init__(self, name):
            self.name = name

    hometown = MockLocation("Hometown")
    citycenter = MockLocation("City Center")
    p.current_location = hometown

    # Updated Travel Test
    # p.travel(citycenter, 5) # Old signature
    # New signature: start_travel returns a manager. We simulate it manually here or check init.
    manager = p.start_travel(citycenter, 300, "bus")
    assert manager is not None
    # Simulate completion
    while not manager.is_finished:
        manager.advance_one_hour()
    p.current_location = citycenter # Manually set for test continuity

    # Test Vehicle Travel
    my_van = Vehicle("Tour Van", 2000, 80, 50, 10, 50) # efficient: 10km/l
    p.add_vehicle(my_van)
    p.current_location = hometown # Reset

    manager = p.start_travel(citycenter, 400, my_van) # 400km trip.
    assert manager is not None
    # Need to find the vehicle in player's inventory because add_vehicle clones it
    owned_van = p.vehicles[0]

    # Simulate completion
    while not manager.is_finished:
        manager.advance_one_hour()

    assert owned_van.fuel <= 10 # Started with 50, used ~40.

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

    # Test Vehicle Capacity
    # p.add_vehicle clones the vehicle, so we need to use the owned instance or ensure the test vehicle is considered valid
    # In get_current_gear_capacity, it just reads the object passed.
    assert p.get_current_gear_capacity(my_van) == 50

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
