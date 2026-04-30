"""P1.Screen toy adapter — second deterministic stub with different seeds.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.

Same public interface as P1ScreenStubAdapter.process() but uses a different
deterministic seed salt ("toy_v1" vs "stub_v1") so that values differ while
the schema is identical. Used for plug-swap replaceability tests.

ADMET and affinity values are deterministic string-hash proxies — NOT predictive
chemistry.
"""

from __future__ import annotations

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
    detect_benchmark_leakage,
    detect_clinical_overclaim,
    detect_hit_from_noise,
    detect_lead_without_physchem_feasibility,
    detect_selectivity_not_assessed,
    detect_stub_laundering,
)
from zer0pa_health.hashing import sha256_of_obj
from zer0pa_health.ids import audit_id, run_id as new_run_id
from zer0pa_health.pathway1.contracts.p1_screen import (
    P1ScreenInput,
    P1ScreenOutput,
    P1ScreenedHit,
)
from zer0pa_health.pathway1.layers.screen.adapter import (
    _STUB_TRAIN_INCHIKEYS,
    _build_hit,
)


class P1ScreenToyAdapter:
    """P1.Screen toy adapter — identical schema to P1ScreenStubAdapter, different values.

    Uses salt="toy_v1" so all seeded values differ deterministically.
    All falsifier classes emitted are identical to P1ScreenStubAdapter.
    """

    NAME = "p1-screen-toy"
    VERSION = "0.1.0"
    ENGINE = "boltz2_chemprop_toy_stub"
    BACKEND = Backend.STUB
    _SALT = "toy_v1"

    def process(
        self,
        input: P1ScreenInput,
        *,
        run_id: str | None = None,
        train_inchikeys: set[str] | None = None,
        test_inchikeys: set[str] | None = None,
        _force_pains_map: dict[str, list[str]] | None = None,
        _force_pic50_map: dict[str, float] | None = None,
        _force_esol_map: dict[str, float] | None = None,
    ) -> LayerEnvelope:
        rid = run_id or new_run_id()
        falsifier_items: list[EnvelopeFalsifierItem] = []

        surviving_hits: list[P1ScreenedHit] = []

        for cand in input.candidates:
            cid = cand.get("candidate_id", cand.get("smiles", ""))

            force_pains = (_force_pains_map or {}).get(cid)
            force_pic50 = (_force_pic50_map or {}).get(cid)
            force_esol = (_force_esol_map or {}).get(cid)

            hit = _build_hit(
                cand,
                input.target_id,
                input.target_panel_genes,
                input.pic50_threshold,
                salt=self._SALT,
                force_pains_flags=force_pains,
                force_pic50=force_pic50,
                force_esol=force_esol,
            )

            noise_item = detect_hit_from_noise(
                smiles=hit.smiles,
                sa_score=hit.synthetic_accessibility,
                pains_flags=hit.pains_flags,
                aggregator_flag=hit.aggregator_flag,
            )
            if noise_item.status == FalsifierStatus.FAIL:
                falsifier_items.append(noise_item)
                continue

            feasibility_item = detect_lead_without_physchem_feasibility(
                predicted_pic50=hit.predicted_pIC50,
                esol_logs=hit.admet_panel.esol_logs,
                lipinski_violations=hit.admet_panel.lipinski_violations,
                herg_ic50_um=hit.admet_panel.hERG_IC50_uM,
                oral_bioavailability=hit.admet_panel.oral_bioavailability_prob,
                pic50_threshold=input.pic50_threshold,
            )
            falsifier_items.append(feasibility_item)

            surviving_hits.append(hit)

        aggregate_off_target = len(input.target_panel_genes)
        max_pic50 = max((h.predicted_pIC50 for h in surviving_hits), default=0.0)
        selectivity_item = detect_selectivity_not_assessed(
            primary_pic50=max_pic50,
            off_target_prediction_count=aggregate_off_target,
            pic50_threshold=input.pic50_threshold,
        )
        falsifier_items.append(selectivity_item)

        train_iks = train_inchikeys if train_inchikeys is not None else _STUB_TRAIN_INCHIKEYS
        test_iks = test_inchikeys if test_inchikeys is not None else set()
        leakage_item = detect_benchmark_leakage(
            train_inchikeys=train_iks,
            test_inchikeys=test_iks,
        )
        falsifier_items.append(leakage_item)

        laundering_item = detect_stub_laundering(
            backend=self.BACKEND.value,
            claim_kind="mechanism_claim",
            mechanism_escalation=False,
        )
        falsifier_items.append(laundering_item)

        output_obj = P1ScreenOutput(
            target_id=input.target_id,
            n_input_candidates=len(input.candidates),
            n_hits=len(surviving_hits),
            hits=surviving_hits,
        )
        overclaim_item = detect_clinical_overclaim(output_obj.model_dump_json())
        falsifier_items.append(overclaim_item)

        any_fail = any(it.status == FalsifierStatus.FAIL for it in falsifier_items)
        overall_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS

        base_score = 0.58  # toy uses slightly lower base than stub
        if any_fail:
            base_score = max(0.5, base_score - 0.05)

        output_payload = output_obj.model_dump()
        input_payload = input.model_dump()

        return LayerEnvelope(
            run_id=rid,
            layer=LayerName.P1_SCREEN,
            tool_adapter=ToolAdapter(
                name=self.NAME,
                version=self.VERSION,
                backend=self.BACKEND,
                engine=self.ENGINE,
            ),
            input_refs=[],
            output=output_payload,
            confidence=EnvelopeConfidence(
                score=base_score,
                band=ConfidenceBand.MEDIUM,
                basis=["stub_boltz2_stub", "stub_chemprop_v2"],
            ),
            falsifier=EnvelopeFalsifier(
                status=overall_status,
                items=falsifier_items,
            ),
            audit=EnvelopeAudit(
                audit_record_id=audit_id(),
                input_hash=sha256_of_obj(input_payload),
                output_hash=sha256_of_obj(output_payload),
                source_manifest_refs=[],
            ),
            back_edges=[],
        )
