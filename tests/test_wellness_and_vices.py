import unittest
from game.player import Player
from game.wellness_and_vices import WellnessAndVicesSystem


class TestWellnessAndVices(unittest.TestCase):
    def setUp(self):
        self.player = Player("Singer")
        self.player.money = 10000
        self.player.energy = 50
        self.player.stress = 40

    def test_backstage_choices_and_sobriety(self):
        sys = WellnessAndVicesSystem()

        # Wild party choice
        res1 = sys.choose_backstage_lifestyle(self.player, "wild_party")
        self.assertTrue(res1["ok"])
        self.assertEqual(sys.profile.addiction_meter, 12.0)
        self.assertEqual(sys.profile.vocal_fatigue, 15.0)

        # Sobriety warmup
        res2 = sys.choose_backstage_lifestyle(self.player, "vocal_warmup_tea")
        self.assertTrue(res2["ok"])
        self.assertEqual(sys.profile.sobriety_streak_days, 1)
        self.assertLess(sys.profile.vocal_fatigue, 15.0)

    def test_vocal_coaching_and_rehab(self):
        sys = WellnessAndVicesSystem()
        sys.profile.addiction_meter = 45.0

        coach_res = sys.attend_vocal_coaching(self.player)
        self.assertTrue(coach_res["ok"])
        self.assertEqual(sys.profile.vocal_coaching_level, 1)

        rehab_res = sys.check_in_rehab_clinic(self.player)
        self.assertTrue(rehab_res["ok"])
        self.assertEqual(sys.profile.addiction_meter, 0.0)
        self.assertTrue(sys.profile.is_in_rehab)


if __name__ == "__main__":
    unittest.main()
