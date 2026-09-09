"""Preparation must matter to the actual show, not just the room's UI."""
from unittest.mock import patch
import pygame
import pytest
from test_playable_career import career, MenuUI
from game.game import Game
from game.song import Song
from game.staff import StaffMember
from game.merch_system import MerchItem
from game.game_time import current_game_time
from game.club_life import ClubLife
from game.club_scene import ClubScene, SOLIDS, ANCHORS
from game.shop_scene import find_path, walkable
from game.live_bookings import propose_local_show, commit_tour, settle_show, reconcile_bookings
from game.performance import PerformanceManager


def night(game, booked=False):
    venue = game.player.current_location.venues[0]
    game.player.current_poi = venue
    game.player.songs_written = [Song('Night Bus', game.player.name, 'Rock', song_quality=.7)]
    game.player.money = 500
    game.player.fame = 70
    game.player.energy = 95
    game.player.hunger = 5
    game.player.stress = 5
    if booked:
        game.player.fame = 30  # The authored local desk offers an acoustic open mic at this level.
        result = commit_tour(game, propose_local_show(game, venue.venue_id, 2))
        assert result['ok']
        event = next(e for e in venue.events_hosted if getattr(e,'booking_id',None)==result['booking_id'])
        current_game_time.__dict__.update(vars(event.booking_start))
    current_game_time.hour, current_game_time.minute = 18, 0
    life = ClubLife(game, venue)
    life.plan()['monitor_fault'] = False
    return life


def finish_through_game(game, ui):
    ui.choices.append('0')
    game.handle_performance_scene()
    assert game.performance_manager
    ui.enter_live_club = lambda venue: None
    for _ in range(40):
        if game.performance_stage == 'playing':
            if game.performance_manager.state == 'player_input':
                ui.choices.append('safe' if game.performance_manager.current_section_index%2==0 else 'hype')
            elif game.performance_manager.state == 'summary':
                ui.choices.append('finish')
        game.handle_performance_scene()
        if game.game_state != 'performance': break
    assert game.game_state == 'explore' and not ui.choices


def test_soundcheck_and_fault_repair_spend_real_time_and_money_once(career):
    game, _ = career
    life = night(game)
    p = life.plan();p['monitor_fault'] = True
    assert life.prepare('sound')
    assert current_game_time.hour == 18 and current_game_time.minute == 25
    assert p['monitor_revealed'] and not p['monitor_resolved']
    energy = game.player.energy
    assert not life.prepare('sound')
    assert game.player.energy == energy
    money = game.player.money
    assert life.prepare('monitor')
    assert game.player.money == money-8 and current_game_time.minute == 35
    assert not life.prepare('monitor')


def test_sound_and_people_change_actual_performance_start(career):
    game, _ = career
    life = night(game)
    event = life.event()
    song = game.player.songs_written[0]
    unprepared = PerformanceManager(game,event,song,game.ui)
    life.prepare('sound');life.talk('regular');life.talk('promoter')
    current_game_time.hour,current_game_time.minute = 19,0
    assert life.take_stage()[0]
    prepared = PerformanceManager(game,event,song,game.ui)
    assert prepared.sound_bonus == 7
    assert prepared.crowd_hype > unprepared.crowd_hype


def test_late_start_reduces_attendance_and_opening_response(career):
    game, _ = career
    life = night(game)
    current_game_time.hour = 19
    ontime = life.attendance()
    current_game_time.hour = 20
    assert life.attendance() < ontime
    assert life.take_stage()[0]
    context = game.active_performance.club_performance_context
    assert context['late_minutes'] == 60
    assert context['crowd_bonus'] < 0


def test_missing_stock_and_early_soundcheck_do_not_consume_time(career):
    game, _ = career
    life = night(game)
    now = current_game_time.copy()
    assert not life.prepare('merch')
    assert current_game_time == now
    current_game_time.hour = 12
    assert not life.prepare('sound') and current_game_time.hour == 12


def test_crew_works_concurrently_and_survives_save(career, tmp_path):
    game, _ = career
    life = night(game)
    staff = StaffMember('Jamie','Roadie',100,4)
    game.player.staff.append(staff)
    assert life.assign_crew(staff,'sound')
    life.talk('promoter')
    assert current_game_time.minute == 10 and life.plan()['sound'] == 0
    path = tmp_path/'crew.json';assert game.save_game(str(path))
    fresh = Game(MenuUI());assert fresh.load_game(str(path))
    restored = ClubLife(fresh,fresh.player.current_poi)
    assert restored.plan()['crew_task']['staff'] is fresh.player.staff[0]
    restored.elapse(20)
    assert current_game_time.minute == 30
    assert restored.plan()['sound'] == 8 and restored.plan()['crew_task'] is None


def test_fired_crew_cannot_complete_preparation(career):
    game, _ = career
    life = night(game)
    staff = StaffMember('Jamie','Roadie',100,4)
    game.player.staff.append(staff)
    life.assign_crew(staff,'sound')
    game.player.staff.remove(staff)
    life.elapse(30)
    assert life.plan()['sound'] == 0 and not life.plan()['crew_task']


def test_crew_and_player_cannot_duplicate_the_same_task(career):
    game, _ = career
    life = night(game)
    staff = StaffMember('Jamie','Roadie',100,4)
    game.player.staff.append(staff)
    assert life.assign_crew(staff,'sound')
    assert not life.assign_crew(staff,'merch')
    now = current_game_time.copy()
    assert not life.prepare('sound') and current_game_time == now


