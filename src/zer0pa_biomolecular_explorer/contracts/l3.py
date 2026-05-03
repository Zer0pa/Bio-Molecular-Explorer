"""L3 — Process contracts.

Inputs: route packet, material properties, conditions.
Outputs: process graph, mass balance, unit ops, CPP/CQA risks.
Replaceable tools: DWSIM, PharmaPy, OpenFOAM, LIGGGHTS, MFiX, stubs.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class L3UnitOpKind(str, Enum):
    REACTION = "reaction"
    CRYSTALLIZATION = "crystallization"
    FILTRATION = "filtration"
    DRYING = "drying"
    GRANULATION = "granulation"
    BLENDING = "blending"
    TABLET_COMPRESSION = "tablet_compression"
    DISTILLATION = "distillation"
    EXTRACTION = "extraction"
    CHROMATOGRAPHY = "chromatography"


class L3MaterialFlow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inchikey: str | None = None
    canonical_smiles: str | None = None
    role: str  # reactant | reagent | solvent | product | waste | impurity
    moles: float = Field(ge=0.0)
    mass_kg: float = Field(ge=0.0)


class L3UnitOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: L3UnitOpKind
    name: str
    inputs: list[L3MaterialFlow]
    outputs: list[L3MaterialFlow]
    parameters: dict[str, float] = Field(
        default_factory=dict,
        description="Temp, pressure, residence_time, throughput, etc.",
    )


class L3ProcessInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_canonical_smiles: str
    route_rxnsmiles: list[str]
    target_throughput_kg_per_batch: float = Field(default=1.0, gt=0.0)


class L3ProcessOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_canonical_smiles: str
    unit_ops: list[L3UnitOp]
    mass_balance_residual_kg: float = Field(
        ge=0.0,
        description="Sum of |inputs - outputs| in kg; should be ~0 within tolerance.",
    )
    mass_balance_ok: bool
    cpp_cqa_risks: list[str] = Field(default_factory=list)
    process_graph_dot: str | None = Field(
        default=None,
        description="Optional Graphviz DOT representation of the process graph.",
    )
