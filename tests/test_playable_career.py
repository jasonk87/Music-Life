"""Career regressions through the same handlers and data used by the menus."""
import json
import os
import random
from collections import deque
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pytest
from game.game import Game
from game.game_time import GameTime, current_game_time
from game.band import Band, BandMember
from game.staff import StaffMember
from game.song import Song
from game.album import Album
from game.save_manager import JSONSaveManager
from game.streaming_dsp import StreamingPlatformSystem, PlaylistPlacement
from game.traits import TRAIT_CATALOG
from game.event import Event
from game.performance import PerformanceManager


class MenuUI:
    FONT_TITLE = None
    def __init__(self):
        self.choices = deque()
        self.texts = deque()
        self.messages = []
    def add_log_message(self, text): self.messages.append(text)
    add_message = add_log_message
    def present_choices(self, options, title, context=None):
        assert self.choices, f'Unexpected menu: {title}: {options}'
        selected = self.choices.popleft()
        key = selected(options) if callable(selected) else selected
        assert key in options, (title, key, options)
        return key
    def get_text_input(self, prompt, context=None):
        assert self.texts, prompt
        return self.texts.popleft()
    def clear_screen(self): pass
    def draw_text(self, *args, **kwargs): pass
    def draw_ascii_art(self, *args, **kwargs): pass
    def update_display(self): pass


@pytest.fixture
def career():
    random.seed(23)
    current_game_time.__dict__.update(vars(GameTime()))
    ui = MenuUI()
    game = Game(ui)
    assert game.setup_world()
    game.initialize_player()
    ui.texts.append('Alex Shore')
    ui.choices.append('indie')
    game.handle_character_creation()
    return game, ui


def choose_place_action(game, ui, text):
    game.game_state = 'explore'
    game.explore_menu_state = 'poi'
    game.selected_poi = game.player.current_poi
    ui.choices.append(lambda options: next(key for key, label in options.items() if text.lower() in label.lower()))
    game.handle_explore_menu()


def write_through_menus(game, ui, title):
    choose_place_action(game, ui, 'write')
    assert game.explore_menu_state == 'write_song_menu'
    ui.choices.extend(['Rock', 'none', 'yes', 'work', 'work'])
    ui.texts.append(title)
    for _ in range(6): game.handle_explore_menu()
    assert game.player.songs_written[-1].title == title


def test_new_player_can_write_record_release_and_resume(career, tmp_path):
    game, ui = career
    write_through_menus(game, ui, 'Boardwalk Static')
    choose_place_action(game, ui, 'record a home demo')
    assert game.explore_menu_state == 'record_song'
    ui.choices.append('0')
    game.handle_explore_menu()
    song = game.player.songs_written[0]
    assert song.is_recorded, ui.messages[-5:]
    money = game.player.money
    game.music_menu_state = 'release_song'
    ui.choices.append('0')
    game.handle_music_menu()
    assert song.is_released and game.player.money == money - 15
    assert song.song_id in game.streaming_system.catalog
    saved_date = song.release_date.copy()
    game._advance_time_with_needs(24 * 60)
    assert song.release_date == saved_date
    assert game.streaming_system.catalog[song.song_id].total_streams > 0
    path = tmp_path / 'career.json'
    assert game.save_game(str(path))
    fresh = Game(MenuUI())
    assert fresh.load_game(str(path))
    assert fresh.player.songs_written[0].author == 'Alex Shore'
    assert fresh.player.songs_written[0].release_date == saved_date
    assert fresh.player.current_poi is fresh.get_poi_or_venue_by_id(game.player.current_poi.poi_id)


