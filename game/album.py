from game.game_time import current_game_time

class Album:
    def __init__(self, title, artist, tracks, theme=None, release_date=None):
        self.title = title
        self.artist = artist
        self.tracks = tracks # List of Song objects
        self.theme = theme # Overall theme (optional)
        self.release_date = release_date

        self.quality = self.calculate_quality()
        self.reviews = []
        self.sales = 0

    def calculate_quality(self):
        if not self.tracks: return 0.0

        avg_song_quality = sum(s.song_quality for s in self.tracks) / len(self.tracks)
        avg_rec_quality = sum(s.recording_quality for s in self.tracks) / len(self.tracks)

        # Coherence Bonus
        # 1. Genre Consistency
        genres = [s.genre for s in self.tracks]
        unique_genres = set(genres)
        genre_coherence = 1.0
        if len(unique_genres) == 1:
            genre_coherence = 1.1 # Bonus for pure genre album
        elif len(unique_genres) > len(self.tracks) / 2:
            genre_coherence = 0.9 # Penalty for too eclectic/random

        # 2. Theme Consistency
        themes = [s.theme for s in self.tracks if s.theme]
        theme_coherence = 1.0
        if themes and len(set(themes)) == 1:
            theme_coherence = 1.15 # Strong concept album bonus

        base_quality = (avg_song_quality + avg_rec_quality) / 2.0
        final_quality = base_quality * genre_coherence * theme_coherence

        return min(1.0, final_quality)

    def __str__(self):
        return f"Album: {self.title} ({len(self.tracks)} tracks) - Quality: {self.quality:.2f}"
