"""Pydantic models for the ReasonerTuple — PRD section 8 canonical schema.

Schema version: reasoner_tuple.v1
Research boundary enforced on input/output text fields via validators.
All models use ConfigDict(extra="forbid") per architecture invariant.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from zer0pa_biomolecular_explorer.boundary import RESEARCH_BOUNDARY, boundary_violations


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class TaskType(str, Enum):
    EVIDENCE_PACKET = "evidence_packet"
    MECHANISM_BRIDGE = "mechanism_bridge"
    FALSIFIER_GENERATION = "falsifier_generation"
    CONFLICT_RESOLUTION = "conflict_resolution"
    AUDIT_SUMMARY = "audit_summary"
    ROUTE_SELECTION = "route_selection"


class ReasonerFalsifierClass(str, Enum):
    SOURCE_CONFLICT = "source_conflict"
    MULTI_CURRENT_OVERREACH = "multi_current_overreach"
    PHENOTYPE_MISMATCH = "phenotype_mismatch"
    AUDIT_GAP = "audit_gap"
    CLINICAL_OVERCLAIM = "clinical_overclaim"
    ADAPTER_REGRESSION = "adapter_regression"


class ReasonerFalsifierStatus(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class GroundTruthStatus(str, Enum):
    AVAILABLE = "available"
    PENDING = "pending"
    NOT_AVAILABLE = "not_available"
    NOT_APPLICABLE = "not_applicable"


class GroundTruthType(str, Enum):
    SOURCE_ANCHOR = "source_anchor"
    CURATED_LITERATURE = "curated_literature"
    LOCAL_BENCHMARK = "local_benchmark"
    HUMAN_ADJUDICATION = "human_adjudication"
    SIMULATION_GOLDEN = "simulation_golden"


# PRD-mandated authority order (canonical list)
AUTHORITY_ORDER: list[str] = [
    "source_anchor",
    "curated_literature",
    "local_benchmark",
    "simulation",
    "kg_inference",
    "model_output",
]

# PRD-mandated forbidden outputs
FORBIDDEN_OUTPUTS: list[str] = [
    "diagnosis",
    "treatment",
    "prescribing",
    "clinical_certification",
    "regulatory_compliance_claim",
]

# PRD-mandated required caveats
REQUIRED_CAVEATS: list[str] = [
    "research_only",
    "multi_current_context",
    "falsifier_required",
]


# ---------------------------------------------------------------------------
# Sub-models: Entities
# ---------------------------------------------------------------------------


class TupleEntities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    compounds: list[str] = Field(default_factory=list)
    genes: list[str] = Field(default_factory=list)
    currents: list[str] = Field(default_factory=list)
    phenotypes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Sub-models: Constraints
# ---------------------------------------------------------------------------


class TupleConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authority_order: list[str] = Field(default_factory=lambda: list(AUTHORITY_ORDER))
    forbidden_outputs: list[str] = Field(default_factory=lambda: list(FORBIDDEN_OUTPUTS))
    required_caveats: list[str] = Field(default_factory=lambda: list(REQUIRED_CAVEATS))

    @field_validator("authority_order")
    @classmethod
    def _check_authority_order(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("authority_order must not be empty")
        return v

    @field_validator("forbidden_outputs")
    @classmethod
    def _check_forbidden_outputs(cls, v: list[str]) -> list[str]:
        required = set(FORBIDDEN_OUTPUTS)
        missing = required - set(v)
        if missing:
            raise ValueError(
                f"forbidden_outputs missing PRD-mandated entries: {sorted(missing)}"
            )
        return v

    @field_validator("required_caveats")
    @classmethod
    def _check_required_caveats(cls, v: list[str]) -> list[str]:
        required = set(REQUIRED_CAVEATS)
        missing = required - set(v)
        if missing:
            raise ValueError(
                f"required_caveats missing PRD-mandated entries: {sorted(missing)}"
            )
        return v


# ---------------------------------------------------------------------------
# Sub-models: Input block
# ---------------------------------------------------------------------------


class ReasonerInput(BaseModel):
    """The input block of a ReasonerTuple — also used as the adapter's propose() argument."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1)
    entities: TupleEntities = Field(default_factory=TupleEntities)
    context_pack_refs: list[str] = Field(default_factory=list)
    constraints: TupleConstraints = Field(default_factory=TupleConstraints)

    @field_validator("question")
    @classmethod
    def _no_boundary_violations(cls, v: str) -> str:
        violations = boundary_violations(v)
        if violations:
            raise ValueError(
                f"question contains clinical-overclaim phrases: {violations}"
            )
        return v


