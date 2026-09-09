import unittest
from game.player import Player
from game.physical_vinyl_drops import PhysicalVinylDropSystem


class TestPhysicalVinylDrops(unittest.TestCase):
    def setUp(self):
        self.player = Player("VinylHead")
        self.player.fame = 200
        self.sys = PhysicalVinylDropSystem()

    def test_webstore_drop_and_consignment(self):
        # D2C Webstore drop
        drop_res = self.sys.launch_webstore_variant_drop(
            self.player,
            album_title="Neon Horizon",
            variant_name="Seafoam Marble 180g",
            units=100,
            unit_price=35,
        )
        self.assertTrue(drop_res["ok"])
        self.assertGreater(drop_res["initial_sales"], 0)
        self.assertEqual(len(self.sys.active_webstore_drops), 1)

        # Consign to Rough Trade London
        consign_res = self.sys.consign_records_to_local_store(
            self.player,
            store_name="Rough Trade East",
            city_name="London, UK",
            album_title="Neon Horizon",
            units=25,
        )
        self.assertTrue(consign_res["ok"])
        self.assertEqual(len(self.sys.consignments), 1)

        # Process weekly consignment sales
        initial_money = self.player.money
        logs = self.sys.process_weekly_consignment_sales(self.player)
        self.assertGreater(len(logs), 0)
        self.assertGreater(self.player.money, initial_money)


if __name__ == "__main__":
    unittest.main()
