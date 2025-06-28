class GameTime:
    def __init__(self, start_year=2024, start_month=1, start_day=1, start_hour=8, start_minute=0):
        self.year = start_year
        self.month = start_month      # 1-12
        self.day = start_day          # 1-30 (simplified month length)
        self.hour = start_hour        # 0-23
        self.minute = start_minute    # 0-59

    def advance_time(self, minutes=0):
        if minutes < 0:
            print("Warning: Cannot advance time backwards.")
            return

        self.minute += minutes

        # Roll over minutes to hours
        if self.minute >= 60:
            hours_added = self.minute // 60
            self.minute %= 60
            self.hour += hours_added

        # Roll over hours to days
        if self.hour >= 24:
            days_added = self.hour // 24
            self.hour %= 24
            self.day += days_added

        # Roll over days to months (simplified 30-day months)
        while self.day > 30:
            self.day -= 30
            self.month += 1
            if self.month > 12:
                self.month = 1
                self.year += 1

    def __str__(self):
        return f"Time: {self.hour:02d}:{self.minute:02d}, Day: {self.day}, Month: {self.month}, Year: {self.year}"

# Global game time instance
current_game_time = GameTime()

def advance_game_time(minutes=0):
    """Helper function to advance the global game time by a number of minutes."""
    current_game_time.advance_time(minutes=minutes)
    # Optional: print time advancement details here, or let main loop handle it.
    # For now, keeping it less verbose. Callers can print if needed.
    # print(f"Time advanced by {minutes} minutes. Current time: {current_game_time}")


def get_current_time_str():
    return str(current_game_time)
