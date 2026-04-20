from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from game.game_time import current_game_time


@dataclass(frozen=True)
class PersonalityProfile:
    archetype: str
    tone_tendencies: List[str]
    communication_style: str
    risk_attitude: str
    social_posture: str
    reliability_persona: str


PERSONALITY_LIBRARY: Dict[str, PersonalityProfile] = {
    "assistant": PersonalityProfile("professional", ["calm", "focused"], "direct", "cautious", "approachable", "organized"),
    "manager": PersonalityProfile("opportunistic", ["confident", "persuasive"], "direct", "opportunistic", "guarded", "disciplined"),
    "rival": PersonalityProfile("arrogant", ["blunt", "sarcastic"], "short", "bold", "dismissive", "overpromising"),
    "celebrity": PersonalityProfile("professional", ["cool", "selective"], "short", "cautious", "guarded", "disciplined"),
    "fan_voice": PersonalityProfile("friendly", ["enthusiastic", "emotional"], "verbose", "bold", "approachable", "sloppy"),
    "media_voice": PersonalityProfile("opportunistic", ["framed", "punchy"], "direct", "bold", "guarded", "disciplined"),
    "default": PersonalityProfile("professional", ["neutral"], "direct", "cautious", "guarded", "organized"),
}


@dataclass
class InteractionContext:
    interaction_type: str
    participant_id: str
    participant_name: str
    participant_role: str
    location_context: str
    relationship_state: Dict[str, Any]
    recent_memory: List[str]
    visibility_state: Dict[str, float]
    schedule_context: List[str]
    confirmed_plans: List[str]
    allowed_action_topics: List[str]
    tone_hooks: List[str]
    hard_truth_constraints: Dict[str, Any]
    personality_profile: PersonalityProfile
    emotional_stance: str
    reputation_context: Dict[str, Any]
    identity_hooks: List[str]


@dataclass
class InteractionOutput:
    spoken_text: str
    tone: str
    suggested_intent: Optional[str] = None
    requested_action: Optional[Dict[str, Any]] = None
    referenced_entities: List[str] = field(default_factory=list)
    stance: str = "neutral"


@dataclass
class InteractionResult:
    output: InteractionOutput
    approved_action: Optional[Dict[str, Any]] = None
    validation_messages: List[str] = field(default_factory=list)


