"""The spatial shop shares the career clock, people, inventory and save graph."""
from unittest.mock import patch
import pygame
import pytest
from test_playable_career import career, MenuUI
from game.game import Game
from game.game_time import current_game_time
from game.shop_life import ShopLife
from game.shop_scene import ShopScene, ANCHORS, SOLIDS, find_path, walkable
from game.merch_system import MerchItem
from game.song import Song
from game_data.gear_catalog import GEAR_CATALOG


def visit(game):
    poi = next(p for p in game.player.current_location.points_of_interest if p.category == 'SHOP_MUSIC')
    game.player.current_poi = poi
    game.player.energy = 95
    game.player.hunger = 5
    game.player.stress = 5
    game.player.fame = 300
    game.player.active_opportunities['autograph_signing'] = {'status': 'available', 'poi_id': poi.poi_id}
    return ShopLife(game, poi)


def complete(life, attention='listen', pace='brisk', closing='extend'):
    while life.active:
        life.elapse(120, interruptible=True)
        if life.active:
            choices = {'fan': attention, 'queue': pace, 'closing': closing}
            assert life.active['pending'] in choices
            life.decide(choices[life.active['pending']])


def test_regulars_recur_and_cannot_be_farmed_by_reentering(career):
    game, _ = career
    life = visit(game)
    life.enter()
    npc = life.visitors()[0]
    before = current_game_time.copy()
    assert life.talk(npc.npc_id, 'listen')
    assert npc.relationship_score == 4
    fresh = ShopLife(game, life.poi)
    fresh.enter()
    assert fresh.visitors()[0] is npc
    assert not fresh.talk(npc.npc_id, 'listen')
    assert round(current_game_time.days_difference(before)*1440) == 10
    assert len(life.data['visited_days']) == 1
    current_game_time.add_days(1)
    assert fresh.talk(npc.npc_id)
    assert npc.relationship_score == 6
    assert 'remembers' in fresh.greeting(npc)


def test_each_shop_has_its_own_regulars(career):
    game, _ = career
    first = visit(game)
    second_poi = next(poi for city in game.WORLD_MAP.values() for poi in city.points_of_interest
                      if poi.category == 'SHOP_MUSIC' and poi is not first.poi)
    game.player.current_poi = second_poi
    second = ShopLife(game, second_poi)
    assert set(first.data['regular_ids']).isdisjoint(second.data['regular_ids'])


def test_presence_is_required(career):
    game, _ = career
    shop = next(p for p in game.player.current_location.points_of_interest if p.category == 'SHOP_MUSIC')
    with pytest.raises(ValueError): ShopLife(game, shop)


def test_signing_runs_to_decisions_without_per_signature_input(career):
    game, _ = career
    life = visit(game)
    before = current_game_time.copy()
    assert life.start_signing('brisk')
    assert life.elapse(120, interruptible=True) == 20
    assert life.active['pending'] == 'fan'
    assert life.active['met'] > 1
    assert round(current_game_time.days_difference(before)*1440) == 20
    assert life.elapse(30, interruptible=True) == 0
    life.decide('brief')
    assert life.elapse(120, interruptible=True) == 40
    assert life.active['pending'] == 'queue'


def test_stepping_away_stops_service_but_not_walkouts(career):
    game, _ = career
    life = visit(game)
    life.start_signing('personal')
    life.elapse(20, interruptible=True)
    life.decide('brief')
    met = life.active['met']
    life.elapse(40, at_table=False, interruptible=True)
    assert life.active['met'] == met
    assert life.active['left'] > 0
    assert life.active['away_minutes'] == 40


def test_signing_changes_named_relationships_and_shared_history(career):
    game, _ = career
    life = visit(game)
    npc = life.visitors()[0]
    life.start_signing('personal')
    complete(life)
    result = life.data['last_result']
    assert npc.relationship_score >= 3
    assert any('demo' in m for m in npc.memories)
    assert game.player.appearance_history[-1] == result
    assert result['met'] + result['left'] == result['turnout']
    assert not life.active
    assert game.world_memory.query(event_type='public_appearance')
    assert 'Last time' in life.greeting(life.host)


def test_early_closure_changes_host_and_repeat_invitation(career):
    game, _ = career
    life = visit(game)
    life.start_signing('personal')
    life.finish()
    assert life.data['reputation'] < 0
    assert not life.start_signing('brisk')
    money = game.player.money
    assert life.finish() is None
    assert game.player.money == money
    assert len(game.player.appearance_history) == 1


def test_merchandise_sales_are_stock_limited(career):
    game, _ = career
    life = visit(game)
    game.player.merch_stock = [MerchItem('shirts', 'Shirts', 'tshirt', 30, 20, 3)]
    money = game.player.money
    life.start_signing('merch')
    complete(life)
    result = life.data['last_result']
    assert result['units_sold'] == 3 and result['revenue'] == 60
    assert game.player.money == money + 60
    assert game.player.merch_stock[0].unit_count == 0


