"""A club night connects preparation, people, the show and its settlement."""
import random
from game.game_time import current_game_time
from game.npc import NPC
from game.world_memory import WorldMemoryEntry


class ClubLife:
    def __init__(self, game, venue):
        if not hasattr(venue, 'events_hosted') or game.player.current_poi is not venue:
            raise ValueError('Enter the venue before working on its show.')
        self.game, self.poi, self.player = game, venue, game.player
        self.interruption = None
        if not hasattr(venue, 'club_life'):
            rng = random.Random(venue.venue_id)
            ids = []
            for role, names in [('promoter', ['Rae', 'Sid', 'Frankie']), ('engineer', ['Ash', 'Jo', 'Toni']), ('regular', ['Cam', 'Drew', 'Lou'])]:
                key = f'club:{venue.venue_id}:{role}'
                npc = NPC(key, rng.choice(names), 'friendly', home_location=venue, current_location=venue)
                npc.role_tags.add(role)
                game.NPC_REGISTRY[key] = npc
                ids.append(key)
            venue.club_life = {'host_id': ids[0], 'engineer_id': ids[1], 'regular_ids': ids[2:],
                               'plans': {}, 'history': [], 'last_result': None}
        self.data = venue.club_life

    @property
    def active(self):
        # The room is always available; performances use the existing stage controller.
        return None

    @property
    def host(self):
        return self.game.NPC_REGISTRY[self.data['host_id']]

    def enter(self):
        self.refresh()

    def log(self, text):
        self.game.GAME_LOG.add_log_message(text)

    def events(self):
        day = current_game_time.day_index()
        return [e for e in self.poi.events_hosted if e.is_active and (
            getattr(e, 'booking_start', current_game_time).day_index() == day)]

    def event(self):
        candidates = self.events()
        booked = next((e for e in candidates if getattr(e, 'booking_id', None)), None)
        if booked: return booked
        # Keep tonight's settlement visible instead of silently offering another slot.
        last = self.data['last_result']
        if last and last['day'] == current_game_time.day_index():
            finished = next((e for e in self.poi.events_hosted if e.event_id == last.get('event_id')), None)
            if finished: return finished
        return next(iter(candidates), None)

    def times(self, event=None):
        event = event or self.event()
        start = getattr(event, 'booking_start', None)
        if start is None:
            start = current_game_time.copy(); start.hour, start.minute = 19, 0
        end = getattr(event, 'booking_end', None)
        if end is None:
            end = start.copy(); end.add_hours(4)
        doors = start.copy()
        # Simplified calendar arithmetic, including midnight-crossing bookings.
        minutes = start.hour * 60 + start.minute
        if minutes >= 30:
            doors.hour, doors.minute = divmod(minutes - 30, 60)
        else:
            doors.day -= 1
            if doors.day < 1:
                doors.day = 30; doors.month -= 1
                if doors.month < 1: doors.month = 12; doors.year -= 1
            doors.hour, doors.minute = divmod(1440 + minutes - 30, 60)
        return doors, start, end

    def plan(self, event=None):
        event = event or self.event()
        if not event: return None
        key = f'{event.event_id}:{current_game_time.day_index()}'
        if key not in self.data['plans']:
            rng = random.Random(f'{self.poi.venue_id}:{key}')
            self.data['plans'][key] = {'key': key, 'day': current_game_time.day_index(), 'event_id': event.event_id,
                'sound': 0, 'merch_ready': False, 'promoter_met': False, 'crowd_connection': 0,
                'monitor_fault': rng.random() < .35, 'monitor_resolved': False, 'monitor_revealed': False,
                'crew_task': None, 'status': 'preparing', 'seen_cues': [], 'decisions': [], 'final_hype': None}
        return self.data['plans'][key]

    def refresh(self):
        # Work finishes on the shared clock even when the player visits another room.
        for plan in self.data['plans'].values():
            task = plan['crew_task']
            if not task or plan['status'] != 'preparing': continue
            if task['staff'] not in self.player.staff:
                plan['crew_task'] = None
                self.log('Crew preparation stopped: that staff member is no longer working for you.')
            elif current_game_time >= task['ready_at']:
                if task['kind'] == 'sound':
                    plan['sound'] = min(9, 4 + task['staff'].skill_level)
                    plan['monitor_revealed'] = plan['monitor_fault']
                else:
                    plan['merch_ready'] = True
                self.log(f"{task['staff'].name} finished {'soundcheck' if task['kind']=='sound' else 'the merch table'}.")
                plan['crew_task'] = None

    def can_prepare(self):
        event = self.event()
        if not event: return False, 'There is no available show in this room today.'
        _, start, end = self.times(event)
        plan = self.plan(event)
        if plan['status'] != 'preparing' or getattr(event, 'last_played_day', -1) == current_game_time.day_index():
            return False, 'Your set in this room is already finished or underway.'
        if current_game_time < start and start.days_difference(current_game_time) * 1440 > 90:
            return False, 'Load-in begins ninety minutes before the set.'
        if current_game_time > end: return False, 'The performance window has closed.'
        return True, ''

    def elapse(self, minutes, at_table=False, interruptible=False):
        elapsed = 0
        for _ in range(int(minutes)):
            before = current_game_time.copy()
            upcoming = self.player.schedule.get_upcoming_events(before, limit=1)
            self.game._advance_time_with_needs(1)
            elapsed += 1
            self.refresh()
            event = self.event()
            if event:
                doors, start, end = self.times(event)
                for cue, date in [('doors', doors), ('set', start), ('closed', end)]:
                    if before < date <= current_game_time:
                        text = {'doors': 'Doors are open. People are moving toward the stage.',
                                'set': 'Your set window is open. The stage is waiting.',
                                'closed': 'The performance window has ended.'}[cue]
                        self.log(text)
                        if interruptible:
                            self.interruption = text
            if upcoming and before < upcoming[0].start_time <= current_game_time and interruptible:
                self.interruption = f'Calendar: {upcoming[0].description} is starting.'
            if self.interruption and interruptible: break
        return elapsed

    def prepare(self, kind):
        allowed, reason = self.can_prepare()
        if not allowed:
            self.log(reason); return False
        p = self.plan()
        if kind == 'sound':
            if p['sound']:
                self.log('The soundcheck is already done.'); return False
            if p['crew_task'] and p['crew_task']['kind'] == 'sound':
                self.log('Your crew is already checking the sound.'); return False
            self.elapse(25)
            self.player.energy = max(0, self.player.energy - 5)
            p['sound'] = 7
            p['monitor_revealed'] = p['monitor_fault']
            self.log('Soundcheck finished. ' + ('There is a hum in the stage monitor.' if p['monitor_fault'] else 'You can hear the vocal clearly from the stage.'))
        elif kind == 'merch':
            if p['merch_ready'] or (p['crew_task'] and p['crew_task']['kind'] == 'merch'): return False
            if not any(getattr(m, 'unit_count', getattr(m, 'stock', 0)) > 0 for m in self.player.merch_stock):
                self.log('There is no merchandise in your stock.'); return False
            self.elapse(15)
            p['merch_ready'] = True
            self.log('Your stock is laid out and priced for after the set.')
        elif kind == 'monitor':
            if not p['monitor_revealed'] or p['monitor_resolved']: return False
            if self.player.money < 8:
                self.log('A replacement lead costs $8. No payment taken.'); return False
            self.player.money -= 8
            self.elapse(10)
            p['monitor_resolved'] = True
            self.log('The replacement lead clears the monitor hum. Paid $8.')
        else:
            return False
        p['decisions'].append(kind)
        return True

    def talk(self, role):
        keys = {'promoter': self.data['host_id'], 'regular': self.data['regular_ids'][0]}
        if role not in keys: return False
        npc = self.game.NPC_REGISTRY[keys[role]]
        day = current_game_time.day_index()
        if getattr(npc, 'last_club_chat_day', -1) == day:
            self.log(f'{npc.name}: "We will catch up after the show."'); return False
        npc.last_club_chat_day = day
        self.elapse(10 if role == 'promoter' else 5)
        npc.update_relationship(2)
        npc.add_memory(f'{self.player.name} made time to talk at {self.poi.name}.')
        plan = self.plan()
        if plan and plan['status'] == 'preparing':
            if role == 'promoter': plan['promoter_met'] = True
            else: plan['crowd_connection'] = 4
        self.log(f'You catch up with {npc.name}.')
        return True

    def assign_crew(self, staff, kind):
        allowed, reason = self.can_prepare()
        if not allowed:
            self.log(reason); return False
        if staff not in self.player.staff or kind not in {'sound', 'merch'}: return False
        if staff.role.lower().replace('_',' ') not in {'roadie', 'sound engineer'}: return False
        if kind == 'merch' and not any(getattr(m, 'unit_count', getattr(m, 'stock', 0)) > 0 for m in self.player.merch_stock):
            self.log('There is no merchandise in your stock.'); return False
        plan = self.plan()
        if plan['crew_task'] or (plan['sound'] if kind == 'sound' else plan['merch_ready']): return False
        for city in self.game.WORLD_MAP.values():
            for venue in city.venues:
                for other in getattr(venue, 'club_life', {}).get('plans', {}).values():
                    task = other.get('crew_task')
                    if task and task['staff'] is staff and current_game_time < task['ready_at']:
                        self.log(f'{staff.name} is still working on another task.'); return False
        ready = current_game_time.copy(); ready.advance_time(30 if kind == 'sound' else 20)
        plan['crew_task'] = {'staff': staff, 'kind': kind, 'ready_at': ready}
        self.log(f'{staff.name} gets started. Expected finish: {ready.hour:02d}:{ready.minute:02d}.')
        return True

    def attendance(self):
        event = self.event()
        if not event: return 0
        doors, start, _ = self.times(event)
        if current_game_time <= doors: return 0
        progress = max(0, min(1, current_game_time.days_difference(doors)*1440 / 30))
        demand = max(6, min(self.poi.capacity, int(10 + self.player.fame*.3 + max(0, self.host.relationship_score)*.4)))
        late = max(0, current_game_time.days_difference(start)*1440 - 10) if current_game_time > start else 0
        return int(demand * progress * max(.25, 1-late/150))

    def take_stage(self):
        event = self.event()
        if not event: return False, 'No available slot today.'
        if self.plan(event)['status'] != 'preparing':
            return False, 'Your slot in this room is already finished or underway.'
        _, start, end = self.times(event)
        if not start <= current_game_time <= end:
            return False, f'The set window is {start.hour:02d}:{start.minute:02d} to {end.hour:02d}:{end.minute:02d}.'
        ready, reason, _ = event.can_perform(self.player)
        if not ready: return False, reason
        self.refresh()
        plan = self.plan(event)
        plan['status'] = 'called'
        sound = plan['sound'] - (5 if plan['monitor_fault'] and not plan['monitor_resolved'] else 0)
        late = max(0, round(current_game_time.days_difference(start)*1440))
        event.club_performance_context = {'plan_key': plan['key'], 'day': plan['day'], 'sound_bonus': sound,
            'late_minutes': late,
            'crowd_bonus': plan['crowd_connection'] + (2 if plan['promoter_met'] else 0) - min(25,late//3),
            'merch_ready': plan['merch_ready'], 'attendance': self.attendance()}
        self.game.active_performance = event
        self.game.performance_stage = 'choose_song'
        self.game.performance_requirement_penalty = 1.0
        self.game.game_state = 'performance'
        self.player.schedule.scheduled_items = [item for item in self.player.schedule.scheduled_items
                                                if item.details.get('event_id') != event.event_id]
        return True, 'You take the stage.'


def record_club_show(game, event, status, paid):
    context = getattr(event, 'club_performance_context', None)
    data = getattr(getattr(event, 'location', None), 'club_life', None)
    if not data: return
    if not context:
        day = getattr(event, 'booking_start', current_game_time).day_index()
        plan = data['plans'].get(f'{event.event_id}:{day}')
        if not plan: return
        context = {'plan_key': plan['key'], 'day': day, 'sound_bonus': plan['sound'], 'merch_ready': plan['merch_ready']}
    plan = data['plans'].get(context['plan_key'])
    if not plan or plan['status'] in {'played', 'cancelled', 'missed'}: return
    plan['status'] = status
    hype = context.get('final_hype', 0)
    result = {'day': context['day'], 'event': event.name, 'event_id': event.event_id, 'status': status, 'paid': paid,
              'hype': hype, 'sound': context['sound_bonus'], 'merch_ready': context['merch_ready']}
    data['history'].append(result)
    data['last_result'] = result
    npc = game.NPC_REGISTRY[data['host_id']]
    change = (3 if hype >= 60 else 1 if hype >= 35 else -2) if status == 'played' else -3
    change -= min(4, context.get('late_minutes',0)//15)
    npc.update_relationship(change)
    npc.add_memory(f"{game.player.name}'s last show at {event.location.name}: {status}, crowd response {hype:.0f}/100.")
    game.world_memory.add(WorldMemoryEntry('club_night', [game.player.name, npc.npc_id], event.location.name,
        current_game_time.copy(), tags=['venue', 'performance'], impact_score=change, metadata=result,
        source_key=f"club:{context['plan_key']}"))