class InteractionContextBuilder:
    def __init__(self, game):
        self.game = game

    def build(
        self,
        interaction_type: str,
        participant,
        participant_role: str,
        allowed_action_topics: Optional[List[str]] = None,
        tone_hooks: Optional[List[str]] = None,
    ) -> InteractionContext:
        player = self.game.player
        participant_id = getattr(participant, "npc_id", getattr(participant, "name", "unknown"))
        participant_name = getattr(participant, "name", "Unknown")
        relationship_score = getattr(participant, "relationship_score", 0)
        relationship_label = getattr(getattr(participant, "relationship_with_player", None), "name", "NEUTRAL")
        fame_gap = getattr(participant, "fame", 0) - getattr(player, "fame", 0)

        city = player.current_location.name if player and player.current_location else "Unknown"
        place = player.current_poi.name if player and player.current_poi else city
        location_context = f"{city} - {place}"
        if self.game.game_state == "travel_active" and self.game.travel_manager:
            location_context = f"In transit to {self.game.travel_manager.destination.name}"

        recent_memory = self._recent_memory_for(participant_id=participant_id, player_name=player.name if player else None)
        visibility_state = self._visibility_for(participant_id, city)
        schedule_context = self._schedule_lines(limit=4)
        confirmed_plans = self._confirmed_plan_labels()
        personality = self._resolve_personality(participant, participant_role, interaction_type)
        emotional_stance = self._derive_emotional_stance(
            relationship_score=relationship_score,
            relationship_label=relationship_label,
            fame_gap=fame_gap,
            recent_memory=recent_memory,
        )
        reputation_context, identity_hooks = self._reputation_context(participant_id, player.name if player else None, city)

        return InteractionContext(
            interaction_type=interaction_type,
            participant_id=str(participant_id),
            participant_name=participant_name,
            participant_role=participant_role,
            location_context=location_context,
            relationship_state={
                "score": relationship_score,
                "label": relationship_label,
                "fame_gap": fame_gap,
                "trust_proxy": relationship_score,
            },
            recent_memory=recent_memory,
            visibility_state=visibility_state,
            schedule_context=schedule_context,
            confirmed_plans=confirmed_plans,
            allowed_action_topics=list(allowed_action_topics or []),
            tone_hooks=list(tone_hooks or []),
            hard_truth_constraints={
                "confirmed_plans_only": True,
                "no_unbacked_claims": True,
                "no_state_mutation_from_text": True,
            },
            personality_profile=personality,
            emotional_stance=emotional_stance,
            reputation_context=reputation_context,
            identity_hooks=identity_hooks,
        )

    def _recent_memory_for(self, participant_id: str, player_name: Optional[str]) -> List[str]:
        if not hasattr(self.game, "world_memory"):
            return []
        lines: List[str] = []
        for entry in reversed(self.game.world_memory.entries[-30:]):
            entities = entry.involved_entities or []
            if participant_id not in entities and (player_name and player_name not in entities):
                continue
            lines.append(entry.event_type)
            if len(lines) >= 6:
                break
        return lines

    def _visibility_for(self, participant_id: str, city: str) -> Dict[str, float]:
        if not hasattr(self.game, "visibility_system"):
            return {}
        return self.game.visibility_system.get_visibility(participant_id, city)

    def _schedule_lines(self, limit: int = 4) -> List[str]:
        player = self.game.player
        if not player or not hasattr(player, "schedule"):
            return []
        upcoming = player.schedule.get_upcoming_events(current_game_time.copy(), limit=limit)
        lines = []
        for item in upcoming:
            lines.append(f"{item.start_time.get_time_string_for_schedule()} - {item.description}")
        return lines

    def _confirmed_plan_labels(self) -> List[str]:
        player = self.game.player
        labels: List[str] = []
        if player and hasattr(player, "schedule"):
            for item in player.schedule.get_upcoming_events(current_game_time.copy(), limit=8):
                labels.append(item.description)
        if getattr(player, "active_opportunities", None):
            for opp_id, details in player.active_opportunities.items():
                if isinstance(details, dict) and details.get("status") == "available":
                    labels.append(f"opportunity:{opp_id}")
        if getattr(self.game, "travel_manager", None):
            labels.append(f"travel:{self.game.travel_manager.destination.name}")
        return labels

    def _resolve_personality(self, participant, participant_role: str, interaction_type: str) -> PersonalityProfile:
        explicit_key = getattr(participant, "personality_key", None)
        if explicit_key and explicit_key in PERSONALITY_LIBRARY:
            return PERSONALITY_LIBRARY[explicit_key]
        if interaction_type in {"media_quote", "social_post", "news_blurb"}:
            if participant_role in {"fan", "fans"}:
                return PERSONALITY_LIBRARY["fan_voice"]
            if participant_role in {"media", "interviewer"}:
                return PERSONALITY_LIBRARY["media_voice"]
        if participant_role in {"assistant", "manager", "rival", "celebrity"}:
            return PERSONALITY_LIBRARY[participant_role]
        return PERSONALITY_LIBRARY["default"]

    def _derive_emotional_stance(self, relationship_score: int, relationship_label: str, fame_gap: int, recent_memory: List[str]) -> str:
        lower_mem = {m.lower() for m in recent_memory}
        if any("rivalry" in m for m in lower_mem):
            return "competitive"
        if any("missed" in m or "late" in m for m in lower_mem):
            return "critical"
        if relationship_score >= 35 or relationship_label in {"ALLY", "FRIENDLY"}:
            return "open"
        if relationship_score <= -20 or relationship_label in {"HOSTILE", "UNFRIENDLY"}:
            return "dismissive"
        if fame_gap >= 70:
            return "guarded"
        return "neutral"

    def _reputation_context(self, participant_id: str, player_name: Optional[str], city: str):
        if not hasattr(self.game, "reputation_system"):
            return {}, []
        rep = self.game.reputation_system
        participant_tags = rep.summarize(participant_id, scope=f"city:{city}", limit=2) + rep.summarize(participant_id, scope="global", limit=2)
        player_tags = rep.summarize(player_name, scope=f"city:{city}", limit=2) if player_name else []
        hooks = []
        if player_tags:
            hooks.append(f"player_known_for:{', '.join(player_tags[:2])}")
        if participant_tags:
            hooks.append(f"participant_known_for:{', '.join(participant_tags[:2])}")
        return {
            "participant_tags": participant_tags[:3],
            "player_tags": player_tags[:3],
            "participant_bias": rep.bias_for(participant_id, location=city),
            "player_bias": rep.bias_for(player_name, location=city) if player_name else {},
        }, hooks


