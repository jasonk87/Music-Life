"""Reviewable live bookings, persistent itineraries, and show settlement."""
import heapq
from copy import deepcopy
import random
import uuid
from types import SimpleNamespace

from game.event import Event
from game.game_time import current_game_time


def cheapest_route(game, origin, destination):
    """A fare estimate for known connections, not an automatic travel action."""
    queue = [(0, 0, origin, [])]
    seen = set()
    while queue:
        cost, hours, city, path = heapq.heappop(queue)
        if city == destination: return {'cost': cost, 'hours': hours, 'legs': path}
        if city in seen: continue
        seen.add(city)
        location = game.WORLD_MAP.get(city)
        if location is None: continue
        for target, route in location.travel_connections.items():
            if target in seen or target not in game.WORLD_MAP: continue
            leg = f"{city} → {target} ({route.get('method', 'bus')})"
            heapq.heappush(queue, (cost + route['cost'], hours + route['time_hours'], target, path + [leg]))
    return None


def propose_tour(game, template_id):
    template = next((t for t in game.TOURS if t['tour_id'] == template_id), None)
    if not template: return {'ok': False, 'explanation': 'That itinerary is unavailable.'}
    if game.player.current_tour_id: return {'ok': False, 'explanation': 'An itinerary is already active.'}
    if game.player.fame < template.get('min_fame', 0):
        return {'ok': False, 'explanation': 'The booking desks are not offering you these rooms yet.'}
    rng = random.Random(f'{template_id}:{current_game_time.day_index()}:{game.player.name}')
    legs = []
    previous_city = getattr(game.player.current_location, 'name', '')
    previous_date = current_game_time.copy()
    for i, spec in enumerate(template['gig_templates']):
        candidates = [(name, v) for name in spec['city_options'] if name in game.WORLD_MAP
                      for v in game.WORLD_MAP[name].venues if v.venue_type in spec['venue_type_options']]
        rng.shuffle(candidates)
        selection = None
        for city, venue in candidates:
            route = cheapest_route(game, previous_city, city)
            if route is not None:
                selection = city, venue, route
                break
        if selection is None:
            return {'ok': False, 'explanation': f'No reachable room is available for date {i + 1}. Nothing was booked.'}
        city, venue, route = selection
        start = previous_date.copy()
        start.add_days(rng.randint(spec['days_offset_min'], spec['days_offset_max']))
        start.hour, start.minute = 19, 0
        if start.days_difference(previous_date) * 24 < route['hours'] + 4:
            return {'ok': False, 'explanation': 'This routing leaves insufficient travel time. Nothing was booked.'}
        end = start.copy();end.add_hours(3)
        legs.append({'city': city, 'venue_id': venue.venue_id, 'venue_name': venue.name,
                     'start': start, 'end': end, 'event_type': spec['event_type'],
                     'skills': dict(spec.get('required_skills_override', {})),
                     'guarantee': int(spec['base_payout_estimate']), 'route': route})
        previous_city, previous_date = city, end
    days = max(0, legs[-1]['end'].day_index() - current_game_time.day_index())
    elapsed = getattr(game.player, 'early_life_days_elapsed', 0)
    rent_weeks = (elapsed + days) // 7 - elapsed // 7
    tier = game.early_life.LODGING.get(getattr(game.player, 'lodging_tier', 'shared_room'))
    living_estimate = days * 7 + rent_weeks * (tier.weekly_cost if tier else 105)
    return {'ok': True, 'template_id': template_id, 'name': template['name'], 'legs': legs,
            'living_estimate': living_estimate, 'days': days,
            'quoted_day': current_game_time.day_index(), 'fee': 5 * len(legs), 'fare_estimate': sum(leg['route']['cost'] for leg in legs)}


