"""L1 — Molecular simulation contracts.

Inputs: SMILES/InChIKey, target manifests, mmCIF/PDB refs, channel panel.
Outputs: standardized ligand, pose, binding estimate, MD/FEP result, channel panel hypothesis.
Replaceable tools: RDKit, DiffDock V2, Boltz-2, Protenix, OpenMM, OpenFE, stubs.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class L1ChannelGene(str, Enum):
    KCNH2 = "KCNH2"
    SCN5A = "SCN5A"
    KCNQ1 = "KCNQ1"
    CACNA1C = "CACNA1C"
    KCNE1 = "KCNE1"
    KCNE2 = "KCNE2"
    KCNJ2 = "KCNJ2"
    HCN4 = "HCN4"
    RYR2 = "RYR2"


class L1IonCurrent(str, Enum):
    IKr = "IKr"
    IKs = "IKs"
    INa = "INa"
    INaL = "INaL"
    ICaL = "ICaL"
    IK1 = "IK1"
    If = "If"


class L1MoleculeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    smiles: str
    inchikey: str | None = None
    name: str | None = None
    source_manifest_refs: list[str] = Field(default_factory=list)


class L1TargetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gene: L1ChannelGene
    current: L1IonCurrent
    structure_ref: str | None = Field(
        default=None, description="mmCIF/PDB locator (URL, PDB ID, or local manifest ref)."
    )


class L1ChannelPanelInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    targets: list[L1TargetInput]


class L1DockingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    molecule: L1MoleculeInput
    target: L1TargetInput
    n_poses: int = Field(default=10, ge=1, le=200)


class L1Pose(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pose_index: int
    confidence: float = Field(ge=0.0, le=1.0)
    estimated_binding_kcal_mol: float | None = None
    structure_basis: Literal["mmCIF", "PDB", "stub"] = "stub"


class L1DockingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    molecule_inchikey: str
    target_gene: L1ChannelGene
    target_current: L1IonCurrent
    poses: list[L1Pose]
    structure_confidence: float = Field(ge=0.0, le=1.0)
    binding_confidence: float = Field(ge=0.0, le=1.0)


class L1MDInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    molecule: L1MoleculeInput
    target: L1TargetInput
    pose_index: int
    sim_ns: float = Field(default=10.0, gt=0.0)


class L1MDOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    molecule_inchikey: str
    target_gene: L1ChannelGene
    rmsd_nm: float = Field(ge=0.0)
    convergence_metric: float = Field(ge=0.0, le=1.0)
    n_frames: int = Field(ge=0)


class L1FEPInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ligand_a: L1MoleculeInput
    ligand_b: L1MoleculeInput
    target: L1TargetInput
    method: Literal["RBFE", "ABFE"] = "RBFE"


class L1FEPOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ddg_kcal_mol: float
    ddg_uncertainty_kcal_mol: float = Field(ge=0.0)
    convergence_ok: bool
    method: Literal["RBFE", "ABFE"]


class L1ChannelPanelHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    molecule_inchikey: str
    panel: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "gene -> {'ic50_uM': float|None, 'block_fraction_at_cmax_unbound': float|None, "
            "'method': str, 'confidence': float, 'source_refs': list[str], "
            "'explicit_absence': str|None}. The widening to Any preserves panel provenance "
            "(method, source_refs, explicit_absence flag) end-to-end so the cardiac packet "
            "assembler can source these from the L1 envelope rather than the fixture."
        ),
    )
    multi_current_balance_score: float | None = Field(
        default=None, ge=-1.0, le=1.0,
        description=(
            "Net repolarization balance: HIGHER = more outward-current block relative to "
            "inward-current block = greater APD-prolongation tendency in research-only "
            "multi-current models. RESEARCH INDICATOR ONLY — no clinical or safety claim "
            "implied in any direction. See L5 cardiac_bridge.py for canonical formula."
        ),
    )
