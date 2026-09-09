from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time, advance_game_time


@dataclass
class VinylBatchOrder:
    order_id: str
    album_title: str
    units_ordered: int
    cost_per_unit: float
    total_cost: float
    order_day: int
    days_to_deliver: int = 21
    delivered: bool = False
    units_in_stock: int = 0
    units_sold: int = 0
    retail_price: float = 25.0
    wholesale_price: float = 15.0


@dataclass
class AlbumRelease:
    album_id: str
    title: str
    artist: str
    track_ids: List[str]
    tracks_data: List[Dict[str, Any]]
    format_type: str  # "DIGITAL", "CD", "VINYL", "DELUXE"
    release_date_str: str
    release_day: int
    genre: str = "Indie"
    theme: Optional[str] = None
    overall_quality: float = 0.5
    concept_coherence: float = 1.0
    total_physical_sales: int = 0
    total_digital_sales: int = 0
    total_revenue: float = 0.0
    vinyl_batch: Optional[VinylBatchOrder] = None
    reviews: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def quality(self):
        return self.overall_quality

    def __str__(self):
        return f"{self.title} / {len(self.track_ids)} tracks / {self.format_type.title()} / {self.overall_quality:.0%} quality"


class AlbumProductionSystem:
    """Manages the creation, track sequencing, physical vinyl pressing, and release of full albums."""

    VINYL_UNIT_COST = 6.0  # Manufacturing cost per vinyl record
    VINYL_LEAD_DAYS = 21   # 3 weeks pressing plant lead time
    VINYL_RETAIL = 25.0
    VINYL_WHOLESALE = 15.0

    def __init__(self):
        self.released_albums: List[AlbumRelease] = []
        self.pending_vinyl_orders: List[VinylBatchOrder] = []
        self.delivered_vinyl_batches: List[VinylBatchOrder] = []

    def calculate_album_coherence(self, songs: List[Any], theme: Optional[str] = None) -> Dict[str, float]:
        if not songs:
            return {"coherence": 0.5, "quality": 0.5, "genre_match": 0.5}

        # 1. Genre Harmony
        genres = [getattr(s, "genre", "Rock") for s in songs]
        unique_genres = set(genres)
        if len(unique_genres) == 1:
            genre_mult = 1.15  # Pure genre album
        elif len(unique_genres) <= 2:
            genre_mult = 1.05  # Focused fusion
        else:
            genre_mult = 0.90  # Too scattered

        # 2. Concept / Theme Harmony
        themes = [getattr(s, "theme", None) for s in songs if getattr(s, "theme", None)]
        if theme and themes:
            matching_theme_count = sum(1 for t in themes if t == theme)
            theme_mult = 1.0 + (0.15 * (matching_theme_count / len(songs)))
        elif len(themes) > 0 and len(set(themes)) == 1:
            theme_mult = 1.15
        else:
            theme_mult = 1.0

        # 3. Track Sequencing & Master Quality
        avg_song_q = sum(getattr(s, "song_quality", 0.5) for s in songs) / len(songs)
        avg_rec_q = sum(getattr(s, "recording_quality", 0.5) for s in songs) / len(songs)
        base_quality = (avg_song_q * 0.45) + (avg_rec_q * 0.55)

        final_coherence = round(min(1.3, genre_mult * theme_mult), 2)
        final_quality = round(min(1.0, base_quality * final_coherence), 2)

        return {
            "coherence": final_coherence,
            "quality": final_quality,
            "genre_match": round(genre_mult, 2),
        }

    def assemble_album(self, player, title: str, songs: List[Any], format_type: str = "DIGITAL", theme: Optional[str] = None) -> Dict[str, Any]:
        ids = [getattr(song, 'song_id', None) for song in songs]
        if len(set(ids)) != len(ids):
            return {"ok": False, "explanation": "A track can appear only once on a release."}
        if any(set(a.track_ids) == set(ids) for a in self.released_albums):
            return {"ok": False, "explanation": "This collection has already been released."}
        if len(songs) < 3:
            return {"ok": False, "explanation": "An EP or Album requires at least 3 master recorded tracks."}
        if len(songs) > 16:
            return {"ok": False, "explanation": "Maximum 16 tracks per album release."}

        unrecorded = [s.title for s in songs if not getattr(s, "is_recorded", False)]
        if unrecorded:
            return {"ok": False, "explanation": f"The following tracks must be recorded before album release: {', '.join(unrecorded)}"}

        eval_res = self.calculate_album_coherence(songs, theme)
        primary_genre = songs[0].genre if hasattr(songs[0], "genre") else "Indie"

        tracks_data = []
        track_ids = []
        for s in songs:
            sid = getattr(s, "song_id", str(uuid.uuid4()))
            track_ids.append(sid)
            tracks_data.append({
                "song_id": sid,
                "title": getattr(s, "title", "Untitled"),
                "genre": getattr(s, "genre", primary_genre),
                "quality": getattr(s, "song_quality", 0.5),
                "recording_quality": getattr(s, "recording_quality", 0.5),
            })
            if not s.is_released:
                s.mark_as_released(current_game_time)

        album = AlbumRelease(
            album_id=str(uuid.uuid4()),
            title=title,
            artist=getattr(player, "name", "Musician"),
            track_ids=track_ids,
            tracks_data=tracks_data,
            format_type=format_type,
            release_date_str=f"Day {current_game_time.day}, Year {current_game_time.year}",
            release_day=current_game_time.day_index(),
            genre=primary_genre,
            theme=theme,
            overall_quality=eval_res["quality"],
            concept_coherence=eval_res["coherence"],
        )

        self.released_albums.append(album)
        if hasattr(player, "albums_released"):
            player.albums_released.append(album)
        player.fame = min(1000, player.fame + int(eval_res["quality"] * 25))
        player.street_cred = min(100, player.street_cred + int(eval_res["coherence"] * 10))

        return {
            "ok": True,
            "album": album,
            "explanation": f"Successfully released full album '{title}' ({format_type}) with quality {eval_res['quality']:.2f}!",
        }

    def order_vinyl_pressing(self, player, album: Any, units: int = 500) -> Dict[str, Any]:
        if units < 100:
            return {"ok": False, "explanation": "Minimum vinyl pressing plant order is 100 units."}

        album_obj = None
        if isinstance(album, str):
            album_title = album
            for a in self.released_albums:
                if a.title.lower() == album.lower():
                    album_obj = a
                    break
        else:
            album_obj = album
            album_title = getattr(album, "title", str(album))

        if album_obj is None:
            return {"ok": False, "explanation": "No released album matches this order."}
        total_cost = int(units * self.VINYL_UNIT_COST)
        if player.money < total_cost:
            return {"ok": False, "explanation": f"Insufficient funds. Ordering {units} vinyl copies requires ${total_cost}."}

        player.money -= total_cost
        order = VinylBatchOrder(
            order_id=str(uuid.uuid4()),
            album_title=album_title,
            units_ordered=units,
            cost_per_unit=self.VINYL_UNIT_COST,
            total_cost=total_cost,
            order_day=current_game_time.day_index(),
            days_to_deliver=self.VINYL_LEAD_DAYS,
            retail_price=self.VINYL_RETAIL,
            wholesale_price=self.VINYL_WHOLESALE,
        )

        self.pending_vinyl_orders.append(order)
        if album_obj and hasattr(album_obj, "vinyl_batch"):
            album_obj.vinyl_batch = order

        return {
            "ok": True,
            "order": order,
            "explanation": f"Ordered {units}x 180g Vinyl records of '{album_title}' for ${total_cost}. Delivered in {self.VINYL_LEAD_DAYS} days.",
        }

    def process_daily_vinyl_manufacturing_and_sales(self, player) -> List[str]:
        logs = []
        current_day = current_game_time.day_index()

        # Check Deliveries
        for order in list(self.pending_vinyl_orders):
            if current_day >= order.order_day + order.days_to_deliver:
                order.delivered = True
                order.units_in_stock = order.units_ordered
                self.pending_vinyl_orders.remove(order)
                self.delivered_vinyl_batches.append(order)
                logs.append(f"Vinyl Pressing Plant delivered {order.units_ordered}x records of '{order.album_title}' to your merch inventory!")

        # Process Direct-To-Fan & Indie Record Store Wholesale Sales
        for batch in self.delivered_vinyl_batches:
            if batch.units_in_stock > 0:
                # Organic sales based on player fame and cred
                fame = getattr(player, "fame", 10)
                cred = getattr(player, "street_cred", 50)
                daily_demand = max(1, int((fame * 0.15) + (cred * 0.08)))
                sales_today = min(batch.units_in_stock, daily_demand)

                if sales_today > 0:
                    revenue = sales_today * batch.retail_price
                    batch.units_in_stock -= sales_today
                    batch.units_sold += sales_today
                    player.money += int(revenue)
                    logs.append(f"Sold {sales_today}x vinyl records of '{batch.album_title}' (Earned +${int(revenue)}).")

        return logs
