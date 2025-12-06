import pygame
import random
from game.game_time import advance_game_time

class PerformanceManager:
    def __init__(self, game_ref, event, song, ui):
        self.game = game_ref
        self.event = event
        self.song = song
        self.ui = ui

        self.state = "setup" # setup, section_intro, player_input, resolution, summary
        self.sections = ["Intro", "Verse 1", "Chorus", "Verse 2", "Chorus", "Bridge", "Chorus", "Outro"]
        self.current_section_index = 0

        # Stats
        self.crowd_hype = 50 # 0-100
        self.band_energy = 100 # 0-100
        self.performance_quality = 0 # Accumulator

        self.log = []
        self.timer = 0
        self.last_action = None
        self.turn_result = ""

    def update(self):
        # Non-blocking timer logic could go here if we were running a realtime loop
        pass

    def get_current_section(self):
        if 0 <= self.current_section_index < len(self.sections):
            return self.sections[self.current_section_index]
        return "Finished"

    def handle_input(self, choice_key):
        if self.state == "player_input":
            self.resolve_action(choice_key)
            self.state = "resolution"
            self.current_section_index += 1
            if self.current_section_index >= len(self.sections):
                self.state = "summary"
            else:
                # In a real-time game we'd wait, but for turn-based menu flow,
                # we might just stay in 'resolution' until user clicks 'continue'
                # or auto-advance. Let's make resolution require a 'continue'.
                pass
        elif self.state == "resolution":
            self.state = "player_input"

    def resolve_action(self, action):
        # Basic logic for actions
        base_skill = self.game.player.skills.get('guitar', 0) + self.game.player.skills.get('vocals', 0)
        roll = random.randint(0, 100) + base_skill

        section = self.get_current_section()

        if action == "safe":
            self.crowd_hype += 2
            self.band_energy -= 2
            self.turn_result = f"You played the {section} cleanly. The crowd nods along."
        elif action == "hype":
            if roll > 50:
                self.crowd_hype += 10
                self.band_energy -= 10
                self.turn_result = f"You hyped up the crowd during the {section}! They are screaming!"
            else:
                self.crowd_hype -= 2
                self.band_energy -= 5
                self.turn_result = f"You tried to hype them up, but it felt a bit forced."
        elif action == "solo":
            if roll > 70:
                self.crowd_hype += 15
                self.band_energy -= 15
                self.turn_result = f"You shredded a face-melting solo during the {section}!"
            else:
                self.crowd_hype -= 5
                self.band_energy -= 10
                self.turn_result = f"You fumbled the solo in the {section}. Ouch."

        self.crowd_hype = max(0, min(100, self.crowd_hype))
        self.band_energy = max(0, min(100, self.band_energy))
        self.log.insert(0, self.turn_result)

    def draw_screen(self):
        self.ui.clear_screen()

        # Header
        self.ui.draw_text(f"Live at {self.event.location.name}", self.ui.FONT_TITLE, (255, 255, 255), 640, 50, centered=True)
        self.ui.draw_text(f"Playing: {self.song.title}", self.ui.FONT_DEFAULT, (200, 200, 200), 640, 90, centered=True)

        # Meters
        self.ui.draw_text(f"Crowd Hype: {self.crowd_hype}/100", self.ui.FONT_DEFAULT, (255, 255, 0), 100, 150)
        self.ui.draw_text(f"Band Energy: {self.band_energy}/100", self.ui.FONT_DEFAULT, (0, 255, 255), 900, 150)

        # Main Display
        if self.state == "player_input":
            self.ui.draw_text(f"Current Section: {self.get_current_section()}", self.ui.FONT_TITLE, (255, 255, 255), 640, 250, centered=True)
            self.ui.draw_text("Choose your action:", self.ui.FONT_DEFAULT, (255, 255, 255), 640, 300, centered=True)

            # Draw choices manually since we are managing the loop here?
            # Or pass back control to game loop to call present_choices?
            # Ideally, game loop calls update/draw.
            # For simplicity, we can reuse present_choices if we break the loop, but we want custom UI.
            # Let's assume Game loop handles input and calls manager.handle_input
            pass

        elif self.state == "resolution":
            self.ui.draw_text(self.turn_result, self.ui.FONT_DEFAULT, (255, 255, 255), 640, 300, centered=True)
            self.ui.draw_text("Press Enter to continue...", self.ui.FONT_LOG, (150, 150, 150), 640, 400, centered=True)

        elif self.state == "summary":
            self.ui.draw_text("Performance Finished!", self.ui.FONT_TITLE, (255, 255, 255), 640, 250, centered=True)
            self.ui.draw_text(f"Final Hype: {self.crowd_hype}", self.ui.FONT_DEFAULT, (255, 255, 255), 640, 300, centered=True)
            self.ui.draw_text("Press Enter to leave stage.", self.ui.FONT_LOG, (150, 150, 150), 640, 400, centered=True)

        self.ui.update_display()
