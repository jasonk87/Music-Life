import unittest

from game.game_time import current_game_time, GameTime
from game.llm_interaction_layer import (
    InteractionContextBuilder,
    LLMInteractionEngine,
    PERSONALITY_LIBRARY,
    SocialMediaExpressionLayer,
)
from game.location import Location
from game.npc import NPC
from game.player import Player
from game.player_schedule import PlayerSchedule
from game.poi import PointOfInterest
from game.visibility_system import VisibilitySystem
from game.world_memory import WorldMemoryStore, WorldMemoryEntry


class DummyGame:
    def __init__(self):
        self.player = Player("Hero")
        self.player.schedule = PlayerSchedule()
        self.player.current_location = Location("Austin", "TX")
        self.player.current_poi = PointOfInterest("club", "The Rusty Nail", "Venue", category="VENUE_CLUB")
        self.player.current_location.add_poi(self.player.current_poi)

        self.world_memory = WorldMemoryStore()
        self.visibility_system = VisibilitySystem()
        self.game_state = "main_menu"
        self.travel_manager = None


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload

    def generate(self, context, player_input):
        return dict(self.payload)


class FakeMediaLLM:
    def generate_media(self, payload):
        return {"text": f"Headline: {payload['event_type']} in {payload.get('location') or 'town'}."}


