"""KG schema (PRD section 6).

Node and edge types are explicit enums; nothing else may be used. Hard
constraints are enforced in `validator.py`.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class NodeType(str, Enum):
    COMPOUND = "Compound"
    GENE = "Gene"
    CHANNEL = "Channel"
    ION_CURRENT = "IonCurrent"
    PHENOTYPE_FEATURE = "PhenotypeFeature"
    ASSAY_MODEL = "AssayModel"
    DATASET_MANIFEST = "DatasetManifest"
    SOURCE_MANIFEST = "SourceManifest"
    EVIDENCE_ITEM = "EvidenceItem"
    CLAIM = "Claim"
    FALSIFIER = "Falsifier"
    LAYER = "Layer"
    TOOL_ADAPTER = "ToolAdapter"
    INTERFACE_CONTRACT = "InterfaceContract"
    OUTPUT_ENVELOPE = "OutputEnvelope"
    EVIDENCE_PACKET = "EvidencePacket"
    EPISODE = "Episode"
    REASONER_TUPLE = "ReasonerTuple"
    ACCEPTANCE_GATE = "AcceptanceGate"
    AUDIT_RECORD = "AuditRecord"
    # Pathway 1 — R&D / Drug Discovery extensions (PATHWAY1_PRD.md §2)
    TARGET = "Target"
    HIT = "Hit"
    LEAD = "Lead"
    GENERATIVE_PROPOSAL = "GenerativeProposal"
    DISEASE = "Disease"
    BINDING_POCKET = "BindingPocket"


class EdgeType(str, Enum):
    ENCODES = "ENCODES"
    MEDIATES_CURRENT = "MEDIATES_CURRENT"
    MODULATES = "MODULATES"
    AFFECTS_FEATURE = "AFFECTS_FEATURE"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    QUALIFIES = "QUALIFIES"
    HAS_SOURCE = "HAS_SOURCE"
    HAS_FALSIFIER = "HAS_FALSIFIER"
    GENERATED_BY = "GENERATED_BY"
    HAS_AUDIT = "HAS_AUDIT"
    CONSUMES_CONTRACT = "CONSUMES_CONTRACT"
    PRODUCES_CONTRACT = "PRODUCES_CONTRACT"
    MEMBER_OF_PACKET = "MEMBER_OF_PACKET"
    TRIGGERS_BACKEDGE = "TRIGGERS_BACKEDGE"
    DERIVES_TUPLE = "DERIVES_TUPLE"
    SUPERSEDES = "SUPERSEDES"
    # Pathway 1 extensions
    ENCODES_TARGET = "ENCODES_TARGET"
    HAS_DISEASE_ASSOCIATION = "HAS_DISEASE_ASSOCIATION"
    HAS_BINDING_POCKET = "HAS_BINDING_POCKET"


class ClaimStatus(str, Enum):
    PROPOSED = "proposed"
    SUPPORTED_FOR_RESEARCH = "supported_for_research"
    SUPPORTED_WITH_LIMIT = "supported_with_limit"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class KGNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    node_type: NodeType
    properties: dict[str, Any] = Field(default_factory=dict)
    research_boundary: str = "Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification."


class KGEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str
    edge_type: EdgeType
    source_node_id: str
    target_node_id: str
    properties: dict[str, Any] = Field(default_factory=dict)


# Hard KG constraints (PRD section 6).
HARD_KG_CONSTRAINTS: tuple[str, ...] = (
    "K1: A Claim may not be SUPPORTED_FOR_RESEARCH unless it has at least one EvidenceItem, "
    "one SourceManifest, one Falsifier, and one AuditRecord.",
    "K2: A mechanism edge may not be source-grounded if its only evidence is a codec/replay metric.",
    "K3: Any Claim touching QT, TdP, proarrhythmia, or cardiac safety MUST include multi-current "
    "framing or fail the hERG-only falsifier.",
    "K4: Every layer Output must exist as an OutputEnvelope node.",
    "K5: Episode nodes support resume and learning, but cannot serve as scientific evidence on their own.",
)
