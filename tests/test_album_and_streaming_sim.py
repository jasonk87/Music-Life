import unittest
from game.player import Player
from game.song import Song
from game.album_system import AlbumProductionSystem
from game.music_video import MusicVideoSystem
from game.streaming_dsp import StreamingPlatformSystem


class TestAlbumAndStreamingSim(unittest.TestCase):
    def setUp(self):
        self.player = Player("Rocker")
        self.player.money = 10000
        self.player.fame = 20
        self.player.street_cred = 60

        self.songs = []
        for i in range(4):
            s = Song(f"Track {i+1}", "Rocker", "Rock", song_quality=0.75)
            s.is_recorded = True
            s.recording_quality = 0.80
            self.songs.append(s)

    def test_album_assembly_and_coherence(self):
        system = AlbumProductionSystem()
        res = system.assemble_album(self.player, "Debut Anthem LP", self.songs, format_type="VINYL")
        self.assertTrue(res["ok"])
        album = res["album"]
        self.assertEqual(album.title, "Debut Anthem LP")
        self.assertEqual(len(album.track_ids), 4)
        self.assertGreater(album.overall_quality, 0.70)
        self.assertGreaterEqual(album.concept_coherence, 1.0)
        self.assertGreater(self.player.fame, 20)

    def test_vinyl_batch_pressing_and_delivery(self):
        system = AlbumProductionSystem()
        res = system.assemble_album(self.player, "Vinyl Dreams", self.songs)
        album = res["album"]

        order_res = system.order_vinyl_pressing(self.player, album, units=500)
        self.assertTrue(order_res["ok"])
        self.assertEqual(len(system.pending_vinyl_orders), 1)

        # Advance days to trigger delivery
        from game.game_time import advance_game_time
        advance_game_time(days=22)
        logs = system.process_daily_vinyl_manufacturing_and_sales(self.player)
        self.assertEqual(len(system.delivered_vinyl_batches), 1)
        self.assertIn("delivered 500x records", logs[0])

    def test_music_video_production_and_views(self):
        video_sys = MusicVideoSystem()
        song = self.songs[0]
        res = video_sys.shoot_music_video(self.player, song, tier_key="INDIE_DIRECTOR")
        self.assertTrue(res["ok"])
        video = res["video"]
        self.assertEqual(video.tier, "INDIE_DIRECTOR")
        self.assertGreater(video.views, 10000)
        self.assertTrue(song.has_music_video)

        # Ad revenue processing
        logs = video_sys.process_daily_views_and_ad_revenue(self.player)
        self.assertTrue(len(logs) > 0)

    def test_streaming_platform_pitching_and_royalties(self):
        dsp = StreamingPlatformSystem()
        song = self.songs[0]
        track_data = dsp.register_song_for_streaming(song, initial_fame=20)
        self.assertGreater(track_data.daily_streams, 100)

        # Pitch to playlist
        pitch_res = dsp.pitch_to_editorial_playlist(self.player, track_data.song_id, "pl_rock_essentials")
        self.assertIn("ok", pitch_res)

        # Process daily streams
        dsp.accumulated_unpaid_royalties = 10.0
        logs = dsp.process_daily_streams_and_royalties(self.player)
        self.assertTrue(any("royalty deposit" in l for l in logs))


if __name__ == "__main__":
    unittest.main()
