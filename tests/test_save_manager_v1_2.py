import os
import unittest
from game.game import Game
from game.save_manager import JSONSaveManager
from game.song import Song


class DummyUI:
    def add_log_message(self, msg):
        pass


class TestSaveManagerV1_2(unittest.TestCase):
    def setUp(self):
        from game.player import Player
        self.game = Game(DummyUI())
        self.game.player = Player("Ziggy")
        self.game.player.money = 500000
        self.game.player.fame = 80
        self.game.player.street_cred = 75

        # Create album
        s1 = Song("Album Hit 1", "Ziggy", "Rock", song_quality=0.8)
        s1.is_recorded = True
        s1.recording_quality = 0.85
        s2 = Song("Album Hit 2", "Ziggy", "Rock", song_quality=0.85)
        s2.is_recorded = True
        s2.recording_quality = 0.90
        s3 = Song("Album Hit 3", "Ziggy", "Rock", song_quality=0.75)
        s3.is_recorded = True
        s3.recording_quality = 0.80
        self.game.player.songs_written = [s1, s2, s3]

        self.game.album_system.assemble_album(self.game.player, "The Stardust Odyssey", [s1, s2, s3], format_type="VINYL")
        album = self.game.album_system.released_albums[0]
        self.game.album_system.order_vinyl_pressing(self.game.player, album, units=500)

        # Shoot music video
        self.game.music_video_system.shoot_music_video(self.game.player, s1, tier_key="INDIE_DIRECTOR")

        # Register track in streaming
        self.game.streaming_system.register_song_for_streaming(s1, initial_fame=80)
        self.game.streaming_system.accumulated_unpaid_royalties = 45.50

        # Real estate & studio upgrades
        self.game.real_estate_system.buy_property(self.game.player, "philly_rowhouse")
        self.game.real_estate_system.install_studio_gear(self.game.player, "gear_tape_machine")

        # Tour life contract
        self.game.tour_life_simulation.register_bandmate("Spiders", "Drummer", split_pct=30.0, weekly_wage=200)

    def test_save_load_roundtrip_v1_2(self):
        save_file = "test_save_v1_2.json"
        saved = JSONSaveManager.save_game(self.game, filepath=save_file)
        self.assertTrue(saved)

        # Create new game instance and load
        new_game = Game(DummyUI())
        loaded = JSONSaveManager.load_game(new_game, filepath=save_file)
        self.assertTrue(loaded)

        # Verify player
        self.assertEqual(new_game.player.name, "Ziggy")
        self.assertEqual(new_game.player.fame, self.game.player.fame)

        # Verify album system
        self.assertEqual(len(new_game.album_system.released_albums), 1)
        self.assertEqual(new_game.album_system.released_albums[0].title, "The Stardust Odyssey")
        self.assertEqual(len(new_game.album_system.pending_vinyl_orders), 1)

        # Verify music videos
        self.assertEqual(len(new_game.music_video_system.videos), 1)
        self.assertEqual(new_game.music_video_system.videos[0].tier, "INDIE_DIRECTOR")

        # Verify streaming DSP
        self.assertAlmostEqual(new_game.streaming_system.accumulated_unpaid_royalties, 45.50, places=2)
        self.assertTrue(len(new_game.streaming_system.catalog) > 0)

        # Verify real estate & studio gear
        self.assertEqual(new_game.real_estate_system.current_residence_id, "philly_rowhouse")
        self.assertTrue(new_game.real_estate_system.properties["philly_rowhouse"].is_owned)
        self.assertEqual(len(new_game.real_estate_system.current_residence.studio_gear), 1)
        self.assertEqual(new_game.real_estate_system.current_residence.studio_gear[0].gear_id, "gear_tape_machine")

        # Verify tour contract
        self.assertIn("Spiders", new_game.tour_life_simulation.contracts)
        self.assertEqual(new_game.tour_life_simulation.contracts["Spiders"].publishing_split_pct, 30.0)

        if os.path.exists(save_file):
            os.remove(save_file)


if __name__ == "__main__":
    unittest.main()
