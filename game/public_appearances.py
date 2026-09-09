"""A public appearance is a short, consequential scene, not an attendance reward."""
import random
from game.game_time import current_game_time
from game.career_actions import report
from game.world_memory import WorldMemoryEntry


def run_signing(game):
    p = game.player
    poi = p.current_poi
    opportunity = p.active_opportunities.get('autograph_signing', {})
    if (game.game_state == 'travel_active' or getattr(poi, 'category', '') != 'SHOP_MUSIC'
            or opportunity.get('status') != 'available'):
        game.GAME_LOG.add_log_message('A signing needs an available invitation and your presence at a music shop.')
        return
    day = current_game_time.day_index()
    history = getattr(p, 'appearance_history', [])
    if any(h['city'] == p.current_location.name and day - h['day'] < 7 for h in history):
        game.GAME_LOG.add_log_message('This city has already hosted you this week.')
        return
    rng = random.Random(f'{p.name}:{poi.poi_id}:{day}')
    turnout = max(3, min(100, int(p.fame * .18 + p.street_cred * .12) + rng.randint(-3, 6)))
    state = {'city': p.current_location.name, 'day': day, 'venue': poi.name,
             'turnout': turnout, 'waiting': turnout, 'met': 0, 'left': 0,
             'goodwill': 0, 'revenue': 0, 'units_sold': 0, 'minutes': 0, 'decisions': []}

    def choose(title, subtitle, options, descriptions=None):
        return game.ui.present_choices(options, title, context={
            'eyebrow': f'In store / {poi.name}', 'subtitle': subtitle,
            'appearance': dict(state),
            'panel_title': 'At the signing table',
            'details': [f"{state['waiting']} waiting / {state['met']} met / {state['left']} left",
                        f"{state['minutes']} min elapsed / 90 min advertised",
                        f"${state['revenue']} merchandise receipts / {state['units_sold']} items",
                        f'Energy {p.energy:.0f} / stress {p.stress:.0f}',
                        'Signing is free. Income requires stock and buyers.'],
            'option_descriptions': descriptions or {},
        })

    policy = choose('Before the doors open', f'{turnout} people have turned up. Set the pace for the table.', {
        'personal': 'Make time for a conversation with each fan',
        'brisk': 'Keep the line moving / names and signatures',
        'merch': 'Sign at the merchandise table', 'back': 'Decline the appearance',
    }, {'personal': 'More personal attention, fewer people reached before closing.',
        'brisk': 'Shorter waits and more signatures, less time to connect.',
        'merch': 'More buyers, but handling stock slows the line. Uses your existing merchandise.'})
    if policy == 'back':
        return
    previous_state = game.game_state
    game.game_state = 'appearance'
    state['decisions'].append(policy)

    def batch(minutes, attention=0):
        pace = {'personal': 4, 'brisk': 2, 'merch': 3}[policy]
        condition = max(.35, min(1, p.energy / 45)) * (1 - p.stress / 250)
        served = min(state['waiting'], max(0, int((minutes - attention) / pace * condition)))
        state['waiting'] -= served
        state['met'] += served
        state['goodwill'] += served * (2 if policy == 'personal' else 1)
        # A person buys at most one item. No stock is conjured by the event.
        buyers = int(served * (.6 if policy == 'merch' else .25))
        for item in p.merch_stock:
            count_attr = 'unit_count' if hasattr(item, 'unit_count') else 'stock'
            stock = getattr(item, count_attr, 0)
            price = getattr(item, 'suggested_price', getattr(item, 'sale_price', 0))
            affordable_buyers = buyers if price <= 25 else buyers // 2
            sold = min(stock, affordable_buyers) if price > 0 else 0
            setattr(item, count_attr, stock - sold)
            buyers -= sold
            revenue = sold * price
            p.money += revenue
            state['revenue'] += revenue
            state['units_sold'] += sold
        state['minutes'] += minutes
        p.energy = max(0, p.energy - minutes / 6)
        p.stress = min(100, p.stress + state['waiting'] / 12)
        game._advance_time_with_needs(minutes)
        if state['minutes'] >= 60:
            walkouts = min(state['waiting'], max(0, int(state['waiting'] * .18)))
            state['waiting'] -= walkouts
            state['left'] += walkouts
        game.GAME_LOG.add_log_message(f"Signing: {served} more people met; {state['waiting']} still waiting.")

    try:
        batch(30)
        if state['waiting']:
            moment = rng.choice(['letter', 'demo'])
            story = ('A fan has brought a letter about what your music meant during a difficult year.' if moment == 'letter'
                     else 'A young musician has brought a homemade demo and wants you to listen.')
            choice = choose('Someone at the table', story, {
                'listen': 'Give them ten minutes',
                'kind': 'Have a brief word and keep the queue moving',
                'close': 'End the session here',
            }, {'listen': 'This person gets your attention; everyone behind them waits longer.',
                'kind': 'A short, warm exchange leaves time for the rest of the queue.',
                'close': 'People who have not reached the table leave without meeting you.'})
            state['decisions'].append(choice)
            if choice != 'close':
                if choice == 'listen':
                    state['goodwill'] += 6
                    p.inspiration = min(100, p.inspiration + 3)
                batch(30, attention=10 if choice == 'listen' else 0)
                if state['waiting']:
                    choice = choose('The line is slowing', 'A phone is filming. People at the back are asking whether everyone will get a turn.', {
                        'brisk': 'Switch to one signature each',
                        'personal': 'Keep giving people time',
                        'close': 'Thank everyone and close early',
                    })
                    state['decisions'].append(choice)
                    if choice != 'close':
                        policy = choice
                        batch(30)
                        if state['waiting']:
                            choice = choose('Closing time', 'The advertised session is over. Some people are still waiting.', {
                                'extend': 'Stay another half hour', 'close': 'Close the table',
                            }, {'extend': 'More people reached, more fatigue, and your next commitment gets half an hour closer.',
                                'close': 'Protect the rest of your day. The remaining fans leave without a signature.'})
                            state['decisions'].append(choice)
                            if choice == 'extend':
                                batch(30)
        state['left'] += state['waiting']
        state['waiting'] = 0
        fame = max(-4, min(8, int((state['met'] - state['left'] * .6) / 5)))
        cred = max(-5, min(5, int((state['goodwill'] - state['left']) / 8)))
        p.fame = max(0, p.fame + fame)
        p.street_cred = max(0, min(100, p.street_cred + cred))
        state.update(fame_change=fame, cred_change=cred)
        p.appearance_history = history + [state]
        opportunity['status'] = 'completed'
        game.world_memory.add(WorldMemoryEntry(
            'public_appearance', [p.name], state['city'], current_game_time.copy(),
            tags=['fans', 'signing'], impact_score=cred,
            metadata=dict(state), source_key=f"signing:{p.name}:{poi.poi_id}:{day}"))
        text = (f"{state['venue']} / {state['minutes']} minutes\n\n"
                f"{turnout} attended. {state['met']} met you; {state['left']} left without a signature.\n"
                f"{state['units_sold']} items sold from your stock / ${state['revenue']} receipts.\n"
                f"Fame {fame:+} / street credibility {cred:+}.\n\n"
                'Receipts are sales, before the cost of making the merchandise. The queue and your condition shaped the result.')
        game.GAME_LOG.add_log_message(text)
        report(game, 'After the signing', text)
    finally:
        game.game_state = previous_state
