import pygame
import sys
from game.portrait import Portrait
from game.game_time import get_current_time_str

# --- Constants ---
SCREEN_WIDTH = 1160
SCREEN_HEIGHT = 680
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (128, 128, 128)
LIGHT_GREY = (200, 200, 200)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (90, 150, 255)
YELLOW = (255, 215, 90)
ORANGE = (255, 140, 70)
PANEL_BG = (18, 22, 30)
PANEL_ALT = (28, 34, 44)

# Fonts
pygame.font.init()
FONT_DEFAULT = pygame.font.Font(None, 32)
FONT_TITLE = pygame.font.Font(None, 48)
FONT_LOG = pygame.font.Font(None, 24)
FONT_ASCII = pygame.font.SysFont('monospace', 18)

class PygameUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Music-Life Sim")
        self.clock = pygame.time.Clock()
        self.log_messages = []
        self.portrait = Portrait(self.screen)

        # Expose fonts as instance attributes
        self.FONT_DEFAULT = FONT_DEFAULT
        self.FONT_TITLE = FONT_TITLE
        self.FONT_LOG = FONT_LOG
        self.FONT_ASCII = FONT_ASCII

    def clear_screen(self):
        self.screen.fill(BLACK)

    def update_display(self):
        pygame.display.flip()
        self.clock.tick(FPS)

    def draw_text(self, text, font, color, x, y, centered=False):
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect()
        if centered:
            text_rect.center = (x, y)
        else:
            text_rect.topleft = (x, y)
        self.screen.blit(text_surface, text_rect)

    def wrap_text(self, text, font, max_width):
        words = text.split()
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

    def draw_meter(self, label, value, maximum, x, y, width, color):
        pct = 0 if maximum <= 0 else max(0.0, min(1.0, value / maximum))
        self.draw_text(f"{label}: {int(value)}/{int(maximum)}", self.FONT_LOG, WHITE, x, y)
        bar_rect = pygame.Rect(x, y + 22, width, 12)
        pygame.draw.rect(self.screen, PANEL_ALT, bar_rect)
        fill_rect = pygame.Rect(x, y + 22, int(width * pct), 12)
        pygame.draw.rect(self.screen, color, fill_rect)
        pygame.draw.rect(self.screen, LIGHT_GREY, bar_rect, 1)

    def draw_panel(self, rect, title=None, accent=BLUE, alpha=235):
        panel_surface = pygame.Surface((rect.width, rect.height))
        panel_surface.set_alpha(alpha)
        panel_surface.fill(PANEL_BG)
        self.screen.blit(panel_surface, rect.topleft)
        pygame.draw.rect(self.screen, PANEL_ALT, rect, 2, border_radius=10)
        pygame.draw.line(self.screen, accent, (rect.x + 18, rect.y + 18), (rect.x + rect.width - 18, rect.y + 18), 3)
        if title:
            self.draw_text(title, self.FONT_LOG, WHITE, rect.x + 20, rect.y + 28)

    def draw_wrapped_lines(self, text, font, color, x, y, max_width, line_height=None, max_lines=None):
        lines = self.wrap_text(text, font, max_width)
        if max_lines is not None:
            lines = lines[:max_lines]
        line_height = line_height or font.get_linesize()
        for idx, line in enumerate(lines):
            self.draw_text(line, font, color, x, y + (idx * line_height))
        return y + (len(lines) * line_height)

    def draw_choice_background(self):
        self.screen.fill((8, 10, 16))
        pygame.draw.circle(self.screen, (24, 44, 68), (180, 140), 170)
        pygame.draw.circle(self.screen, (48, 32, 24), (1120, 120), 150)
        pygame.draw.circle(self.screen, (18, 28, 22), (1040, 620), 220)
        pygame.draw.rect(self.screen, (12, 16, 24), (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

    def draw_career_overview(self, data):
        self.clear_screen()
        self.draw_choice_background()
        self.draw_text("Career Overview", self.FONT_TITLE, WHITE, 72, 54)
        self.draw_text(data.get("subtitle", ""), self.FONT_LOG, LIGHT_GREY, 74, 100)

        summary_rect = pygame.Rect(60, 148, 360, 380)
        milestones_rect = pygame.Rect(450, 148, 360, 380)
        opportunities_rect = pygame.Rect(840, 148, 380, 380)
        footer_rect = pygame.Rect(60, 552, 1160, 110)

        self.draw_panel(summary_rect, "Current Standing", YELLOW)
        y_pos = summary_rect.y + 66
        for label, value in data.get("summary_rows", []):
            self.draw_text(label, self.FONT_LOG, LIGHT_GREY, summary_rect.x + 22, y_pos)
            self.draw_text(str(value), self.FONT_DEFAULT, WHITE, summary_rect.x + 22, y_pos + 22)
            y_pos += 54

        self.draw_panel(milestones_rect, "Milestones", BLUE)
        y_pos = milestones_rect.y + 62
        for item in data.get("milestones", []):
            status_color = GREEN if item.get("done") else LIGHT_GREY
            bullet = "DONE" if item.get("done") else "NEXT"
            self.draw_text(f"{bullet}  {item['label']}", self.FONT_LOG, status_color, milestones_rect.x + 22, y_pos)
            y_pos = self.draw_wrapped_lines(item["detail"], self.FONT_LOG, WHITE, milestones_rect.x + 22, y_pos + 22, milestones_rect.width - 44, 20, 2) + 12

        self.draw_panel(opportunities_rect, "Opportunity Track", ORANGE)
        y_pos = opportunities_rect.y + 62
        for item in data.get("opportunities", []):
            self.draw_text(item["label"], self.FONT_LOG, LIGHT_GREY, opportunities_rect.x + 22, y_pos)
            self.draw_text(item["value"], self.FONT_DEFAULT, WHITE, opportunities_rect.x + 22, y_pos + 20)
            y_pos += 56
        y_pos += 6
        for hint in data.get("focus_items", []):
            y_pos = self.draw_wrapped_lines(f"- {hint}", self.FONT_LOG, LIGHT_GREY, opportunities_rect.x + 22, y_pos, opportunities_rect.width - 44, 20, 2) + 8

        self.draw_panel(footer_rect, "Current Focus", BLUE)
        self.draw_wrapped_lines(data.get("focus_summary", ""), self.FONT_DEFAULT, WHITE, footer_rect.x + 22, footer_rect.y + 58, footer_rect.width - 44, 28, 2)
        self.draw_text("Press ESC to return", self.FONT_LOG, LIGHT_GREY, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 34, centered=True)

    def draw_hud(self, player, date_str, location_str, next_event_str, progress_hint):
        hud_height = 174
        hud_surface = pygame.Surface((SCREEN_WIDTH, hud_height))
        hud_surface.set_alpha(245)
        hud_surface.fill(PANEL_BG)
        self.screen.blit(hud_surface, (0, 0))

        pygame.draw.line(self.screen, PANEL_ALT, (420, 12), (420, hud_height - 12), 2)
        pygame.draw.line(self.screen, PANEL_ALT, (930, 12), (930, hud_height - 12), 2)

        self.draw_text(date_str, self.FONT_DEFAULT, WHITE, 20, 14)
        self.draw_text(location_str, self.FONT_LOG, LIGHT_GREY, 20, 48)
        next_lines = self.wrap_text(f"Next: {next_event_str}", self.FONT_LOG, 360)
        for idx, line in enumerate(next_lines[:2]):
            self.draw_text(line, self.FONT_LOG, LIGHT_GREY, 20, 74 + (idx * 22))

        self.draw_text(f"Cash: ${player.money}", self.FONT_DEFAULT, YELLOW, 20, 126)
        self.draw_text(f"Fame: {player.fame}", self.FONT_LOG, WHITE, 170, 130)
        self.draw_text(f"Health: {player.health}/100", self.FONT_LOG, WHITE, 270, 130)
        self.draw_text(f"Inspiration: {player.inspiration}/100", self.FONT_LOG, WHITE, 270, 148)

        self.draw_meter("Energy", player.energy, 100, 445, 20, 210, GREEN)
        self.draw_meter("Stress", player.stress, 100, 445, 58, 210, RED)
        self.draw_meter("Hunger", player.hunger, 100, 445, 96, 210, YELLOW)
        self.draw_meter("Comfort", player.comfort, 100, 445, 134, 210, BLUE)

        songs_written = len(player.songs_written)
        songs_recorded = sum(1 for song in player.songs_written if song.is_recorded)
        songs_released = sum(1 for song in player.songs_written if song.is_released)
        top_buzz = max((song.buzz_score for song in player.songs_written), default=0)
        self.draw_text("Career Progress", self.FONT_LOG, WHITE, 955, 18)
        self.draw_text(f"Songs: {songs_written}", self.FONT_LOG, LIGHT_GREY, 955, 46)
        self.draw_text(f"Recorded: {songs_recorded}", self.FONT_LOG, LIGHT_GREY, 955, 68)
        self.draw_text(f"Released: {songs_released}", self.FONT_LOG, LIGHT_GREY, 955, 90)
        self.draw_text(f"Top Buzz: {int(top_buzz)}", self.FONT_LOG, LIGHT_GREY, 955, 112)

        portrait_rect = pygame.Rect(SCREEN_WIDTH - 110, 24, 72, 72)
        self.portrait.draw(portrait_rect.x, portrait_rect.y, portrait_rect.width, portrait_rect.height, player.hair_length, player.beard_length)
        pygame.draw.rect(self.screen, WHITE, portrait_rect, 2)
        self.draw_text(f"Hair {player.hair_length}", self.FONT_LOG, LIGHT_GREY, 1048, 28)
        self.draw_text(f"Beard {player.beard_length}", self.FONT_LOG, LIGHT_GREY, 1048, 52)

        hint_lines = self.wrap_text(f"Next step: {progress_hint}", self.FONT_LOG, SCREEN_WIDTH - 40)
        for idx, line in enumerate(hint_lines[:2]):
            self.draw_text(line, self.FONT_LOG, WHITE if idx == 0 else LIGHT_GREY, 20, 152 + (idx * 18))

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

        # Three compact columns for schedule / actions / feed
        col_w = SCREEN_WIDTH // 3
        today = shell_state.get("schedule", {}).get("Today", [])[:4]
        actions = shell_state.get("scene", {}).get("actions", [])[:4]
        feed = shell_state.get("world_feed", [])[:4]

        self.draw_text("Today", self.FONT_LOG, YELLOW, 16, top_h + 84)
        for i, line in enumerate(today):
            self.draw_text(f"- {line}", self.FONT_LOG, WHITE, 16, top_h + 106 + i * 20)

        self.draw_text("Actions", self.FONT_LOG, YELLOW, 16 + col_w, top_h + 84)
        for i, line in enumerate(actions):
            self.draw_text(f"- {line}", self.FONT_LOG, WHITE, 16 + col_w, top_h + 106 + i * 20)

        self.draw_text("World", self.FONT_LOG, YELLOW, 16 + col_w * 2, top_h + 84)
        for i, line in enumerate(feed):
            self.draw_text(f"- {line}", self.FONT_LOG, WHITE, 16 + col_w * 2, top_h + 106 + i * 20)

    def draw_ascii_art(self, art_lines, x, y, color=WHITE):
        line_height = FONT_ASCII.get_linesize()
        for i, line in enumerate(art_lines):
            self.draw_text(line, FONT_ASCII, color, x, y + (i * line_height))

    def add_log_message(self, message):
        self.log_messages.insert(0, message)
        if len(self.log_messages) > 5:
            self.log_messages.pop()

    def draw_log(self):
        log_surface = pygame.Surface((SCREEN_WIDTH, 140))
        log_surface.set_alpha(128)
        log_surface.fill(BLACK)
        self.screen.blit(log_surface, (0, SCREEN_HEIGHT - 140))

        self.draw_text("Recent Activity", self.FONT_LOG, WHITE, 20, SCREEN_HEIGHT - 138)

        log_y_start = SCREEN_HEIGHT - 114
        for i, msg in enumerate(self.log_messages):
            self.draw_text(msg, FONT_LOG, LIGHT_GREY, 20, log_y_start + (i * 20))

        pygame.draw.rect(self.screen, WHITE, (0, SCREEN_HEIGHT - 140, SCREEN_WIDTH, 140), 2)

    def draw_skills_screen(self, player):
        self.draw_text("Skills", FONT_TITLE, WHITE, SCREEN_WIDTH // 2, 50, centered=True)

        y_pos = 120
        for skill, value in player.skills.items():
            self.draw_text(f"{skill.capitalize()}: {value:.1f}", FONT_DEFAULT, WHITE, 100, y_pos)
            y_pos += 40

        self.draw_text("Press ESC to go back", FONT_DEFAULT, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50, centered=True)

    def draw_schedule_screen(self, scheduled_items):
        self.draw_text("Upcoming Schedule", FONT_TITLE, WHITE, SCREEN_WIDTH // 2, 50, centered=True)

        y_pos = 120
        if not scheduled_items:
            self.draw_text("Your schedule is empty.", FONT_DEFAULT, WHITE, 100, y_pos)
        else:
            for item in scheduled_items:
                self.draw_text(str(item), FONT_DEFAULT, WHITE, 100, y_pos)
                y_pos += 40

        self.draw_text("Press ESC to go back", FONT_DEFAULT, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50, centered=True)

    def draw_inventory_screen(self, player):
        self.draw_text("Inventory", FONT_TITLE, WHITE, SCREEN_WIDTH // 2, 50, centered=True)

        y_pos = 120
        if not player.gear_inventory:
            self.draw_text("Your inventory is empty.", FONT_DEFAULT, WHITE, 100, y_pos)
        else:
            for item in player.gear_inventory:
                self.draw_text(f"- {item.name} (Size: {item.size})", FONT_DEFAULT, WHITE, 100, y_pos)
                y_pos += 40

        self.draw_text(f"Capacity: {player.get_current_gear_load()}/{player.get_current_gear_capacity()}", FONT_DEFAULT, WHITE, 100, SCREEN_HEIGHT - 100)
        self.draw_text("Press ESC to go back", FONT_DEFAULT, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50, centered=True)

    def draw_character_stats(self, player):
        self.draw_text("Character Stats", FONT_TITLE, WHITE, SCREEN_WIDTH // 2, 50, centered=True)

        y_pos = 120
        stats = {
            "Name": player.name,
            "Age": player.age,
            "Fame": player.fame,
            "Money": f"${player.money}",
            "Energy": f"{player.energy}/100",
            "Stress": f"{player.stress}/100",
            "Hunger": f"{player.hunger}/100",
            "Comfort": f"{player.comfort}/100",
            "Homesickness": f"{player.homesickness}/100",
        }

        if player.vocal_strain > 0:
            stats["Vocal Strain"] = f"{player.vocal_strain}/100"
        if player.wrist_strain > 0:
            stats["Wrist Strain"] = f"{player.wrist_strain}/100"
        if player.substance_dependency > 0:
            stats["Dependency"] = f"{player.substance_dependency}/100"

        for key, value in stats.items():
            color = RED if "Strain" in key or "Dependency" in key else WHITE
            self.draw_text(f"{key}: {value}", FONT_DEFAULT, color, 100, y_pos)
            y_pos += 40

        self.draw_text("Press ESC to go back", FONT_DEFAULT, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50, centered=True)

    def draw_band_screen(self, band):
        self.draw_text(band.name, FONT_TITLE, WHITE, SCREEN_WIDTH // 2, 50, centered=True)

        # Members
        self.draw_text("Members:", FONT_DEFAULT, WHITE, 100, 120)
        y_pos = 160
        for member in band.members:
            self.draw_text(f"- {member.name}", FONT_DEFAULT, WHITE, 120, y_pos)
            y_pos += 30
            # Draw member skills
            for skill, value in member.skills.items():
                self.draw_text(f"  {skill.capitalize()}: {value}", FONT_LOG, LIGHT_GREY, 140, y_pos)
                y_pos += 25
            y_pos += 15

        # Average Band Skills
        self.draw_text("Average Band Skills:", FONT_DEFAULT, WHITE, 600, 120)
        y_pos = 160
        for skill, value in band.band_skills.items():
            self.draw_text(f"{skill.capitalize()}: {value:.1f}", FONT_DEFAULT, WHITE, 620, y_pos)
            y_pos += 40

        self.draw_text("Press ESC to go back", FONT_DEFAULT, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50, centered=True)

    def draw_contact_details_screen(self, npc):
        self.draw_text(npc.name, FONT_TITLE, WHITE, SCREEN_WIDTH // 2, 50, centered=True)

        y_pos = 120
        self.draw_text(f"Relationship: {npc.relationship_with_player.name} ({npc.relationship_score}/100)", FONT_DEFAULT, WHITE, 100, y_pos)
        y_pos += 60

        if npc.skills:
            self.draw_text("Skills:", FONT_DEFAULT, WHITE, 100, y_pos)
            y_pos += 40
            for skill, value in npc.skills.items():
                self.draw_text(f"- {skill.capitalize()}: {value}", FONT_DEFAULT, LIGHT_GREY, 120, y_pos)
                y_pos += 40

        self.draw_text("Press ESC to go back", FONT_DEFAULT, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50, centered=True)

    def get_current_time_str(self, date_only=False):
        return get_current_time_str(date_only)

    def get_text_input(self, prompt, context=None):
        text = ""
        context = context or {}
        accent = context.get("accent", BLUE)
        subtitle = context.get("subtitle", "Type your answer, then press Enter to confirm.")
        panel_title = context.get("panel_title", "Entry")
        notes = context.get("details", [])
        placeholder = context.get("placeholder", "")
        max_length = context.get("max_length", 32)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        return text.strip()
                    if event.key == pygame.K_ESCAPE:
                        return text.strip()
                    if event.key == pygame.K_BACKSPACE:
                        text = text[:-1]
                    elif event.unicode and event.unicode.isprintable() and len(text) < max_length:
                        text += event.unicode

            self.clear_screen()
            self.draw_choice_background()

            hero_rect = pygame.Rect(60, 48, 1160, 128)
            input_rect = pygame.Rect(88, 228, 720, 90)
            notes_rect = pygame.Rect(840, 228, 360, 270)
            frame_rect = pygame.Rect(72, 212, 752, 122)

            self.draw_panel(hero_rect, None, accent)
            self.draw_text("Character Setup", self.FONT_LOG, accent, 82, 66)
            self.draw_text(prompt, self.FONT_TITLE, WHITE, 82, 92)
            self.draw_wrapped_lines(subtitle, self.FONT_LOG, LIGHT_GREY, 82, 138, 720, 22, 2)
            self.draw_text("Enter confirms. Esc keeps current text and continues.", self.FONT_LOG, LIGHT_GREY, SCREEN_WIDTH // 2, 190, centered=True)

            self.draw_panel(notes_rect, panel_title, accent)
            note_y = notes_rect.y + 62
            for note in notes[:5]:
                note_y = self.draw_wrapped_lines(note, self.FONT_LOG, WHITE, notes_rect.x + 22, note_y, notes_rect.width - 44, 22, 3) + 12

            pygame.draw.rect(self.screen, PANEL_ALT, frame_rect, border_radius=10)
            pygame.draw.rect(self.screen, accent, frame_rect, 3, border_radius=10)
            pygame.draw.rect(self.screen, (12, 16, 24), input_rect, border_radius=8)

            displayed_text = text if text else placeholder
            text_color = WHITE if text else GREY
            self.draw_text(displayed_text, self.FONT_DEFAULT, text_color, input_rect.x + 22, input_rect.y + 29)

            if (pygame.time.get_ticks() // 500) % 2 == 0 and len(text) < max_length:
                caret_x = input_rect.x + 22 + self.FONT_DEFAULT.size(text)[0]
                pygame.draw.line(self.screen, accent, (caret_x, input_rect.y + 20), (caret_x, input_rect.y + 62), 2)

            self.draw_text(f"{len(text)}/{max_length}", self.FONT_LOG, LIGHT_GREY, input_rect.right - 18, input_rect.bottom + 12, centered=True)
            self.update_display()

    def draw_dialogue_screen(self, npc_name, conversation_history, player_input):
        self.draw_text(f"Talking to {npc_name}", FONT_TITLE, WHITE, SCREEN_WIDTH // 2, 50, centered=True)

        y_pos = 120
        for line in conversation_history:
            self.draw_text(line, FONT_DEFAULT, WHITE, 100, y_pos)
            y_pos += 40

        self.draw_text(f"> {player_input}", FONT_DEFAULT, WHITE, 100, SCREEN_HEIGHT - 100)

    def draw_text_viewer(self, text_content):
        self.clear_screen()
        self.draw_text("Viewing Document", FONT_TITLE, WHITE, SCREEN_WIDTH // 2, 50, centered=True)

        y_pos = 120
        lines = text_content.split('\n')
        for line in lines:
            self.draw_text(line, FONT_LOG, WHITE, 50, y_pos)
            y_pos += 25

        self.draw_text("Press Enter or ESC to go back", FONT_DEFAULT, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50, centered=True)

    def present_travel_choices(self, options, data):
        selected_index = 0
        keys = list(options.keys())
        values = list(options.values())
        buttons = []

        button_width = 420
        button_height = 48
        spacing = 14
        start_x = 78
        start_y = 430
        for i in range(len(options)):
            buttons.append(pygame.Rect(start_x, start_y + i * (button_height + spacing), button_width, button_height))

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        selected_index = (selected_index - 1) % len(options)
                    elif event.key == pygame.K_DOWN:
                        selected_index = (selected_index + 1) % len(options)
                    elif event.key == pygame.K_RETURN:
                        return keys[selected_index]
                if event.type == pygame.MOUSEMOTION:
                    for i, button_rect in enumerate(buttons):
                        if button_rect.collidepoint(event.pos):
                            selected_index = i
                if event.type == pygame.MOUSEBUTTONUP:
                    for i, button_rect in enumerate(buttons):
                        if button_rect.collidepoint(event.pos):
                            return keys[i]

            self.clear_screen()
            self.draw_choice_background()

            hero_rect = pygame.Rect(50, 40, 1060, 138)
            route_rect = pygame.Rect(50, 204, 480, 190)
            status_rect = pygame.Rect(554, 204, 556, 190)
            button_panel_rect = pygame.Rect(50, 404, 480, 220)
            notes_rect = pygame.Rect(554, 404, 556, 220)

            accent = data.get("accent", ORANGE)
            self.draw_panel(hero_rect, None, accent)
            self.draw_text(data.get("eyebrow", "On The Move"), self.FONT_LOG, accent, 72, 58)
            self.draw_text(data.get("title", "Traveling"), self.FONT_TITLE, WHITE, 72, 84)
            self.draw_wrapped_lines(data.get("subtitle", ""), self.FONT_LOG, LIGHT_GREY, 72, 130, 880, 22, 2)

            self.draw_panel(route_rect, "Route", accent)
            route_y = route_rect.y + 62
            for label, value in data.get("route_rows", []):
                self.draw_text(label, self.FONT_LOG, LIGHT_GREY, route_rect.x + 22, route_y)
                self.draw_text(str(value), self.FONT_DEFAULT, WHITE, route_rect.x + 22, route_y + 20)
                route_y += 54

            self.draw_panel(status_rect, "Progress", BLUE)
            self.draw_text(f"{int(data.get('progress_pct', 0) * 100)}% Complete", self.FONT_TITLE, WHITE, status_rect.x + 22, status_rect.y + 58)
            progress_bar_rect = pygame.Rect(status_rect.x + 22, status_rect.y + 112, status_rect.width - 44, 20)
            pygame.draw.rect(self.screen, PANEL_ALT, progress_bar_rect, border_radius=8)
            fill_width = int(progress_bar_rect.width * max(0.0, min(1.0, data.get("progress_pct", 0))))
            pygame.draw.rect(self.screen, accent, pygame.Rect(progress_bar_rect.x, progress_bar_rect.y, fill_width, progress_bar_rect.height), border_radius=8)
            pygame.draw.rect(self.screen, LIGHT_GREY, progress_bar_rect, 1, border_radius=8)
            self.draw_text(data.get("progress_label", ""), self.FONT_LOG, WHITE, status_rect.x + 22, status_rect.y + 146)
            self.draw_text(data.get("condition_label", ""), self.FONT_LOG, LIGHT_GREY, status_rect.x + 22, status_rect.y + 172)

            self.draw_panel(button_panel_rect, "What You Can Do", accent)
            for i, text in enumerate(values):
                button_rect = buttons[i]
                is_selected = (i == selected_index)
                bg_color = PANEL_ALT if not is_selected else (52, 66, 86)
                pygame.draw.rect(self.screen, bg_color, button_rect, border_radius=8)
                border_color = accent if is_selected else GREY
                pygame.draw.rect(self.screen, border_color, button_rect, 2 if not is_selected else 3, border_radius=8)
                self.draw_text(text, self.FONT_DEFAULT, WHITE if is_selected else LIGHT_GREY, button_rect.centerx, button_rect.centery, centered=True)

            self.draw_panel(notes_rect, "Trip Notes", BLUE)
            note_y = notes_rect.y + 62
            for note in data.get("notes", [])[:6]:
                note_y = self.draw_wrapped_lines(note, self.FONT_LOG, WHITE, notes_rect.x + 22, note_y, notes_rect.width - 44, 22, 2) + 10

            self.draw_text("Use arrow keys and Enter, or click.", self.FONT_LOG, LIGHT_GREY, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 26, centered=True)
            self.update_display()

    def present_choices(self, options, title, context=None):
        selected_index = 0
        buttons = []
        keys = list(options.keys())
        values = list(options.values())
        context = context or {}

        # Calculate dynamic width
        max_text_width = 0
        for text in values:
            w = self.FONT_DEFAULT.size(text)[0]
            if w > max_text_width:
                max_text_width = w

        has_side_panel = bool(context)
        button_width = 560 if has_side_panel else max(420, min(760, max_text_width + 80))
        button_height = 44 if len(options) > 8 else 50
        spacing = 10 if len(options) > 8 else 15
        total_height = len(options) * (button_height + spacing)
        start_y = max(220, min(330, (SCREEN_HEIGHT - total_height) // 2 + 70))
        button_x = 88 if has_side_panel else (SCREEN_WIDTH - button_width) // 2

        for i, (key, text) in enumerate(options.items()):
            x = button_x
            y = start_y + i * (button_height + spacing)
            button_rect = pygame.Rect(x, y, button_width, button_height)
            buttons.append(button_rect)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        selected_index = (selected_index - 1) % len(options)
                    elif event.key == pygame.K_DOWN:
                        selected_index = (selected_index + 1) % len(options)
                    elif event.key == pygame.K_RETURN:
                        return keys[selected_index]
                if event.type == pygame.MOUSEMOTION:
                    for i, button_rect in enumerate(buttons):
                        if button_rect.collidepoint(event.pos):
                            selected_index = i
                if event.type == pygame.MOUSEBUTTONUP:
                    for i, button_rect in enumerate(buttons):
                        if button_rect.collidepoint(event.pos):
                            return keys[i]

            self.clear_screen()
            self.draw_choice_background()
            hero_rect = pygame.Rect(60, 48, 1160, 128)
            self.draw_panel(hero_rect, None, context.get("accent", BLUE))
            eyebrow = context.get("eyebrow")
            if eyebrow:
                self.draw_text(eyebrow, self.FONT_LOG, context.get("accent", BLUE), 82, 66)
            title_lines = self.wrap_text(title, self.FONT_TITLE, SCREEN_WIDTH - 140)
            title_y = 92 if eyebrow else 78
            for i, line in enumerate(title_lines[:2]):
                self.draw_text(line, self.FONT_TITLE if i == 0 else self.FONT_DEFAULT, WHITE, 82, title_y + (i * 34))
            subtitle = context.get("subtitle")
            if subtitle:
                self.draw_wrapped_lines(subtitle, self.FONT_LOG, LIGHT_GREY, 82, 138, 700, 22, 2)
            self.draw_text(context.get("footer", "Use arrow keys and Enter, or click."), self.FONT_LOG, LIGHT_GREY, SCREEN_WIDTH // 2, 190, centered=True)

            if has_side_panel:
                panel_rect = pygame.Rect(700, 220, 500, 340)
                self.draw_panel(panel_rect, context.get("panel_title", "At a Glance"), context.get("accent", BLUE))
                detail_y = panel_rect.y + 60
                for detail in context.get("details", [])[:6]:
                    detail_y = self.draw_wrapped_lines(detail, self.FONT_LOG, WHITE, panel_rect.x + 22, detail_y, panel_rect.width - 44, 22, 2) + 10

            for i, text in enumerate(values):
                button_rect = buttons[i]
                is_selected = (i == selected_index)

                bg_color = PANEL_ALT if not is_selected else (52, 66, 86)
                pygame.draw.rect(self.screen, bg_color, button_rect, border_radius=8)

                border_color = context.get("accent", WHITE) if is_selected else GREY
                pygame.draw.rect(self.screen, border_color, button_rect, 2 if not is_selected else 3, border_radius=8)

                text_color = WHITE if is_selected else LIGHT_GREY
                text_lines = self.wrap_text(text, self.FONT_DEFAULT, button_rect.width - 30)
                if len(text_lines) == 1:
                    self.draw_text(text_lines[0], self.FONT_DEFAULT, text_color, button_rect.centerx, button_rect.centery, centered=True)
                else:
                    self.draw_text(text_lines[0], self.FONT_LOG, text_color, button_rect.centerx, button_rect.centery - 10, centered=True)
                    self.draw_text(text_lines[1], self.FONT_LOG, text_color, button_rect.centerx, button_rect.centery + 10, centered=True)

            self.update_display()
