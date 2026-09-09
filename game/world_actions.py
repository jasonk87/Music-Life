"""Bridge authored place actions to executable services and explicit transactions."""
import re
from game.game_time import current_game_time

ALIASES = {
    'Rest / Sleep': 'Rest (8 hours)', 'Practice Guitar': 'Practice guitar (at home)',
    'Write Song': 'Write a new song', 'Write Songs': 'Write a new song',
    'Record a song': 'Book recording session', 'Repair Gear': 'Repair Instrument',
    'Browse used items': 'Browse Pawn Shop', 'Pawn gear for quick cash': 'Pawn Item',
    'Read local paper': "Look for today's paper", 'Read latest music reviews': "Look for today's paper",
    'Check bulletin board': 'Look for Gig Flyers', 'Watch Street Musicians': 'People Watch',
    'Get Haircut ($15)': 'Get a haircut', 'Order Coffee ($2)': 'Order Drip Coffee ($2)',
    'Interview with Brenda Reporter': 'Ask for a journalist',
    'Chat with cashier': 'Talk to Staff', 'Network with Musician': 'Talk to Musicians',
    'Inquire about Superstar Management': 'Inquire about PR representation',
    'Inquire about Label Deals': 'Talk to Talent Agent',
}


def normalize_action(text):
    if text.startswith('Book Studio Time'): return 'Book recording session'
    return ALIASES.get(text, text)


def normalize_places(game):
    for city in game.WORLD_MAP.values():
        for poi in city.points_of_interest:
            if poi.category == 'RECORD_LABEL_HQ': poi.category = 'OFFICE_RECORD_LABEL'
            if poi.category == 'HOME':
                if 'Record a home demo' not in poi.interaction_options: poi.interaction_options.append('Record a home demo')
                poi.rest_quality = max(0.6, poi.rest_quality)
            if poi.menu_items:
                food_texts = [m['display_text'] for m in poi.menu_items]
                poi.interaction_options = [t for t in poi.interaction_options if not (t.startswith('Order ') or t in ('Buy snacks', 'Buy energy drink'))]
                poi.interaction_options = food_texts + poi.interaction_options
            poi.interaction_options = list(dict.fromkeys(normalize_action(t) for t in poi.interaction_options))


def _pay(game, cost, minutes):
    if game.player.money < cost:
        game.GAME_LOG.add_log_message(f'This costs ${cost}. No payment was taken.')
        return False
    game.player.money -= cost
    game._advance_time_with_needs(minutes)
    return True


def _add_road_vehicle(game):
    from game.vehicle import Vehicle
    source = game.player.vehicle
    road = Vehicle(source.name, source.cost, source.speed, source.fuel_capacity,
                   source.km_per_liter, 24 if 'van' in source.model_key else 12, source.reliability)
    road.rental_until = getattr(source, 'rental_until', None)
    game.player.vehicles.append(road)


