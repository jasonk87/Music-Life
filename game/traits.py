from typing import Dict, Any


class Trait:
    def __init__(self, id: str, name: str, description: str, effect_type: str, effect_value: float):
        self.id = id
        self.name = name
        self.description = description
        self.effect_type = effect_type  # e.g. "stat_mod", "skill_bonus", "energy_decay", "hype_mult"
        self.effect_value = effect_value

    def __str__(self):
        return f"{self.name}: {self.description}"


TRAIT_CATALOG: Dict[str, Trait] = {
    "charismatic": Trait(
        "charismatic", "Charismatic Frontperson",
        "Natural magnetic stage charm. +20% crowd hype gain from live performances.",
        "hype_gain_mult", 1.20,
    ),
    "virtuoso": Trait(
        "virtuoso", "Virtuoso Multi-Instrumentalist",
        "Musical polymath with innate ear for pitch and scales. +25% instrumental skill gain.",
        "skill_gain_mult", 1.25,
    ),
    "audiophile_perfectionist": Trait(
        "audiophile_perfectionist", "Audiophile Perfectionist",
        "Obsessive attention to acoustic fidelity and frequency separation. +15% recording quality bonus.",
        "recording_quality_mult", 1.15,
    ),
    "night_owl": Trait(
        "night_owl", "Night Owl",
        "Thrives in late-night clubs and midnight studio lockouts. 50% slower energy decay past 10 PM.",
        "night_energy_decay_mult", 0.50,
    ),
    "resilient_road_dog": Trait(
        "resilient_road_dog", "Resilient Road Dog",
        "Hardened by years of roughing it on the road. Stress gains reduced by 25%.",
        "stress_gain_mult", 0.75,
    ),
    "diy_workhorse": Trait(
        "diy_workhorse", "DIY Workhorse",
        "Self-reliant underground hustler. Merch production and venue booking costs reduced by 20%.",
        "diy_cost_reduction_mult", 0.80,
    ),
    "analog_purist": Trait(
        "analog_purist", "Analog Tape Purist",
        "Devoted to genuine vacuum tubes, transformer warmth, and vinyl. +15 Street Cred boost on album releases.",
        "purist_cred_bonus", 15.0,
    ),
    "improvisational_wizard": Trait(
        "improvisational_wizard", "Improvisational Wizard",
        "Effortlessly invents jaw-dropping solos and stage banter on the fly. Concert mishap chance reduced to 0.",
        "zero_mishap_bonus", 1.0,
    ),
    "stage_fright": Trait(
        "stage_fright", "Stage Fright",
        "Gets nervous under blinding stage lights. +20% stress gain during live concerts.",
        "stress_gain_mult", 1.20,
    ),
    "studio_hermit": Trait(
        "studio_hermit", "Studio Hermit",
        "Flourishes alone at the mixing desk, but feels drained by massive festival crowds.",
        "introvert_mult", 1.15,
    ),
    "tone_deaf": Trait(
        "tone_deaf", "Tone Deaf (Flaw)",
        "Struggles with subtle vocal microtones. -20 Vocals skill effective cap.",
        "vocals_penalty", 20.0,
    ),
    "restless_nomad": Trait(
        "restless_nomad", "Restless Nomad",
        "Cannot stand staying in one city for more than a week. Homesickness meter disabled while touring.",
        "no_homesickness", 1.0,
    ),
}

# Aliases for backward compatibility
TRAIT_CATALOG["resilient"] = TRAIT_CATALOG["resilient_road_dog"]

