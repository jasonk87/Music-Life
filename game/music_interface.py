"""Music Life's shared visual shell. All decisions remain in the simulation."""
from pathlib import Path
import math
import pygame

INK = (12, 19, 25)
PAPER = (231, 224, 207)
MUTED = (144, 160, 162)
AMBER = (223, 174, 98)
TEAL = (111, 182, 177)
LINE = (45, 60, 65)
ART = Path(__file__).resolve().parent.parent / 'game_data' / 'art'


class MusicInterface:
    def __init__(self, ui):
        self.ui = ui
        self.images = {}
        self.positions = {}
        self.display_font = pygame.font.SysFont('georgia', 76)
        self.brand_font = pygame.font.SysFont('segoeui', 16, bold=True)

    def art(self, name, rect):
        key = (name, rect.size)
        if key not in self.images:
            path = ART / name
            if not path.exists(): return False
            image = pygame.image.load(str(path)).convert()
            factor = max(rect.w / image.get_width(), rect.h / image.get_height())
            image = pygame.transform.smoothscale(image, (int(image.get_width()*factor)+1, int(image.get_height()*factor)+1))
            crop = image.subsurface(((image.get_width()-rect.w)//2, (image.get_height()-rect.h)//2, rect.w, rect.h)).copy()
            self.images[key] = crop
        self.ui.screen.blit(self.images[key], rect)
        return True

    def text(self, text, x, y, color=PAPER, font=None, width=None, lines=1):
        ui = self.ui
        font = font or ui.FONT_LOG
        if width:
            return ui.draw_wrapped_lines(text, font, color, x, y, width, max_lines=lines)
        ui.draw_text(text, font, color, x, y)
        return y + font.get_linesize()

    def hud(self, player):
        from game.game_time import current_game_time as clock
        ui = self.ui
        pygame.draw.rect(ui.screen, (15, 24, 31), (0, 0, 1160, 86))
        pygame.draw.line(ui.screen, LINE, (24, 85), (1136, 85))
        self.text('MUSIC / LIFE', 24, 14, AMBER, self.brand_font)
        self.text(player.name, 24, 41, PAPER, ui.FONT_DEFAULT, 185)
        city = getattr(player.current_location, 'name', 'On the road')
        self.text(f'{clock.hour:02d}:{clock.minute:02d}    {clock.year}.{clock.month:02d}.{clock.day:02d}', 225, 14, PAPER, ui.FONT_DEFAULT)
        self.text(city, 225, 45, MUTED, width=260)
        self.text(f'${player.money:,.0f}', 520, 10, AMBER, ui.FONT_TITLE)
        self.text(f'Fame {player.fame}   /   Cred {player.street_cred}', 520, 49, MUTED, ui.FONT_SMALL)
        for i, (label, value, inverse) in enumerate([
            ('Energy', player.energy, False), ('Hunger', player.hunger, True),
            ('Stress', player.stress, True), ('Health', player.health, False)]):
            x = 748 + i * 96
            self.text(f'{label} {int(value)}', x, 20, MUTED, ui.FONT_SMALL)
            pygame.draw.rect(ui.screen, LINE, (x, 49, 78, 4))
            danger = value > 75 if inverse else value < 25
            pygame.draw.rect(ui.screen, (204, 113, 94) if danger else TEAL, (x, 49, int(78*max(0,min(100,value))/100), 4))

    def journal_strip(self):
        ui = self.ui
        pygame.draw.line(ui.screen, LINE, (24, 546), (1136, 546))
        self.text('RECENT DAYS', 24, 559, AMBER, self.brand_font)
        self.text('J  Open journal', 986, 559, MUTED, ui.FONT_SMALL)
        for i, line in enumerate(ui.log_messages[:3]):
            self.text(line, 24, 587+i*19, PAPER if i == 0 else MUTED, ui.FONT_SMALL, 1110)

    def sidebar(self, title, context, choice):
        ui, game = self.ui, self.ui.game
        player = getattr(game, 'player', None)
        poi = getattr(player, 'current_poi', None)
        home = getattr(poi, 'category', '') == 'HOME'
        rect = pygame.Rect(780, 108, 356, 188)
        self.art('room-afternoon.png' if home else 'shore-night.png', rect)
        pygame.draw.rect(ui.screen, LINE, rect, 1)
        location = getattr(poi, 'name', getattr(getattr(player, 'current_location', None), 'name', 'Music Life'))
        self.text(location.upper(), 780, 307, AMBER, self.brand_font, 354)
        desc = context.get('option_descriptions', {}).get(choice)
        if desc:
            self.text(desc, 780, 337, PAPER, width=350, lines=4)
        else:
            self.text(context.get('subtitle', ''), 780, 337, PAPER, width=350, lines=3)
        details = context.get('details', [])
        # The full context is available with Tab; brief scene facts stay legible.
        performance = getattr(game, 'performance_manager', None)
        travel = getattr(game, 'travel_manager', None)
        appearance = context.get('appearance')
        if appearance:
            self.text(f"{appearance['waiting']} waiting / {appearance['met']} met / {appearance['left']} left", 780, 418, TEAL, ui.FONT_SMALL)
            pygame.draw.rect(ui.screen, LINE, (780, 443, 350, 6))
            met_width = int(350 * appearance['met'] / max(1, appearance['turnout']))
            pygame.draw.rect(ui.screen, TEAL, (780, 443, met_width, 6))
            self.text(f"{appearance['minutes']} / 90 min advertised", 780, 460, MUTED, ui.FONT_SMALL)
            self.text(f"${appearance['revenue']} sales / {appearance['units_sold']} items", 780, 481, MUTED, ui.FONT_SMALL)
        elif performance and getattr(game, 'game_state', '') == 'performance':
            self.text(f'Crowd {performance.crowd_hype}/100 / Stage energy {int(performance.band_energy)}',
                      780, 428, TEAL, ui.FONT_SMALL, 350)
            pygame.draw.rect(ui.screen, LINE, (780, 454, 350, 5))
            pygame.draw.rect(ui.screen, AMBER, (780, 454, int(350 * max(0, min(100, performance.crowd_hype)) / 100), 5))
            self.text(f'Section {min(performance.current_section_index + 1, len(performance.sections))} of {len(performance.sections)}',
                      780, 473, MUTED, ui.FONT_SMALL)
        elif travel and getattr(game, 'game_state', '') == 'travel_active':
            self.text(f'{int(travel.get_progress_percent() * 100)}% of the journey complete', 780, 428, TEAL, ui.FONT_SMALL)
            pygame.draw.rect(ui.screen, LINE, (780, 454, 350, 5))
            pygame.draw.rect(ui.screen, TEAL, (780, 454, int(350 * max(0, min(1, travel.get_progress_percent()))), 5))
            self.text(f'{travel.distance_covered:.0f} / {travel.distance_total:.0f} km', 780, 473, MUTED, ui.FONT_SMALL)
        elif player and game:
            self.text(game._get_progress_hint(), 780, 428, TEAL, ui.FONT_SMALL, 350)
            from game.game_time import current_game_time
            upcoming = player.schedule.get_upcoming_events(current_game_time, limit=1)
            if upcoming:
                self.text(str(upcoming[0]), 780, 450, MUTED, ui.FONT_SMALL, 350, 2)
        if details:
            self.text('TAB  Details & commitments', 780, 499, MUTED, ui.FONT_SMALL)

    def draw_menu(self, options, title, context, selected, page, page_size):
        ui = self.ui
        ui.screen.fill(INK)
        player = getattr(ui.game, 'player', None)
        if player: self.hud(player)
        keys = list(options)
        visible = keys[page*page_size:(page+1)*page_size]
        self.text(context.get('eyebrow', 'Music Life').upper(), 24, 108, AMBER, self.brand_font)
        self.text(title, 24, 133, PAPER, ui.FONT_TITLE, 718)
        rects = []
        for i, key in enumerate(visible):
            rect = pygame.Rect(24, 184+i*44, 718, 40)
            rects.append(rect)
            active = i == selected
            pygame.draw.rect(ui.screen, (33, 51, 55) if active else (18, 28, 35), rect, border_radius=3)
            if active: pygame.draw.rect(ui.screen, AMBER, (rect.x, rect.y+4, 3, rect.h-8))
            self.text(str(page*page_size+i+1).zfill(2), 38, rect.y+11, AMBER if active else MUTED, ui.FONT_SMALL)
            label = str(options[key])
            if label.startswith('[') and ']' in label: label = label.split(']',1)[1].strip()
            self.text(label, 77, rect.y+7, PAPER if active else MUTED, ui.FONT_DEFAULT, 645)
        total_pages = math.ceil(len(keys)/page_size)
        if total_pages > 1:
            self.text(f'< Previous     {page+1} / {total_pages}     Next >', 24, 505, MUTED, ui.FONT_SMALL)
        if context.get('appearance'):
            self.text(context.get('subtitle', ''), 24, 196+len(visible)*44, PAPER, width=700, lines=4)
        self.sidebar(title, context, visible[selected])
        self.journal_strip()
        self.text('Arrows / mouse  Select     Enter  Confirm     Esc  Back     F5  Save', 24, 652, MUTED, ui.FONT_SMALL)
        return rects

    def title_frame(self, options, selected):
        ui = self.ui
        ui.screen.fill(INK)
        self.art('shore-night.png', pygame.Rect(0, 0, 1160, 680))
        veil = pygame.Surface((620, 680), pygame.SRCALPHA)
        for x in range(620):
            pygame.draw.line(veil, (5, 12, 19, int(195*(1-x/620))), (x,0), (x,680))
        ui.screen.blit(veil, (0,0))
        self.text('A MUSICIAN\'S LIFE', 54, 66, AMBER, self.brand_font)
        self.text('Music Life', 48, 101, PAPER, self.display_font)
        self.text('Make a living. Make a sound.', 54, 205, PAPER, ui.FONT_DEFAULT)
        self.text('The world keeps its own time.', 54, 235, MUTED, ui.FONT_LOG)
        rects=[]
        for i, (key, label) in enumerate(options.items()):
            r=pygame.Rect(54, 350+i*55, 358, 46)
            rects.append(r)
            pygame.draw.rect(ui.screen, (29,46,51) if selected==i else (13,24,32), r, border_radius=3)
            pygame.draw.line(ui.screen, AMBER if selected==i else LINE, r.bottomleft, r.bottomright)
            self.text(label, 70, r.y+10, PAPER if selected==i else MUTED, ui.FONT_DEFAULT)
        self.text('Independent lives. Unscripted careers.',54,605,MUTED,ui.FONT_SMALL)
        self.text('Arrow keys / mouse    Enter to select',54,634,MUTED,ui.FONT_SMALL)
        return rects

    def present_choices(self, options, title, context=None):
        ui=self.ui
        context=context or {}
        if not options: return None
        if not isinstance(options,dict): options=dict(enumerate(options))
        keys=list(options)
        signature=(title,tuple(keys))
        page,selected=self.positions.get(signature,(0,0))
        page_size=7
        pages=math.ceil(len(keys)/page_size)
        is_title=getattr(ui.game,'game_state',None)=='title_screen'
        old_mouse=pygame.mouse.get_pos()
        while True:
            visible=keys[page*page_size:(page+1)*page_size]
            selected=min(selected,len(visible)-1)
            rects=self.title_frame(options,selected) if is_title else self.draw_menu(options,title,context,selected,page,page_size)
            ui.update_display()
            for event in pygame.event.get():
                if event.type==pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                visible=keys[page*page_size:(page+1)*page_size]
                selected=min(selected,len(visible)-1)
                choice=None
                if event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_UP: selected=(selected-1)%len(visible)
                    elif event.key==pygame.K_DOWN: selected=(selected+1)%len(visible)
                    elif event.key in (pygame.K_LEFT,pygame.K_PAGEUP): page=max(0,page-1);selected=0
                    elif event.key in (pygame.K_RIGHT,pygame.K_PAGEDOWN): page=min(pages-1,page+1);selected=0
                    elif event.key==pygame.K_RETURN: choice=visible[selected]
                    elif event.key==pygame.K_ESCAPE:
                        # Cancel must never accept a purchase, deal or decision.
                        for cancel in ('back','cancel','no','none','quit'):
                            if cancel in options: choice=cancel;break
                        if choice is None: continue
                    elif pygame.K_1<=event.key<=pygame.K_7:
                        index=event.key-pygame.K_1
                        if index<len(visible): choice=visible[index]
                    elif event.key==pygame.K_F5 and getattr(ui.game,'player',None): ui.game.quick_save()
                    elif event.key==pygame.K_j and not is_title:
                        self.read_document('Journal', '\n\n'.join(ui.log_messages))
                    elif event.key==pygame.K_TAB and not is_title:
                        facts=[title,str(options[visible[selected]]),context.get('subtitle','')]+list(context.get('details',[]))
                        player=getattr(ui.game,'player',None)
                        if player:
                            facts+=['','CALENDAR']+[str(e) for e in player.schedule.scheduled_items]
                        self.read_document('Details & commitments','\n\n'.join(facts))
                elif event.type==pygame.MOUSEWHEEL:
                    page=max(0,min(pages-1,page-event.y));selected=0
                elif event.type==pygame.MOUSEMOTION and event.pos!=old_mouse:
                    old_mouse=event.pos
                    for i,r in enumerate(rects):
                        if r.collidepoint(event.pos): selected=i
                elif event.type==pygame.MOUSEBUTTONUP and event.button==1:
                    for i,r in enumerate(rects):
                        if r.collidepoint(event.pos): choice=visible[i]
                    if not is_title and 500<=event.pos[1]<=536:
                        if event.pos[0]<112: page=max(0,page-1)
                        elif event.pos[0]<350: page=min(pages-1,page+1)
                        selected=0
                if choice is not None:
                    self.positions[signature]=(page,selected)
                    return choice

    def read_document(self,title,text):
        ui=self.ui
        lines=[]
        for line in str(text).splitlines(): lines.extend(ui.wrap_text(line,ui.FONT_LOG,1020))
        offset=0
        while True:
            ui.screen.fill(INK)
            self.text(title,54,35,AMBER,ui.FONT_TITLE)
            pygame.draw.line(ui.screen,LINE,(54,85),(1106,85))
            for i,line in enumerate(lines[offset:offset+21]): self.text(line,54,105+i*24)
            self.text(f'Up / Down / wheel  Scroll    Esc / Enter  Close     {offset+1} / {max(1,len(lines))}',54,641,MUTED,ui.FONT_SMALL)
            ui.update_display()
            for event in pygame.event.get():
                if event.type==pygame.QUIT: pygame.quit();raise SystemExit
                if event.type==pygame.MOUSEWHEEL: offset-=event.y*3
                elif event.type==pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE,pygame.K_RETURN): return
                    if event.key==pygame.K_DOWN: offset+=1
                    elif event.key==pygame.K_UP: offset-=1
                    elif event.key==pygame.K_PAGEDOWN: offset+=18
                    elif event.key==pygame.K_PAGEUP: offset-=18
                offset=max(0,min(max(0,len(lines)-21),offset))
