"""Audit record schemas — one per audit table (PRD section 6, 12 tables).

Every record carries:
  - schema_version
  - created_at_utc (ISO-8601)
  - research_boundary (canonical)
  - record_hash, prev_record_hash (sha256, hex-prefixed)

These five fields form the hash chain. The validator rejects any record missing them.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from zer0pa_health.boundary import RESEARCH_BOUNDARY, assert_boundary_string


class _AuditBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="v1")
    created_at_utc: str
    research_boundary: str = RESEARCH_BOUNDARY
    record_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    prev_record_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("research_boundary")
    @classmethod
    def _check_boundary(cls, v: str) -> str:
        assert_boundary_string(v)
        return v


class RunRecord(_AuditBase):
    table: Literal["runs"] = "runs"
    run_id: str
    git_commit: str | None = None
    executor_identity: str
    environment: dict[str, str] = Field(default_factory=dict)


class MoleculeRecord(_AuditBase):
    table: Literal["molecules"] = "molecules"
    run_id: str
    molecule_id: str
    inchikey: str | None = None
    canonical_smiles: str | None = None
    name: str | None = None
    source_manifest_refs: list[str] = Field(default_factory=list)


class ModelToolRecord(_AuditBase):
    table: Literal["model_tools"] = "model_tools"
    run_id: str
    layer: str
    adapter_id: str
    tool_name: str
    tool_version: str
    backend: str
    license_class: str  # A | B | C | D | E
    license_flags: list[str] = Field(default_factory=list)


class SourceManifestRecord(_AuditBase):
    table: Literal["source_manifest"] = "source_manifest"
    run_id: str
    source_manifest_id: str
    locator: str  # URL or local manifest path; never raw bulk data
    retrieval_timestamp_utc: str | None = None
    content_hash: str | None = None
    license_class: str
    source_class: str  # regulatory_science | peer_reviewed | public_dataset_metadata | local_proof | inference
    summary: str = Field(max_length=2000)


class ParametersRecord(_AuditBase):
    table: Literal["parameters"] = "parameters"
    run_id: str
    layer: str
    adapter_id: str
    parameters: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ConfidenceRecord(_AuditBase):
    table: Literal["confidence"] = "confidence"
    run_id: str
    envelope_id: str
    layer: str
    score: float = Field(ge=0.0, le=1.0)
    band: str
    decomposition: dict[str, float] = Field(default_factory=dict)
    calibration_basis: list[str] = Field(default_factory=list)


class FalsifierRecord(_AuditBase):
    table: Literal["falsifiers"] = "falsifiers"
    run_id: str
    falsifier_id: str
    falsifier_class: str
    layer_scope: list[str]
    trigger_condition: str
    status: str  # pass|fail|blocked|inconclusive
    evidence: list[str] = Field(default_factory=list)
    backedge_proposed_target: str | None = None


class DecisionRecord(_AuditBase):
    table: Literal["decisions"] = "decisions"
    run_id: str
    decision_id: str
    actor: str  # "lead_agent" | "L6_router" | "human_operator" | adapter_id
    decision_kind: str  # promote|downgrade|reroute|block|backedge|hold|exec
    rationale: str
    triggered_by: list[str] = Field(default_factory=list)
    supersedes: str | None = None


class ArtifactRecord(_AuditBase):
    table: Literal["artifacts"] = "artifacts"
    run_id: str
    artifact_id: str
    path: str
    size_bytes: int = Field(ge=0)
    content_hash: str
    offload_ref: str | None = None  # private HF dataset locator if offloaded


class ReplayCommandRecord(_AuditBase):
    table: Literal["replay_commands"] = "replay_commands"
    run_id: str
    layer: str
    command: str
    deterministic: bool
    notes: str = ""


class OffloadManifestRecord(_AuditBase):
    table: Literal["offload_manifest"] = "offload_manifest"
    run_id: str
    artifact_id: str
    hf_dataset_ref: str  # e.g., "Architect-Prime/zer0pa-health-cardiac-v0:files/abc.json"
    size_bytes: int = Field(ge=0)
    contains_phi: Literal[False] = False
    contains_secrets: Literal[False] = False


class MIDDAssessmentRecord(_AuditBase):
    """Model-Informed Drug Development assessment shape (research only)."""

    table: Literal["midd_assessments"] = "midd_assessments"
    run_id: str
    assessment_id: str
    model_kind: str
    qualification_basis: list[str]
    decision_context: str
    boundary_check: Literal["passed_research_boundary"] = "passed_research_boundary"
