from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class VintageHolyGrailGear:
    gear_id: str
    name: str
    city: str
    shop_location: str
    year_made: int
    category: str
    price: int
    tone_mojo_boost: float
    street_cred_boost: int
    fame_boost: int
    history_lore: str
    is_discovered: bool = False
    is_purchased: bool = False


class VintageGearNetworkSystem:
    """Manages location-driven rare vintage instrument discoveries, pawn shop finds, and collector's items."""

    VINTAGE_CATALOG = {
        "burst_59_les_paul": VintageHolyGrailGear(
            gear_id="burst_59_les_paul",
            name="1959 Gibson Les Paul Standard 'Burst'",
            city="Nashville, TN",
            shop_location="Nashville Vintage Guitars (Music Row)",
            year_made=1959,
            category="ELECTRIC_GUITAR",
            price=125000,
            tone_mojo_boost=0.40,
            street_cred_boost=25,
            fame_boost=35,
            history_lore="The Holy Grail of electric guitars. Original PAF humbuckers and flame maple top played on classic 70s rock records.",
        ),
        "strat_62_lake_placid": VintageHolyGrailGear(
            gear_id="strat_62_lake_placid",
            name="1962 Fender Stratocaster in Lake Placid Blue",
            city="Austin, TX",
            shop_location="Austin Guitar Emporium (South Congress)",
            year_made=1962,
            category="ELECTRIC_GUITAR",
            price=45000,
            tone_mojo_boost=0.35,
            street_cred_boost=20,
            fame_boost=25,
            history_lore="Slab Brazilian rosewood fretboard with chimey bell-like single coils favored by Texas blues legends.",
        ),
        "gibson_54_es295": VintageHolyGrailGear(
            gear_id="gibson_54_es295",
            name="1954 Gibson ES-295 Goldtop Hollowbody",
            city="Memphis, TN",
            shop_location="Beale Street River Pawn & Exchange",
            year_made=1954,
            category="HOLLOWBODY_GUITAR",
            price=30000,
            tone_mojo_boost=0.30,
            street_cred_boost=22,
            fame_boost=20,
            history_lore="All-gold finish with P-90 pickups, identical to Scotty Moore's guitar on the early Sun Studio recordings.",
        ),
        "roland_tr808_1980": VintageHolyGrailGear(
            gear_id="roland_tr808_1980",
            name="1980 Original Roland TR-808 Rhythm Composer",
            city="Atlanta, GA",
            shop_location="Trap Sound Complex Collector's Vault",
            year_made=1980,
            category="DRUM_MACHINE",
            price=12000,
            tone_mojo_boost=0.35,
            street_cred_boost=20,
            fame_boost=18,
            history_lore="The unmistakable boom of analog transistor bass drums that defined hip-hop, trap, and electronic music.",
        ),
        "ems_synthi_1971": VintageHolyGrailGear(
            gear_id="ems_synthi_1971",
            name="1971 EMS Synthi VCS3 Modular Synthesizer",
            city="Berlin, Germany",
            shop_location="Industrial Sound Factory (Kreuzberg)",
            year_made=1971,
            category="SYNTHESIZER",
            price=38000,
            tone_mojo_boost=0.35,
            street_cred_boost=25,
            fame_boost=20,
            history_lore="Pin-matrix patch panel synth used by Pink Floyd and Brian Eno to generate otherworldly soundscapes.",
        ),
        "shinei_fuzz_tokyo": VintageHolyGrailGear(
            gear_id="shinei_fuzz_tokyo",
            name="1970s Shin-ei Companion FY-2 Fuzz & Lawsuit Takamine",
            city="Tokyo, Japan",
            shop_location="Ochanomizu Vintage Guitar Alley",
            year_made=1973,
            category="PEDAL_INSTRUMENT",
            price=8000,
            tone_mojo_boost=0.28,
            street_cred_boost=18,
            fame_boost=15,
            history_lore="Savage, chainsaw-fuzz harmonics paired with resonant Japanese craftsmanship prized by alternative shoegaze bands.",
        ),
        "studer_a800_nyc": VintageHolyGrailGear(
            gear_id="studer_a800_nyc",
            name="1982 Studer A800 24-Track 2-Inch Master Tape Machine",
            city="New York City, NY",
            shop_location="East Village Vault & Studio Exchange",
            year_made=1982,
            category="STUDIO_RECORDER",
            price=28000,
            tone_mojo_boost=0.32,
            street_cred_boost=20,
            fame_boost=22,
            history_lore="The pinnacle of Swiss analog engineering. Imparts rich tape compression and low-end depth to entire album masters.",
        ),
    }

    def __init__(self):
        import copy
        self.catalog = {k: copy.deepcopy(v) for k, v in self.VINTAGE_CATALOG.items()}
        self.owned_grails: List[VintageHolyGrailGear] = []

    def scout_city_shops_for_vintage(self, player) -> List[VintageHolyGrailGear]:
        """Scouts current city for Holy Grail vintage gear."""
        loc_name = getattr(player.current_location, "name", str(player.current_location))
        found = []
        for item in self.catalog.values():
            if item.city == loc_name and not item.is_purchased:
                item.is_discovered = True
                found.append(item)
        return found

    def purchase_vintage_grail(self, player, gear_key: str) -> Dict[str, Any]:
        item = self.catalog.get(gear_key)
        if not item:
            return {"ok": False, "explanation": "Vintage gear item not found."}

        if item.is_purchased:
            return {"ok": False, "explanation": f"You already own {item.name}."}

        loc_name = getattr(player.current_location, "name", str(player.current_location))
        if item.city != loc_name:
            return {"ok": False, "explanation": f"You must travel to {item.city} to inspect and purchase this at {item.shop_location}."}

        if player.money < item.price:
            return {"ok": False, "explanation": f"Insufficient funds. {item.name} costs ${item.price:,}."}

        player.money -= item.price
        item.is_purchased = True
        self.owned_grails.append(item)

        player.fame = min(1000, player.fame + item.fame_boost)
        player.street_cred = min(100, player.street_cred + item.street_cred_boost)

        summary = (
            f"🎸 ACQUIRED HOLY GRAIL VINTAGE GEAR: {item.name}!\n"
            f"- Location Found: {item.shop_location} in {item.city}\n"
            f"- Price Paid: -${item.price:,}\n"
            f"- History & Provenance: {item.history_lore}\n"
            f"- Tonal Mojo Boost: +{int(item.tone_mojo_boost * 100)}%\n"
            f"- Collector Status: +{item.fame_boost} Fame, +{item.street_cred_boost} Street Cred"
        )
        return {"ok": True, "item": item, "explanation": summary}
