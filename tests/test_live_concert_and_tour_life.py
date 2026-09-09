import unittest
from types import SimpleNamespace
from game.player import Player
from game.song import Song
from game.live_concert_sim import LiveConcertSimulator
from game.tour_life_sim import TourLifeSimulation


class TestLiveConcertAndTourLife(unittest.TestCase):
    def setUp(self):
        self.player = Player("Frontman")
        self.player.money = 2000
        self.player.fame = 40
        self.player.street_cred = 65

        self.venue = SimpleNamespace(name="The Stone Pony", capacity=450, prestige=3)
        self.songs = [
            Song("Opener Anthem", "Frontman", "Rock", song_quality=0.8, catchiness=0.9),
            Song("Midtempo Hit", "Frontman", "Rock", song_quality=0.85, catchiness=0.8),
            Song("Closer", "Frontman", "Rock", song_quality=0.9, catchiness=0.95),
        ]

    def test_live_concert_flow_banter_and_encore(self):
        sim = LiveConcertSimulator()
        state = sim.start_concert(self.player, self.venue, self.songs, ticket_price=20)
        self.assertGreater(state.attendance, 50)

        # Song 1
        res1 = sim.perform_next_song(self.player, state, has_roadie=True)
        self.assertTrue(res1["ok"])
        self.assertLess(state.band_stamina, 100.0)

        # Stage Banter
        banter_res = sim.deliver_stage_banter(state, "storytelling")
        self.assertTrue(banter_res["ok"])
        self.assertGreater(state.band_stamina, res1["band_stamina"])

        # Remaining songs
        sim.perform_next_song(self.player, state, has_roadie=True)
        sim.perform_next_song(self.player, state, has_roadie=True)

        state.crowd_hype = 90.0
        state.encore_earned = True
        encore_res = sim.perform_encore(self.player, state)
        self.assertTrue(encore_res["ok"])

        # Finalize
        fin_res = sim.finalize_concert(self.player, state)
        self.assertTrue(fin_res["ok"])
        self.assertGreater(fin_res["total_earnings"], 0)

    def test_tour_life_highway_hazards_and_disputes(self):
        tour_sim = TourLifeSimulation()
        contract = tour_sim.register_bandmate("Sarah", "Bassist", split_pct=25.0, weekly_wage=150)
        self.assertEqual(contract.member_name, "Sarah")

        # Roll hazard with driver
        enc = tour_sim.roll_highway_encounter(self.player, has_driver=True)
        if enc and enc.get("avoided"):
            self.assertIn("Driver", enc["explanation"])

        # Resolve publishing dispute
        contract.satisfaction = 30.0
        disp_res = tour_sim.resolve_dispute_choice(self.player, "Sarah", "publishing_split", "compromise")
        self.assertTrue(disp_res["ok"])
        self.assertEqual(contract.publishing_split_pct, 35.0)
        self.assertGreater(contract.satisfaction, 30.0)


if __name__ == "__main__":
    unittest.main()
