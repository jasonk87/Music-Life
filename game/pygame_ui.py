import pygame
import sys
import math
import os
from pathlib import Path
from game.music_interface import MusicInterface
from typing import Dict, List, Optional, Any
from game.portrait import Portrait
from game.game_time import get_current_time_str

# --- Geometry & Display Constants ---
SCREEN_WIDTH = 1160
SCREEN_HEIGHT = 680
FPS = 60
MARGIN = 24

# --- Color Palette ---
BLACK = (0, 0, 0)
BG_DARK = (12, 19, 25)
BG_DEEP = (12, 19, 25)
PANEL_BG = (18, 24, 36)
PANEL_ALT = (26, 34, 50)
PANEL_HEADER = (30, 40, 60)
PANEL_BORDER = (46, 60, 88)
BUTTON_BG = (22, 30, 44)
BUTTON_HOVER = (40, 58, 86)
BUTTON_SELECTED = (48, 74, 114)
BUTTON_BORDER = (56, 76, 110)
CHASSIS_BORDER = (45, 54, 72)

WHITE = (231, 224, 207)
LIGHT_GREY = (180, 192, 210)
GREY = (120, 134, 154)
DARK_GREY = (60, 72, 90)

BLUE = (111, 182, 177)
YELLOW = (223, 174, 98)
GREEN = (52, 211, 153)
EMERALD = (52, 211, 153)
RED = (248, 113, 113)
CRIMSON = (248, 113, 113)
ORANGE = (255, 140, 70)
AMBER = (251, 191, 36)
CYAN = (34, 211, 238)
PURPLE = (192, 132, 252)

# Fonts
pygame.font.init()
FONT_DEFAULT = pygame.font.Font(None, 30)
FONT_TITLE = pygame.font.Font(None, 42)
FONT_LOG = pygame.font.Font(None, 22)
FONT_SMALL = pygame.font.Font(None, 19)
FONT_ASCII = pygame.font.SysFont('monospace', 17)


