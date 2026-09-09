import unittest
from game.player import Player
from game.album_system import AlbumRelease
from game.music_press_reviews import MusicPressReviewsSystem


class TestMusicPressReviews(unittest.TestCase):
    def setUp(self):
        self.player = Player("Mastermind")
        self.album = AlbumRelease(
            album_id="alb_masterpiece",
            title="OK Computer Era Masterwork",
            artist="Mastermind",
            track_ids=["t1", "t2"],
            tracks_data=[],
            format_type="DIGITAL",
            release_date_str="2024-05-01",
            release_day=1,
            overall_quality=0.95,
            concept_coherence=1.25,
        )

    def test_generate_pitchfork_and_rolling_stone_reviews(self):
        sys = MusicPressReviewsSystem()
        reviews = sys.generate_press_reviews_for_album(self.player, self.album)

        self.assertEqual(len(reviews), 2)
        pf = next(r for r in reviews if r.publication == "Pitchfork")
        self.assertGreaterEqual(pf.numeric_score, 8.0)
        self.assertTrue(pf.is_best_new_music)
        self.assertIn("urgent, transcendent", pf.review_headline)


if __name__ == "__main__":
    unittest.main()
