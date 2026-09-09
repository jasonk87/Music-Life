"""Remote work uses the same career data at home and in a passenger seat."""
from game.game_time import current_game_time
from game.career_actions import report


def contact_card(game, npc_id, spend_time=None):
    npc = game.NPC_REGISTRY.get(npc_id)
    if not npc:
        return
    spend_time = spend_time or game._advance_time_with_needs
    day = current_game_time.day_index()
    called = getattr(npc, 'last_player_call_day', -1) == day
    options = {'call': 'Call / 15 min' if not called else 'Already spoke today', 'back': 'Back to contacts'}
    choice = game.ui.present_choices(options, npc.name, context={
        'eyebrow': 'Address book', 'subtitle': 'A conversation needs time. Reading a contact does not.',
        'panel_title': 'Your connection',
        'details': [f'{npc.relationship_with_player.name.title()} / {npc.relationship_score:+}',
                    f"Last conversation: {'today' if called else 'not today'}"] + list(npc.memories[-3:]),
        'option_descriptions': {'call': 'Check in about life on the road. Repeated calls on the same day do not improve the relationship.'},
    })
    if choice != 'call' or called:
        return
    if getattr(npc, 'contact_access', {}).get('blocked'):
        game.GAME_LOG.add_log_message(f'{npc.name} is not taking your calls.')
        return
    # Commit before time advances, so calendar callbacks cannot repeat this call.
    npc.last_player_call_day = day
    npc.update_relationship(2)
    npc.add_memory(f'{game.player.name} called to catch up on {current_game_time}.')
    game.player.stress = max(0, game.player.stress - 2)
    spend_time(15)
    game.GAME_LOG.add_log_message(f'You caught up with {npc.name}.')


def choose_contact(game, spend_time=None):
    options = {key: game.NPC_REGISTRY[key].name for key in game.player.contacts if key in game.NPC_REGISTRY}
    options['back'] = 'Back'
    choice = game.ui.present_choices(options, 'Contacts')
    if choice != 'back':
        contact_card(game, choice, spend_time)


def onboard_phone(game, tm, spend_time):
    """Only remote actions; consuming time also moves the existing journey."""
    from game.live_bookings import booking_desk
    while not tm.is_finished:
        choice = game.ui.present_choices({
            'calendar': 'Calendar & commitments',
            'bookings': 'Live bookings & settlements',
            'contacts': 'Contacts / calls take 15 min',
            'news': 'Read the scene feed',
            'back': 'Put phone away',
        }, 'Phone / in transit', context={
            'eyebrow': f'En route to {tm.destination.name}',
            'subtitle': 'Calls and confirmed bookings use journey time. Browsing does not.',
            'panel_title': 'Journey continues',
            'details': [f'{tm.get_progress_percent():.0%} of route covered',
                        f'{game.transit_layer.estimate_remaining_minutes(tm)} min estimated remaining',
                        'Booking administration: 15 min after a change.',
                        'Local listings refer to your departure city.'],
        })
        if choice == 'back':
            return
        if choice == 'calendar':
            report(game, 'Calendar', '\n\n'.join(str(e) for e in game.player.schedule.scheduled_items) or 'No commitments.')
        elif choice == 'news':
            from game.rivals import get_news_feed
            feed = list(reversed(game.dynamic_musicians.world_event_logs[-15:])) + get_news_feed()[:10]
            report(game, 'The music pages', '\n\n'.join(feed) or 'Nothing in the music pages today.')
        elif choice == 'contacts':
            choose_contact(game, spend_time)
        elif choice == 'bookings':
            before = repr(getattr(game.player, 'tour_ledgers', {}))
            booking_desk(game)
            if before != repr(getattr(game.player, 'tour_ledgers', {})):
                spend_time(15)
