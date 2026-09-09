from typing import Dict, List, Any

THEME_CATALOG: Dict[str, Dict[str, Any]] = {
    "love": {
        "name": "Love & Romance",
        "description": "Songs about magnetic intimacy, passionate romance, and devotion.",
        "genre_affinity": ["Pop", "R&B", "Folk", "Indie"],
        "bonus_multiplier": 1.15,
    },
    "heartbreak": {
        "name": "Heartbreak & Loss",
        "description": "Melancholic laments on broken trust, separation, and mourning.",
        "genre_affinity": ["Blues", "Indie", "Folk", "Americana", "Pop"],
        "bonus_multiplier": 1.15,
    },
    "rebellion": {
        "name": "Rebellion & Anti-Establishment",
        "description": "Fiery anthems raging against corporate power and societal hypocrisy.",
        "genre_affinity": ["Rock", "Punk", "Metal", "Alternative", "Hip-Hop"],
        "bonus_multiplier": 1.20,
    },
    "party": {
        "name": "Party & Nightlife Catharsis",
        "description": "High-octane floor-fillers celebrating wild nights and euphoria.",
        "genre_affinity": ["Pop", "Electronic", "Dance", "Hip-Hop"],
        "bonus_multiplier": 1.15,
    },
    "introspection": {
        "name": "Introspection & Existentialism",
        "description": "Deep psychological excavations of memory, mortality, and identity.",
        "genre_affinity": ["Indie", "Folk", "Shoegaze", "Alternative"],
        "bonus_multiplier": 1.15,
    },
    "cyberpunk_dystopia": {
        "name": "Cyberpunk Dystopia & Neon Paranoia",
        "description": "Cinematic narratives of synthetic cities, cybernetic hackers, and high-tech alienation.",
        "genre_affinity": ["Electronic", "Synthwave", "Industrial", "Alternative"],
        "bonus_multiplier": 1.20,
    },
    "blue_collar_struggle": {
        "name": "Working-Class Blue Collar Blues",
        "description": "Grounded grit documenting factory shifts, unpaid debts, and small-town survival.",
        "genre_affinity": ["Americana", "Blues", "Folk", "Rock"],
        "bonus_multiplier": 1.20,
    },
    "gothic_noir": {
        "name": "Gothic Noir & Dark Mystery",
        "description": "Atmospheric shadows, fog-drenched streets, velvet doom, and fatal romance.",
        "genre_affinity": ["Post-Punk", "Gothic Rock", "Shoegaze", "Alternative"],
        "bonus_multiplier": 1.20,
    },
    "summer_nostalgia": {
        "name": "Summer Nostalgia & Golden Hour",
        "description": "Warm memories of coastal road trips, teenage boardwalks, and youth.",
        "genre_affinity": ["Indie Rock", "Pop", "Surf Rock", "Folk"],
        "bonus_multiplier": 1.15,
    },
    "road_freedom": {
        "name": "Highway Drift & Road Freedom",
        "description": "The open highway, midnight gas stations, and escape from routine.",
        "genre_affinity": ["Rock", "Americana", "Country", "Blues"],
        "bonus_multiplier": 1.18,
    },
    "cosmic_psychedelia": {
        "name": "Cosmic Psychedelia & Transcendence",
        "description": "Mind-expanding astral journeys, swirling colors, and mystical visions.",
        "genre_affinity": ["Psychedelic Rock", "Prog Rock", "Shoegaze", "Electronic"],
        "bonus_multiplier": 1.22,
    },
    "fantasy": {
        "name": "Mythology & Ancient Fantasy",
        "description": "Epic allegorical lore of dragons, sea voyagers, and forgotten kingdoms.",
        "genre_affinity": ["Prog Rock", "Metal", "Folk"],
        "bonus_multiplier": 1.15,
    },
}
