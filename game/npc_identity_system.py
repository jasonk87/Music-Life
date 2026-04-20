from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from game.game_time import current_game_time
from game.world_memory import WorldMemoryEntry


@dataclass
class RoleTransition:
    npc_id: str
    from_role: Optional[str]
    to_role: Optional[str]
    reason: str


class NPCIdentitySystem:
    """Persistent identity-first model: people first, role tags second."""

    def __init__(self, game):
        self.game = game

    def ensure_identity_fields(self, npc):
        if not hasattr(npc, "role_tags"):
            npc.role_tags = set()
        if not hasattr(npc, "status"):
            npc.status = "active"
        if not hasattr(npc, "is_persistent"):
            npc.is_persistent = False
        if not hasattr(npc, "contact_access"):
            npc.contact_access = {
                "known_contact": False,
                "has_phone_number": False,
                "blocked": False,
                "mediated_by": None,
                "public_only": True,
            }
        if not hasattr(npc, "role_history"):
            npc.role_history = []

    def mark_meaningful_encounter(self, npc, context: str, role_hint: Optional[str] = None):
        self.ensure_identity_fields(npc)
        npc.is_persistent = True
        if role_hint:
            npc.role_tags.add(role_hint)
        if context == "met_in_person":
            npc.contact_access["known_contact"] = True
        self._record_identity_memory(npc, event_type="meaningful_encounter", metadata={"context": context})

    def transition_role(self, npc, from_role: Optional[str], to_role: Optional[str], reason: str) -> RoleTransition:
        self.ensure_identity_fields(npc)
        if from_role:
            npc.role_tags.discard(from_role)
        if to_role:
            npc.role_tags.add(to_role)
        npc.role_history.append(
            {
                "from": from_role,
                "to": to_role,
                "reason": reason,
                "timestamp": current_game_time.get_time_string_for_schedule(),
            }
        )
        self._record_identity_memory(
            npc,
            event_type="npc_role_transition",
            metadata={"from": from_role, "to": to_role, "reason": reason},
        )
        return RoleTransition(npc_id=npc.npc_id, from_role=from_role, to_role=to_role, reason=reason)

    def set_contact_access(self, npc, known_contact=None, has_phone_number=None, blocked=None, mediated_by=None, public_only=None):
        self.ensure_identity_fields(npc)
        if known_contact is not None:
            npc.contact_access["known_contact"] = bool(known_contact)
        if has_phone_number is not None:
            npc.contact_access["has_phone_number"] = bool(has_phone_number)
        if blocked is not None:
            npc.contact_access["blocked"] = bool(blocked)
        if mediated_by is not None:
            npc.contact_access["mediated_by"] = mediated_by
        if public_only is not None:
            npc.contact_access["public_only"] = bool(public_only)

    def can_reach(self, npc, channel: str = "phone") -> bool:
        self.ensure_identity_fields(npc)
        access = npc.contact_access
        if access.get("blocked"):
            return False
        if channel == "phone" and not access.get("has_phone_number"):
            return False
        if channel == "direct" and access.get("mediated_by"):
            return False
        if channel == "private" and access.get("public_only"):
            return False
        return access.get("known_contact", False)

    def hire_npc_into_support_role(self, player, npc, support_role: str, delegation_system, competence=0.6, reliability=0.65, experience=0.55):
        self.ensure_identity_fields(npc)
        npc.is_persistent = True
        self.set_contact_access(npc, known_contact=True, has_phone_number=True, public_only=False)
        from_role = "contact" if "contact" in npc.role_tags else None
        self.transition_role(npc, from_role=from_role, to_role=support_role, reason="hired_into_inner_circle")
        delegation_system.add_or_update_role(
            player,
            support_role,
            active=True,
            competence=competence,
            reliability=reliability,
            experience=experience,
            npc_id=npc.npc_id,
        )
        self._record_identity_memory(npc, event_type="npc_hired_support", metadata={"support_role": support_role})

    def end_support_role(self, player, npc, support_role: str, delegation_system, reason: str):
        self.ensure_identity_fields(npc)
        former_tag = f"former_{support_role}"
        self.transition_role(npc, from_role=support_role, to_role=former_tag, reason=reason)

        role = delegation_system.get_role(player, support_role)
        if role and getattr(role, "npc_id", None) == npc.npc_id:
            role.active = False

        self._record_identity_memory(npc, event_type="npc_support_role_ended", metadata={"support_role": support_role, "reason": reason})

    def _record_identity_memory(self, npc, event_type: str, metadata=None):
        if not hasattr(self.game, "world_memory") or not hasattr(self.game, "player") or not self.game.player:
            return
        self.game.world_memory.add(
            WorldMemoryEntry(
                event_type=event_type,
                involved_entities=[self.game.player.name, npc.npc_id],
                location=getattr(npc.current_location, "name", None),
                timestamp=current_game_time.copy(),
                tags=["identity", "relationship"],
                impact_score=1.2,
                metadata=metadata or {},
                source_key=f"{event_type}:{self.game.player.name}:{npc.npc_id}:{current_game_time.get_time_string_for_schedule()}",
            )
        )
