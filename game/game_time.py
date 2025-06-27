class GameTime:
    def __init__(self, start_hour=8, start_day=1, start_month=1, start_year=2024):
        self.hour = start_hour        # 0-23
        self.day = start_day          # 1-30 (simplified month length)
        self.month = start_month      # 1-12
        self.year = start_year

    def advance_time(self, hours=0, days=0):
        self.hour += hours
        while self.hour >= 24:
            self.hour -= 24
            self.day += 1

        self.day += days
        while self.day > 30: # Simplified month
            self.day -= 30
            self.month += 1
            if self.month > 12:
                self.month -= 12
                self.year += 1

    def __str__(self):
        return f"Time: {self.hour:02d}:00, Day: {self.day}, Month: {self.month}, Year: {self.year}"

# Global game time instance (can be managed better in a Game class later)
current_game_time = GameTime()

def advance_game_time(hours=0, days=0):
    """Helper function to advance the global game time."""
    current_game_time.advance_time(hours=hours, days=days)
    print(f"Time advanced. Current time: {current_game_time}")

def get_current_time_str():
    return str(current_game_time)
