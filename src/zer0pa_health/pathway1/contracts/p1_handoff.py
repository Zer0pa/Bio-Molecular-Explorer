"""P1.Handoff contract — CRO-ready candidate dossier.

Inputs: optimized leads.
Outputs: P1HandoffPacket (per-lead) — the final Pathway 1 deliverable. Bridges
into the existing cardiac wedge for cardiac targets via `l1_channel_panel_input`.
Replaceable adapters: handoff composer (CPU; RDKit pre-filter + ZINC-22 lookup).

Cardiac integration: when target_gene ∈ {KCNH2, SCN5A, KCNQ1, CACNA1C}, the
adapter populates `l1_channel_panel_input` to match the existing
`L1ChannelPanelInput` Pydantic schema exactly. Non-cardiac targets get
`l1_channel_panel_input = None` and are routed to a future general-target wedge.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from zer0pa_health.boundary import boundary_violations


_CARDIAC_GENES = {"KCNH2", "SCN5A", "KCNQ1", "CACNA1C"}


class P1HandoffInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    target_gene: str
    leads: list[dict]  # P1OptimizedLead dumps
    pathway1_run_id: str
    audit_refs: list[str] = Field(default_factory=list)
    cloud_lab_enabled: bool = False


class P1L1ChannelPanelTarget(BaseModel):
    """Pathway 1 → existing L1 cardiac panel bridge.

    Matches the field set of `contracts.l1.L1TargetInput` (gene + current).
    Stored as a plain dict in the packet so the existing L1 adapter consumes it
    without import gymnastics.
    """

    model_config = ConfigDict(extra="forbid")

    gene: str
    current: str
    structure_ref: str | None = None


class P1L1ChannelPanelInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    targets: list[P1L1ChannelPanelTarget]


class P1HandoffPacket(BaseModel):
    """The PRD section 6 dossier shape. v0.1."""

    model_config = ConfigDict(extra="forbid")

    research_boundary: str = (
        "Research use only. Not for diagnosis, treatment, cure claims, prescribing, "
        "clinical deployment, regulatory compliance, or drug-safety certification."
    )
    schema_version: str = "p1.handoff_packet.v0.1"
    pathway1_run_id: str
    candidate_id: str
    smiles: str
    target_id: str
    target_gene: str
    predicted_pIC50: float | None
    binding_affinity_source: str
    admet: dict
    selectivity_score: float | None
    synthetic_accessibility: float | None
    estimated_synthesis_steps: int | None
    suggested_route: str | None
    confidence_tier: Literal["A", "B", "C"]
    generation_method: str
    iteration_number: int
    parent_scaffold: str | None
    audit_refs: list[str] = Field(min_length=1)
    kg_node_refs: list[str] = Field(default_factory=list)
    source_manifest_refs: list[str] = Field(default_factory=list)
    l1_channel_panel_input: P1L1ChannelPanelInput | None = None
    pains_alert: bool = False
    structural_alert_flags: list[str] = Field(default_factory=list)
    zinc22_purchasable_analogue: str | None = None
    is_cardiac_target: bool = False
    verdict_at_handoff: Literal["pass", "hold", "blocked"]
    falsifier_refs: list[str] = Field(default_factory=list)
    distinct_models_count: int = Field(ge=0)
    stub_provenance_note: str = ""

    @field_validator("suggested_route", "stub_provenance_note")
    @classmethod
    def _no_overclaim(cls, v: str | None) -> str | None:
        if v is None:
            return None
        violations = boundary_violations(v)
        if violations:
            raise ValueError(
                f"clinical-overclaim phrase in handoff packet text field: {len(violations)} matches"
            )
        return v


class P1HandoffOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pathway1_run_id: str
    target_id: str
    n_packets: int
    packets: list[P1HandoffPacket]
    cloud_lab_dry_runs_attempted: int = 0
