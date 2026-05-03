"""P1.Optimize contract — hit-to-lead refinement.

Inputs: ranked hits + target product profile (TPP).
Outputs: optimized leads with iteration_number, confidence_tier.
Replaceable adapters: REINVENT 4 RL (Apache 2.0), BoTorch + Ax (MIT; CPU), Chemprop v2 oracle
(runpod_gpu), Boltz-2 oracle (runpod_gpu), ASKCOS (MIT). BoTorch is the multi-objective
Bayesian optimization layer.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class P1TargetProductProfile(BaseModel):
    """Multi-parameter optimization target."""

    model_config = ConfigDict(extra="forbid")

    target_pic50_min: float = Field(default=7.0, ge=4.0, le=12.0)
    qed_min: float = Field(default=0.6, ge=0.0, le=1.0)
    sa_score_max: float = Field(default=4.0, ge=1.0, le=10.0)
    herg_ic50_uM_min: float = Field(default=30.0, gt=0.0)
    esol_logs_min: float = Field(default=-4.0)


class P1OptimizeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    hits: list[dict]  # P1ScreenedHit dumps
    tpp: P1TargetProductProfile = Field(default_factory=P1TargetProductProfile)
    max_iterations: int = Field(default=50, ge=1, le=500)


class P1ASKCOSRouteStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_index: int
    rxn_smarts: str
    reagents: list[str] = Field(default_factory=list)


class P1OptimizedLead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_id: str
    target_id: str
    smiles: str
    predicted_pIC50: float
    admet_panel: dict  # P1ADMETPanel dump
    selectivity_score: float
    synthetic_accessibility: float
    askcos_route_steps: list[P1ASKCOSRouteStep] = Field(default_factory=list)
    estimated_synthesis_steps: int = Field(ge=0)
    iteration_number: int = Field(ge=0)
    parent_scaffold: str | None = None
    confidence_tier: str = Field(pattern=r"^[ABC]$")
    distinct_models_count: int = Field(
        ge=0, description="Number of independent scoring engines that ran on this lead."
    )
    generation_method: str = Field(
        default="unknown",
        description="Generation method carried through from P1.Generate (e.g., REINVENT4_RL, DiffSBDD).",
    )


class P1OptimizeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    n_input_hits: int
    n_leads: int
    iterations_used: int
    leads: list[P1OptimizedLead]
    tpp_used: P1TargetProductProfile