def test_full_career_graph_preserves_band_schedule_and_world_identity(career, tmp_path):
    game, _ = career
    p = game.player
    p.band = Band('Low Tide', p)
    p.band.add_member(BandMember('Rae'))
    p.staff = [StaffMember('Jo', 'Roadie', 80)]
    p.traits = [TRAIT_CATALOG['charismatic']]
    song = Song('Salt Air', p.name, 'Rock', originality=.91, theme='summer_nostalgia')
    song.mark_as_recorded(.8);song.mark_as_released(current_game_time)
    p.songs_written.append(song)
    p.albums_released = [Album('Tide', p.name, [song])]
    npc = next(iter(game.NPC_REGISTRY.values()))
    p.contacts.append(npc.npc_id)
    game.npc_world_sim.ensure_npc_state(npc)
    npc.relationship_state.trust = 57
    game.early_life.schedule_job_shift(p, 'retail_corner_mart')
    path = tmp_path / 'career.json'
    assert game.save_game(str(path))
    new = Game(MenuUI())
    assert new.load_game(str(path))
    assert new.player.band.members[0] is new.player
    assert len(new.player.band.members) == 2
    assert len(new.player.staff) == 1 and len(new.player.traits) == 1
    assert new.player.albums_released[0].tracks[0] is new.player.songs_written[0]
    assert len(new.player.schedule.scheduled_items) == len(p.schedule.scheduled_items)
    assert new.NPC_REGISTRY[npc.npc_id].relationship_state.trust == 57
    assert new.npc_world_sim.game is new
    assert new.player.songs_written[0].originality == .91


def test_failed_save_keeps_previous_file(career, tmp_path):
    game, _ = career
    path = tmp_path / 'career.json'
    assert game.save_game(str(path))
    before = path.read_bytes()
    with patch('game.save_manager.os.replace', side_effect=OSError('disk unavailable')):
        assert not game.save_game(str(path))
    assert path.read_bytes() == before
    assert not list(tmp_path.glob('*.tmp'))


def test_invalid_graph_does_not_replace_active_career(career, tmp_path):
    game, _ = career
    path=tmp_path/'career.json'
    assert game.save_game(str(path))
    payload=json.loads(path.read_text(encoding='utf-8'))
    node=next(n for n in payload['career_archive']['nodes'] if n['kind']=='object')
    node['cls']='subprocess.Popen'
    path.write_text(json.dumps(payload),encoding='utf-8')
    p=game.player; clock=current_game_time.copy()
    assert not game.load_game(str(path))
    assert game.player is p and current_game_time==clock


