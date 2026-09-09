from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class LivePerformanceState:
    venue_name: str
    city_name: str
    crowd_capacity: int
    crowd_attendance: int
    ticket_price: int
    current_song_index: int = 0
    crowd_temperature: str = "WARMING_UP" # "SKEPTICAL", "RESTLESS", "WARMING_UP", "ELECTRIFIED", "TRANSCENDENT"
    hype_score: float = 50.0              # 0 to 100
    encore_triggered: bool = False
    encore_completed: bool = False
    gross_revenue: int = 0
    song_log: List[str] = field(default_factory=list)


class LiveConcertDynamicsEngine:
    """Simulates real-time mid-show concert tactics: crowd reading, setlist pivots, solos, stage banter, and encores."""

    CROWD_TEMPERATURES = ["SKEPTICAL", "RESTLESS", "WARMING_UP", "ELECTRIFIED", "TRANSCENDENT"]

    @classmethod
    def start_concert(cls, player, venue, setlist: List[Any], ticket_price: int = 25) -> LivePerformanceState:
        capacity = getattr(venue, "capacity", 250)
        fame = getattr(player, "fame", 10)
        attendance_pct = min(1.0, max(0.20, (fame * 0.002) + random.uniform(0.30, 0.60)))
        attendance = int(capacity * attendance_pct)
        gross = attendance * ticket_price

        # Initial crowd temp based on fame & venue
        initial_temp = "WARMING_UP"
        if fame < 30:
            initial_temp = "SKEPTICAL"
        elif fame > 300:
            initial_temp = "ELECTRIFIED"

        return LivePerformanceState(
            venue_name=getattr(venue, "name", "The Venue"),
            city_name=player.current_location.name if hasattr(player.current_location, "name") else "Local City",
            crowd_capacity=capacity,
            crowd_attendance=attendance,
            ticket_price=ticket_price,
            current_song_index=0,
            crowd_temperature=initial_temp,
            hype_score=60.0 if initial_temp == "ELECTRIFIED" else 40.0,
            gross_revenue=gross,
        )

    @classmethod
    def perform_song_with_tactic(cls, player, perf: LivePerformanceState, song, tactic: str = "STANDARD") -> Dict[str, Any]:
        """
        Tactics:
        - "STANDARD": Solid performance, moderate energy.
        - "SOLO_ACROBATICS": Extended guitar/synth solo or stage dive. High hype, slight mishap risk.
        - "CITY_BANTER": Dedicate song to local scene/city. Boosts local cred and stabilizes restless crowd.
        - "READ_ROOM_PIVOT": Adjust arrangement dynamically on the fly to match crowd temperature.
        """
        song_quality = getattr(song, "song_quality", 0.5)
        rec_quality = getattr(song, "recording_quality", 0.5)
        perf.current_song_index += 1

        hype_delta = 0.0
        mishap_occurred = False
        summary = ""

        if tactic == "SOLO_ACROBATICS":
            mishap_roll = random.random()
            if mishap_roll < 0.08: # 8% chance of broken string or feedback screech
                mishap_occurred = True
                hype_delta = -10.0
                player.stress = min(100, player.stress + 10)
                summary = f"🎸 SOLO MISHAP: Snapped a string during an aggressive solo on '{song.title}'! The crowd winced, but you recovered."
            else:
                hype_delta = random.uniform(18.0, 30.0)
                player.energy = max(0, player.energy - 15)
                summary = f"🔥 VIRAL SOLO: Blistered through an extended improvisational solo on '{song.title}'! The crowd erupted!"

        elif tactic == "CITY_BANTER":
            hype_delta = random.uniform(12.0, 20.0)
            player.street_cred = min(100, player.street_cred + 2)
            summary = f"🎙️ STAGE BANTER: 'What's up {perf.city_name}?! This one is for every soul on the streets tonight!' Crowd cheered in local pride."

        elif tactic == "READ_ROOM_PIVOT":
            # If crowd is cold/restless, pivot boosts by +25
            if perf.crowd_temperature in ["SKEPTICAL", "RESTLESS"]:
                hype_delta = 25.0
                perf.crowd_temperature = "WARMING_UP"
                summary = f"🔄 ROOM PIVOT: Sensed crowd restlessness and shifted tempo on '{song.title}' into an upbeat groove! Re-engaged the entire room."
            else:
                hype_delta = random.uniform(10.0, 18.0)
                summary = f"✨ SEAMLESS TRANSITION: Dynamically adjusted dynamics on '{song.title}' to ride the room's energy."

        else: # STANDARD
            base_gain = (song_quality * 15.0) + (rec_quality * 10.0)
            hype_delta = base_gain
            summary = f"🎵 PERFORMANCE: Delivered a tight, convincing rendition of '{song.title}'."

        perf.hype_score = max(0.0, min(100.0, perf.hype_score + hype_delta))

        # Update crowd temperature
        if perf.hype_score >= 85.0:
            perf.crowd_temperature = "TRANSCENDENT"
        elif perf.hype_score >= 65.0:
            perf.crowd_temperature = "ELECTRIFIED"
        elif perf.hype_score >= 40.0:
            perf.crowd_temperature = "WARMING_UP"
        elif perf.hype_score >= 20.0:
            perf.crowd_temperature = "RESTLESS"
        else:
            perf.crowd_temperature = "SKEPTICAL"

        perf.song_log.append(summary)
        return {
            "ok": True,
            "tactic": tactic,
            "hype_score": perf.hype_score,
            "crowd_temperature": perf.crowd_temperature,
            "mishap": mishap_occurred,
            "explanation": summary,
        }

    @classmethod
    def trigger_encore(cls, player, perf: LivePerformanceState, encore_song) -> Dict[str, Any]:
        if perf.hype_score < 75.0:
            return {"ok": False, "explanation": f"Crowd hype ({perf.hype_score:.0f}%) was not high enough to demand an encore (Need 75%+)."}

        perf.encore_triggered = True
        perf.encore_completed = True
        bonus_hype = 20.0
        perf.hype_score = min(100.0, perf.hype_score + bonus_hype)
        player.fame = min(1000, player.fame + 15)
        player.street_cred = min(100, player.street_cred + 10)
        bonus_rev = int(perf.gross_revenue * 0.20)
        perf.gross_revenue += bonus_rev

        summary = (
            f"🎆 ENCORE TRIUMPH: The crowd chanted your name until the house lights came back up!\n"
            f"- Performed explosive encore of '{encore_song.title}'!\n"
            f"- Final Crowd State: {perf.crowd_temperature} (Hype: {perf.hype_score:.0f}%)\n"
            f"- Merch & Tips Surge: +${bonus_rev:,} Bonus Gross, +15 Fame, +10 Street Cred!"
        )
        perf.song_log.append(summary)
        return {"ok": True, "bonus_gross": bonus_rev, "explanation": summary}
