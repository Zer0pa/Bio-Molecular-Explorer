"""P1.Generate contract — generative molecule design.

Inputs: P1StructureDossier + generation mode + library_size.
Outputs: candidate library (SMILES + generation_method + provenance).
Replaceable adapters: REINVENT 4 (Apache 2.0; runpod_gpu), DiffSBDD (MIT; runpod_gpu),
RFdiffusion3 (Baker Lab commercial-permissive; runpod_gpu), local stub.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class P1GenerateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    structure_ref: str
    pocket_id: str
    mode: Literal[
        "de_novo", "sbdd", "scaffold_hop", "linker", "fragment_grow", "binder_design"
    ] = "sbdd"
    library_size: int = Field(default=1000, ge=10, le=100_000)
    seed_scaffold_smiles: str | None = None  # required for scaffold_hop / linker / fragment_grow


class P1GeneratedCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    smiles: str
    generation_method: str  # e.g., "REINVENT4_RL", "DiffSBDD"
    parent_scaffold: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class P1GenerateOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    library_size_actual: int
    candidates: list[P1GeneratedCandidate]
    mode_used: str
    backend_used: str  # adapter backend (stub/cpu_lite/runpod_gpu)
