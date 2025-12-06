import random

def generate_road_event(player, vehicle, distance_segment, transport_mode="car"):
    """
    Generates a random event during travel.
    Returns (event_description, time_delay_hours, stress_change, money_change, stop_travel)
    """

    # Base chance of an event per segment (e.g. per 100km or per hour)
    # Reduced chance for planes/trains
    event_chance = 0.3
    if transport_mode == "plane": event_chance = 0.1
    if transport_mode == "train": event_chance = 0.15

    if random.random() > event_chance:
        return None, 0, 0, 0, False

    # Define Event Pools
    car_events = [
        {
            "name": "Traffic Jam",
            "desc": "You got stuck in heavy traffic due to construction.",
            "time": random.uniform(1, 3),
            "stress": 10,
            "money": 0,
            "stop": False
        },
        {
            "name": "Scenic Route",
            "desc": "You took a beautiful scenic detour. Inspiration strikes!",
            "time": 1,
            "stress": -10,
            "money": 0,
            "stop": False,
            "effect": lambda p: setattr(p, 'inspiration', min(100, p.inspiration + 10))
        },
        {
            "name": "Speed Trap",
            "desc": "Police radar! You got a speeding ticket.",
            "time": 0.5,
            "stress": 15,
            "money": -150,
            "stop": False
        },
        {
            "name": "Flat Tire",
            "desc": "Pop! A flat tire. You have to change it on the side of the road.",
            "time": 2,
            "stress": 20,
            "money": 0,
            "stop": False
        },
        {
            "name": "Strange Hitchhiker",
            "desc": "You pick up a hitchhiker who tells you wild stories.",
            "time": 0,
            "stress": 5,
            "money": 0,
            "stop": False,
            "effect": lambda p: setattr(p, 'inspiration', min(100, p.inspiration + 5))
        }
    ]

    plane_events = [
        {
            "name": "Turbulence",
            "desc": "Rough air! The flight is bumpy.",
            "time": 0,
            "stress": 10,
            "money": 0,
            "stop": False
        },
        {
            "name": "Flight Delay",
            "desc": "The flight is circling due to weather.",
            "time": 1,
            "stress": 5,
            "money": 0,
            "stop": False
        },
        {
            "name": "Great View",
            "desc": "A beautiful view from the clouds inspires you.",
            "time": 0,
            "stress": -5,
            "money": 0,
            "stop": False,
            "effect": lambda p: setattr(p, 'inspiration', min(100, p.inspiration + 5))
        }
    ]

    train_events = [
        {
            "name": "Signal Failure",
            "desc": "Train stopped due to signal failure.",
            "time": random.uniform(0.5, 2),
            "stress": 5,
            "money": 0,
            "stop": False
        },
        {
            "name": "Quiet Cabin",
            "desc": "The train is peaceful. You get some rest.",
            "time": 0,
            "stress": -10,
            "money": 0,
            "stop": False
        }
    ]

    events = car_events
    if transport_mode == "plane":
        events = plane_events
    elif transport_mode == "train":
        events = train_events
    elif transport_mode == "bus":
        events = car_events # Bus shares road events mostly, maybe filter speed trap? keeping simple.

    event = random.choice(events)

    # Safety check for inspiration attribute, just in case
    if "effect" in event:
        if hasattr(player, 'inspiration'):
            event["effect"](player)
        else:
            # If inspiration is missing, just ignore the effect (or log it)
            pass

    return event["desc"], event["time"], event["stress"], event["money"], event["stop"]
