from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class InventoryEntry:
    item: object
    item_id: str
    category: str
    quantity: int
    condition: int
    container: str
    location_ref: Optional[str] = None


@dataclass
class RequirementSpec:
    key: str
    match_type: str  # item_id | gear_type | semantic
    count: int = 1
    mandatory: bool = True


@dataclass
class RequirementAssessment:
    status: str
    fulfilled: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    missing_recoverable: List[str] = field(default_factory=list)
    missing_severe: List[str] = field(default_factory=list)
    details: Dict[str, str] = field(default_factory=dict)


class InventoryLoadoutService:
    def ensure_player_fields(self, player):
        if not hasattr(player, "loadouts"):
            player.loadouts = {
                "daily_carry": [
                    {"match_type": "semantic", "key": "instrument", "count": 1, "mandatory": True},
                    {"match_type": "semantic", "key": "strings", "count": 1, "mandatory": False},
                ],
                "local_gig_kit": [
                    {"match_type": "semantic", "key": "instrument", "count": 1, "mandatory": True},
                    {"match_type": "semantic", "key": "strings", "count": 1, "mandatory": True},
                ],
                "travel_kit": [
                    {"match_type": "semantic", "key": "instrument", "count": 1, "mandatory": False},
                    {"match_type": "item_id", "key": "notebook_lyrics", "count": 1, "mandatory": False},
                ],
                "tour_kit": [
                    {"match_type": "semantic", "key": "instrument", "count": 1, "mandatory": True},
                    {"match_type": "semantic", "key": "strings", "count": 2, "mandatory": True},
                ],
            }
        if not hasattr(player, "vehicle_storage"):
            player.vehicle_storage = {}  # vehicle_name -> [GearItem]
        if not hasattr(player, "temporary_stashes"):
            player.temporary_stashes = {}  # poi_id -> [GearItem]

    def build_inventory(self, player) -> List[InventoryEntry]:
        self.ensure_player_fields(player)
        entries: List[InventoryEntry] = []

        for item in player.gear_inventory:
            entries.append(self._entry(item, "on_person"))

        for item in player.home_storage:
            entries.append(self._entry(item, "home_storage"))

        for poi_id, stash_items in player.temporary_stashes.items():
            for item in stash_items:
                entries.append(self._entry(item, "temporary_lodging", location_ref=poi_id))

        for vehicle_name, vehicle_items in player.vehicle_storage.items():
            for item in vehicle_items:
                entries.append(self._entry(item, "vehicle_storage", location_ref=vehicle_name))

        return entries

    def _entry(self, item, container: str, location_ref: Optional[str] = None) -> InventoryEntry:
        return InventoryEntry(
            item=item,
            item_id=getattr(item, "item_id", "unknown_item"),
            category=getattr(item, "gear_type", "UNKNOWN"),
            quantity=1,
            condition=int(getattr(item, "durability", 100)),
            container=container,
            location_ref=location_ref,
        )

    def accessible_now(self, player, home_poi_id: Optional[str], current_poi_id: Optional[str]) -> List[InventoryEntry]:
        entries = self.build_inventory(player)
        accessible: List[InventoryEntry] = []
        for entry in entries:
            if entry.container == "on_person":
                accessible.append(entry)
            elif entry.container == "temporary_lodging" and current_poi_id and entry.location_ref == current_poi_id:
                accessible.append(entry)
            elif entry.container == "home_storage" and home_poi_id and current_poi_id == home_poi_id:
                accessible.append(entry)
            elif entry.container == "vehicle_storage":
                # Vehicle storage is accessible when player owns that vehicle and is currently at a POI.
                if current_poi_id and any(v.name == entry.location_ref for v in getattr(player, "vehicles", [])):
                    accessible.append(entry)
        return accessible

    def define_loadout(self, player, name: str, requirements: List[Dict]):
        self.ensure_player_fields(player)
        player.loadouts[name] = requirements

    def apply_loadout(self, player, name: str, home_poi_id: Optional[str], current_poi_id: Optional[str]) -> RequirementAssessment:
        self.ensure_player_fields(player)
        reqs = player.loadouts.get(name, [])
        assessment = self.assess_requirements(player, reqs, home_poi_id, current_poi_id)

        # Pull accessible stashed items onto player for convenience.
        if current_poi_id:
            pulled = []
            for item in list(player.temporary_stashes.get(current_poi_id, [])):
                if self._item_matches_any(item, reqs):
                    player.gear_inventory.append(item)
                    pulled.append(item)
            for item in pulled:
                player.temporary_stashes[current_poi_id].remove(item)

        if home_poi_id and current_poi_id == home_poi_id:
            pulled_home = []
            for item in list(player.home_storage):
                if self._item_matches_any(item, reqs):
                    player.gear_inventory.append(item)
                    pulled_home.append(item)
            for item in pulled_home:
                player.home_storage.remove(item)

        return assessment

    def _item_matches_any(self, item, requirements: List[Dict]) -> bool:
        for req in requirements:
            if self._matches(item, req.get("match_type", "item_id"), req.get("key", "")):
                return True
        return False

    def assess_requirements(self, player, requirements: List[Dict], home_poi_id: Optional[str], current_poi_id: Optional[str]) -> RequirementAssessment:
        accessible = self.accessible_now(player, home_poi_id, current_poi_id)
        status = "fully_satisfied"
        fulfilled, missing, missing_recoverable, missing_severe = [], [], [], []
        details = {}

        for req in requirements:
            needed = int(req.get("count", 1))
            match_type = req.get("match_type", "item_id")
            key = req.get("key", "")
            mandatory = bool(req.get("mandatory", True))

            count = 0
            for entry in accessible:
                if self._matches(entry.item, match_type, key):
                    if getattr(entry.item, "is_broken", False):
                        continue
                    count += entry.quantity

            if count >= needed:
                fulfilled.append(key)
                continue

            missing.append(key)
            recoverable = self._is_recoverable_requirement(key)
            if recoverable:
                missing_recoverable.append(key)
                details[key] = "missing_but_recoverable"
            elif mandatory:
                missing_severe.append(key)
                details[key] = "missing_and_severe"
            else:
                details[key] = "missing_optional"

        if missing_severe:
            status = "missing_and_severe"
        elif missing and missing_recoverable:
            status = "missing_but_recoverable"
        elif missing:
            status = "partially_satisfied"

        return RequirementAssessment(
            status=status,
            fulfilled=fulfilled,
            missing=missing,
            missing_recoverable=missing_recoverable,
            missing_severe=missing_severe,
            details=details,
        )

    def _is_recoverable_requirement(self, key: str) -> bool:
        return key in {"strings", "guitar_strings_basic"}

    def _matches(self, item, match_type: str, key: str) -> bool:
        item_id = getattr(item, "item_id", "")
        gear_type = getattr(item, "gear_type", "")
        name = getattr(item, "name", "").lower()

        if match_type == "item_id":
            return item_id == key
        if match_type == "gear_type":
            return gear_type == key
        if match_type == "semantic":
            if key == "instrument":
                return gear_type.startswith("INSTRUMENT")
            if key == "strings":
                return "string" in item_id.lower() or "string" in name
        return False
