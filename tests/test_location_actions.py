import pytest
from game.game import Game
from game.player import Player
from game.poi import PointOfInterest
from game.place_presence import LocalAction
from game.location import Location

class DummyLog:
    def add_log_message(self, *args, **kwargs): pass
    def add_message(self, *args, **kwargs): pass
    def print_recent_logs(self, *args, **kwargs): pass
    def clear(self): pass

class DummyUI:
    def draw_ascii_art(self, *args, **kwargs): pass
    def present_choices(self, *args, **kwargs): return "0"
    def display_message(self, *args, **kwargs): pass
    def show_message(self, *args, **kwargs): pass

@pytest.fixture
def game_env():
    game = Game(ui=DummyUI())
    game.GAME_LOG = DummyLog()
    game.setup_world()
    player = Player("Test Player")
    player.money = 100
    player.current_location = Location("loc", "Loc", "A Loc")
    game.player = player
    return game

def test_practice_requires_valid_location(game_env):
    player = game_env.player
    poi = PointOfInterest("street_poi", "Street", "A street", category="DOWNTOWN")
    player.current_poi = poi

    # Should fail in downtown
    res = game_env.do_practice_grind("vocals", 1)
    assert not res.get("ok")
    assert res.get("reason") == "wrong_location"

    # Should work at home and train the specific skill requested
    home_poi = PointOfInterest("home_poi", "Home", "Home", category="HOME")
    player.current_poi = home_poi
    player.skills["vocals"] = 0
    res = game_env.do_practice_grind("vocals", 1)
    assert res.get("ok")
    assert player.skills.get("vocals", 0) > 0
    home_skill = player.skills.get("vocals")

    # Should scale better at studio
    player.skills["vocals"] = 0
    studio_poi = PointOfInterest("studio_poi", "Studio", "Studio", category="STUDIO_RECORDING")
    player.current_poi = studio_poi
    res = game_env.do_practice_grind("vocals", 1)
    assert res.get("ok")
    assert player.skills.get("vocals", 0) > home_skill

def test_open_mic_requires_venue_and_time(game_env):
    player = game_env.player
    player.energy = 50
    home_poi = PointOfInterest("home_poi", "Home", "Home", category="HOME")
    player.current_poi = home_poi

    # Fail at home
    res = game_env.do_open_mic_set()
    assert not res.get("ok")
    assert res.get("reason") == "wrong_location"

    # Attempt at bar
    bar_poi = PointOfInterest("bar_poi", "Bar", "Bar", category="VENUE_BAR")
    player.current_poi = bar_poi

    from game.game_time import current_game_time
    # Fail morning
    current_game_time.hour = 10
    time_before = current_game_time.copy()

    res = game_env.do_open_mic_set()
    assert not res.get("ok")
    assert res.get("reason") == "wrong_time"
    assert current_game_time.minute == time_before.minute and current_game_time.hour == time_before.hour # Time not consumed on failure

    # Succeed evening
    current_game_time.hour = 20
    res = game_env.do_open_mic_set()
    assert res.get("ok")

    # Succeed morning if there's an active OPEN_MIC event
    current_game_time.hour = 10
    from game.event import Event
    bar_poi.events = [Event("Morning Mic", bar_poi, event_type="OPEN_MIC")]
    res = game_env.do_open_mic_set()
    assert res.get("ok")

    # Fail if there is an active competing event
    bar_poi.events = [Event("Club Gig", bar_poi, event_type="CLUB_GIG")]
    res = game_env.do_open_mic_set()
    assert not res.get("ok")
    assert res.get("reason") == "competing_event"

def test_rest_recovers_energy_based_on_location(game_env):
    player = game_env.player
    player.energy = 10

    # Motel should fail without a rental
    motel_poi = PointOfInterest("motel_poi", "Motel", "Motel", category="ACCOMMODATION_MOTEL", rest_quality=0.5)
    player.current_poi = motel_poi
    game_env.rest(8)
    assert player.energy == 10 # Didn't sleep

    # Motel should succeed with rental
    from game.game_time import current_game_time
    checkout = current_game_time.copy()
    checkout.add_hours(24)
    player.rented_accommodation_info = {"poi_id": "motel_poi", "checkout_time_obj": checkout}
    game_env.rest(8)
    assert player.energy > 10 # Successfully slept

    # Reset energy
    player.energy = 10

    # Home should work natively
    home_poi = PointOfInterest("home_poi", "Home", "Home", category="HOME", rest_quality=0.5)
    player.current_poi = home_poi
    player.has_home = True

    game_env.rest(8) # Should sleep_rest via location engine
    assert player.energy > 10

    # Reset energy
    player.energy = 10

    # Home should fail without has_home
    player.has_home = False
    game_env.rest(8)
    assert player.energy == 10

def test_purchase_essential_item_grants_gear(game_env):
    player = game_env.player
    music_store = PointOfInterest("store", "Store", "Store", category="SHOP_MUSIC")
    player.current_poi = music_store

    # Buy strings
    res = game_env.buy_essential_item("guitar_strings_basic")
    assert res.get("ok")
    assert any(g.item_id == "guitar_strings_basic" for g in player.gear_inventory)

    # Buy acoustic guitar
    res = game_env.buy_essential_item("worn_acoustic_guitar")
    assert res.get("ok")
    assert any(g.item_id == "worn_acoustic_guitar" for g in player.gear_inventory)

    # Test purchase failure due to wrong location
    street_poi = PointOfInterest("street_poi", "Street", "Street", category="DOWNTOWN")
    player.current_poi = street_poi
    res = game_env.buy_essential_item("guitar_strings_basic")
    assert not res.get("ok")
    assert res.get("reason") == "wrong_location"
