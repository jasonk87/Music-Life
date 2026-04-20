from __future__ import annotations

from typing import Dict, List

from game.game_time import current_game_time, get_current_time_str


FORBIDDEN_WORDS = {"risk", "obligation"}


class PlayerUIShell:
    """Lightweight, signal-driven player-facing shell.

    Presents grounded context/schedule/scene/feed without advice or internal math.
    """

    def __init__(self, game):
        self.game = game

    def build(self) -> Dict:
        return {
            "top_context": self.top_context_bar(),
            "schedule": self.schedule_panel(),
            "scene": self.scene_panel(),
            "world_feed": self.world_feed_panel(),
            "contacts": self.contacts_panel(),
            "projects": self.project_panel(),
        }

    def top_context_bar(self) -> Dict:
        context = self.game.ui_signals.get_current_context() if hasattr(self.game, "ui_signals") else {}
        tags = self.game.ui_signals.get_condition_tags() if hasattr(self.game, "ui_signals") else []
        tags = [self._clean_text(t) for t in tags]

        return {
            "headline": self._clean_text(context.get("label", "Unknown Place")),
            "city": context.get("city"),
            "state": context.get("state", "grounded"),
            "clock": get_current_time_str(),
            "day": f"Day {current_game_time.day}",
            "tags": tags[:6],
        }

    def schedule_panel(self) -> Dict[str, List[str]]:
        groups = self.game.ui_signals.get_schedule_view(limit=10) if hasattr(self.game, "ui_signals") else {"Today": [], "Tomorrow": [], "Upcoming": []}
        out = {"Today": [], "Tomorrow": [], "Upcoming": []}
        for bucket in out.keys():
            for item in groups.get(bucket, []):
                title = item.get("title", "Untitled")
                city = item.get("city")
                t = item.get("time", "")
                if city:
                    line = f"{title} — {city} ({t})"
                else:
                    line = f"{title} ({t})"
                out[bucket].append(self._clean_text(line))
        return out

    def scene_panel(self) -> Dict:
        player = getattr(self.game, "player", None)
        if not player:
            return {"header": "No active character", "actions": [], "interaction": None}

        context = self.game.ui_signals.get_current_context() if hasattr(self.game, "ui_signals") else {}
        header = self._clean_text(context.get("label", "Current Scene"))

        if getattr(self.game, "game_state", None) == "travel_active" and getattr(self.game, "travel_manager", None):
            actions = []
            if hasattr(self.game, "transit_layer"):
                actions = list(self.game.transit_layer.available_actions(self.game, self.game.travel_manager).values())
            actions = [self._clean_text(a) for a in actions]
            return {
                "header": header,
                "actions": actions,
                "interaction": self._interaction_view(),
                "transit": {
                    "destination": getattr(self.game.travel_manager.destination, "name", None),
                    "time_remaining": context.get("time_remaining"),
                    "next_item": context.get("next_item"),
                },
            }

        actions = []
        if hasattr(self.game, "location_action_engine") and player.current_poi and player.current_location:
            generated = self.game.location_action_engine.generate_actions(player, player.current_poi, player.current_location)
            actions = [self._clean_text(a.label) for a in generated]
        if not actions:
            actions = ["Look Around", "Check Phone", "Leave"]

        return {
            "header": header,
            "actions": actions,
            "interaction": self._interaction_view(),
            "transit": None,
        }

    def world_feed_panel(self) -> List[str]:
        items = self.game.ui_signals.get_world_feed(limit=8) if hasattr(self.game, "ui_signals") else []
        return [self._clean_text(x.get("text", "")) for x in items if x.get("text")]

    def contacts_panel(self) -> List[Dict[str, str]]:
        player = getattr(self.game, "player", None)
        if not player:
            return []

        entries = []
        if hasattr(self.game, "delegation_system"):
            for role_name in ["assistant", "manager", "driver", "security"]:
                role = self.game.delegation_system.get_role(player, role_name)
                if not role:
                    continue
                label = role_name.title()
                npc_name = role.npc_id or "Assigned"
                entries.append({"name": npc_name, "role": label, "type": "support"})

        for npc_id in list(getattr(player, "contacts", []) or [])[:6]:
            npc = self.game.NPC_REGISTRY.get(npc_id) if hasattr(self.game, "NPC_REGISTRY") else None
            if not npc:
                continue
            entries.append({"name": npc.name, "role": "Contact", "type": "recurring"})

        return entries[:8]

    def project_panel(self) -> List[str]:
        player = getattr(self.game, "player", None)
        if not player or not hasattr(self.game, "production_pipeline"):
            return []

        lines = []
        for p in self.game.production_pipeline.projects.values():
            if p.lead_artist_id != player.name:
                continue
            stage = p.current_stage.replace("_", " ").title()
            proj = p.project_type.replace("_", " ").title()
            lines.append(self._clean_text(f"{proj} — {stage}"))
        return lines[:6]

    def _interaction_view(self):
        if getattr(self.game, "selected_npc", None):
            npc = self.game.selected_npc
            return {
                "with": getattr(npc, "name", "Unknown"),
                "last_lines": list(getattr(self.game, "conversation_history", [])[-2:]),
            }
        return None

    def _clean_text(self, text: str) -> str:
        clean = str(text or "").strip()
        for forbidden in FORBIDDEN_WORDS:
            clean = clean.replace(forbidden, "")
            clean = clean.replace(forbidden.title(), "")
        return " ".join(clean.split())
