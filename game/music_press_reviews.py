from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass
class AlbumReview:
    review_id: str
    album_id: str
    album_title: str
    publication: str       # "PITCHFORK", "ROLLING_STONE", "NME"
    numeric_score: float   # e.g. 8.8 (out of 10.0) or 4.5 stars
    is_best_new_music: bool
    review_headline: str
    review_blurb: str
    day_published: int


class MusicPressReviewsSystem:
    """Manages Pitchfork, Rolling Stone, and NME critical album review scores and cultural acclaim."""

    def __init__(self):
        self.review_archive: List[AlbumReview] = []

    def generate_press_reviews_for_album(self, player, album) -> List[AlbumReview]:
        base_q = getattr(album, "overall_quality", 0.70)
        coherence = getattr(album, "concept_coherence", 1.0)

        # 1. Pitchfork Review
        # Quality scale 0.0 to 10.0 with critical nuances
        pf_score = round(min(10.0, max(4.0, (base_q * 8.5) + ((coherence - 1.0) * 3.0) + random.uniform(-0.3, 0.4))), 1)
        is_bnm = pf_score >= 8.5

        if is_bnm:
            headline = f"Best New Music: {album.title} is an urgent, transcendent masterwork."
            blurb = f"On '{album.title}', {player.name} channels raw catharsis and surgical sonic architecture into one of the defining statements of modern indie music."
        elif pf_score >= 7.0:
            headline = f"Sharp, evocative songwriting carries {album.title} through thrilling peaks."
            blurb = f"An ambitious and tightly-cohesive record that establishes {player.name}'s distinctive voice in the contemporary landscape."
        else:
            headline = f"{album.title} offers flashes of brilliance amid stylistic exploration."
            blurb = f"While showing tremendous musical chops, {album.title} occasionally grapples with its thematic ambition."

        pf_review = AlbumReview(
            review_id=f"rev_pf_{album.album_id}",
            album_id=album.album_id,
            album_title=album.title,
            publication="Pitchfork",
            numeric_score=pf_score,
            is_best_new_music=is_bnm,
            review_headline=headline,
            review_blurb=blurb,
            day_published=current_game_time.day,
        )

        # 2. Rolling Stone Review
        stars = round(min(5.0, max(2.5, (pf_score / 2.0))), 1)
        rs_review = AlbumReview(
            review_id=f"rev_rs_{album.album_id}",
            album_id=album.album_id,
            album_title=album.title,
            publication="Rolling Stone",
            numeric_score=stars,
            is_best_new_music=False,
            review_headline=f"★★★★ {stars} Stars: {album.title} delivers pure rock and roll conviction.",
            review_blurb=f"Packed with anthemic choruses and visceral guitar tone, this album proves {player.name} is built for arena glory.",
            day_published=current_game_time.day,
        )

        self.review_archive.extend([pf_review, rs_review])

        if is_bnm:
            player.fame = min(1000, player.fame + 40)
            player.street_cred = min(100, player.street_cred + 25)
        else:
            player.fame = min(1000, player.fame + 15)
            player.street_cred = min(100, player.street_cred + 10)

        return [pf_review, rs_review]
