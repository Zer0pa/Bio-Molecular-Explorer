"""P1.Target stub adapter — canned dossiers from fixtures/pathway1/targets/*.json.

Adapter discipline
------------------
- backend = Backend.STUB; engine = "stub_canned_targets"
- Loads all six target fixtures at import time; filters by disease_association overlap.
- Dossiers are ordered by genetic_evidence_score DESC (canonical stub ordering).
- Falsifiers run on every process() call:
    detect_target_validation_overreach  — per dossier
    detect_gpt_rosalind_unavailable     — once per call (api_http_status kwarg)
    detect_clinical_overclaim           — over serialised output JSON
    detect_license_drift                — PASS when gpt_rosalind_status == 200 (approved variant)
                                          PASS when != 200  (explicit fallback; license drift only
                                          fires when an *unapproved new variant* is introduced)
- gpt_rosalind_status=429 → GPT_ROSALIND_UNAVAILABLE FAIL, output.gpt_rosalind_used=False,
  output.fallback_engine="biogpt_stub"
- Confidence band: 0.5-0.7 when all falsifiers PASS; lower if any FAIL.
- Pure Python; no LLM calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from zer0pa_health.envelope import (
    Backend,
    ConfidenceBand,
    EnvelopeAudit,
    EnvelopeConfidence,
    EnvelopeFalsifier,
    EnvelopeFalsifierItem,
    FalsifierStatus,
    LayerEnvelope,
    LayerName,
    ToolAdapter,
)
from zer0pa_health.falsifiers.detectors import (
    detect_clinical_overclaim,
    detect_gpt_rosalind_unavailable,
    detect_license_drift,
    detect_target_validation_overreach,
)
from zer0pa_health.hashing import sha256_of_obj
from zer0pa_health.ids import audit_id
from zer0pa_health.ids import run_id as new_run_id
from zer0pa_health.pathway1.contracts.p1_target import (
    P1TargetDossier,
    P1TargetEvidencePillars,
    P1TargetInput,
    P1TargetOutput,
)

_ADAPTER_NAME = "p1-target-stub"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "stub_canned_targets"

# Approved GPT-Rosalind variant for license-drift check
_ALLOWED_ROSALIND_VARIANTS = ["gpt_rosalind_v1"]
_GPT_ROSALIND_VARIANT = "gpt_rosalind_v1"

_FIXTURES_DIR = (
    Path(__file__).parent.parent.parent.parent.parent.parent
    / "fixtures"
    / "pathway1"
    / "targets"
)


def _load_fixtures() -> list[dict[str, Any]]:
    """Load all target fixture JSON files from fixtures/pathway1/targets/*.json."""
    records: list[dict[str, Any]] = []
    if not _FIXTURES_DIR.exists():
        return records
    for path in sorted(_FIXTURES_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        records.append(data)
    return records


# Load once at module import — deterministic
_ALL_FIXTURES: list[dict[str, Any]] = _load_fixtures()


def _dossier_from_fixture(raw: dict[str, Any]) -> P1TargetDossier:
    """Convert a raw fixture dict into a P1TargetDossier."""
    ep = raw.get("evidence_pillars", {})
    pillars = P1TargetEvidencePillars(
        genetic_evidence_score=ep.get("genetic_evidence_score", 0.0),
        literature_hit_count=ep.get("literature_hit_count", 0),
        pocket_volume_angstrom3=ep.get("pocket_volume_angstrom3"),
        ttd_entry_present=ep.get("ttd_entry_present", False),
    )
    return P1TargetDossier(
        target_id=raw["target_id"],
        gene_symbol=raw["gene_symbol"],
        protein_name=raw["protein_name"],
        disease_associations=raw.get("disease_associations", []),
        evidence_pillars=pillars,
        druggability_score=raw.get("druggability_score", 0.0),
        novelty_flag=raw.get("novelty_flag", False),
        structure_refs=raw.get("structure_refs", []),
        source_manifest_refs=raw.get("source_manifest_refs", []),
        confidence=round(raw.get("genetic_evidence_score", 0.5) * 0.8 + 0.1, 3),
    )


def _filter_by_disease(
    fixtures: list[dict[str, Any]],
    disease_ids: list[str],
    max_targets: int,
) -> list[dict[str, Any]]:
    """Return fixtures whose disease_associations overlap with requested disease_ids.

    Ordered by genetic_evidence_score DESC (canonical stub ordering).
    """
    requested = set(disease_ids)
    matched = [
        f for f in fixtures
        if requested.intersection(set(f.get("disease_associations", [])))
    ]
    matched.sort(key=lambda f: f.get("genetic_evidence_score", 0.0), reverse=True)
    return matched[:max_targets]


class P1TargetStubAdapter:
    """Stub adapter for P1.Target.

    Returns canned dossiers from fixtures/pathway1/targets/*.json.
    Dossiers are filtered by disease_association overlap then ordered by
    genetic_evidence_score DESC.

    Parameters
    ----------
    input:
        P1TargetInput (disease_ids, gene_class_hint, max_targets)
    run_id:
        Optional run ID; generated if absent.
    gpt_rosalind_status:
        Simulated HTTP status for GPT-Rosalind API (default 200 = OK).
        Pass 429 to trigger GPT_ROSALIND_UNAVAILABLE FAIL + fallback_engine.
    """

    def process(
        self,
        input: P1TargetInput,
        *,
        run_id: str | None = None,
        gpt_rosalind_status: int = 200,
    ) -> LayerEnvelope:
        rid = run_id or new_run_id()
        input_dict = input.model_dump()

        falsifier_items: list[EnvelopeFalsifierItem] = []

        # ── 1. Filter fixtures by disease association ──────────────────────
        matched_fixtures = _filter_by_disease(
            _ALL_FIXTURES, input.disease_ids, input.max_targets
        )

        # ── 2. Build dossiers + run per-dossier overreach detector ─────────
        dossiers: list[P1TargetDossier] = []
        for raw in matched_fixtures:
            dossier = _dossier_from_fixture(raw)
            dossiers.append(dossier)
            ep = dossier.evidence_pillars
            overreach_item = detect_target_validation_overreach(
                genetic_evidence_score=ep.genetic_evidence_score,
                literature_hit_count=ep.literature_hit_count,
                pocket_volume_angstrom3=ep.pocket_volume_angstrom3,
                ttd_entry_present=ep.ttd_entry_present,
            )
            falsifier_items.append(overreach_item)

        # When there are no dossiers (bogus disease), add a single overreach FAIL
        # with all-zero evidence pillars so the falsifier fires.
        if not dossiers:
            overreach_item = detect_target_validation_overreach(
                genetic_evidence_score=0.0,
                literature_hit_count=0,
                pocket_volume_angstrom3=None,
                ttd_entry_present=False,
            )
            falsifier_items.append(overreach_item)

        # ── 3. GPT-Rosalind availability ───────────────────────────────────
        gpt_unavailable = gpt_rosalind_status not in (200, 201)
        fallback_engine: str | None = "biogpt_stub" if gpt_unavailable else None

        gpt_item = detect_gpt_rosalind_unavailable(
            api_http_status=gpt_rosalind_status,
            fallback_used=fallback_engine,
        )
        falsifier_items.append(gpt_item)

        # ── 4. License drift ───────────────────────────────────────────────
        # License drift fires only when an unapproved NEW variant is introduced.
        # gpt_rosalind_v1 is the approved variant (200 path).
        # Explicit fallback (biogpt_stub) is also sanctioned; no new variant added.
        license_item = detect_license_drift(
            tool_name="gpt_rosalind",
            requested_variant=_GPT_ROSALIND_VARIANT,
            allowed_variants=_ALLOWED_ROSALIND_VARIANTS,
        )
        falsifier_items.append(license_item)

        # ── 5. Build output dict ───────────────────────────────────────────
        output_obj = P1TargetOutput(
            dossiers=dossiers,
            gpt_rosalind_used=not gpt_unavailable,
            fallback_engine=fallback_engine,
        )
        output_dict: dict[str, Any] = output_obj.model_dump()
        output_dict["basis"] = ["stub_canned_targets", "no_real_open_targets_call"]

        # ── 6. Clinical overclaim scan over output JSON ───────────────────
        output_json_str = json.dumps(output_dict, ensure_ascii=False)
        overclaim_item = detect_clinical_overclaim(output_json_str)
        falsifier_items.append(overclaim_item)

        # ── 7. Confidence ─────────────────────────────────────────────────
        any_fail = any(i.status == FalsifierStatus.FAIL for i in falsifier_items)
        if any_fail:
            confidence_score = 0.42
            confidence_band = ConfidenceBand.LOW
        else:
            confidence_score = 0.62
            confidence_band = ConfidenceBand.MEDIUM

        # ── 8. Assemble envelope ───────────────────────────────────────────
        falsifier_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS

        return LayerEnvelope(
            run_id=rid,
            layer=LayerName.P1_TARGET,
            tool_adapter=ToolAdapter(
                name=_ADAPTER_NAME,
                version=_ADAPTER_VERSION,
                backend=Backend.STUB,
                engine=_ENGINE,
            ),
            input_refs=[],
            output=output_dict,
            confidence=EnvelopeConfidence(
                score=confidence_score,
                band=confidence_band,
                basis=["stub_canned_targets", "no_real_open_targets_call"],
            ),
            falsifier=EnvelopeFalsifier(
                status=falsifier_status,
                items=falsifier_items,
            ),
            audit=EnvelopeAudit(
                audit_record_id=audit_id(),
                input_hash=sha256_of_obj(input_dict),
                output_hash=sha256_of_obj(output_dict),
                source_manifest_refs=[
                    "OpenTargets_v25_06",
                    "TTD_2026",
                    "GWAS_Catalog_EBI",
                    "ChEMBL_36",
                    "UniProt_SwissProt",
                ],
            ),
            back_edges=[],
        )
