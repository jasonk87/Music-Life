import random
from .song import Song

class Chart:
    def __init__(self, name, max_size=10, chart_genre_preference=None):
        self.name = name
        self.max_size = max_size
        self.chart_genre_preference = chart_genre_preference # Optional: e.g., "Indie", "Rock"
        self.entries = [] # List of dictionaries, each representing a charted song
        self._populate_initial_ai_songs()

        # Each entry dictionary could look like:
        # {
        #     'song_id': 'uuid_string_here',
        #     'song_obj': song_object_reference, # For easy access to qualities
        #     'song_title': 'Title of Song',
        #     'artist_name': 'Player Name',
        #     'current_position': 1,
        #     'previous_position': 2, # Or None if new entry
        #     'weeks_on_chart': 1,
        #     'peak_position': 1,
        #     'chart_score': 150.75
        # }

    def __str__(self):
        if not self.entries:
            return f"--- {self.name} (Top {self.max_size}) ---\nChart is currently empty."

        s = f"--- {self.name} (Top {self.max_size}) ---\n"
        # Sort entries by current_position for display
        sorted_entries = sorted(self.entries, key=lambda x: x['current_position'])
        for entry in sorted_entries:
            pos_change = ""
            if entry['previous_position'] is not None:
                if entry['previous_position'] > entry['current_position']:
                    pos_change = " (Up)"
                elif entry['previous_position'] < entry['current_position']:
                    pos_change = " (Down)"
                else:
                    pos_change = " (-)" # No change

            s += (f"{entry['current_position']}. {entry['song_title']} by {entry['artist_name']} "
                  f"[Score: {entry['chart_score']:.2f}, Weeks: {entry['weeks_on_chart']}, Peak: {entry['peak_position']}]"
                  f"{pos_change}\n")
        return s

    def _generate_ai_song(self):
        # Helper to create a random song for AI artists
        genres = ["Rock", "Pop", "Folk", "Indie", "Electronic", "Blues"]
        adjectives = ["Midnight", "Broken", "Summer", "Electric", "Forgotten", "Cosmic"]
        nouns = ["Heart", "Dream", "Highway", "Tears", "Echoes", "Sky"]
        artists = ["The Wanderers", "Starlight Machine", "Echo Bloom", "Neon Kites", "Rivertown Prophets"]

        title = f"{random.choice(adjectives)} {random.choice(nouns)}"
        genre = self.chart_genre_preference or random.choice(genres)

        song = Song(
            title=title,
            author=random.choice(artists),
            genre=genre,
            originality=random.uniform(0.4, 0.8),
            catchiness=random.uniform(0.5, 0.9),
            lyrical_depth=random.uniform(0.3, 0.7),
            music_complexity=random.uniform(0.4, 0.8)
        )
        song.is_recorded = True
        song.recording_quality = random.uniform(0.5, 0.8)
        song.is_released = True # AI songs are always "released"
        return song

    def _populate_initial_ai_songs(self):
        num_songs = self.max_size - 2 # Leave some room for the player
        if num_songs <= 0:
            return
        for _ in range(num_songs):
            song = self._generate_ai_song()
            # Calculate a chart score. AI artists don't have fame, so we pass a mock player or just 0 fame.
            # Let's create a simple score calculation for AI songs.
            chart_score = (song.song_quality * 75) + (song.recording_quality * 50) + random.uniform(0, 30)
            self.entries.append({
                'song_id': song.song_id,
                'song_obj': song,
                'song_title': song.title,
                'artist_name': song.author,
                'current_position': None,
                'previous_position': None,
                'weeks_on_chart': random.randint(1, 15),
                'peak_position': None,
                'chart_score': chart_score
            })
        self._sort_and_trim_entries()

    def calculate_song_chart_score(self, song_obj, player_obj): # Now takes player_obj
        """
        Calculates a score for a song based on its qualities, player's fame,
        and potential label marketing bonus.
        This score determines its likelihood of charting and its position.
        """
        if not player_obj: # Should not happen in normal flow
            return 0

        # Base score from song & recording quality
        score = (song_obj.song_quality * 75) + (song_obj.recording_quality * 50)

        # Fame contribution
        fame_bonus = min(50, player_obj.fame / 10)
        score += fame_bonus

        # Genre preference bonus for this specific chart
        if self.chart_genre_preference:
            if song_obj.genre == self.chart_genre_preference:
                score += 25

        # Add current buzz score (e.g. from recent promotion)
        # Buzz score could be a direct addition, or a multiplier. Let's add directly for now.
        # Max buzz contribution could be capped, e.g. 30-50 points.
        buzz_contribution = min(40, getattr(song_obj, 'buzz_score', 0.0))
        score += buzz_contribution

        # Apply marketing bonus if song released via signed label
        if song_obj.released_by_label_id and player_obj.signed_label_deal and \
           player_obj.signed_label_deal['label_poi_id'] == song_obj.released_by_label_id:
            marketing_multiplier = player_obj.signed_label_deal.get('marketing_support_bonus', 1.0)
            score *= marketing_multiplier
            # print(f"DEBUG: Applied marketing bonus {marketing_multiplier}x to '{song_obj.title}' for chart score.")

        # Randomness factor (e.g., +/- 5% of score) - kept small to not overshadow other factors too much
        # score *= random.uniform(0.95, 1.05) # Requires import random at top of file

        return max(0, score)

    def _sort_and_trim_entries(self):
        """
        Sorts entries by chart_score (desc) and trims to max_size.
        Updates current_position and previous_position.
        """
        # Store previous positions before re-sorting
        old_positions = {entry['song_id']: entry['current_position'] for entry in self.entries}

        # Sort by chart_score in descending order
        self.entries.sort(key=lambda x: x['chart_score'], reverse=True)

        # Trim to max_size
        self.entries = self.entries[:self.max_size]

        # Update positions
        for i, entry in enumerate(self.entries):
            entry['current_position'] = i + 1
            entry['previous_position'] = old_positions.get(entry['song_id']) # Might be None if it wasn't on chart
            # Update peak position
            if entry['peak_position'] is None or entry['current_position'] < entry['peak_position']:
                entry['peak_position'] = entry['current_position']

    def _add_or_update_song_entry(self, song_obj, chart_score, player_name):
        """
        Adds a new song or updates an existing one in the chart entries if it qualifies.
        This is typically called before _sort_and_trim_entries.
        """
        existing_entry = next((e for e in self.entries if e['song_id'] == song_obj.song_id), None)

        if existing_entry:
            # Update existing song's score if it's still being considered (e.g. re-evaluated)
            existing_entry['chart_score'] = chart_score
            # Weeks on chart and peak position are managed by update_weekly and _sort_and_trim_entries
        else:
            # Add as a new candidate if not already present
            # current_position and previous_position will be set by _sort_and_trim_entries
            self.entries.append({
                'song_id': song_obj.song_id,
                'song_obj': song_obj, # Keep reference for easy access to changing qualities if needed later
                'song_title': song_obj.title,
                'artist_name': player_name,
                'current_position': None, # Placeholder, will be set by sort_and_trim
                'previous_position': None, # Placeholder
                'weeks_on_chart': 0, # Will be incremented in update_weekly if it makes the cut
                'peak_position': None, # Placeholder
                'chart_score': chart_score
            })

    def update_weekly(self, all_songs, player_obj, current_game_time_obj):
        """
        Main weekly update logic for the chart.
        - Decays scores of existing songs.
        - Considers new releases from all artists (player and NPCs).
        - Re-sorts and trims the chart.
        """
        # print(f"\nUpdating chart: {self.name} for week of {current_game_time_obj.get_time_string_for_schedule()}...")

        # 1. Decay existing entries and increment weeks on chart
        for entry in self.entries:
            # Don't decay brand new entries from AI artists that have 0 weeks on chart
            if entry['weeks_on_chart'] > 0:
                entry['chart_score'] *= 0.85  # Decay factor

            entry['weeks_on_chart'] += 1

            # Mark for removal if score is too low or too many weeks
            if entry['chart_score'] < 10 or entry['weeks_on_chart'] > 52:
                entry['chart_score'] = -1  # Mark for removal

        # 2. Consider all released songs as candidates
        RECENCY_WINDOW_DAYS = 8 * 7

        for song in all_songs:
            if not song.is_released:
                continue

            is_on_chart = any(e['song_id'] == song.song_id for e in self.entries if e['chart_score'] > 0)

            days_since_release = float('inf')
            if song.release_date:
                try:
                    days_since_release = current_game_time_obj.days_difference(song.release_date)
                except (ValueError, AttributeError): # Catch issues if release_date is not a valid GameTime object
                     pass # Keep days_since_release as inf

            # A song is a candidate if it's already on the chart or was released recently.
            if is_on_chart or (days_since_release <= RECENCY_WINDOW_DAYS):
                chart_score = 0
                artist_name = song.author

                if artist_name == player_obj.name:
                    # It's a player song, calculate score with fame/label bonuses
                    chart_score = self.calculate_song_chart_score(song, player_obj)
                else:
                    # It's an NPC/AI song. Use a simplified scoring logic.
                    chart_score = (song.song_quality * 75) + (song.recording_quality * 50)
                    if self.chart_genre_preference and song.genre == self.chart_genre_preference:
                        chart_score += 25
                    # Add some random buzz to make the charts more dynamic
                    chart_score += random.uniform(0, 20)

                self._add_or_update_song_entry(song, chart_score, artist_name)

        # 3. Finalize chart positions and generate feedback
        previous_chart_state = {e['song_id']: e.copy() for e in self.entries}
        self._sort_and_trim_entries()

        feedback_events = []
        for entry in self.entries:
            song_id = entry['song_id']
            prev_entry_details = previous_chart_state.get(song_id)

            chart_details = entry.copy()
            chart_details['chart_name'] = self.name # Add chart name to details

            is_new_debut = prev_entry_details is None or prev_entry_details.get('weeks_on_chart', 0) == 0

            if is_new_debut:
                feedback_events.append({
                    "type": "chart_debut",
                    "song_id": song_id,
                    "song_obj": entry['song_obj'],
                    "chart_details": chart_details
                })
            elif entry['current_position'] == 1 and (prev_entry_details is None or prev_entry_details.get('current_position') != 1):
                feedback_events.append({
                    "type": "hit_number_one",
                    "song_id": song_id,
                    "song_obj": entry['song_obj'],
                    "chart_details": chart_details
                })

        # print(f"Chart '{self.name}' update complete. {len(self.entries)} songs.")
        return feedback_events


