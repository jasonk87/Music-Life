class Trait:
    def __init__(self, id, name, description, effect_type, effect_value):
        self.id = id
        self.name = name
        self.description = description
        self.effect_type = effect_type # e.g., "stat_mod", "skill_bonus", "energy_decay"
        self.effect_value = effect_value

TRAIT_CATALOG = {
    "charismatic": Trait(
        "charismatic", "Charismatic",
        "You have a natural magnetism. +20% Crowd Hype gain.",
        "hype_gain_mult", 1.2
    ),
    "stage_fright": Trait(
        "stage_fright", "Stage Fright",
        "You get nervous easily. -10 Stage Presence, +20% Stress from shows.",
        "stress_gain_mult", 1.2
    ),
    "night_owl": Trait(
        "night_owl", "Night Owl",
        "You thrive at night. Energy decays 50% slower between 10PM and 4AM.",
        "night_energy_decay_mult", 0.5
    ),
    "virtuoso": Trait(
        "virtuoso", "Virtuoso",
        "You learn instruments faster. +20% Skill Gain.",
        "skill_gain_mult", 1.2
    ),
    "tone_deaf": Trait(
        "tone_deaf", "Tone Deaf",
        "You struggle with pitch. -20 Vocals skill effective value.",
        "vocals_penalty", 20
    ),
    "resilient": Trait(
        "resilient", "Resilient",
        "Life is tough, but so are you. Stress gains reduced by 20%.",
        "stress_gain_mult", 0.8
    )
}
