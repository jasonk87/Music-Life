from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid
import random

from game.game_time import current_game_time
from game.world_memory import WorldMemoryEntry


@dataclass
class ContractTerms:
    creative_control: float = 0.5
    output_expectation: int = 1          # releases expected each cycle
    appearance_expectation: int = 1      # appearances expected each cycle
    exclusivity: float = 0.5
    advance_style: str = "modest"
    review_strictness: float = 0.5


@dataclass
class Organization:
    organization_id: str
    name: str
    org_type: str = "label"
    home_city: Optional[str] = None
    tier: float = 0.5
    pressure_style: str = "balanced"
    member_npc_ids: List[str] = field(default_factory=list)
    artist_ids: List[str] = field(default_factory=list)
    policies: Dict = field(default_factory=dict)
    reputation: float = 0.0


@dataclass
class ArtistContract:
    contract_id: str
    organization_id: str
    artist_id: str
    start_time: object
    duration_days: int
    active: bool
    terms: ContractTerms
    leverage_snapshot: float
    standing: float = 0.0
    warnings: int = 0
    misses: int = 0
    contact_npc_id: Optional[str] = None
    last_pressure_day: int = -1


class OrganizationContractSystem:
    def __init__(self, game):
        self.game = game
        self.organizations: Dict[str, Organization] = {}
        self.contracts: Dict[str, ArtistContract] = {}

    def create_organization(
        self,
        organization_id: str,
        name: str,
        org_type: str = "label",
        home_city: Optional[str] = None,
        tier: float = 0.5,
        pressure_style: str = "balanced",
    ) -> Organization:
        org = Organization(
            organization_id=organization_id,
            name=name,
            org_type=org_type,
            home_city=home_city,
            tier=max(0.0, min(1.0, tier)),
            pressure_style=pressure_style,
        )
        self.organizations[organization_id] = org
        return org

    def attach_member_npc(self, organization_id: str, npc_id: str, role_tag: str = "label_contact") -> bool:
        org = self.organizations.get(organization_id)
        npc = self.game.NPC_REGISTRY.get(npc_id) if hasattr(self.game, "NPC_REGISTRY") else None
        if not org or not npc:
            return False

        if npc_id not in org.member_npc_ids:
            org.member_npc_ids.append(npc_id)

        if hasattr(self.game, "npc_identity"):
            self.game.npc_identity.ensure_identity_fields(npc)
            npc.is_persistent = True
            npc.role_tags.add(role_tag)
            npc.role_tags.add("organization_member")

        return True

    def compute_leverage(self, artist_id: str, organization_id: str, contact_npc_id: Optional[str] = None) -> float:
        org = self.organizations.get(organization_id)
        if not org:
            return 0.3

        visibility = 0.0
        reliability = 0.0
        momentum = 0.0
        rel_bias = 0.0

        if artist_id == getattr(self.game.player, "name", None):
            city = self.game.player.current_location.name if self.game.player and self.game.player.current_location else None
            vis = self.game.visibility_system.get_visibility(self.game.player.name, city)
            visibility = vis.get("public_visibility", 0.0)
            reliability = self.game.world_memory.reliability_score(self.game.player.name, current_game_time.copy())
            momentum = getattr(self.game.player, "fame", 0) / 100.0
        else:
            npc = self.game.NPC_REGISTRY.get(artist_id) if hasattr(self.game, "NPC_REGISTRY") else None
            if npc:
                visibility = getattr(npc, "fame", 0) / 3.0
                reliability = getattr(npc, "momentum", 0)
                momentum = getattr(npc, "fame", 0) / 120.0

        if contact_npc_id and hasattr(self.game, "NPC_REGISTRY"):
            contact = self.game.NPC_REGISTRY.get(contact_npc_id)
            if contact:
                rel_bias = getattr(contact, "relationship_score", 0) / 120.0

        org_need = max(0.0, 1.0 - org.tier * 0.55)
        score = 0.25 + (visibility / 80.0) + (reliability / 60.0) + momentum + rel_bias + org_need * 0.15
        if hasattr(self.game, "reputation_system"):
            city = self.game.player.current_location.name if getattr(self.game, "player", None) and self.game.player.current_location else None
            rep = self.game.reputation_system.bias_for(artist_id, location=city, organization_id=organization_id)
            score += rep.get("negotiation", 0.0) * 0.12
            score += rep.get("trust", 0.0) * 0.08
            score -= rep.get("scrutiny", 0.0) * 0.08
        return max(0.05, min(0.95, score))

    def propose_terms(self, leverage: float, organization_tier: float, contact_flex_bias: float = 0.0) -> ContractTerms:
        leverage = max(0.05, min(0.95, leverage + contact_flex_bias))
        creative = max(0.1, min(0.9, 0.2 + leverage * 0.7 - organization_tier * 0.2))
        output = 3 if leverage < 0.25 else 2 if leverage < 0.55 else 1
        appearances = 3 if leverage < 0.3 else 2 if leverage < 0.6 else 1
        exclusivity = max(0.2, min(1.0, 0.85 - leverage * 0.6 + organization_tier * 0.15))
        strictness = max(0.2, min(0.95, 0.75 - leverage * 0.35 + organization_tier * 0.25))
        advance = "small" if leverage < 0.35 else "modest" if leverage < 0.7 else "strong"
        return ContractTerms(
            creative_control=creative,
            output_expectation=output,
            appearance_expectation=appearances,
            exclusivity=exclusivity,
            advance_style=advance,
            review_strictness=strictness,
        )

    def sign_contract(
        self,
        organization_id: str,
        artist_id: str,
        contact_npc_id: Optional[str] = None,
        duration_days: int = 180,
        terms: Optional[ContractTerms] = None,
    ) -> ArtistContract:
        org = self.organizations[organization_id]
        leverage = self.compute_leverage(artist_id, organization_id, contact_npc_id=contact_npc_id)
        contact_bias = self._contact_bias(contact_npc_id)
        selected_terms = terms or self.propose_terms(leverage, org.tier, contact_flex_bias=contact_bias)
        if hasattr(self.game, "reputation_system"):
            rep = self.game.reputation_system.bias_for(artist_id, location=org.home_city, organization_id=organization_id)
            selected_terms.review_strictness = max(0.1, min(0.98, selected_terms.review_strictness + rep.get("scrutiny", 0.0) * 0.07 - rep.get("trust", 0.0) * 0.05))
            selected_terms.creative_control = max(0.1, min(0.95, selected_terms.creative_control + rep.get("negotiation", 0.0) * 0.06))
            selected_terms.exclusivity = max(0.1, min(1.0, selected_terms.exclusivity - rep.get("trust", 0.0) * 0.05 + rep.get("scrutiny", 0.0) * 0.04))

        contract = ArtistContract(
            contract_id=f"contract_{uuid.uuid4().hex[:10]}",
            organization_id=organization_id,
            artist_id=artist_id,
            start_time=current_game_time.copy(),
            duration_days=duration_days,
            active=True,
            terms=selected_terms,
            leverage_snapshot=leverage,
            contact_npc_id=contact_npc_id,
        )
        self.contracts[contract.contract_id] = contract
        if artist_id not in org.artist_ids:
            org.artist_ids.append(artist_id)

        self._record_contract_memory(contract, "contract_signed", {"organization": org.name})
        return contract

    def active_contracts_for(self, artist_id: str) -> List[ArtistContract]:
        return [c for c in self.contracts.values() if c.artist_id == artist_id and c.active]

    def tick(self, minutes: int):
        if minutes <= 0:
            return
        self._generate_player_contract_pressure()
        self._simulate_npc_contract_pressure()

    def _generate_player_contract_pressure(self):
        player_id = getattr(self.game.player, "name", None)
        if not player_id:
            return
        flow = getattr(self.game, "life_flow", None)

        for contract in self.active_contracts_for(player_id):
            today = current_game_time.day + (current_game_time.month * 30)
            if contract.last_pressure_day == today:
                continue
            contract.last_pressure_day = today

            org = self.organizations.get(contract.organization_id)
            if not org:
                continue

            # Generate lightweight pressure items from terms
            for idx in range(contract.terms.output_expectation):
                due = current_game_time.copy()
                days_ahead = 5 + (idx * 2)
                if flow:
                    days_ahead = flow.modulate_days_ahead(days_ahead, source="contract", major=True)
                due.add_days(days_ahead)
                self.game.player.schedule.add_event(
                    due,
                    due,
                    f"{org.name} release milestone",
                    "Label Visit",
                    {
                        "requires_presence": True,
                        "location_name": org.home_city or (self.game.player.current_location.name if self.game.player.current_location else None),
                        "organization_id": org.organization_id,
                        "contract_id": contract.contract_id,
                        "pressure_item": "output",
                    },
                )
                if flow:
                    flow.record_pressure("contract", 1.2)

            for idx in range(contract.terms.appearance_expectation):
                due = current_game_time.copy()
                days_ahead = 3 + idx
                if flow:
                    days_ahead = flow.modulate_days_ahead(days_ahead, source="appearance", major=False)
                due.add_days(days_ahead)
                self.game.player.schedule.add_event(
                    due,
                    due,
                    f"{org.name} media appearance",
                    "Meeting",
                    {
                        "requires_presence": True,
                        "location_name": org.home_city or (self.game.player.current_location.name if self.game.player.current_location else None),
                        "organization_id": org.organization_id,
                        "contract_id": contract.contract_id,
                        "pressure_item": "appearance",
                    },
                )
                if flow:
                    flow.record_pressure("appearance", 0.8)
            # Contract pressure pushes against real creative work when present.
            if hasattr(self.game, "production_pipeline"):
                for project in self.game.production_pipeline.projects.values():
                    if project.lead_artist_id == player_id and project.status == "active":
                        strictness = contract.terms.review_strictness
                        if flow:
                            strictness *= flow.effective_pressure_multiplier()
                        self.game.production_pipeline.apply_contract_deadline_pressure(
                            project.project_id, strictness
                        )
                        break
            self._record_contract_memory(contract, "contract_pressure_generated", {"org": org.name})

    def record_contract_outcome(self, contract_id: str, outcome: str):
        contract = self.contracts.get(contract_id)
        if not contract or not contract.active:
            return

        if outcome == "success":
            contract.standing = min(10.0, contract.standing + 1.25)
            contract.misses = max(0, contract.misses - 1)
            self._record_contract_memory(contract, "contract_milestone_hit", {})
            return

        if outcome == "miss":
            contract.standing -= 1.6
            contract.misses += 1
            self._record_contract_memory(contract, "contract_missed_expectation", {})
            self._review_contract_state(contract)

    def _review_contract_state(self, contract: ArtistContract):
        bias = self._contact_bias(contract.contact_npc_id)
        strictness = contract.terms.review_strictness - bias

        if contract.misses >= 2 and strictness > 0.35 and contract.warnings == 0:
            contract.warnings += 1
            self._record_contract_memory(contract, "contract_warning", {"warnings": contract.warnings})
            return

        if contract.misses >= 3 and strictness > 0.5:
            if bias > 0.2:
                contract.warnings += 1
                self._record_contract_memory(contract, "contract_second_chance", {"warnings": contract.warnings})
            else:
                contract.active = False
                self._record_contract_memory(contract, "contract_dropped", {})

    def _simulate_npc_contract_pressure(self):
        if not hasattr(self.game, "NPC_REGISTRY"):
            return
        for contract in self.contracts.values():
            if not contract.active or contract.artist_id == getattr(self.game.player, "name", None):
                continue
            npc = self.game.NPC_REGISTRY.get(contract.artist_id)
            if not npc:
                continue
            # Lightweight world pressure: lower-momentum artists miss more under strict terms.
            momentum = getattr(npc, "momentum", 0.0)
            miss_chance = max(0.08, min(0.75, 0.35 + contract.terms.review_strictness * 0.35 - momentum * 0.05))
            if random.random() < miss_chance:
                self.record_contract_outcome(contract.contract_id, "miss")
            else:
                self.record_contract_outcome(contract.contract_id, "success")

    def _contact_bias(self, contact_npc_id: Optional[str]) -> float:
        if not contact_npc_id or not hasattr(self.game, "NPC_REGISTRY"):
            return 0.0
        npc = self.game.NPC_REGISTRY.get(contact_npc_id)
        if not npc:
            return 0.0
        return max(-0.25, min(0.25, getattr(npc, "relationship_score", 0) / 200.0))

    def _record_contract_memory(self, contract: ArtistContract, event_type: str, metadata: Dict):
        if not hasattr(self.game, "world_memory"):
            return
        self.game.world_memory.add(
            WorldMemoryEntry(
                event_type=event_type,
                involved_entities=[contract.artist_id],
                location=self.organizations.get(contract.organization_id).home_city if self.organizations.get(contract.organization_id) else None,
                timestamp=current_game_time.copy(),
                tags=["organization", "contract"],
                impact_score=1.8,
                metadata={"contract_id": contract.contract_id, "organization_id": contract.organization_id, **metadata},
                source_key=f"{event_type}:{contract.contract_id}:{current_game_time.get_time_string_for_schedule()}",
            )
        )
