import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.dialogue import generate_npc_response
from game.npc import NPC


class TestDialogue(unittest.TestCase):
    def test_generate_npc_response_falls_back_without_api_key(self):
        npc = NPC("npc_joe", "Old Joe", "old_timer_joe")
        response = generate_npc_response("hello", npc, "Player")

        self.assertIsInstance(response, str)
        self.assertTrue(response)
        self.assertNotIn("Error: config.py missing.", response)
        self.assertNotIn("Please set your GEMINI_API_KEY", response)


if __name__ == "__main__":
    unittest.main()
