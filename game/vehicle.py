class Vehicle:
    def __init__(self, name, cost, speed, fuel_capacity, fuel_efficiency):
        self.name = name
        self.cost = cost
        self.speed = speed
        self.fuel_capacity = fuel_capacity
        self.fuel = fuel_capacity
        self.fuel_efficiency = fuel_efficiency # e.g., km per liter

    def travel(self, distance):
        fuel_needed = distance / self.fuel_efficiency
        if self.fuel >= fuel_needed:
            self.fuel -= fuel_needed
            return True
        else:
            return False

    def refuel(self, amount):
        self.fuel = min(self.fuel_capacity, self.fuel + amount)

    def __str__(self):
        return f"{self.name} (Speed: {self.speed}, Fuel: {self.fuel}/{self.fuel_capacity})"
