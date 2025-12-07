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
            return self.vehicle.speed
        if self.transport_mode == "plane": return 800.0
        if self.transport_mode == "train": return 100.0
        if self.transport_mode == "bus": return 60.0
        if self.transport_mode == "bike": return 15.0 # Slow!
        if self.transport_mode == "walk": return 5.0
        return 60.0

    def advance_one_hour(self):
        """
        Simulates 1 hour of travel.
        Returns (events_list, arrived_bool)
        """
        if self.is_finished:
            return [], True

        events = []
        # Update speed (variance)
        speed = self.current_speed * random.uniform(0.9, 1.1)
        dist_leg = speed # 1 hour

        # Cap at remaining
        if self.distance_covered + dist_leg >= self.distance_total:
            dist_leg = self.distance_total - self.distance_covered
            self.is_finished = True

        # Resource Consumption & Vehicle Logic
        if self.vehicle:
            result = self.vehicle.travel(dist_leg)
            if not result['success']:
                if result.get('breakdown'):
                    events.append(f"BREAKDOWN: {result['message']}")
                    # Breakdown adds delay?
                    # In this turn-based system, delay means "distance doesn't increase but time passes"?
                    # Or we explicitly add delay hours.
                    # Let's say breakdown effectively halts progress for this turn AND adds extra time to 'elapsed' counter conceptually,
                    # but since we are stepping 1 hour at a time, maybe we just set is_finished=False and don't advance distance?
                    # Simpler: Breakdown stops distance gain this turn.
                    dist_leg = 0 # No progress
                    self.player.stress += 10
                elif "fuel" in result.get('message', '').lower():
                    events.append("Out of fuel! Called tow truck ($200).")
                    self.player.money -= 200
                    self.vehicle.refuel(10)
                    dist_leg = 0

            # Vehicle wear/fuel is handled inside vehicle.travel

        # Player Stats (Fatigue/Stress)
        # Class multipliers
        stress_mult = 1.0
        if self.ticket_class == "business": stress_mult = 0.5
        elif self.ticket_class == "first": stress_mult = 0.0

        self.player.energy = max(0, self.player.energy - 2) # Constant drain
        self.player.stress = min(100, self.player.stress + (1 * stress_mult))

        # Random Road Events
        # We pass "car", "plane", etc.
        mode_str = "car" if self.vehicle else self.transport_mode
        evt_desc, delay, stress_mod, money_mod, stop = generate_road_event(self.player, self.vehicle, dist_leg, mode_str)

        if evt_desc:
            events.append(f"EVENT: {evt_desc}")
            self.player.stress = min(100, self.player.stress + (stress_mod * stress_mult))
            self.player.money += money_mod
            # Delay in "Interactive Travel" means we just don't progress distance, or we progress less?
            # If delay > 0, effectively we spend hours not moving.
            # But advance_one_hour is 1 hour.
            # We can handle delay by adding to a "delay_pool" that must drain before moving?
            # Or just ignore exact hour tracking for events and just say "You lost 2 hours" (and manually advance game time elsewhere?)
            # Let's keep it simple: Events are flavor + stat changes. Progress continues unless 'stop' is True.
            if stop:
                dist_leg = 0
                events.append("Travel halted for this hour.")

        self.distance_covered += dist_leg
        self.travel_time_elapsed += 1

        if self.distance_covered >= self.distance_total:
            self.is_finished = True

        return events, self.is_finished

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
