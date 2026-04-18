import re

with open('game/game.py', 'r') as f:
    content = f.read()

search_str = """        elif choice == "plan_tour":
            self.GAME_LOG.add_log_message("Agent: 'I'll look for routing options. Check back later.'")
            # Placeholder for complex tour logic"""

replace_str = """        elif choice == "seek_label":
            self.GAME_LOG.add_log_message("Agent: 'Let me pitch your portfolio to some A&R reps. Give me a few hours.'")
            self._advance_time_with_needs(180) # 3 hours

            manager_skill = 1
            for staff in self.player.staff:
                if staff.role == "Manager":
                    manager_skill = staff.skill_level
                    break

            # Base chance is dependent on fame, plus manager skill
            base_chance = min(0.8, (self.player.fame / 1000.0) + (manager_skill * 0.05))

            if random.random() < base_chance:
                # Success! Generate a contract
                label_names = ["Big Sonic Records", "IndiePulse Music", "Neon Nights Audio", "Monolith Media"]
                label_name = random.choice(label_names)

                advance = random.randint(500, 5000) + (self.player.fame * 10) + (manager_skill * 1000)
                royalty = random.uniform(0.05, 0.20) + (manager_skill * 0.01)
                marketing = random.randint(100, 2000) + (self.player.fame * 5)

                new_contract = Contract(label_name, advance, min(0.5, royalty), marketing)
                self.player.pending_contracts.append(new_contract)

                self.GAME_LOG.add_log_message(f"Agent: 'Great news! I got an offer from {label_name}!'")
                self.GAME_LOG.add_log_message("Check the 'Label Offers' menu on your phone to review the contract.")
            else:
                self.GAME_LOG.add_log_message("Agent: 'Sorry, none of the labels I pitched to are biting right now. Build up your fame and try again later.'")

        elif choice == "plan_tour":
            self.GAME_LOG.add_log_message("Agent: 'Let me look at some routing options for a regional tour...'")
            self._advance_time_with_needs(240) # 4 hours

            if self.player.fame < 100:
                self.GAME_LOG.add_log_message("Agent: 'You don't have enough pull yet for a multi-city tour. We need to build your local fame first.'")
            else:
                self.GAME_LOG.add_log_message("Agent: 'I've mapped out a short 3-stop regional tour!'")
                # Find venues across different cities if possible, or just 3 decent venues
                all_venues = []
                for loc in self.LOCATIONS.values():
                    all_venues.extend(loc.venues)

                if len(all_venues) >= 3:
                    tour_venues = random.sample(all_venues, 3)
                    start_time = current_game_time.copy()
                    start_time.add_days(2) # Start in 2 days

                    for i, venue in enumerate(tour_venues):
                        gig_time = start_time.copy()
                        gig_time.add_days(i * 2) # Every 2 days
                        gig_time.hour = 20

                        booked_event = Event(
                            name=f"Tour Gig @ {venue.name}",
                            event_type="CLUB_GIG",
                            location=venue,
                        )
                        venue.add_event(booked_event)

                        gig_end_time = gig_time.copy()
                        gig_end_time.add_hours(2)

                        self.player.schedule.add_event(
                            gig_time,
                            gig_end_time,
                            f"Tour: {venue.name}",
                            "Gig",
                            {"event_id": booked_event.event_id, "venue_id": venue.venue_id},
                        )
                    self.GAME_LOG.add_log_message("Check your Schedule for the new tour dates!")
                else:
                    self.GAME_LOG.add_log_message("Agent: 'Actually, I couldn't find enough suitable venues to string together a tour right now.'")"""

content = content.replace(search_str, replace_str)

with open('game/game.py', 'w') as f:
    f.write(content)