class PygameUI:
    def __init__(self):
        pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()
        flags = pygame.RESIZABLE
        if pygame.display.get_driver() != "dummy":
            flags |= pygame.SCALED
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        pygame.display.set_caption("Music-Life Sim")
        self.clock = pygame.time.Clock()
        self.log_messages = []
        self.portrait = Portrait(self.screen)
        self.game = None
        self.interface = MusicInterface(self)

        # Use the regular face explicitly; Windows font aliases can select a thin face.
        font_root = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
        def face(size, bold=False):
            path = font_root / ('segoeuib.ttf' if bold else 'segoeui.ttf')
            return pygame.font.Font(str(path), size) if path.exists() else pygame.font.Font(None, size+3)
        # Expose fonts as fresh instance attributes
        self.FONT_DEFAULT = face(20)
        self.FONT_TITLE = face(28, True)
        self.FONT_LOG = face(17)
        self.FONT_SMALL = face(14)
        self.FONT_ASCII = pygame.font.SysFont('monospace', 17)

    def clear_screen(self):
        self.screen.fill(BG_DARK)

    def enter_music_shop(self, poi):
        from game.shop_scene import run_shop_scene
        run_shop_scene(self.game, poi)

    def enter_live_club(self, venue):
        from game.club_scene import ClubScene
        ClubScene(self.game, venue).run()

    def update_display(self):
        pygame.display.flip()
        self.clock.tick(FPS)

    def draw_text(self, text, font, color, x, y, centered=False):
        text_surface = font.render(str(text), True, color)
        text_rect = text_surface.get_rect()
        if centered:
            text_rect.center = (int(x), int(y))
        else:
            text_rect.topleft = (int(x), int(y))
        self.screen.blit(text_surface, text_rect)
        return text_rect

    def wrap_text(self, text, font, max_width):
        words = str(text).split()
        if not words:
            return [""]
        lines = []
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if font.size(trial)[0] <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def draw_wrapped_lines(self, text, font, color, x, y, max_width, line_height=None, max_lines=None):
        lines = self.wrap_text(text, font, max_width)
        if max_lines is not None:
            lines = lines[:max_lines]
        line_height = line_height or font.get_linesize()
        for idx, line in enumerate(lines):
            self.draw_text(line, font, color, x, y + (idx * line_height))
        return y + (len(lines) * line_height)

    def draw_choice_background(self):
        """Draw a dark atmospheric cyber-indie background with subtle ambient glows."""
        self.screen.fill(BG_DEEP)

        # Ambient glow circles with alpha surfaces
        glow_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, (28, 52, 84, 40), (160, 120), 220)
        pygame.draw.circle(glow_surface, (54, 38, 28, 30), (SCREEN_WIDTH - 120, 100), 200)
        pygame.draw.circle(glow_surface, (20, 36, 30, 35), (SCREEN_WIDTH - 180, SCREEN_HEIGHT - 100), 240)
        pygame.draw.circle(glow_surface, (40, 20, 48, 25), (200, SCREEN_HEIGHT - 80), 180)

        # Subtle horizontal guide lines
        for y_line in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(glow_surface, (30, 40, 60, 12), (0, y_line), (SCREEN_WIDTH, y_line), 1)

        self.screen.blit(glow_surface, (0, 0))

    def draw_panel(self, rect, title=None, accent=BLUE, alpha=235, subtitle=None):
        """Draws a standardized rounded glassmorphic card panel."""
        panel_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        panel_surface.fill((*PANEL_BG, alpha))
        self.screen.blit(panel_surface, rect.topleft)

        # Border
        pygame.draw.rect(self.screen, PANEL_BORDER, rect, 1, border_radius=8)

        # Top Accent Strip
        if accent:
            accent_rect = pygame.Rect(rect.x + 14, rect.y + 12, rect.width - 28, 3)
            pygame.draw.rect(self.screen, accent, accent_rect, border_radius=2)

        # Title & Subtitle
        if title:
            self.draw_text(title, self.FONT_LOG, WHITE, rect.x + 18, rect.y + 22)
            if subtitle:
                self.draw_text(subtitle, self.FONT_SMALL, LIGHT_GREY, rect.x + 18, rect.y + 42)

    def draw_meter(self, label, value, maximum, x, y, width, color, height=14):
        """Hardware LED Segmented VU Meter Bar."""
        pct = 0 if maximum <= 0 else max(0.0, min(1.0, float(value) / float(maximum)))
        val_str = f"{int(value)}/{int(maximum)}" if maximum > 0 else f"{int(value)}"
        self.draw_text(f"{label}: {val_str}", self.FONT_SMALL, LIGHT_GREY, x, y)

        bar_y = y + 16
        bar_rect = pygame.Rect(x, bar_y, width, height)
        pygame.draw.rect(self.screen, (10, 14, 20), bar_rect, border_radius=3)

        num_segments = 14
        gap = 2
        seg_w = (width - ((num_segments - 1) * gap)) / num_segments
        active_segments = int(round(pct * num_segments))

        for i in range(num_segments):
            seg_x = x + int(i * (seg_w + gap))
            seg_rect = pygame.Rect(seg_x, bar_y + 1, max(1, int(seg_w)), height - 2)
            if i < active_segments:
                seg_col = color if i < num_segments - 2 else RED
                pygame.draw.rect(self.screen, seg_col, seg_rect, border_radius=1)
            else:
                pygame.draw.rect(self.screen, (22, 28, 40), seg_rect, border_radius=1)

        pygame.draw.rect(self.screen, (40, 52, 72), bar_rect, 1, border_radius=3)

    def draw_badge(self, text, x, y, bg_color=PANEL_ALT, text_color=WHITE):
        """Draws a compact status badge/tag."""
        padding_x = 8
        padding_y = 3
        text_w, text_h = self.FONT_SMALL.size(text)
        badge_rect = pygame.Rect(x, y, text_w + padding_x * 2, text_h + padding_y * 2)
        pygame.draw.rect(self.screen, bg_color, badge_rect, border_radius=4)
        pygame.draw.rect(self.screen, (60, 80, 110), badge_rect, 1, border_radius=4)
        self.draw_text(text, self.FONT_SMALL, text_color, x + padding_x, y + padding_y)
        return badge_rect.right

    def draw_hud(self, player, date_str, location_str, next_event_str, progress_hint):
        self.interface.hud(player)

    def draw_log(self):
        """Draws the bottom recent activity log bar."""
        log_h = 34
        log_w = SCREEN_WIDTH - (MARGIN * 2)
        log_rect = pygame.Rect(MARGIN, SCREEN_HEIGHT - log_h - 10, log_w, log_h)

        log_surface = pygame.Surface((log_rect.width, log_rect.height), pygame.SRCALPHA)
        log_surface.fill((*PANEL_BG, 210))
        self.screen.blit(log_surface, log_rect.topleft)
        pygame.draw.rect(self.screen, PANEL_BORDER, log_rect, 1, border_radius=6)

        latest_msg = self.log_messages[0] if self.log_messages else "Ready."
        self.draw_text("Latest Activity:", self.FONT_SMALL, YELLOW, log_rect.x + 12, log_rect.y + 9)
        self.draw_text(latest_msg, self.FONT_SMALL, LIGHT_GREY, log_rect.x + 120, log_rect.y + 9)

    def add_log_message(self, message):
        message = str(message).strip()
        if not message: return
        if message.lower().startswith(("loaded ", "loading ", "initialized ", "world setup", "initializing ", "offline npc dialogue")): return
        for line in message.splitlines():
            self.log_messages.insert(0, line)
        if self.game and self.game.player:
            self.game.journal = self.log_messages[:500]
        if len(self.log_messages) > 500:
            self.log_messages.pop()

    add_message = add_log_message

    def present_choices(self, options: Any, title: str, context: Optional[Dict] = None):
        event = getattr(self.game, 'active_performance', None)
        if (getattr(self.game, 'game_state', '') == 'performance' and event
                and getattr(event.location, 'club_life', None)):
            from game.club_scene import present_club_performance
            return present_club_performance(self.game, options, title, context)
        return self.interface.present_choices(options, title, context)

    def get_text_input(self, prompt, context=None):
        """Displays a clean modal text input card."""
        text = ""
        context = context or {}
        accent = context.get("accent", BLUE)
        subtitle = context.get("subtitle", "Type your answer, then press Enter to confirm.")
        panel_title = context.get("panel_title", "Entry")
        notes = context.get("details", [])
        placeholder = context.get("placeholder", "")
        max_length = context.get("max_length", 32)

        card_w = 840
        card_h = 380
        card_rect = pygame.Rect((SCREEN_WIDTH - card_w) // 2, (SCREEN_HEIGHT - card_h) // 2, card_w, card_h)

        input_box_w = card_w - 56
        input_box_h = 56
        input_rect = pygame.Rect(card_rect.x + 28, card_rect.y + 140, input_box_w, input_box_h)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        return text.strip()
                    if event.key == pygame.K_ESCAPE:
                        return None
                    if event.key == pygame.K_BACKSPACE:
                        text = text[:-1]
                    elif event.unicode and event.unicode.isprintable() and len(text) < max_length:
                        text += event.unicode

            self.clear_screen()
            self.draw_choice_background()

            # Render Main Card
            self.draw_panel(card_rect, None, accent)

            # Header inside Card
            self.draw_text(panel_title.upper(), self.FONT_SMALL, accent, card_rect.x + 28, card_rect.y + 24)
            self.draw_text(prompt, self.FONT_TITLE, WHITE, card_rect.x + 28, card_rect.y + 48)
            self.draw_wrapped_lines(subtitle, self.FONT_LOG, LIGHT_GREY, card_rect.x + 28, card_rect.y + 90, card_w - 56, line_height=20, max_lines=2)

            # Input Box
            pygame.draw.rect(self.screen, (10, 14, 22), input_rect, border_radius=8)
            pygame.draw.rect(self.screen, accent, input_rect, 2, border_radius=8)

            display_val = text if text else placeholder
            text_col = WHITE if text else GREY
            self.draw_text(display_val, self.FONT_DEFAULT, text_col, input_rect.x + 18, input_rect.y + 16)

            # Blinking Cursor
            if (pygame.time.get_ticks() // 500) % 2 == 0:
                cur_x = input_rect.x + 18 + self.FONT_DEFAULT.size(text)[0]
                pygame.draw.line(self.screen, accent, (cur_x, input_rect.y + 12), (cur_x, input_rect.bottom - 12), 2)

            # Length Counter Badge
            self.draw_text(f"{len(text)} / {max_length}", self.FONT_SMALL, LIGHT_GREY, input_rect.right - 14, input_rect.bottom + 12, centered=True)

            # Extra Notes inside Card
            note_y = card_rect.y + 240
            for note in notes[:2]:
                note_y = self.draw_wrapped_lines(f"• {note}", self.FONT_SMALL, LIGHT_GREY, card_rect.x + 28, note_y, card_w - 56, 18, 2) + 6

            # Footer
            self.draw_text("Press Enter to Confirm  •  Esc to Cancel", self.FONT_SMALL, GREY, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 32, centered=True)

            self.update_display()

    def draw_character_stats(self, player):
        """Modernized, fully structured Character Stats screen."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    running = False
                if event.type == pygame.MOUSEBUTTONUP:
                    running = False

            self.clear_screen()
            self.draw_choice_background()

            # Top HUD
            date_str = get_current_time_str(date_only=True)
            loc_str = player.current_poi.name if getattr(player, "current_poi", None) else getattr(player.current_location, "name", "On the road")
            self.draw_hud(player, date_str, loc_str, "Stats Review", "Inspect your physical and career condition")

            col_w = (SCREEN_WIDTH - (MARGIN * 2) - 32) // 3
            col_h = SCREEN_HEIGHT - 120 - 48
            y_start = 104

            # Panel 1: Identity & Vitals
            rect1 = pygame.Rect(MARGIN, y_start, col_w, col_h)
            self.draw_panel(rect1, "Identity & Vitals", BLUE)
            y = rect1.y + 54
            self.draw_text(f"Name: {player.name}", self.FONT_DEFAULT, WHITE, rect1.x + 18, y)
            y += 34
            self.draw_text(f"Age: {getattr(player, 'age', 21)}", self.FONT_LOG, LIGHT_GREY, rect1.x + 18, y)
            y += 30
            self.draw_meter("Health", getattr(player, "health", 100), 100, rect1.x + 18, y, col_w - 36, EMERALD)
            y += 44
            self.draw_meter("Comfort", getattr(player, "comfort", 100), 100, rect1.x + 18, y, col_w - 36, CYAN)
            y += 44
            self.draw_meter("Energy", getattr(player, "energy", 100), 100, rect1.x + 18, y, col_w - 36, EMERALD)
            y += 44
            self.draw_meter("Stress", getattr(player, "stress", 0), 100, rect1.x + 18, y, col_w - 36, CRIMSON)
            y += 44
            self.draw_meter("Hunger", getattr(player, "hunger", 0), 100, rect1.x + 18, y, col_w - 36, AMBER)

            # Panel 2: Career & Financials
            rect2 = pygame.Rect(rect1.right + 16, y_start, col_w, col_h)
            self.draw_panel(rect2, "Career Standing", YELLOW)
            y = rect2.y + 54
            self.draw_text("Cash Balance", self.FONT_SMALL, LIGHT_GREY, rect2.x + 18, y)
            self.draw_text(f"${player.money}", self.FONT_TITLE, YELLOW, rect2.x + 18, y + 18)
            y += 66
            self.draw_text(f"Fame Score: {player.fame}", self.FONT_DEFAULT, WHITE, rect2.x + 18, y)
            y += 34
            self.draw_text(f"Street Credibility: {getattr(player, 'street_cred', 50)}/100", self.FONT_LOG, CYAN, rect2.x + 18, y)
            y += 38

            songs_written = len(player.songs_written)
            songs_recorded = sum(1 for s in player.songs_written if s.is_recorded)
            songs_released = sum(1 for s in player.songs_written if s.is_released)
            top_buzz = max((s.buzz_score for s in player.songs_written), default=0)

            self.draw_text(f"Songs Written: {songs_written}", self.FONT_LOG, LIGHT_GREY, rect2.x + 18, y)
            y += 26
            self.draw_text(f"Songs Recorded: {songs_recorded}", self.FONT_LOG, LIGHT_GREY, rect2.x + 18, y)
            y += 26
            self.draw_text(f"Songs Released: {songs_released}", self.FONT_LOG, LIGHT_GREY, rect2.x + 18, y)
            y += 26
            self.draw_text(f"Top Song Buzz: {int(top_buzz)}", self.FONT_LOG, LIGHT_GREY, rect2.x + 18, y)

            # Panel 3: Strain, Vices & Traits
            rect3 = pygame.Rect(rect2.right + 16, y_start, col_w, col_h)
            self.draw_panel(rect3, "Strain & Traits", ORANGE)
            y = rect3.y + 54

            has_strain = False
            if player.vocal_strain > 0:
                self.draw_meter("Vocal Strain", player.vocal_strain, 100, rect3.x + 18, y, col_w - 36, CRIMSON)
                y += 44
                has_strain = True
            if player.wrist_strain > 0:
                self.draw_meter("Wrist Strain", player.wrist_strain, 100, rect3.x + 18, y, col_w - 36, CRIMSON)
                y += 44
                has_strain = True
            if player.substance_dependency > 0:
                self.draw_meter("Dependency", player.substance_dependency, 100, rect3.x + 18, y, col_w - 36, RED)
                y += 44
                has_strain = True

            if not has_strain:
                self.draw_text("No physical strain detected.", self.FONT_SMALL, GREEN, rect3.x + 18, y)
                y += 28

            y += 8
            self.draw_text("Active Traits:", self.FONT_LOG, WHITE, rect3.x + 18, y)
            y += 24
            if getattr(player, "traits", []):
                for trait in player.traits[:4]:
                    trait_name = getattr(trait, "name", str(trait))
                    trait_desc = getattr(trait, "description", "")
                    self.draw_badge(trait_name, rect3.x + 18, y, bg_color=PANEL_HEADER, text_color=CYAN)
                    y += 26
                    if trait_desc:
                        y = self.draw_wrapped_lines(trait_desc, self.FONT_SMALL, LIGHT_GREY, rect3.x + 18, y, col_w - 36, 16, 2) + 6
            else:
                self.draw_text("None", self.FONT_SMALL, GREY, rect3.x + 18, y)

            # Footer
            self.draw_text("Press ESC or Click to return to menu", self.FONT_SMALL, GREY, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 24, centered=True)

            self.update_display()

    def draw_skills_screen(self, player):
        """Modernized Skills Screen with visual mastery meters and descriptions."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    running = False
                if event.type == pygame.MOUSEBUTTONUP:
                    running = False

            self.clear_screen()
            self.draw_choice_background()

            # Top HUD
            date_str = get_current_time_str(date_only=True)
            loc_str = player.current_poi.name if getattr(player, "current_poi", None) else getattr(player.current_location, "name", "On the road")
            self.draw_hud(player, date_str, loc_str, "Skills Overview", "Practice and gigs improve your core musical disciplines")

            panel_w = 880
            panel_h = SCREEN_HEIGHT - 120 - 48
            panel_rect = pygame.Rect((SCREEN_WIDTH - panel_w) // 2, 104, panel_w, panel_h)
            self.draw_panel(panel_rect, "Musical & Performance Skills", CYAN)

            y = panel_rect.y + 60
            skills_info = {
                "songwriting": "Crafting catchy hooks, deep lyrics, and tight song structures.",
                "guitar": "Acoustic and electric fretwork, solos, and rhythm comping.",
                "vocals": "Pitch control, vocal timbre, breathing stamina, and live range.",
                "stage_presence": "Charisma, crowd connection, and commanding the stage.",
                "electronic": "Beat programming, synthesizers, sound design, and DAW production.",
            }

            for skill_name, skill_desc in skills_info.items():
                val = player.skills.get(skill_name, 0.0)
                card_rect = pygame.Rect(panel_rect.x + 24, y, panel_w - 48, 64)
                pygame.draw.rect(self.screen, PANEL_ALT, card_rect, border_radius=6)
                pygame.draw.rect(self.screen, PANEL_BORDER, card_rect, 1, border_radius=6)

                # Skill Name & Level
                self.draw_text(skill_name.capitalize(), self.FONT_DEFAULT, WHITE, card_rect.x + 18, card_rect.y + 12)
                self.draw_wrapped_lines(skill_desc, self.FONT_SMALL, LIGHT_GREY, card_rect.x + 18, card_rect.y + 38, card_rect.width - 240, 16, 1)

                # Skill Rating & Meter
                meter_x = card_rect.right - 220
                tier = "Master" if val >= 50 else ("Pro" if val >= 30 else ("Adept" if val >= 15 else "Novice"))
                self.draw_badge(tier, meter_x - 70, card_rect.y + 20, bg_color=PANEL_HEADER, text_color=CYAN)
                self.draw_meter(f"{val:.1f}/100", val, 100, meter_x, card_rect.y + 14, 200, CYAN)

                y += 74

            self.draw_text("Press ESC or Click to return", self.FONT_SMALL, GREY, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 24, centered=True)
            self.update_display()

    def draw_career_overview(self, data):
        """A factual record; the player sets their own ambitions."""
        lines = [f"{label}: {value}" for label, value in data.get("summary_rows", [])]
        if data.get("milestones"):
            lines += ["", "CATALOG & STANDING"]
        lines += [f"{item['label']}: {'Established' if item.get('done') else 'Not yet recorded'}"
                  for item in data.get("milestones", [])]
        lines += ["", "BUSINESS"]
        lines += [f"{item['label']}: {item['value']}" for item in data.get("opportunities", [])]
        self.interface.read_document("Career record", "\n\n".join(lines))

    def draw_inventory_screen(self, player):
        """Displays player inventory and gear load."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    running = False
                if event.type == pygame.MOUSEBUTTONUP:
                    running = False

            self.clear_screen()
            self.draw_choice_background()

            # Top HUD
            date_str = get_current_time_str(date_only=True)
            loc_str = player.current_poi.name if getattr(player, "current_poi", None) else getattr(player.current_location, "name", "On the road")
            self.draw_hud(player, date_str, loc_str, "Inventory", "Inspect carried gear, instruments, and consumables")

            panel_w = 880
            panel_h = SCREEN_HEIGHT - 120 - 48
            panel_rect = pygame.Rect((SCREEN_WIDTH - panel_w) // 2, 104, panel_w, panel_h)
            self.draw_panel(panel_rect, "Inventory Loadout", ORANGE)

            current_load = player.get_current_gear_load() if hasattr(player, "get_current_gear_load") else len(player.gear_inventory)
            max_capacity = player.get_current_gear_capacity() if hasattr(player, "get_current_gear_capacity") else 10
            self.draw_meter(f"Carried Load", current_load, max_capacity, panel_rect.x + 24, panel_rect.y + 54, 280, ORANGE)

            y = panel_rect.y + 110
            if not player.gear_inventory:
                self.draw_text("Your gear inventory is empty.", self.FONT_DEFAULT, GREY, panel_rect.x + 24, y)
            else:
                for item in player.gear_inventory[:6]:
                    card_rect = pygame.Rect(panel_rect.x + 24, y, panel_w - 48, 54)
                    pygame.draw.rect(self.screen, PANEL_ALT, card_rect, border_radius=6)
                    pygame.draw.rect(self.screen, PANEL_BORDER, card_rect, 1, border_radius=6)

                    self.draw_text(item.name, self.FONT_DEFAULT, WHITE, card_rect.x + 16, card_rect.y + 10)
                    desc_lines = self.wrap_text(getattr(item, "description", ""), self.FONT_SMALL, card_rect.width - 200)
                    self.draw_text(desc_lines[0] if desc_lines else "", self.FONT_SMALL, LIGHT_GREY, card_rect.x + 16, card_rect.y + 32)

                    gear_type = getattr(item, "gear_type", "ITEM")
                    self.draw_badge(gear_type, card_rect.right - 140, card_rect.y + 14, bg_color=PANEL_HEADER, text_color=YELLOW)

                    y += 62

            self.draw_text("Press ESC or Click to return", self.FONT_SMALL, GREY, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 24, centered=True)
            self.update_display()

    def draw_band_screen(self, band):
        """Displays Band lineup and chemistry."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    running = False
                if event.type == pygame.MOUSEBUTTONUP:
                    running = False

            self.clear_screen()
            self.draw_choice_background()

            panel_w = 900
            panel_h = SCREEN_HEIGHT - 120
            panel_rect = pygame.Rect((SCREEN_WIDTH - panel_w) // 2, 60, panel_w, panel_h)
            band_name = band.name if band else "No Active Band"
            self.draw_panel(panel_rect, f"Band Lineup: {band_name}", PURPLE)

            if not band or not band.members:
                self.draw_text("You are currently a solo artist. Recruit musicians in Explore > Venues & Hangouts.", self.FONT_DEFAULT, LIGHT_GREY, panel_rect.x + 24, panel_rect.y + 60)
            else:
                y = panel_rect.y + 60
                for member in band.members[:4]:
                    card_rect = pygame.Rect(panel_rect.x + 24, y, panel_w - 48, 80)
                    pygame.draw.rect(self.screen, PANEL_ALT, card_rect, border_radius=6)
                    pygame.draw.rect(self.screen, PANEL_BORDER, card_rect, 1, border_radius=6)

                    self.draw_text(member.name, self.FONT_DEFAULT, WHITE, card_rect.x + 16, card_rect.y + 12)
                    role = getattr(member, "role", "Musician")
                    self.draw_badge(role, card_rect.x + 16, card_rect.y + 42, bg_color=PANEL_HEADER, text_color=CYAN)

                    # Skills snippet
                    skills_str = ", ".join([f"{k.capitalize()}: {v}" for k, v in getattr(member, "skills", {}).items()])
                    self.draw_text(skills_str, self.FONT_SMALL, LIGHT_GREY, card_rect.x + 120, card_rect.y + 44)

                    y += 90

            self.draw_text("Press ESC or Click to return", self.FONT_SMALL, GREY, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 24, centered=True)
            self.update_display()

    def draw_contact_details_screen(self, npc):
        """Displays detailed NPC contact card."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    running = False
                if event.type == pygame.MOUSEBUTTONUP:
                    running = False

            self.clear_screen()
            self.draw_choice_background()

            card_w = 640
            card_h = 420
            card_rect = pygame.Rect((SCREEN_WIDTH - card_w) // 2, (SCREEN_HEIGHT - card_h) // 2, card_w, card_h)
            self.draw_panel(card_rect, f"Contact Details: {npc.name}", BLUE)

            y = card_rect.y + 60
            rel_name = getattr(npc.relationship_with_player, "name", "Contact")
            rel_score = getattr(npc, "relationship_score", 50)
            self.draw_text(f"Status: {rel_name}", self.FONT_DEFAULT, WHITE, card_rect.x + 24, y)
            y += 36
            self.draw_meter("Relationship", rel_score, 100, card_rect.x + 24, y, card_w - 48, EMERALD)
            y += 60

            if getattr(npc, "skills", None):
                self.draw_text("Known Skills:", self.FONT_LOG, WHITE, card_rect.x + 24, y)
                y += 24
                for skill, val in npc.skills.items():
                    self.draw_text(f"• {skill.capitalize()}: {val}", self.FONT_SMALL, LIGHT_GREY, card_rect.x + 24, y)
                    y += 20

            self.draw_text("Press ESC or Click to return", self.FONT_SMALL, GREY, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 24, centered=True)
            self.update_display()

    def draw_schedule_screen(self, scheduled_items):
        """Accept either a player or an event list, including long tour calendars."""
        if hasattr(scheduled_items, 'schedule'):
            scheduled_items = scheduled_items.schedule.scheduled_items
        self.interface.read_document('Calendar', '\n\n'.join(str(e) for e in scheduled_items)
                                     or 'Your calendar is clear.')

    def draw_text_viewer(self, text_content):
        self.interface.read_document("Notebook", text_content)
        if self.game and self.game.game_state == "view_text":
            self.game.game_state = "main_menu"

    def draw_dialogue_screen(self, npc_name, conversation_history, player_input):
        """Renders stylized NPC dialogue box."""
        self.clear_screen()
        self.draw_choice_background()

        panel_w = 880
        panel_h = SCREEN_HEIGHT - 120
        panel_rect = pygame.Rect((SCREEN_WIDTH - panel_w) // 2, 60, panel_w, panel_h)
        self.draw_panel(panel_rect, f"Conversation: {npc_name}", CYAN)

        y = panel_rect.y + 60
        for line in conversation_history[-8:]:
            self.draw_text(line, self.FONT_DEFAULT, WHITE, panel_rect.x + 24, y)
            y += 34

        input_box = pygame.Rect(panel_rect.x + 24, panel_rect.bottom - 60, panel_w - 48, 44)
        pygame.draw.rect(self.screen, PANEL_ALT, input_box, border_radius=6)
        pygame.draw.rect(self.screen, CYAN, input_box, 1, border_radius=6)
        self.draw_text(f"> {player_input}", self.FONT_DEFAULT, YELLOW, input_box.x + 14, input_box.y + 11)

    def present_travel_choices(self, options, data):
        """Presents travel itinerary and route choices."""
        context = {
            "eyebrow": data.get("eyebrow", "Travel in Progress"),
            "subtitle": f"{int(data.get('progress_pct', 0) * 100)}% complete / {data.get('progress_label', '')}",
            "accent": data.get("accent", ORANGE),
            "panel_title": "Trip Status",
            "details": [
                f"Progress: {int(data.get('progress_pct', 0) * 100)}% ({data.get('progress_label', '')})",
                f"Status: {data.get('condition_label', '')}",
            ] + data.get("notes", [])[:4]
        }
        return self.present_choices(options, data.get("title", "Traveling"), context=context)

    def draw_crowd_hype_gauge(self, hype_value: float, x=40, y=180, width=300, height=24):
        """Draws the live concert crowd hype meter."""
        rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (20, 26, 38), rect, border_radius=6)
        pct = max(0.0, min(1.0, float(hype_value) / 100.0))
        fill_width = int(width * pct)
        if fill_width > 0:
            fill_rect = pygame.Rect(x, y, fill_width, height)
            color = GREEN if pct >= 0.75 else (YELLOW if pct >= 0.4 else RED)
            pygame.draw.rect(self.screen, color, fill_rect, border_radius=6)
        pygame.draw.rect(self.screen, PANEL_BORDER, rect, 2, border_radius=6)
        label = f"Crowd Hype: {int(hype_value)}/100"
        self.draw_text(label, self.FONT_SMALL, WHITE, x + width // 2, y + height // 2, centered=True)

    def draw_ascii_art(self, art_lines, x, y, color=WHITE):
        line_height = self.FONT_ASCII.get_linesize()
        for i, line in enumerate(art_lines):
            self.draw_text(line, self.FONT_ASCII, color, x, y + (i * line_height))

    def get_current_time_str(self, date_only=False):
        return get_current_time_str(date_only)

    def draw_shell_backdrop_layout(self, shell_state, backdrop_renderer=None, backdrop_spec=None):
        """Render a lightweight shell composition: backdrop top, shell text bottom."""
        self.clear_screen()
        self.draw_choice_background()

        top_h = int(SCREEN_HEIGHT * 0.62)
        if backdrop_renderer and backdrop_spec:
            backdrop_renderer.draw(self.screen, backdrop_spec, (0, 0, SCREEN_WIDTH, top_h), tick=pygame.time.get_ticks())
            title = backdrop_spec.overlay.get("title") or backdrop_spec.label
            subtitle = backdrop_spec.overlay.get("subtitle", "")
            self.draw_text(title, self.FONT_DEFAULT, WHITE, 18, 14)
            if subtitle:
                self.draw_text(subtitle, self.FONT_LOG, LIGHT_GREY, 18, 40)

        bottom = pygame.Rect(0, top_h, SCREEN_WIDTH, SCREEN_HEIGHT - top_h)
        self.draw_panel(bottom, title="Life")

        context = shell_state.get("top_context", {})
        self.draw_text(context.get("headline", ""), self.FONT_LOG, WHITE, 16, top_h + 28)
        tag_line = " • ".join(context.get("tags", [])[:4])
        if tag_line:
            self.draw_text(tag_line, self.FONT_LOG, LIGHT_GREY, 16, top_h + 52)
