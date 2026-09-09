from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class LegendaryProducer:
    producer_id: str
    name: str
    city: str
    studio_home: str
    style_description: str
    fee_per_track: int
    quality_bonus: float
    energy_bonus: float
    resonance_bonus: float


@dataclass
class SessionMusicianUnion:
    section_id: str
    name: str
    city: str
    instruments: str
    fee_per_track: int
    complexity_boost: float
    prestige_boost: int


class ProducersAndSessionsSystem:
    """Manages location-driven Legendary Producers and elite city Session Musician hiring."""

    LEGENDARY_PRODUCERS = {
        "chicago_tape_purist": LegendaryProducer(
            producer_id="chicago_tape_purist",
            name="Steve 'The Tape Purist' (Electrical Audio style)",
            city="Chicago, IL",
            studio_home="Electrical Audio Analog Complex",
            style_description="Zero computer screens, pure 2-inch tape, visceral room mics, explosive drum transients.",
            fee_per_track=2500,
            quality_bonus=0.30,
            energy_bonus=0.35,
            resonance_bonus=0.20,
        ),
        "la_sonic_guru": LegendaryProducer(
            producer_id="la_sonic_guru",
            name="The Sonic Guru (Sunset Sound style)",
            city="Los Angeles, CA",
            studio_home="Sunset Sound Studio A (Hollywood, LA)",
            style_description="Stripping arrangements down to emotional essence, vocal coaching, timeless minimalism.",
            fee_per_track=4000,
            quality_bonus=0.35,
            energy_bonus=0.15,
            resonance_bonus=0.40,
        ),
        "london_orchestral_architect": LegendaryProducer(
            producer_id="london_orchestral_architect",
            name="The Symphonic Architect (Abbey Road style)",
            city="London, UK",
            studio_home="Abbey Road Studio Two (St John's Wood)",
            style_description="Massive orchestral string arrangements, tape loops, lush British harmonic depth.",
            fee_per_track=5000,
            quality_bonus=0.40,
            energy_bonus=0.20,
            resonance_bonus=0.35,
        ),
        "atlanta_808_hitmaker": LegendaryProducer(
            producer_id="atlanta_808_hitmaker",
            name="808 Hitmaker Labs",
            city="Atlanta, GA",
            studio_home="Trap Sound Complex (Midtown Atlanta)",
            style_description="Sub-bass that rattles car trunks, ear-candy vocal chops, precision chart radio mix.",
            fee_per_track=3500,
            quality_bonus=0.35,
            energy_bonus=0.40,
            resonance_bonus=0.25,
        ),
        "nashville_music_row_maestro": LegendaryProducer(
            producer_id="nashville_music_row_maestro",
            name="Music Row Maestro",
            city="Nashville, TN",
            studio_home="RCA Studio A Historic Hall",
            style_description="Layered acoustic guitars, silky three-part vocal harmonies, timeless analog console warmth.",
            fee_per_track=3000,
            quality_bonus=0.35,
            energy_bonus=0.20,
            resonance_bonus=0.30,
        ),
    }

    SESSION_UNIONS = {
        "london_philharmonia_strings": SessionMusicianUnion(
            section_id="london_philharmonia_strings",
            name="London Philharmonia String Quartet",
            city="London, UK",
            instruments="Cellos, Violins, Viola (16-piece string arrangement)",
            fee_per_track=1800,
            complexity_boost=0.25,
            prestige_boost=15,
        ),
        "nashville_a_team_pickers": SessionMusicianUnion(
            section_id="nashville_a_team_pickers",
            name="Nashville 'A-Team' Session Pickers",
            city="Nashville, TN",
            instruments="Pedal Steel, Mandolin, Vintage Telecaster",
            fee_per_track=1200,
            complexity_boost=0.20,
            prestige_boost=10,
        ),
        "detroit_motown_brass": SessionMusicianUnion(
            section_id="detroit_motown_brass",
            name="Motor City Funk Brass Section",
            city="Detroit, MI",
            instruments="Trumpet, Tenor Sax, Trombone Horn Trio",
            fee_per_track=1400,
            complexity_boost=0.22,
            prestige_boost=12,
        ),
        "la_hollywood_session_horns": SessionMusicianUnion(
            section_id="la_hollywood_session_horns",
            name="Hollywood Film Session Brass",
            city="Los Angeles, CA",
            instruments="French Horns, Trumpets, Orchestral Flute",
            fee_per_track=2000,
            complexity_boost=0.25,
            prestige_boost=15,
        ),
    }

    def produce_track_with_legend(self, player, song, producer_key: str) -> Dict[str, Any]:
        producer = self.LEGENDARY_PRODUCERS.get(producer_key)
        if not producer:
            return {"ok": False, "explanation": "Unknown producer."}

        loc_name = getattr(player.current_location, "name", str(player.current_location))
        if producer.city != loc_name:
            return {"ok": False, "explanation": f"You must travel to {producer.city} to record at {producer.studio_home}."}

        if player.money < producer.fee_per_track:
            return {"ok": False, "explanation": f"Need ${producer.fee_per_track:,} to hire {producer.name}."}

        player.money -= producer.fee_per_track
        song.is_recorded = True
        base_q = getattr(song, "song_quality", 0.5)
        song.recording_quality = round(min(1.0, base_q + producer.quality_bonus), 2)
        song.song_quality = round(min(1.0, base_q + (producer.resonance_bonus * 0.5)), 2)

        player.fame = min(1000, player.fame + 10)
        player.street_cred = min(100, player.street_cred + 8)

        summary = (
            f"🎛️ TRACK PRODUCED BY {producer.name} at {producer.studio_home}!\n"
            f"- Production Aesthetic: {producer.style_description}\n"
            f"- Master Recording Quality: {song.recording_quality:.2f} / 1.00\n"
            f"- Fee Paid: -${producer.fee_per_track:,}\n"
            f"- Industry Buzz: +10 Fame, +8 Street Cred"
        )
        return {"ok": True, "producer": producer, "explanation": summary}

    def hire_session_section(self, player, song, section_key: str) -> Dict[str, Any]:
        section = self.SESSION_UNIONS.get(section_key)
        if not section:
            return {"ok": False, "explanation": "Unknown session section."}

        loc_name = getattr(player.current_location, "name", str(player.current_location))
        if section.city != loc_name:
            return {"ok": False, "explanation": f"You must travel to {section.city} to track with {section.name}."}

        if player.money < section.fee_per_track:
            return {"ok": False, "explanation": f"Need ${section.fee_per_track:,} to hire {section.name}."}

        player.money -= section.fee_per_track
        curr_complexity = getattr(song, "music_complexity", 0.5)
        song.music_complexity = round(min(1.0, curr_complexity + section.complexity_boost), 2)
        player.street_cred = min(100, player.street_cred + section.prestige_boost)

        summary = (
            f"🎻 SESSION TRACKING COMPLETED with {section.name} in {section.city}!\n"
            f"- Instrumentation Added: {section.instruments}\n"
            f"- Music Complexity Boost: +{int(section.complexity_boost * 100)}%\n"
            f"- Fee Paid: -${section.fee_per_track:,}\n"
            f"- Musicianship Prestige: +{section.prestige_boost} Street Cred"
        )
        return {"ok": True, "section": section, "explanation": summary}
