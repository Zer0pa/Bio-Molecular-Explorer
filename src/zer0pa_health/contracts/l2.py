"""L2 — Property / formulation contracts.

Inputs: standardized molecule, descriptors, L2.5 feedback.
Outputs: property scores, liability flags, reward modifiers.
Replaceable tools: RDKit, DeepChem, DeepXDE, REINVENT scorer, stubs.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class L2MoleculeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    smiles: str
    canonical_smiles: str | None = None
    inchikey: str | None = None


class L2RetrosynthFeedback(BaseModel):
    """Back-edge from L2.5 into L2 scoring (Inversion A: back-edges before forward passes)."""

    model_config = ConfigDict(extra="forbid")

    smiles: str
    route_score: float = Field(ge=0.0, le=1.0)
    route_depth: int = Field(ge=0)
    sa_score: float | None = Field(default=None, ge=1.0, le=10.0)
    starting_material_cost_usd: float | None = Field(default=None, ge=0.0)
    routes_found: bool


class L2PropertyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    molecule: L2MoleculeInput
    retrosynth_feedback: L2RetrosynthFeedback | None = None


class L2LiabilityFlag(str):
    HERG_LIABILITY = "hERG_liability"
    PAINS = "PAINS"
    LIPINSKI_VIOLATION = "lipinski_violation"
    REACTIVE_GROUP = "reactive_group"
    POOR_PERMEABILITY = "poor_permeability"
    HIGH_CLEARANCE = "high_clearance"


class L2PropertyOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    smiles: str
    canonical_smiles: str
    inchikey: str | None = None
    descriptors: dict[str, float] = Field(default_factory=dict)
    admet_scores: dict[str, float] = Field(
        default_factory=dict,
        description="e.g., {'logP': 2.4, 'tpsa': 75.3, 'hia_prob': 0.91}",
    )
    liability_flags: list[str] = Field(default_factory=list)
    reward_modifier: float = Field(
        ge=-1.0, le=1.0,
        description="Net REINVENT-style reward modifier from L2 (incl. L2.5 feedback if present).",
    )
    valid_smiles: bool


class L2DissolutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    molecule: L2MoleculeInput
    formulation: Literal["IR_tablet", "ER_tablet", "capsule", "solution", "suspension"] = "IR_tablet"
    dose_mg: float = Field(gt=0.0)


class L2DissolutionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    smiles: str
    formulation: str
    dose_mg: float
    pinn_basis: Literal["DeepXDE_stub", "DeepXDE_cpu", "deferred_runpod"] = "DeepXDE_stub"
    fraction_dissolved_at_30min: float = Field(ge=0.0, le=1.0)
    fraction_dissolved_at_60min: float = Field(ge=0.0, le=1.0)
    fraction_dissolved_at_120min: float = Field(ge=0.0, le=1.0)
