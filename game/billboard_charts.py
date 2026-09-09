from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class BillboardChartEntry:
    song_id: str
    title: str
    artist: str
    current_position: int
    peak_position: int
    weeks_on_chart: int
    points: float
    is_number_one: bool = False


class BillboardChartSystem:
    """Simulates real-world Billboard Hot 100 chart formulas, radio airplay spins, streaming, and #1 single battles."""

    CITY_RADIO_STATIONS = [
        {"city": "Asbury Park, NJ", "station": "90.5 The Night (Asbury FM)", "weight": 1.0},
        {"city": "Philadelphia, PA", "station": "WXPN 88.5 Philadelphia", "weight": 1.4},
        {"city": "New York City, NY", "station": "Z100 / Q104.3 NYC Radio", "weight": 2.5},
        {"city": "Nashville, TN", "station": "WSM 650 AM Music City", "weight": 1.8},
        {"city": "Austin, TX", "station": "KUTX 98.9 Austin FM", "weight": 1.5},
        {"city": "Los Angeles, CA", "station": "KROQ 106.7 & KCRW LA", "weight": 2.5},
        {"city": "Chicago, IL", "station": "WXRT 93.1 Chicago Rock", "weight": 2.0},
        {"city": "New Orleans, LA", "station": "WWOZ 90.7 New Orleans", "weight": 1.2},
        {"city": "Memphis, TN", "station": "WEVL 89.9 Memphis FM", "weight": 1.1},
        {"city": "Detroit, MI", "station": "WRIF 101.1 Motor City", "weight": 1.5},
        {"city": "Atlanta, GA", "station": "Hot 107.9 & V103 Atlanta", "weight": 2.0},
        {"city": "Seattle, WA", "station": "KEXP 90.3 Seattle", "weight": 1.6},
        {"city": "London, UK", "station": "BBC Radio 1 & 6 Music", "weight": 2.5},
        {"city": "Tokyo, Japan", "station": "InterFM897 Tokyo", "weight": 2.0},
        {"city": "Berlin, Germany", "station": "Radio Eins Berlin", "weight": 1.8},
    ]

    RIVAL_HOT_HITS = [
        {"title": "Neon Sunset Boulevard", "artist": "The Silver Strays", "base_pts": 8500},
        {"title": "Midnight Radio Ghost", "artist": "Luna & The Eclipse", "base_pts": 7200},
        {"title": "Diamond Velvet Dream", "artist": "Apex Royalty", "base_pts": 9400},
        {"title": "Electric Thunderstorm", "artist": "Crash Voltage", "base_pts": 6800},
        {"title": "Subway Line Serenade", "artist": "Brooklyn Echoes", "base_pts": 5900},
    ]

    def __init__(self):
        self.chart_entries: Dict[str, BillboardChartEntry] = {}
        self.number_one_milestones: List[Dict[str, Any]] = []

    def calculate_song_chart_points(self, player, song, streaming_sys=None, album_sys=None) -> float:
        # 1. Radio airplay points across cities
        fame = getattr(player, "fame", 10)
        cred = getattr(player, "street_cred", 50)
        rec_qual = getattr(song, "recording_quality", 0.5)
        song_qual = getattr(song, "song_quality", 0.5)

        base_airplay = ((rec_qual * 2000) + (song_qual * 1500) + (fame * 40) + (cred * 25))
        radio_total = base_airplay * 1.5

        # 2. Streaming Points (1 stream = 0.001 chart points)
        stream_points = 0.0
        if streaming_sys and song.song_id in streaming_sys.catalog:
            st = streaming_sys.catalog[song.song_id]
            stream_points = st.daily_streams * 7 * 0.05

        # 3. Major label boost
        label_boost = 1.35 if getattr(player, "signed_label_deal", None) else 1.0

        total_pts = (radio_total + stream_points) * label_boost
        return round(total_pts, 1)

    def update_weekly_billboard_hot_100(self, player, songs: List[Any], streaming_sys=None) -> List[str]:
        logs = []
        all_pool = []

        # Evaluate player's released songs
        for s in songs:
            if getattr(s, "is_released", False):
                pts = self.calculate_song_chart_points(player, s, streaming_sys)
                all_pool.append({"id": s.song_id, "title": s.title, "artist": player.name, "points": pts, "is_player": True})

        # Add rival hits
        for rh in self.RIVAL_HOT_HITS:
            drift = random.uniform(0.90, 1.10)
            pts = rh["base_pts"] * drift
            all_pool.append({"id": rh["title"], "title": rh["title"], "artist": rh["artist"], "points": pts, "is_player": False})

        # Sort descending by points
        all_pool.sort(key=lambda x: x["points"], reverse=True)

        for rank_idx, item in enumerate(all_pool[:100], start=1):
            sid = item["id"]
            if item["is_player"]:
                if sid not in self.chart_entries:
                    entry = BillboardChartEntry(
                        song_id=sid,
                        title=item["title"],
                        artist=item["artist"],
                        current_position=rank_idx,
                        peak_position=rank_idx,
                        weeks_on_chart=1,
                        points=item["points"],
                        is_number_one=(rank_idx == 1),
                    )
                    self.chart_entries[sid] = entry
                    logs.append(f"📈 BILLBOARD HOT 100 DEBUT: '{item['title']}' enters the chart at #{rank_idx}!")
                else:
                    entry = self.chart_entries[sid]
                    entry.current_position = rank_idx
                    entry.weeks_on_chart += 1
                    if rank_idx < entry.peak_position:
                        entry.peak_position = rank_idx
                    entry.points = item["points"]
                    if rank_idx == 1 and not entry.is_number_one:
                        entry.is_number_one = True
                        player.fame = min(1000, player.fame + 50)
                        self.number_one_milestones.append({"title": item["title"], "day": current_game_time.day})
                        logs.append(f"🏆 🔥 NUMBER ONE HIT ON BILLBOARD HOT 100! '{item['title']}' hits #1 on the national charts!")
                    else:
                        logs.append(f"Billboard Hot 100: '{item['title']}' is currently #{rank_idx} (Peak: #{entry.peak_position}).")

        return logs