def commit_tour(game, proposal):
    """Validate the entire proposal before changing a venue, calendar, or wallet."""
    p = game.player
    if not proposal.get('ok') or not proposal.get('legs'):
        return {'ok': False, 'explanation': proposal.get('explanation', 'No dates in this itinerary.')}
    if p.current_tour_id and proposal.get('kind', 'tour') == 'tour':
        return {'ok': False, 'explanation': 'A tour is already active.'}
    if proposal.get('quoted_day', current_game_time.day_index()) != current_game_time.day_index():
        return {'ok': False, 'explanation': 'This quote has expired. Review a fresh itinerary.'}
    if p.money < proposal['fee']: return {'ok': False, 'explanation': f"The booking fee is ${proposal['fee']}. Nothing was booked."}
    prepared = []
    for leg in proposal['legs']:
        venue = game.get_poi_or_venue_by_id(leg['venue_id'])
        if venue not in getattr(game.WORLD_MAP.get(leg['city']), 'venues', []) or leg['start'] <= current_game_time:
            return {'ok': False, 'explanation': 'A room or date is no longer available. Nothing was booked.'}
        if any(item.start_time < leg['end'] and item.end_time > leg['start'] for item in p.schedule.scheduled_items):
            return {'ok': False, 'explanation': f"{leg['venue_name']} conflicts with your calendar. Nothing was booked."}
        if any(old['start'] < leg['end'] and old['end'] > leg['start'] for old, _ in prepared):
            return {'ok': False, 'explanation': 'The proposed dates overlap. Nothing was booked.'}
        prepared.append((leg, venue))
    itinerary_id = 'live_' + uuid.uuid4().hex[:12]
    ledger = {'name': proposal['name'], 'template_id': proposal['template_id'], 'status': 'ongoing',
              'kind': proposal.get('kind', 'tour'),
              'expenses': proposal['fee'], 'income': 0, 'booking_fee': proposal['fee'],
              'cash_at_booking': p.money, 'started': current_game_time.copy(),
              'fare_estimate': proposal['fare_estimate'], 'living_estimate': proposal.get('living_estimate', 0), 'completed_gigs': [], 'legs': []}
    # All operations below operate on already validated local objects.
    for leg, venue in prepared:
        event = Event(f"{proposal['name']} @ {venue.name}", venue, leg['event_type'],
                      required_skills=dict(leg['skills']),
                      required_gear_types=Event.EVENT_TYPES.get(leg['event_type'], {}).get('default_gear', []),
                      specific_payout=leg['guarantee'], is_tour_gig=proposal.get('kind', 'tour') == 'tour')
        event.booking_id = itinerary_id
        event.booking_start, event.booking_end = leg['start'].copy(), leg['end'].copy()
        event.guaranteed_payout = leg['guarantee']
        venue.add_event(event)
        p.schedule.add_event(leg['start'], leg['end'], event.name, 'Gig' if proposal.get('kind') == 'single' else 'Gig (Tour)',
                            {'event_id': event.event_id, 'venue_id': venue.venue_id,
                             'destination_id': venue.venue_id, 'requires_presence': True, 'booking_id': itinerary_id})
        ledger['legs'].append({**leg, 'event_id': event.event_id, 'status': 'booked', 'paid': 0})
    p.tour_ledgers[itinerary_id] = ledger
    if proposal.get('kind', 'tour') == 'tour': p.current_tour_id = itinerary_id
    p.money -= proposal['fee']
    game.GAME_LOG.add_log_message(f"Booked {len(prepared)} dates for {proposal['name']}. ${proposal['fee']} booking fee paid.")
    return {'ok': True, 'booking_id': itinerary_id, 'explanation': 'All dates are on your calendar. Travel and living costs are paid separately.'}


