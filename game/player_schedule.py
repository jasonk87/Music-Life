# game/player_schedule.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional

PRESENCE_REQUIRED_CATEGORIES = {"Gig", "Gig (Tour)", "Job", "Rehearsal", "Meeting", "Label Visit", "Studio Session"}

from game.game_time import GameTime # Assuming GameTime is in game_time.py

def item_time_range_overlaps(item, first_day, last_day):
    return item.start_time.day_index() <= last_day and item.end_time.day_index() >= first_day


@dataclass
class ScheduledItem:
    start_time: GameTime
    end_time: GameTime
    description: str
    category: str # E.g., "Gig", "Travel", "Interview", "Personal", "Rehearsal"
    details: Optional[Dict] = field(default_factory=dict) # For extra context-specific data

    def __lt__(self, other):
        if not isinstance(other, ScheduledItem):
            return NotImplemented
        return self.start_time < other.start_time

    def __str__(self):
        return f"{self.start_time.get_time_string_for_schedule()} - {self.end_time.get_time_string_for_schedule()}: {self.description} [{self.category}]"

    def get_destination_id(self) -> Optional[str]:
        if not self.details:
            return None
        return self.details.get("destination_id") or self.details.get("venue_id") or self.details.get("poi_id")

    def requires_presence(self) -> bool:
        if self.details and "requires_presence" in self.details:
            return bool(self.details.get("requires_presence"))
        return self.category in PRESENCE_REQUIRED_CATEGORIES

class PlayerSchedule:
    def __init__(self):
        self.scheduled_items: List[ScheduledItem] = []

    def add_event(self, start_time: GameTime, end_time: GameTime, description: str, category: str, details: Optional[Dict] = None):
        if not all(isinstance(t, GameTime) for t in [start_time, end_time]):
            raise ValueError("start_time and end_time must be GameTime objects.")
        if end_time < start_time:
            # Allow events that might end on the same "minute" if duration is very short, but not inverted
            raise ValueError("End time cannot be before start time.")

        event_details = details or {}
        if category in PRESENCE_REQUIRED_CATEGORIES and not (event_details.get("destination_id") or event_details.get("venue_id") or event_details.get("poi_id") or event_details.get("location_name")):
            raise ValueError(f"{category} events require a destination reference.")

        item = ScheduledItem(start_time=start_time.copy(),
                             end_time=end_time.copy(),
                             description=description,
                             category=category,
                             details=event_details)
        self.scheduled_items.append(item)
        self.scheduled_items.sort() # Keep sorted by start_time
        print(f"Scheduled: {description} from {start_time} to {end_time}")

    def _is_on_date(self, item_time: GameTime, year: int, month: int, day: int) -> bool:
        return item_time.year == year and item_time.month == month and item_time.day == day

    def _event_overlaps_date(self, event: ScheduledItem, year: int, month: int, day: int) -> bool:
        """Checks if an event (which can span multiple days) overlaps with the given single date."""
        check_day = GameTime(year, month, day).day_index()
        return item_time_range_overlaps(event, check_day, check_day)

    def get_events_for_day(self, year: int, month: int, day: int) -> List[ScheduledItem]:
        # Returns events that START on this day, or are ongoing through this day.
        # For simplicity, let's focus on events that start on this day or span it.
        daily_events = []
        for item in self.scheduled_items:
            if self._event_overlaps_date(item, year, month, day):
                daily_events.append(item)
        return sorted(daily_events) # Ensure they are sorted by start time

    def get_events_for_week(self, year: int, month: int, day: int, week_starts_on_monday=True) -> List[ScheduledItem]:
        """Use the same 30-day calendar as travel, bookings and living costs."""
        index = GameTime(year, month, day).day_index()
        # The starting career date (2024-01-01) is a Monday.
        weekday = (index - GameTime(2024, 1, 1).day_index()) % 7
        offset = weekday if week_starts_on_monday else (weekday + 1) % 7
        first = index - offset
        return sorted(item for item in self.scheduled_items
                      if item_time_range_overlaps(item, first, first + 6))

    def get_next_presence_obligation(self, current_time: GameTime, cutoff_time: Optional[GameTime] = None) -> Optional[ScheduledItem]:
        for item in self.scheduled_items:
            if not item.requires_presence():
                continue
            if item.end_time < current_time:
                continue
            if cutoff_time and item.start_time > cutoff_time:
                continue
            return item
        return None

    def get_upcoming_events(self, current_time: GameTime, limit=5) -> List[ScheduledItem]:
        upcoming = []
        count = 0
        for item in self.scheduled_items: # Assumes items are sorted by start_time
            if item.start_time >= current_time: # Use direct GameTime comparison
                upcoming.append(item)
                count += 1
                if count >= limit:
                    break
        return upcoming # Already sorted due to main list being sorted

