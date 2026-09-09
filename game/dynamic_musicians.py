from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class DynamicTrack:
    title: str
    genre: str
    quality: float
    streams: int = 0


@dataclass
class AutonomousMusician:
    artist_id: str
    name: str
    band_type: str         # "SOLO_ARTIST", "DUO", "4_PIECE_BAND"
    genre: str
    skill_level: int       # 1 to 10
    fame: int              # 0 to 1000
    funds: int             # Money in USD
    current_city: str
    destination_city: Optional[str] = None
    travel_days_left: int = 0
    status: str = "TOURING" # "TOURING", "IN_TRANSIT", "RESTING", "RECORDING", "WRITING"
    energy: int = 85
    stress: int = 20
    current_poi_id: Optional[str] = None
    tour_itinerary: List[str] = field(default_factory=list) # List of city names
    catalog: List[DynamicTrack] = field(default_factory=list)
    affinity_with_player: float = 10.0 # -100 to 100
    co_headlining_with_player: bool = False
    is_signed_to_player_label: bool = False


class DynamicWorldMusiciansSystem:
    """Manages autonomous AI musicians who travel, perform, record, stay at hotels, and interact with the player."""

    CORE_CITIES = [
        "Asbury Park, NJ", "Philadelphia, PA", "New York City, NY", "London, UK",
        "Los Angeles, CA", "Nashville, TN", "Austin, TX", "Seattle, WA",
        "Berlin, Germany", "Tokyo, Japan", "Chicago, IL", "New Orleans, LA",
        "Detroit, MI", "Memphis, TN", "Atlanta, GA",
    ]

    DEFAULT_AI_MUSICIANS = [
        AutonomousMusician(
            artist_id="ai_nightjars",
            name="The Nightjars",
            band_type="4_PIECE_BAND",
            genre="Indie Rock",
            skill_level=7,
            fame=120,
            funds=4500,
            current_city="Asbury Park, NJ",
            current_poi_id="the_stone_pony",
            tour_itinerary=["Philadelphia, PA", "New York City, NY", "Boston, MA"],
            catalog=[
                DynamicTrack("Boardwalk Lanterns", "Indie Rock", 0.78, 125000),
                DynamicTrack("Atlantic Midnight", "Indie Rock", 0.82, 340000),
            ],
        ),
        AutonomousMusician(
            artist_id="ai_elena_fox",
            name="Elena Fox & The Void",
            band_type="DUO",
            genre="Post-Punk",
            skill_level=8,
            fame=180,
            funds=8500,
            current_city="London, UK",
            current_poi_id="the_100_club",
            tour_itinerary=["Berlin, Germany", "Amsterdam, Netherlands", "Paris, France"],
            catalog=[
                DynamicTrack("Cobblestone Static", "Post-Punk", 0.85, 450000),
                DynamicTrack("Thames Fog", "Post-Punk", 0.89, 890000),
            ],
        ),
        AutonomousMusician(
            artist_id="ai_jasper_clay",
            name="Jasper Clay",
            band_type="SOLO_ARTIST",
            genre="Americana",
            skill_level=8,
            fame=140,
            funds=6200,
            current_city="Nashville, TN",
            current_poi_id="ryman_auditorium",
            tour_itinerary=["Memphis, TN", "New Orleans, LA", "Austin, TX"],
            catalog=[
                DynamicTrack("Whiskey River Blues", "Americana", 0.84, 280000),
                DynamicTrack("Highway 61 Dust", "Americana", 0.88, 610000),
            ],
        ),
        AutonomousMusician(
            artist_id="ai_tokyo_drifters",
            name="Tokyo Neon Drifters",
            band_type="4_PIECE_BAND",
            genre="Synthwave",
            skill_level=9,
            fame=240,
            funds=15000,
            current_city="Tokyo, Japan",
            current_poi_id="club_quattro",
            tour_itinerary=["Los Angeles, CA", "Seattle, WA", "Chicago, IL"],
            catalog=[
                DynamicTrack("Shibuya Cyber Rain", "Synthwave", 0.91, 1200000),
                DynamicTrack("Midnight Expressway", "Synthwave", 0.94, 2400000),
            ],
        ),
        AutonomousMusician(
            artist_id="ai_velvet_echo",
            name="Velvet Echo",
            band_type="DUO",
            genre="Shoegaze",
            skill_level=7,
            fame=95,
            funds=3200,
            current_city="Philadelphia, PA",
            current_poi_id="johnny_brendas",
            tour_itinerary=["New York City, NY", "Asbury Park, NJ", "Washington, DC"],
            catalog=[
                DynamicTrack("Fuzz Dream Horizon", "Shoegaze", 0.76, 85000),
            ],
        ),
    ]

    def __init__(self):
        self.musicians: Dict[str, AutonomousMusician] = {}
        for m in self.DEFAULT_AI_MUSICIANS:
            self.musicians[m.artist_id] = AutonomousMusician(
                artist_id=m.artist_id,
                name=m.name,
                band_type=m.band_type,
                genre=m.genre,
                skill_level=m.skill_level,
                fame=m.fame,
                funds=m.funds,
                current_city=m.current_city,
                destination_city=m.destination_city,
                travel_days_left=m.travel_days_left,
                status=m.status,
                energy=m.energy,
                stress=m.stress,
                current_poi_id=m.current_poi_id,
                tour_itinerary=list(m.tour_itinerary),
                catalog=[DynamicTrack(t.title, t.genre, t.quality, t.streams) for t in m.catalog],
                affinity_with_player=m.affinity_with_player,
            )
        self.world_event_logs: List[str] = []

    def get_musicians_in_city(self, city_name: str) -> List[AutonomousMusician]:
        return [m for m in self.musicians.values() if m.current_city == city_name and m.status != "IN_TRANSIT"]

    def get_musicians_at_poi(self, poi_id: str) -> List[AutonomousMusician]:
        return [m for m in self.musicians.values() if m.current_poi_id == poi_id and m.status != "IN_TRANSIT"]

    def tick_daily_world_musicians(self) -> List[str]:
        """Runs daily AI life simulation tick for all autonomous musicians."""
        logs = []
        for m in self.musicians.values():
            # 1. If traveling along highway route
            if m.status == "IN_TRANSIT":
                m.travel_days_left -= 1
                if m.travel_days_left <= 0:
                    m.current_city = m.destination_city or m.current_city
                    m.destination_city = None
                    m.status = "TOURING"
                    m.energy = max(30, m.energy - 15)
                    arrival_msg = f"🚐 TOUR ARRIVAL: {m.name} arrived in {m.current_city} after an all-night highway drive!"
                    logs.append(arrival_msg)
                    self.world_event_logs.append(arrival_msg)
                continue

            # 2. If in a city, decide daily activity
            roll = random.random()
            if m.energy < 40:
                # Rest at motel / hotel
                m.status = "RESTING"
                m.energy = min(100, m.energy + 35)
                m.stress = max(0, m.stress - 20)
                m.funds = max(0, m.funds - 90) # Hotel cost

            elif roll < 0.45:
                # Perform an evening concert in current city
                m.status = "PERFORMING"
                m.energy = max(20, m.energy - 25)
                m.stress = min(100, m.stress + 10)
                ticket_rev = random.randint(800, 2500)
                m.funds += ticket_rev
                m.fame = min(1000, m.fame + random.randint(1, 3))
                show_msg = f"🎸 LIVE CONCERT: {m.name} performed a packed show in {m.current_city} (+${ticket_rev:,} gross)!"
                logs.append(show_msg)
                self.world_event_logs.append(show_msg)

            elif roll < 0.70 and m.tour_itinerary:
                # Depart for next city on tour itinerary
                next_city = m.tour_itinerary.pop(0)
                # re-append to loop tour
                m.tour_itinerary.append(next_city)
                m.destination_city = next_city
                m.status = "IN_TRANSIT"
                m.travel_days_left = 1
                dep_msg = f"🛣️ ON THE ROAD: {m.name} loaded their van in {m.current_city} and departed for {next_city}."
                logs.append(dep_msg)
                self.world_event_logs.append(dep_msg)

            elif roll < 0.85:
                # Write & Record in studio
                m.status = "RECORDING"
                m.energy = max(20, m.energy - 20)
                m.funds = max(0, m.funds - 400) # Studio time
                new_track_title = f"{m.name} Studio Session #{len(m.catalog)+1}"
                new_track = DynamicTrack(new_track_title, m.genre, round(random.uniform(0.70, 0.92), 2), 0)
                m.catalog.append(new_track)
                rec_msg = f"🎙️ STUDIO TRACKING: {m.name} recorded new master track '{new_track_title}' in {m.current_city}!"
                logs.append(rec_msg)
                self.world_event_logs.append(rec_msg)

            else:
                # Hang out at local diners / record shops
                m.status = "HANGING_OUT"
                m.energy = min(100, m.energy + 15)
                m.stress = max(0, m.stress - 15)

        return logs