def settle_show(game, event, status, paid=0, reason=''):
    if event is None: return
    from game.club_life import record_club_show
    record_club_show(game, event, status, paid)
    for item in getattr(event, 'stage_loans', []):
        if item in game.player.gear_inventory: game.player.gear_inventory.remove(item)
    event.stage_loans = []
    booking_id = getattr(event, 'booking_id', None)
    if not booking_id: return
    ledger = game.player.tour_ledgers.get(booking_id)
    if not ledger: return
    leg = next((x for x in ledger['legs'] if x['event_id'] == event.event_id), None)
    if not leg or leg['status'] != 'booked': return
    leg.update(status=status, paid=paid, reason=reason, settled=current_game_time.copy())
    ledger['income'] += paid
    if status in ('played', 'cancelled'):
        game.player.schedule.scheduled_items = [item for item in game.player.schedule.scheduled_items
                                               if item.details.get('event_id') != event.event_id]
    event.is_active = False
    if status == 'played': ledger['completed_gigs'].append(event.event_id)
    else:
        game.player.fame = max(0, game.player.fame - 2)
        game.player.stress = min(100, game.player.stress + 4)
    if all(x['status'] != 'booked' for x in ledger['legs']):
        ledger['status'] = 'completed' if all(x['status'] == 'played' for x in ledger['legs']) else 'closed_with_missed_dates'
        ledger['cash_at_close'] = game.player.money
        ledger['closed'] = current_game_time.copy()
        if game.player.current_tour_id == booking_id: game.player.current_tour_id = None
        if ledger['status'] == 'completed' and ledger.get('kind', 'tour') == 'tour' and ledger['template_id'] not in game.player.completed_tour_ids:
            game.player.completed_tour_ids.append(ledger['template_id'])
        game.GAME_LOG.add_log_message(f"{ledger['name']} closed: {len(ledger['completed_gigs'])}/{len(ledger['legs'])} shows played, ${ledger['income']} in show receipts.")


def cancel_remaining(game, booking_id):
    ledger = game.player.tour_ledgers.get(booking_id)
    if not ledger or ledger['status'] != 'ongoing': return
    for leg in ledger['legs']:
        if leg['status'] != 'booked': continue
        event = game._find_scheduled_event(leg['event_id'], leg['venue_id']) or SimpleNamespace(booking_id=booking_id, event_id=leg['event_id'])
        settle_show(game, event, 'cancelled', reason='Artist cancelled')
    game.player.schedule.scheduled_items = [e for e in game.player.schedule.scheduled_items
                                           if e.details.get('booking_id') != booking_id]
    ledger['status'] = 'cancelled'
    if game.player.current_tour_id == booking_id: game.player.current_tour_id = None
    game.GAME_LOG.add_log_message('Remaining dates cancelled. The booking fee is not refunded; promoters remember the cancellations.')


def itinerary_text(proposal):
    lines = [proposal['name'], f"Booking fee: ${proposal['fee']} (nonrefundable)",
             f"Total show guarantees: ${sum(x['guarantee'] for x in proposal['legs'])}",
             f"Lowest known public fares: ${proposal['fare_estimate']} before return travel.",
             f"Baseline groceries and current lodging through the last date: about ${proposal.get('living_estimate', 0)}.",
             'This baseline is already part of living costs, not an extra booking charge. Crew, extra meals and away lodging are additional.', 
             'Guarantees are paid for completed sets. Travel, food, lodging and crew are separate costs.',
             'Quote valid today. Cancellation forfeits fees and costs 2 fame and 4 stress per unplayed date.', '']
    for i, leg in enumerate(proposal['legs'], 1):
        count = Event.EVENT_TYPES.get(leg['event_type'], {}).get('songs_required', 1)
        gear = ', '.join(name.replace('INSTRUMENT_', '').replace('_', ' ').title() for name in Event.EVENT_TYPES.get(leg['event_type'], {}).get('default_gear', []))
        multiplier = Event.EVENT_TYPES.get(leg['event_type'], {}).get('skill_multiplier', 1)
        skills = ', '.join(f'{name.replace("_", " ").title()} {max(1, int(value * multiplier))}' for name, value in leg['skills'].items())
        lines.extend([f"{i}. {leg['start'].get_time_string_for_schedule()} / {leg['city']}",
                      f"{leg['venue_name']} / ${leg['guarantee']} guarantee / {count} songs",
                      f"Gear: {gear or 'None specified'}; skills: {skills or 'No minimum specified'}",
                      f"Travel estimate: ${leg['route']['cost']} / {leg['route']['hours']} hours",
                      *leg['route']['legs'], ''])
    return '\n'.join(lines)


