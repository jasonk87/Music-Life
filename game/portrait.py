from __future__ import annotations

import pygame
from game.pixel_portrait import PixelPortraitGenerator


class Portrait:
    """Renders the player's dynamic layered pixel art portrait with growing hair,
    beards, emotional expressions, and accessories.
    """

    def __init__(self, screen):
        self.screen = screen

    def draw(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        hair_length: int = 2,
        beard_length: int = 0,
        energy: int = 100,
        stress: int = 0,
        has_sunglasses: bool = False,
        skin_tone: str = "peach",
        hair_color: str = "brown",
        eye_color: str = "blue"
    ):
        """Renders procedural pixel art character portrait onto the target screen rect."""
        surface = PixelPortraitGenerator.render_pixel_portrait(
            hair_length=hair_length,
            beard_length=beard_length,
            energy=energy,
            stress=stress,
            skin_tone_key=skin_tone,
            hair_color_key=hair_color,
            eye_color_key=eye_color,
            has_sunglasses=has_sunglasses,
            has_earring=True,
            target_size=(int(width), int(height)),
        )
        self.screen.blit(surface, (x, y))

        # Subtle brushed gunmetal border frame with chamfered inner highlight
        frame_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (45, 52, 68), frame_rect, 2, border_radius=4)
        pygame.draw.rect(self.screen, (15, 18, 24), frame_rect.inflate(-4, -4), 1, border_radius=3)
