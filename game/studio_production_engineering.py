from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class StudioEngineeringPreset:
    tracking_medium: str       # "ANALOG_2INCH_TAPE", "DIGITAL_PRO_TOOLS"
    vocal_chain: str           # "RAW_SINGLE_TAKE", "DOUBLE_TRACKED_HARMONIES", "PLATE_REVERB_TAPE_ECHO"
    mix_philosophy: str        # "WALL_OF_SOUND", "RHYTHM_SECTION_PUNCH", "RADIO_POLISH_LIMITING"


class StudioEngineeringSystem:
    """Multi-track studio tone engineering: analog tape vs digital, vocal chain layering, and mix balancing."""

    MEDIUM_SPECS = {
        "ANALOG_2INCH_TAPE": {
            "name": "Studer A800 2-Inch 24-Track Analog Tape",
            "tape_cost": 1200,
            "quality_boost": 0.12,
            "harmonic_warmth": "Rich 2nd-order analog tape saturation and transformer low-end punch.",
        },
        "DIGITAL_PRO_TOOLS": {
            "name": "192kHz 32-Bit Float Pristine Digital HD",
            "tape_cost": 0,
            "quality_boost": 0.05,
            "harmonic_warmth": "Ultra-transparent transient clarity with zero tape hiss.",
        },
    }

    VOCAL_SPECS = {
        "RAW_SINGLE_TAKE": {
            "name": "Raw Unfiltered Single-Take Lead",
            "energy_cost": 5,
            "cred_boost": 8,
            "quality_boost": 0.04,
            "desc": "Intimate, uncorrected vocal tracking prioritizing emotional honesty.",
        },
        "DOUBLE_TRACKED_HARMONIES": {
            "name": "Double-Tracked Harmonies & Vocal Stacks",
            "energy_cost": 15,
            "cred_boost": 2,
            "quality_boost": 0.09,
            "desc": "Four tight unison layers providing wide stereo width and thick chorused bloom.",
        },
        "PLATE_REVERB_TAPE_ECHO": {
            "name": "EMT 140 Plate Reverb & Space Echo",
            "energy_cost": 10,
            "cred_boost": 5,
            "quality_boost": 0.08,
            "desc": "Lush atmospheric diffusion with analog tape slapback delay.",
        },
    }

    MIX_SPECS = {
        "WALL_OF_SOUND": {
            "name": "Guitar-Heavy Wall of Sound",
            "genre_synergy": ["Rock", "Indie", "Shoegaze", "Metal", "Punk"],
            "desc": "Thick quad-tracked tube amps dominating the stereo field.",
        },
        "RHYTHM_SECTION_PUNCH": {
            "name": "Groove-Locked Rhythm Section & Sub-Bass",
            "genre_synergy": ["Hip-Hop", "Electronic", "R&B", "Funk", "Pop"],
            "desc": "Pumping sidechain compression locking the bass guitar to the kick drum.",
        },
        "RADIO_POLISH_LIMITING": {
            "name": "Radio-Ready Master Bus Limiting",
            "genre_synergy": ["Pop", "Indie Rock", "Country", "Americana"],
            "desc": "Pristine multi-band dynamic control and high-end air tuned for broadcast loudness.",
        },
    }

    @classmethod
    def engineer_master_track(
        cls,
        player,
        song,
        tracking_medium: str = "ANALOG_2INCH_TAPE",
        vocal_chain: str = "DOUBLE_TRACKED_HARMONIES",
        mix_philosophy: str = "WALL_OF_SOUND"
    ) -> Dict[str, Any]:
        med = cls.MEDIUM_SPECS.get(tracking_medium, cls.MEDIUM_SPECS["DIGITAL_PRO_TOOLS"])
        voc = cls.VOCAL_SPECS.get(vocal_chain, cls.VOCAL_SPECS["RAW_SINGLE_TAKE"])
        mix = cls.MIX_SPECS.get(mix_philosophy, cls.MIX_SPECS["WALL_OF_SOUND"])

        if player.money < med["tape_cost"]:
            return {"ok": False, "explanation": f"Need ${med['tape_cost']:,} for 2-inch tape reels."}

        player.money -= med["tape_cost"]
        player.energy = max(0, player.energy - voc["energy_cost"])
        player.street_cred = min(100, player.street_cred + voc["cred_boost"])

        # Quality boost calculations
        total_boost = med["quality_boost"] + voc["quality_boost"]
        genre = getattr(song, "genre", "Rock")
        if genre in mix["genre_synergy"]:
            total_boost += 0.06

        song.recording_quality = min(1.0, round(getattr(song, "recording_quality", 0.5) + total_boost, 2))
        song.is_recorded = True

        summary = (
            f"🎛️ STUDIO MASTER TRACKING COMPLETE: '{song.title}'!\n"
            f"- Tracking Medium: {med['name']} (-${med['tape_cost']:,})\n"
            f"  {med['harmonic_warmth']}\n"
            f"- Vocal Engineering: {voc['name']} ({voc['desc']})\n"
            f"- Mix Philosophy: {mix['name']} ({mix['desc']})\n"
            f"- Final Master Recording Quality: {song.recording_quality:.2f}/1.00 (+{total_boost:.2f} boost)!"
        )
        return {"ok": True, "song": song, "quality": song.recording_quality, "explanation": summary}