def booking_desk(game):
    from game.career_actions import report
    reconcile_bookings(game)
    p = game.player
    options = {'local': 'Book a local show', 'offers': 'Browse tour itineraries', 'ledger': 'Itineraries & settlements', 'back': 'Back to phone'}
    if any(value['status'] == 'ongoing' for value in p.tour_ledgers.values()): options['cancel'] = 'Cancel a booking'
    choice = game.ui.present_choices(options, 'Live bookings', context={
        'subtitle': 'Dates, guarantees and obligations. You arrange the travel.',
        'details': [f'Cash available: ${p.money:.0f}', 'Booking a date reserves a performance window; it does not move you there.']})
    if choice == 'local':
        local_show_desk(game)
    elif choice == 'offers':
        if p.current_tour_id:
            game.GAME_LOG.add_log_message('An itinerary is already active.');return
        eligible = [t for t in game.TOURS if t.get('min_fame', 0) <= p.fame]
        opts = {t['tour_id']: f"{t['name']} / {len(t['gig_templates'])} dates" for t in eligible};opts['back'] = 'Back'
        selected = game.ui.present_choices(opts, 'Booking offers')
        if selected == 'back': return
        proposal = propose_tour(game, selected)
        if not proposal['ok']: game.GAME_LOG.add_log_message(proposal['explanation']);return
        selected = review_proposal(game, proposal)
        if selected == 'book':
            result = commit_tour(game, proposal);game.GAME_LOG.add_log_message(result['explanation'])
    elif choice == 'ledger':
        opts = {key: f"{value['name']} / {value['status'].replace('_', ' ')}" for key, value in p.tour_ledgers.items()};opts['back'] = 'Back'
        selected = game.ui.present_choices(opts, 'Live ledger')
        if selected == 'back': return
        ledger = p.tour_ledgers[selected]
        lines = [ledger['name'], f"Status: {ledger['status'].replace('_', ' ').capitalize()}", f"Show receipts: ${ledger['income']}",
                 f"Booking fee paid: ${ledger.get('booking_fee', 0)}",
                 f"Stage equipment rental: ${ledger.get('equipment_expenses', 0)}",
                 'Show receipts exclude streaming, merch and other income. Fares and living costs are paid from your cash.']
        if 'cash_at_booking' in ledger:
            close = ledger.get('cash_at_close', p.money)
            lines += [f"Cash at booking: ${ledger['cash_at_booking']:.2f}", f"{'Cash at settlement' if 'cash_at_close' in ledger else 'Current cash'}: ${close:.2f}",
                      f"Cash change during these dates (all activity): ${close - ledger['cash_at_booking']:.2f}"]
        for leg in ledger.get('legs', []):
            lines += ['', f"{leg['start'].get_time_string_for_schedule()} / {leg['city']} / {leg['venue_name']}",
                      f"{leg['status'].capitalize()} / ${leg['paid']} received" + (f" / {leg['reason']}" if leg.get('reason') else '')]
        report(game, 'Live settlement', '\n'.join(lines))
    elif choice == 'cancel':
        active = {key: value['name'] for key, value in p.tour_ledgers.items() if value['status'] == 'ongoing'}
        active['back'] = 'Back'
        booking_id = game.ui.present_choices(active, 'Which booking?')
        if booking_id == 'back': return
        selected = game.ui.present_choices({'cancel': 'Cancel remaining dates', 'back': 'Keep bookings'},
            'Cancel itinerary?', context={'subtitle': 'No fee refund. Each cancellation costs 2 fame and adds 4 stress.'})
        if selected == 'cancel': cancel_remaining(game, booking_id)


