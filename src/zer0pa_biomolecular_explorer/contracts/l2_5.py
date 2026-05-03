"""L2.5 — Retrosynthesis contracts.

Inputs: canonical SMILES, policy, buyability catalogs.
Outputs: RXNSMILES, atom-mapped route, route confidence, feasibility feedback.
Replaceable tools: AiZynthFinder, ASKCOS (USPTO/Pistachio only — Reaxys is CC BY-NC), Chemprop, Rxnmapper, stubs.

Note on Reaxys: ASKCOS Reaxys model is CC BY-NC 4.0; default to USPTO/Pistachio.
The license-drift falsifier triggers if `model_variant == "reaxys"` is requested without explicit governance.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class L25Policy(str, Enum):
    AIZYNTHFINDER_DEFAULT = "aizynthfinder_default"
    ASKCOS_USPTO = "askcos_uspto"
    ASKCOS_PISTACHIO = "askcos_pistachio"
    ASKCOS_REAXYS = "askcos_reaxys"  # license-flagged; non-commercial only
    STUB = "stub"


class L25Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_smiles: str
    policy: L25Policy = L25Policy.AIZYNTHFINDER_DEFAULT
    max_steps: int = Field(default=8, ge=1, le=20)
    excluded_reaction_types: list[str] = Field(default_factory=list)
    available_reagents: list[str] = Field(
        default_factory=list,
        description="InChIKey or canonical SMILES of starting materials available in stock.",
    )


class L25ReactionStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rxnsmiles: str  # reactants>reagents>products
    atom_mapped_rxnsmiles: str | None = None
    template_smarts: str | None = None
    predicted_yield: float | None = Field(default=None, ge=0.0, le=1.0)
    conditions: dict[str, str] = Field(default_factory=dict)
    step_confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("rxnsmiles")
    @classmethod
    def _check_rxn_arrows(cls, v: str) -> str:
        if ">>" not in v and v.count(">") < 2:
            raise ValueError(
                "rxnsmiles must contain '>>' (reactants>>products) or 'reactants>reagents>products'."
            )
        return v


class L25Route(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_canonical_smiles: str
    steps: list[L25ReactionStep]
    route_score: float = Field(ge=0.0, le=1.0)
    sa_score: float | None = Field(default=None, ge=1.0, le=10.0)
    total_steps: int = Field(ge=1)
    starting_materials_inchikeys: list[str] = Field(default_factory=list)
    starting_materials_cost_usd: float | None = Field(default=None, ge=0.0)


class L25Output(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_canonical_smiles: str
    routes: list[L25Route]
    routes_found: bool
    policy_used: L25Policy
    license_flag: str | None = Field(
        default=None,
        description="Set to 'CC-BY-NC' if Reaxys variant used without governance.",
    )
    feedback_to_l2: dict[str, float] = Field(
        default_factory=dict,
        description="Compact dict suitable for L2RetrosynthFeedback construction.",
    )
