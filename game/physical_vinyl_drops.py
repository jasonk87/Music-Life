from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class DirectVinylDrop:
    drop_id: str
    album_title: str
    variant_name: str     # "Seafoam Marble 180g", "Blood Orange Splatter", "Opaque White"
    units_total: int
    units_remaining: int
    unit_price: int = 35
    total_revenue_earned: int = 0
    is_sold_out: bool = False


@dataclass
class RecordStoreConsignment:
    store_name: str
    city_name: str
    album_title: str
    units_consigned: int
    units_sold: int = 0
    wholesale_rate: int = 18
    total_payout: int = 0


class PhysicalVinylDropSystem:
    """Manages D2C online webstore drops and indie record shop consignment networks."""

    ICONIC_RECORD_STORES = [
        {"city": "Asbury Park, NJ", "store": "Hold Fast Records & Vintage Vault"},
        {"city": "Philadelphia, PA", "store": "Repo Records South Street"},
        {"city": "New York City, NY", "store": "Generation Records Greenwich Village"},
        {"city": "Nashville, TN", "store": "Grimey's Too Music & Books"},
        {"city": "Austin, TX", "store": "Waterloo Records 6th St"},
        {"city": "Los Angeles, CA", "store": "Amoeba Music Hollywood"},
        {"city": "Seattle, WA", "store": "Easy Street Records West Seattle"},
        {"city": "London, UK", "store": "Rough Trade East Brick Lane"},
        {"city": "Tokyo, Japan", "store": "Disk Union Shibuya Underground"},
        {"city": "Berlin, Germany", "store": "Space Hall Berlin Vinyl Archive"},
    ]

    def __init__(self):
        self.active_webstore_drops: List[DirectVinylDrop] = []
        self.consignments: List[RecordStoreConsignment] = []
        self.total_vinyl_drop_revenue: int = 0

    def launch_webstore_variant_drop(
        self,
        player,
        album_title: str,
        variant_name: str = "Limited Seafoam Marble 180g",
        units: int = 150,
        unit_price: int = 38
    ) -> Dict[str, Any]:
        drop = DirectVinylDrop(
            drop_id=f"drop_{len(self.active_webstore_drops)+1}",
            album_title=album_title,
            variant_name=variant_name,
            units_total=units,
            units_remaining=units,
            unit_price=unit_price,
            total_revenue_earned=0,
            is_sold_out=False,
        )

        # Calculate initial frenzy sales based on player fame
        fame = getattr(player, "fame", 10)
        frenzy_units = min(units, int((fame * 0.40) + random.randint(15, 45)))
        drop.units_remaining -= frenzy_units
        initial_rev = frenzy_units * unit_price
        drop.total_revenue_earned += initial_rev
        self.total_vinyl_drop_revenue += initial_rev
        player.money += initial_rev
        if drop.units_remaining <= 0:
            drop.is_sold_out = True
            drop.units_remaining = 0

        self.active_webstore_drops.append(drop)
        player.fame = min(1000, player.fame + 10)
        player.street_cred = min(100, player.street_cred + 8)

        status_txt = "SOLD OUT IN 4 MINUTES!" if drop.is_sold_out else f"{drop.units_remaining}/{units} units remaining"
        summary = (
            f"📦 LAUNCHED D2C VINYL WEBSTORE DROP: '{album_title}' ({variant_name})!\n"
            f"- Edition Size: {units} Hand-Numbered Copies at ${unit_price} each\n"
            f"- Launch Frenzy Sales: {frenzy_units} units sold instantly (+${initial_rev:,} gross)\n"
            f"- Inventory Status: {status_txt}\n"
            f"- Brand Momentum: +10 Fame, +8 Street Cred"
        )
        return {"ok": True, "drop": drop, "initial_sales": frenzy_units, "explanation": summary}

    def consign_records_to_local_store(
        self,
        player,
        store_name: str,
        city_name: str,
        album_title: str,
        units: int = 25
    ) -> Dict[str, Any]:
        consign = RecordStoreConsignment(
            store_name=store_name,
            city_name=city_name,
            album_title=album_title,
            units_consigned=units,
            units_sold=0,
            wholesale_rate=18,
            total_payout=0,
        )
        self.consignments.append(consign)
        player.street_cred = min(100, player.street_cred + 5)

        summary = (
            f"🏬 CONSIGNED VINYL AT {store_name} ({city_name})!\n"
            f"- Stocked: {units}x 180g Vinyl copies of '{album_title}' in the New Releases bin.\n"
            f"- Wholesale Terms: ${consign.wholesale_rate}/copy upon customer sale\n"
            f"- Local Scene Cred: +5 Street Cred in {city_name}!"
        )
        return {"ok": True, "consignment": consign, "explanation": summary}

    def process_weekly_consignment_sales(self, player) -> List[str]:
        logs = []
        for c in self.consignments:
            if c.units_sold < c.units_consigned:
                unsold = c.units_consigned - c.units_sold
                sold_this_week = min(unsold, random.randint(3, 10))
                if sold_this_week > 0:
                    payout = sold_this_week * c.wholesale_rate
                    c.units_sold += sold_this_week
                    c.total_payout += payout
                    player.money += payout
                    logs.append(f"🏬 CONSIGNMENT PAYOUT: {c.store_name} sold {sold_this_week} copies of '{c.album_title}' (+${payout:,}).")
        return logs
