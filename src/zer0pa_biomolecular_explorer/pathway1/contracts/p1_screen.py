"""P1.Screen contract — in silico screening.

Inputs: candidate library + target panel.
Outputs: ranked hits with predicted_pIC50, ADMET panel, selectivity, SA score.
Replaceable adapters: Boltz-2 (MIT; runpod_gpu) for affinity, GNINA (Apache 2.0; runpod_gpu)
for pose, Chemprop v2 (MIT; runpod_gpu) for ADMET, ASKCOS (MIT) for synthesizability,
RDKit (BSD) for pre-filter and SA score, local stub.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class P1ScreenInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    structure_ref: str
    pocket_id: str
    candidates: list[dict]  # {"candidate_id": str, "smiles": str, ...}
    target_panel_genes: list[str] = Field(
        default_factory=list,
        description="Off-target panel for selectivity screening (e.g., other cardiac channels).",
    )
    pic50_threshold: float = Field(default=7.0, ge=4.0, le=12.0)


class P1ADMETPanel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    logP: float
    tpsa: float = Field(ge=0.0)
    BBB_penetration_prob: float = Field(ge=0.0, le=1.0)
    hERG_IC50_uM: float = Field(ge=0.0)
    hepatotox_flag: bool
    oral_bioavailability_prob: float = Field(default=0.5, ge=0.0, le=1.0)
    esol_logs: float = Field(default=-3.0)
    lipinski_violations: int = Field(default=0, ge=0, le=4)


class P1ScreenedHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hit_id: str
    target_id: str
    smiles: str
    predicted_pIC50: float = Field(ge=4.0, le=12.0)
    affinity_source: str  # e.g., "Boltz-2_stub"
    admet_panel: P1ADMETPanel
    selectivity_score: float = Field(ge=0.0, le=1.0)
    synthetic_accessibility: float = Field(ge=1.0, le=10.0)
    pains_flags: list[str] = Field(default_factory=list)
    aggregator_flag: bool = False
    off_target_prediction_count: int = Field(ge=0)
    confidence_tier: str = Field(pattern=r"^[ABC]$")


class P1ScreenOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    n_input_candidates: int
    n_hits: int
    hits: list[P1ScreenedHit]