def test_calendar_processes_each_day_once_over_month_boundary(career):
    game, _ = career
    current_game_time.__dict__.update(vars(GameTime(2024, 1, 30, 23, 0)))
    game.last_world_day=current_game_time.day_index()
    start=game.last_world_day
    days=[];weeks=[]
    with patch.object(game,'_daily_world_update',side_effect=lambda:days.append(current_game_time.day_index())), patch.object(game,'_weekly_world_update',side_effect=lambda:weeks.append(current_game_time.day_index())):
        game._advance_time_with_needs(60+8*1440)
        game._process_calendar_updates()
    assert days==list(range(start+1,start+10))
    assert weeks==[d for d in days if d//7>(d-1)//7]
    assert current_game_time.month==2 and current_game_time.day==9


def test_weekly_chart_update_is_not_daily(career):
    game, _=career
    with patch.object(game.ACTIVE_CHARTS[0],'update_weekly',return_value=[]) as chart:
        start=current_game_time.day_index()
        for _ in range(14): game._advance_time_with_needs(1440)
    assert chart.call_count==2
    assert game.last_world_day==start+14


def test_playlist_streams_do_not_compound(career):
    game, _=career
    dsp=StreamingPlatformSystem()
    song=Song('Test',game.player.name,'Rock',song_quality=.8);song.mark_as_recorded(.8)
    t=dsp.register_song_for_streaming(song,20)
    t.active_playlists=[PlaylistPlacement('p','Playlist','EDITORIAL','Rock',1000,2000,2)]
    dsp.process_daily_streams_and_royalties(game.player)
    first=t.daily_streams
    dsp.process_daily_streams_and_royalties(game.player)
    assert t.daily_streams<=first
    dsp.process_daily_streams_and_royalties(game.player)
    assert t.daily_streams<1000
    assert t.total_royalties_earned>0


def test_authored_rest_practice_food_and_recording_actions_work(career):
    game, ui=career
    p=game.player
    p.energy=30
    before=current_game_time.copy()
    choose_place_action(game,ui,'Rest (8 hours)')
    assert current_game_time.days_difference(before)==pytest.approx(8/24)
    assert p.energy>30
    skill=p.skills['guitar']
    choose_place_action(game,ui,'Practice')
    assert p.skills['guitar']>skill
    diner=game.get_poi_or_venue_by_id('asbury_greasy_spoon')
    p.current_poi=diner;p.hunger=70
    cash=p.money
    choose_place_action(game,ui,'Breakfast')
    assert p.money==cash-8 and p.hunger<40


def test_venue_event_menu_survives_dispatch(career):
    game, ui=career
    venue=game.WORLD_MAP['Asbury Park, NJ'].venues[0]
    game.player.current_poi=venue
    choose_place_action(game,ui,'View upcoming events')
    assert game.explore_menu_state=='view_events' and game.selected_poi is venue


def test_performance_plays_entire_setlist_and_spends_time(career):
    game, _=career
    songs=[Song(f'Track {i}',game.player.name,'Rock',song_quality=.7) for i in range(3)]
    game.performance_setlist=songs
    event=Event('Club set',game.WORLD_MAP['Asbury Park, NJ'].venues[0],event_type='CLUB_GIG')
    manager=PerformanceManager(game,event,songs[0],game.ui)
    manager.state='player_input'
    before=current_game_time.copy()
    played=[]
    while manager.state!='summary':
        if manager.state=='player_input':
            played.append(manager.song.title);manager.handle_input('safe')
        else:manager.handle_input('ok')
    assert set(played)=={s.title for s in songs}
    assert current_game_time>before
    assert game.player.energy<100


def test_catalog_gear_is_not_damaged_by_a_career(career):
    from game_data.gear_catalog import GEAR_CATALOG
    game,_=career
    guitar=next(g for g in game.player.gear_inventory if g.item_id=='worn_acoustic_guitar')
    assert guitar is not GEAR_CATALOG['worn_acoustic_guitar']
    original=GEAR_CATALOG['worn_acoustic_guitar'].durability
    guitar.take_damage(20)
    assert GEAR_CATALOG['worn_acoustic_guitar'].durability==original


def test_gig_through_venue_and_performance_menus(career):
    game, ui = career
    game.player.songs_written.append(Song('Night Bus', game.player.name, 'Rock', song_quality=.7))
    venue = next(v for v in game.player.current_location.venues
                 if any(e.event_type == 'OPEN_MIC' for e in v.events_hosted))
    game.player.current_poi = venue
    choose_place_action(game, ui, 'View upcoming events')
    index = next(i for i, e in enumerate(venue.events_hosted) if e.event_type == 'OPEN_MIC')
    event = venue.events_hosted[index]
    ui.choices.append(str(index)); game.handle_explore_menu()
    assert game.game_state == 'performance'
    ui.choices.append('0'); game.handle_performance_scene()
    before = current_game_time.copy(); cash = game.player.money
    for _ in range(30):
        if game.performance_stage == 'finish':
            game.handle_performance_scene(); break
        state = game.performance_manager.state
        ui.choices.append({'player_input': 'safe', 'resolution': 'ok', 'summary': 'finish'}[state])
        game.handle_performance_scene()
    assert game.performance_manager is None
    assert current_game_time > before and game.player.money > cash
    assert not event.can_perform(game.player)[0]


def test_authored_bus_hub_ticket_and_arrival(career):
    game, ui = career
    city = game.player.current_location
    hub = next(p for p in city.points_of_interest if p.category in ('BUS_STOP', 'TRANSPORT_BUS', 'TRANSPORT_HUB'))
    destination = next(name for name, route in city.travel_connections.items() if route['method'].lower() == 'bus')
    game.player.current_poi = hub
    game.player.money = 500
    before = current_game_time.copy()
    ui.choices.extend(['inter_city', destination, 'public', 'economy'])
    game.handle_travel_menu()
    assert game.game_state == 'travel_active'
    for _ in range(24):
        if game.game_state != 'travel_active': break
        ui.choices.append('wait');game.handle_travel_active_state()
    assert game.player.current_location is game.WORLD_MAP[destination]
    assert game.player.current_poi in game.player.current_location.points_of_interest
    assert game.player.money < 500 and current_game_time > before


def test_ticket_cancel_does_not_spend_money_or_time(career):
    game, ui = career
    city = game.player.current_location
    game.player.current_poi = next(p for p in city.points_of_interest if p.category in ('BUS_STOP', 'TRANSPORT_BUS', 'TRANSPORT_HUB'))
    destination = next(name for name, r in city.travel_connections.items() if r['method'].lower() == 'bus')
    before = current_game_time.copy();cash = game.player.money
    ui.choices.extend(['inter_city', destination, 'public', 'back'])
    game.handle_travel_menu()
    assert current_game_time == before and game.player.money == cash
    assert game.travel_manager is None


def test_work_is_voluntary_and_requires_attendance(career):
    from game.career_actions import shift_listings
    game, ui = career
    assert not game.player.schedule.scheduled_items
    cash = game.player.money; home = game.player.current_poi
    ui.choices.extend(['retail_corner_mart', 'book'])
    shift_listings(game)
    event = game.player.schedule.scheduled_items[0]
    assert game.player.money == cash
    current_game_time.__dict__.update(vars(event.start_time))
    game.check_for_scheduled_events()
    assert game.player.current_poi is home
    assert game.player.money == cash and game.player.job_reliability < 50
    assert not game.player.schedule.scheduled_items


def test_rented_vehicle_expires_across_month_boundary(career):
    from game.world_actions import _add_road_vehicle
    game, _ = career
    current_game_time.__dict__.update(vars(GameTime(2024, 1, 30, 8, 0)))
    game.last_world_day = current_game_time.day_index()
    game.player.money = 500
    assert game.transit_hub_system.rent_vehicle(game.player, 'van_rental', 3)['ok']
    _add_road_vehicle(game)
    assert game.player.vehicles
    game._advance_time_with_needs(3 * 1440)
    assert not game.player.vehicles


def test_quick_save_does_not_discard_active_show(career):
    game, _ = career
    game.game_state = 'performance'
    with patch.object(game, 'save_game') as save:
        assert not game.quick_save()
    save.assert_not_called()


def test_real_pygame_menu_input_and_cancel(career):
    import pygame
    from game.pygame_ui import PygameUI
    game, _ = career
    ui = PygameUI(); ui.game = game
    ui.update_display = lambda: None
    before = current_game_time.copy()
    def press(*keys):
        pygame.event.clear()
        for key in keys: pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, unicode=''))
    press(pygame.K_DOWN, pygame.K_RETURN)
    assert ui.present_choices({'buy':'Buy', 'back':'Cancel'}, 'Purchase') == 'back'
    press(pygame.K_ESCAPE)
    assert ui.present_choices({'buy':'Buy', 'back':'Cancel'}, 'Purchase') == 'back'
    press(pygame.K_PAGEDOWN, pygame.K_RETURN)
    assert ui.present_choices({str(i): f'Choice {i}' for i in range(10)}, 'Pages') == '7'
    # Escape in a mandatory choice must not select the highlighted option.
    press(pygame.K_ESCAPE, pygame.K_DOWN, pygame.K_RETURN)
    assert ui.present_choices({'a':'First', 'b':'Second'}, 'Mandatory') == 'b'
    assert current_game_time == before
    pygame.quit()


