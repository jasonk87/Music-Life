import pygame
import sys
from game.portrait import Portrait
from game.game_time import get_current_time_str

# --- Constants ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (128, 128, 128)
LIGHT_GREY = (200, 200, 200)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

# Fonts
pygame.font.init()
FONT_DEFAULT = pygame.font.Font(None, 32)
FONT_TITLE = pygame.font.Font(None, 48)
FONT_LOG = pygame.font.Font(None, 24)
FONT_ASCII = pygame.font.SysFont('monospace', 18)

class PygameUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
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

    def draw_hud(self, date_str, location_str, next_event_str, money_str, hair_length, beard_length):
        # A semi-transparent background for the HUD
        hud_surface = pygame.Surface((SCREEN_WIDTH, 120)) # Increased height
        hud_surface.set_alpha(128)
        hud_surface.fill(BLACK)
        self.screen.blit(hud_surface, (0, 0))

        # Top-left: Date, Location, Next Event
        self.draw_text(f"Date: {date_str}", self.FONT_DEFAULT, WHITE, 20, 10)
        self.draw_text(f"Location: {location_str}", self.FONT_LOG, LIGHT_GREY, 20, 45)
        self.draw_text(f"Next Up: {next_event_str}", self.FONT_LOG, LIGHT_GREY, 20, 70)

        # Top-right: Money, Portrait, and indicators
        # Dynamic alignment for money/stats to avoid overlap
        portrait_rect = pygame.Rect(SCREEN_WIDTH - 120, 10, 80, 80)

        money_text = f"Money: ${money_str}"
        money_width = self.FONT_DEFAULT.size(money_text)[0]
        # Position left of portrait with 20px padding
        money_x = portrait_rect.left - 20 - money_width

        self.draw_text(money_text, self.FONT_DEFAULT, WHITE, money_x, 10)

        self.portrait.draw(portrait_rect.x, portrait_rect.y, portrait_rect.width, portrait_rect.height, hair_length, beard_length)
        pygame.draw.rect(self.screen, WHITE, portrait_rect, 2)

        hair_text = f"Hair: {str(hair_length)}"
        beard_text = f"Beard: {str(beard_length)}"

        # Align appearance stats with money X (right aligned logic roughly)
        self.draw_text(hair_text, self.FONT_LOG, WHITE, money_x, 45)
        self.draw_text(beard_text, self.FONT_LOG, WHITE, money_x, 70)

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

        log_y_start = SCREEN_HEIGHT - 120
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

        for key, value in stats.items():
            self.draw_text(f"{key}: {value}", FONT_DEFAULT, WHITE, 100, y_pos)
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

    def get_text_input(self, prompt):
        text = ""
        input_active = True
        while input_active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        input_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        text = text[:-1]
                    else:
                        text += event.unicode

            self.clear_screen()
            self.draw_text(prompt, FONT_TITLE, WHITE, SCREEN_WIDTH // 2, 100, centered=True)
            self.draw_text(text, FONT_DEFAULT, WHITE, SCREEN_WIDTH // 2, 200, centered=True)
            self.update_display()
        return text

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

    def present_choices(self, options, title):
        selected_index = 0
        buttons = []
        keys = list(options.keys())
        values = list(options.values())

        # Calculate dynamic width
        max_text_width = 0
        for text in values:
            w = self.FONT_DEFAULT.size(text)[0]
            if w > max_text_width:
                max_text_width = w

        button_width = max(400, max_text_width + 60) # Min 400, plus padding
        button_height = 50
        spacing = 15
        total_height = len(options) * (button_height + spacing)
        start_y = max(150, (SCREEN_HEIGHT - total_height) // 2 + 50) # Center vertically roughly, offset for title

        for i, (key, text) in enumerate(options.items()):
            x = (SCREEN_WIDTH - button_width) // 2
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
            self.draw_text(title, self.FONT_TITLE, WHITE, SCREEN_WIDTH // 2, start_y - 60, centered=True)

            for i, text in enumerate(values):
                button_rect = buttons[i]
                is_selected = (i == selected_index)

                # Draw background for better contrast/smoothness
                bg_color = (30, 30, 30) if not is_selected else (60, 60, 60)
                pygame.draw.rect(self.screen, bg_color, button_rect)

                # Draw Border
                border_color = WHITE if is_selected else GREY
                pygame.draw.rect(self.screen, border_color, button_rect, 2 if not is_selected else 3)

                # Draw Text
                text_color = WHITE if is_selected else LIGHT_GREY
                self.draw_text(text, self.FONT_DEFAULT, text_color, button_rect.centerx, button_rect.centery, centered=True)

            self.update_display()
