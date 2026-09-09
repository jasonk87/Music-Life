import os
import unittest
from types import SimpleNamespace
from game.game import Game
from game.player import Player
from game.song import Song
from game.save_manager import JSONSaveManager
from game.live_concert_dynamics import LiveConcertDynamicsEngine
from game.studio_production_engineering import StudioEngineeringSystem
from game.dynamic_musician_interactions import DynamicMusicianInteractions


class DummyUI:
    def add_log_message(self, msg):
        pass


class TestEndToEndGameplayPlaythrough(unittest.TestCase):
    """Automated multi-stage end-to-end integration playthrough test."""

    def test_full_progression_lifecycle(self):
        ui = DummyUI()
        game = Game(ui)

        # 1. Start career in Asbury Park
        game.player = Player("Sam Vance")
        game.player.current_location = SimpleNamespace(name="Asbury Park, NJ")
        game.player.money = 25000

        # 2. Write and track 3 songs with studio engineering
        s1 = Song("Ocean Avenue", "Sam Vance", "Rock", song_quality=0.82, theme="summer_nostalgia")
        s2 = Song("Boardwalk Shadows", "Sam Vance", "Rock", song_quality=0.85, theme="summer_nostalgia")
        s3 = Song("Stone Pony Lights", "Sam Vance", "Rock", song_quality=0.88, theme="summer_nostalgia")

        for s in [s1, s2, s3]:
            eng_res = StudioEngineeringSystem.engineer_master_track(
                game.player, s,
                tracking_medium="ANALOG_2INCH_TAPE",
                vocal_chain="DOUBLE_TRACKED_HARMONIES",
                mix_philosophy="WALL_OF_SOUND",
            )
            self.assertTrue(eng_res["ok"])
            s.is_released = True
            game.player.songs_written.append(s)

        # 3. Assemble and release album
        album_res = game.album_system.assemble_album(
            game.player,
            title="Asbury Drift",
            songs=[s1, s2, s3],
            format_type="DELUXE",
            theme="summer_nostalgia",
        )
        self.assertTrue(album_res["ok"])
        self.assertEqual(len(game.album_system.released_albums), 1)

        # 4. Vinyl Pressing & Webstore D2C Drop
        game.player.money += 5000
        vinyl_res = game.album_system.order_vinyl_pressing(game.player, "Asbury Drift", units=500)
        self.assertTrue(vinyl_res["ok"])

        drop_res = game.physical_vinyl_drops.launch_webstore_variant_drop(
            game.player, "Asbury Drift", variant_name="Seafoam Marble 180g", units=100
        )
        self.assertTrue(drop_res["ok"])

        # 5. Live show dynamics at Stone Pony
        venue = SimpleNamespace(name="The Stone Pony", capacity=1000)
        perf = LiveConcertDynamicsEngine.start_concert(game.player, venue, [s1, s2, s3], ticket_price=25)
        self.assertGreater(perf.crowd_attendance, 0)

        tactic_res = LiveConcertDynamicsEngine.perform_song_with_tactic(game.player, perf, s1, tactic="CITY_BANTER")
        self.assertTrue(tactic_res["ok"])

        perf.hype_score = 88.0
        encore_res = LiveConcertDynamicsEngine.trigger_encore(game.player, perf, s3)
        self.assertTrue(encore_res["ok"])

        # 6. International Touring Visa & Flight to London
        game.player.money += 10000
        visa_res = game.international_touring.apply_for_artist_visa(game.player, "London, UK")
        self.assertTrue(visa_res["ok"])

        carnet_res = game.international_touring.purchase_ata_carnet_customs_bond(game.player)
        self.assertTrue(carnet_res["ok"])

        game.player.current_location = SimpleNamespace(name="London, UK")
        arr_res = game.international_touring.process_international_flight_arrival(game.player, "London, UK")
        self.assertTrue(arr_res["ok"])

        # 7. Press Reviews & Billboard Charts
        reviews = game.music_press_reviews.generate_press_reviews_for_album(game.player, album_res["album"])
        self.assertEqual(len(reviews), 2)

        chart_logs = game.billboard_charts.update_weekly_billboard_hot_100(game.player, [s1], game.streaming_system)
        self.assertGreater(len(chart_logs), 0)

        # 8. Full Save/Load Roundtrip
        save_file = "test_end_to_end_save.json"
        saved = JSONSaveManager.save_game(game, filepath=save_file)
        self.assertTrue(saved)

        restored_game = Game(ui)
        loaded = JSONSaveManager.load_game(restored_game, filepath=save_file)
        self.assertTrue(loaded)
        self.assertEqual(restored_game.player.name, "Sam Vance")
        self.assertEqual(restored_game.player.current_location.name, "London, UK")
        self.assertTrue(restored_game.international_touring.has_ata_carnet_bond)

        if os.path.exists(save_file):
            os.remove(save_file)


if __name__ == "__main__":
    unittest.main()
