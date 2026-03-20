import os
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.game import Game
from game.npc import NPC, RelationshipStatus
from game.player import Player
from game.song import Song
from game.chart import Chart


class DummyUI:
    def add_log_message(self, message):
        pass

    def add_message(self, message):
        pass


class TestProgressionThresholds(unittest.TestCase):
    def test_radio_and_blog_unlock_earlier_for_released_song(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        song = Song("Single", "Tester", "Pop", song_quality=0.7)
        song.mark_as_recorded(0.7)
        song.is_released = True
        game.player.songs_written = [song]

        game.player.fame = 20
        self.assertTrue(game.OPPORTUNITY_CATALOG["radio_interview_local"]["trigger"](game.player, game))

        game.player.fame = 35
        self.assertTrue(game.OPPORTUNITY_CATALOG["music_blog_feature"]["trigger"](game.player, game))

    def test_media_outcome_scales_from_context(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        game.player.fame = 35
        game.player.contacts = ["a", "b", "c", "d"]
        game.player.has_pr_manager = True
        song = Song("Single", "Tester", "Pop", song_quality=0.8)
        song.mark_as_recorded(0.85)
        song.is_released = True
        song.buzz_score = 18
        game.player.songs_written = [song]

        with patch("game.game.random.randint", return_value=70):
            outcome = game._resolve_media_outcome("blog")

        self.assertEqual(outcome["band"], "strong")

    def test_npc_cosign_can_raise_song_buzz(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        npc = NPC("ally_1", "Ally", personality_key="friendly")
        npc.skills = {"vocals": 20}
        npc.relationship_with_player = RelationshipStatus.ALLY
        game.player.contacts = [npc.npc_id]
        game.NPC_REGISTRY[npc.npc_id] = npc

        song = Song("Signal", "Tester", "Pop", song_quality=0.9)
        song.mark_as_recorded(0.9)
        song.buzz_score = 25

        with patch.object(game, "_calculate_npc_fame", return_value=120), patch("game.game.random.randint", return_value=100):
            game._maybe_trigger_npc_cosign(song, "a post")

        self.assertGreater(song.buzz_score, 25)

    def test_friend_feature_opportunity_comes_from_context(self):
        game = Game(DummyUI())
        game.player = Player("Tester")
        npc = NPC("friend_1", "Friend", personality_key="friendly")
        npc.skills = {"vocals": 15}
        npc.relationship_with_player = RelationshipStatus.FRIENDLY
        game.player.contacts = [npc.npc_id]
        game.NPC_REGISTRY[npc.npc_id] = npc

        song = Song("Signal", "Tester", "Pop", song_quality=0.9)
        song.mark_as_recorded(0.9)
        song.is_released = True
        song.buzz_score = 30
        game.player.songs_written = [song]

        with patch.object(game, "_calculate_npc_fame", return_value=120), patch("game.game.random.randint", return_value=100):
            game.check_for_new_opportunities()

        self.assertIn("guest_feature_friend_1", game.player.active_opportunities)

    def test_chart_initial_ai_song_uses_contextual_roll(self):
        with patch("game.chart.random.randint", return_value=100):
            chart = Chart("Test Chart", max_size=3)

        self.assertTrue(all(entry["chart_score"] >= 0 for entry in chart.entries))


if __name__ == "__main__":
    unittest.main()
