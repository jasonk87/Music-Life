import unittest
from types import SimpleNamespace
from game.player import Player
from game.relationships_and_family import RelationshipsAndFamilySystem


class TestRelationshipsAndFamily(unittest.TestCase):
    def setUp(self):
        self.player = Player("Romantic")
        self.player.money = 25000
        self.player.stress = 50
        self.player.current_location = SimpleNamespace(name="Asbury Park, NJ")

    def test_dating_and_relationship_progression(self):
        sys = RelationshipsAndFamilySystem()

        # Meet Maya in Asbury
        meet_res = sys.meet_and_ask_out(self.player, "maya_artist_asbury")
        self.assertTrue(meet_res["ok"])
        self.assertIsNotNone(sys.partner)
        self.assertEqual(sys.partner.relationship_status, "DATING")

        # Dates to increase affection
        for _ in range(3):
            sys.go_on_date(self.player, "dinner_date")

        self.assertGreaterEqual(sys.partner.affection_level, 50.0)
        self.assertEqual(sys.partner.relationship_status, "EXCLUSIVE")

        # Propose marriage
        sys.partner.affection_level = 90.0
        prop_res = sys.propose_marriage(self.player)
        self.assertTrue(prop_res["ok"])
        self.assertEqual(sys.partner.relationship_status, "MARRIED")

    def test_family_calls_and_financial_support(self):
        sys = RelationshipsAndFamilySystem()

        call_res = sys.call_family_home(self.player)
        self.assertTrue(call_res["ok"])

        send_res = sys.send_money_to_family(self.player, amount=2000)
        self.assertTrue(send_res["ok"])
        self.assertEqual(sys.family.total_money_sent_home, 2000)
        self.assertGreater(sys.family.parents_relationship, 75.0)


if __name__ == "__main__":
    unittest.main()
