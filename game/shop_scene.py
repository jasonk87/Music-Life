"""A walkable Pygame shop. The room remains visible during conversations."""
from collections import deque
import math
import pygame
from game.shop_life import ShopLife
from game.music_interface import INK, PAPER, MUTED, AMBER, TEAL, LINE
from game.game_time import current_game_time
from game_data.gear_catalog import GEAR_CATALOG

FLOOR = pygame.Rect(44, 225, 724, 348)
SOLIDS = [pygame.Rect(64, 225, 222, 58), pygame.Rect(317, 329, 139, 104),
          pygame.Rect(590, 237, 141, 63), pygame.Rect(60, 423, 136, 48)]
ANCHORS = {'host': (151, 301), 'records': (384, 458), 'table': (650, 321),
           'repairs': (270, 309), 'door': (731, 542)}
OBJECT_HITS = [('repairs', pygame.Rect(243,225,43,58)), ('records', SOLIDS[1]),
               ('table', SOLIDS[2]), ('host', SOLIDS[0]), ('door', pygame.Rect(703,537,57,36))]


def walkable(point, solids=SOLIDS):
    return FLOOR.inflate(-18, -18).collidepoint(point) and not any(r.inflate(18, 18).collidepoint(point) for r in solids)


def find_path(start, target, solids=SOLIDS):
    """Small four-way navigation grid; furniture is solid for mouse and keys."""
    cell = 14
    def grid(p): return (round((p[0] - FLOOR.x) / cell), round((p[1] - FLOOR.y) / cell))
    def pixel(g): return (FLOOR.x + g[0] * cell, FLOOR.y + g[1] * cell)
    a, b = grid(start), grid(target)
    if not walkable(pixel(b), solids):
        return []
    queue, parent = deque([a]), {a: None}
    while queue:
        node = queue.popleft()
        if node == b:
            route = []
            while node != a:
                route.append(pixel(node)); node = parent[node]
            return list(reversed(route))
        for dx, dy in ((0, 1), (1, 0), (-1, 0), (0, -1)):
            neighbor = (node[0] + dx, node[1] + dy)
            if neighbor not in parent and walkable(pixel(neighbor), solids):
                parent[neighbor] = node; queue.append(neighbor)
    return []


