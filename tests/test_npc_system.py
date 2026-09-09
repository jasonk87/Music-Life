import unittest
from types import SimpleNamespace
from game.player import Player
from game.npc_system import NPCSystem


class TestNPCSystem(unittest.TestCase):
    def setUp(self):
        self.player = Player("Guitarist")
        self.player.money = 5000
        self.player.stress = 40
        self.player.current_location = SimpleNamespace(name="Asbury Park, NJ")

    def test_npc_lookup_and_conversation(self):
        sys = NPCSystem()
        asbury_npcs = sys.get_npcs_in_city("Asbury Park, NJ")
        self.assertEqual(len(asbury_npcs), 1)
        self.assertEqual(asbury_npcs[0].npc_id, "sal_moretti")

        # Talk with Sal
        talk_res = sys.talk_with_npc(self.player, "sal_moretti", topic="gear_talk")
        self.assertTrue(talk_res["ok"])
        sal = talk_res["npc"]
        self.assertGreater(sal.affinity, 10.0)
        self.assertGreater(sal.respect, 10.0)
        self.assertEqual(len(sal.memories), 1)

    def test_give_favorite_gift(self):
        sys = NPCSystem()
        # Sal loves vintage_whiskey
        gift_res = sys.give_gift_to_npc(self.player, "sal_moretti", "vintage_whiskey")
        self.assertTrue(gift_res["ok"])
        sal = sys.get_npc("sal_moretti")
        self.assertEqual(sal.affinity, 35.0)  # 10 + 25
        self.assertEqual(sal.relationship_tier, "FRIENDLY")


if __name__ == "__main__":
    unittest.main()
