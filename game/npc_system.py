from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class NPC:
    npc_id: str
    name: str
    city: str
    poi_id: str
    role: str               # "BOOKER", "ENGINEER", "VINYL_CLERK", "MUSICIAN", "JOURNALIST", "ROADIE"
    bio: str
    personality_trait: str
    favorite_gifts: List[str]
    affinity: float = 10.0   # -100 to 100
    respect: float = 10.0    # 0 to 100
    favors_available: int = 1
    favors_used: int = 0
    memories: List[str] = field(default_factory=list)

    @property
    def relationship_tier(self) -> str:
        if self.affinity >= 80.0:
            return "LIFELONG_CONFIDANT"
        elif self.affinity >= 50.0:
            return "TRUSTED_ALLY"
        elif self.affinity >= 20.0:
            return "FRIENDLY"
        elif self.affinity >= -20.0:
            return "ACQUAINTANCE"
        else:
            return "HOSTILE"


class NPCSystem:
    """Manages the directory of living NPCs across 15 cities, conversations, gifts, and social memory."""

    DEFAULT_NPCS = {
        "sal_moretti": NPC(
            npc_id="sal_moretti",
            name="Sal 'The Gatekeeper' Moretti",
            city="Asbury Park, NJ",
            poi_id="the_stone_pony",
            role="BOOKER",
            bio="Gruff, cigarette-smoking booking manager who has run the club since 1978. Hard to impress but fiercely loyal to real musicians.",
            personality_trait="Blunt, nostalgic, values punctuality and sweat on stage.",
            favorite_gifts=["vintage_whiskey", "boardwalk_salt_water_taffy", "analog_guitar_pedal"],
        ),
        "gary_sterling": NPC(
            npc_id="gary_sterling",
            name="Gary 'Tape Head' Sterling",
            city="New York City, NY",
            poi_id="electric_lady_studios",
            role="ENGINEER",
            bio="Grammy-winning chief analog tracking engineer who worked with classic 70s legends.",
            personality_trait="Audio purist, obsessive about 2-inch tape saturation and tube mics.",
            favorite_gifts=["rare_vacuum_tubes", "italian_espresso_beans", "first_pressing_vinyl"],
        ),
        "chloe_sinclair": NPC(
            npc_id="chloe_sinclair",
            name="Chloe 'Velvet' Sinclair",
            city="Los Angeles, CA",
            poi_id="troubadour",
            role="BOOKER",
            bio="Tastemaker talent buyer who discovers the next big breakthrough indie acts on the Sunset Strip.",
            personality_trait="Charismatic, sharp eye for stage charisma and songwriting hooks.",
            favorite_gifts=["matcha_tea_set", "backstage_vip_pass", "limited_tour_poster"],
        ),
        "yuki_takahashi": NPC(
            npc_id="yuki_takahashi",
            name="Yuki Takahashi",
            city="Tokyo, Japan",
            poi_id="disk_union_shibuya",
            role="VINYL_CLERK",
            bio="Legendary Shibuya crate-digger with encyclopedic knowledge of rare Japanese city pop and 70s psych vinyl.",
            favorite_gifts=["first_pressing_vinyl", "artisanal_green_tea", "vintage_guitar_pick"],
            personality_trait="Quiet, deeply respectful of dedicated music collectors.",
        ),
        "hans_richter": NPC(
            npc_id="hans_richter",
            name="Hans 'Kraut' Richter",
            city="Berlin, Germany",
            poi_id="hansa_tonstudio",
            role="ENGINEER",
            bio="Modular synth designer and ambient tape looping pioneer who lived through the Berlin underground era.",
            favorite_gifts=["rare_vacuum_tubes", "german_craft_beer", "synth_patch_cables"],
            personality_trait="Experimental, philosophical, hates cookie-cutter commercial pop.",
        ),
        "earl_montgomery": NPC(
            npc_id="earl_montgomery",
            name="Earl 'Pappy' Montgomery",
            city="Nashville, TN",
            poi_id="ryman_auditorium",
            role="MUSICIAN",
            bio="Grand Ole Opry veteran acoustic flatpicker and master luthier who knows every song in the American songbook.",
            favorite_gifts=["handmade_bone_picks", "bourbon_whiskey", "vintage_strap"],
            personality_trait="Warm, storytelling mentor who respects instrumental mastery.",
        ),
        "marcus_vance": NPC(
            npc_id="marcus_vance",
            name="Marcus 'Sticks' Vance",
            city="London, UK",
            poi_id="the_100_club",
            role="BOOKER",
            bio="Sarcastic punk veteran promoter in Soho who ran underground DIY gigs in London during the 80s.",
            favorite_gifts=["english_tea_tin", "punk_fanzine", "vintage_fuzz_pedal"],
            personality_trait="Dry British wit, hates arrogant rockstars, loves raw energy.",
        ),
        "rex_robinson": NPC(
            npc_id="rex_robinson",
            name="Rex 'Blind Dog' Robinson",
            city="Memphis, TN",
            poi_id="sun_studio",
            role="MUSICIAN",
            bio="Beale Street blues harp virtuoso with 50 years of road stories across the Mississippi Delta.",
            favorite_gifts=["harmonica_set", "memphis_dry_rub", "vintage_whiskey"],
            personality_trait="Soulful, generous with musical tips, tells mesmerizing stories.",
        ),
    }

    def __init__(self):
        self.npcs: Dict[str, NPC] = {}
        for k, n in self.DEFAULT_NPCS.items():
            self.npcs[k] = NPC(
                npc_id=n.npc_id,
                name=n.name,
                city=n.city,
                poi_id=n.poi_id,
                role=n.role,
                bio=n.bio,
                personality_trait=n.personality_trait,
                favorite_gifts=list(n.favorite_gifts),
                affinity=n.affinity,
                respect=n.respect,
                favors_available=n.favors_available,
                favors_used=n.favors_used,
                memories=[],
            )

    def get_npcs_in_city(self, city_name: str) -> List[NPC]:
        return [npc for npc in self.npcs.values() if npc.city == city_name]

    def get_npc(self, npc_id: str) -> Optional[NPC]:
        return self.npcs.get(npc_id)

    def talk_with_npc(self, player, npc_id: str, topic: str = "music_scene") -> Dict[str, Any]:
        npc = self.npcs.get(npc_id)
        if not npc:
            return {"ok": False, "explanation": "NPC not found."}

        loc_name = getattr(player.current_location, "name", str(player.current_location))
        if npc.city != loc_name:
            return {"ok": False, "explanation": f"{npc.name} is in {npc.city}, you are in {loc_name}."}

        if topic == "music_scene":
            npc.affinity = min(100.0, npc.affinity + 5.0)
            npc.respect = min(100.0, npc.respect + 3.0)
            dialogue = f"{npc.name}: 'The scene around here has seen a lot of folks come and go, but passion never lies. Keep your head down and stay honest with your chords.'"
        elif topic == "gear_talk":
            npc.affinity = min(100.0, npc.affinity + 8.0)
            npc.respect = min(100.0, npc.respect + 5.0)
            dialogue = f"{npc.name}: 'You know what you're talking about. True tone isn't in fancy knobs—it's in the fingers and the air between the speaker and the mic.'"
        else:
            npc.affinity = min(100.0, npc.affinity + 10.0)
            dialogue = f"{npc.name}: 'Good to share a quiet moment and a laugh. The road can wear anyone down—stay centered, kid.'"

        player.stress = max(0, player.stress - 10)
        memory = f"Day {current_game_time.day}: Shared a meaningful conversation with {player.name} about {topic.replace('_', ' ')}."
        npc.memories.append(memory)

        summary = (
            f"🗣️ TALKED WITH {npc.name} ({npc.role}) in {npc.city}\n"
            f"💬 {dialogue}\n"
            f"- Affinity: {npc.affinity:.0f}/100 ({npc.relationship_tier}) | Respect: {npc.respect:.0f}/100\n"
            f"- Stress reduced by 10 points."
        )
        return {"ok": True, "npc": npc, "explanation": summary}

    def give_gift_to_npc(self, player, npc_id: str, gift_key: str) -> Dict[str, Any]:
        npc = self.npcs.get(npc_id)
        if not npc:
            return {"ok": False, "explanation": "NPC not found."}

        loc_name = getattr(player.current_location, "name", str(player.current_location))
        if npc.city != loc_name:
            return {"ok": False, "explanation": f"{npc.name} is in {npc.city}, you are in {loc_name}."}

        gift_costs = {
            "vintage_whiskey": 80,
            "rare_vacuum_tubes": 150,
            "first_pressing_vinyl": 120,
            "matcha_tea_set": 60,
            "backstage_vip_pass": 0,
            "handmade_bone_picks": 35,
            "english_tea_tin": 25,
            "harmonica_set": 95,
            "general_coffee": 15,
        }
        cost = gift_costs.get(gift_key, 50)
        if player.money < cost:
            return {"ok": False, "explanation": f"Need ${cost} to purchase {gift_key.replace('_', ' ').title()}."}

        player.money -= cost
        is_favorite = gift_key in npc.favorite_gifts

        if is_favorite:
            affinity_boost = 25.0
            respect_boost = 15.0
            reaction = f"{npc.name}: 'Are you kidding me? {gift_key.replace('_', ' ').title()}?! You really know what makes me tick. I won't forget this!'"
        else:
            affinity_boost = 10.0
            respect_boost = 5.0
            reaction = f"{npc.name}: 'Thank you! That is very kind and thoughtful of you.'"

        npc.affinity = min(100.0, npc.affinity + affinity_boost)
        npc.respect = min(100.0, npc.respect + respect_boost)

        memory = f"Day {current_game_time.day}: {player.name} gifted me {gift_key.replace('_', ' ')}."
        npc.memories.append(memory)

        summary = (
            f"🎁 GAVE GIFT TO {npc.name}: {gift_key.replace('_', ' ').title()} (-${cost})\n"
            f"💬 {reaction}\n"
            f"- Affinity: +{affinity_boost:.0f} (Now {npc.affinity:.0f}/100) [{npc.relationship_tier}]\n"
            f"- Respect: +{respect_boost:.0f} (Now {npc.respect:.0f}/100)"
        )
        return {"ok": True, "npc": npc, "explanation": summary}
