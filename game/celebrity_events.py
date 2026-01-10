import random

def check_for_celebrity_event(player):
    """
    Checks if a celebrity event invite arrives.
    Returns (event_name, description) or None.
    """
    if player.fame < 200:
        return None

    events = [
        {"name": "Music Awards Gala", "req": 200, "desc": "You are invited to the Golden Mic Awards.", "fame_gain": 50},
        {"name": "Super Bowl Party", "req": 500, "desc": "An invite to the wildest Super Bowl afterparty.", "fame_gain": 100},
        {"name": "Charity Ball", "req": 300, "desc": "A high-society charity event. Good for reputation.", "fame_gain": 30},
        {"name": "Met Gala", "req": 800, "desc": "The most exclusive fashion event of the year.", "fame_gain": 200}
    ]

    # Check one random event per call (weekly?)
    evt = random.choice(events)

    if player.fame >= evt['req']:
        if random.random() < 0.1: # 10% chance if eligible
            return evt

    return None