if __name__ == '__main__':
    print("--- Testing PlayerSchedule ---")

    # Test GameTime and ScheduledItem
    t1_start = GameTime(2024, 7, 20, 10, 0)
    t1_end = GameTime(2024, 7, 20, 12, 0)
    item1 = ScheduledItem(t1_start, t1_end, "Morning Rehearsal", "Rehearsal")
    print(f"Item 1: {item1}")

    t2_start = GameTime(2024, 7, 20, 19, 0)
    t2_end = GameTime(2024, 7, 20, 22, 0)
    item2 = ScheduledItem(t2_start, t2_end, "Gig at The Rusty Mug", "Gig")
    print(f"Item 2: {item2}")

    assert item1 < item2

    # Test PlayerSchedule
    schedule = PlayerSchedule()
    schedule.add_event(t2_start, t2_end, "Gig at The Rusty Mug", "Gig", {"venue_id": "test_venue"}) # Add out of order
    schedule.add_event(t1_start, t1_end, "Morning Rehearsal", "Rehearsal", {"poi_id": "test_studio"})

    print("\nFull Schedule (Sorted):")
    for item in schedule.scheduled_items:
        print(item)
    assert len(schedule.scheduled_items) == 2
    assert schedule.scheduled_items[0].description == "Morning Rehearsal"

    # Test get_events_for_day
    print("\nEvents for 2024-07-20:")
    day_events = schedule.get_events_for_day(2024, 7, 20)
    for item in day_events:
        print(item)
    assert len(day_events) == 2

    print("\nEvents for 2024-07-21:")
    day_events_none = schedule.get_events_for_day(2024, 7, 21)
    assert len(day_events_none) == 0
    print("(None expected)")

    # Test get_upcoming_events
    current_sim_time = GameTime(2024, 7, 20, 9, 0)
    print(f"\nUpcoming events after {current_sim_time}:")
    upcoming = schedule.get_upcoming_events(current_sim_time, limit=5)
    for item in upcoming:
        print(item)
    assert len(upcoming) == 2
    assert upcoming[0].description == "Morning Rehearsal"

    current_sim_time_mid = GameTime(2024, 7, 20, 15, 0)
    print(f"\nUpcoming events after {current_sim_time_mid}:")
    upcoming_mid = schedule.get_upcoming_events(current_sim_time_mid, limit=5)
    for item in upcoming_mid:
        print(item)
    assert len(upcoming_mid) == 1
    assert upcoming_mid[0].description == "Gig at The Rusty Mug"

    current_sim_time_late = GameTime(2024, 7, 20, 23, 0)
    print(f"\nUpcoming events after {current_sim_time_late}:")
    upcoming_late = schedule.get_upcoming_events(current_sim_time_late, limit=5)
    assert len(upcoming_late) == 0
    print("(None expected)")

    # Test multi-day event spanning a date
    t_multi_start = GameTime(2024, 7, 22, 10, 0) # Monday
    t_multi_end = GameTime(2024, 7, 24, 18, 0)   # Wednesday
    schedule.add_event(t_multi_start, t_multi_end, "Travel to NYC", "Travel")

    print("\nEvents for 2024-07-23 (during multi-day travel):")
    day_events_multi = schedule.get_events_for_day(2024, 7, 23) # Tuesday
    for item in day_events_multi:
        print(item)
    assert len(day_events_multi) == 1
    assert day_events_multi[0].description == "Travel to NYC"

    print("\nEvents for 2024-07-22 (start of multi-day travel):")
    day_events_multi_start = schedule.get_events_for_day(2024, 7, 22) # Monday
    assert len(day_events_multi_start) == 1

    print("\nEvents for 2024-07-24 (end of multi-day travel):")
    day_events_multi_end = schedule.get_events_for_day(2024, 7, 24) # Wednesday
    assert len(day_events_multi_end) == 1

    print("\nEvents for 2024-07-25 (after multi-day travel):")
    day_events_multi_after = schedule.get_events_for_day(2024, 7, 25) # Thursday
    assert len(day_events_multi_after) == 0

    # Test get_events_for_week
    # GameTime(2024, 7, 20) is a Saturday. Week starting Monday 2024-07-15, ending Sunday 2024-07-21
    print("\nEvents for week of 2024-07-20 (Saturday):")
    week_events = schedule.get_events_for_week(2024, 7, 20)
    for item in week_events:
        print(item)
    # Expected: Morning Rehearsal, Gig at The Rusty Mug (both on Sat 20th)
    assert len(week_events) == 2
    assert "Morning Rehearsal" in [e.description for e in week_events]
    assert "Gig at The Rusty Mug" in [e.description for e in week_events]

    # Week containing the multi-day event
    # GameTime(2024, 7, 23) is a Tuesday. Week starting Monday 2024-07-22, ending Sunday 2024-07-28
    print("\nEvents for week of 2024-07-23 (Tuesday):")
    week_events_multi = schedule.get_events_for_week(2024, 7, 23)
    for item in week_events_multi:
        print(item)
    assert len(week_events_multi) == 1
    assert week_events_multi[0].description == "Travel to NYC"

    print("\nAll PlayerSchedule tests seem to pass based on output.")