def test_save_mid_signing_resumes_same_queue_and_npcs(career, tmp_path):
    game, _ = career
    life = visit(game)
    life.start_signing('brisk')
    life.elapse(20, interruptible=True)
    saved_queue = list(life.active['queue'])
    path = tmp_path/'shop.json'
    game.game_state = 'shop_scene'
    from game.save_manager import JSONSaveManager
    with patch.object(Game, 'save_game', lambda self: JSONSaveManager.save_game(self, str(path))):
        assert game.quick_save()
    fresh = Game(MenuUI())
    assert fresh.load_game(str(path))
    assert fresh.game_state == 'explore'
    restored = ShopLife(fresh, fresh.player.current_poi)
    assert restored.active['queue'] == saved_queue
    assert restored.active['pending'] == 'fan'
    assert restored.visitors()[0] is fresh.NPC_REGISTRY[restored.data['regular_ids'][0]]
    assert restored.visitors()[0].home_location is fresh.player.current_poi
    restored.decide('brief')
    complete(restored)
    assert len(fresh.player.appearance_history) == 1


def test_known_fans_increase_next_turnout(career):
    game, _ = career
    life = visit(game)
    life.start_signing('brisk')
    first = life.active['turnout']
    life.data['active'] = None
    for npc in life.visitors(): npc.update_relationship(20)
    life.start_signing('brisk')
    assert life.active['turnout'] > first


def test_released_artist_can_ask_host_without_an_active_tour(career):
    game, _ = career
    life = visit(game)
    game.player.active_opportunities.clear()
    assert not life.invitation()[0]
    song = Song('Basement Tape', game.player.name, 'Rock')
    song.is_released = True
    game.player.songs_written.append(song)
    assert life.invitation()[0]
    assert life.start_signing('personal')


def test_purchase_checks_capacity_and_copies_catalog(career):
    game, _ = career
    life = visit(game)
    item_id = life.poi.shop_inventory_item_ids[0]
    game.player.money = 1000
    before = current_game_time.copy()
    with patch.object(game.player, 'can_carry_gear', return_value=False):
        assert not life.buy(item_id)
    assert game.player.money == 1000 and current_game_time == before
    assert life.buy(item_id)
    assert game.player.gear_inventory[-1] is not GEAR_CATALOG[item_id]
    assert round(current_game_time.days_difference(before)*1440) == 5


@pytest.mark.parametrize('key', list(ANCHORS))
def test_every_station_is_reachable_around_furniture(key):
    path = find_path((696, 522), ANCHORS[key])
    assert path, key
    assert all(walkable(p) for p in path)
    assert all(not any(r.collidepoint(p) for r in SOLIDS) for p in path)


def test_room_mouse_and_keyboard_approach_and_pause(career):
    game, _ = career
    life = visit(game)
    scene = ShopScene(game, life.poi)
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=ANCHORS['host']))
    assert scene.path
    for _ in range(100): scene.update(.1)
    assert scene.dialog['title'] == life.host.name
    assert scene.speed == 0
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert scene.dialog is None
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2))
    assert scene.speed == 4
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    assert scene.speed == 0


def test_room_pause_is_free_and_speed_drives_actual_activity(career):
    game, _ = career
    life = visit(game)
    scene = ShopScene(game, life.poi)
    scene.begin('brisk')
    scene.set_speed(0)
    before = current_game_time.copy()
    scene.update(30)
    assert current_game_time == before and life.active['minutes'] == 0
    scene.set_speed(12)
    scene.update(1)
    assert life.active['minutes'] == 12
    scene.update(1)
    assert life.active['minutes'] == 20
    assert scene.dialog and scene.speed == 0


def test_explore_routes_shop_into_spatial_ui(career):
    game, ui = career
    life = visit(game)
    game.game_state = 'explore'
    game.explore_menu_state = 'poi'
    game.selected_poi = life.poi
    seen = []
    ui.enter_music_shop = lambda poi: seen.append(poi)
    game.handle_explore_menu()
    assert seen == [life.poi]
    assert game.game_state == 'main_menu' and not ui.choices


def test_clicking_furniture_approaches_its_service(career):
    game, _ = career
    life = visit(game)
    scene = ShopScene(game, life.poi)
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=SOLIDS[1].center))
    assert scene.destination_action == 'records'
    for _ in range(80): scene.update(.1)
    assert scene.dialog['title'] == 'Under the counter'


def test_scene_clock_pauses_at_commitment_without_teleporting(career):
    game, _ = career
    life = visit(game)
    start = current_game_time.copy(); start.advance_time(7)
    end = start.copy(); end.advance_time(30)
    game.player.schedule.add_event(start, end, 'Press call', 'Interview')
    scene = ShopScene(game, life.poi)
    scene.set_speed(12)
    scene.update(1)
    assert current_game_time == start
    assert scene.speed == 0 and 'Press call' in scene.notice
    assert game.player.current_poi is life.poi


def test_mid_scene_f5_records_exact_position_without_serializing_ui(career, tmp_path):
    game, _ = career
    life = visit(game)
    scene = ShopScene(game, life.poi)
    scene.begin('personal')
    scene.position.update(485, 466)
    game.game_state = 'shop_scene'
    path = tmp_path/'position.json'
    from game.save_manager import JSONSaveManager
    with patch.object(Game, 'save_game', lambda self: JSONSaveManager.save_game(self, str(path))):
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F5))
    assert scene.speed == 0
    fresh = Game(MenuUI()); assert fresh.load_game(str(path))
    restored = ShopScene(fresh, fresh.player.current_poi)
    assert restored.position == pygame.Vector2(485,466)
    assert restored.life.active['minutes'] == 0
