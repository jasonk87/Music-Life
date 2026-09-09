import math
import random
import pygame


class SoundManager:
    def __init__(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2)
            self.mixer_initialized = True
        except Exception:
            self.mixer_initialized = False

    def _sample_rate(self) -> int:
        init = pygame.mixer.get_init()
        return init[0] if init else 44100

    def play_buy_sound(self):
        self.play_cash_sound()

    def play_cash_sound(self):
        if not self.mixer_initialized:
            return
        try:
            buf = self.create_chime_buffer(freq1=660, freq2=880, duration=0.15)
            sound = pygame.mixer.Sound(buffer=buf)
            sound.play()
        except Exception:
            pass

    def play_cheer_sound(self):
        if not self.mixer_initialized:
            return
        try:
            buf = self.create_noise_burst_buffer(duration=0.3, high_pass=True)
            sound = pygame.mixer.Sound(buffer=buf)
            sound.play()
        except Exception:
            pass

    def play_boo_sound(self):
        if not self.mixer_initialized:
            return
        try:
            buf = self.create_rumble_buffer(duration=0.3)
            sound = pygame.mixer.Sound(buffer=buf)
            sound.play()
        except Exception:
            pass

    def play_rhythm_beat(self):
        if not self.mixer_initialized:
            return
        try:
            buf = self.create_beep_buffer(frequency=220, duration=0.08, volume=0.4)
            sound = pygame.mixer.Sound(buffer=buf)
            sound.play()
        except Exception:
            pass

    def create_beep_buffer(self, frequency=440, duration=0.1, volume=0.5):
        sample_rate = self._sample_rate()
        num_samples = int(sample_rate * duration)
        buffer = bytearray(num_samples * 2)
        for i in range(num_samples):
            angle = (frequency * i * 360.0) / sample_rate
            value = int(32767.0 * volume * math.sin(math.radians(angle)))
            buffer[i * 2 : (i * 2) + 2] = value.to_bytes(2, byteorder="little", signed=True)
        return bytes(buffer)

    def create_chime_buffer(self, freq1=660, freq2=880, duration=0.15, volume=0.5):
        sample_rate = self._sample_rate()
        num_samples = int(sample_rate * duration)
        buffer = bytearray(num_samples * 2)
        half = num_samples // 2
        for i in range(num_samples):
            freq = freq1 if i < half else freq2
            angle = (freq * i * 360.0) / sample_rate
            value = int(32767.0 * volume * math.sin(math.radians(angle)))
            buffer[i * 2 : (i * 2) + 2] = value.to_bytes(2, byteorder="little", signed=True)
        return bytes(buffer)

    def create_noise_burst_buffer(self, duration=0.3, high_pass=True, volume=0.4):
        sample_rate = self._sample_rate()
        num_samples = int(sample_rate * duration)
        buffer = bytearray(num_samples * 2)
        for i in range(num_samples):
            envelope = 1.0 - (i / float(num_samples))
            val = random.uniform(-1.0, 1.0) * envelope * volume
            sample_val = int(32767.0 * val)
            buffer[i * 2 : (i * 2) + 2] = sample_val.to_bytes(2, byteorder="little", signed=True)
        return bytes(buffer)

    def create_rumble_buffer(self, duration=0.3, volume=0.4):
        sample_rate = self._sample_rate()
        num_samples = int(sample_rate * duration)
        buffer = bytearray(num_samples * 2)
        for i in range(num_samples):
            freq = 90 + int(math.sin(i / 100.0) * 30)
            angle = (freq * i * 360.0) / sample_rate
            value = int(32767.0 * volume * math.sin(math.radians(angle)))
            buffer[i * 2 : (i * 2) + 2] = value.to_bytes(2, byteorder="little", signed=True)
        return bytes(buffer)
