import unittest
from game.player import Player
from game.stage_production import StageProductionSystem


class TestStageProduction(unittest.TestCase):
    def setUp(self):
        self.player = Player("ArenaStar")
        self.player.money = 150000

    def test_purchase_and_equip_arena_rig(self):
        sys = StageProductionSystem()
        self.assertEqual(sys.active_rig.rig_id, "diy_club_rig")

        res = sys.purchase_and_equip_rig(self.player, "arena_spectacle_rig")
        self.assertTrue(res["ok"])
        self.assertEqual(sys.active_rig.rig_id, "arena_spectacle_rig")
        self.assertEqual(sys.active_rig.hype_multiplier, 1.40)
        self.assertEqual(sys.active_rig.ticket_price_premium, 35)


if __name__ == "__main__":
    unittest.main()