def reconcile_bookings(game):
    """Close elapsed dates and recover the unfinished itinerary shape in older saves."""
    p = game.player
    resolved_ids = set()
    for booking_id, ledger in p.tour_ledgers.items():
        if ledger.get('status') != 'ongoing': continue
        if 'legs' not in ledger:
            ledger.update(legs=[], template_id=booking_id, booking_fee=0,
                          cash_at_booking=p.money, completed_gigs=ledger.get('completed_gigs', []))
            for item in p.schedule.scheduled_items:
                if item.category != 'Gig (Tour)': continue
                event = game._find_scheduled_event(item.details.get('event_id'), item.details.get('venue_id'))
                if not event: continue
                event.booking_id = booking_id
                event.booking_start, event.booking_end = item.start_time.copy(), item.end_time.copy()
                item.details['booking_id'] = booking_id
                venue = event.location
                city = next((city.name for city in game.WORLD_MAP.values() if venue in city.venues), 'Unknown')
                ledger['legs'].append({'event_id': event.event_id, 'venue_id': venue.venue_id,
                                      'venue_name': venue.name, 'city': city, 'start': item.start_time.copy(),
                                      'end': item.end_time.copy(), 'status': 'booked', 'paid': 0})
            if not ledger['legs']:
                ledger['status'] = 'legacy_closed'
                ledger['cash_at_close'] = p.money
                if p.current_tour_id == booking_id: p.current_tour_id = None
                continue
        for leg in ledger['legs']:
            if leg['status'] != 'booked':
                resolved_ids.add(leg['event_id']);continue
            event = game._find_scheduled_event(leg['event_id'], leg['venue_id'])
            if current_game_time > leg['end'] and (event is None or game.active_performance is not event):
                event = event or SimpleNamespace(booking_id=booking_id, event_id=leg['event_id'])
                settle_show(game, event, 'missed', reason='Performance window elapsed')
                resolved_ids.add(leg['event_id'])
    p.schedule.scheduled_items = [item for item in p.schedule.scheduled_items
                                 if item.details.get('event_id') not in resolved_ids]
    if p.current_tour_id and p.tour_ledgers.get(p.current_tour_id, {}).get('status') != 'ongoing':
        p.current_tour_id = None


def prepare_stage(game):
    """Venue gear is a paid, temporary loan, never free equipment for the career."""
    event, p = game.active_performance, game.player
    okay, reason, rental_needed = event._check_gear_requirements(p)
    if not okay:
        game.GAME_LOG.add_log_message(reason);return False
    if not rental_needed: return True
    venue = event.location
    fee = max(0, venue.gear_rental_fee)
    if p.money < fee:
        game.GAME_LOG.add_log_message(f'Venue equipment costs ${fee}; you cannot cover the rental.');return False
    from game_data.gear_catalog import GEAR_CATALOG
    owned = {item.gear_type for item in p.gear_inventory if not item.is_broken}
    loans = []
    for gear_type in event.required_gear_types:
        if gear_type in owned: continue
        template = next((GEAR_CATALOG[key] for key in venue.available_rental_gear_ids
                         if key in GEAR_CATALOG and GEAR_CATALOG[key].gear_type == gear_type), None)
        if template is None: return False
        loans.append(deepcopy(template));owned.add(gear_type)
    choice = game.ui.present_choices({'rent': f'Rent venue equipment / ${fee}', 'back': 'Withdraw from the set'},
        'Stage equipment', context={'subtitle': 'Equipment stays at the venue after the show.',
                                    'details': [item.name for item in loans]})
    if choice != 'rent': return False
    p.money -= fee
    p.gear_inventory.extend(loans)
    event.stage_loans = loans
    ledger = p.tour_ledgers.get(getattr(event, 'booking_id', None))
    if ledger:
        ledger['expenses'] += fee
        ledger['equipment_expenses'] = ledger.get('equipment_expenses', 0) + fee
    game.GAME_LOG.add_log_message(f'Paid ${fee} for venue equipment. It will be returned after the set.')
    return True


