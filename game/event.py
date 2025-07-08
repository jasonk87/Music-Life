import random # Needed for incident chance

class Event:
    EVENT_TYPES = {
        "OPEN_MIC": {"base_fame": 10, "base_payout": 50, "skill_multiplier": 1.0, "songs_required": 1},
        "CLUB_GIG": {"base_fame": 50, "base_payout": 250, "skill_multiplier": 1.5, "songs_required": 3},
        "CONCERT": {"base_fame": 200, "base_payout": 1000, "skill_multiplier": 2.0, "songs_required": 5},
        "FESTIVAL_SLOT": {"base_fame": 500, "base_payout": 3000, "skill_multiplier": 2.5, "songs_required": 7}
    }

    def __init__(self, name, location, event_type="OPEN_MIC", required_skills=None,
                 required_gear_types=None,
                 description="", specific_fame_reward=None, specific_payout=None, is_tour_gig=False): # Added is_tour_gig
        self.name = name
        self.location = location
        self.event_type = event_type
        self.required_gear_types = required_gear_types if required_gear_types else []

        type_details = Event.EVENT_TYPES.get(event_type, Event.EVENT_TYPES["OPEN_MIC"])
        self.songs_required_count = type_details.get("songs_required", 1)

        self.required_skills = required_skills if required_skills else {}
        for skill in list(self.required_skills.keys()):
            self.required_skills[skill] = max(1, int(self.required_skills[skill] * type_details["skill_multiplier"]))

        self.fame_reward = specific_fame_reward if specific_fame_reward is not None else type_details["base_fame"]
        self.payout = specific_payout if specific_payout is not None else type_details["base_payout"]

        self.description = description
        self.is_active = True
        self.preparation_tasks_required = {}
        self.preparation_complete = False
        self.is_tour_gig = is_tour_gig # Store if this event is part of a tour


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
            return False, "This event is no longer active.", False

        if not self.are_preparations_complete():
            pending_tasks = [task for task, completed in self.preparation_tasks_required.items() if not completed]
            return False, f"Event preparations are not complete. Pending: {', '.join(pending_tasks)}", False

        for skill, required_level in self.required_skills.items():
            if player.skills.get(skill, 0) < required_level:
                return False, f"Player does not meet skill requirement for {skill} (needs {required_level}, has {player.skills.get(skill, 0)}).", False

        if len(player.songs_written) < self.songs_required_count:
            return False, f"Player does not have enough songs written (needs {self.songs_required_count}, has {len(player.songs_written)}).", False

        gear_ok, gear_message, needs_rental = self._check_gear_requirements(player)
        if not gear_ok:
            return False, gear_message, needs_rental

        return True, "Player meets all requirements.", needs_rental

    def _check_gear_requirements(self, player):
        if not self.required_gear_types:
            return True, "No specific gear required.", False

        from game_data.gear_catalog import GEAR_CATALOG

        player_gear_types_owned_and_working = set()
        for item in player.gear_inventory:
            if not item.is_broken:
                player_gear_types_owned_and_working.add(item.gear_type)

        missing_gear_messages = []
        actually_needs_rental_for_event = False

        for req_type in self.required_gear_types:
            if req_type not in player_gear_types_owned_and_working:
                venue = self.location
                if hasattr(venue, 'can_rent_gear') and venue.can_rent_gear:
                    can_rent_this_type = False
                    for item_id in venue.available_rental_gear_ids:
                        rental_item = GEAR_CATALOG.get(item_id)
                        if rental_item and rental_item.gear_type == req_type:
                            can_rent_this_type = True
                            break
                    if can_rent_this_type:
                        actually_needs_rental_for_event = True
                        continue
                    else:
                        missing_gear_messages.append(f"Missing {req_type} (venue does not rent this type).")
                else:
                    missing_gear_messages.append(f"Missing {req_type} (rental not possible/available at venue).")

        if missing_gear_messages:
            return False, "Missing required gear: " + ", ".join(missing_gear_messages), actually_needs_rental_for_event

        return True, "All gear requirements met (owned or rentable).", actually_needs_rental_for_event

    def perform_event(self, player, setlist=None):
        # Returns tuple: (success_bool, tour_just_completed_bool)
        can_perform_bool, message_str, needs_rental_bool = self.can_perform(player)
        if not can_perform_bool:
            print(f"Cannot perform {self.name}: {message_str}")
            return False, False

        if not setlist or len(setlist) != self.songs_required_count:
            print(f"Error: Setlist mismatch for {self.name}. Expected {self.songs_required_count} songs, got {len(setlist) if setlist else 0}.")
            return False, False

        print(f"\n{player.name} is performing at {self.name} at {self.location.name}!")
        print("Setlist:")
        total_song_quality = 0
        for i, song_obj in enumerate(setlist):
            print(f"  {i+1}. {song_obj.title} (Q: {song_obj.song_quality:.2f}, G: {song_obj.genre})")
            total_song_quality += song_obj.song_quality
        avg_song_quality = total_song_quality / len(setlist) if setlist else 0

        performance_score = 50
        skill_contribution_total = 0
        num_req_skills = len(self.required_skills)
        if num_req_skills > 0:
            for skill, req_level in self.required_skills.items():
                player_skill = player.skills.get(skill, 0)
                skill_diff = player_skill - req_level
                skill_impact = max(-10, min(10, skill_diff * 2))
                skill_contribution_total += skill_impact
            performance_score += (skill_contribution_total / num_req_skills) * 1.5

        if player.energy < 25: performance_score -= 10
        elif player.energy < 50: performance_score -= 5
        elif player.energy > 90: performance_score += 5

        if player.stress > 75: performance_score -= 10
        elif player.stress > 50: performance_score -= 5
        elif player.stress < 15: performance_score += 5

        song_quality_modifier = (avg_song_quality - 0.5) * 30
        performance_score += song_quality_modifier

        if self.preparation_tasks_required and self.are_preparations_complete():
            performance_score += 5

        if hasattr(player, 'tour_fatigue'):
            performance_score -= player.tour_fatigue / 5

        performance_score += random.randint(-5, 5)
        performance_score = max(0, min(100, int(performance_score)))

        actual_fame_reward = self.fame_reward
        actual_payout = self.payout
        outcome_message = ""

        if performance_score >= 90:
            outcome_message = "Legendary performance! The crowd is ecstatic! Encore! Encore!"
            actual_fame_reward = int(self.fame_reward * 2.0)
            actual_payout = int(self.payout * 1.5)
        elif performance_score >= 75:
            outcome_message = "Fantastic show! You really connected with the audience."
            actual_fame_reward = int(self.fame_reward * 1.5)
            actual_payout = int(self.payout * 1.2)
        elif performance_score >= 55:
            outcome_message = "Good gig! The crowd seemed to enjoy it."
            actual_fame_reward = int(self.fame_reward * 1.1)
        elif performance_score >= 35:
            outcome_message = "It was... a performance. Some claps, some confused looks."
            actual_fame_reward = int(self.fame_reward * 0.8)
            actual_payout = int(self.payout * 0.9)
        else:
            outcome_message = "Yikes. That didn't go well. Better luck next time."
            actual_fame_reward = int(self.fame_reward * 0.25)
            actual_payout = int(self.payout * 0.5)

        print(f"\nPerformance Score: {performance_score}/100")
        print(outcome_message)

        used_owned_gear_for_event = []
        player_owned_gear_types = {item.gear_type for item in player.gear_inventory if not item.is_broken}
        for req_type in self.required_gear_types:
            if req_type in player_owned_gear_types:
                for item in player.gear_inventory:
                    if item.gear_type == req_type and not item.is_broken:
                        used_owned_gear_for_event.append(item)
                        break
        if used_owned_gear_for_event:
            print("\n--- Gear Wear & Tear from Performance ---")
            for item in used_owned_gear_for_event:
                damage = random.randint(3, 8)
                item.take_damage(damage)
                print(f"Your {item.name} saw some action! Durability: {item.durability}/100.")
                if item.is_broken:
                     print(f"Disaster! Your {item.name} broke mid-show (or just after)!")

        incident_chance = 0.10
        if random.random() < incident_chance:
            incident_candidate_gear = used_owned_gear_for_event
            if not incident_candidate_gear:
                incident_candidate_gear = [
                    item for item in player.gear_inventory
                    if (item.gear_type.startswith("INSTRUMENT") or item.gear_type == "AMPLIFIER") and not item.is_broken
                ]
            if incident_candidate_gear:
                affected_gear = random.choice(incident_candidate_gear)
                base_repair_cost = random.randint(5, 25)
                incident_resolved_by_spare = False
                final_incident_cost = base_repair_cost
                incident_description = "had a minor issue"
                gt = affected_gear.gear_type
                is_stringed_instrument = gt in ["INSTRUMENT_ACOUSTIC", "INSTRUMENT_ELECTRIC", "INSTRUMENT_BASS"]
                if is_stringed_instrument:
                    incident_description = "a string snapped"
                    spare_strings_item = None
                    for item_in_inventory in player.gear_inventory:
                        if item_in_inventory.item_id == "guitar_strings_basic" and not item_in_inventory.is_broken:
                            spare_strings_item = item_in_inventory
                            break
                    if spare_strings_item:
                        player.remove_gear(spare_strings_item)
                        print(f"\nOh no! During the performance, your {affected_gear.name} {incident_description}!")
                        print("Luckily, you had spare strings and quickly replaced it. The show goes on!")
                        incident_resolved_by_spare = True
                        final_incident_cost = 0
                    else:
                        print(f"\nOh no! During the performance, your {affected_gear.name} {incident_description}!")
                        print("You don't have any spare strings! You try to play around it, costing you some focus and potentially money for a rush replacement.")
                if not incident_resolved_by_spare:
                    if gt == "AMPLIFIER": incident_description = "a tube blew"
                    elif gt == "INSTRUMENT_DRUMS": incident_description = "a drum skin split or a cymbal cracked"
                    elif not is_stringed_instrument: incident_description = "had a component fail"
                    print(f"\nOh no! During the performance, your {affected_gear.name} had an issue ({incident_description})!")
                    print(f"Immediate repair/replacement cost: ${final_incident_cost}.")
                    if player.money >= final_incident_cost:
                        player.money -= final_incident_cost
                        print(f"${final_incident_cost} deducted for repairs/replacement.")
                    else:
                        print(f"You couldn't afford the immediate ${final_incident_cost} cost. This might cause issues later!")
            else:
                print("\nLuckily, all your owned gear made it through the performance unscathed (or you didn't use any!).")

        if needs_rental_bool:
            venue = self.location
            if hasattr(venue, 'can_rent_gear') and venue.can_rent_gear and venue.gear_rental_fee > 0:
                player.money -= venue.gear_rental_fee
                print(f"A gear rental fee of ${venue.gear_rental_fee} was deducted.")

        player.fame += actual_fame_reward
        player.money += actual_payout

        tour_just_completed = False
        if self.is_tour_gig and player.current_tour_id and player.current_tour_id in player.tour_ledgers:
            tour_ledger = player.tour_ledgers[player.current_tour_id]
            if tour_ledger["status"] == "ongoing":
                gig_found_in_ledger = False
                all_gigs_performed_on_tour = True # Assume true until an unperformed one is found
                for gig_detail in tour_ledger.get("gigs_details", []):
                    # Match based on event name, which should be unique for tour gigs like "Tour: Player at Venue"
                    if gig_detail["event_name"] == self.name:
                        gig_detail["performed"] = True
                        tour_ledger["income"] += actual_payout # Add this gig's payout to tour income
                        gig_found_in_ledger = True
                        print(f"LOG: Payout ${actual_payout} added to income for tour '{tour_ledger['name']}'. Gig '{self.name}' marked as performed.")
                    if not gig_detail.get("performed", False):
                        all_gigs_performed_on_tour = False # Found an unperformed gig

                if gig_found_in_ledger and all_gigs_performed_on_tour:
                    tour_just_completed = True
                    # Tour completion summary will be handled in main.py after this function returns

            tour_stress_penalty = random.randint(3, 7)
            tour_energy_penalty = random.randint(5, 15)
            player.stress = min(100, player.stress + tour_stress_penalty)
            player.energy = max(0, player.energy - tour_energy_penalty)
            if hasattr(player, 'tour_fatigue'):
                 player.tour_fatigue = min(100, player.tour_fatigue + random.randint(5,10))
                 print(f"The grind of the tour takes its toll... (Stress +{tour_stress_penalty}, Energy -{tour_energy_penalty}, Fatigue now {player.tour_fatigue})")
            else:
                 print(f"Being on tour is tiring! (Stress +{tour_stress_penalty}, Energy -{tour_energy_penalty})")

        print(f"\n{player.name} gained {actual_fame_reward} fame. Total fame: {player.fame}.")
        print(f"{player.name} earned ${actual_payout} (Advertised: ${self.payout}). Final money after gig: ${player.money}.")
        self.is_active = False
        return True, tour_just_completed

    def __str__(self):
        venue_name = self.location.name if hasattr(self.location, 'name') else "Unknown Venue"
        if hasattr(self.location, 'venue_type'):
             venue_name = f"{self.location.name} ({self.location.venue_type})"
        return f"Event: {self.name} at {venue_name}, Requires: {self.required_skills}, Reward: {self.fame_reward} fame, Payout: ${self.payout}."

