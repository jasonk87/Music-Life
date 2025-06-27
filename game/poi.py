# poi.py (Point Of Interest)

class PointOfInterest:
    def __init__(self, name, description, poi_type="GENERAL", interaction_options=None):
        self.name = name
        self.description = description
        self.poi_type = poi_type # e.g., "MUSIC_STORE", "REHEARSAL_STUDIO", "RECORD_LABEL"

        # interaction_options could be a list of strings representing actions,
        # or a dict mapping action names to functions/outcomes.
        # For now, let's keep it simple.
        self.interaction_options = interaction_options if interaction_options else []
        # Example: ["Browse Guitars", "Buy Strings", "Talk to Owner"] for a music store.

    def __str__(self):
        return f"{self.name} ({self.poi_type}) - {self.description}"

    def get_interactions(self):
        return self.interaction_options

# Example POI types and their specific interactions could be expanded later.
# e.g., a Music Store POI might have a method to generate an inventory of items to buy.
# A Rehearsal Studio might have a method to book time, costing money and allowing skill practice.
# For now, they are primarily informational.