if __name__ == '__main__':
    import random
    from game.song import Song
    from game.game_time import GameTime # Actual GameTime for release_date

    # Basic test
    test_chart = Chart(name="Global Test Hits", max_size=3)
    print(test_chart)

    # Mock song objects for testing structure
    class MockSong:
        def __init__(self, song_id, title, genre, song_quality, recording_quality):
            self.song_id = song_id
            self.title = title
            self.genre = genre
            self.song_quality = song_quality
            self.recording_quality = recording_quality

    song_a = MockSong("id_a", "Summer Breeze", "Pop", 0.8, 0.7)
    song_b = MockSong("id_b", "Rock The Night", "Rock", 0.9, 0.85)
    song_c = MockSong("id_c", "Indie Anthem", "Indie", 0.7, 0.6)
    song_d = MockSong("id_d", "Forgotten Tune", "Pop", 0.5, 0.4)

    test_chart.entries = [
        {
            'song_id': song_b.song_id, 'song_obj': song_b, 'song_title': song_b.title, 'artist_name': 'The Rockers',
            'current_position': 1, 'previous_position': 2, 'weeks_on_chart': 5, 'peak_position': 1, 'chart_score': 250.0
        },
        {
            'song_id': song_a.song_id, 'song_obj': song_a, 'song_title': song_a.title, 'artist_name': 'Pop Star',
            'current_position': 2, 'previous_position': 1, 'weeks_on_chart': 10, 'peak_position': 1, 'chart_score': 220.5
        },
        {
            'song_id': song_c.song_id, 'song_obj': song_c, 'song_title': song_c.title, 'artist_name': 'Indie Kid',
            'current_position': 3, 'previous_position': None, 'weeks_on_chart': 1, 'peak_position': 3, 'chart_score': 180.0
        },
    ]
    print("\nPopulated chart:")
    print(test_chart)

    print("\nChart class initial structure test complete.")