class ShopScene:
    life_type = ShopLife
    scene_state = 'shop_scene'
    solids = SOLIDS
    object_hits = OBJECT_HITS
    people = {'host'}

    def __init__(self, game, poi):
        self.game, self.ui = game, game.ui
        self.life = self.life_type(game, poi)
        self.life.enter()
        self.position = pygame.Vector2(self.life.data.get('player_position', ANCHORS['table'] if self.life.active else (696, 522)))
        self.path = []
        self.destination_action = None
        self.focus = 'table' if self.life.active else 'host'
        self.speed = 0
        self.accumulator = 0.
        self.animation = 0.
        self.dialog = None
        self.buttons = []
        self.closed = False
        self.notice = 'The bell above the door settles. A record is turning behind the counter.'
        self.last_log = None
        self.next_state = None

    def targets(self):
        result = {key: {'pos': value, 'name': label} for key, value, label in [
            ('host', ANCHORS['host'], self.life.host.name), ('records', ANCHORS['records'], 'Record bins & gear'),
            ('table', ANCHORS['table'], 'Signing table'), ('repairs', ANCHORS['repairs'], 'Repair bench'),
            ('door', ANCHORS['door'], 'Front door')]}
        s = self.life.active
        for i, npc in enumerate(self.life.visitors()):
            if s and npc.npc_id in s['left_ids']:
                continue
            pos = [(230, 390), (485, 466), (240, 508)][i]
            if s and npc.npc_id in s['queue']:
                pos = self.queue_position(s['queue'].index(npc.npc_id))
            if s and s['pending'] == 'fan' and i == 0:
                pos = (555, 319)
            result[npc.npc_id] = {'pos': pos, 'name': npc.name}
        return result

    @staticmethod
    def queue_position(index):
        return (648 - (index // 6) * 39, 353 + (index % 6) * 31)

    def approach(self, key):
        target = self.targets().get(key)
        if not target:
            return
        self.focus = key
        point = target['pos']
        if key in self.people or key in self.game.NPC_REGISTRY:
            candidates = [(point[0]+dx,point[1]+dy) for dx,dy in [(24,0),(-24,0),(0,24),(0,-24)]]
            point = min((p for p in candidates if walkable(p, self.solids)), key=lambda p:self.position.distance_to(p), default=point)
        self.path = find_path(self.position, point, self.solids)
        self.destination_action = key
        if not self.path and self.position.distance_to(target['pos']) < 30:
            self.destination_action = None
            self.interact(key)

    def open_dialog(self, title, text, choices):
        self.speed = 0
        self.accumulator = 0
        self.path = []
        self.destination_action = None
        self.dialog = {'title': title, 'text': text, 'choices': choices}

    def dismiss(self):
        self.dialog = None

    def interact(self, key):
        self.focus = key
        self.speed = 0
        if key == 'host':
            allowed, terms = self.life.invitation()
            choices = [('Catch up / 5 min', lambda: self.chat(self.life.host.npc_id)),
                       ('Ask about the signing table', self.signing_terms), ('Back to the room', self.dismiss)]
            self.open_dialog(self.life.host.name, self.life.greeting(self.life.host), choices)
        elif key == 'table':
            if self.life.active:
                if self.life.active['pending']:
                    self.show_moment()
                else:
                    self.open_dialog('At the signing table', 'Choose a pace and let the line move. You can pause or step away at any time.', [
                        ('Personal conversations', lambda: self.policy('personal')),
                        ('Names and signatures', lambda: self.policy('brisk')),
                        ('Sign and sell merchandise', lambda: self.policy('merch')),
                        ('Close the table', self.close_signing), ('Back to the room', self.dismiss)])
            else:
                self.signing_terms()
        elif key == 'records':
            stock = [GEAR_CATALOG[k] for k in (self.life.poi.shop_inventory_item_ids or []) if k in GEAR_CATALOG]
            choices = [(f'{item.name} / ${item.cost}', lambda k=item.item_id: self.review_purchase(k)) for item in stock]
            self.open_dialog('Under the counter', 'The shop carries these instruments and supplies. Purchases take five minutes.',
                             choices + [('Back to the room', self.dismiss)])
        elif key == 'repairs':
            worn = [g for g in self.game.player.gear_inventory if g.durability < 100]
            self.open_dialog('Repair bench', 'A basic service costs $10 per instrument and takes fifteen minutes.',
                [(f'{g.name} / {g.durability:.0f}%', lambda gear=g: self.repair(gear)) for g in worn]
                + [('Back to the room', self.dismiss)])
        elif key == 'door':
            if self.life.active:
                self.open_dialog('Leave the shop?', 'The signing is still underway. Leaving closes the table; people still waiting will go home.', [
                    ('Close the table and leave', self.leave), ('Stay in the shop', self.dismiss)])
            else:
                self.closed = True
        else:
            npc = self.game.NPC_REGISTRY.get(key)
            if npc:
                choices = [('Catch up / 5 min', lambda: self.chat(key))]
                if getattr(npc, 'shop_interest', '') == 'demo':
                    choices.insert(0, ('Listen to the demo / 10 min', lambda: self.chat(key, 'listen')))
                self.open_dialog(npc.name, self.life.greeting(npc), choices + [('Back to the room', self.dismiss)])

    def chat(self, key, kind='chat'):
        self.life.talk(key, kind)
        self.notice = self.life.greeting(self.game.NPC_REGISTRY[key])
        self.dismiss()
        self.after_action()

    def signing_terms(self):
        allowed, terms = self.life.invitation()
        self.open_dialog('An afternoon in store', terms, ([('Set up the table', self.choose_start)] if allowed else [])
                         + [('Back to the room', self.dismiss)])

    def choose_start(self):
        self.open_dialog('Set the pace', 'Personal attention takes longer. A brisk table reaches more people. Merchandising uses your real stock.', [
            ('Personal conversations', lambda: self.begin('personal')),
            ('Names and signatures', lambda: self.begin('brisk')),
            ('Sign and sell merchandise', lambda: self.begin('merch')),
            ('Decide later', self.dismiss)])

    def begin(self, policy):
        if self.life.start_signing(policy):
            self.position.update(ANCHORS['table'])
            self.focus = 'table'
            self.notice = 'The first people come to the table. Your chosen pace carries the routine work.'
            self.dismiss()
            self.speed = 1

    def policy(self, policy):
        if self.life.active:
            self.life.active['policy'] = policy
            self.life.active['decisions'].append(policy)
        self.position.update(ANCHORS['table'])
        self.dismiss()
        self.speed = 1

    def show_moment(self):
        s = self.life.active
        if not s or not s['pending']:
            return
        moment = s['pending']
        if moment == 'fan':
            name = self.game.NPC_REGISTRY[self.life.data['regular_ids'][0]].name
            self.open_dialog(f'{name} comes back over', 'They have a cassette they made at home. "Would you have ten minutes to listen?" The rest of the line is watching.', [
                ('Listen together / 10 min', lambda: self.resolve('listen')),
                ('Have a brief word; keep signing', lambda: self.resolve('brief'))])
        elif moment == 'queue':
            self.open_dialog('Voices from the back', f"{s['waiting']} people are still waiting. Some have started looking at the door. There are {s['limit']-s['minutes']} minutes left.", [
                ('Switch to one signature each', lambda: self.resolve('brisk')),
                ('Keep making time for people', lambda: self.resolve('personal'))])
        else:
            choices = [('Close the table', lambda: self.resolve('close'))]
            if s['limit'] < 120:
                choices.insert(0, ('Stay another half hour', lambda: self.resolve('extend')))
            self.open_dialog('The session is over', f"{s['waiting']} people have not reached the table. {self.life.host.name} is stacking chairs.", choices)

    def resolve(self, choice):
        self.life.decide(choice)
        self.dismiss()
        self.after_action()
        # Resume only after the player chooses a speed; decisions do not run
        # the next stretch while they are reading its outcome.

    def close_signing(self):
        self.open_dialog('Close the table?', 'Anyone still waiting will leave without meeting you.', [
            ('Close now', lambda: self.resolve_close()), ('Keep the table open', self.dismiss)])

    def resolve_close(self):
        self.life.finish()
        self.dismiss()
        self.after_action()

    def leave(self):
        self.life.finish()
        self.closed = True

    def review_purchase(self, key):
        item = GEAR_CATALOG[key]
        self.open_dialog(item.name, f'{item.description}\n\n${item.cost} / size {item.size}.', [
            ('Buy / 5 min', lambda: self.purchase(key)), ('Back', lambda: self.interact('records'))])

    def purchase(self, key):
        self.life.buy(key)
        self.dismiss()
        self.after_action()

    def repair(self, gear):
        if self.game.player.money < 10:
            self.notice = 'The service costs $10. No payment taken.'
        else:
            self.game.player.money -= 10
            gear.repair()
            self.life.elapse(15, at_table=False)
            self.notice = f'{gear.name} has been serviced. Paid $10.'
        self.dismiss()
        self.after_action()

    def phone(self):
        self.open_dialog('Phone', 'Reading is free. Committed calls and booking work use time; the signing queue keeps waiting.', [
            ('Calendar', self.calendar), ('Call a contact', self.contacts),
            ('Live bookings', self.bookings), ('Put phone away', self.dismiss)])

    def calendar(self):
        items = self.game.player.schedule.scheduled_items
        self.open_dialog('Calendar', '\n\n'.join(str(e) for e in items[:3]) or 'No commitments.', [
            ('Read full calendar', self.full_calendar), ('Back to phone', self.phone)])

    def full_calendar(self):
        self.ui.interface.read_document('Calendar', '\n\n'.join(str(e) for e in self.game.player.schedule.scheduled_items) or 'No commitments.')

    def contacts(self):
        from game.phone_actions import choose_contact
        choose_contact(self.game, lambda minutes: self.life.elapse(minutes, at_table=False))
        self.dismiss()
        self.after_action()

    def bookings(self):
        from game.live_bookings import booking_desk
        before = repr(self.game.player.tour_ledgers)
        booking_desk(self.game)
        if repr(self.game.player.tour_ledgers) != before:
            self.life.elapse(15, at_table=False)
        self.dismiss()
        self.after_action()

    def after_action(self):
        if self.life.active and self.life.active['pending']:
            self.show_moment()
        elif not self.life.active and self.life.data['last_result']:
            s = self.life.data['last_result']
            self.notice = f"After the signing: {s['met']} met you, {s['left']} left. ${s['revenue']} from {s['units_sold']} items."

    def update(self, seconds):
        self.animation += seconds
        if self.dialog:
            return
        distance = 175 * seconds
        while self.path and distance > 0:
            point = pygame.Vector2(self.path[0])
            delta = point - self.position
            length = delta.length()
            if length <= distance:
                self.position = point; self.path.pop(0); distance -= length
            else:
                self.position += delta.normalize() * distance; distance = 0
        if not self.path and self.destination_action:
            action = self.destination_action; self.destination_action = None
            target = self.targets().get(action)
            if target and self.position.distance_to(target['pos']) > 42:
                self.approach(action)
            elif target:
                self.interact(action)
            return
        if self.speed:
            self.accumulator += seconds * self.speed
            count = min(12, int(self.accumulator))
            if count:
                self.accumulator -= count
                active_before = self.life.active
                at_table = self.position.distance_to(ANCHORS['table']) < 37 and not self.path
                self.life.elapse(count, at_table, interruptible=True)
                logs = getattr(self.ui, 'log_messages', [])
                if logs and logs[0] != self.last_log:
                    self.notice = str(logs[0]); self.last_log = logs[0]
                if (self.life.active and self.life.active['pending']) or (active_before and not self.life.active):
                    self.speed = 0; self.accumulator = 0
                    self.after_action()
                if self.life.interruption:
                    self.speed = 0; self.accumulator = 0
                    self.notice = self.life.interruption
                    self.life.interruption = None
                if self.game.player.energy < 15 or self.game.player.hunger >= 85:
                    self.speed = 0
                    self.notice = 'You stop for a moment. Your body is catching up with the day.'

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            pygame.quit(); raise SystemExit
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for rect, callback in self.buttons:
                if rect.collidepoint(event.pos):
                    callback(); return
            if self.dialog:
                return
            for key, target in self.targets().items():
                if pygame.Vector2(target['pos']).distance_to(event.pos) < 28:
                    self.approach(key); return
            for key, rect in self.object_hits:
                if rect.collidepoint(event.pos):
                    self.approach(key); return
            if walkable(event.pos, self.solids):
                self.path = find_path(self.position, event.pos, self.solids); self.destination_action = None
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F5:
                self.speed = 0
                self.life.data['player_position'] = list(self.position)
                self.game.quick_save()
                return
            if self.dialog:
                if pygame.K_1 <= event.key <= pygame.K_9:
                    index = event.key - pygame.K_1
                    if index < min(4, len(self.dialog['choices'])): self.dialog['choices'][index][1]()
                elif event.key == pygame.K_ESCAPE:
                    self.dismiss()
                return
            if event.key == pygame.K_SPACE:
                if self.life.active and self.life.active['pending']:
                    self.show_moment()
                else:
                    self.speed = 0 if self.speed else 1
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                if self.life.active and self.life.active['pending']:
                    self.show_moment()
                else:
                    self.speed = {pygame.K_1: 1, pygame.K_2: 4, pygame.K_3: 12}[event.key]
            elif event.key == pygame.K_p:
                self.phone()
            elif event.key == pygame.K_j:
                self.speed = 0
                self.ui.interface.read_document('Journal', '\n\n'.join(self.ui.log_messages))
            elif event.key == pygame.K_TAB:
                keys = list(self.targets())
                self.focus = keys[(keys.index(self.focus) + 1) % len(keys)] if self.focus in keys else keys[0]
            elif event.key == pygame.K_RETURN:
                self.approach(self.focus)
            elif event.key == pygame.K_e:
                nearby = [(pygame.Vector2(t['pos']).distance_to(self.position), key) for key, t in self.targets().items()]
                distance, key = min(nearby)
                if distance < 42: self.interact(key)
            elif event.key == pygame.K_ESCAPE:
                self.interact('door')

    def move_keys(self, seconds):
        if self.dialog:
            return
        keys = pygame.key.get_pressed()
        dx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
        if dx or dy:
            self.path = []; self.destination_action = None
            vector = pygame.Vector2(dx, dy).normalize() * 150 * seconds
            for axis in (0, 1):
                point = self.position.copy(); point[axis] += vector[axis]
                if walkable(point, self.solids): self.position = point

    def run(self):
        previous_state = self.game.game_state
        self.game.game_state = self.scene_state
        clock = pygame.time.Clock()
        try:
            if self.life.active and self.life.active['pending']: self.show_moment()
            while not self.closed:
                seconds = min(.1, clock.tick(60) / 1000)
                self.move_keys(seconds)
                self.update(seconds)
                self.draw()
                self.ui.update_display()
                for event in pygame.event.get(): self.handle_event(event)
        finally:
            if self.closed:
                self.life.data.pop('player_position', None)
            self.game.game_state = self.next_state or previous_state

    def text(self, text, x, y, color=PAPER, font=None, width=None, lines=1):
        return self.ui.interface.text(text, x, y, color, font, width, lines)

    def sprite(self, pos, color, label=None, selected=False, player=False):
        x, y = map(int, pos)
        surface = self.ui.screen
        pygame.draw.ellipse(surface, (38, 32, 31), (x-13, y+7, 26, 10))
        if selected: pygame.draw.ellipse(surface, AMBER, (x-18, y+5, 36, 15), 2)
        pygame.draw.rect(surface, (32, 37, 42), (x-7, y+1, 5, 12), border_radius=2)
        pygame.draw.rect(surface, (32, 37, 42), (x+2, y+1, 5, 12), border_radius=2)
        pygame.draw.rect(surface, color, (x-10, y-17, 20, 23), border_radius=6)
        pygame.draw.circle(surface, (197, 154, 122), (x, y-22), 8)
        pygame.draw.arc(surface, (58, 43, 38), (x-9, y-31, 18, 17), 0, math.pi, 6)
        if player: pygame.draw.rect(surface, PAPER, (x-5, y-12, 3, 12))
        if label:
            font = self.ui.FONT_SMALL
            width = font.size(label)[0]
            box = pygame.Rect(x-width//2-5, y-53, width+10, 20)
            pygame.draw.rect(surface, INK, box, border_radius=3)
            self.text(label, box.x+5, box.y+1, AMBER if selected else PAPER, font)

    def draw_room(self):
        surface = self.ui.screen
        pygame.draw.rect(surface, (23, 38, 42), (24, 174, 760, 413), border_radius=6)
        pygame.draw.rect(surface, (107, 78, 56), FLOOR)
        # Staggered timber flooring, bounded to the room.
        for row, y in enumerate(range(225, 573, 24)):
            pygame.draw.line(surface, (85, 63, 49), (44, y), (768, y))
            for x in range(44 + (row % 2) * 56, 768, 112):
                pygame.draw.line(surface, (91, 67, 51), (x, y), (x, min(y+24, 573)))
        for x in (79, 195, 311):
            pygame.draw.rect(surface, (43, 65, 66), (x, 184, 98, 33))
            pygame.draw.rect(surface, (136, 159, 151), (x+3, 187, 92, 26), 1)
        self.text('RECORDS  /  REPAIRS  /  LOCAL MUSIC', 83, 193, PAPER, self.ui.FONT_SMALL)
        for x, color in [(474, AMBER), (520, TEAL), (563, (167, 98, 79))]:
            pygame.draw.line(surface, (153, 132, 97), (x, 183), (x, 205), 5)
            pygame.draw.ellipse(surface, color, (x-10, 200, 21, 20))
            pygame.draw.circle(surface, INK, (x, 207), 3)
        self.text('IN STORE', 649, 193, AMBER, self.ui.FONT_SMALL)
        for rect in SOLIDS:
            pygame.draw.rect(surface, (65, 44, 35), rect.move(0, 9), border_radius=3)
            pygame.draw.rect(surface, (151, 110, 76), rect, border_radius=3)
            pygame.draw.line(surface, (189, 150, 104), rect.topleft, rect.topright, 3)
        # Counter: turntable, till and stacked sleeves.
        pygame.draw.rect(surface, (34, 43, 43), (83, 239, 65, 32), border_radius=3)
        pygame.draw.circle(surface, (14, 21, 24), (105, 255), 13)
        pygame.draw.circle(surface, AMBER, (105, 255), 4)
        angle = self.animation * 1.5
        pygame.draw.line(surface, MUTED, (105,255), (105+int(math.cos(angle)*11),255+int(math.sin(angle)*11)))
        pygame.draw.rect(surface, (46, 56, 53), (220, 239, 39, 27), border_radius=2)
        pygame.draw.rect(surface, TEAL, (225, 243, 27, 10))
        pygame.draw.line(surface, PAPER, (267,244),(277,267), 3)
        pygame.draw.circle(surface, LINE, (266,242), 5, 2)
        # Two rows of browsing bins with individual record sleeves.
        sleeve_colors = [TEAL, AMBER, (173, 101, 88), (87, 112, 128), (188, 170, 129)]
        for row in range(2):
            for col in range(8):
                x, y = 328+col*15, 343+row*44
                pygame.draw.polygon(surface, sleeve_colors[(row*3+col)%5], [(x,y+27),(x+12,y+27),(x+12,y),(x,y+3)])
                pygame.draw.line(surface, INK, (x+3,y+8),(x+9,y+8))
        self.text('USED  /  NEW', 342, 408, INK, self.ui.FONT_SMALL)
        # Listening couch and signing desk.
        pygame.draw.rect(surface, (54, 91, 85), (65, 426, 126, 38), border_radius=8)
        for x in (72, 112, 152): pygame.draw.rect(surface, (71, 107, 95), (x,430,33,27), border_radius=4)
        pygame.draw.rect(surface, PAPER, (613, 251, 43, 29))
        pygame.draw.line(surface, INK, (620,272), (645,257), 2)
        pygame.draw.rect(surface, (92, 61, 50), (681, 249, 34, 31))
        for x in range(684, 711, 6): pygame.draw.line(surface, AMBER, (x,252),(x,276),2)
        pygame.draw.rect(surface, (43, 58, 56), (703, 537, 57, 34), border_radius=3)
        self.text('EXIT', 717, 547, PAPER, self.ui.FONT_SMALL)
        s = self.life.active
        if s:
            for i, key in enumerate(s['queue'][:12]):
                if key not in self.game.NPC_REGISTRY:
                    self.sprite(self.queue_position(i), sleeve_colors[i%5])
            if len(s['queue']) > 12:
                self.text(f"+ {len(s['queue'])-12} outside", 570, 552, PAPER, self.ui.FONT_SMALL)
        for key, target in self.targets().items():
            if key in {'host'} or key in self.game.NPC_REGISTRY:
                colors = [(156,111,97), (112,140,161), (184,165,114)]
                color = (120,135,98) if key == 'host' else colors[self.life.data['regular_ids'].index(key) % len(colors)]
                self.sprite(target['pos'], color, target['name'], self.focus == key)
            elif self.focus == key:
                x,y = target['pos']
                pygame.draw.ellipse(surface, AMBER, (x-22, y-9, 44, 18), 2)
                self.text(target['name'], x-55, 282 if key == 'table' else y+13, PAPER, self.ui.FONT_SMALL, 135)
        for point in self.path[::2]: pygame.draw.circle(surface, (169,155,118), point, 2)
        nearby_person = any(self.position.distance_to(t['pos']) < 48 for key,t in self.targets().items()
                            if key == 'host' or key in self.game.NPC_REGISTRY)
        self.sprite(self.position, TEAL, None if nearby_person else 'You', player=True)

    def button(self, label, rect, action, active=False):
        pygame.draw.rect(self.ui.screen, (37,58,59) if active else (23,35,42), rect, border_radius=4)
        pygame.draw.rect(self.ui.screen, AMBER if active else LINE, rect, 1, border_radius=4)
        small = rect.height < 30
        self.text(label, rect.x+11, rect.y+(3 if small else 8), PAPER,
                  self.ui.FONT_SMALL if small else self.ui.FONT_LOG, rect.width-20, 2)
        self.buttons.append((rect, action))

    def set_speed(self, speed):
        if self.dialog:
            return
        if self.life.active and self.life.active['pending']:
            self.show_moment()
        else:
            self.speed = speed

    def draw(self):
        surface = self.ui.screen
        surface.fill(INK)
        self.buttons = []
        self.ui.interface.hud(self.game.player)
        self.text('THE NEIGHBORHOOD / MUSIC SHOP', 24, 102, AMBER, self.ui.FONT_SMALL)
        self.text(self.life.poi.name, 24, 124, PAPER, self.ui.FONT_TITLE, 755)
        self.draw_room()
        pygame.draw.rect(surface, (16,27,34), (801,101,335,488), border_radius=5)
        s = self.life.active
        if self.dialog:
            d = self.dialog
            self.text(d['title'], 818, 117, AMBER, self.ui.FONT_DEFAULT, 297, 2)
            self.text(d['text'], 818, 169, PAPER, self.ui.FONT_LOG, 296, 9)
            count = len(d['choices'])
            # Long shop inventories remain navigable instead of rendering offscreen.
            visible = d['choices'][:4]
            for i, (label, action) in enumerate(visible):
                self.button(f'{i+1}. {label}', pygame.Rect(816, 350+i*54, 304, 50), action)
            if count > 4:
                self.button('More items', pygame.Rect(816, 565, 304, 22), lambda: self.more_choices())
        else:
            self.text('AT THE TABLE' if s else 'A PLACE TO SPEND TIME', 818, 119, AMBER, self.ui.FONT_SMALL)
            if s:
                self.text(f"{s['waiting']} waiting", 818, 151, PAPER, self.ui.FONT_TITLE)
                self.text(f"{s['met']} met you / {s['left']} left", 818, 194, MUTED)
                pygame.draw.rect(surface, LINE, (818, 228, 297, 6))
                pygame.draw.rect(surface, TEAL, (818, 228, int(297*s['met']/max(1,s['turnout'])), 6))
                self.text(f"{s['minutes']} / {s['limit']} minutes", 818, 249, PAPER)
                self.text(f"${s['revenue']} sales / {s['units_sold']} items", 818, 276, MUTED)
                away = self.position.distance_to(ANCHORS['table']) >= 37
                self.text('The line waits while you are away.' if away else f"Pace: {s['policy'].capitalize()}", 818, 315, TEAL, width=293, lines=2)
                self.button('Return to the table', pygame.Rect(816,377,304,42), lambda:self.approach('table'))
            else:
                self.text('The needle finds the groove.', 818, 160, PAPER, width=285, lines=2)
                self.text('People linger over records and repair slips. Walk over to someone or click to approach.', 818, 224, MUTED, width=285, lines=4)
                if self.life.data['last_result']:
                    last = self.life.data['last_result']
                    self.text(f"Last signing: {last['met']} met you. {last['left']} left.", 818, 324, TEAL, width=285, lines=2)
            self.button('Phone  [P]', pygame.Rect(816,434,304,42), self.phone)
            self.button('Calendar', pygame.Rect(816,486,304,42), self.calendar)
            self.text('Click a person / object to approach', 818, 553, MUTED, self.ui.FONT_SMALL, 295)
        state = 'PAUSED' if not self.speed else f'{self.speed}x / 1 game min per second at 1x'
        self.text(state, 24, 598, TEAL, self.ui.FONT_SMALL)
        for i, (label, speed) in enumerate([('Pause',0),('1x',1),('4x',4),('12x',12)]):
            self.button(label, pygame.Rect(439+i*84,594,77,32), lambda value=speed:self.set_speed(value), self.speed==speed)
        self.text(self.notice, 24, 632, MUTED, self.ui.FONT_SMALL, 1110, 1)
        self.text('WASD / arrows Move   E Interact   Tab / Enter Approach   Space Pause   1 / 2 / 3 Speed   F5 Save   Esc Leave', 24, 658, MUTED, self.ui.FONT_SMALL)

    def more_choices(self):
        choices = self.dialog['choices']
        self.dialog['choices'] = choices[4:] + choices[:4]


def run_shop_scene(game, poi):
    ShopScene(game, poi).run()
