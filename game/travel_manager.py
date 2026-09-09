from game.road_events import generate_road_event
import random

class TravelManager:
    def __init__(self, player, destination, distance_total, transport_mode, ticket_class="economy", vehicle=None):
        self.player = player
        self.destination = destination
        self.distance_total = distance_total
        self.distance_covered = 0
        self.transport_mode = transport_mode # "bus", "train", "plane", or "car" (if vehicle provided)
        self.ticket_class = ticket_class
        self.vehicle = vehicle # Vehicle object if driving own car

        self.is_finished = False
        self.log = []
        self.segment_length = 50.0 # km per "tick" or hour?
        # Let's base segment on time. 1 hour segments.
        # Speed determines distance per hour.

        self.current_speed = self._get_speed()
        self.travel_time_elapsed = 0.0

    def _get_speed(self):
        if self.vehicle:
            # Early vehicle catalogs stored road-speed multipliers.
            return self.vehicle.speed * 60 if self.vehicle.speed <= 5 else self.vehicle.speed
        if self.transport_mode == "plane": return 800.0
        if self.transport_mode == "train": return 100.0
        if self.transport_mode == "bus": return 60.0
        if self.transport_mode == "bike": return 15.0 # Slow!
        if self.transport_mode == "walk": return 5.0
        return 60.0

    def advance_one_hour(self):
        events, arrived, _ = self.advance_minutes(60)
        return events, arrived

    def advance_minutes(self, minutes):
        """Return events, arrival and actual elapsed minutes, including delays.

        Road events are checked per hour of movement, independent of how often
        the player opens the phone. Partial final legs stop at arrival.
        """
        from math import ceil
        events, elapsed = [], 0
        self.delay_minutes = getattr(self, 'delay_minutes', 0)
        self.road_check_in = getattr(self, 'road_check_in', 60)
        while elapsed < minutes and not self.is_finished:
            if self.delay_minutes > 0:
                step = min(minutes - elapsed, self.delay_minutes)
                self.delay_minutes -= step
            else:
                if self.road_check_in <= 0:
                    self.road_check_in = 60
                    mode = 'car' if self.vehicle else self.transport_mode
                    desc, delay, stress, money, stop = generate_road_event(self.player, self.vehicle, 60 * self.current_speed / 60, mode)
                    if desc:
                        events.append(f'EVENT: {desc}')
                        self.player.stress = max(0, min(100, self.player.stress + stress))
                        self.player.money += money
                        self.delay_minutes = max(ceil(delay * 60), 60 if stop else 0)
                        if self.delay_minutes:
                            events.append(f'Delay: {self.delay_minutes} minutes before moving again.')
                            continue
                remaining = max(0, self.distance_total - self.distance_covered)
                if remaining < 0.000001:
                    self.is_finished = True
                    break
                step = min(minutes - elapsed, self.road_check_in, max(1, ceil(remaining / self.current_speed * 60)))
                distance = min(remaining, self.current_speed * step / 60)
                if self.vehicle:
                    result = self.vehicle.travel(distance)
                    if not result['success']:
                        distance = 0
                        if result.get('breakdown'):
                            events.append(f"BREAKDOWN: {result['message']}")
                            self.player.stress = min(100, self.player.stress + 10)
                        else:
                            events.append('Out of fuel! Called tow truck ($200).')
                            self.player.money -= 200
                            self.vehicle.refuel(10)
                self.distance_covered += distance
                self.road_check_in -= step
            elapsed += step
            self.player.energy = max(0, self.player.energy - 2 * step / 60)
            stress_rate = {'business': .5, 'first': 0}.get(self.ticket_class, 1)
            self.player.stress = max(0, min(100, self.player.stress + stress_rate * step / 60))
            self.is_finished = self.distance_covered >= self.distance_total and self.delay_minutes <= 0
            # Hand control back after trouble; never silently run through it.
            if events:
                break
        self.travel_time_elapsed += elapsed / 60
        return events, self.is_finished, elapsed

    def get_progress_percent(self):
        if self.distance_total == 0: return 1.0
        return min(1.0, self.distance_covered / self.distance_total)

    def get_actions(self):
        actions = {"continue": "Continue Journey"}

        if self.transport_mode in ["plane", "train", "bus"] or (self.vehicle and self.vehicle.name == "Custom Tour Bus"):
            actions["nap"] = "Nap (+Energy)"
            actions["phone"] = "Check Phone"

        if self.ticket_class in ["business", "first"] or (self.vehicle and self.vehicle.name == "Custom Tour Bus"):
            actions["meal"] = "Eat Meal"
            actions["drink"] = "Have a Drink"

        return actions
