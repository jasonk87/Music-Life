from game.vehicle import Vehicle

VEHICLE_CATALOG = {
    "rusty_sedan": Vehicle(
        name="Rusty Sedan",
        cost=1500,
        speed=1.2,
        fuel_capacity=40,
        fuel_efficiency=10
    ),
    "used_hatchback": Vehicle(
        name="Used Hatchback",
        cost=4000,
        speed=1.5,
        fuel_capacity=50,
        fuel_efficiency=15
    ),
    "tour_van": Vehicle(
        name="Tour Van",
        cost=8000,
        speed=1.3,
        fuel_capacity=80,
        fuel_efficiency=12
    ),
    "motorcycle": Vehicle(
        name="Motorcycle",
        cost=6000,
        speed=2.0,
        fuel_capacity=20,
        fuel_efficiency=20
    ),
}
