from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class SetlistSong:
    title: str
    genre: str
    energy_level: float  # 0.0 to 1.0 (ballad vs energetic anthem)
    quality: float
    is_hit: bool = False


@dataclass
class ConcertState:
    venue_name: str
    venue_capacity: int
    ticket_price: int
    attendance: int
    setlist: List[SetlistSong]
    current_song_index: int = 0
    crowd_hype: float = 50.0  # 0 - 100
    band_stamina: float = 100.0  # 0 - 100
    stage_presence_accum: float = 0.0
    mishap_occurred: bool = False
    encore_earned: bool = False
    encore_performed: bool = False
    total_tips: int = 0
    merch_sales: int = 0
    concert_log: List[str] = field(default_factory=list)


class LiveConcertSimulator:
    """Simulates realistic live club and arena concert dynamics, fatigue, stage banter, gear mishaps, and encores."""

    BANTER_OPTIONS = {
        "storytelling": {
            "name": "Tell Emotional Story Behind Next Song",
            "stamina_recovery": 15.0,
            "hype_mod": 8.0,
            "desc": "You share the raw origin story of the song. The audience leans in with deep respect.",
        },
        "hype_city": {
            "name": "Shout Out the City & Crowd Energy",
            "stamina_recovery": 5.0,
            "hype_mod": 15.0,
            "desc": "You scream the city name into the mic! The crowd roars back at deafening volume.",
        },
        "thank_openers": {
            "name": "Thank Local Opening Acts & Sound Crew",
            "stamina_recovery": 10.0,
            "hype_mod": 10.0,
            "desc": "You give credit to the opening band and stage techs. Street cred and good vibes ripple through the room.",
        },
        "handle_heckler": {
            "name": "Witty Comeback to Rowdy Heckler",
            "stamina_recovery": 0.0,
            "hype_mod": 18.0,
            "desc": "You deliver a sharp, hilarious comeback to a drunk heckler. The room erupts in laughter and cheers.",
        },
    }

    GEAR_MISHAPS = [
        {"name": "Snapped Guitar String", "penalty": -15.0, "roadie_saves": True, "desc": "Snap! High E string breaks during a solo."},
        {"name": "Blown Amplifier Tube", "penalty": -20.0, "roadie_saves": True, "desc": "Loud pop! Guitar tone suddenly cuts out to a buzz."},
        {"name": "Ear-Piercing Mic Feedback", "penalty": -10.0, "roadie_saves": False, "desc": "Screeching monitor feedback rings through the house."},
        {"name": "Broken Drum Bass Pedal", "penalty": -15.0, "roadie_saves": True, "desc": "The drum pedal linkage snaps mid-groove."},
    ]

    def start_concert(self, player, venue, songs: List[Any], ticket_price: int = 15) -> ConcertState:
        cap = getattr(venue, "capacity", 200)
        prestige = getattr(venue, "prestige", 2)
        fame = getattr(player, "fame", 10)
        cred = getattr(player, "street_cred", 50)

        # Realistic attendance calculation
        demand = int((fame * 4.5) + (cred * 1.5) + (prestige * 15))
        attendance = max(15, min(cap, demand))

        setlist_items = []
        for s in songs:
            qual = getattr(s, "song_quality", 0.5)
            catch = getattr(s, "catchiness", 0.5)
            energy = min(1.0, max(0.2, catch * 1.2))
            is_hit = getattr(s, "buzz_score", 0.0) > 40.0 or getattr(s, "fame", 0) > 30
            setlist_items.append(SetlistSong(
                title=getattr(s, "title", "Track"),
                genre=getattr(s, "genre", "Rock"),
                energy_level=energy,
                quality=qual,
                is_hit=is_hit,
            ))

        state = ConcertState(
            venue_name=getattr(venue, "name", "The Stage"),
            venue_capacity=cap,
            ticket_price=ticket_price,
            attendance=attendance,
            setlist=setlist_items,
        )
        state.concert_log.append(f"Walked on stage at {state.venue_name} in front of {attendance:,} fans!")
        return state

    def perform_next_song(self, player, state: ConcertState, has_roadie: bool = False) -> Dict[str, Any]:
        if state.current_song_index >= len(state.setlist):
            return {"ok": False, "explanation": "Setlist completed."}

        song = state.setlist[state.current_song_index]
        state.current_song_index += 1

        # Calculate stamina drain and hype generation
        stamina_cost = 12.0 * song.energy_level
        state.band_stamina = max(0.0, state.band_stamina - stamina_cost)

        # Performance quality modified by stamina
        stamina_factor = 0.5 + (0.5 * (state.band_stamina / 100.0))
        base_hype_gain = (song.quality * 20.0 * stamina_factor) + (10.0 if song.is_hit else 0.0)

        # Check for realistic gear mishap (8% chance)
        mishap_msg = ""
        if random.random() < 0.08 and not state.mishap_occurred:
            mishap = random.choice(self.GEAR_MISHAPS)
            state.mishap_occurred = True
            if mishap["roadie_saves"] and has_roadie:
                mishap_msg = f" ⚠️ {mishap['desc']} Your Roadie rushed a backup on stage in 5 seconds flat! (Zero hype lost!)"
            else:
                loss = mishap["penalty"]
                base_hype_gain += loss
                mishap_msg = f" ⚠️ {mishap['desc']} Awkward technical pause! ({loss:.0f} Hype)"

        state.crowd_hype = max(0.0, min(100.0, state.crowd_hype + base_hype_gain))
        log_entry = f"Played '{song.title}' ({song.genre}) -> Crowd Hype: {state.crowd_hype:.0f}% | Stamina: {state.band_stamina:.0f}%"
        if mishap_msg:
            log_entry += mishap_msg
        state.concert_log.append(log_entry)

        # Check if set is done and if encore is earned
        is_last_song = state.current_song_index >= len(state.setlist)
        if is_last_song and state.crowd_hype >= 85.0:
            state.encore_earned = True
            state.concert_log.append("🔥 ENCORE CHANT! The crowd is stomping their feet and screaming 'ONE MORE SONG!'")

        return {
            "ok": True,
            "song_played": song.title,
            "crowd_hype": state.crowd_hype,
            "band_stamina": state.band_stamina,
            "encore_earned": state.encore_earned,
            "is_set_complete": is_last_song,
            "log": log_entry,
        }

    def deliver_stage_banter(self, state: ConcertState, banter_key: str) -> Dict[str, Any]:
        banter = self.BANTER_OPTIONS.get(banter_key)
        if not banter:
            return {"ok": False, "explanation": "Unknown banter choice."}

        state.band_stamina = min(100.0, state.band_stamina + banter["stamina_recovery"])
        state.crowd_hype = min(100.0, state.crowd_hype + banter["hype_mod"])

        log_msg = f"Stage Banter: {banter['desc']} (+{banter['stamina_recovery']:.0f} Stamina, +{banter['hype_mod']:.0f} Hype)"
        state.concert_log.append(log_msg)

        return {
            "ok": True,
            "crowd_hype": state.crowd_hype,
            "band_stamina": state.band_stamina,
            "explanation": log_msg,
        }

    def perform_encore(self, player, state: ConcertState) -> Dict[str, Any]:
        if not state.encore_earned or state.encore_performed:
            return {"ok": False, "explanation": "No encore available or already played."}

        state.encore_performed = True
        state.crowd_hype = min(100.0, state.crowd_hype + 15.0)
        player.fame = min(1000, player.fame + 15)
        player.street_cred = min(100, player.street_cred + 8)

        msg = "🎸 Rushed back on stage for an electrifying Encore! The venue goes absolutely wild!"
        state.concert_log.append(msg)
        return {"ok": True, "explanation": msg, "crowd_hype": state.crowd_hype}

    def finalize_concert(self, player, state: ConcertState) -> Dict[str, Any]:
        # Ticket split (Player gets 70% of gross door after venue cut)
        gross_door = state.attendance * state.ticket_price
        artist_guarantee = int(gross_door * 0.70)

        # Merch booth conversion (15-30% of attendees buy merch)
        merch_buyers = int(state.attendance * (0.15 + (state.crowd_hype * 0.0015)))
        merch_rev = merch_buyers * 20
        tips = int(state.attendance * 0.50 * (state.crowd_hype / 100.0))

        total_earnings = artist_guarantee + merch_rev + tips
        player.money += total_earnings

        fame_gain = int((state.attendance * 0.05) * (state.crowd_hype / 100.0))
        player.fame = min(1000, player.fame + max(2, fame_gain))

        summary = (
            f"Concert Complete at {state.venue_name}!\n"
            f"- Attendance: {state.attendance:,} / {state.venue_capacity:,} fans\n"
            f"- Final Crowd Hype: {state.crowd_hype:.0f}%\n"
            f"- Door Revenue: ${artist_guarantee} (70% split)\n"
            f"- Merch Sales: ${merch_rev}\n"
            f"- Tip Jar: ${tips}\n"
            f"- Total Earnings: +${total_earnings}\n"
            f"- Fame Gain: +{fame_gain}"
        )
        state.concert_log.append(summary)

        return {
            "ok": True,
            "total_earnings": total_earnings,
            "fame_gain": fame_gain,
            "attendance": state.attendance,
            "summary": summary,
        }
