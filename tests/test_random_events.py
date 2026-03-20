import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.random_events import RandomEvent


class TestRandomEvents(unittest.TestCase):
    def test_random_event_defaults(self):
        event = RandomEvent("Test", "At {poi_name}")
        self.assertEqual(event.actions, [])
        self.assertIsNone(event.npc_interaction)
        self.assertIsNone(event.custom_interaction_fn_name)

    def test_random_event_accepts_custom_interaction_handler(self):
        event = RandomEvent(
            "Autograph",
            "Fan event",
            custom_interaction_fn_name="handle_autograph_interaction",
        )
        self.assertEqual(event.custom_interaction_fn_name, "handle_autograph_interaction")


if __name__ == "__main__":
    unittest.main()
