import pygame

class Portrait:
    def __init__(self, screen):
        self.screen = screen

    def draw(self, x, y, width, height, hair_length, beard_length):
        # Head
        head_color = (255, 224, 189)  # A light skin tone
        pygame.draw.ellipse(self.screen, head_color, [x, y, width, height])

        # Hair
        hair_color = (101, 67, 33)  # Brown
        if hair_length > 0:
            hair_height = min(hair_length * 5, height / 2)
            pygame.draw.rect(self.screen, hair_color, [x, y, width, hair_height])

        # Beard
        beard_color = (101, 67, 33)  # Brown
        if beard_length > 0:
            beard_height = min(beard_length * 5, height / 2)
            pygame.draw.rect(self.screen, beard_color, [x, y + height - beard_height, width, beard_height])
