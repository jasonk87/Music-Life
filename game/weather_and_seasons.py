from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class CityWeatherReport:
    city: str
    season: str            # "SPRING", "SUMMER", "AUTUMN", "WINTER"
    condition: str         # "CLEAR", "RAIN_DRIZZLE", "THUNDERSTORM", "BLIZZARD", "HEATWAVE", "CHERRY_BLOSSOM_BREEZE"
    temperature_f: int
    travel_impact: str
    atmosphere_lore: str


class WeatherAndSeasonsSystem:
    """Manages 4 distinct seasons, realistic city climates, and extreme weather travel impacts."""

    CLIMATE_ZONES = {
        "Chicago, IL": {"winter_blizzard_prob": 0.35, "summer_heat_prob": 0.20, "base_temp": 50},
        "Berlin, Germany": {"winter_blizzard_prob": 0.30, "summer_heat_prob": 0.15, "base_temp": 48},
        "New York City, NY": {"winter_blizzard_prob": 0.25, "summer_heat_prob": 0.25, "base_temp": 55},
        "London, UK": {"rain_prob": 0.45, "winter_blizzard_prob": 0.05, "base_temp": 52},
        "Seattle, WA": {"rain_prob": 0.50, "winter_blizzard_prob": 0.08, "base_temp": 51},
        "Austin, TX": {"summer_heat_prob": 0.55, "winter_blizzard_prob": 0.02, "base_temp": 72},
        "New Orleans, LA": {"summer_heat_prob": 0.50, "rain_prob": 0.35, "base_temp": 70},
        "Los Angeles, CA": {"summer_heat_prob": 0.30, "clear_prob": 0.70, "base_temp": 68},
        "Tokyo, Japan": {"spring_sakura_prob": 0.60, "summer_heat_prob": 0.30, "base_temp": 58},
        "Nashville, TN": {"summer_heat_prob": 0.30, "rain_prob": 0.25, "base_temp": 60},
        "Asbury Park, NJ": {"coastal_breeze_prob": 0.40, "winter_blizzard_prob": 0.20, "base_temp": 54},
        "Philadelphia, PA": {"winter_blizzard_prob": 0.22, "summer_heat_prob": 0.25, "base_temp": 56},
        "Memphis, TN": {"summer_heat_prob": 0.35, "rain_prob": 0.25, "base_temp": 62},
        "Detroit, MI": {"winter_blizzard_prob": 0.32, "summer_heat_prob": 0.18, "base_temp": 49},
        "Atlanta, GA": {"summer_heat_prob": 0.40, "rain_prob": 0.25, "base_temp": 65},
    }

    def __init__(self):
        self.cached_weather: Dict[str, CityWeatherReport] = {}

    def get_current_season(self) -> str:
        month = getattr(current_game_time, "month", 1)
        if month in [3, 4, 5]:
            return "SPRING"
        elif month in [6, 7, 8]:
            return "SUMMER"
        elif month in [9, 10, 11]:
            return "AUTUMN"
        else:
            return "WINTER"

    def get_city_weather(self, city_name: str) -> CityWeatherReport:
        season = self.get_current_season()
        clim = self.CLIMATE_ZONES.get(city_name, {"base_temp": 55})

        if season == "WINTER":
            temp = clim.get("base_temp", 50) - 25
            if clim.get("winter_blizzard_prob", 0.1) > 0.20:
                condition = "BLIZZARD"
                travel = "Heavy snowfall! Highway speeds reduced by 30%, charter flights grounded."
                lore = "Snow plows rumbling outside while steam rises from manholes and venue alleyways."
            else:
                condition = "CLEAR_COLD"
                travel = "Chilly conditions, normal transit operational."
                lore = "Crisp winter air, breath visible in frosty venue doorways."

        elif season == "SUMMER":
            temp = clim.get("base_temp", 50) + 25
            if clim.get("summer_heat_prob", 0.2) > 0.30:
                condition = "HEATWAVE"
                travel = "Scorching asphalt! Vehicle engine cooling under high load."
                lore = "Shimmering heatwaves above the pavement, outdoor beer gardens packed with fans."
            else:
                condition = "CLEAR_WARM"
                travel = "Sunny, optimal highway driving."
                lore = "Warm summer breeze, golden hour sunlight reflecting off venue marquees."

        elif season == "SPRING":
            temp = clim.get("base_temp", 50)
            if "Tokyo" in city_name:
                condition = "CHERRY_BLOSSOM_BREEZE"
                travel = "Festive seasonal crowds, optimal transit."
                lore = "Pink sakura petals drifting along Shibuya avenues and neon alleyways."
            else:
                condition = "CLEAR_MILD"
                travel = "Pleasant spring conditions."
                lore = "Fresh spring energy, indie record stores opening front windows to the sidewalk."

        else: # AUTUMN
            temp = clim.get("base_temp", 50) - 5
            if clim.get("rain_prob", 0.2) > 0.35:
                condition = "RAIN_DRIZZLE"
                travel = "Wet roads, careful highway braking required."
                lore = "Atmospheric rain pattering against diner windows, wet cobblestones reflecting streetlamps."
            else:
                condition = "CRISP_AUTUMN"
                travel = "Cool, clear tour highway weather."
                lore = "Amber fall foliage, cozy coffee shops and packed acoustic venue evenings."

        report = CityWeatherReport(
            city=city_name,
            season=season,
            condition=condition,
            temperature_f=temp,
            travel_impact=travel,
            atmosphere_lore=lore,
        )
        self.cached_weather[city_name] = report
        return report