def test_doors_open_and_pause_the_room_clock(career):
    game, _ = career
    life = night(game)
    current_game_time.minute = 25
    scene = ClubScene(game,life.poi)
    scene.set_speed(12);scene.update(1)
    assert current_game_time.minute == 30
    assert scene.speed == 0
    assert life.attendance() == 0
    scene.set_speed(12);scene.update(1)
    assert life.attendance() > 0


def test_booked_show_waits_for_stage_action_in_spatial_ui(career):
    game, ui = career
    life = night(game,booked=True)
    ui.enter_live_club = lambda venue: None
    current_game_time.hour = 19
    game.check_for_scheduled_events()
    assert game.active_performance is None
    assert any(item.category=='Gig' for item in game.player.schedule.scheduled_items)
    assert life.take_stage()[0]
    assert game.game_state == 'performance'
    assert not any(item.details.get('event_id')==game.active_performance.event_id for item in game.player.schedule.scheduled_items)


def test_full_booked_night_preparation_show_merch_and_settlement(career):
    game, ui = career
    life = night(game,booked=True)
    event = life.event()
    game.player.merch_stock = [MerchItem('shirts','Shirts','tshirt',40,20,10)]
    assert life.prepare('sound') and life.prepare('merch')
    life.talk('regular')
    current_game_time.hour,current_game_time.minute = 19,0
    assert life.take_stage()[0]
    finish_through_game(game,ui)
    result = life.data['last_result']
    assert result['status'] == 'played'
    assert result['paid'] >= event.guaranteed_payout
    assert result['merch_ready'] and game.player.merch_stock[0].unit_count < 10
    assert len(life.data['history']) == 1
    money = game.player.money
    settle_show(game,event,'played',result['paid'])
    assert len(life.data['history']) == 1 and game.player.money == money
    assert game.world_memory.query(event_type='club_night')


def test_unprepared_table_does_not_sell_automatically(career):
    game, ui = career
    life = night(game)
    game.player.merch_stock = [MerchItem('shirts','Shirts','tshirt',40,20,10)]
    current_game_time.hour = 19
    assert life.take_stage()[0]
    finish_through_game(game,ui)
    assert game.player.merch_stock[0].unit_count == 10
    assert life.data['last_result']['status']=='played'


def test_new_night_does_not_reuse_old_preparation(career):
    game, _ = career
    life = night(game)
    life.prepare('sound')
    current_game_time.add_days(1)
    assert life.plan()['sound'] == 0


@pytest.mark.parametrize('key', list(ANCHORS))
def test_club_stations_are_reachable(key):
    path=find_path((696,522),ANCHORS[key],SOLIDS)
    assert path,key
    assert all(walkable(point,SOLIDS) for point in path)


def test_stage_handoff_survives_explore_return(career):
    game, ui = career
    life=night(game)
    current_game_time.hour=19
    game.game_state='explore';game.explore_menu_state='poi';game.selected_poi=life.poi
    ui.enter_live_club=lambda venue: life.take_stage()
    game.handle_explore_menu()
    assert game.game_state=='performance' and game.active_performance


def test_mouse_can_approach_console(career):
    game, _=career
    life=night(game)
    scene=ClubScene(game,life.poi)
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=SOLIDS[4].center))
    for _ in range(100):scene.update(.1)
    assert scene.dialog['title']==scene.targets()['engineer']['name']


def test_crowd_only_arrives_after_doors(career):
    game, _ = career
    life = night(game)
    assert life.attendance() == 0
    current_game_time.minute = 45
    halfway = life.attendance()
    current_game_time.hour, current_game_time.minute = 19, 0
    assert 0 < halfway < life.attendance()


def test_late_preparation_remains_possible_within_window(career):
    game, _ = career
    life = night(game)
    current_game_time.hour = 21
    assert life.prepare('sound')


def test_withdrawn_public_slot_closes_once(career):
    game, ui = career
    life = night(game)
    current_game_time.hour = 19
    assert life.take_stage()[0]
    event = life.event()
    ui.choices.append('back')
    game.handle_performance_scene()
    assert game.game_state == 'explore'
    assert life.data['last_result']['status'] == 'cancelled'
    assert not life.take_stage()[0]
    settle_show(game,event,'cancelled')
    assert len(life.data['history']) == 1


def test_prepared_missed_booking_retains_history_and_closes_slot(career):
    game, _ = career
    life = night(game,booked=True)
    event = life.event()
    life.prepare('sound')
    current_game_time.__dict__.update(vars(event.booking_end))
    current_game_time.advance_time(1)
    reconcile_bookings(game)
    assert life.data['last_result']['status'] == 'missed'
    assert life.event() is event
    assert not life.prepare('sound') and not life.take_stage()[0]
    assert life.data['last_result']['sound'] == 7
    reconcile_bookings(game)
    assert len(life.data['history']) == 1


def test_completed_booking_stays_in_room_after_set(career):
    game, ui = career
    life = night(game,booked=True)
    event = life.event()
    life.prepare('sound')
    current_game_time.hour, current_game_time.minute = 19, 0
    assert life.take_stage()[0]
    finish_through_game(game,ui)
    assert life.event() is event and life.plan()['sound'] == 7
    assert not life.take_stage()[0]
    current_game_time.add_days(1)
    assert life.event() is not event and life.plan()['sound'] == 0
