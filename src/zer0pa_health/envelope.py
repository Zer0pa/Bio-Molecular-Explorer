"""Universal Layer Envelope (PRD section 2 — Architecture Invariant).

Every layer in L1, L2, L2.5, L3, L4, L5, L6 must emit an envelope of this shape.
Cross-layer code depends ONLY on this envelope plus the per-layer contract for
`output`. Tool implementations (RDKit, OpenFE, PharmaPy, etc.) live behind
adapters and never leak into the envelope contract.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from zer0pa_health.boundary import RESEARCH_BOUNDARY, assert_boundary_string


CONTRACT_VERSION: Literal["zer0pa.layer-envelope.v1"] = "zer0pa.layer-envelope.v1"


class LayerName(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L2_5 = "L2.5"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"
    # Pathway 1 — R&D / Drug Discovery front-end (PATHWAY1_PRD.md §2)
    P1_TARGET = "P1.Target"
    P1_STRUCTURE = "P1.Structure"
    P1_GENERATE = "P1.Generate"
    P1_SCREEN = "P1.Screen"
    P1_OPTIMIZE = "P1.Optimize"
    P1_HANDOFF = "P1.Handoff"


class Backend(str, Enum):
    STUB = "stub"
    CPU_LITE = "cpu_lite"
    RUNPOD_GPU = "runpod_gpu"
    EXTERNAL_API = "external_api"  # Pathway 1: Open Targets, TTD, GPT-Rosalind, ChEMBL, ZINC-22, etc.


class ConfidenceBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FalsifierStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    INCONCLUSIVE = "inconclusive"


class ToolAdapter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    backend: Backend
    engine: str  # specific tool/model name (e.g., "rdkit", "openfe", "boltz-2")


class EnvelopeConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0.0, le=1.0)
    band: ConfidenceBand
    basis: list[str] = Field(
        default_factory=list,
        description="Free-form list of basis points (e.g., 'docking_score=0.71', 'fep_uncertainty=0.4_kcal_mol').",
    )


class EnvelopeFalsifierItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    falsifier_id: str
    falsifier_class: str  # e.g., "hERG_only_overreach", "stub_laundering"
    trigger_condition: str
    status: FalsifierStatus
    evidence: list[str] = Field(default_factory=list)


class EnvelopeFalsifier(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: FalsifierStatus
    items: list[EnvelopeFalsifierItem] = Field(default_factory=list)


class EnvelopeAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_record_id: str
    input_hash: str
    output_hash: str
    source_manifest_refs: list[str] = Field(default_factory=list)


class BackEdge(BaseModel):
    """A back-edge: an upstream layer is asked to revise based on this layer's findings.

    Examples:
      L2.5 unsynthesizable -> L2.feedback (penalize this scaffold)
      L4 unmanufacturable -> L2.5.feedback (avoid this route)
      L5 channel-overreach -> L1.feedback (request multi-current panel)
    """

    model_config = ConfigDict(extra="forbid")

    target_layer: LayerName
    reason: str
    proposed_constraint: dict[str, Any] = Field(default_factory=dict)
    triggered_by_falsifier_id: str | None = None


class LayerEnvelope(BaseModel):
    """The PRD section 2 universal envelope.

    NB: `output` is intentionally `dict[str, Any]` here — per-layer contracts
    in `zer0pa_health.contracts.*` constrain what goes inside via Pydantic
    validators on the layer-specific subclasses.
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    contract_version: Literal["zer0pa.layer-envelope.v1"] = CONTRACT_VERSION
    research_boundary: str = RESEARCH_BOUNDARY
    run_id: str
    layer: LayerName
    tool_adapter: ToolAdapter
    input_refs: list[str] = Field(default_factory=list)
    output: dict[str, Any] = Field(default_factory=dict)
    confidence: EnvelopeConfidence
    falsifier: EnvelopeFalsifier
    audit: EnvelopeAudit
    back_edges: list[BackEdge] = Field(default_factory=list)

    @field_validator("research_boundary")
    @classmethod
    def _check_boundary(cls, v: str) -> str:
        assert_boundary_string(v)
        return v

    def dump_json(self) -> str:
        return self.model_dump_json(by_alias=False, exclude_none=False)