# ---------------------------------------------------------------------------
# Sub-models: Claim / Abstention / KG edge / Next action
# ---------------------------------------------------------------------------


class TupleClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_refs: list[str] = Field(default_factory=list)
    falsifier_ref: str  # mandatory — every claim must reference a falsifier
    multi_current_context: bool = False

    @field_validator("text")
    @classmethod
    def _no_boundary_violations(cls, v: str) -> str:
        violations = boundary_violations(v)
        if violations:
            raise ValueError(
                f"claim text contains clinical-overclaim phrases: {violations}"
            )
        return v

    @field_validator("falsifier_ref")
    @classmethod
    def _falsifier_ref_required(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("falsifier_ref is required on every claim (missing_falsifier_ref guard)")
        return v


class TupleAbstention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity: str
    reason: str
    evidence_gap: str = ""


class KGEdgeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str
    predicate: str
    object: str  # noqa: A003
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    source_ref: str = ""
    claim_ref: str = ""


class NextAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    reason: str
    priority: str = "normal"  # high | normal | low


# ---------------------------------------------------------------------------
# Sub-models: Output block
# ---------------------------------------------------------------------------


class ReasonerOutput(BaseModel):
    """The output block of a ReasonerTuple — also returned by adapter.propose()."""

    model_config = ConfigDict(extra="forbid")

    claims: list[TupleClaim] = Field(default_factory=list)
    abstentions: list[TupleAbstention] = Field(default_factory=list)
    kg_edge_proposals: list[KGEdgeProposal] = Field(default_factory=list)
    next_actions: list[NextAction] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Sub-models: Falsifier block
# ---------------------------------------------------------------------------


class TupleFalsifier(BaseModel):
    model_config = ConfigDict(extra="forbid")

    falsifier_id: str
    falsifier_class: ReasonerFalsifierClass = Field(alias="class")
    trigger_condition: str
    status: ReasonerFalsifierStatus

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("falsifier_id")
    @classmethod
    def _id_required(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("falsifier_id must not be empty")
        return v

    @field_validator("trigger_condition")
    @classmethod
    def _condition_required(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("trigger_condition must not be empty")
        return v


# ---------------------------------------------------------------------------
# Sub-models: Ground truth block
# ---------------------------------------------------------------------------


class TupleGroundTruth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: GroundTruthStatus
    type: GroundTruthType | None = None  # noqa: A003
    source_refs: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Sub-models: Audit block
# ---------------------------------------------------------------------------


class TupleAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_hash: str
    context_hash: str
    output_hash: str
    license_flags: list[str] = Field(default_factory=list)

    @field_validator("prompt_hash", "context_hash", "output_hash")
    @classmethod
    def _hash_format(cls, v: str) -> str:
        if not v.startswith("sha256:"):
            raise ValueError(f"hash must start with 'sha256:' — got {v!r}")
        return v


# ---------------------------------------------------------------------------
# Top-level ReasonerTuple
# ---------------------------------------------------------------------------


class ReasonerTuple(BaseModel):
    """Canonical reasoner tuple — PRD section 8.

    Every interaction with a ReasonerAdapter produces one of these.
    Append to the queue via ReasonerQueue; never mutate after enqueue.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tuple_id: str
    schema_version: Literal["reasoner_tuple.v1"] = "reasoner_tuple.v1"
    created_at_utc: str  # ISO-8601
    run_id: str
    task_type: TaskType
    input: ReasonerInput  # noqa: A003
    output: ReasonerOutput
    falsifier: TupleFalsifier
    ground_truth: TupleGroundTruth
    audit: TupleAudit

    @field_validator("tuple_id")
    @classmethod
    def _tuple_id_format(cls, v: str) -> str:
        if not v.startswith("tuple:"):
            raise ValueError(f"tuple_id must start with 'tuple:' — got {v!r}")
        return v

    @field_validator("run_id")
    @classmethod
    def _run_id_format(cls, v: str) -> str:
        if not v.startswith("run:"):
            raise ValueError(f"run_id must start with 'run:' — got {v!r}")
        return v

    @field_validator("created_at_utc")
    @classmethod
    def _created_at_format(cls, v: str) -> str:
        if not v:
            raise ValueError("created_at_utc must not be empty")
        return v
