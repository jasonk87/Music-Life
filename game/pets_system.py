from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class AdoptedPet:
    pet_id: str
    name: str
    species: str        # "DOG", "CAT"
    breed: str
    city_adopted: str
    happiness: float = 80.0       # 0 to 100
    hunger: float = 20.0          # 0 (full) to 100 (starving)
    is_tour_companion: bool = True
    personality: str = "Playful and cuddly"


class PetsSystem:
    """Manages pet adoption from animal shelters, daily pet care, and tour bus companions."""

    SHELTER_ANIMALS = {
        "asbury_golden": {
            "species": "DOG",
            "breed": "Golden Retriever Mix",
            "city": "Asbury Park, NJ",
            "default_name": "Barnaby",
            "personality": "Goofy, loyal, loves chasing tennis balls on the beach.",
        },
        "philly_tabby": {
            "species": "CAT",
            "breed": "Domestic Short Hair Tabby",
            "city": "Philadelphia, PA",
            "default_name": "Cleo",
            "personality": "Independent, purrs loudly while you practice guitar.",
        },
        "austin_frenchie": {
            "species": "DOG",
            "breed": "French Bulldog",
            "city": "Austin, TX",
            "default_name": "Buster",
            "personality": "Calm, sleeps peacefully in the tour bus bunk.",
        },
        "seattle_collie": {
            "species": "DOG",
            "breed": "Border Collie",
            "city": "Seattle, WA",
            "default_name": "Skye",
            "personality": "Hyper-intelligent, loves mountain trail hikes.",
        },
    }

    def __init__(self):
        self.pets: List[AdoptedPet] = []

    def adopt_shelter_pet(self, player, animal_key: str, custom_name: Optional[str] = None) -> Dict[str, Any]:
        a_def = self.SHELTER_ANIMALS.get(animal_key)
        if not a_def:
            return {"ok": False, "explanation": "Animal not found in shelter directory."}

        loc_name = getattr(player.current_location, "name", str(player.current_location))
        if a_def["city"] != loc_name:
            return {"ok": False, "explanation": f"You must be in {a_def['city']} to visit this animal rescue shelter."}

        adoption_fee = 150
        if player.money < adoption_fee:
            return {"ok": False, "explanation": f"Need ${adoption_fee} adoption fee."}

        player.money -= adoption_fee
        pet_name = custom_name.strip() if custom_name and custom_name.strip() else a_def["default_name"]

        pet = AdoptedPet(
            pet_id=f"pet_{animal_key}_{len(self.pets)+1}",
            name=pet_name,
            species=a_def["species"],
            breed=a_def["breed"],
            city_adopted=a_def["city"],
            happiness=90.0,
            hunger=10.0,
            is_tour_companion=True,
            personality=a_def["personality"],
        )
        self.pets.append(pet)
        player.stress = max(0, player.stress - 25)

        summary = (
            f"🐾 ADOPTED A NEW COMPANION: {pet.name} ({pet.breed}) from {pet.city_adopted} shelter!\n"
            f"- Personality: {pet.personality}\n"
            f"- Stress reduced by 25 points. {pet.name} is now your loyal companion!"
        )
        return {"ok": True, "pet": pet, "explanation": summary}

    def care_for_pet(self, player, pet_id: str, action: str = "play_and_walk") -> Dict[str, Any]:
        """
        Actions:
        - "feed_gourmet_food": $20 (-40 Hunger, +10 Happiness)
        - "play_and_walk": $0 (+25 Happiness, -20 Player Stress, +5 Player Health)
        - "vet_checkup": $150 (Full health, +30 Happiness)
        """
        pet = next((p for p in self.pets if p.pet_id == pet_id), None)
        if not pet:
            return {"ok": False, "explanation": "Pet not found."}

        if action == "feed_gourmet_food":
            cost = 20
            if player.money < cost:
                return {"ok": False, "explanation": f"Need ${cost} for premium pet food."}
            player.money -= cost
            pet.hunger = max(0.0, pet.hunger - 40.0)
            pet.happiness = min(100.0, pet.happiness + 10.0)
            msg = f"🥩 Fed {pet.name} premium organic meals! Hunger satisfied."

        elif action == "play_and_walk":
            pet.happiness = min(100.0, pet.happiness + 25.0)
            player.stress = max(0, player.stress - 20)
            player.health = min(100, player.health + 5)
            msg = f"🎾 Took {pet.name} for an energizing walk and game of fetch in the park! (-20 Stress, +5 Health)."

        elif action == "vet_checkup":
            cost = 150
            if player.money < cost:
                return {"ok": False, "explanation": f"Need ${cost} for veterinary wellness exam."}
            player.money -= cost
            pet.happiness = 100.0
            pet.hunger = 10.0
            msg = f"🩺 Veterinary checkup and vaccinations completed for {pet.name}! Full clean bill of health."
        else:
            return {"ok": False, "explanation": "Unknown care action."}

        return {"ok": True, "pet": pet, "explanation": msg}
