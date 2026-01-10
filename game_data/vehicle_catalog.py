from game.vehicle import Vehicle

VEHICLE_CATALOG = {
    "rusty_sedan": Vehicle(
        name="Rusty Sedan",
        cost=1500,
        speed=1.2,
        fuel_capacity=40,
        fuel_efficiency=10,
        cargo_capacity=10,
        reliability=0.6,
        condition=50.0
    ),
    "used_hatchback": Vehicle(
        name="Used Hatchback",
        cost=4000,
        speed=1.5,
        fuel_capacity=50,
        fuel_efficiency=15,
        cargo_capacity=20,
        reliability=0.8,
        condition=80.0
    ),
    "tour_van": Vehicle(
        name="Tour Van",
        cost=8000,
        speed=1.3,
        fuel_capacity=80,
        fuel_efficiency=12,
        cargo_capacity=50,
        reliability=0.9,
        condition=90.0
    ),
    "motorcycle": Vehicle(
        name="Motorcycle",
        cost=6000,
        speed=2.0,
        fuel_capacity=20,
        fuel_efficiency=20,
        cargo_capacity=5,
        reliability=0.85,
        condition=100.0
    ),
    "luxury_suv": Vehicle(
        name="Luxury SUV",
        cost=45000,
        speed=1.8,
        fuel_capacity=70,
        fuel_efficiency=8,
        cargo_capacity=40,
        reliability=0.95,
        condition=100.0
    ),
    "tour_bus": Vehicle(
        name="Custom Tour Bus",
        cost=150000,
        speed=1.1,
        fuel_capacity=300,
        fuel_efficiency=5,
        cargo_capacity=200,
        reliability=0.98,
        condition=100.0
    ),
    "private_jet": Vehicle(
        name="Chartered Private Jet",
        cost=2000000,
        speed=10.0,
        fuel_capacity=1000,
        fuel_efficiency=2, # High consumption but immense speed
        cargo_capacity=100,
        reliability=0.99,
        condition=100.0
    )
}
