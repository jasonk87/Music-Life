"""Player-accessible career systems. Menus inspect; committed actions spend time."""
from game.game_time import current_game_time


def report(game, title, text):
    if hasattr(game.ui, 'interface'):
        game.ui.interface.read_document(title, text)
    else:
        game.GAME_LOG.add_log_message(text)


def assemble_release(game):
    candidates = [s for s in game.player.songs_written if s.is_recorded]
    if len(candidates) < 3:
        game.GAME_LOG.add_log_message('A release needs at least three recorded tracks.')
        return
    selected = []
    while True:
        options = {str(i): f"{'Selected / ' if s in selected else ''}{s.title}" for i, s in enumerate(candidates)}
        options['release'] = f'Release {len(selected)} tracks / $50 distribution'
        options['back'] = 'Cancel release'
        choice = game.ui.present_choices(options, 'Sequence a record', context={
            'eyebrow': 'Release desk', 'subtitle': 'Selection order becomes the running order.',
            'details': [f'{i+1}. {s.title}' for i, s in enumerate(selected)] or ['No tracks selected.'],
        })
        if choice == 'back': return
        if choice == 'release':
            if not 3 <= len(selected) <= 16:
                game.GAME_LOG.add_log_message('The distributor accepts between 3 and 16 tracks.')
                continue
            if game.player.money < 50:
                game.GAME_LOG.add_log_message('Distribution costs $50. No payment was taken.')
                return
            title = game.ui.get_text_input('Record title', context={'panel_title': 'Release desk'})
            if not title: return
            result = game.album_system.assemble_album(game.player, title, selected)
            if result['ok']:
                game.player.money -= 50
                for song in selected: game.streaming_system.register_song_for_streaming(song, game.player.fame)
                game.music_press_reviews.generate_press_reviews_for_album(game.player, result['album'])
                game._advance_time_with_needs(30)
            game.GAME_LOG.add_log_message(result['explanation'])
            return
        if choice in options:
            song = candidates[int(choice)]
            if song in selected: selected.remove(song)
            elif len(selected) < 16: selected.append(song)


def catalog_business(game):
    for song in game.player.songs_written:
        if song.is_released: game.streaming_system.register_song_for_streaming(song, game.player.fame)
    choice = game.ui.present_choices({
        'statement': 'Streaming statement', 'pitch': 'Submit an editorial pitch / 30 min',
        'press': 'Order vinyl / from $600', 'orders': 'Pressing orders & inventory',
        'reviews': 'Records & press reviews', 'back': 'Back to music',
    }, 'The release desk', context={'eyebrow': 'Independent distribution',
        'subtitle': 'Audience, manufacturing and the money behind the music.',
        'details': [f'{len(game.streaming_system.catalog)} tracks distributed',
                    f'${game.streaming_system.accumulated_unpaid_royalties:.2f} awaiting payout',
                    f'{len(game.album_system.released_albums)} records released'],
        'option_descriptions': {
            'pitch': 'Editorial fit, production quality and your reputation determine acceptance. One submission per curator per track every seven days.',
            'press': '100, 250 or 500 records. $6 per copy; 21-day manufacturing lead time. Sales depend on audience demand.',
            'statement': 'Actual streams and royalties accumulated as the calendar advances.',
        }})
    if choice == 'statement':
        lines=[]
        for track in game.streaming_system.catalog.values():
            lines += [track.title, f'{track.total_streams:,} lifetime streams / {track.daily_streams:,} last day',
                      f'${track.total_royalties_earned:.2f} earned',
                      'Placements: '+(', '.join(p.name for p in track.active_playlists) or 'None'), '']
        report(game,'Streaming statement','\n'.join(lines) or 'No releases in distribution.')
    elif choice == 'pitch':
        catalog=game.streaming_system.catalog
        if not catalog:
            game.GAME_LOG.add_log_message('There are no distributed tracks to submit.');return
        tracks={sid:t.title for sid,t in catalog.items()};tracks['back']='Cancel'
        sid=game.ui.present_choices(tracks,'Choose a track')
        if sid=='back':return
        playlists={p['id']:f"{p['name']} / {p['genre']}" for p in game.streaming_system.CURATED_PLAYLISTS}
        playlists['back']='Cancel'
        target=game.ui.present_choices(playlists,'Editorial desks')
        if target=='back':return
        result=game.streaming_system.pitch_to_editorial_playlist(game.player,sid,target)
        game._advance_time_with_needs(30)
        game.GAME_LOG.add_log_message(result['explanation'])
    elif choice == 'press':
        albums=game.album_system.released_albums
        if not albums:
            game.GAME_LOG.add_log_message('No released albums are available for pressing.');return
        opts={str(i):a.title for i,a in enumerate(albums)};opts['back']='Cancel'
        chosen=game.ui.present_choices(opts,'Pressing plant / album')
        if chosen=='back':return
        units=game.ui.present_choices({'100':'100 copies / $600','250':'250 copies / $1,500','500':'500 copies / $3,000','back':'Cancel'},'Pressing quantity')
        if units=='back':return
        result=game.album_system.order_vinyl_pressing(game.player,albums[int(chosen)],int(units))
        if result['ok']:game._advance_time_with_needs(30)
        game.GAME_LOG.add_log_message(result['explanation'])
    elif choice == 'orders':
        orders=game.album_system.pending_vinyl_orders+game.album_system.delivered_vinyl_batches
        lines=[]
        for order in orders:
            remaining=max(0,order.order_day+order.days_to_deliver-current_game_time.day_index())
            lines.append(f'{order.album_title}: '+(f'{order.units_in_stock} in stock / {order.units_sold} sold' if order.delivered else f'{remaining} days until delivery / {order.units_ordered} copies'))
        report(game,'Pressing ledger','\n\n'.join(lines) or 'No manufacturing orders.')
    elif choice == 'reviews':
        lines=[str(a) for a in game.album_system.released_albums]
        for review in getattr(game.music_press_reviews,'review_archive',[]):lines.append(f'{review.publication}: {review.numeric_score} / {review.review_headline}\n{review.review_blurb}')
        report(game,'Discography','\n\n'.join(lines) or 'No records released.')


