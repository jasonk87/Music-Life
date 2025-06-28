class Event:
    EVENT_TYPES = {
        "OPEN_MIC": {"base_fame": 10, "base_payout": 50, "skill_multiplier": 1.0},
        "CLUB_GIG": {"base_fame": 50, "base_payout": 250, "skill_multiplier": 1.5},
        "CONCERT": {"base_fame": 200, "base_payout": 1000, "skill_multiplier": 2.0},
        "FESTIVAL_SLOT": {"base_fame": 500, "base_payout": 3000, "skill_multiplier": 2.5}
    }

    def __init__(self, name, location, event_type="OPEN_MIC", required_skills=None,
                 required_gear_types=None, # New attribute
                 description="", specific_fame_reward=None, specific_payout=None):
        self.name = name
        self.location = location # Venue or Location object
        self.event_type = event_type
        self.required_gear_types = required_gear_types if required_gear_types else []

        type_details = Event.EVENT_TYPES.get(event_type, Event.EVENT_TYPES["OPEN_MIC"])

        self.required_skills = required_skills if required_skills else {} # e.g., {"guitar": 5}
        # Adjust required skills based on event type, e.g. higher for concerts
        for skill in list(self.required_skills.keys()): # Iterate over a copy of keys
            self.required_skills[skill] = max(1, int(self.required_skills[skill] * type_details["skill_multiplier"]))

        self.fame_reward = specific_fame_reward if specific_fame_reward is not None else type_details["base_fame"]
        self.payout = specific_payout if specific_payout is not None else type_details["base_payout"] # Assuming we'll add money later

        self.description = description
        self.is_active = True
        self.preparation_tasks_required = {} # e.g., {"rehearse_setlist": False, "promote_show": False}
        self.preparation_complete = False # Player must complete tasks before performing

    def are_preparations_complete(self):
        if not self.preparation_tasks_required:
            return True
        return all(self.preparation_tasks_required.values())

    def complete_preparation_task(self, task_name):
        if task_name in self.preparation_tasks_required:
            self.preparation_tasks_required[task_name] = True
            print(f"Preparation task '{task_name}' for '{self.name}' completed.")
            if self.are_preparations_complete():
                self.preparation_complete = True
                print(f"All preparations for '{self.name}' are complete!")
            return True
        print(f"Task '{task_name}' not found or already completed for this event.")
        return False

    def can_perform(self, player):
        if not self.is_active:
            return False, "This event is no longer active."

        if not self.are_preparations_complete():
            pending_tasks = [task for task, completed in self.preparation_tasks_required.items() if not completed]
            return False, f"Event preparations are not complete. Pending: {', '.join(pending_tasks)}"

        for skill, required_level in self.required_skills.items():
            if player.skills.get(skill, 0) < required_level:
                return False, f"Player does not meet skill requirement for {skill} (needs {required_level}, has {player.skills.get(skill, 0)}).", False

        # Gear check
        gear_ok, gear_message, needs_rental = self._check_gear_requirements(player)
        if not gear_ok:
            return False, gear_message, needs_rental # needs_rental might be true if partial rental was possible but other gear missing

        return True, "Player meets all requirements.", needs_rental

    def _check_gear_requirements(self, player):
        """
        Checks if the player has the required gear types or can rent them from the venue.
        Returns: (bool_can_perform, message_str, bool_needs_rental)
        """
        if not self.required_gear_types:
            return True, "No specific gear required.", False # No gear needed

        from game_data.gear_catalog import GEAR_CATALOG # Import locally to avoid circular dependency issues at module load time

        player_gear_types_owned = set()
        for item in player.gear_inventory:
            player_gear_types_owned.add(item.gear_type)

        missing_gear_messages = []
        actually_needs_rental_for_event = False

        for req_type in self.required_gear_types:
            if req_type not in player_gear_types_owned:
                # Player doesn't own this type of gear. Can it be rented?
                venue = self.location # Assuming event.location is always a Venue object for events requiring gear
                if hasattr(venue, 'can_rent_gear') and venue.can_rent_gear:
                    # Check if venue has this type of gear available for rent
                    can_rent_this_type = False
                    for item_id in venue.available_rental_gear_ids:
                        rental_item = GEAR_CATALOG.get(item_id)
                        if rental_item and rental_item.gear_type == req_type:
                            can_rent_this_type = True
                            break

                    if can_rent_this_type:
                        actually_needs_rental_for_event = True
                        # Player can rent this type, so requirement is met via rental.
                        # print(f"DEBUG: Player can rent {req_type} at {venue.name}.") # Optional debug
                        continue # Move to next required gear type
                    else:
                        missing_gear_messages.append(f"Missing {req_type} (venue does not rent this type).")
                else: # Venue doesn't rent gear or is not a proper venue object
                    missing_gear_messages.append(f"Missing {req_type} (rental not possible/available at venue).")
            # Else: player owns this gear type, requirement met.

        if missing_gear_messages:
            return False, "Missing required gear: " + ", ".join(missing_gear_messages), actually_needs_rental_for_event

        return True, "All gear requirements met (owned or rentable).", actually_needs_rental_for_event


    def perform_event(self, player):
        # The needs_rental flag is now passed from can_perform
        can_perform, message, needs_rental = self.can_perform(player)
        if not can_perform:
            print(f"Cannot perform {self.name}: {message}")
            return False

        print(f"{player.name} is performing at {self.name} at {self.location.name}!")
