import random

def generate_road_event(player, vehicle, distance_segment):
    """
    Generates a random event during travel.
    Returns (event_description, time_delay_hours, stress_change, money_change, stop_travel)
    """

    # Base chance of an event per segment (e.g. per 100km or per hour)
    event_chance = 0.3
    if random.random() > event_chance:
        return None, 0, 0, 0, False

    events = [
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
            "money": 0, # Could cost money if no spare? Assumed manual fix.
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

    event = random.choice(events)

    # Safety check for inspiration attribute, just in case
    if "effect" in event:
        if hasattr(player, 'inspiration'):
            event["effect"](player)
        else:
            # If inspiration is missing, just ignore the effect (or log it)
            pass

    return event["desc"], event["time"], event["stress"], event["money"], event["stop"]