class TestLLMInteractionLayer(unittest.TestCase):
    def setUp(self):
        current_game_time.year = 2024
        current_game_time.month = 1
        current_game_time.day = 1
        current_game_time.hour = 10
        current_game_time.minute = 0

        self.game = DummyGame()
        self.builder = InteractionContextBuilder(self.game)

    def test_assistant_cannot_claim_fake_booking(self):
        assistant = NPC("assistant_1", "Mika", "assistant")
        llm = FakeLLM(
            {
                "spoken_text": "Your hotel is booked at Hotel California.",
                "tone": "confident",
                "requested_action": {"action_type": "confirm_booking", "target": "Hotel California"},
            }
        )
        engine = LLMInteractionEngine(self.game, llm_client=llm)
        context = self.builder.build(
            interaction_type="assistant_briefing",
            participant=assistant,
            participant_role="assistant",
            allowed_action_topics=["confirm_booking"],
        )

        result = engine.run_interaction(context, "Are we booked?")

        self.assertIsNone(result.approved_action)
        self.assertIn("blocked_unconfirmed_booking_claim", result.validation_messages)

    def test_conversation_tone_changes_with_relationship_and_fame_gap(self):
        friendly = NPC("npc_friend", "Nova", "artist")
        friendly.relationship_score = 40
        friendly.fame = 10

        hostile = NPC("npc_hostile", "Icon", "artist")
        hostile.relationship_score = -25
        hostile.fame = 220

        engine = LLMInteractionEngine(self.game, llm_client=None)

        ctx_warm = self.builder.build("in_person", friendly, "artist")
        ctx_cold = self.builder.build("in_person", hostile, "artist")

        warm = engine.run_interaction(ctx_warm, "Hey")
        cold = engine.run_interaction(ctx_cold, "Hey")

        self.assertNotEqual(warm.output.tone, cold.output.tone)

    def test_personality_profile_changes_expression_style(self):
        assistant = NPC("assistant_1", "Mika", "assistant")
        rival = NPC("rival_1", "Rex", "rival")
        rival.personality_key = "rival"

        engine = LLMInteractionEngine(self.game, llm_client=None)
        assistant_ctx = self.builder.build("in_person", assistant, "assistant")
        rival_ctx = self.builder.build("in_person", rival, "rival")

        a = engine.run_interaction(assistant_ctx, "Hi")
        r = engine.run_interaction(rival_ctx, "Hi")

        self.assertIn(assistant_ctx.personality_profile.archetype, {"professional", "friendly", "default"})
        self.assertEqual(rival_ctx.personality_profile.archetype, PERSONALITY_LIBRARY["rival"].archetype)
        self.assertNotEqual(a.output.tone, r.output.tone)

    def test_memory_references_are_grounded_in_real_events_only(self):
        npc = NPC("assistant_1", "Mika", "assistant")
        self.game.world_memory.add(WorldMemoryEntry("missed_gig", ["Hero"], "Austin", current_game_time.copy(), impact_score=4.0))

        ctx = self.builder.build("assistant_briefing", npc, "assistant")
        result = LLMInteractionEngine(self.game, llm_client=None).run_interaction(ctx, "brief me")

        self.assertIn("missed", result.output.spoken_text.lower())
        self.assertNotIn("invented", result.output.spoken_text.lower())

    def test_celebrity_mode_dismissive_vs_open_with_fame_gap(self):
        celeb = NPC("celeb_1", "Starlight", "celebrity")
        celeb.fame = 300
        celeb.relationship_score = -5
        engine = LLMInteractionEngine(self.game, llm_client=None)

        self.game.player.fame = 5
        low_ctx = self.builder.build("in_person", celeb, "celebrity")
        low = engine.run_interaction(low_ctx, "Hey")

        self.game.player.fame = 260
        celeb.relationship_score = 35
        high_ctx = self.builder.build("in_person", celeb, "celebrity")
        high = engine.run_interaction(high_ctx, "Hey")

        self.assertIn("quick", low.output.spoken_text.lower())
        self.assertIn("listening", high.output.spoken_text.lower())

    def test_social_media_voice_profiles_are_distinct(self):
        layer = SocialMediaExpressionLayer(llm_client=None)
        entry = WorldMemoryEntry("missed_gig", ["Hero"], "Austin", current_game_time.copy(), impact_score=5.0)

        fan = layer.generate_from_memory(entry, style="fan_post")
        rival = layer.generate_from_memory(entry, style="rival_post")
        media = layer.generate_from_memory(entry, style="news_blurb")

        self.assertNotEqual(fan["text"], rival["text"])
        self.assertNotEqual(media["voice_archetype"], fan["voice_archetype"])

    def test_requested_action_requires_validation_before_execution(self):
        assistant = NPC("assistant_1", "Mika", "assistant")
        llm = FakeLLM(
            {
                "spoken_text": "I'll leave a plan note.",
                "tone": "professional",
                "requested_action": {"action_type": "mark_plan_note", "note": "Call promoter at noon"},
            }
        )
        engine = LLMInteractionEngine(self.game, llm_client=llm)
        context = self.builder.build(
            interaction_type="assistant_briefing",
            participant=assistant,
            participant_role="assistant",
            allowed_action_topics=["mark_plan_note"],
        )

        before = len(self.game.player.feedback_received)
        result = engine.run_interaction(context, "Add a reminder")

        self.assertEqual(len(self.game.player.feedback_received), before)  # no mutation from raw output
        self.assertIsNotNone(result.approved_action)

        applied = engine.execute_approved_action(result.approved_action)
        self.assertTrue(applied)
        self.assertEqual(len(self.game.player.feedback_received), before + 1)

    def test_media_generation_references_real_events_only(self):
        layer = SocialMediaExpressionLayer(llm_client=FakeMediaLLM())
        real = WorldMemoryEntry("missed_gig", ["Hero"], "Austin", current_game_time.copy(), impact_score=5.0)
        fake = WorldMemoryEntry("made_up_viral_moment", ["Hero"], "Austin", current_game_time.copy(), impact_score=9.0)

        real_post = layer.generate_from_memory(real, style="news_blurb")
        fake_post = layer.generate_from_memory(fake, style="news_blurb")

        self.assertIsNotNone(real_post)
        self.assertEqual(real_post["source_event"], "missed_gig")
        self.assertIsNone(fake_post)

    def test_fallback_template_rendering_works_without_llm(self):
        npc = NPC("promoter_1", "Dax", "promoter")
        engine = LLMInteractionEngine(self.game, llm_client=None)
        context = self.builder.build("phone_call", npc, "promoter")

        result = engine.run_interaction(context, "What's lined up?")

        self.assertIn("Dax", result.output.spoken_text)
        self.assertTrue(result.output.tone)

    def test_fallback_rendering_is_structurally_consistent(self):
        npc = NPC("mgr_1", "Kai", "manager")
        ctx = self.builder.build("phone_call", npc, "manager")
        out = LLMInteractionEngine(self.game, llm_client=None).run_interaction(ctx, "update me").output
        self.assertIsInstance(out.spoken_text, str)
        self.assertIsInstance(out.tone, str)
        self.assertTrue(hasattr(out, "suggested_intent"))
        self.assertTrue(hasattr(out, "requested_action"))

    def test_no_state_mutation_from_raw_llm_output_alone(self):
        self.game.player.schedule.add_event(
            GameTime(2024, 1, 1, 18, 0),
            GameTime(2024, 1, 1, 20, 0),
            "Show @ Rusty Nail",
            "Gig",
            {"requires_presence": True, "location_name": "Austin"},
        )
        promoter = NPC("promoter_1", "Dax", "promoter")
        llm = FakeLLM(
            {
                "spoken_text": "Done. I changed your whole schedule.",
                "tone": "confident",
                "requested_action": {"action_type": "reschedule_all"},
            }
        )
        engine = LLMInteractionEngine(self.game, llm_client=llm)
        context = self.builder.build(
            interaction_type="phone_call",
            participant=promoter,
            participant_role="promoter",
            allowed_action_topics=["mark_plan_note"],
        )

        schedule_before = list(self.game.player.schedule.scheduled_items)
        result = engine.run_interaction(context, "Move everything")

        self.assertIsNone(result.approved_action)
        self.assertEqual(schedule_before, self.game.player.schedule.scheduled_items)


if __name__ == "__main__":
    unittest.main()