def test_album_business_and_manufacturing_through_menus(career):
    from game.career_actions import assemble_release, catalog_business
    game, ui = career
    songs = [Song(f'Tide {i}', game.player.name, 'Rock', song_quality=.8) for i in range(3)]
    for song in songs: song.mark_as_recorded(.8)
    game.player.songs_written.extend(songs)
    ui.choices.extend(['2', '0', '1', 'release']); ui.texts.append('Low Water')
    before = game.player.money
    assemble_release(game)
    album = game.album_system.released_albums[0]
    assert album.track_ids == [songs[i].song_id for i in [2, 0, 1]]
    assert game.player.albums_released[0] is album
    assert game.player.money == before - 50 and len(game.streaming_system.catalog) == 3
    assert game.music_press_reviews.review_archive
    game.player.money = 1000
    ui.choices.extend(['press', '0', '100']);catalog_business(game)
    order = game.album_system.pending_vinyl_orders[0]
    assert game.player.money == 400 and not order.delivered
    game._advance_time_with_needs(21 * 1440)
    assert order.delivered and order in game.album_system.delivered_vinyl_batches
    ui.choices.append('reviews');catalog_business(game)
    assert any('Low Water' in message for message in ui.messages)


def test_arriving_for_a_booked_shift_earns_pay(career):
    from game.career_actions import shift_listings
    game, ui = career
    ui.choices.extend(['retail_corner_mart', 'book']);shift_listings(game)
    event = game.player.schedule.scheduled_items[0]
    game.player.current_poi = game.get_poi_or_venue_by_id(event.details['destination_id'])
    current_game_time.__dict__.update(vars(event.start_time))
    before = game.player.money
    game.check_for_scheduled_events()
    assert game.player.money == before + 52
    assert current_game_time == event.end_time
    assert not game.player.schedule.scheduled_items


