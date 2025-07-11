import random
from game.game_time import current_game_time

# --- Feedback Templates & Components ---

# Sources of feedback
SOURCES = {
    "fan": ["Fan Forum Post", "Social Media Comment", "Street Team Member"],
    "local_media": ["Local Music Blog", "Hometown Radio DJ", "Community Newspaper Critic"],
    "pro_critics": ["Indie Music Zine", "National Music Reviewer", "Respected Music Journalist"]
    # Add more specific sources if needed
}

# General tone based on overall song quality
TONE_BY_QUALITY = {
    "very_bad": ["This is... an attempt.", "Needs a lot more work.", "Hard to listen to, honestly."], # 0.0 - 0.2
    "bad": ["Not quite there yet.", "Shows some potential, but rough around the edges.", "A for effort?"], # 0.2 - 0.4
    "average": ["It's a decent track.", "Solid effort.", "Listenable, but doesn't stand out."], # 0.4 - 0.6
    "good": ["Pretty good stuff!", "I like this.", "Has a good vibe.", "Well-crafted song."], # 0.6 - 0.8
    "excellent": ["This is fantastic!", "Instant classic!", "Amazing work!", "Absolutely brilliant!"] # 0.8 - 1.0
}

# Comments based on specific attributes (can be positive or negative based on score)
ATTRIBUTE_COMMENTS = {
    "originality": {
        "high": ["Sounds fresh and unique.", "Breaking new ground here.", "Very inventive!"],
        "low": ["A bit derivative.", "Heard this kind of thing before.", "Doesn't offer much new."]
    },
    "catchiness": {
        "high": ["Super catchy! It's an earworm.", "Can't get this out of my head!", "Instantly memorable."],
        "low": ["Doesn't really grab you.", "Lacks a strong hook.", "Forgettable melody."]
    },
    "lyrical_depth": {
        "high": ["The lyrics are really thought-provoking.", "Deep and meaningful words.", "Poetic and insightful."],
        "low": ["Lyrics are a bit simplistic.", "Could say more.", "The words don't quite hit."]
    },
    "music_complexity": {
        "high": ["Complex and interesting arrangement.", "Musically sophisticated.", "Lots of layers to appreciate."],
        "low": ["Musically straightforward.", "A simple tune.", "Could use more musical development."]
    },
    "recording_quality": { # Separate from song components
        "high": ["Crisp and clear production.", "Sounds professionally recorded.", "The mix is excellent."],
        "low": ["A bit muddy sounding.", "Recording quality could be better.", "Sounds like a demo."]
    }
}

# --- Feedback Generation Function ---

def get_source_for_feedback(player_fame, chart_success_level=0):
    """Determines a plausible source based on fame and chart success."""
    # chart_success_level: 0=none, 1=low chart, 2=mid chart, 3=high chart/hit
    if player_fame < 50 and chart_success_level == 0:
        return random.choice(SOURCES["fan"])
    elif player_fame < 200 or chart_success_level == 1:
        return random.choice(SOURCES["fan"] + SOURCES["local_media"])
    else: # Higher fame or significant chart success
        return random.choice(SOURCES["local_media"] + SOURCES["pro_critics"])


def get_tone_comment(song_quality):
    if song_quality < 0.2: return random.choice(TONE_BY_QUALITY["very_bad"])
    if song_quality < 0.4: return random.choice(TONE_BY_QUALITY["bad"])
    if song_quality < 0.6: return random.choice(TONE_BY_QUALITY["average"])
    if song_quality < 0.8: return random.choice(TONE_BY_QUALITY["good"])
    return random.choice(TONE_BY_QUALITY["excellent"])

def get_attribute_comment(attr_name, attr_value):
    """Gets a comment for a specific attribute like originality, catchiness, etc."""
    if attr_value >= 0.7: # High
        return random.choice(ATTRIBUTE_COMMENTS[attr_name]["high"])
    elif attr_value <= 0.3: # Low
        return random.choice(ATTRIBUTE_COMMENTS[attr_name]["low"])
    return None # No strong comment for mid-range values