def scene_network(game):
    from game.dynamic_musician_interactions import DynamicMusicianInteractions
    city=game.player.current_location.name
    musicians=game.dynamic_musicians.get_musicians_in_city(city)
    options={m.artist_id:f'{m.name} / {m.status.replace("_"," ").title()}' for m in musicians}
    options['back']='Back to phone'
    choice=game.ui.present_choices(options,'Artists in town',context={
        'eyebrow':city,'subtitle':'Other musicians have their own schedules, money and ambitions.',
        'details':[f'{m.name}: {getattr(game.get_poi_or_venue_by_id(m.current_poi_id), "name", "On the move")}' for m in musicians]})
    if choice=='back':return
    musician=game.dynamic_musicians.musicians[choice]
    poi=game.player.current_poi
    here=getattr(poi,'poi_id',getattr(poi,'venue_id',None))
    if here!=musician.current_poi_id:
        place=game.get_poi_or_venue_by_id(musician.current_poi_id)
        game.GAME_LOG.add_log_message(f'{musician.name} is at {getattr(place,"name","another location")}.');return
    if musician.status in ('PERFORMING','RECORDING'):
        game.GAME_LOG.add_log_message(f'{musician.name} is working and cannot talk right now.');return
    action=game.ui.present_choices({'chat':'Share a coffee / $5 / 1 hour','cowrite':'Work on an unfinished song / 2 hours','back':'Leave them to it'},musician.name,
        context={'eyebrow':musician.genre,'subtitle':f'Familiarity {musician.affinity_with_player:.0f} / 100','details':[f'Currently {musician.status.lower().replace("_"," ")}']})
    if action=='back':return
    if getattr(musician,'last_player_visit',-1)==current_game_time.day_index():
        game.GAME_LOG.add_log_message(f'{musician.name} has other plans for the rest of today.');return
    if action=='chat':
        if game.player.money<5:game.GAME_LOG.add_log_message('Coffee costs $5.');return
        game.player.money-=5
        result=DynamicMusicianInteractions.hang_out_and_chat(game.player,musician)
        duration=60
    else:
        songs=[s for s in game.player.songs_written if not s.is_recorded and not getattr(s,'coauthor_ids',[])]
        if not songs:game.GAME_LOG.add_log_message('No unfinished solo compositions to bring to the session.');return
        opts={str(i):s.title for i,s in enumerate(songs)};opts['back']='Cancel'
        selected=game.ui.present_choices(opts,'Bring a song')
        if selected=='back':return
        song=songs[int(selected)]
        result=DynamicMusicianInteractions.jam_and_cowrite_song(game.player,musician,song)
        if result['ok']:song.coauthor_ids=[musician.artist_id]
        duration=120
    if result['ok']:
        musician.last_player_visit=current_game_time.day_index()
        game._advance_time_with_needs(duration)
    game.GAME_LOG.add_log_message(result['explanation'])


def shift_listings(game):
    """Book a specific shift. Availability is information, never an assignment."""
    p = game.player
    game.early_life.bootstrap_player_jobs(p)
    jobs = {key: job for key, job in p.early_jobs.items()
            if any(site.poi_id == job['location_id'] for site in p.current_location.points_of_interest)}
    options = {key: f"{job['title']} / ${job['pay']} / {job['shift_duration_minutes'] / 60:g} hours"
               for key, job in jobs.items()}
    options['back'] = 'Back to phone'
    chosen = game.ui.present_choices(options, 'Local shift listings', context={
        'subtitle': 'One shift at a time. Pay depends on attendance.',
        'details': [f"{job['title']}: {job['location_name']}" for job in jobs.values()]})
    if chosen == 'back': return
    job = jobs[chosen]
    start = game.early_life._next_shift_start(current_game_time.copy())
    end = start.copy(); end.advance_time(job['shift_duration_minutes'])
    overlaps = [e for e in p.schedule.scheduled_items if e.start_time < end and e.end_time > start]
    if overlaps:
        game.GAME_LOG.add_log_message(f"That shift overlaps {overlaps[0].description}. No booking made.")
        return
    choice = game.ui.present_choices({'book': 'Accept this shift', 'back': 'Leave listing'},
        job['location_name'], context={'subtitle': f"{start} / ${job['pay']}",
        'details': [f"Ends {end}", 'Travel to the workplace before the shift. Absence earns no pay and reduces reliability.']})
    if choice == 'back': return
    result = game.early_life.schedule_job_shift(p, chosen, start)
    if result['ok']:
        game.GAME_LOG.add_log_message(f"Booked {job['title']} at {job['location_name']}, {start}. ${job['pay']} for a full shift.")