class LLMInteractionEngine:
    def __init__(self, game, llm_client=None):
        self.game = game
        self.llm_client = llm_client

    def run_interaction(self, context: InteractionContext, player_input: str) -> InteractionResult:
        raw = self._render_structured_output(context, player_input)
        output = self._coerce_output(raw)
        validated_action, messages = self._validate_requested_action(context, output.requested_action)
        return InteractionResult(output=output, approved_action=validated_action, validation_messages=messages)

    def execute_approved_action(self, approved_action: Dict[str, Any]) -> bool:
        if not approved_action:
            return False
        action_type = approved_action.get("action_type")
        if action_type == "mark_plan_note":
            note = approved_action.get("note")
            if note and hasattr(self.game.player, "feedback_received"):
                self.game.player.feedback_received.append({"type": "assistant_note", "text": note})
                return True
        return False

    def _render_structured_output(self, context: InteractionContext, player_input: str) -> Dict[str, Any]:
        if self.llm_client:
            return self.llm_client.generate(context=context, player_input=player_input)
        return self._template_fallback(context, player_input)

    def _template_fallback(self, context: InteractionContext, player_input: str) -> Dict[str, Any]:
        profile = context.personality_profile
        tone = profile.tone_tendencies[0] if profile.tone_tendencies else "neutral"
        rel = context.relationship_state.get("score", 0)
        fame_gap = context.relationship_state.get("fame_gap", 0)
        if rel >= 30:
            tone = "warm" if "cold" not in profile.tone_tendencies else "measured"
        elif rel <= -15:
            tone = "dismissive"
        elif fame_gap >= 60:
            tone = "aloof"
        if context.emotional_stance == "competitive":
            tone = "sharp"
        if context.reputation_context.get("player_bias", {}).get("scrutiny", 0) > 0.9:
            tone = "measured"

        text = f"{context.participant_name}: "
        if context.interaction_type == "assistant_briefing":
            if context.confirmed_plans:
                text += f"Current confirmed items: {', '.join(context.confirmed_plans[:3])}."
            else:
                text += "No confirmed items on the board right now."
            if context.recent_memory:
                text += f" Latest note: {self._memory_phrase(context.recent_memory[0])}."
            if context.reputation_context.get("player_tags"):
                text += f" Scene read: {', '.join(context.reputation_context['player_tags'][:2])}."
        elif context.interaction_type == "phone_call":
            text += "I got your call. We can talk through what's already lined up."
        elif context.interaction_type == "in_person":
            if fame_gap >= 80 and rel <= 0:
                text += "Make it quick."
            elif rel >= 25:
                text += "Good timing. I'm listening."
            else:
                text += "Yeah?"
            if context.recent_memory and context.emotional_stance in {"competitive", "critical"}:
                text += f" I remember: {self._memory_phrase(context.recent_memory[0])}."
            participant_tags = context.reputation_context.get("participant_tags") or []
            if participant_tags:
                text += f" People read me as {participant_tags[0]}."
        else:
            text += "Good to see you."

        suggested_intent = "maintain_contact"
        if "collab" in player_input.lower():
            suggested_intent = "explore_collab"

        return {
            "spoken_text": text,
            "tone": tone,
            "suggested_intent": suggested_intent,
            "requested_action": None,
            "referenced_entities": [context.participant_id],
            "stance": context.emotional_stance,
        }

    def _memory_phrase(self, event_type: str) -> str:
        mapping = {
            "missed_gig": "you missed that set",
            "great_performance": "last show landed well",
            "rivalry_escalation": "the rivalry noise is up",
            "late_obligation": "timing has been tight",
        }
        return mapping.get(event_type, event_type.replace("_", " "))

    def _coerce_output(self, raw: Dict[str, Any]) -> InteractionOutput:
        return InteractionOutput(
            spoken_text=str(raw.get("spoken_text", "...")),
            tone=str(raw.get("tone", "neutral")),
            suggested_intent=raw.get("suggested_intent"),
            requested_action=raw.get("requested_action"),
            referenced_entities=list(raw.get("referenced_entities", [])),
            stance=str(raw.get("stance", "neutral")),
        )

    def _validate_requested_action(self, context: InteractionContext, action: Optional[Dict[str, Any]]):
        if not action:
            return None, []

        messages = []
        action_type = action.get("action_type")
        if action_type not in context.allowed_action_topics:
            messages.append(f"blocked_action_topic:{action_type}")
            return None, messages

        if action_type == "confirm_booking":
            target = str(action.get("target", ""))
            if target not in context.confirmed_plans:
                messages.append("blocked_unconfirmed_booking_claim")
                return None, messages

        if action_type == "create_opportunity":
            target = str(action.get("target", ""))
            if f"opportunity:{target}" not in context.confirmed_plans:
                messages.append("blocked_unapproved_opportunity")
                return None, messages

        return dict(action), messages


