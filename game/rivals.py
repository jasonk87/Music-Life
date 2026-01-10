import random

NEWS_FEED = []

def add_news(headline):
    NEWS_FEED.insert(0, headline)
    if len(NEWS_FEED) > 20:
        NEWS_FEED.pop()

def simulate_rivals(npc_registry):
    """
    Simulates weekly events for rival bands/musicians.
    """
    for npc in npc_registry.values():
        if npc.career_stage == "active_musician" and npc.band_name:
            # 1. Fame Fluctuation
            change = random.randint(-5, 10)
            npc.fame = max(0, npc.fame + change)

            # 2. Random Events
            roll = random.random()
            if roll < 0.05:
                # Release Album
                add_news(f"MUSIC NEWS: {npc.band_name} released a new album! Critics are mixed.")
                npc.fame += 20
            elif roll < 0.08:
                # Scandal
                add_news(f"GOSSIP: {npc.name} of {npc.band_name} spotted in drunken brawl! Reputation hits rock bottom.")
                npc.reputation -= 20
                npc.fame += 5 # No publicity is bad publicity?
            elif roll < 0.10:
                # Tour
                add_news(f"TOUR ALERT: {npc.band_name} announces a world tour.")
                npc.fame += 15
            elif roll < 0.12:
                # Breakup / Leaving
                if random.random() < 0.3:
                    add_news(f"BREAKING: {npc.name} has LEFT {npc.band_name} due to creative differences!")
                    npc.band_name = None # Now a solo agent
                    npc.career_stage = "looking_for_band"

def get_news_feed():
    return NEWS_FEED