import random # Needed for incident chance

# ... (rest of the class definition up to perform_event)

    def perform_event(self, player):
        # The needs_rental flag is now passed from can_perform
        can_perform, message, needs_rental = self.can_perform(player)
        if not can_perform:
            print(f"Cannot perform {self.name}: {message}")
            return False

        print(f"{player.name} is performing at {self.name} at {self.location.name}!")
        # Add more event logic here (e.g., minigame, skill checks for quality)
        print(f"The event was a success!")

        # --- Gear Incident Chance ---
        incident_chance = 0.10 # 10% chance of a gear incident
        if random.random() < incident_chance:
            # Identify player's owned gear that could be relevant (instruments, amps)
            relevant_owned_gear = [
                item for item in player.gear_inventory
                if item.gear_type.startswith("INSTRUMENT") or item.gear_type == "AMPLIFIER"
            ]
            if relevant_owned_gear:
                affected_gear = random.choice(relevant_owned_gear)
                repair_cost = random.randint(5, 25) # Random repair cost

                incident_description = "had a minor issue" # Default fallback
                gt = affected_gear.gear_type
                if gt == "AMPLIFIER":
                    incident_description = "a tube blew"
                elif gt == "INSTRUMENT_ACOUSTIC":
                    incident_description = "a string snapped"
                elif gt == "INSTRUMENT_ELECTRIC" or gt == "INSTRUMENT_BASS":
                    incident_description = "a cable shorted out or a knob came loose"
                elif gt == "INSTRUMENT_DRUMS":
                    incident_description = "a drum skin split or a cymbal cracked"

                print(f"\nOh no! During the performance, your {affected_gear.name} had an issue ({incident_description})!")
                print(f"Immediate repair/replacement cost: ${repair_cost}.")

                if player.money >= repair_cost:
                    player.money -= repair_cost
                    print(f"${repair_cost} deducted for repairs.")
                else:
                    print(f"You couldn't afford the immediate ${repair_cost} repair. This might cause issues later!")
                    # Player money doesn't go negative for this simple incident for now.
                    # Or: player.money -= repair_cost (allowing negative)
                    # Or: Store as debt (more complex)
            else:
                # Player owns no relevant gear (maybe rented everything or it's a vocals-only event)
                # Could have a non-gear incident like "mic feedback" or "sore throat" here.
                # For now, if no player-owned gear, no player-gear-damage incident.
                print("\nLuckily, all your owned gear made it through the performance unscathed (or you didn't use any!).")

        # --- Payout and Fame ---
        if needs_rental:
            venue = self.location
            if hasattr(venue, 'can_rent_gear') and venue.can_rent_gear and venue.gear_rental_fee > 0:
                player.money -= venue.gear_rental_fee
                print(f"A gear rental fee of ${venue.gear_rental_fee} was deducted.")

        player.fame += self.fame_reward
        player.money += self.payout

        # --- Sell Merchandise Phase ---
        player_merch_items = [item for item in player.gear_inventory if item.gear_type == "MERCHANDISE"]
        if player_merch_items:
            print("\n--- Sell Merchandise ---")
            # Consolidate merch by item_id for selling choice
            sellable_merch_summary = {}
            for item in player_merch_items:
                if item.item_id not in sellable_merch_summary:
                    sellable_merch_summary[item.item_id] = {"name": item.name, "sell_price": item.base_sell_price, "stock": 0, "item_template": item}
                sellable_merch_summary[item.item_id]["stock"] += 1

            if not sellable_merch_summary: # Should not happen if player_merch_items is not empty
                print("No merchandise available to sell.")
            else:
                print("You have some merchandise to sell:")
                merch_options_list = []
                merch_map = {} # Maps choice index to item_id
                choice_idx = 1
                for item_id, details in sellable_merch_summary.items():
                    merch_options_list.append(f"{details['name']} (Stock: {details['stock']}, Sell Price: ${details['sell_price']})")
                    merch_map[str(choice_idx)] = item_id
                    choice_idx +=1
                merch_options_list.append("Don't sell anything now.")

                # Using game.main.present_choices requires importing it or moving it to a shared util
                # For now, simulate a simple input choice for this event-specific interaction
                # This part would ideally use the main loop's present_choices
                for i, option_text in enumerate(merch_options_list):
                    print(f"{i+1}. {option_text}")

                merch_sell_choice_str = input("Choose merch to sell (number) or pass: ")

                if merch_sell_choice_str.isdigit():
                    chosen_option_idx = int(merch_sell_choice_str)
                    if chosen_option_idx > 0 and chosen_option_idx <= len(sellable_merch_summary): # Check if a merch item was chosen
                        chosen_item_id_to_sell = merch_map[str(chosen_option_idx)]
                        item_details = sellable_merch_summary[chosen_item_id_to_sell]
                        item_template = item_details["item_template"] # The actual GearItem template

                        # Sales calculation (simplified)
                        venue_capacity = self.location.capacity if hasattr(self.location, 'capacity') else 50 # Default if not a venue
                        # Fame factor: 0.0 to 2.0 (for fame 0 to 1000). Min 0.01 interest.
                        fame_effect = (player.fame / 500.0) if player.fame > 0 else 0.0
                        base_interest_pct = 0.01 + fame_effect * 0.05 # Base 1% + up to 10% from fame (max 11% of capacity)

                        # Random sales percentage of interested people (e.g. 10% to 50% of those interested might buy)
                        random_sales_conversion_pct = random.uniform(0.1, 0.5)

                        potential_buyers = int(venue_capacity * base_interest_pct)
                        potential_sales_units = int(potential_buyers * random_sales_conversion_pct)

                        actual_sales_units = min(potential_sales_units, item_details["stock"])

                        if actual_sales_units > 0:
                            earnings = actual_sales_units * item_template.base_sell_price
                            player.money += earnings

                            # Remove sold items from player inventory (one by one)
                            items_removed_count = 0
                            temp_inventory = list(player.gear_inventory) # Iterate over a copy
                            for item_instance in temp_inventory:
                                if items_removed_count < actual_sales_units and item_instance.item_id == chosen_item_id_to_sell:
                                    player.remove_gear(item_instance) # remove_gear takes instance or ID
                                    items_removed_count += 1

                            print(f"You sold {actual_sales_units} of '{item_template.name}' for ${earnings}!")
                        else:
                            print(f"Didn't manage to sell any '{item_template.name}' this time.")
                    else: # Chose "Don't sell anything" or invalid number
                        print("Decided not to sell merchandise right now.")
                else: # Invalid input
                    print("No valid merchandise selling choice made.")
        # --- End Sell Merchandise Phase ---

        print(f"\n{player.name} gained {self.fame_reward} fame. Total fame: {player.fame}.")
        print(f"{player.name} earned ${self.payout} (Advertised from gig). Final money after gig, incidents & merch: ${player.money}.")
        self.is_active = False
        return True

    def __str__(self):
        venue_name = self.location.name if hasattr(self.location, 'name') else "Unknown Venue"
        if hasattr(self.location, 'venue_type'): # If location is a Venue object
             venue_name = f"{self.location.name} ({self.location.venue_type})"
        return f"Event: {self.name} at {venue_name}, Requires: {self.required_skills}, Reward: {self.fame_reward} fame, Payout: ${self.payout}."

