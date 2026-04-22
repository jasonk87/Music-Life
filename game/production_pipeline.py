from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid
import random

from game.game_time import current_game_time
from game.world_memory import WorldMemoryEntry


@dataclass
class CreativeProject:
    project_id: str
    project_type: str
    lead_artist_id: str
    collaborator_ids: List[str] = field(default_factory=list)
    organization_id: Optional[str] = None
    current_stage: str = "concept"
    status: str = "active"
    target_release: Optional[str] = None
    budget_spent: float = 0.0
    quality_score: float = 0.0
    progress_points: float = 0.0
    deadline_day: Optional[int] = None
    stage_history: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


class ProductionPipelineSystem:
    STAGE_MAP = {
        "song": ["concept", "writing", "recording", "mix_master", "ready_for_release", "released"],
        "single": ["concept", "writing", "recording", "mix_master", "ready_for_release", "released"],
        "album": ["concept", "writing", "recording", "mix_master", "ready_for_release", "released"],
        "music_video": ["concept", "schedule_prep", "shoot", "edit_finalize", "ready_for_release", "released"],
        "promo_cycle": ["concept", "schedule_prep", "appearance", "ready_for_release", "released"],
    }

    def __init__(self, game):
        self.game = game
        self.projects: Dict[str, CreativeProject] = {}

    def create_project(
        self,
        project_type: str,
        lead_artist_id: str,
        collaborator_ids: Optional[List[str]] = None,
        organization_id: Optional[str] = None,
        target_release: Optional[str] = None,
        deadline_day: Optional[int] = None,
    ) -> CreativeProject:
        pid = f"proj_{uuid.uuid4().hex[:10]}"
        project = CreativeProject(
            project_id=pid,
            project_type=project_type,
            lead_artist_id=lead_artist_id,
            collaborator_ids=list(collaborator_ids or []),
            organization_id=organization_id,
            target_release=target_release,
            deadline_day=deadline_day,
            stage_history=["concept"],
        )
        self.projects[pid] = project
        self._memory(project, "project_started")
        return project

    def stage_sequence(self, project: CreativeProject) -> List[str]:
        return self.STAGE_MAP.get(project.project_type, self.STAGE_MAP["song"])

    def _resolve_destination_id(self, location_name: Optional[str]) -> Optional[str]:
        if not location_name:
            return None

        resolver = getattr(self.game, "get_poi_or_venue_by_id", None)
        if callable(resolver):
            obj = resolver(location_name)
            if obj:
                return getattr(obj, "poi_id", getattr(obj, "venue_id", None))

        target_name = str(location_name).strip().lower()
        if not target_name:
            return None

        locations = []
        if getattr(self.game, "player", None) and getattr(self.game.player, "current_location", None):
            locations.append(self.game.player.current_location)
        world_map = getattr(self.game, "WORLD_MAP", None)
        if isinstance(world_map, dict):
            locations.extend(world_map.values())

        for loc in locations:
            for poi in getattr(loc, "points_of_interest", []) or []:
                if str(getattr(poi, "name", "")).strip().lower() == target_name:
                    return getattr(poi, "poi_id", None)
            for venue in getattr(loc, "venues", []) or []:
                if str(getattr(venue, "name", "")).strip().lower() == target_name:
                    return getattr(venue, "venue_id", None)

        return None

    def schedule_work_item(
        self,
        project_id: str,
        title: str,
        category: str,
        days_ahead: int,
        minutes: int,
        location_name: Optional[str] = None,
        requires_presence: bool = True,
        cost: float = 0.0,
    ) -> bool:
        project = self.projects.get(project_id)
        if not project:
            return False

        when = current_game_time.copy()
        flow = getattr(self.game, "life_flow", None)
        tuned_days = flow.modulate_days_ahead(days_ahead, source="production", major=(category in {"Gig", "Label Visit"})) if flow else days_ahead
        when.add_days(tuned_days)
        details = {
            "requires_presence": requires_presence,
            "location_name": location_name or (self.game.player.current_location.name if self.game.player and self.game.player.current_location else None),
            "project_id": project_id,
            "work_minutes": minutes,
            "work_category": category,
        }
        if requires_presence and self.game.player and self.game.player.current_poi:
            current_ref = getattr(
                self.game.player.current_poi,
                "poi_id",
                getattr(self.game.player.current_poi, "venue_id", None),
            )
            if current_ref:
                details["destination_id"] = current_ref
        if requires_presence and not details.get("destination_id"):
            resolved_dest = self._resolve_destination_id(location_name)
            if resolved_dest:
                details["destination_id"] = resolved_dest
        if project.organization_id:
            details["organization_id"] = project.organization_id
        if cost > 0:
            details["project_cost"] = cost

        if project.lead_artist_id == getattr(self.game.player, "name", None):
            self.game.player.schedule.add_event(when, when, title, category, details)
            if flow:
                flow.record_pressure("production", 0.9 if category in {"Gig", "Label Visit"} else 0.55)
            return True
        return False

    def apply_work_session(
        self,
        project_id: str,
        minutes_spent: int,
        resource_quality: float,
        condition_score: float,
        pressure_level: float,
        interruption_level: float,
        budget_spend: float,
        collaborator_fit: float = 0.5,
    ) -> Optional[CreativeProject]:
        project = self.projects.get(project_id)
        if not project or project.status != "active":
            return None

        session_factor = max(0.1, minutes_spent / 120.0)
        quality_gain = (
            session_factor * 0.35
            + max(0.0, resource_quality) * 0.28
            + max(0.0, condition_score) * 0.2
            + max(0.0, collaborator_fit) * 0.17
            - max(0.0, pressure_level) * 0.22
            - max(0.0, interruption_level) * 0.2
        )
        project.quality_score += quality_gain
        project.progress_points += max(0.2, session_factor + resource_quality * 0.35 - interruption_level * 0.25)
        project.budget_spent += max(0.0, budget_spend)

        if budget_spend > 0 and project.lead_artist_id == getattr(self.game.player, "name", None):
            self.game.player.money -= budget_spend

        if pressure_level > 0.75:
            self._memory(project, "rushed_session")
        else:
            self._memory(project, "studio_session_completed")

        self._maybe_advance_stage(project)
        return project

    def _maybe_advance_stage(self, project: CreativeProject):
        stages = self.stage_sequence(project)
        idx = stages.index(project.current_stage)
        if idx >= len(stages) - 1:
            return
        threshold = 1.4 + idx * 0.75
        if project.progress_points < threshold:
            return

        project.progress_points = max(0.0, project.progress_points - threshold)
        project.current_stage = stages[idx + 1]
        project.stage_history.append(project.current_stage)

        if project.current_stage == "ready_for_release":
            self._memory(project, "project_ready_for_release")

    def link_collaboration(self, project_id: str, collaborator_id: str) -> bool:
        project = self.projects.get(project_id)
        if not project:
            return False
        if collaborator_id not in project.collaborator_ids:
            project.collaborator_ids.append(collaborator_id)
            self._memory(project, "collaboration_confirmed", {"collaborator": collaborator_id})
        return True

    def release_project(self, project_id: str) -> bool:
        project = self.projects.get(project_id)
        if not project:
            return False
        stages = self.stage_sequence(project)
        if project.current_stage not in {"ready_for_release", "released"}:
            return False

        project.current_stage = "released"
        project.status = "released"
        project.stage_history.append("released")

        if project.project_type in {"single", "song"}:
            self._memory(project, "single_released")
        elif project.project_type == "album":
            self._memory(project, "album_released")
        elif project.project_type == "music_video":
            self._memory(project, "video_shot")

        if project.quality_score >= 2.6:
            self._memory(project, "breakout_release")
        elif project.quality_score <= 0.7:
            self._memory(project, "poor_release_reception")

        self.generate_promo_work_items(project_id)
        return True

    def generate_promo_work_items(self, project_id: str):
        project = self.projects.get(project_id)
        if not project:
            return
        if project.lead_artist_id != getattr(self.game.player, "name", None):
            return

        flow = getattr(self.game, "life_flow", None)
        if flow and not flow.allow_pressure("promo", base_weight=1.0, major=True):
            # Keep promo real but give breathing room when heavily overloaded.
            day_one = 2
            day_two = 4
        else:
            day_one = 1
            day_two = 2

        self.schedule_work_item(
            project_id,
            title=f"Promo interview for {project.project_type}",
            category="Meeting",
            days_ahead=day_one,
            minutes=90,
            requires_presence=True,
            cost=0,
        )
        self.schedule_work_item(
            project_id,
            title=f"Autograph signing for {project.project_type}",
            category="Gig",
            days_ahead=day_two,
            minutes=120,
            requires_presence=True,
            cost=40,
        )
        self._memory(project, "promo_event_completed")

    def apply_contract_deadline_pressure(self, project_id: str, contract_review_strictness: float):
        project = self.projects.get(project_id)
        if not project:
            return
        pressure = max(0.0, contract_review_strictness)
        project.quality_score -= pressure * 0.25
        project.metadata["contract_pressure"] = pressure

    def tick(self, minutes: int):
        if minutes <= 0:
            return
        flow = getattr(self.game, "life_flow", None)
        chance_mult = flow.effective_pressure_multiplier() if flow else 1.0

        # Lightweight NPC participation under same pipeline logic
        for project in self.projects.values():
            if project.status != "active":
                continue
            if project.lead_artist_id == getattr(self.game.player, "name", None):
                continue
            base = 0.3 * chance_mult
            if random.random() < base:
                self.apply_work_session(
                    project.project_id,
                    minutes_spent=90,
                    resource_quality=0.55,
                    condition_score=0.55,
                    pressure_level=0.35,
                    interruption_level=0.25,
                    budget_spend=0,
                    collaborator_fit=0.5,
                )

    def _memory(self, project: CreativeProject, event_type: str, metadata: Optional[Dict] = None):
        if not hasattr(self.game, "world_memory"):
            return
        location = self.game.player.current_location.name if self.game.player and self.game.player.current_location else None
        self.game.world_memory.add(
            WorldMemoryEntry(
                event_type=event_type,
                involved_entities=[project.lead_artist_id] + list(project.collaborator_ids),
                location=location,
                timestamp=current_game_time.copy(),
                tags=["production", project.project_type],
                impact_score=1.5,
                metadata={"project_id": project.project_id, "stage": project.current_stage, **(metadata or {})},
                source_key=f"{event_type}:{project.project_id}:{current_game_time.get_time_string_for_schedule()}",
            )
        )
