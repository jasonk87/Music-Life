import os
import unittest
import pygame
from game.pixel_portrait import PixelPortraitGenerator
from game.portrait import Portrait


class TestPixelPortraitRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize headless pygame for testing surface operations
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    def test_render_pixel_portrait_basic(self):
        surf = PixelPortraitGenerator.render_pixel_portrait(
            hair_length=3,
            beard_length=2,
            energy=80,
            stress=20,
            skin_tone_key="olive",
            hair_color_key="black",
            eye_color_key="green",
            has_sunglasses=False,
            target_size=(128, 128)
        )
        self.assertIsNotNone(surf)
        self.assertEqual(surf.get_width(), 128)
        self.assertEqual(surf.get_height(), 128)

    def test_render_sunglasses_and_heavy_beard(self):
        surf = PixelPortraitGenerator.render_pixel_portrait(
            hair_length=8,
            beard_length=7,
            energy=20,
            stress=85,
            skin_tone_key="tan",
            hair_color_key="blonde",
            eye_color_key="blue",
            has_sunglasses=True,
            target_size=(256, 256)
        )
        self.assertIsNotNone(surf)
        self.assertEqual(surf.get_width(), 256)
        self.assertEqual(surf.get_height(), 256)

    def test_portrait_wrapper_draw(self):
        screen_surf = pygame.Surface((400, 400))
        p = Portrait(screen_surf)
        # Should execute cleanly without error
        p.draw(10, 10, 80, 80, hair_length=4, beard_length=3, energy=90, stress=10)


if __name__ == "__main__":
    unittest.main()