if __name__ == '__main__':
    # Basic tests for Event class
    # Need mock Player and Location/Venue for full testing
    class MockPlayer:
        def __init__(self):
            self.skills = {"guitar": 5, "vocals": 5}
            self.fame = 0
            self.money = 0

    class MockVenue:
        def __init__(self, name="Test Venue"):
            self.name = name
            self.venue_type = "CLUB"

    player = MockPlayer()
    venue = MockVenue()

    # Test basic event
    event1 = Event("Open Mic", venue, event_type="OPEN_MIC", required_skills={"guitar": 1})
    assert event1.name == "Open Mic"
    assert event1.fame_reward == Event.EVENT_TYPES["OPEN_MIC"]["base_fame"]
    can_perform, _ = event1.can_perform(player)
    assert can_perform

    # Test event with preparations
    event2 = Event("Big Show", venue, event_type="CONCERT", required_skills={"vocals": 10}) # Player vocals are 5
    event2.preparation_tasks_required = {"Rehearse": False, "Promote": False}

    can_perform, msg = event2.can_perform(player)
    assert not can_perform
    assert "preparations are not complete" in msg

    event2.complete_preparation_task("Rehearse")
    assert event2.preparation_tasks_required["Rehearse"]
    can_perform, msg = event2.can_perform(player)
    assert not can_perform # Still needs Promote, and also skill check will fail

    event2.complete_preparation_task("Promote")
    assert event2.are_preparations_complete()

    can_perform, msg = event2.can_perform(player) # Now prep is done, but skills are too low
    assert not can_perform
    assert "Player does not meet skill requirement for vocals" in msg

    player.skills["vocals"] = 10 # Meet skill req
    can_perform, msg = event2.can_perform(player)
    assert can_perform

    # Test performance
    initial_fame = player.fame
    initial_money = player.money
    event2.perform_event(player)
    assert player.fame == initial_fame + Event.EVENT_TYPES["CONCERT"]["base_fame"]
    assert player.money == initial_money + Event.EVENT_TYPES["CONCERT"]["base_payout"]
    assert not event2.is_active

    print("Event class basic tests passed.")
