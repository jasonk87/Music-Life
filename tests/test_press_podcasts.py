import unittest
from game.player import Player
from game.press_podcasts import PressPodcastsSystem


class TestPressPodcasts(unittest.TestCase):
    def setUp(self):
        self.player = Player("Icon")
        self.player.fame = 80
        self.player.street_cred = 60

    def test_guest_on_song_exploder_auteur(self):
        sys = PressPodcastsSystem()

        res = sys.guest_on_podcast(self.player, "song_exploder", answer_style="auteur")
        self.assertTrue(res["ok"])
        self.assertEqual(sys.persona.auteur_score, 35)
        self.assertEqual(sys.persona.total_podcasts_done, 1)

    def test_guest_on_zane_lowe_maverick(self):
        sys = PressPodcastsSystem()

        res = sys.guest_on_podcast(self.player, "zane_lowe_deep_dive", answer_style="maverick")
        self.assertTrue(res["ok"])
        self.assertEqual(sys.persona.maverick_score, 35)
        self.assertEqual(len(sys.podcast_history), 1)


if __name__ == "__main__":
    unittest.main()
