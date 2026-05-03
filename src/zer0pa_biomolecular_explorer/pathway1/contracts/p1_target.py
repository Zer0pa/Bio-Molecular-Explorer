"""P1.Target contract — target identification.

Inputs: disease IDs (EFO/Orphanet) + optional gene class hint.
Outputs: ranked target dossier (UniProt + druggability + evidence pillars).
Replaceable adapters: Open Targets/TTD/GWAS Catalog/PubTator (external_api),
GPT-Rosalind (external_api Reasoner), local stub.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class P1TargetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disease_ids: list[str] = Field(
        min_length=1,
        description="EFO / Orphanet / OMIM disease identifiers.",
    )
    gene_class_hint: str | None = Field(
        default=None,
        description="Optional gene-class hint, e.g. 'ion_channel', 'kinase', 'GPCR'.",
    )
    max_targets: int = Field(default=10, ge=1, le=200)


class P1TargetEvidencePillars(BaseModel):
    model_config = ConfigDict(extra="forbid")

    genetic_evidence_score: float = Field(ge=0.0, le=1.0)
    literature_hit_count: int = Field(ge=0)
    pocket_volume_angstrom3: float | None = None
    ttd_entry_present: bool


class P1TargetDossier(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str = Field(pattern=r"^uniprot:[A-Z0-9_]+$")
    gene_symbol: str
    protein_name: str
    disease_associations: list[str]
    evidence_pillars: P1TargetEvidencePillars
    druggability_score: float = Field(ge=0.0, le=1.0)
    novelty_flag: bool
    structure_refs: list[str] = Field(default_factory=list)
    source_manifest_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class P1TargetOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dossiers: list[P1TargetDossier]
    gpt_rosalind_used: bool = False
    fallback_engine: str | None = None