def test_draft_can_pause_save_and_resume_without_repeating_work(career, tmp_path):
    from game.creative_work import open_notebook
    game, ui = career
    choose_place_action(game, ui, 'write')
    ui.choices.extend(['Rock', 'none', 'yes']); ui.texts.append('Unfinished Business')
    for _ in range(4): game.handle_explore_menu()
    assert not game.player.songs_written
    assert game.song_in_progress['session_index'] == 1
    lyrics = game.song_in_progress['lyrical_depth']
    assert game.player.energy == 90
    ui.choices.append('back'); game.handle_explore_menu()
    path = tmp_path / 'draft.json'
    assert game.save_game(str(path))
    loaded_ui = MenuUI();loaded = Game(loaded_ui)
    assert loaded.load_game(str(path))
    loaded.player.energy = 100
    before = current_game_time.copy()
    open_notebook(loaded)
    loaded_ui.choices.extend(['work', 'work'])
    loaded.handle_explore_menu();loaded.handle_explore_menu()
    assert loaded.player.songs_written[0].title == 'Unfinished Business'
    assert loaded.player.songs_written[0].lyrical_depth == round(lyrics, 2)
    assert current_game_time.days_difference(before) == pytest.approx(6 / 24)
    assert loaded.player.energy == 70
    assert not loaded.song_in_progress


def test_creative_fatigue_changes_recording_quality_and_refuses_exhausted_session(career):
    game, ui = career
    song = Song('Tired Take', game.player.name, 'Rock', song_quality=.7)
    game.player.songs_written.append(song)
    game.player.energy = 100
    rested = game._calculate_recording_quality(song, .6)
    game.player.energy = 20;game.player.stress = 85
    assert game._calculate_recording_quality(song, .6) < rested
    game.player.energy = 5
    choose_place_action(game, ui, 'record a home demo')
    before = current_game_time.copy();cash = game.player.money
    ui.choices.append('0');game.handle_explore_menu()
    assert not song.is_recorded and game.player.money == cash
    assert current_game_time == before


def test_breakdown_on_last_leg_does_not_complete_trip(career):
    from game.travel_manager import TravelManager
    from game.vehicle import Vehicle
    game, _ = career
    car = Vehicle('Test car', 1000, 60, 40, 10, 12)
    tm = TravelManager(game.player, game.player.current_location, 20, 'car', vehicle=car)
    with patch.object(car, 'travel', return_value={'success': False, 'breakdown': True, 'message': 'Engine trouble'}), patch('game.travel_manager.generate_road_event', return_value=(None, 0, 0, 0, False)):
        _, arrived = tm.advance_one_hour()
    assert not arrived and tm.distance_covered == 0


def test_flight_timing_uses_authored_route_hours(career):
    game, ui = career
    city = next(c for c in game.WORLD_MAP.values() if any(r['method'].lower() == 'plane' for r in c.travel_connections.values())
                and any(p.category in ('AIRPORT', 'TRANSPORT_AIRPORT') for p in c.points_of_interest))
    game.player.current_location = city
    game.player.current_poi = next(p for p in city.points_of_interest if p.category in ('AIRPORT', 'TRANSPORT_AIRPORT'))
    destination, route = next((n, r) for n, r in city.travel_connections.items() if r['method'].lower() == 'plane')
    game.player.money = 5000
    ui.choices.extend(['inter_city', destination, 'public', 'economy'])
    game.handle_travel_menu()
    tm = game.travel_manager
    assert tm.distance_total / tm.current_speed == route['time_hours']


def test_fuel_stop_has_a_cost_and_does_not_move_vehicle(career):
    from game.travel_manager import TravelManager
    from game.vehicle import Vehicle
    game, _ = career
    car = Vehicle('Test car', 1000, 60, 40, 10, 12);car.fuel = 10
    tm = TravelManager(game.player, game.player.current_location, 120, 'car', vehicle=car)
    session = game.transit_layer.start_session(tm)
    before = current_game_time.copy();cash = game.player.money
    result = game.transit_layer.execute_chunk(game, tm, session, 'refuel')
    assert not result['arrived'] and tm.distance_covered == 0
    assert car.fuel == 40 and game.player.money == cash - 90
    assert current_game_time.days_difference(before) == pytest.approx(.5 / 24)
