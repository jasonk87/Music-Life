"""Play the passenger phone and public appearance through their real menus."""
from unittest.mock import patch
import pytest
from test_playable_career import career, MenuUI
from game.game import Game
from game.game_time import current_game_time
from game.travel_manager import TravelManager
from game.public_appearances import run_signing
from game.merch_system import MerchItem


def journey(game, distance=120):
    destination = next(city for city in game.WORLD_MAP.values() if city is not game.player.current_location)
    tm = TravelManager(game.player, destination, distance, 'bus')
    game.travel_manager = tm
    game.transit_session = game.transit_layer.start_session(tm)
    game.game_state = 'travel_active'
    return tm


def contact(game):
    npc = next(iter(game.NPC_REGISTRY.values()))
    game.player.contacts.append(npc.npc_id)
    return npc


def signing(game):
    p = game.player
    p.current_poi = next(poi for poi in p.current_location.points_of_interest if poi.category == 'SHOP_MUSIC')
    p.active_opportunities['autograph_signing'] = {'status': 'available'}
    p.fame = 420
    p.energy = 95
    p.stress = 10
    p.hunger = 10
    p.money = 500
    game.game_state = 'explore'


def minutes_since(start):
    return round(current_game_time.days_difference(start) * 1440)


def test_contact_details_dispatch_returns_and_actual_call_has_daily_limit(career):
    game, ui = career
    npc = contact(game)
    game.phone_menu_state = 'contacts'
    ui.choices.extend([npc.npc_id, 'call'])
    start = current_game_time.copy()
    score = npc.relationship_score
    game.handle_phone_menu()
    assert game.phone_menu_state == 'contact_details'
    game.handle_phone_menu()
    assert game.phone_menu_state == 'contacts'
    assert minutes_since(start) == 15
    assert npc.relationship_score == score + 2
    ui.choices.extend([npc.npc_id, 'call'])
    game.handle_phone_menu(); game.handle_phone_menu()
    assert npc.relationship_score == score + 2 and minutes_since(start) == 15


def test_passenger_phone_inspection_is_free_and_call_moves_same_journey(career):
    game, ui = career
    npc = contact(game)
    tm = journey(game)
    start = current_game_time.copy()
    ui.choices.extend(['phone', 'calendar', 'news', 'back'])
    game.handle_travel_active_state()
    assert minutes_since(start) == 0 and tm.distance_covered == 0
    assert game.player.current_poi is None
    ui.choices.extend(['phone', 'contacts', npc.npc_id, 'call', 'back'])
    game.handle_travel_active_state()
    assert minutes_since(start) == 15 and tm.distance_covered == 15
    assert game.travel_manager is tm and game.game_state == 'travel_active'
    assert not ui.choices


def test_call_can_finish_after_arriving_without_extending_the_route(career):
    game, ui = career
    npc = contact(game)
    tm = journey(game, 5)
    start = current_game_time.copy()
    ui.choices.extend(['phone', 'contacts', npc.npc_id, 'call'])
    game.handle_travel_active_state()
    assert minutes_since(start) == 15
    assert tm.travel_time_elapsed == pytest.approx(5 / 60)
    assert game.player.current_location is tm.destination
    assert game.game_state == 'main_menu' and game.travel_manager is None


def test_continue_removes_hourly_confirmations_and_stops_at_arrival(career):
    game, ui = career
    tm = journey(game, 135)
    game.player.energy = 100; game.player.hunger = 0
    start = current_game_time.copy()
    ui.choices.append('continue')
    with patch('game.travel_manager.generate_road_event', return_value=(None, 0, 0, 0, False)):
        game.handle_travel_active_state()
    assert minutes_since(start) == 135
    assert game.player.current_location is tm.destination
    assert tm.is_finished