if __name__ == '__main__':
    class MockPlayer:
        def __init__(self):
            self.name = "Test Player"
            self.skills = {"guitar": 5, "vocals": 5, "songwriting": 2}
            self.fame = 100 # Give some initial fame for testing tour offers
            self.money = 1000
            self.energy = 100
            self.stress = 0
            self.songs_written = []
            self.gear_inventory = []
            self.current_tour_id = None
            self.tour_ledgers = {}
            self.tour_fatigue = 0
            self.completed_tour_ids = []
            self.active_tour_offer = None


    class MockVenue:
        def __init__(self, name="Test Venue", venue_id="test_venue_01"): # Added venue_id
            self.name = name
            self.venue_id = venue_id # Added for matching
            self.venue_type = "CLUB"
            self.capacity = 100
            self.can_rent_gear = False
            self.gear_rental_fee = 0
            self.available_rental_gear_ids = []
            self.events_hosted = []
        def add_event(self, event): self.events_hosted.append(event)

    class Song:
        def __init__(self, title, author, genre, song_quality=0.0):
            self.title = title; self.author = author; self.genre = genre; self.song_quality = song_quality
        def __str__(self): return f"'{self.title}' ({self.genre}, Q:{self.song_quality:.2f})"

    player = MockPlayer()
    venue = MockVenue()

    player.songs_written.extend([
        Song("Hit Single", player.name, "Pop", 0.9), Song("Rock Anthem", player.name, "Rock", 0.8),
        Song("Indie Jam", player.name, "Indie", 0.7), Song("Folk Tale", player.name, "Folk", 0.6),
        Song("Bluesy Mood", player.name, "Blues", 0.75)
    ])

    # Test Tour Gig
    tour_gig_name = f"Tour: {player.name} at {venue.name}"
    tour_gig = Event(tour_gig_name, venue, event_type="CLUB_GIG",
                     required_skills={"vocals": 5}, is_tour_gig=True)

    player.current_tour_id = "test_tour_01"
    player.tour_ledgers[player.current_tour_id] = {
        "name": "My First Real Tour",
        "expenses": 50, "income": 0, "status": "ongoing",
        "gigs_details": [
            {"venue_id": venue.venue_id, "event_name": tour_gig_name, "performed": False, "city_name": "Testville"},
            {"venue_id": "other_venue", "event_name": "Tour: Other Gig", "performed": False, "city_name": "Otherville"}
        ]
    }
    player.tour_fatigue = 20
    player.skills["vocals"] = 7

    print(f"\n--- Testing Tour Gig: {tour_gig.name} ---")
    can_perform_status, msg, _ = tour_gig.can_perform(player)
    print(f"Can perform: {can_perform_status}, Message: {msg}")
    assert can_perform_status

    setlist_tour_gig = player.songs_written[:tour_gig.songs_required_count]
    success_flag, tour_completed_flag = tour_gig.perform_event(player, setlist=setlist_tour_gig)
    assert success_flag
    assert not tour_completed_flag # Only one gig of two performed
    assert player.tour_ledgers[player.current_tour_id]["income"] > 0
    assert player.tour_ledgers[player.current_tour_id]["gigs_details"][0]["performed"]
    assert player.tour_fatigue > 20

    print("\nEvent class advanced tests passed (check output for score details).")
