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

    def get_time_string_for_schedule(self): # For more compact schedule display
        return f"{self.year}-{self.month:02d}-{self.day:02d} {self.hour:02d}:{self.minute:02d}"

    def copy(self):
        return GameTime(self.year, self.month, self.day, self.hour, self.minute)

    def _to_tuple(self):
        """Helper for comparisons."""
        return (self.year, self.month, self.day, self.hour, self.minute)

    def __eq__(self, other):
        if not isinstance(other, GameTime):
            return NotImplemented
        return self._to_tuple() == other._to_tuple()

    def __lt__(self, other):
        if not isinstance(other, GameTime):
            return NotImplemented
        return self._to_tuple() < other._to_tuple()

    def __le__(self, other):
        if not isinstance(other, GameTime):
            return NotImplemented
        return self._to_tuple() <= other._to_tuple()

    def __gt__(self, other):
        if not isinstance(other, GameTime):
            return NotImplemented
        return self._to_tuple() > other._to_tuple()

    def __ge__(self, other):
        if not isinstance(other, GameTime):
            return NotImplemented
        return self._to_tuple() >= other._to_tuple()

    def days_difference(self, other_time_obj):
        """
        Calculates the approximate number of days between this GameTime object (self) and another (other_time_obj).
        Assumes self is later than other_time_obj. Returns a positive float.
        Simplified: 30 days per month.
        """
        if not isinstance(other_time_obj, GameTime):
            raise ValueError("Can only calculate difference with another GameTime object.")

        # Calculate total days from a common epoch (year 0, month 0, day 0) for both times
        self_total_days = self.year * 360 + self.month * 30 + self.day + (self.hour / 24.0) + (self.minute / (24.0 * 60.0))
        other_total_days = other_time_obj.year * 360 + other_time_obj.month * 30 + other_time_obj.day + \
                           (other_time_obj.hour / 24.0) + (other_time_obj.minute / (24.0 * 60.0))

        return abs(self_total_days - other_total_days)


# Global game time instance
current_game_time = GameTime()

def advance_game_time(minutes=0):
    """Helper function to advance the global game time by a number of minutes."""
    current_game_time.advance_time(minutes=minutes)
    # Optional: print time advancement details here, or let main loop handle it.
    # For now, keeping it less verbose. Callers can print if needed.
    # print(f"Time advanced by {minutes} minutes. Current time: {current_game_time}")


def get_current_time_str(date_only=False):
    if date_only:
        return f"{current_game_time.year}-{current_game_time.month:02d}-{current_game_time.day:02d}"
    return str(current_game_time)

def calculate_player_age(player_start_date, current_time, initial_age=18):
    """
    Calculates the player's age based on their start date in the game and the current game time.
    Age increments on the anniversary of the start month and day.
    """
    if not player_start_date or not current_time:
        return initial_age # Should not happen if player_start_date is set

    years_passed = current_time.year - player_start_date.year
    age = initial_age + years_passed

    # Check if the anniversary of the start month/day has passed this year
    if current_time.month < player_start_date.month:
        age -= 1 # Anniversary month not yet reached this year
    elif current_time.month == player_start_date.month:
        if current_time.day < player_start_date.day:
            age -= 1 # Anniversary day not yet reached this month

    return age
