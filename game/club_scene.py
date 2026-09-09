"""A club room built on the shop's navigation, input and conversation controls."""
import math
import pygame
from game.shop_scene import ShopScene, FLOOR
from game.club_life import ClubLife
from game.music_interface import INK, PAPER, MUTED, AMBER, TEAL, LINE
from game.game_time import current_game_time

SOLIDS = [pygame.Rect(64,233,268,145), pygame.Rect(592,233,141,84),
          pygame.Rect(590,448,140,43), pygame.Rect(65,444,125,41), pygame.Rect(634,353,97,54)]
ANCHORS = {'stage': (208,404), 'engineer': (542,331), 'host': (544,500),
           'merch': (642,516), 'regular': (405,494), 'rest': (125,510), 'door': (731,548)}


class ClubScene(ShopScene):
    life_type = ClubLife
    scene_state = 'club_scene'
    solids = SOLIDS
    people = {'host','engineer','regular'}
    object_hits = [('stage',SOLIDS[0]), ('engineer',SOLIDS[4]), ('merch',SOLIDS[2]),
                   ('rest',SOLIDS[3]), ('door',pygame.Rect(708,532,48,40))]

    def __init__(self, game, venue):
        super().__init__(game, venue)
        self.focus = 'stage'
        self.notice = 'Cables cross the stage. The room smells of warm amplifiers and old wood.'
        self.performance_view = False

    def targets(self):
        return {key: {'pos': pos, 'name': name} for key,pos,name in [
            ('stage',ANCHORS['stage'],'Stage'), ('engineer',ANCHORS['engineer'],self.game.NPC_REGISTRY[self.life.data['engineer_id']].name),
            ('host',ANCHORS['host'],self.life.host.name), ('merch',ANCHORS['merch'],'Merch table'),
            ('regular',ANCHORS['regular'],self.game.NPC_REGISTRY[self.life.data['regular_ids'][0]].name),
            ('rest',ANCHORS['rest'],'Green room'), ('door',ANCHORS['door'],'Front door')]}

    def interact(self, key):
        self.focus = key
        if key == 'stage':
            event = self.life.event()
            if not event:
                self.open_dialog('The stage', 'No available slot in this room today.', [('Back',self.dismiss)])
                return
            if self.life.plan(event)['status'] in {'played','cancelled','missed'}:
                self.open_dialog('After the set', 'Your slot is closed for tonight. The people in the room will remember how it went.', [('Back to the room',self.dismiss)])
                return
            doors,start,end = self.life.times(event)
            self.open_dialog(event.name,
                f'Doors {doors.hour:02d}:{doors.minute:02d}. Set window {start.hour:02d}:{start.minute:02d}–{end.hour:02d}:{end.minute:02d}. '
                f'{event.songs_required_count} song(s) required. The crowd will lose patience if you leave them waiting.', [
                ('Take the stage',self.stage), ('Talk to the sound engineer',lambda:self.approach_dialog('engineer')),
                ('Back to the room',self.dismiss)])
        elif key == 'engineer':
            plan = self.life.plan()
            text = 'We can check your levels and the monitors. Soundcheck takes twenty-five minutes and some energy.'
            if plan and plan['sound']:
                text = 'Your levels have been checked. ' + ('There is still a hum in the monitor.' if plan['monitor_fault'] and not plan['monitor_resolved'] else 'The monitor is clear.')
            choices = [('Run soundcheck / 25 min',lambda:self.prep('sound'))]
            if plan and plan['monitor_revealed'] and not plan['monitor_resolved']:
                choices.insert(0,('Replace monitor lead / $8, 10 min',lambda:self.prep('monitor')))
            choices += [('Ask your crew to handle it',lambda:self.crew('sound')),('Back to the room',self.dismiss)]
            self.open_dialog(self.targets()['engineer']['name'],text,choices)
        elif key == 'host':
            last = self.life.data['last_result']
            text = (self.life.host.memories[-1] if last else 'The promoter checks the clock, then the door. "I want this room to remember you."')
            self.open_dialog(self.life.host.name,text,[('Catch up / 10 min',lambda:self.chat_role('promoter')),
                ('Review live bookings',self.bookings),('Back to the room',self.dismiss)])
        elif key == 'merch':
            plan = self.life.plan()
            text = ('Your stock is ready for after the set.' if plan and plan['merch_ready'] else
                    'Lay out stock and prices before the show. An unprepared table does not sell automatically in this room.')
            self.open_dialog('Beside the door',text,[('Lay out merchandise / 15 min',lambda:self.prep('merch')),
                ('Ask your crew to set up',lambda:self.crew('merch')),('Back to the room',self.dismiss)])
        elif key == 'regular':
            npc = self.game.NPC_REGISTRY[self.life.data['regular_ids'][0]]
            self.open_dialog(npc.name,npc.memories[-1] if npc.memories else 'They know the room and most of its regulars. "What are you playing tonight?"',[
                ('Spend a few minutes together / 5 min',lambda:self.chat_role('regular')),('Back to the room',self.dismiss)])
        elif key == 'rest':
            self.open_dialog('Behind the stage', 'Ten quiet minutes may help your nerves. The doors and your set time keep approaching.',[
                ('Sit and breathe / 10 min',self.rest),('Back to the room',self.dismiss)])
        elif key == 'door':
            self.closed = True

    def approach_dialog(self,key):
        self.dismiss();self.approach(key)

    def prep(self,kind):
        self.life.prepare(kind)
        self.dismiss();self.after_action()
        plan = self.life.plan()
        if plan and plan['monitor_revealed'] and not plan['monitor_resolved'] and kind=='sound':
            self.interact('engineer')

    def chat_role(self,role):
        self.life.talk(role);self.dismiss();self.after_action()

    def rest(self):
        self.life.elapse(10)
        self.game.player.energy = min(100,self.game.player.energy+3)
        self.game.player.stress = max(0,self.game.player.stress-4)
        self.dismiss();self.notice = 'A little quieter. The rest of the room kept moving.'

    def crew(self,kind):
        candidates = [s for s in self.game.player.staff if s.role.lower().replace('_',' ') in {'roadie','sound engineer'}]
        choices = [(f'{s.name} / {s.role}',lambda staff=s:self.assign(staff,kind)) for s in candidates]
        self.open_dialog('Your crew', 'Soundcheck takes thirty minutes; the merch table takes twenty. Crew can work while you do something else.'
                         if candidates else 'You have no roadie or sound engineer on staff.', choices+[('Back',self.dismiss)])

    def assign(self,staff,kind):
        self.life.assign_crew(staff,kind);self.dismiss();self.after_action()

    def stage(self):
        ok,text = self.life.take_stage()
        if ok:
            self.next_state = 'performance';self.closed = True
        else:
            self.open_dialog('Before you go on',text,[('Back to the room',self.dismiss)])

    def after_action(self):
        logs = getattr(self.ui,'log_messages',[])
        if logs:self.notice = logs[0]

    def phone(self):
        self.open_dialog('Phone','Reading is free. Calls and booking work consume time while the venue keeps its schedule.',[
            ('Calendar',self.calendar),('Call a contact',self.contacts),('Live bookings',self.bookings),('Put phone away',self.dismiss)])

    def draw_room(self):
        surface = self.ui.screen
        pygame.draw.rect(surface,(31,30,44),(24,174,760,413),border_radius=6)
        pygame.draw.rect(surface,(58,54,61),FLOOR)
        for y in range(225,574,25):pygame.draw.line(surface,(46,45,53),(44,y),(768,y))
        for x in range(44,768,90):pygame.draw.line(surface,(48,46,54),(x,225),(x,573))
        self.text('LIVE TONIGHT',90,194,AMBER,self.ui.FONT_DEFAULT)
        self.text('LOAD IN  /  SOUND  /  DOORS',400,196,MUTED,self.ui.FONT_SMALL)
        # Raised stage, curtains, amps and drum kit.
        for r in SOLIDS:
            pygame.draw.rect(surface,(22,24,32),r.move(0,8),border_radius=3)
            pygame.draw.rect(surface,(81,65,66),r,border_radius=3)
        pygame.draw.rect(surface,(64,38,54),(68,236,260,29))
        for x in range(72,330,18):pygame.draw.line(surface,(104,54,71),(x,238),(x,262),5)
        for x in (77,283):
            pygame.draw.rect(surface,(23,28,34),(x,291,35,58),border_radius=3)
            for y in (307,331):pygame.draw.circle(surface,(69,74,77),(x+17,y),11,2)
        for x,y,r in [(195,292,24),(166,280,13),(222,277,13)]:
            pygame.draw.circle(surface,(168,128,93),(x,y),r)
            pygame.draw.circle(surface,(64,53,52),(x,y),r,3)
        pygame.draw.line(surface,PAPER,(237,294),(237,346),2)
        pygame.draw.line(surface,PAPER,(225,346),(249,346),2)
        pygame.draw.line(surface,INK,(236,292),(247,287),4)
        # Amber and violet stage lights.
        veil = pygame.Surface(surface.get_size(),pygame.SRCALPHA)
        for x,color in [(119,(236,173,87,30)),(285,(162,125,221,35))]:
            pygame.draw.polygon(veil,color,[(x,221),(x-55,373),(x+55,373)])
            pygame.draw.circle(surface,color[:3],(x,219),6)
        surface.blit(veil,(0,0))
        # Bar and engineer's console.
        for x in range(610,725,21):
            pygame.draw.rect(surface,(121,158,137),(x,248,8,23),border_radius=2)
        self.text('BAR',643,283,PAPER,self.ui.FONT_SMALL)
        pygame.draw.rect(surface,(26,33,39),(643,361,79,35),border_radius=2)
        for x in range(650,720,10):
            pygame.draw.line(surface,MUTED,(x,367),(x,390))
            pygame.draw.rect(surface,TEAL,(x-2,374+(x%3)*3,5,4))
        self.text('MERCH',612,459,PAPER,self.ui.FONT_SMALL)
        plan = self.life.plan()
        if plan and plan['merch_ready']:
            for x in range(650,720,16):pygame.draw.rect(surface,AMBER,(x,454,11,23))
        pygame.draw.rect(surface,(51,81,78),(69,447,117,31),border_radius=6)
        self.text('EXIT',709,552,PAPER,self.ui.FONT_SMALL)
        # The visible group grows as doors open; additional attendees are counted.
        attendance = self.life.attendance()
        manager = self.game.performance_manager if self.performance_view else None
        if manager:
            attendance = getattr(self.game.active_performance,'club_performance_context',{}).get('attendance',attendance)
        for i in range(min(18,attendance)):
            x,y = 369+(i%6)*34,367+(i//6)*43
            sway = math.sin(self.animation*2+i)*2 if manager else 0
            self.sprite((x+sway,y),[(129,113,151),(123,150,140),(167,126,103)][i%3])
        for key in ('host','engineer','regular'):
            target = self.targets()[key]
            self.sprite(target['pos'],{'host':(177,123,100),'engineer':(125,142,162),'regular':(159,145,100)}[key],target['name'],self.focus==key)
        for point in self.path[::2]:pygame.draw.circle(surface,(170,155,123),point,2)
        player_pos = (239,334) if self.performance_view else self.position
        nearby = any(math.dist(player_pos,self.targets()[key]['pos']) < 50 for key in self.people)
        self.sprite(player_pos,TEAL,None if nearby else 'You',player=True)
        if attendance:self.text(f'{attendance} in the room',347,554,PAPER,self.ui.FONT_SMALL)

    def draw(self):
        surface=self.ui.screen;surface.fill(INK);self.buttons=[]
        self.ui.interface.hud(self.game.player)
        self.text('ON STAGE / LIVE ROOM' if self.performance_view else 'AFTER LOAD-IN / LIVE ROOM',24,102,AMBER,self.ui.FONT_SMALL)
        self.text(self.life.poi.name,24,124,PAPER,self.ui.FONT_TITLE,755)
        self.draw_room()
        pygame.draw.rect(surface,(19,26,35),(801,101,335,488),border_radius=5)
        if self.dialog:
            d=self.dialog
            self.text(d['title'],818,117,AMBER,self.ui.FONT_DEFAULT,297,2)
            y = 169
            for paragraph in d['text'].split('\n'):
                if y >= 337: break
                y = self.text(paragraph,818,y,PAPER,self.ui.FONT_LOG,296,max(1,(337-y)//self.ui.FONT_LOG.get_linesize())) + 4
            for i,(label,action) in enumerate(d['choices'][:4]):
                self.button(f'{i+1}. {label}',pygame.Rect(816,350+i*54,304,50),action)
            if len(d['choices'])>4:self.button('More',pygame.Rect(816,565,304,22),self.more_choices)
        else:
            event=self.life.event();plan=self.life.plan()
            finished = plan and plan['status'] in {'played','cancelled','missed'}
            self.text('AFTER THE SET' if finished else 'THE ROOM BEFORE THE SET',818,120,AMBER,self.ui.FONT_SMALL)
            if event:
                doors,start,end=self.life.times(event)
                self.text(plan['status'].title() if finished else f'{start.hour:02d}:{start.minute:02d} / Set time',818,150,PAPER,self.ui.FONT_TITLE)
                self.text('Tonight\'s slot is closed.' if finished else f'Doors {doors.hour:02d}:{doors.minute:02d} / {self.life.attendance()} inside',818,192,MUTED)
                sound='Not checked' if not plan['sound'] else 'Monitor hum' if plan['monitor_fault'] and not plan['monitor_resolved'] else 'Clear monitor'
                facts=[f'Sound: {sound}',f"Merch table: {'ready' if plan['merch_ready'] else 'not set up'}"]
                if plan['crew_task']:
                    task=plan['crew_task'];facts.append(f"{task['staff'].name} working until {task['ready_at'].hour:02d}:{task['ready_at'].minute:02d}")
                for index,fact in enumerate(facts):
                    self.text(fact,818,241+index*29,TEAL,self.ui.FONT_SMALL,width=292,lines=1)
            else:self.text('No available show in this room today.',818,168,MUTED,width=292,lines=3)
            last=self.life.data['last_result']
            if last:self.text(f"Last set: {last['status']} / crowd {last['hype']:.0f}/100",818,340,MUTED,width=292,lines=2)
            self.button('Talk to the promoter' if finished else 'Approach the stage',pygame.Rect(816,389,304,42),lambda:self.approach('host' if finished else 'stage'))
            self.button('Phone  [P]',pygame.Rect(816,441,304,42),self.phone)
            self.button('Calendar',pygame.Rect(816,493,304,42),self.calendar)
        self.text('ON STAGE' if self.performance_view else 'PAUSED' if not self.speed else f'{self.speed}x',24,600,TEAL,self.ui.FONT_SMALL)
        if not self.performance_view:
            for i,(label,speed) in enumerate([('Pause',0),('1x',1),('4x',4),('12x',12)]):
                self.button(label,pygame.Rect(439+i*84,594,77,32),lambda value=speed:self.set_speed(value),self.speed==speed)
        self.text(self.notice,24,632,MUTED,self.ui.FONT_SMALL,1110)
        self.text('1–4 Choose / mouse    Esc Back    Tab Details' if self.performance_view else
                  'WASD / arrows Move   E Interact   Tab / Enter Approach   Space Pause   1 / 2 / 3 Speed   F5 Save   Esc Leave',24,658,MUTED,self.ui.FONT_SMALL)


def present_club_performance(game, options, title, context=None):
    """Keep the live room on screen through set selection and performance."""
    context=context or {}
    scene=ClubScene(game,game.active_performance.location)
    scene.performance_view=True
    scene.notice='The room responds to your playing. Tab opens the full stage notes and action details.'
    selected=[]
    details=list(dict.fromkeys(context.get('details',[])))
    scene.open_dialog(title,context.get('subtitle','')+'\n'+'\n'.join(details[:2]),
                      [(str(label),lambda key=key:selected.append(key)) for key,label in options.items()])
    clock=pygame.time.Clock()
    while not selected:
        scene.animation+=clock.tick(60)/1000
        scene.draw();game.ui.update_display()
        for event in pygame.event.get():
            if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
                if 'back' in options:return 'back'
                continue
            if event.type==pygame.KEYDOWN and event.key==pygame.K_TAB:
                descriptions=[f'{options[key]}: {value}' for key,value in context.get('option_descriptions',{}).items() if key in options]
                game.ui.interface.read_document('Stage notes','\n\n'.join([title,context.get('subtitle','')]+descriptions+details))
                continue
            scene.handle_event(event)
    return selected[0]
