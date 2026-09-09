"""Resumable creative sessions with physical costs and persistent drafts."""
import random

STAGES = (("Lyrics", 120), ("Melody", 180), ("Arrangement", 180))


def condition_multiplier(player):
    fatigue = max(0, 65 - player.energy) / 100
    stress = max(0, player.stress - 40) / 200
    hunger = max(0, player.hunger - 55) / 250
    return max(0.45, 1.0 - fatigue * 0.55 - stress - hunger)


def spend_session(game, minutes, effort=5):
    game._advance_time_with_needs(minutes)
    game.player.energy = max(0, game.player.energy - int(minutes / 60 * effort))
    game.player.stress = min(100, game.player.stress + int(minutes / 60))


def open_notebook(game):
    if not game.song_in_progress.get('session_started'):
        game.song_in_progress = {}
        game.songwriting_stage = 'choose_genre'
    else:
        game.songwriting_stage = 'writing_components'
    game.selected_poi = game.player.current_poi
    game.explore_menu_state = 'write_song_menu'
    game.game_state = 'explore'


def work_on_draft(game):
    draft, p = game.song_in_progress, game.player
    index = draft.get('session_index', 0)
    if index >= len(STAGES):
        game.songwriting_stage = 'invite_feature'
        return True
    label, minutes = STAGES[index]
    if draft.get('session_started'):
        choice = game.ui.present_choices({'work': f'Work on {label.lower()} / {minutes // 60} hours',
                                         'back': 'Close notebook / keep draft'},
            draft.get('title', 'Untitled'), context={
                'eyebrow': 'Song notebook',
                'subtitle': f"{label} / {index} of 3 sessions complete",
                'details': [f'Energy {p.energy}/100; hunger {p.hunger}/100; stress {p.stress}/100.',
                            'Sessions consume 5 energy per hour. Fatigue, hunger and stress affect the work.',
                            'The draft remains in your notebook when you leave.'],
                'option_descriptions': {'work': f'{minutes // 60} hours with the notebook and instrument. Earlier sections retain their quality.',
                                        'back': 'Keep the work as it stands. No time passes.'}})
        if choice == 'back':
            game.game_state = 'main_menu';game.explore_menu_state = 'poi'
            return False
    if p.energy < 15:
        game.GAME_LOG.add_log_message('You cannot concentrate on a writing session. The draft is kept.')
        game.game_state = 'main_menu';game.explore_menu_state = 'poi'
        return False
    draft['session_started'] = True
    bonus = draft.get('inspiration_bonus', 0)
    band = p.band if draft.get('is_collaborative') else None
    if band:
        bonus += (band.chemistry - 50) / 200
        if random.random() < max(.05, .5 - band.chemistry / 150):
            band.update_chemistry(-3);bonus -= .1;p.stress = min(100, p.stress + 5)
            game.GAME_LOG.add_log_message('The band disagrees over the direction of the song.')
        elif random.random() < band.chemistry / 150:
            band.update_chemistry(1);bonus += .05
            game.GAME_LOG.add_log_message('The band finds an arrangement everyone can get behind.')
    original_band = p.band
    if not band: p.band = None
    def quality(primary, secondary=None, weight=.75):
        value = game._calculate_song_component_quality(primary, secondary, weight) + bonus
        return max(.05, min(1.0, value * condition_multiplier(p)))
    try:
        if index == 0: draft['lyrical_depth'] = quality('songwriting')
        elif index == 1: draft['catchiness'] = quality('songwriting', 'guitar')
        else:
            draft['music_complexity'] = quality('guitar', 'songwriting', .7)
            draft['originality'] = quality('songwriting')
    finally:
        p.band = original_band
    spend_session(game, minutes)
    p.practice_skill('songwriting', minutes / 120)
    draft['session_index'] = index + 1
    game.GAME_LOG.add_log_message(f"{label} session finished for '{draft['title']}'. Energy {p.energy}/100.")
    if index == 2:
        game.songwriting_stage = 'invite_feature'
        return True
    return False
