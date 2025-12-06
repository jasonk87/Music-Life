import random

class TrendManager:
    def __init__(self, genres):
        self.genres = genres
        self.genre_popularity = {genre: 1.0 for genre in genres}
        self.randomize_trends() # Initial setup

    def randomize_trends(self):
        # Set one genre as "The Next Big Thing" (1.5x)
        # Set one as "Dead" (0.5x)
        # Randomize others around 1.0

        big_thing = random.choice(self.genres)
        dead_thing = random.choice([g for g in self.genres if g != big_thing])

        for genre in self.genres:
            if genre == big_thing:
                self.genre_popularity[genre] = 1.5
            elif genre == dead_thing:
                self.genre_popularity[genre] = 0.5
            else:
                self.genre_popularity[genre] = random.uniform(0.8, 1.2)

    def update_weekly(self):
        # Drift trends slightly
        for genre in self.genres:
            change = random.uniform(-0.1, 0.1)
            self.genre_popularity[genre] = max(0.4, min(1.8, self.genre_popularity[genre] + change))

        # Occasional "paradigm shift" (5% chance)
        if random.random() < 0.05:
            self.randomize_trends()
            return True # Signal that a big shift happened
        return False

    def get_popularity(self, genre):
        return self.genre_popularity.get(genre, 1.0)

    def get_top_genre(self):
        return max(self.genre_popularity, key=self.genre_popularity.get)