def generate_feedback_for_song(song_obj, player_obj, chart_entry_details=None, feedback_type="general"):
    """
    Generates a piece of feedback for a song.
    feedback_type: "general" (e.g. on release), "chart_debut" (when first charting), "hit_number_one", etc.
    chart_entry_details: dictionary with info if feedback is chart-related.
    """
    if not song_obj or not player_obj:
        return None

    # Determine chart success level for source selection
    chart_level = 0
    if chart_entry_details:
        pos = chart_entry_details.get('current_position', 100)
        if pos == 1: chart_level = 3
        elif pos <= 5: chart_level = 2
        elif pos <= 10: chart_level = 1 # Assuming Top 10 chart for this example

    source = get_source_for_feedback(player_obj.fame, chart_level)

    # --- Construct the quote ---
    quote_parts = []

    # 1. General tone based on overall song quality
    quote_parts.append(get_tone_comment(song_obj.song_quality))

    # 2. Comments on 1-2 specific song attributes (components or recording quality)
    possible_attributes = {
        "originality": song_obj.originality,
        "catchiness": song_obj.catchiness,
        "lyrical_depth": song_obj.lyrical_depth,
        "music_complexity": song_obj.music_complexity,
        "recording_quality": song_obj.recording_quality
    }

    commented_attrs = 0
    # Shuffle attributes to get variety in comments
    attr_names = list(possible_attributes.keys())
    random.shuffle(attr_names)

    for attr_name in attr_names:
        if commented_attrs >= 2: break # Max 2 attribute comments
        comment = get_attribute_comment(attr_name, possible_attributes[attr_name])
        if comment:
            quote_parts.append(comment)
            commented_attrs += 1

    # 3. Specific comment if it's a chart debut or special achievement
    if feedback_type == "chart_debut" and chart_entry_details:
        quote_parts.append(f"It's great to see '{song_obj.title}' debut at #{chart_entry_details.get('current_position','?')} this week!")
    elif feedback_type == "hit_number_one" and chart_entry_details:
        source = random.choice(SOURCES["pro_critics"]) # Big news!
        quote_parts = [f"'{song_obj.title}' skyrockets to #1! {player_obj.name} is on top of the world! This is a certified hit!"] # Override other parts for #1

    final_quote = " ".join(quote_parts)

    feedback_item = {
        "source": source,
        "quote": final_quote,
        "song_id": song_obj.song_id,
        "song_title": song_obj.title, # For easier display
        "date_generated": current_game_time.copy(), # Use the global current_game_time
        "read": False, # For UI purposes
        "impact": {} # Placeholder for future: e.g. {"fame": 1, "stress": -2}
    }

    # Small chance of fame/stress impact based on very good/bad review
    if song_obj.song_quality >= 0.9 and chart_level >=2 : # Excellent song, good chart
        feedback_item["impact"] = {"fame": random.randint(1,3) , "stress": random.randint(-5, -1)}
    elif song_obj.song_quality <= 0.2 : # Very bad song
        feedback_item["impact"] = {"fame": 0, "stress": random.randint(1,3)}


    print(f"DEBUG FeedbackGen: Generated for '{song_obj.title}': {feedback_item['quote']} (Source: {feedback_item['source']})")
    return feedback_item


def generate_feedback_for_album(player_obj, album_songs, label_name, current_time_obj):
    """
    Generates a piece of feedback for an album release.
    album_songs: A list of Song objects included in the album.
    label_name: Name of the label releasing the album.
    """
    if not player_obj or not album_songs:
        return None

    num_songs = len(album_songs)
    avg_song_quality = sum(s.song_quality for s in album_songs) / num_songs if num_songs > 0 else 0
    avg_rec_quality = sum(s.recording_quality for s in album_songs) / num_songs if num_songs > 0 else 0

    # Determine source - album reviews are usually more formal
    source_type_rand = random.random()
    if player_obj.fame < 100 :
        source = random.choice(SOURCES["local_media"])
    elif source_type_rand < 0.6 or player_obj.fame < 300: # 60% local media if not super famous
        source = random.choice(SOURCES["local_media"] + SOURCES["pro_critics"][:1]) # Mix in some lower-tier pro critics
    else: # Higher fame, more chance of pro critics
        source = random.choice(SOURCES["pro_critics"])

    quote_parts = []

    # 1. Overall impression based on average song quality
    album_tone_comment = ""
    if avg_song_quality < 0.3: album_tone_comment = f"The new album from {player_obj.name} on {label_name} is, frankly, a disappointment."
    elif avg_song_quality < 0.5: album_tone_comment = f"{player_obj.name}'s latest offering on {label_name} shows some glimmers but ultimately falls short."
    elif avg_song_quality < 0.7: album_tone_comment = f"A solid, if somewhat unremarkable, album from {player_obj.name} via {label_name}."
    elif avg_song_quality < 0.85: album_tone_comment = f"{player_obj.name} delivers a strong collection of songs on their new {label_name} release."
    else: album_tone_comment = f"Absolutely stellar! {player_obj.name}'s new album on {label_name} is a triumph and a must-listen."
    quote_parts.append(album_tone_comment)

    # 2. Comment on coherence/variety (simple genre check for now)
    genres_on_album = set(s.genre for s in album_songs)
    if len(genres_on_album) == 1:
        quote_parts.append(f"The album is very focused, sticking to its {list(genres_on_album)[0]} roots throughout.")
    elif len(genres_on_album) <= 3:
        quote_parts.append(f"There's a nice variety of sounds, blending {', '.join(list(genres_on_album)[:2])} elements effectively.")
    else:
        quote_parts.append(f"It's an eclectic mix, perhaps trying to cover too much ground with genres like {', '.join(list(genres_on_album))} all present.")

    # 3. Comment on production based on average recording quality
    if avg_rec_quality > 0.75:
        quote_parts.append("The production quality across the album is consistently excellent.")
    elif avg_rec_quality < 0.4:
        quote_parts.append("Unfortunately, the overall recording quality doesn't do the songs justice.")

    # 4. Pick one or two standout/weakest tracks (simplified)
    if num_songs > 0:
        sorted_songs = sorted(album_songs, key=lambda s: s.song_quality)
        if avg_song_quality > 0.6 and sorted_songs[-1].song_quality > avg_song_quality + 0.1 : # Good album with a clear standout
            quote_parts.append(f"Tracks like '{sorted_songs[-1].title}' really shine.")
        elif avg_song_quality < 0.5 and sorted_songs[0].song_quality < avg_song_quality - 0.1: # Weak album with a clear laggard
             quote_parts.append(f"However, '{sorted_songs[0].title}' feels like a bit of a letdown.")


    final_quote = " ".join(quote_parts)

    feedback_item = {
        "source": source,
        "quote": final_quote,
        "album_title_suggestion": f"{player_obj.name} - Self-Titled Album (via {label_name})", # Or generate one
        "song_id": None, # Not for a single song
        "song_title": "Album Review", # For display grouping
        "date_generated": current_time_obj.copy(),
        "read": False,
        "impact": {}
    }

    # Album review impact
    fame_impact = 0
    stress_impact = 0
    label_rel_impact = 0

    if avg_song_quality >= 0.8: # Excellent album
        fame_impact = random.randint(5, 10)
        stress_impact = random.randint(-10, -5)
        label_rel_impact = random.randint(5,10)
    elif avg_song_quality >= 0.6: # Good album
        fame_impact = random.randint(2, 5)
        stress_impact = random.randint(-5, 0)
        label_rel_impact = random.randint(2,5)
    elif avg_song_quality <= 0.3: # Poor album
        fame_impact = random.randint(-5, -1)
        stress_impact = random.randint(5, 10)
        label_rel_impact = random.randint(-10, -5)
    elif avg_song_quality <= 0.5: # Mediocre
        stress_impact = random.randint(0,5)
        label_rel_impact = random.randint(-5, 0)

    feedback_item["impact"] = {"fame": fame_impact, "stress": stress_impact, "label_relationship": label_rel_impact}

    print(f"DEBUG FeedbackGen: Generated for ALBUM by {player_obj.name}: {feedback_item['quote']} (Source: {feedback_item['source']})")
    return feedback_item


