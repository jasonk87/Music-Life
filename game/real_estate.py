from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class HomeStudioGear:
    gear_id: str
    name: str
    category: str
    cost: int
    quality_boost: float  # e.g. 0.15 = +15% recording quality
    desc: str
    installed: bool = False


@dataclass
class Property:
    property_id: str
    name: str
    city: str
    property_type: str  # "APARTMENT", "ROWHOUSE", "RANCH", "MANSION", "LOFT"
    purchase_price: int
    monthly_rent: int
    comfort_rating: int  # 0 - 100
    noise_tolerance: float  # 0.0 to 1.0 (urban apartment low vs ranch estate high)
    is_owned: bool = False
    is_rented: bool = False
    home_studio_installed: bool = False
    studio_gear: List[HomeStudioGear] = field(default_factory=list)


class RealEstateSystem:
    """Manages real estate housing purchases, monthly rentals, noise complaints, and home studio acoustic installations."""

    AVAILABLE_PROPERTIES = {
        "asbury_apt": Property(
            property_id="asbury_apt",
            name="Asbury Park Boardwalk Apartment",
            city="Asbury Park, NJ",
            property_type="APARTMENT",
            purchase_price=95000,
            monthly_rent=400,
            comfort_rating=65,
            noise_tolerance=0.30,  # Neighbors complain if you play loud drums after 9 PM
        ),
        "philly_rowhouse": Property(
            property_id="philly_rowhouse",
            name="Philadelphia Historic Brownstone Rowhouse",
            city="Philadelphia, PA",
            property_type="ROWHOUSE",
            purchase_price=250000,
            monthly_rent=1200,
            comfort_rating=80,
            noise_tolerance=0.55,
        ),
        "nashville_ranch": Property(
            property_id="nashville_ranch",
            name="Nashville Country Ranch & Barn Estate",
            city="Nashville, TN",
            property_type="RANCH",
            purchase_price=600000,
            monthly_rent=2800,
            comfort_rating=92,
            noise_tolerance=1.0,   # Isolated acreage, zero noise complaints
        ),
        "hollywood_villa": Property(
            property_id="hollywood_villa",
            name="Hollywood Hills Recording Mansion",
            city="Los Angeles, CA",
            property_type="MANSION",
            purchase_price=1800000,
            monthly_rent=7500,
            comfort_rating=98,
            noise_tolerance=0.90,
        ),
        "berlin_loft": Property(
            property_id="berlin_loft",
            name="Berlin Kreuzberg High-Ceiling Artist Loft",
            city="Berlin, Germany",
            property_type="LOFT",
            purchase_price=320000,
            monthly_rent=1500,
            comfort_rating=85,
            noise_tolerance=0.70,
        ),
    }

    STUDIO_ACOUSTIC_CATALOG = [
        HomeStudioGear("gear_bass_traps", "Acoustic Bass Traps & Diffusers", "ACOUSTICS", 450, 0.15, "Tightens low frequencies and eliminates room flutter echo."),
        HomeStudioGear("gear_tube_preamp", "Warm Audio Tube Microphone Preamp", "HARDWARE", 1200, 0.20, "Adds lush vintage harmonic saturation to vocal and guitar inputs."),
        HomeStudioGear("gear_monitors", "Yamaha HS8 Studio Reference Monitors", "MONITORING", 800, 0.15, "Crystal clear flat frequency response for precision mixing."),
        HomeStudioGear("gear_tape_machine", "16-Track 2-Inch Analog Tape Deck", "RECORDER", 4500, 0.25, "Rich tape compression that gives tracks instant golden-era warmth."),
        HomeStudioGear("gear_u87_mic", "Neumann U87 Large-Diaphragm Condenser Mic", "MICROPHONE", 3200, 0.20, "Industry gold standard for vocal presence and acoustic guitar clarity."),
    ]

    def __init__(self):
        import copy
        self.properties = {k: copy.deepcopy(v) for k, v in self.AVAILABLE_PROPERTIES.items()}
        self.properties["asbury_apt"].is_rented = True
        self.current_residence_id = "asbury_apt"

    @property
    def current_residence(self) -> Property:
        return self.properties.get(self.current_residence_id, self.properties["asbury_apt"])

    def rent_property(self, player, property_id: str) -> Dict[str, Any]:
        prop = self.properties.get(property_id)
        if not prop:
            return {"ok": False, "explanation": "Property not found."}

        first_month = prop.monthly_rent
        if player.money < first_month:
            return {"ok": False, "explanation": f"Need ${first_month} first month rent to lease {prop.name}."}

        player.money -= first_month
        # Relinquish previous rental if not owned
        prev = self.current_residence
        if prev and not prev.is_owned:
            prev.is_rented = False

        prop.is_rented = True
        self.current_residence_id = prop.property_id
        player.comfort = prop.comfort_rating

        return {
            "ok": True,
            "property": prop,
            "explanation": f"Leased {prop.name} in {prop.city} (${prop.monthly_rent}/month). Comfort set to {prop.comfort_rating}!",
        }

    def buy_property(self, player, property_id: str) -> Dict[str, Any]:
        prop = self.properties.get(property_id)
        if not prop:
            return {"ok": False, "explanation": "Property not found."}

        if prop.is_owned:
            return {"ok": False, "explanation": f"You already own {prop.name}."}

        if player.money < prop.purchase_price:
            return {"ok": False, "explanation": f"Need ${prop.purchase_price:,} to purchase {prop.name} in full."}

        player.money -= prop.purchase_price
        prop.is_owned = True
        prop.is_rented = False
        self.current_residence_id = prop.property_id
        player.comfort = prop.comfort_rating
        player.fame = min(1000, player.fame + 30)

        return {
            "ok": True,
            "property": prop,
            "explanation": f"Purchased {prop.name} in {prop.city} for ${prop.purchase_price:,}! Real Estate deed is now registered to you.",
        }

    def install_studio_gear(self, player, gear_id: str) -> Dict[str, Any]:
        res = self.current_residence
        gear_item = next((g for g in self.STUDIO_ACOUSTIC_CATALOG if g.gear_id == gear_id), None)
        if not gear_item:
            return {"ok": False, "explanation": "Acoustic gear item not found in catalog."}

        # Check if already installed in current residence
        if any(g.gear_id == gear_id for g in res.studio_gear):
            return {"ok": False, "explanation": f"{gear_item.name} is already installed in your home studio."}

        if player.money < gear_item.cost:
            return {"ok": False, "explanation": f"Need ${gear_item.cost} to buy and install {gear_item.name}."}

        player.money -= gear_item.cost
        res.home_studio_installed = True
        res.studio_gear.append(gear_item)

        return {
            "ok": True,
            "gear": gear_item,
            "explanation": f"Installed {gear_item.name} in {res.name} studio! (+{int(gear_item.quality_boost * 100)}% Recording Polish)",
        }

    def calculate_home_recording_quality(self) -> float:
        """Returns the recording quality achievable at player's home studio."""
        res = self.current_residence
        base_quality = 0.50  # Standard starter phone/mic recording
        if not res.studio_gear:
            return base_quality

        boost = sum(g.quality_boost for g in res.studio_gear)
        return min(0.95, base_quality + boost)

    def check_noise_complaint(self, hour: int) -> Optional[str]:
        """Checks if late night rehearsals (after 21:00 or before 07:00) trigger neighbor noise complaints."""
        res = self.current_residence
        is_quiet_hours = hour >= 21 or hour < 7
        if is_quiet_hours and res.noise_tolerance < 0.60:
            return f"⚠️ Noise Complaint! Neighbors in {res.name} banged on the wall due to late-night drumming during quiet hours."
        return None