def test_road_delays_are_real_and_interrupt_continuous_travel(career):
    game, ui = career
    tm = journey(game, 200)
    game.player.energy = 100; game.player.hunger = 0
    start = current_game_time.copy()
    ui.choices.append('continue')
    with patch('game.travel_manager.generate_road_event', return_value=('Signal failure', 2, 5, 0, False)):
        game.handle_travel_active_state()
    assert not tm.is_finished and tm.distance_covered == 60
    assert minutes_since(start) == 120 and tm.delay_minutes == 60
    ui.choices.append('wait')
    game.handle_travel_active_state()
    assert tm.distance_covered == 60 and tm.delay_minutes == 0
    assert minutes_since(start) == 180


def test_travel_action_partition_does_not_reroll_road_events(career):
    game, _ = career
    tm = journey(game, 200)
    with patch('game.travel_manager.generate_road_event', return_value=(None, 0, 0, 0, False)) as events:
        for _ in range(8): tm.advance_minutes(15)
    assert tm.distance_covered == 120
    assert events.call_count == 1


def test_short_final_leg_does_not_grant_an_hour_of_rest(career):
    game, ui = career
    journey(game, 5)
    game.player.energy = 40
    ui.choices.append('sleep')
    start = current_game_time.copy()
    game.handle_travel_active_state()
    assert minutes_since(start) == 5
    assert game.player.energy < 42


@pytest.mark.parametrize('mode', ['walk', 'bike'])
def test_self_powered_travel_is_not_a_passenger_seat(career, mode):
    game, _ = career
    tm = journey(game)
    tm.transport_mode = mode
    options = game.transit_layer.available_actions(game, tm)
    assert not {'phone', 'sleep', 'call', 'drink', 'gear_check'} & options.keys()


def test_signing_decline_and_remote_attempt_have_no_reward_or_time_cost(career):
    game, ui = career
    signing(game)
    start = current_game_time.copy()
    money = game.player.money
    ui.choices.append('back')
    run_signing(game)
    assert not hasattr(game.player, 'appearance_history')
    assert minutes_since(start) == 0 and game.player.money == money
    game.game_state = 'travel_active'
    run_signing(game)
    assert minutes_since(start) == 0 and not ui.choices


def test_signing_sells_only_real_stock_and_keeps_an_honest_record(career, tmp_path):
    game, ui = career
    signing(game)
    game.player.merch_stock = [MerchItem('tees', 'Tees', 'tshirt', 40, 20, 3)]
    ui.choices.extend(['merch', 'kind', 'brisk', 'extend'])
    money = game.player.money
    start = current_game_time.copy()
    game.handle_opportunity('autograph_signing')
    record = game.player.appearance_history[-1]
    assert record['units_sold'] == 3 and record['revenue'] == 60
    assert game.player.merch_stock[0].unit_count == 0
    assert game.player.money == money + 60
    assert record['met'] + record['left'] == record['turnout']
    assert record['minutes'] == minutes_since(start) == 120
    assert game.game_state == 'explore'
    assert game.world_memory.query(event_type='public_appearance')
    # Cannot reopen the same invitation to farm rewards.
    game.handle_opportunity('autograph_signing')
    assert game.player.money == money + 60 and minutes_since(start) == 120
    path = tmp_path / 'signing.json'
    assert game.save_game(str(path))
    fresh = Game(MenuUI())
    assert fresh.load_game(str(path))
    assert fresh.player.appearance_history == game.player.appearance_history


def test_no_stock_signing_and_early_close_do_not_conjure_cash(career):
    game, ui = career
    signing(game)
    money = game.player.money
    ui.choices.extend(['personal', 'close'])
    run_signing(game)
    record = game.player.appearance_history[-1]
    assert game.player.money == money and record['revenue'] == 0
    assert record['minutes'] == 30 and record['left'] > record['met']
    assert record['fame_change'] < 0


def test_signing_policy_changes_throughput_and_tradeoffs(career):
    game, ui = career
    signing(game)
    start = current_game_time.copy()
    p = game.player
    ui.choices.extend(['personal', 'kind', 'personal', 'close'])
    run_signing(game)
    personal = p.appearance_history[-1].copy()
    p.appearance_history = []
    current_game_time.__dict__.update(vars(start))
    signing(game)
    ui.choices.extend(['brisk', 'kind', 'brisk', 'close'])
    run_signing(game)
    brisk = p.appearance_history[-1]
    assert brisk['met'] > personal['met']
    assert personal['goodwill'] / personal['met'] > brisk['goodwill'] / brisk['met']
    assert brisk['left'] < personal['left']


