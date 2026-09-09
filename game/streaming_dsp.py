from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class PlaylistPlacement:
    playlist_id: str
    name: str
    curator_type: str  # "EDITORIAL", "ALGORITHMIC", "USER_CURATED"
    genre: str
    reach_followers: int
    daily_streams_boost: int
    days_remaining: int = 14


@dataclass
class TrackStreamingData:
    song_id: str
    title: str
    genre: str
    total_streams: int = 0
    daily_streams: int = 0
    total_royalties_earned: float = 0.0
    active_playlists: List[PlaylistPlacement] = field(default_factory=list)
    release_day: int = 0
    organic_streams: int = 0
    production_quality: float = 0.5
    pitch_dates: Dict[str, int] = field(default_factory=dict)


class StreamingPlatformSystem:
    """Simulates real-world digital streaming platform algorithms, editorial playlists, and $0.0035/stream royalties."""

    ROYALTY_RATE_PER_STREAM = 0.0035  # Realistic industry standard rate

    CURATED_PLAYLISTS = [
        {"id": "pl_indie_radar", "name": "Indie Radar", "type": "EDITORIAL", "genre": "Indie", "reach": 150000, "boost": 2500, "min_qual": 0.60},
        {"id": "pl_rock_essentials", "name": "Heavy Rock Essentials", "type": "EDITORIAL", "genre": "Rock", "reach": 350000, "boost": 6000, "min_qual": 0.70},
        {"id": "pl_acoustic_mornings", "name": "Acoustic Mornings", "type": "EDITORIAL", "genre": "Folk", "reach": 200000, "boost": 3500, "min_qual": 0.65},
        {"id": "pl_new_music_friday", "name": "New Music Friday", "type": "EDITORIAL", "genre": "All", "reach": 1200000, "boost": 20000, "min_qual": 0.80},
        {"id": "pl_algo_discover", "name": "Discover Weekly Engine", "type": "ALGORITHMIC", "genre": "All", "reach": 50000, "boost": 1200, "min_qual": 0.50},
    ]

    def __init__(self):
        self.catalog: Dict[str, TrackStreamingData] = {}
        self.accumulated_unpaid_royalties: float = 0.0

    def register_song_for_streaming(self, song, initial_fame: int = 0) -> TrackStreamingData:
        sid = getattr(song, "song_id", str(uuid.uuid4()))
        if sid in self.catalog:
            return self.catalog[sid]

        # Initial launch stream burst
        quality = getattr(song, "song_quality", 0.5)
        rec_qual = getattr(song, "recording_quality", 0.5)
        buzz = getattr(song, "buzz_score", 0.0)

        initial_daily = max(2, int((quality * 65 + rec_qual * 65) * (1 + initial_fame / 20) + buzz * 8))
        track_data = TrackStreamingData(
            song_id=sid,
            title=getattr(song, "title", "Untitled"),
            genre=getattr(song, "genre", "Indie"),
            total_streams=0,
            daily_streams=initial_daily,
            release_day=current_game_time.day_index(),
            organic_streams=initial_daily,
            production_quality=(quality + rec_qual) / 2,
        )

        self.catalog[sid] = track_data
        return track_data

    def pitch_to_editorial_playlist(self, player, song_id: str, playlist_id: str) -> Dict[str, Any]:
        track = self.catalog.get(song_id)
        if not track:
            return {"ok": False, "explanation": "Track not registered in streaming catalog."}

        target_pl = next((p for p in self.CURATED_PLAYLISTS if p["id"] == playlist_id), None)
        if not target_pl:
            return {"ok": False, "explanation": f"Unknown playlist ID '{playlist_id}'."}

        # Check if already placed
        if any(p.playlist_id == playlist_id for p in track.active_playlists):
            return {"ok": False, "explanation": f"'{track.title}' is already featured on {target_pl['name']}."}

        today = current_game_time.day_index()
        if not hasattr(track, 'pitch_dates'): track.pitch_dates = {}
        if today - track.pitch_dates.get(playlist_id, -99999999) < 7:
            return {"ok": False, "explanation": "This curator is still considering your last pitch. Submissions reopen after seven days."}
        track.pitch_dates[playlist_id] = today

        # Production, scene momentum and editorial fit influence a pitch.
        fame_bonus = min(0.15, player.fame / 1000)
        has_publicist = getattr(player, "has_publicist", False) or getattr(player, "has_manager", False)
        staff_bonus = 0.05 if has_publicist else 0.0

        genre_ok = target_pl["genre"] in ("All", track.genre)
        pitch_score = getattr(track, "production_quality", 0.5) * 0.8 + fame_bonus + staff_bonus + (0.1 if genre_ok else -0.3)

        if pitch_score >= target_pl["min_qual"]:
            placement = PlaylistPlacement(
                playlist_id=target_pl["id"],
                name=target_pl["name"],
                curator_type=target_pl["type"],
                genre=target_pl["genre"],
                reach_followers=target_pl["reach"],
                daily_streams_boost=target_pl["boost"],
                days_remaining=14,
            )
            track.active_playlists.append(placement)
            player.fame = min(1000, player.fame + 5)
            return {
                "ok": True,
                "placement": placement,
                "explanation": f"ACCEPTED! Editorial curators added '{track.title}' to '{target_pl['name']}' ({target_pl['reach']:,} followers)!",
            }
        else:
            return {
                "ok": False,
                "explanation": f"Pitch declined by {target_pl['name']} curators. Editorial note: 'Needs higher production polish or bigger scene momentum.'",
            }

    def process_daily_streams_and_royalties(self, player) -> List[str]:
        logs = []
        daily_total_streams = 0
        current_day = current_game_time.day

        for sid, track in self.catalog.items():
            # Calculate stream boosts from active playlist placements
            playlist_boost = 0
            for pl in list(track.active_playlists):
                playlist_boost += pl.daily_streams_boost
                pl.days_remaining -= 1
                if pl.days_remaining <= 0:
                    track.active_playlists.remove(pl)
                    logs.append(f"Playlist run ended: '{track.title}' rotated off '{pl.name}'.")

            # Base organic stream decay (0.98 per day)
            organic_streams = max(1, int(getattr(track, "organic_streams", track.daily_streams) * 0.98))
            track.organic_streams = organic_streams
            today_streams = organic_streams + playlist_boost
            track.daily_streams = max(1, today_streams)
            track.total_royalties_earned += track.daily_streams * self.ROYALTY_RATE_PER_STREAM
            track.total_streams += track.daily_streams

            daily_total_streams += track.daily_streams

        # Calculate $0.0035/stream
        daily_royalties = daily_total_streams * self.ROYALTY_RATE_PER_STREAM
        self.accumulated_unpaid_royalties += daily_royalties

        # Payout when exceeding $5.00
        if self.accumulated_unpaid_royalties >= 5.0:
            payout = int(self.accumulated_unpaid_royalties)
            player.money += payout
            player.total_music_income_to_date = getattr(player, "total_music_income_to_date", 0) + payout
            self.accumulated_unpaid_royalties -= payout
            logs.append(f"Received digital streaming royalty deposit: +${payout} ({daily_total_streams:,} streams across catalog).")

        return logs
