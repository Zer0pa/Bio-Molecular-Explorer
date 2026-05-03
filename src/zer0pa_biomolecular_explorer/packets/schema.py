"""Cardiac evidence packet schema — PRD section 7.

The packet is the artifact shipped to a reviewer. Every field is research-only.
Boundary-violating language must be impossible by construction (Pydantic validators
+ explicit clinical-overclaim detector pass on assemble).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from zer0pa_biomolecular_explorer.boundary import RESEARCH_BOUNDARY, assert_boundary_string, boundary_violations


class PacketVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    BLOCKED = "blocked"


class PacketCompound(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    inchikey: str
    canonical_smiles: str
    research_label: str  # e.g., "Class III antiarrhythmic (research label; not a clinical recommendation)"
    cardiac_research_role: str  # e.g., "IKr-pure positive control"


class PacketChannelMember(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gene: str
    channel: str
    current: str
    ic50_uM: float | None = None
    block_fraction_at_cmax_unbound: float | None = None
    method: str  # "stub" | "boltz-2" | "openfe-rbfe" | etc.
    confidence: float = Field(ge=0.0, le=1.0)
    explicit_absence: str | None = None  # reason if no value provided


class PacketChannelPanel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    KCNH2_hERG_IKr: PacketChannelMember
    SCN5A_Nav1_5_INa_INaL: PacketChannelMember
    KCNQ1_Kv7_1_IKs: PacketChannelMember
    CACNA1C_CaV1_2_ICaL: PacketChannelMember


class PacketMorphologyBridge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cmax_unbound_uM: float | None = None
    multi_current_balance_score: float | None = None
    expected_morphology_signal: str  # research-only signal description
    morphology_gate_result: dict[str, Any] = Field(default_factory=dict)


class PacketClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    text: str  # research-only language; clinical-overclaim phrases auto-rejected
    multi_current_context: bool
    source_refs: list[str]  # source_manifest IDs
    falsifier_refs: list[str] = Field(min_length=1)
    audit_refs: list[str] = Field(min_length=1)
    confidence_band: str  # "low" | "medium" | "high"

    @field_validator("text")
    @classmethod
    def _no_overclaim(cls, v: str) -> str:
        violations = boundary_violations(v)
        if violations:
            raise ValueError(f"clinical-overclaim phrase in claim text: {violations[:3]}")
        return v


class PacketContradiction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contradiction_id: str
    description: str
    sources_in_conflict: list[str]
    resolution: str  # "open" | "downgraded" | "abstained"


class PacketEngineValueAdd(BaseModel):
    """What the packet provides that PubMed + competent reader does not (PRD section 7)."""

    model_config = ConfigDict(extra="forbid")

    rerunnable_source_manifest: bool
    machine_valid_graph: bool
    explicit_contradiction_table: bool
    falsifier_ledger_present: bool
    local_morphology_linkage: bool
    audit_trail_present: bool
    next_experiment_backedges: list[str] = Field(default_factory=list)


class CardiacEvidencePacket(BaseModel):
    """v0.1 — PRD section 7 schema."""

    model_config = ConfigDict(extra="forbid")

    packet_id: str
    research_boundary: str = RESEARCH_BOUNDARY
    schema_version: str = "cardiac_evidence_packet.v0.1"
    run_id: str
    compound: PacketCompound
    source_manifest_refs: list[str] = Field(default_factory=list)
    channel_panel: PacketChannelPanel
    multi_current_interpretation: str
    ecg_morphology_bridge: PacketMorphologyBridge
    claims: list[PacketClaim] = Field(min_length=1)
    contradictions: list[PacketContradiction] = Field(default_factory=list)
    falsifiers: list[dict[str, Any]] = Field(min_length=1)
    audit_refs: list[str] = Field(min_length=1)
    engine_value_add: PacketEngineValueAdd
    verdict: PacketVerdict

    @field_validator("research_boundary")
    @classmethod
    def _check_boundary(cls, v: str) -> str:
        assert_boundary_string(v)
        return v

    @field_validator("multi_current_interpretation")
    @classmethod
    def _no_overclaim_interp(cls, v: str) -> str:
        violations = boundary_violations(v)
        if violations:
            raise ValueError(
                f"clinical-overclaim phrase in multi_current_interpretation: {violations[:3]}"
            )
        return v
