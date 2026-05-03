"""P1.Structure contract — protein structure prediction + binding pocket.

Inputs: P1TargetDossier (or just target_id + gene_symbol).
Outputs: P1StructureDossier with mmCIF/PDB ref, binding pocket, pLDDT confidence.
Replaceable adapters: OpenFold3 (Apache 2.0; runpod_gpu), Boltz-2 joint structure (MIT; runpod_gpu),
ESM3 (open weights; runpod_gpu), local stub.

CRITICAL: AlphaFold DB pre-computed structures are Class D non-commercial;
detect_alphafold_d_leakage triggers if structure_source_tag == 'alphafold_db_precomputed'
without an OpenFold3 recompute provenance ref.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class P1StructureInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str = Field(pattern=r"^uniprot:[A-Z0-9_]+$")
    gene_symbol: str
    sequence: str | None = Field(
        default=None, description="Optional FASTA sequence; if None, fetched from UniProt."
    )
    pdb_ref_hint: str | None = None  # optional pre-existing PDB structure to use as template


class P1BindingPocket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pocket_id: str
    binding_site_residues: list[int] = Field(default_factory=list)
    binding_site_residue_labels: list[str] = Field(default_factory=list)
    pocket_volume_angstrom3: float = Field(ge=0.0)
    pocket_label: str = ""  # e.g., "DHP_binding_site"


class P1StructureDossier(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    gene_symbol: str
    structure_source_tag: Literal[
        "openfold3", "boltz_2_joint", "esm3", "alphafold_db_precomputed", "stub", "experimental_pdb"
    ]
    structure_ref: str  # mmCIF/PDB locator
    uniprot_af_id: str | None = None  # only set if structure_source_tag == "alphafold_db_precomputed"
    openfold3_run_id: str | None = None  # provenance for OpenFold3 recompute (required for commercial)
    pocket: P1BindingPocket
    mean_plddt: float = Field(ge=0.0, le=100.0)
    binding_site_mean_plddt: float = Field(ge=0.0, le=100.0)


class P1StructureOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dossier: P1StructureDossier