if __name__ == '__main__':
    # Requires Song and Player mock objects or actual classes if run directly
    class MockSong:
        def __init__(self, song_id, title, genre, song_quality, rec_q, orig, catch, lyrics, complex):
            self.song_id = song_id
            self.title = title
            self.genre = genre
            self.song_quality = song_quality
            self.recording_quality = rec_q
            self.originality = orig
            self.catchiness = catch
            self.lyrical_depth = lyrics
            self.music_complexity = complex

    class MockPlayer:
        def __init__(self, name, fame):
            self.name = name
            self.fame = fame
            self.feedback_received = []

    # Test Cases
    player1 = MockPlayer("Rookie Rick", 20)
    song1 = MockSong("s1", "My First Song", "Indie", 0.55, 0.5, 0.6, 0.7, 0.4, 0.5) # Average
    song2 = MockSong("s2", "Epic Ballad", "Rock", 0.85, 0.9, 0.8, 0.9, 0.8, 0.9)   # Excellent
    song3 = MockSong("s3", "Trash Fire", "Punk", 0.15, 0.2, 0.1, 0.2, 0.1, 0.1)    # Very Bad

    print("--- General Feedback Test ---")
    fb1 = generate_feedback_for_song(song1, player1)
    if fb1: player1.feedback_received.append(fb1)

    fb2 = generate_feedback_for_song(song2, player1)
    if fb2: player1.feedback_received.append(fb2)

    fb3 = generate_feedback_for_song(song3, player1)
    if fb3: player1.feedback_received.append(fb3)

    print("\n--- Chart Debut Feedback Test ---")
    chart_details_s1 = {'current_position': 8, 'song_id': song1.song_id}
    fb4 = generate_feedback_for_song(song1, player1, chart_entry_details=chart_details_s1, feedback_type="chart_debut")
    if fb4: player1.feedback_received.append(fb4)

    chart_details_s2_hit = {'current_position': 1, 'song_id': song2.song_id}
    fb5 = generate_feedback_for_song(song2, player1, chart_entry_details=chart_details_s2_hit, feedback_type="hit_number_one")
    if fb5: player1.feedback_received.append(fb5)

    print("\n--- Player's Feedback Received ---")
    for item in player1.feedback_received:
        print(f"[{item['date_generated'].get_time_string_for_schedule()}] From: {item['source']} about '{item['song_title']}': \"{item['quote']}\" Impact: {item['impact']}")

    print("\nFeedback generator tests complete.")
