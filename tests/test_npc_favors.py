import unittest
from game.player import Player
from game.song import Song
from game.npc_system import NPC
from game.npc_favors import NPCFavorsSystem


class TestNPCFavors(unittest.TestCase):
    def setUp(self):
        self.player = Player("Songwriter")
        self.player.money = 1000
        self.player.fame = 50

        self.booker = NPC(
            npc_id="sal",
            name="Sal",
            city="Asbury Park, NJ",
            poi_id="the_stone_pony",
            role="BOOKER",
            bio="Booker",
            personality_trait="Gruff",
            favorite_gifts=[],
            affinity=50.0,
            respect=40.0,
        )

        self.engineer = NPC(
            npc_id="gary",
            name="Gary",
            city="New York City, NY",
            poi_id="electric_lady",
            role="ENGINEER",
            bio="Engineer",
            personality_trait="Purist",
            favorite_gifts=[],
            affinity=60.0,
            respect=50.0,
        )

        self.musician = NPC(
            npc_id="earl",
            name="Earl",
            city="Nashville, TN",
            poi_id="ryman",
            role="MUSICIAN",
            bio="Legend",
            personality_trait="Warm",
            favorite_gifts=[],
            affinity=55.0,
            respect=45.0,
        )

        self.song = Song("Country Highway", "Songwriter", "Americana", song_quality=0.70)
        self.song.is_recorded = True
        self.song.recording_quality = 0.75

    def test_booker_prime_slot_favor(self):
        res = NPCFavorsSystem.request_booker_prime_slot_favor(self.player, self.booker)
        self.assertTrue(res["ok"])
        self.assertEqual(self.player.money, 3500)
        self.assertEqual(self.booker.favors_used, 1)

    def test_engineer_tape_saturation_favor(self):
        res = NPCFavorsSystem.request_engineer_tape_saturation_favor(self.player, self.engineer, self.song)
        self.assertTrue(res["ok"])
        self.assertGreater(self.song.recording_quality, 0.85)

    def test_musician_cowrite_favor(self):
        res = NPCFavorsSystem.request_musician_cowrite_favor(self.player, self.musician, self.song)
        self.assertTrue(res["ok"])
        self.assertGreater(self.song.song_quality, 0.80)


if __name__ == "__main__":
    unittest.main()
