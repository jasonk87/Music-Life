import uuid

class Song:
    def __init__(self, title, author, genre,
                 originality=None, catchiness=None, lyrical_depth=None, music_complexity=None,
                 song_quality=None): # song_quality can be an override
        self.song_id = str(uuid.uuid4())
        self.title = title
        self.author = author
        self.genre = genre

        # Component attributes (0.0 - 1.0)
        # If specific component qualities aren't provided, default them for calculation
        self.originality = round(max(0.0, min(1.0, originality if originality is not None else 0.5)), 2)
        self.catchiness = round(max(0.0, min(1.0, catchiness if catchiness is not None else 0.5)), 2)
        self.lyrical_depth = round(max(0.0, min(1.0, lyrical_depth if lyrical_depth is not None else 0.5)), 2)
        self.music_complexity = round(max(0.0, min(1.0, music_complexity if music_complexity is not None else 0.5)), 2)

        if song_quality is not None:
            self.song_quality = round(max(0.0, min(1.0, song_quality)), 2)
        else:
            # Calculate overall song_quality as an average of its components
            self.song_quality = round( (self.originality + self.catchiness + self.lyrical_depth + self.music_complexity) / 4.0, 2)

        self.is_recorded = False
        self.recording_quality = 0.0
        self.is_released = False
        self.release_date = None # Will be a GameTime object or string
        self.released_by_label_id = None # Store POI ID of the label if released through one
        self.buzz_score = 0.0 # Represents temporary promotional heat
        self.has_music_video = False
        self.music_video_quality = 0.0
        self.considered_for_album_with_label_id = None # Store label_poi_id if part of their album discussion/release
        self.is_remix = False
        self.original_song_id = None

    def __str__(self):
        details = [
            f"Orig: {self.originality:.2f}",
            f"Catch: {self.catchiness:.2f}",
            f"Lyrics: {self.lyrical_depth:.2f}",
            f"Music: {self.music_complexity:.2f}",
            f"OverallQ: {self.song_quality:.2f}"
        ]
        status = f"'{self.title}' by {self.author} [{self.genre}] ({', '.join(details)})"
        if self.is_recorded:
            status += f" (RecQ: {self.recording_quality:.2f})"
        else:
            status += " (Unrecorded)"

        if self.is_released:
            release_info = f"Released: {self.release_date.get_time_string_for_schedule() if self.release_date and hasattr(self.release_date, 'get_time_string_for_schedule') else 'N/A'}"
            if self.released_by_label_id:
                # This part is tricky as Song class doesn't know about WORLD_MAP to get label name.
                # For now, just show the ID or a generic "via Label".
                # A better way would be to pass label name when marking release or have a global lookup.
                release_info += f" (Via Label ID: {self.released_by_label_id})"
            else:
                release_info += " (Self-Released)"
            status += f" ({release_info})"

        if self.has_music_video:
            status += f" (VideoQ: {self.music_video_quality:.2f})"

        return status

    def mark_as_recorded(self, recording_quality):
        self.is_recorded = True
        self.recording_quality = round(max(0.0, min(1.0, recording_quality)), 2)
        # print(f"Song '{self.title}' marked as recorded with quality: {self.recording_quality:.2f}") # Less verbose

    def mark_as_released(self, release_date_obj, released_by_label_id=None):
        if not self.is_recorded:
            print(f"Error: Song '{self.title}' must be recorded before it can be released.")
            return False
        self.is_released = True
        self.release_date = release_date_obj # Expects a GameTime object
        self.released_by_label_id = released_by_label_id

        release_method = f"via Label ID: {self.released_by_label_id}" if self.released_by_label_id else "self-released"
        print(f"Song '{self.title}' marked as released on {self.release_date.get_time_string_for_schedule()} ({release_method}).")
        return True

if __name__ == "__main__":
    # Test case 1: Override song_quality
    song1 = Song(title="My First Tune", author="Test Player", genre="Folk", song_quality=0.65)
    print(song1)
    assert song1.song_quality == 0.65
    # Component qualities will be defaults if not specified alongside an override song_quality
    # This behavior is fine; if song_quality is given, it's the source of truth.
    # If we wanted components to also be set, __init__ would need more logic or disallow song_quality if components are set.
    # For now, this test confirms song_quality override works.

    song1.mark_as_recorded(0.77)
    print(song1)
    assert song1.is_recorded
    assert song1.recording_quality == 0.77

    # Test case 2: Calculated song_quality from components
    song2 = Song(title="Rock Anthem", author="Test Player", genre="Rock",
                 originality=0.8, catchiness=0.9, lyrical_depth=0.7, music_complexity=0.6)
    print(song2)
    expected_q2 = round((0.8 + 0.9 + 0.7 + 0.6) / 4.0, 2)
    assert song2.song_quality == expected_q2
    assert song2.originality == 0.8
    assert song2.catchiness == 0.9
    assert song2.lyrical_depth == 0.7
    assert song2.music_complexity == 0.6

    # Test case 3: Default component values if nothing specified
    song3 = Song(title="Default Song", author="Test Player", genre="Pop")
    print(song3)
    expected_q3 = round((0.5 + 0.5 + 0.5 + 0.5) / 4.0, 2) # All components default to 0.5
    assert song3.song_quality == expected_q3
    assert song3.originality == 0.5

    # Test case 4: Mixed - some components provided, others default
    song4 = Song(title="Partial Song", author="Test Player", genre="Blues", originality=0.9, music_complexity=0.7)
    print(song4)
    expected_q4 = round((0.9 + 0.5 + 0.5 + 0.7) / 4.0, 2) # catchiness and lyrical_depth default to 0.5
    assert song4.song_quality == expected_q4
    assert song4.catchiness == 0.5

    # Test case 5: Release mechanics
    song5 = Song(title="Release Me", author="Test Player", genre="Indie", originality=0.7, catchiness=0.8)
    print(song5)
    assert not song5.is_released
    assert song5.release_date is None

    # Try to release before recording (should fail)
    # For testing mark_as_released directly, we need a mock GameTime object or to import the actual one.
    # Let's assume a simple string for testing __str__ if GameTime is complex to mock here.
    class MockGameTime:
        def get_time_string_for_schedule(self):
            return "2024-08-15 10:00"

    mock_date = MockGameTime()
    assert not song5.mark_as_released(mock_date)

    song5.mark_as_recorded(0.75)
    assert song5.is_recorded
    assert song5.mark_as_released(mock_date)
    assert song5.is_released
    assert song5.release_date == mock_date
    print(song5) # Should show release date

    print("\nSong class enhanced tests passed.")