def dispatch(game, text):
    """True means consumed; False lets an existing canonical handler run."""
    p, poi = game.player, game.selected_poi
    if poi is None: return False
    price_match = re.search(r'\$(\d+)', text)
    cost = int(price_match.group(1)) if price_match else 0
    menu = next((m for m in getattr(poi, 'menu_items', []) if m['display_text'] == text), None)
    if menu or text.startswith(('Drink ', 'Eat ')):
        menu = menu or {'cost': cost, 'hunger_reduction': 40 if text.startswith('Eat ') else 3, 'energy_boost': 12}
        if _pay(game, menu['cost'], 30):
            effects = menu.get('effects', {})
            p.hunger = max(0, p.hunger - menu.get('hunger_reduction', -effects.get('hunger', -25)))
            p.energy = min(100, p.energy + menu.get('energy_boost', effects.get('energy', 5)))
            p.comfort = max(0, min(100, p.comfort + effects.get('comfort', 4)))
            for stat in ('health', 'stress'):
                if stat in effects: setattr(p, stat, max(0, min(100, getattr(p, stat) + effects[stat])))
            game.GAME_LOG.add_log_message(f'{text}. Hunger {p.hunger}/100; energy {p.energy}/100.')
        return True
    if text.startswith('Book Night Rest'):
        if _pay(game, cost, 15):
            checkout=current_game_time.copy();checkout.add_hours(16)
            p.rented_accommodation_info={'poi_id':poi.poi_id,'checkout_time_obj':checkout}
            game.rest(8)
        return True
    if text == 'Sleep in Van ($0)':
        if not p.vehicles: game.GAME_LOG.add_log_message('There is no vehicle to sleep in.')
        else:
            game._advance_time_with_needs(360)
            p.energy=min(100,p.energy+28);p.comfort=max(0,p.comfort-8)
            game.GAME_LOG.add_log_message('Six cramped hours in the vehicle. You wake stiff but rested.')
        return True
    if text.startswith('Get Checkup') or text=='Rest & Recover':
        if _pay(game, cost, 120):
            p.health=min(100,p.health+25);p.stress=max(0,p.stress-12)
            game.GAME_LOG.add_log_message(f'Clinic visit complete. Health {p.health}/100.')
        return True
    if text in ('Book flight','View flight destinations','View bus schedule','Buy bus ticket','View Departures & Buy Tickets') or text.startswith('Buy ticket to '):
        game.game_state='travel'
        return True
    if text == 'Wait in terminal':
        game._advance_time_with_needs(60)
        game.GAME_LOG.add_log_message('An hour passes in the terminal.');return True
    if text in ('Hire Dedicated Driver','Manager Pre-Book Fleet'):
        if text=='Hire Dedicated Driver':
            game.game_state='phone';game.phone_menu_state='staff'
        else:
            result=game.transit_hub_system.manager_prebook_tour_fleet(game)
            if result['ok']:_add_road_vehicle(game)
            game.GAME_LOG.add_log_message(result['explanation'])
        return True
    if text in ('Buy Vehicle','Rent Vehicle'):
        from game.vehicle_system import VehicleMarket
        renting=text=='Rent Vehicle'
        options=({k:f'{v.name} / ${v.daily_rate * 3} for 3 days' for k,v in game.transit_hub_system.RENTALS.items()} if renting else {k:f"{v['name']} / ${v['cost']}" for k,v in VehicleMarket.VEHICLES.items()})
        options['back']='Cancel'
        choice=game.ui.present_choices(options,'Fleet counter')
        if choice=='back':return True
        result=(game.transit_hub_system.rent_vehicle(p,choice,3) if renting else game.transit_hub_system.buy_vehicle(p,choice))
        if result['ok']:
            if renting:p.vehicle.rental_until=current_game_time.day_index()+3
            _add_road_vehicle(game)
            game._advance_time_with_needs(30)
        game.GAME_LOG.add_log_message(result['explanation']);return True
    if text.startswith('Hail Taxi'):
        targets={getattr(t,'poi_id',getattr(t,'venue_id',None)):t for t in p.current_location.points_of_interest+p.current_location.venues if t is not poi}
        options={k:t.name for k,t in targets.items()};options['back']='Cancel'
        chosen=game.ui.present_choices(options,'Taxi / $15')
        if chosen!='back' and _pay(game,15,15):
            p.current_poi=targets[chosen]
            game.GAME_LOG.add_log_message(f'The taxi drops you at {p.current_poi.name}.')
        return True
    if text in ('Sell Vinyl / Merch','Read latest music reviews'):
        game.game_state='music_menu';game.music_menu_state='business';return True
    if text in ('Browse Records','Submit Demo for Airplay','Pitch Song to Publisher'):
        if text=='Browse Records':
            game._advance_time_with_needs(30);p.inspiration=min(100,p.inspiration+5)
            game.GAME_LOG.add_log_message(f'The listening station is playing {game.trend_manager.get_top_genre()}.')
        else:
            from game.career_actions import catalog_business
            catalog_business(game)
        return True
    if text in ('Play Acoustic Open Mic','Jam with Brass Band','Busk for Tips & Street Cred'):
        if not any(not g.is_broken and g.gear_type.startswith('INSTRUMENT') for g in p.gear_inventory):
            game.GAME_LOG.add_log_message('You need a working instrument.');return True
        if p.energy<15:
            game.GAME_LOG.add_log_message('You are too exhausted to play.');return True
        city=p.current_location.name
        report=game.weather_and_seasons.get_city_weather(city)
        outdoor=poi.category=='PUBLIC_PARK'
        modifier=0.5 if outdoor and report.condition in ('BLIZZARD','RAIN_DRIZZLE') else 1.0
        tips=int((p.skills.get('guitar',0)+p.skills.get('vocals',0))*0.7*modifier)
        game._advance_time_with_needs(60)
        p.money+=tips;p.energy=max(0,p.energy-10);p.inspiration=min(100,p.inspiration+4)
        p.street_cred=min(100,p.street_cred+1)
        game.GAME_LOG.add_log_message(f'An hour playing at {poi.name}. You collect ${tips} in tips.');return True
    return False
