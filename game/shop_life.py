"""Persistent people and minute-by-minute activity for playable music shops.

All save data is plain data on the canonical POI. This controller is disposable.
"""
import random
from game.npc import NPC
from game.game_time import current_game_time
from game.world_memory import WorldMemoryEntry
from game_data.gear_catalog import GEAR_CATALOG


class ShopLife:
    def __init__(self, game, poi):
        self.game, self.poi, self.player = game, poi, game.player
        self.interruption = None
        if getattr(poi, 'category', '') != 'SHOP_MUSIC' or self.player.current_poi is not poi:
            raise ValueError('Enter the music shop before interacting with it.')
        if not hasattr(poi, 'shop_life'):
            rng = random.Random(poi.poi_id)
            names = rng.sample(['Mara', 'Dev', 'Jules', 'Ren', 'Ellis', 'Nico', 'Sam', 'Imani', 'Luca', 'Kit'], 3)
            owner_id = getattr(poi, 'owner_npc_id', None)
            if hasattr(owner_id, 'npc_id'):
                owner_id = owner_id.npc_id
            if owner_id not in game.NPC_REGISTRY:
                owner_id = f'shop_host:{poi.poi_id}'
                game.NPC_REGISTRY[owner_id] = NPC(owner_id, rng.choice(['Robin', 'Casey', 'Morgan']), 'friendly', home_location=poi)
            ids = []
            for i, name in enumerate(names):
                key = f'shop_regular:{poi.poi_id}:{i}'
                npc = NPC(key, name, 'friendly', home_location=poi, current_location=poi)
                npc.role_tags.add('shop_regular')
                npc.shop_interest = ['demo', 'collector', 'fan'][i]
                game.NPC_REGISTRY[key] = npc
                ids.append(key)
            poi.shop_life = {'host_id': owner_id, 'regular_ids': ids, 'reputation': 0,
                             'visited_days': [], 'active': None, 'last_result': None}
        self.data = poi.shop_life

    @property
    def active(self):
        return self.data['active']

    @property
    def host(self):
        return self.game.NPC_REGISTRY[self.data['host_id']]

    def visitors(self):
        ids = self.data['regular_ids']
        # Two locals have regular spots; the third drops in on alternate days.
        present = ids[:2] + (ids[2:] if current_game_time.day_index() % 2 == 0 else [])
        return [self.game.NPC_REGISTRY[key] for key in present]

    def enter(self):
        day = current_game_time.day_index()
        if day not in self.data['visited_days']:
            self.data['visited_days'] = (self.data['visited_days'] + [day])[-30:]
            self.log(f"The bell rings at {self.poi.name}. {self.host.name} looks up from the counter.")

    def log(self, text):
        self.game.GAME_LOG.add_log_message(text)

    def greeting(self, npc):
        if npc is self.host:
            result = self.data['last_result']
            if result:
                return (f"Last time, {result['met']} people reached your table and {result['left']} left without a signature. "
                        + ('People have been asking when you will return.' if self.data['reputation'] >= 0 else 'We need to handle the crowd better before doing that again.'))
            return 'The counter is covered in repair slips. "Looking for something, or just stopping by?"'
        if npc.memories:
            return npc.memories[-1]
        return {'demo': 'They are turning a homemade cassette over in their hands. "I recorded this in my bedroom."',
                'collector': 'They are searching the used bins. "The records you keep coming back to tell you something."',
                'fan': 'They glance from the flyers to you. "Are you playing around here?"'}[npc.shop_interest]

    def talk(self, npc_id, kind='chat'):
        npc = self.game.NPC_REGISTRY.get(npc_id)
        if npc is None or npc_id not in [self.data['host_id']] + [n.npc_id for n in self.visitors()]:
            return False
        day = current_game_time.day_index()
        if getattr(npc, 'last_shop_chat_day', -1) == day:
            self.log(f'{npc.name}: "Catch you next time."')
            return False
        npc.last_shop_chat_day = day
        minutes = 10 if kind == 'listen' else 5
        npc.update_relationship(4 if kind == 'listen' else 2)
        message = (f'{npc.name} remembers you taking time to listen to their demo.' if kind == 'listen'
                   else f'{npc.name} remembers catching up with you among the records.')
        npc.add_memory(message)
        self.player.inspiration = min(100, self.player.inspiration + (3 if kind == 'listen' else 1))
        self.elapse(minutes, at_table=False)
        self.log(message)
        return True

    def invitation(self):
        day = current_game_time.day_index()
        history = [h for h in getattr(self.player, 'appearance_history', []) if h['city'] == self.player.current_location.name]
        cooldown = 14 if self.data['reputation'] < -5 else 7
        if history and day - max(h['day'] for h in history) < cooldown:
            return False, f'We leave {cooldown} days between appearances in town. Give people time to want another visit.'
        offer = self.player.active_opportunities.get('autograph_signing', {})
        invited = offer.get('status') == 'available' and offer.get('poi_id', self.poi.poi_id) == self.poi.poi_id
        if not (invited or self.player.current_tour_id or any(s.is_released for s in self.player.songs_written)):
            return False, 'Bring us a released record or a tour date to put on the flyer, and we can talk about a signing.'
        return True, 'We can give you the table for ninety minutes. Signing is free; bring your own merchandise to sell.'

    def start_signing(self, policy):
        if policy not in {'personal', 'brisk', 'merch'} or self.active:
            return False
        allowed, explanation = self.invitation()
        if not allowed:
            self.log(explanation)
            return False
        rng = random.Random(f'{self.player.name}:{self.poi.poi_id}:{current_game_time.day_index()}')
        goodwill = sum(max(0, self.game.NPC_REGISTRY[key].relationship_score) for key in self.data['regular_ids'])
        turnout = max(3, min(100, int(self.player.fame * .18 + self.player.street_cred * .12)
                            + rng.randint(-3, 6) + min(12, goodwill // 4) + self.data['reputation'] // 3))
        regulars = [n.npc_id for n in self.visitors()]
        queue = regulars + [f'visitor:{i}' for i in range(max(0, turnout - len(regulars)))]
        queue = queue[:turnout]
        state = {'city': self.player.current_location.name, 'day': current_game_time.day_index(), 'venue': self.poi.name,
                 'turnout': turnout, 'queue': queue, 'met': 0, 'left': 0, 'waiting': turnout,
                 'goodwill': 0, 'revenue': 0, 'units_sold': 0, 'minutes': 0, 'decisions': [policy],
                 'policy': policy, 'service_credit': 0., 'buyer_credit': 0., 'met_ids': [], 'left_ids': [],
                 'pending': None, 'moments': [], 'limit': 90, 'away_minutes': 0,
                 'last_clock': current_game_time.copy()}
        self.data['active'] = state
        self.player.active_opportunities['autograph_signing'] = {'status': 'available', 'poi_id': self.poi.poi_id}
        self.log(f"{turnout} people have come for the signing. {self.host.name} opens the line.")
        return True

    def _remember_fan(self, npc_id, met, personal=False):
        npc = self.game.NPC_REGISTRY.get(npc_id)
        if not npc:
            return
        npc.update_relationship((3 if personal else 1) if met else -2)
        npc.add_memory(f"{npc.name} remembers " + ('a real conversation at your signing.' if met and personal else
                       'getting a signature at your signing.' if met else 'leaving your signing without reaching the table.'))

    def _sell(self):
        s = self.active
        if s['buyer_credit'] < 1:
            return
        # One purchase per willing buyer; high prices lose half the demand.
        s['buyer_credit'] -= 1
        for item in self.player.merch_stock:
            count = 'unit_count' if hasattr(item, 'unit_count') else 'stock'
            price = getattr(item, 'suggested_price', getattr(item, 'sale_price', 0))
            if getattr(item, count, 0) > 0 and price > 0:
                if price > 25 and s['met'] % 2:
                    return
                setattr(item, count, getattr(item, count) - 1)
                self.player.money += price
                s['revenue'] += price
                s['units_sold'] += 1
                return

    def _minute(self, at_table):
        s = self.active
        s['minutes'] += 1
        if at_table:
            pace = {'personal': 4, 'brisk': 2, 'merch': 3}[s['policy']]
            condition = max(.35, min(1, self.player.energy / 45)) * (1 - self.player.stress / 250)
            s['service_credit'] += condition / pace
            while s['service_credit'] >= 1 and s['queue']:
                key = s['queue'].pop(0)
                s['service_credit'] -= 1
                s['met'] += 1
                s['met_ids'].append(key)
                s['goodwill'] += 2 if s['policy'] == 'personal' else 1
                self._remember_fan(key, True, s['policy'] == 'personal')
                s['buyer_credit'] += .6 if s['policy'] == 'merch' else .25
                self._sell()
            self.player.energy = max(0, self.player.energy - 1 / 6)
        else:
            s['away_minutes'] += 1
        self.player.stress = min(100, self.player.stress + len(s['queue']) / 360)
        if s['queue'] and s['minutes'] >= 45 and s['minutes'] % 10 == 0:
            count = max(1, int(len(s['queue']) * .06))
            for _ in range(min(count, len(s['queue']))):
                key = s['queue'].pop()
                s['left_ids'].append(key)
                s['left'] += 1
                self._remember_fan(key, False)
            self.log(f"{count} people leave the queue. {len(s['queue'])} are still waiting.")
        s['waiting'] = len(s['queue'])
        if s['minutes'] >= 20 and 'fan' not in s['moments'] and s['queue']:
            s['pending'] = 'fan'
        elif s['minutes'] >= 60 and 'queue' not in s['moments'] and s['queue']:
            s['pending'] = 'queue'
        elif s['minutes'] >= s['limit']:
            s['pending'] = 'closing'

    def elapse(self, minutes, at_table=True, interruptible=False):
        """Advance world and activity together. Inspecting a paused room is free."""
        elapsed = 0
        for _ in range(max(0, int(minutes))):
            if self.active and self.active['pending'] and interruptible:
                break
            upcoming = self.player.schedule.get_upcoming_events(current_game_time.copy(), limit=1)
            starting = upcoming[0] if upcoming and round(upcoming[0].start_time.days_difference(current_game_time)*1440) == 1 else None
            self.game._advance_time_with_needs(1)
            elapsed += 1
            if self.active:
                self._minute(at_table)
                self.active['last_clock'] = current_game_time.copy()
                if not self.active['queue']:
                    self.finish()
                    break
                if self.active['minutes'] >= self.active['limit'] and not interruptible:
                    self.finish()
                    break
            if starting and interruptible:
                self.interruption = f'Calendar: {starting.description} is starting. You are still at {self.poi.name}.'
                self.log(self.interruption)
                break
        return elapsed

    def decide(self, choice):
        s = self.active
        if not s:
            return False
        moment = s['pending']
        allowed = {'fan': {'listen', 'brief'}, 'queue': {'brisk', 'personal'}, 'closing': {'extend', 'close'}}
        if choice not in allowed.get(moment, set()):
            return False
        if moment == 'closing' and (choice == 'close' or s['limit'] >= 120):
            self.finish()
            return True
        s['moments'].append(moment)
        s['decisions'].append(choice)
        s['pending'] = None
        if moment == 'fan':
            npc = self.game.NPC_REGISTRY[self.data['regular_ids'][0]]
            if choice == 'listen':
                npc.update_relationship(5)
                npc.add_memory(f'{npc.name} remembers you listening to their demo while the signing queue waited.')
                s['goodwill'] += 6
                self.player.inspiration = min(100, self.player.inspiration + 3)
                self.elapse(10, at_table=False)
            else:
                npc.add_memory(f'{npc.name} remembers a brief word while you kept the signing line moving.')
        elif moment == 'queue':
            s['policy'] = choice
        else:
            s['limit'] = 120
        return True

    def finish(self):
        s = self.active
        if not s:
            return None
        for key in s['queue']:
            self._remember_fan(key, False)
        s['left_ids'].extend(s['queue'])
        s['left'] += len(s['queue'])
        s['queue'] = []
        s['waiting'] = 0
        fame = max(-4, min(8, int((s['met'] - s['left'] * .6) / 5)))
        cred = max(-5, min(5, int((s['goodwill'] - s['left']) / 8)))
        s.update(fame_change=fame, cred_change=cred)
        self.player.fame = max(0, self.player.fame + fame)
        self.player.street_cred = max(0, min(100, self.player.street_cred + cred))
        self.player.appearance_history = getattr(self.player, 'appearance_history', []) + [dict(s)]
        self.data['reputation'] = max(-20, min(20, self.data['reputation'] + cred))
        self.host.update_relationship(cred)
        self.data['last_result'] = dict(s)
        self.player.active_opportunities['autograph_signing']['status'] = 'completed'
        self.game.world_memory.add(WorldMemoryEntry('public_appearance', [self.player.name, self.host.npc_id], s['city'],
            current_game_time.copy(), tags=['fans', 'signing', 'shop'], impact_score=cred, metadata=dict(s),
            source_key=f"signing:{self.player.name}:{self.poi.poi_id}:{s['day']}"))
        self.data['active'] = None
        self.log(f"Table closed: {s['met']} met you, {s['left']} left; ${s['revenue']} sales. Fame {fame:+}, credibility {cred:+}.")
        return s

    def buy(self, item_id):
        item = GEAR_CATALOG.get(item_id)
        if item_id not in (self.poi.shop_inventory_item_ids or []) or item is None:
            return False
        if self.player.money < item.cost:
            self.log('You cannot cover that price. No payment taken.')
            return False
        if not self.player.can_carry_gear(item):
            self.log('There is no room in your loadout. No payment taken.')
            return False
        self.player.money -= item.cost
        self.player.add_gear(item)
        self.elapse(5, at_table=False)
        self.log(f'Bought {item.name} for ${item.cost}.')
        return True
