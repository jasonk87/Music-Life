import random

class Vehicle:
    def __init__(self, name, cost, speed, fuel_capacity, fuel_efficiency, cargo_capacity, reliability=0.9, condition=100.0):
        self.name = name
        self.cost = cost
        self.speed = speed # km/h or generic speed unit
        self.fuel_capacity = fuel_capacity
        self.fuel = fuel_capacity # Start full
        self.fuel_efficiency = fuel_efficiency # km per liter (or unit distance per fuel unit)

        self.cargo_capacity = cargo_capacity # Integer size units
        self.reliability = reliability # Base reliability (0.0 - 1.0)
        self.condition = condition # Current mechanical condition (0.0 - 100.0)
        self.mileage = 0 # Total distance traveled

    def clone(self):
        """Creates a copy of this vehicle."""
        v = Vehicle(self.name, self.cost, self.speed, self.fuel_capacity, self.fuel_efficiency, self.cargo_capacity, self.reliability, self.condition)
        v.fuel = self.fuel
        v.mileage = self.mileage
        return v

    def travel(self, distance):
        """
        Simulates driving the vehicle.
        Returns a dictionary with result details:
        {'success': bool, 'fuel_consumed': float, 'wear': float, 'breakdown': bool, 'message': str}
        """
        result = {
            'success': False,
            'fuel_consumed': 0.0,
            'wear': 0.0,
            'breakdown': False,
            'message': ""
        }

        fuel_needed = distance / self.fuel_efficiency

        if self.fuel < fuel_needed:
            result['message'] = "Not enough fuel to complete the trip."
            # We allow driving until empty in a more complex sim, but for now simple check
            return result

        # Check for breakdown *before* or *during* trip?
        # Let's check based on distance and current condition.
        # Chance of breakdown increases as condition decreases.

        breakdown_chance = (100.0 - self.condition) / 200.0 # e.g. 50% condition -> 0.25 (25%) chance per "trip segment"?
        # Let's scale it by distance. A long trip has higher risk.
        # Say chance is per 100km.
        risk_segments = max(0, distance / 100)

        # Base reliability modifier. High reliability reduces breakdown chance.
        # reliability 1.0 -> chance * 0.5? reliability 0.5 -> chance * 1.5?
        chance_modifier = 2.0 - self.reliability

        final_breakdown_chance = 1 - (1 - min(0.8, breakdown_chance * chance_modifier)) ** risk_segments

        # Cap chance
        final_breakdown_chance = min(0.8, final_breakdown_chance)

        if random.random() < final_breakdown_chance:
            result['breakdown'] = True
            result['message'] = f"The {self.name} broke down! Smoke is pouring from the engine."
            # Breakdown consumes some fuel and adds wear before stopping
            result['fuel_consumed'] = fuel_needed * 0.5
            self.fuel = max(0, self.fuel - result['fuel_consumed'])

            wear_damage = random.uniform(5, 15)
            self.condition = max(0, self.condition - wear_damage)
            result['wear'] = wear_damage

            return result

        # Successful trip
        self.fuel -= fuel_needed
        result['fuel_consumed'] = fuel_needed

        # Apply wear
        # Wear depends on distance. e.g. 0.1 condition lost per 10km
        wear_damage = (distance / 50.0) * random.uniform(0.8, 1.2)
        self.condition = max(0, self.condition - wear_damage)
        result['wear'] = wear_damage

        self.mileage += distance
        result['success'] = True
        result['message'] = f"Traveled {distance}km."

        return result

    def refuel(self, amount):
        old_fuel = self.fuel
        self.fuel = min(self.fuel_capacity, self.fuel + amount)
        added = self.fuel - old_fuel
        return added

    def repair(self, amount=None):
        """
        Repairs the vehicle. If amount is None, full repair.
        """
        if amount is None:
            self.condition = 100.0
        else:
            self.condition = min(100.0, self.condition + amount)

    def get_max_cargo(self):
        return self.cargo_capacity

    def __str__(self):
        return (f"{self.name} [Cond: {self.condition:.1f}%] "
                f"(Fuel: {self.fuel:.1f}/{self.fuel_capacity}) "
                f"Cargo: {self.cargo_capacity}")
