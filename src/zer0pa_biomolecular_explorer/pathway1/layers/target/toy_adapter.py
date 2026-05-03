"""P1.Target toy adapter — deliberately different from stub for plug-swap testing.

Differences from P1TargetStubAdapter:
  - Dossier ordering: druggability_score DESC instead of genetic_evidence_score DESC.
  - Confidence band: 0.55-0.75 instead of 0.50-0.70.
  - engine: "toy_canned_targets" instead of "stub_canned_targets".
  - adapter name: "p1-target-toy".

Same interface, same falsifier-class set, same envelope shape.
Purpose: verify plug-replaceability (same output keys, same falsifier classes,
valid JSON Schema) even when internals differ.
"""

from __future__ import annotations

import json
from typing import Any

from zer0pa_biomolecular_explorer.envelope import (
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
from zer0pa_biomolecular_explorer.falsifiers.detectors import (
    detect_clinical_overclaim,
    detect_gpt_rosalind_unavailable,
    detect_license_drift,
    detect_target_validation_overreach,
)
from zer0pa_biomolecular_explorer.hashing import sha256_of_obj
from zer0pa_biomolecular_explorer.ids import audit_id
from zer0pa_biomolecular_explorer.ids import run_id as new_run_id
from zer0pa_biomolecular_explorer.pathway1.contracts.p1_target import (
    P1TargetInput,
    P1TargetOutput,
)
from zer0pa_biomolecular_explorer.pathway1.layers.target.adapter import (
    _ALL_FIXTURES,
    _ALLOWED_ROSALIND_VARIANTS,
    _GPT_ROSALIND_VARIANT,
    _dossier_from_fixture,
)

_ADAPTER_NAME = "p1-target-toy"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "toy_canned_targets"


def _filter_by_disease_druggability(
    fixtures: list[dict[str, Any]],
    disease_ids: list[str],
    max_targets: int,
) -> list[dict[str, Any]]:
    """Filter by disease overlap, ordered by druggability_score DESC (toy ordering)."""
    requested = set(disease_ids)
    matched = [
        f for f in fixtures
        if requested.intersection(set(f.get("disease_associations", [])))
    ]
    matched.sort(key=lambda f: f.get("druggability_score", 0.0), reverse=True)
    return matched[:max_targets]


class P1TargetToyAdapter:
    """Toy adapter for P1.Target.

    Deliberately different from P1TargetStubAdapter:
    - Orders dossiers by druggability_score DESC (not genetic_evidence_score DESC).
    - Confidence band: 0.55-0.75.

    Same interface and falsifier-class set as P1TargetStubAdapter.
    Used to verify plug-replaceability (output keys, falsifier classes, schema validity).
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

        # ── 1. Filter fixtures by disease, sorted by druggability_score DESC ──
        matched_fixtures = _filter_by_disease_druggability(
            _ALL_FIXTURES, input.disease_ids, input.max_targets
        )

        # ── 2. Build dossiers + per-dossier overreach detector ─────────────
        from zer0pa_biomolecular_explorer.pathway1.contracts.p1_target import P1TargetDossier
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

        # ── 6. Clinical overclaim scan ─────────────────────────────────────
        output_json_str = json.dumps(output_dict, ensure_ascii=False)
        overclaim_item = detect_clinical_overclaim(output_json_str)
        falsifier_items.append(overclaim_item)

        # ── 7. Confidence (toy band: 0.55-0.75) ───────────────────────────
        any_fail = any(i.status == FalsifierStatus.FAIL for i in falsifier_items)
        if any_fail:
            confidence_score = 0.48
            confidence_band = ConfidenceBand.LOW
        else:
            confidence_score = 0.65
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
