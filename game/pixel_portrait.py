from __future__ import annotations

import pygame
from typing import Dict, Tuple, Optional, Any


class PixelPortraitGenerator:
    """Procedural 32x32 layered pixel-art character face and portrait generator.
    Renders crisp, scaled pixel characters with dynamic skin tones, hair lengths,
    facial hair / beards, emotional expressions, fatigue eye bags, and sunglasses.
    """

    # Color Palettes
    SKIN_TONES = {
        "fair": ((255, 220, 195), (235, 195, 170), (200, 155, 130)),
        "peach": ((250, 205, 175), (225, 175, 145), (185, 135, 105)),
        "olive": ((225, 190, 150), (195, 155, 115), (155, 115, 80)),
        "tan": ((200, 150, 110), (170, 120, 80), (130, 85, 50)),
        "bronze": ((160, 105, 65), (130, 80, 45), (95, 50, 25)),
        "ebony": ((100, 60, 40), (75, 40, 25), (45, 20, 10)),
        "pale_goth": ((240, 235, 245), (205, 200, 215), (165, 160, 180)),
    }

    HAIR_COLORS = {
        "black": ((30, 30, 35), (18, 18, 22)),
        "brown": ((90, 55, 30), (60, 35, 18)),
        "blonde": ((235, 200, 95), (190, 150, 60)),
        "red": ((185, 65, 35), (140, 40, 18)),
        "platinum": ((230, 230, 235), (185, 185, 195)),
        "neon_pink": ((255, 45, 135), (200, 20, 90)),
        "neon_cyan": ((30, 225, 245), (15, 165, 190)),
    }

    EYE_COLORS = {
        "blue": (65, 145, 225),
        "brown": (95, 55, 25),
        "green": (55, 165, 75),
        "hazel": (145, 120, 55),
        "grey": (140, 150, 160),
    }

    @classmethod
    def render_pixel_portrait(
        cls,
        hair_length: int = 2,
        beard_length: int = 0,
        energy: int = 100,
        stress: int = 0,
        skin_tone_key: str = "peach",
        hair_color_key: str = "brown",
        eye_color_key: str = "blue",
        has_sunglasses: bool = False,
        has_earring: bool = True,
        target_size: Tuple[int, int] = (128, 128)
    ) -> pygame.Surface:
        """Generates a 32x32 pixel canvas and returns a high-resolution scaled pygame surface."""
        canvas = pygame.Surface((32, 32), pygame.SRCALPHA)
        canvas.fill((0, 0, 0, 0)) # Transparent base

        skin_light, skin_mid, skin_shadow = cls.SKIN_TONES.get(skin_tone_key, cls.SKIN_TONES["peach"])
        hair_main, hair_dark = cls.HAIR_COLORS.get(hair_color_key, cls.HAIR_COLORS["brown"])
        eye_iris = cls.EYE_COLORS.get(eye_color_key, cls.EYE_COLORS["blue"])

        # 1. Torso / Shirt Collar (Y: 26 to 31)
        shirt_color = (40, 48, 65)
        jacket_color = (25, 28, 35)
        for y in range(26, 32):
            for x in range(6, 26):
                canvas.set_at((x, y), jacket_color)
        for y in range(26, 30):
            for x in range(12, 20):
                canvas.set_at((x, y), shirt_color)

        # 2. Neck (Y: 22 to 26, X: 12 to 19)
        for y in range(22, 27):
            for x in range(12, 20):
                canvas.set_at((x, y), skin_shadow if y == 22 or x in (12, 19) else skin_mid)

        # 3. Head & Jaw Base (Y: 8 to 23, X: 8 to 23)
        for y in range(9, 23):
            # Jaw tapers slightly at bottom
            x_min = 9 if y < 20 else 10 if y < 22 else 12
            x_max = 22 if y < 20 else 21 if y < 22 else 19
            for x in range(x_min, x_max + 1):
                # Shading edges
                if x == x_min or x == x_max or y == 22:
                    col = skin_shadow
                elif x in (x_min + 1, x_max - 1) or y == 21:
                    col = skin_mid
                else:
                    col = skin_light
                canvas.set_at((x, y), col)

        # 4. Ears (Y: 13 to 17, X: 7 and 24)
        for y in range(13, 17):
            canvas.set_at((7, y), skin_mid)
            canvas.set_at((8, y), skin_light)
            canvas.set_at((23, y), skin_light)
            canvas.set_at((24, y), skin_mid)

        # Earring (Silver hoop on left ear)
        if has_earring:
            canvas.set_at((7, 17), (220, 225, 235))
            canvas.set_at((7, 18), (180, 185, 195))

        # 5. Eyes & Eyebrows (Y: 13 to 15)
        is_tired = (energy < 35 or stress > 65)

        if has_sunglasses:
            # Cool Dark Aviator / Wayfarer Shades
            shade_frame = (20, 20, 25)
            shade_lens = (35, 40, 50)
            shade_glint = (120, 140, 175)
            # Left lens (X: 9 to 14, Y: 13 to 16)
            for y in range(13, 17):
                for x in range(9, 15):
                    canvas.set_at((x, y), shade_frame if x in (9, 14) or y in (13, 16) else shade_lens)
            # Right lens (X: 17 to 22, Y: 13 to 16)
            for y in range(13, 17):
                for x in range(17, 23):
                    canvas.set_at((x, y), shade_frame if x in (17, 22) or y in (13, 16) else shade_lens)
            # Bridge
            canvas.set_at((15, 13), shade_frame)
            canvas.set_at((16, 13), shade_frame)
            # Glint
            canvas.set_at((10, 14), shade_glint)
            canvas.set_at((18, 14), shade_glint)
        else:
            # Eyebrows (Y: 12)
            brow_col = hair_dark
            for x in range(10, 14):
                canvas.set_at((x, 12), brow_col)
            for x in range(18, 22):
                canvas.set_at((x, 12), brow_col)

            # Left Eye (X: 10, 11, 12, 13 | Y: 14, 15)
            canvas.set_at((10, 14), (250, 250, 250))
            canvas.set_at((11, 14), eye_iris)
            canvas.set_at((12, 14), (20, 20, 25)) # Pupil
            canvas.set_at((13, 14), (250, 250, 250))

            # Right Eye (X: 18, 19, 20, 21 | Y: 14, 15)
            canvas.set_at((18, 14), (250, 250, 250))
            canvas.set_at((19, 14), (20, 20, 25)) # Pupil
            canvas.set_at((20, 14), eye_iris)
            canvas.set_at((21, 14), (250, 250, 250))

            # Fatigue / Sleep Deprived Dark Eye Bags (Y: 16)
            if is_tired:
                eye_bag_color = (130, 95, 90) if skin_tone_key not in ("ebony", "bronze") else (55, 30, 20)
                for x in (10, 11, 12, 13, 18, 19, 20, 21):
                    canvas.set_at((x, 16), eye_bag_color)

        # 6. Nose (Y: 16 to 18, X: 15, 16)
        canvas.set_at((15, 17), skin_shadow)
        canvas.set_at((16, 17), skin_shadow)
        canvas.set_at((15, 18), (140, 90, 70))
        canvas.set_at((16, 18), (140, 90, 70))

        # 7. Mouth & Expression (Y: 20)
        lip_color = (175, 95, 90) if skin_tone_key != "ebony" else (70, 35, 30)
        if stress > 75:
            # Stressed / Grimace
            for x in range(13, 19):
                canvas.set_at((x, 20), lip_color)
            canvas.set_at((13, 21), lip_color)
            canvas.set_at((18, 21), lip_color)
        elif energy > 70 and stress < 30:
            # Confident Rockstar Grin
            for x in range(13, 19):
                canvas.set_at((x, 20), lip_color)
            canvas.set_at((14, 20), (255, 255, 255)) # Tooth glint
            canvas.set_at((15, 20), (255, 255, 255))
            canvas.set_at((18, 19), lip_color)
        else:
            # Neutral / Cool
            for x in range(14, 18):
                canvas.set_at((x, 20), lip_color)

        # 8. Facial Hair & Beard Growth (Dynamic beard_length)
        if beard_length >= 1:
            stubble_color = (hair_dark[0] + 40, hair_dark[1] + 30, hair_dark[2] + 25)
            if beard_length == 1:
                # 5 O'Clock Stubble Shadow (Y: 19 to 22)
                for y in (19, 21, 22):
                    for x in range(11, 21, 2):
                        if (x + y) % 2 == 0:
                            canvas.set_at((x, y), stubble_color)
            elif beard_length <= 3:
                # Trimmed Boxed Beard & Mustache (Y: 19 to 23)
                # Mustache
                for x in range(13, 19):
                    canvas.set_at((x, 19), hair_dark)
                # Jaw beard
                for y in range(21, 24):
                    for x in range(10, 22):
                        if (x in (10, 11, 20, 21) or y == 23) and canvas.get_at((x, y))[3] > 0:
                            canvas.set_at((x, y), hair_main)
            elif beard_length <= 6:
                # Full Heavy Rocker Beard (Y: 19 to 26)
                # Mustache
                for x in range(12, 20):
                    canvas.set_at((x, 19), hair_dark)
                # Full Beard
                for y in range(20, 27):
                    for x in range(9, 23):
                        if y >= 22 or x in (9, 10, 11, 20, 21, 22):
                            canvas.set_at((x, y), hair_main if (x + y) % 3 != 0 else hair_dark)
            else:
                # Long Wizard / ZZ Top Legendary Beard (Y: 19 to 30)
                for y in range(19, 31):
                    x_taper = max(11, 15 - (30 - y) // 2)
                    x_max_t = min(20, 16 + (30 - y) // 2)
                    for x in range(x_taper, x_max_t + 1):
                        canvas.set_at((x, y), hair_main if (x + y) % 2 == 0 else hair_dark)

        # 9. Hair Styles & Length (Dynamic hair_length)
        if hair_length == 0:
            # Bald / Buzzcut shadow on scalp
            for y in range(6, 11):
                for x in range(10, 22):
                    if (x + y) % 2 == 0:
                        canvas.set_at((x, y), (hair_dark[0] + 50, hair_dark[1] + 40, hair_dark[2] + 30))
        elif hair_length <= 2:
            # Short Crop / Pixie / Indie Crop (Y: 5 to 11)
            for y in range(5, 12):
                for x in range(8, 24):
                    if y <= 8 or (y <= 11 and (x <= 10 or x >= 21 or y == 9)):
                        canvas.set_at((x, y), hair_main if (x + y) % 3 != 0 else hair_dark)
        elif hair_length <= 5:
            # Medium Indie Shag / Mop Top / Grunge Curtains (Y: 4 to 18)
            for y in range(4, 19):
                for x in range(7, 25):
                    if y <= 9 or x in (7, 8, 23, 24) or (y <= 12 and x in (9, 10, 21, 22)):
                        canvas.set_at((x, y), hair_main if (x + y) % 3 != 0 else hair_dark)
        else:
            # Long Heavy Metal / Rocker Mane flowing past shoulders (Y: 4 to 28)
            for y in range(4, 29):
                for x in range(6, 26):
                    if y <= 9 or x in (6, 7, 8, 23, 24, 25) or (y >= 20 and x in (9, 10, 21, 22)):
                        canvas.set_at((x, y), hair_main if (x + y) % 3 != 0 else hair_dark)

        # 10. Crisp Nearest-Neighbor Scaling to Target Size
        scaled_surface = pygame.transform.scale(canvas, target_size)
        return scaled_surface