def test_guest_request_can_be_declined_then_recorded_but_not_repeated(career):
    game, ui = career
    npc = contact(game)
    key = f'guest_feature_{npc.npc_id}'
    game.player.active_opportunities[key] = {'status': 'available'}
    game.player.energy = 100
    money = game.player.money
    start = current_game_time.copy()
    ui.choices.append('back')
    game.handle_opportunity(key)
    assert game.player.money == money and minutes_since(start) == 0
    ui.choices.append('record')
    game.handle_opportunity(key)
    assert game.player.money >= money + 100 and minutes_since(start) == 240
    earned = game.player.money
    game.handle_opportunity(key)
    assert game.player.money == earned and minutes_since(start) == 240


def test_booking_from_passenger_phone_reserves_a_real_date_and_uses_journey_time(career):
    game, ui = career
    tm = journey(game)
    origin = game.player.current_location
    venue = next(v for v in origin.venues if v.venue_type in ('BAR_GIG', 'CLUB', 'HALL'))
    start = current_game_time.copy()
    money = game.player.money
    ui.choices.extend(['phone', 'bookings', 'local', venue.venue_id, '2', 'book', 'back'])
    game.handle_travel_active_state()
    assert minutes_since(start) == 15 and tm.distance_covered == 15
    assert game.player.money == money - 5
    ledger = next(iter(game.player.tour_ledgers.values()))
    assert ledger['legs'][0]['city'] == origin.name
    assert game.player.current_poi is None


def test_signing_invitation_follows_next_city_and_respects_local_cooldown(career):
    game, ui = career
    signing(game)
    ui.choices.extend(['personal', 'close'])
    run_signing(game)
    p = game.player
    p.current_tour_id = 'active-tour'
    game.check_for_new_opportunities()
    assert p.active_opportunities['autograph_signing']['status'] == 'completed'
    next_city = next(city for city in game.WORLD_MAP.values() if city is not p.current_location
                     and any(poi.category == 'SHOP_MUSIC' for poi in city.points_of_interest))
    p.current_location = next_city
    game.check_for_new_opportunities()
    invitation = p.active_opportunities['autograph_signing']
    assert invitation['status'] == 'available'
    assert invitation['poi_id'] in [poi.poi_id for poi in next_city.points_of_interest]


def test_signing_cannot_quicksave_an_unfinished_scene(career):
    game, ui = career
    signing(game)
    def close_after_check(options):
        assert game.game_state == 'appearance'
        with patch.object(game, 'save_game') as save:
            assert not game.quick_save()
            save.assert_not_called()
        return 'close'
    ui.choices.extend(['personal', close_after_check])
    run_signing(game)


def test_calendar_accepts_february_thirtieth_and_spanning_dates():
    from game.player_schedule import PlayerSchedule
    from game.game_time import GameTime
    schedule = PlayerSchedule()
    start, end = GameTime(2024, 2, 29), GameTime(2024, 3, 2)
    schedule.add_event(start, end, 'Long journey', 'Travel')
    assert len(schedule.get_events_for_day(2024, 2, 30)) == 1
    assert len(schedule.get_events_for_week(2024, 2, 30)) == 1
    assert not schedule.get_events_for_day(2024, 3, 3)


def test_continuous_travel_stops_when_a_commitment_begins_between_hourly_ticks(career):
    game, ui = career
    tm = journey(game)
    start = current_game_time.copy()
    appointment = start.copy(); appointment.advance_time(25)
    end = appointment.copy(); end.advance_time(30)
    game.player.schedule.add_event(appointment, end, 'Phone interview', 'Interview')
    ui.choices.append('continue')
    game.handle_travel_active_state()
    assert minutes_since(start) == 25 and tm.distance_covered == 25
    assert game.game_state == 'travel_active'