class SocialMediaExpressionLayer:
    """Optional expressive framing of real events; never invents events."""

    ALLOWED_EVENT_TYPES = {
        "great_performance",
        "poor_performance",
        "missed_gig",
        "late_obligation",
        "replacement_slot",
        "collaboration",
        "rivalry_escalation",
        "assistant_success",
        "assistant_prep_failure",
    }

    def __init__(self, game=None, llm_client=None):
        if llm_client is None and game is not None and not hasattr(game, "world_memory"):
            # Backward-compatible constructor for SocialMediaExpressionLayer(llm_client=...)
            self.game = None
            self.llm_client = game
        else:
            self.game = game
            self.llm_client = llm_client

    def generate_from_memory(self, entry, style: str = "social_post") -> Optional[Dict[str, str]]:
        if not entry or entry.event_type not in self.ALLOWED_EVENT_TYPES:
            return None

        voice_profile = self._voice_profile_for(style, entry)
        payload = {
            "style": style,
            "event_type": entry.event_type,
            "location": entry.location,
            "entities": list(entry.involved_entities or []),
            "voice_profile": {
                "archetype": voice_profile.archetype,
                "tone_tendencies": voice_profile.tone_tendencies,
                "communication_style": voice_profile.communication_style,
            },
        }

        if self.llm_client:
            out = self.llm_client.generate_media(payload)
            if isinstance(out, dict) and out.get("text"):
                return {
                    "style": style,
                    "text": str(out["text"]),
                    "source_event": entry.event_type,
                    "voice_archetype": voice_profile.archetype,
                }

        return {
            "style": style,
            "text": self._template_render(entry, voice_profile),
            "source_event": entry.event_type,
            "voice_archetype": voice_profile.archetype,
        }

    def _template_render(self, entry, voice_profile: PersonalityProfile) -> str:
        neutral_mapping = {
            "great_performance": "Crowd buzz climbed after last night's set.",
            "poor_performance": "Last show drew mixed reactions.",
            "missed_gig": "A replacement stepped in after a no-show.",
            "late_obligation": "A late arrival stirred backstage chatter.",
            "replacement_slot": "A replacement artist picked up a slot.",
            "collaboration": "People are talking about a new collaboration.",
            "rivalry_escalation": "A rivalry storyline is heating up online.",
            "assistant_success": "Crew moved cleanly behind the scenes.",
            "assistant_prep_failure": "A prep slip caused some noise backstage.",
        }
        rep_suffix = ""
        if self.game and hasattr(self.game, "reputation_system") and entry.involved_entities:
            tags = self.game.reputation_system.summarize(entry.involved_entities[0], scope=f"city:{entry.location}" if entry.location else "global", limit=1)
            if tags:
                rep_suffix = f" (current read: {tags[0]})"

        if voice_profile.archetype == "friendly":
            fan_mapping = {
                "great_performance": "Fans are hyped after that set.",
                "missed_gig": "People were bummed after the no-show.",
            }
            return fan_mapping.get(entry.event_type, neutral_mapping.get(entry.event_type, "People are talking.")) + rep_suffix
        if voice_profile.archetype == "arrogant":
            rival_mapping = {
                "missed_gig": "Another no-show? Scene noticed.",
                "great_performance": "Decent night, but the bar's still high.",
            }
            return rival_mapping.get(entry.event_type, neutral_mapping.get(entry.event_type, "Scene chatter is active.")) + rep_suffix
        return neutral_mapping.get(entry.event_type, "Scene chatter is active.") + rep_suffix

    def _voice_profile_for(self, style: str, entry) -> PersonalityProfile:
        if style in {"fan_post", "fan_reaction"}:
            return PERSONALITY_LIBRARY["fan_voice"]
        if style in {"rival_post", "rival_reaction"}:
            return PERSONALITY_LIBRARY["rival"]
        if style in {"news_blurb", "media_quote", "interview"}:
            return PERSONALITY_LIBRARY["media_voice"]
        if entry.event_type == "rivalry_escalation":
            return PERSONALITY_LIBRARY["media_voice"]
        return PERSONALITY_LIBRARY["default"]
