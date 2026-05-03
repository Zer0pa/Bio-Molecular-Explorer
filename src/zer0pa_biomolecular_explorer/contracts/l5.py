"""L5 — PKPD / QSP contracts.

Inputs: ADMET, formulation/process outputs, cardiac channel evidence.
Outputs: SBML/QSP packet, exposure-to-channel bridge, cardiac evidence inputs.
Replaceable tools: PK-Sim/MoBi, nlmixr2/RxODE, COPASI, Tellurium, stubs.

This is where COPASI and Tellurium correctly live (Brief #2 correction);
they were misclassified into L4 in Brief #1.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class L5PKModelKind(str, Enum):
    ONE_COMPARTMENT = "one_compartment"
    TWO_COMPARTMENT = "two_compartment"
    PBPK = "pbpk"
    POPULATION_PKPD = "population_pkpd"


class L5SBMLPacket(BaseModel):
    """A minimal SBML-compatible representation; full SBML XML is referenced by hash if used."""

    model_config = ConfigDict(extra="forbid")

    sbml_version: str = "L3V2"
    species: list[dict[str, str | float]] = Field(default_factory=list)
    reactions: list[dict[str, str]] = Field(default_factory=list)
    parameters: dict[str, float] = Field(default_factory=dict)
    sbml_xml_hash: str | None = None  # sha256 of the full SBML document if generated


class L5PKPDInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_smiles: str
    inchikey: str | None = None
    dose_mg: float = Field(gt=0.0)
    dose_route: str = Field(default="oral", description="oral|iv|sc|im|other")
    formulation: str = "IR_tablet"
    model_kind: L5PKModelKind = L5PKModelKind.ONE_COMPARTMENT
    fraction_unbound: float = Field(default=0.5, ge=0.0, le=1.0)
    cl_l_per_h: float = Field(default=10.0, gt=0.0)
    vd_l: float = Field(default=70.0, gt=0.0)
    ka_per_h: float = Field(default=1.0, gt=0.0)


class L5ExposureProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cmax_ng_per_ml: float = Field(ge=0.0)
    tmax_h: float = Field(ge=0.0)
    auc_0_inf_ng_h_per_ml: float = Field(ge=0.0)
    cmax_unbound_uM: float = Field(ge=0.0)
    half_life_h: float = Field(ge=0.0)


class L5ChannelExposureBridge(BaseModel):
    """Maps unbound plasma exposure to channel-level effect predictions.

    For cardiac wedge: exposure -> {IKr, IKs, INa, INaL, ICaL} fractional block.
    """

    model_config = ConfigDict(extra="forbid")

    cmax_unbound_uM: float = Field(ge=0.0)
    fractional_block_at_cmax: dict[str, float] = Field(
        default_factory=dict,
        description="current_name -> fraction blocked at Cmax_unbound (0.0-1.0)",
    )
    multi_current_balance_score: float | None = Field(
        default=None, ge=-1.0, le=1.0,
        description=(
            "Net repolarization balance: HIGHER = more outward-current block relative to "
            "inward-current block = greater APD-prolongation tendency in research-only "
            "multi-current models. RESEARCH INDICATOR ONLY. See L5 cardiac_bridge.py."
        ),
    )


class L5PKPDOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_smiles: str
    model_kind: L5PKModelKind
    sbml_packet: L5SBMLPacket | None = None
    exposure_profile: L5ExposureProfile
    cardiac_bridge: L5ChannelExposureBridge | None = None
    sbml_roundtrip_ok: bool = False
