"""Integration coverage for bookable, playable, and settled live itineraries."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from test_playable_career import career, MenuUI
from game.game import Game
from game.game_time import current_game_time
from game.song import Song
from game.event import Event
from game.live_bookings import propose_tour, commit_tour, booking_desk, cancel_remaining, reconcile_bookings


def test_quote_and_decline_have_no_world_or_money_side_effects(career):
    game, ui = career
    cash = game.player.money;clock = current_game_time.copy()
    counts = [len(v.events_hosted) for c in game.WORLD_MAP.values() for v in c.venues]
    a = propose_tour(game, 'local_intro_tour');b = propose_tour(game, 'local_intro_tour')
    assert a == b and a['ok']
    assert a['living_estimate'] >= a['days'] * 7
    ui.choices.extend(['offers', 'local_intro_tour', 'back']);booking_desk(game)
    assert game.player.money == cash and current_game_time == clock
    assert not game.player.schedule.scheduled_items and not game.player.current_tour_id
    assert counts == [len(v.events_hosted) for c in game.WORLD_MAP.values() for v in c.venues]


def test_invalid_second_venue_and_calendar_conflict_commit_nothing(career):
    game, _ = career
    proposal = propose_tour(game, 'local_intro_tour')
    bad = deepcopy(proposal);bad['legs'][1]['venue_id'] = 'missing'
    cash = game.player.money
    counts = [len(v.events_hosted) for c in game.WORLD_MAP.values() for v in c.venues]
    assert not commit_tour(game, bad)['ok']
    assert not game.player.schedule.scheduled_items and game.player.money == cash
    assert counts == [len(v.events_hosted) for c in game.WORLD_MAP.values() for v in c.venues]
    leg = proposal['legs'][1]
    game.player.schedule.add_event(leg['start'], leg['end'], 'Existing commitment', 'Personal')
    assert not commit_tour(game, proposal)['ok']
    assert len(game.player.schedule.scheduled_items) == 1 and game.player.money == cash


def test_booking_desk_creates_dates_and_prevents_early_performance(career):
    game, ui = career
    ui.choices.extend(['offers', 'local_intro_tour', 'book']);booking_desk(game)
    key = game.player.current_tour_id
    ledger = game.player.tour_ledgers[key]
    assert len(ledger['legs']) == 2 and game.player.money == 490
    first = ledger['legs'][0]
    event = game._find_scheduled_event(first['event_id'], first['venue_id'])
    assert event.booking_id == key and event.guaranteed_payout == first['guarantee']
    assert not event.can_perform(game.player)[0]
    assert all(item.details['booking_id'] == key for item in game.player.schedule.scheduled_items)


def play_booked_date(game, ui, leg):
    venue = game.get_poi_or_venue_by_id(leg['venue_id'])
    game.player.current_poi = venue;game.selected_poi = venue
    game.player.current_location = game.WORLD_MAP[leg['city']]
    current_game_time.__dict__.update(vars(leg['start']))
    game.check_for_scheduled_events()
    assert game.game_state == 'performance'
    ui.choices.append('0');game.handle_performance_scene()
    assert game.performance_stage == 'playing'
    for _ in range(30):
        if game.performance_stage == 'finish':
            game.handle_performance_scene();break
        state = game.performance_manager.state
        ui.choices.append({'player_input': 'safe', 'resolution': 'ok', 'summary': 'finish'}[state])
        game.handle_performance_scene()
    assert game.performance_manager is None


def test_complete_two_date_tour_pays_settles_and_can_resume_save(career, tmp_path):
    game, ui = career
    game.player.songs_written.append(Song('Shoreline', game.player.name, 'Rock', song_quality=.7))
    result = commit_tour(game, propose_tour(game, 'local_intro_tour'))
    ledger = game.player.tour_ledgers[result['booking_id']]
    play_booked_date(game, ui, ledger['legs'][0])
    assert ledger['legs'][0]['status'] == 'played' and ledger['status'] == 'ongoing'
    path = tmp_path / 'tour.json';assert game.save_game(str(path))
    new_ui = MenuUI();resumed = Game(new_ui);assert resumed.load_game(str(path))
    ledger = resumed.player.tour_ledgers[result['booking_id']]
    resumed.player.energy = 100
    play_booked_date(resumed, new_ui, ledger['legs'][1])
    assert ledger['status'] == 'completed'
    assert ledger['income'] >= 120 and len(ledger['completed_gigs']) == 2
    assert resumed.player.current_tour_id is None
    assert 'local_intro_tour' in resumed.player.completed_tour_ids
    assert not resumed.player.schedule.scheduled_items
    income = ledger['income'];reconcile_bookings(resumed)
    assert ledger['income'] == income


def test_missed_dates_close_tour_once_without_teleport_or_payment(career):
    game, _ = career
    result = commit_tour(game, propose_tour(game, 'local_intro_tour'))
    ledger = game.player.tour_ledgers[result['booking_id']]
    home = game.player.current_poi;cash = game.player.money
    current_game_time.__dict__.update(vars(ledger['legs'][-1]['end']))
    current_game_time.add_hours(1)
    reconcile_bookings(game)
    assert ledger['status'] == 'closed_with_missed_dates'
    assert ledger['income'] == 0 and game.player.current_tour_id is None
    assert game.player.current_poi is home and game.player.money == cash
    stress = game.player.stress;reconcile_bookings(game)
    assert game.player.stress == stress


def test_cancellation_closes_dates_and_never_refunds_fee(career):
    game, _ = career
    result = commit_tour(game, propose_tour(game, 'local_intro_tour'))
    cash = game.player.money
    cancel_remaining(game, result['booking_id'])
    ledger = game.player.tour_ledgers[result['booking_id']]
    assert ledger['status'] == 'cancelled' and game.player.money == cash
    assert not game.player.schedule.scheduled_items and game.player.current_tour_id is None
    assert all(leg['status'] == 'cancelled' for leg in ledger['legs'])


def test_legacy_empty_active_tour_is_recoverable(career):
    game, _ = career
    game.player.current_tour_id = 'old'
    game.player.tour_ledgers['old'] = {'name': 'Old tour', 'status': 'ongoing', 'income': 0, 'expenses': 0}
    reconcile_bookings(game)
    assert game.player.current_tour_id is None
    assert game.player.tour_ledgers['old']['status'] == 'legacy_closed'


def test_player_selects_entire_live_setlist_in_order(career):
    game, ui = career
    songs = [Song(str(i), game.player.name, 'Rock', song_quality=.2 + i / 10) for i in range(4)]
    game.player.songs_written = songs
    game.active_performance = Event('Club set', game.player.current_location.venues[0], 'CLUB_GIG')
    game.performance_stage = 'choose_song'
    ui.choices.extend(['3', '0', '2', 'play'])
    for _ in range(4): game.handle_performance_scene()
    assert game.performance_setlist == [songs[3], songs[0], songs[2]]
    assert game.performance_manager.setlist == game.performance_setlist


def test_all_authored_tours_have_reachable_complete_quotes(career):
    game, ui = career
    for template in game.TOURS:
        game.player.fame = template['min_fame']
        proposal = propose_tour(game, template['tour_id'])
        assert proposal['ok'], proposal
        assert len(proposal['legs']) == template['num_gigs']
        assert all(leg['route'] is not None for leg in proposal['legs'])
    game.player.fame = 1000
    ui.choices.extend(['offers', 'local_intro_tour', 'back']);booking_desk(game)
    from game.live_bookings import propose_local_show
    city = game.WORLD_MAP['Philadelphia, PA'];game.player.current_location = city
    hall = next(v for v in city.venues if v.venue_type == 'CONCERT_HALL')
    assert propose_local_show(game, hall.venue_id, 2)['legs'][0]['event_type'] == 'CONCERT'
    assert not game.player.schedule.scheduled_items


def test_insufficient_cash_and_expired_quote_book_nothing(career):
    game, _ = career
    proposal = propose_tour(game, 'local_intro_tour')
    game.player.money = 0
    assert not commit_tour(game, proposal)['ok']
    game.player.money = 500
    current_game_time.add_days(1)
    assert not commit_tour(game, proposal)['ok']
    assert not game.player.schedule.scheduled_items and game.player.money == 500


def test_stage_rental_is_paid_and_returned_without_mutating_catalog(career):
    from game.live_bookings import prepare_stage, settle_show
    from game_data.gear_catalog import GEAR_CATALOG
    game, ui = career
    key = next(key for key, item in GEAR_CATALOG.items() if item.gear_type == 'INSTRUMENT_ELECTRIC')
    venue = game.player.current_location.venues[0]
    venue.can_rent_gear = True;venue.available_rental_gear_ids = [key];venue.gear_rental_fee = 35
    event = Event('Rental set', venue, required_gear_types=['INSTRUMENT_ELECTRIC'])
    game.active_performance = event
    inventory = list(game.player.gear_inventory); cash = game.player.money
    original_condition = GEAR_CATALOG[key].durability
    ui.choices.append('rent')
    assert prepare_stage(game)
    assert game.player.money == cash - 35
    loan = event.stage_loans[0]
    assert loan is not GEAR_CATALOG[key] and loan in game.player.gear_inventory
    loan.take_damage(10)
    settle_show(game, event, 'played', 50)
    assert game.player.gear_inventory == inventory
    assert GEAR_CATALOG[key].durability == original_condition


def test_declining_stage_rental_never_charges_or_grants_gear(career):
    from game.live_bookings import prepare_stage
    from game_data.gear_catalog import GEAR_CATALOG
    game, ui = career
    venue = game.player.current_location.venues[0]
    venue.can_rent_gear = True;venue.gear_rental_fee = 35
    venue.available_rental_gear_ids = [next(key for key, item in GEAR_CATALOG.items() if item.gear_type == 'INSTRUMENT_ELECTRIC')]
    game.active_performance = Event('Rental set', venue, required_gear_types=['INSTRUMENT_ELECTRIC'])
    inventory = list(game.player.gear_inventory);cash = game.player.money
    ui.choices.append('back')
    assert not prepare_stage(game)
    assert game.player.money == cash and game.player.gear_inventory == inventory


def test_local_show_menu_can_book_around_active_tour(career):
    game, ui = career
    result = commit_tour(game, propose_tour(game, 'local_intro_tour'))
    tour_id = result['booking_id']
    venue = game.player.current_location.venues[0]
    ui.choices.extend(['local', venue.venue_id, '2', 'book']);booking_desk(game)
    assert len(game.player.tour_ledgers) == 2
    assert game.player.current_tour_id == tour_id
    singles = [ledger for ledger in game.player.tour_ledgers.values() if ledger['kind'] == 'single']
    assert len(singles) == 1 and len(singles[0]['legs']) == 1
    assert len(game.player.schedule.scheduled_items) == 3
    assert game.player.money == 485


def test_local_show_settles_without_closing_the_tour(career):
    from game.live_bookings import propose_local_show
    game, ui = career
    game.player.songs_written.append(Song('Local Set', game.player.name, 'Rock', song_quality=.7))
    tour = commit_tour(game, propose_tour(game, 'local_intro_tour'))
    venue = game.player.current_location.venues[0]
    single = commit_tour(game, propose_local_show(game, venue.venue_id, 2))
    ledger = game.player.tour_ledgers[single['booking_id']]
    play_booked_date(game, ui, ledger['legs'][0])
    assert ledger['status'] == 'completed'
    assert game.player.current_tour_id == tour['booking_id']
    assert 'local_show' not in game.player.completed_tour_ids
    assert len(game.player.schedule.scheduled_items) == 2


def test_dynamic_tour_offer_is_reviewed_before_booking(career):
    game, ui = career
    key = 'tour_offer_local_intro_tour'
    game.player.active_opportunities[key] = {'status': 'available'}
    ui.choices.append('back');game.handle_opportunity(key)
    assert game.player.active_opportunities[key]['status'] == 'available'
    assert not game.player.schedule.scheduled_items
    ui.choices.append('book');game.handle_opportunity(key)
    assert game.player.active_opportunities[key]['status'] == 'completed'
    assert len(game.player.schedule.scheduled_items) == 2


def test_missing_venue_after_booking_does_not_trap_career(career):
    game, _ = career
    result = commit_tour(game, propose_tour(game, 'local_intro_tour'))
    ledger = game.player.tour_ledgers[result['booking_id']]
    for leg in ledger['legs']:
        venue = game.get_poi_or_venue_by_id(leg['venue_id'])
        venue.events_hosted = [event for event in venue.events_hosted if event.event_id != leg['event_id']]
    current_game_time.__dict__.update(vars(ledger['legs'][-1]['end']))
    current_game_time.add_hours(1)
    reconcile_bookings(game)
    assert ledger['status'] == 'closed_with_missed_dates'
    assert game.player.current_tour_id is None
    assert not game.player.schedule.scheduled_items
