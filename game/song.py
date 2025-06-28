import uuid

class Song:
    def __init__(self, title, author, genre, song_quality=0.0,
                 lyrics_complexity=0.0, music_complexity=0.0):
        self.song_id = str(uuid.uuid4()) # Generate a unique ID for each song
        self.title = title
        self.author = author # Player's name, or co-writers later
        self.genre = genre   # e.g., "Rock", "Pop", "Blues", "Folk"

        # Quality metrics
        self.song_quality = round(max(0.0, min(1.0, song_quality)), 2) # Overall composition quality

        # Complexity metrics (for future use in skill checks, recording, performance)
        self.lyrics_complexity = round(max(0.0, min(1.0, lyrics_complexity)), 2)
        self.music_complexity = round(max(0.0, min(1.0, music_complexity)), 2)

        # Recording status
        self.is_recorded = False
        self.recording_quality = 0.0 # Quality of the actual recording, 0.0-1.0

    def __str__(self):
        status = f"'{self.title}' by {self.author} [{self.genre}] (CompQ: {self.song_quality:.2f})"
        if self.is_recorded:
            status += f" (RecQ: {self.recording_quality:.2f})"
        else:
            status += " (Unrecorded)"
        return status

    def mark_as_recorded(self, recording_quality):
        self.is_recorded = True
        self.recording_quality = round(max(0.0, min(1.0, recording_quality)), 2)
        print(f"Song '{self.title}' marked as recorded with quality: {self.recording_quality:.2f}")

if __name__ == "__main__":
    song1 = Song(title="My First Tune", author="Test Player", genre="Folk", song_quality=0.65)
    print(song1)
    assert song1.song_id is not None
    assert song1.title == "My First Tune"
    assert song1.author == "Test Player"
    assert song1.genre == "Folk"
    assert song1.song_quality == 0.65
    assert not song1.is_recorded
    assert song1.recording_quality == 0.0

    song1.mark_as_recorded(0.77)
    print(song1)
    assert song1.is_recorded
    assert song1.recording_quality == 0.77

    song2 = Song(title="Rock Anthem", author="Test Player", genre="Rock", song_quality=0.88, lyrics_complexity=0.7, music_complexity=0.9)
    print(song2)
    assert song2.lyrics_complexity == 0.7
    assert song2.music_complexity == 0.9

    print("Song class basic tests passed.")