def review_proposal(game, proposal):
    from game.career_actions import report
    options = {f'leg_{i}': f"{leg['start'].month:02d}/{leg['start'].day:02d} 19:00 / {leg['city']} / ${leg['guarantee']}"
               for i, leg in enumerate(proposal['legs'])}
    options['book'] = f"Book all {len(proposal['legs'])} dates / ${proposal['fee']} fee"
    options['back'] = 'Decline itinerary'
    descriptions = {f'leg_{i}': f"{leg['venue_name']}. {Event.EVENT_TYPES[leg['event_type']]['songs_required']} songs. Open for room, equipment and route details."
                    for i, leg in enumerate(proposal['legs'])}
    descriptions['book'] = f"Guarantees ${sum(leg['guarantee'] for leg in proposal['legs'])}. Fares from ${proposal['fare_estimate']}. Baseline living costs ~${proposal.get('living_estimate', 0)}. Return travel, crew and away lodging are extra."
    descriptions['back'] = 'No bookings or charges. This quote stays valid today.'
    while True:
        selected = game.ui.present_choices(options, proposal['name'], context={
            'eyebrow': f"Live itinerary / {current_game_time.year}",
            'subtitle': f"{len(proposal['legs'])} dates / ${proposal['fee']} nonrefundable booking fee",
            'details': itinerary_text(proposal).splitlines(), 'option_descriptions': descriptions})
        if selected in ('book', 'back'): return selected
        leg = proposal['legs'][int(selected.split('_')[1])]
        single = {**proposal, 'legs': [leg], 'name': leg['venue_name']}
        report(game, leg['venue_name'], itinerary_text(single))


def propose_local_show(game, venue_id, days_ahead):
    city = game.player.current_location
    venue = next((v for v in city.venues if v.venue_id == venue_id), None)
    if venue is None or days_ahead not in (2, 4, 7):
        return {'ok': False, 'explanation': 'That room or date is unavailable.'}
    event_type = 'CLUB_GIG' if game.player.fame >= 50 else 'OPEN_MIC'
    if game.player.fame >= 150 and (venue.venue_type == 'CONCERT_HALL' or venue.capacity >= 500):
        event_type = 'CONCERT'
    start = current_game_time.copy();start.add_days(days_ahead);start.hour, start.minute = 19, 0
    end = start.copy();end.add_hours(3)
    elapsed = getattr(game.player, 'early_life_days_elapsed', 0)
    tier = game.early_life.LODGING.get(getattr(game.player, 'lodging_tier', 'shared_room'))
    living = days_ahead * 7 + ((elapsed + days_ahead) // 7 - elapsed // 7) * (tier.weekly_cost if tier else 105)
    return {'ok': True, 'kind': 'single', 'template_id': 'local_show', 'name': f'Live at {venue.name}',
            'fee': 5, 'quoted_day': current_game_time.day_index(), 'fare_estimate': 0,
            'living_estimate': living, 'days': days_ahead,
            'legs': [{'city': city.name, 'venue_id': venue.venue_id, 'venue_name': venue.name,
                      'start': start, 'end': end, 'event_type': event_type, 'skills': {},
                      'guarantee': Event.EVENT_TYPES[event_type]['base_payout'],
                      'route': {'cost': 0, 'hours': 0, 'legs': []}}]}


def local_show_desk(game):
    venues = [v for v in game.player.current_location.venues
              if v.venue_type in ('BAR_GIG', 'CLUB', 'HALL') or game.player.fame >= 150]
    options = {v.venue_id: v.name for v in venues};options['back'] = 'Back'
    selected = game.ui.present_choices(options, 'Local booking desks', context={
        'subtitle': 'Reserve a date in town. Public open mics remain available directly at venues.'})
    if selected == 'back': return
    day = game.ui.present_choices({'2': 'Two days from now / 19:00', '4': 'Four days from now / 19:00',
                                   '7': 'One week from now / 19:00', 'back': 'Back'}, 'Offered dates')
    if day == 'back': return
    proposal = propose_local_show(game, selected, int(day))
    if not proposal['ok']: game.GAME_LOG.add_log_message(proposal['explanation']);return
    if review_proposal(game, proposal) == 'book':
        result = commit_tour(game, proposal)
        game.GAME_LOG.add_log_message(result['explanation'])
