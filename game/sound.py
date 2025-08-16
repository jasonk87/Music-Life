import pygame

class SoundManager:
    def __init__(self):
        pygame.mixer.init()

    def play_buy_sound(self):
        # Create a simple beep sound
        sound = pygame.mixer.Sound(buffer=self.create_beep_buffer())
        sound.play()

    def create_beep_buffer(self, frequency=440, duration=0.1, volume=0.5):
        sample_rate = pygame.mixer.get_init()[0]
        num_samples = int(sample_rate * duration)
        buffer = bytearray(num_samples * 2)
        for i in range(num_samples):
            value = int(32767.0 * volume * pygame.math.Vector2(1, 0).rotate(frequency * i * 360.0 / sample_rate).y)
            buffer[i*2:(i*2)+2] = value.to_bytes(2, byteorder='little', signed=True)
        return bytes(buffer)
