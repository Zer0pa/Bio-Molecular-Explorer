"""P1.Screen stub adapter — in silico screening (Boltz-2/Chemprop/GNINA stub).

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.

Adapter: P1ScreenStubAdapter
  - backend=stub, engine=boltz2_chemprop_stub
  - Deterministic: same input → same output (excluding created_at / audit IDs)
  - Runs all P1.Screen falsifiers per PATHWAY1_PRD §3:
      HIT_FROM_NOISE, LEAD_WITHOUT_PHYSCHEM_FEASIBILITY, SELECTIVITY_NOT_ASSESSED,
      BENCHMARK_LEAKAGE, STUB_LAUNDERING, CLINICAL_OVERCLAIM

ADMET and affinity values are deterministic string-hash proxies — NOT predictive
chemistry. Same SMILES → identical numbers, always. Do NOT use as drug evidence.
"""

from __future__ import annotations

import hashlib
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
    P1ADMETPanel,
    P1ScreenInput,
    P1ScreenOutput,
    P1ScreenedHit,
)


# ---------------------------------------------------------------------------
# Deterministic float seeder
# ---------------------------------------------------------------------------

def _seed(key: str, lo: float, hi: float, *, salt: str = "stub_v1") -> float:
    """Map an arbitrary key string to a float in [lo, hi] deterministically."""
    digest = hashlib.sha256(f"{salt}|{key}".encode("utf-8")).hexdigest()
    n = int(digest[:8], 16) / 0xFFFF_FFFF
    return lo + (hi - lo) * n


def _seed_bool(key: str, *, salt: str = "stub_v1") -> bool:
    digest = hashlib.sha256(f"{salt}|{key}".encode("utf-8")).hexdigest()
    return int(digest[8], 16) % 2 == 1


def _candidate_hash(candidate: dict[str, Any]) -> str:
    """Stable hash for a candidate dict."""
    cid = candidate.get("candidate_id") or candidate.get("smiles", "unknown")
    return hashlib.sha256(str(cid).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# ADMET panel builder (stub-grade, deterministic)
# ---------------------------------------------------------------------------

def _build_admet(candidate: dict[str, Any], *, salt: str = "stub_v1") -> P1ADMETPanel:
    ch = _candidate_hash(candidate)
    return P1ADMETPanel(
        logP=_seed(f"{ch}:logP", 1.5, 4.0, salt=salt),
        tpsa=_seed(f"{ch}:tpsa", 50.0, 110.0, salt=salt),
        BBB_penetration_prob=_seed(f"{ch}:bbb", 0.1, 0.5, salt=salt),
        hERG_IC50_uM=_seed(f"{ch}:herg", 10.0, 60.0, salt=salt),
        hepatotox_flag=_seed_bool(f"{ch}:hepatotox", salt=salt),
        oral_bioavailability_prob=_seed(f"{ch}:orabio", 0.4, 0.85, salt=salt),
        esol_logs=_seed(f"{ch}:esol", -3.5, -1.5, salt=salt),
        lipinski_violations=int(_seed(f"{ch}:lipinski", 0.0, 1.999, salt=salt)),
    )


# ---------------------------------------------------------------------------
# pIC50 and confidence tier
# ---------------------------------------------------------------------------

def _build_pic50(candidate: dict[str, Any], pic50_threshold: float, *, salt: str = "stub_v1") -> float:
    ch = _candidate_hash(candidate)
    return _seed(f"{ch}:pic50", 5.5, 8.5, salt=salt)


def _build_confidence_tier(
    candidate: dict[str, Any],
    predicted_pic50: float,
    pic50_threshold: float,
    *,
    salt: str = "stub_v1",
) -> str:
    """Deterministic confidence tier assignment.

    Rules (stub):
      - Tier C if predicted_pIC50 < pic50_threshold
      - Tier A if a deterministic "all three models agreed" flag is true
      - Tier B otherwise (default)
    """
    if predicted_pic50 < pic50_threshold:
        return "C"
    ch = _candidate_hash(candidate)
    all_agreed = _seed_bool(f"{ch}:all_models_agreed", salt=salt)
    return "A" if all_agreed else "B"


# ---------------------------------------------------------------------------
# Screened hit builder
# ---------------------------------------------------------------------------

def _build_hit(
    candidate: dict[str, Any],
    target_id: str,
    target_panel_genes: list[str],
    pic50_threshold: float,
    *,
    salt: str = "stub_v1",
    force_pains_flags: list[str] | None = None,
    force_pic50: float | None = None,
    force_esol: float | None = None,
) -> P1ScreenedHit:
    ch = _candidate_hash(candidate)
    predicted_pic50 = force_pic50 if force_pic50 is not None else _build_pic50(candidate, pic50_threshold, salt=salt)
    admet = _build_admet(candidate, salt=salt)
    if force_esol is not None:
        admet = P1ADMETPanel(
            logP=admet.logP,
            tpsa=admet.tpsa,
            BBB_penetration_prob=admet.BBB_penetration_prob,
            hERG_IC50_uM=admet.hERG_IC50_uM,
            hepatotox_flag=admet.hepatotox_flag,
            oral_bioavailability_prob=admet.oral_bioavailability_prob,
            esol_logs=force_esol,
            lipinski_violations=admet.lipinski_violations,
        )

    pains_flags = force_pains_flags if force_pains_flags is not None else []

    confidence_tier = _build_confidence_tier(
        candidate, predicted_pic50, pic50_threshold, salt=salt
    )

    return P1ScreenedHit(
        hit_id=f"hit:{ch}:{salt}",
        target_id=target_id,
        smiles=candidate.get("smiles", "C"),
        predicted_pIC50=predicted_pic50,
        affinity_source="Boltz-2_stub",
        admet_panel=admet,
        selectivity_score=_seed(f"{ch}:sel", 0.6, 0.85, salt=salt),
        synthetic_accessibility=_seed(f"{ch}:sa", 2.0, 4.0, salt=salt),
        pains_flags=pains_flags,
        aggregator_flag=False,
        off_target_prediction_count=len(target_panel_genes),
        confidence_tier=confidence_tier,
    )


# ---------------------------------------------------------------------------
# Stub train InChIKeys (empty by default → benchmark leakage PASS by default)
# ---------------------------------------------------------------------------

_STUB_TRAIN_INCHIKEYS: set[str] = set()


# ---------------------------------------------------------------------------
# P1ScreenStubAdapter
# ---------------------------------------------------------------------------

class P1ScreenStubAdapter:
    """P1.Screen stub adapter — Boltz-2 / Chemprop / GNINA stub.

    Parameters for process():
        input: P1ScreenInput
        run_id: Optional caller-supplied run ID
        train_inchikeys: Override training InChIKeys for benchmark leakage test
        test_inchikeys: Override test InChIKeys for benchmark leakage test
        _force_pains_map: {candidate_id: [pains_flag_str]} for test injection
        _force_pic50_map: {candidate_id: float} for test injection
        _force_esol_map: {candidate_id: float} for test injection

    Returns:
        LayerEnvelope with layer=P1_SCREEN, backend=stub
    """

    NAME = "p1-screen-stub"
    VERSION = "0.1.0"
    ENGINE = "boltz2_chemprop_stub"
    BACKEND = Backend.STUB
    _SALT = "stub_v1"

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

        # ── Step 1: Build candidate hits and run per-hit falsifiers ────────
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

            # ── HIT_FROM_NOISE ────────────────────────────────────────────
            noise_item = detect_hit_from_noise(
                smiles=hit.smiles,
                sa_score=hit.synthetic_accessibility,
                pains_flags=hit.pains_flags,
                aggregator_flag=hit.aggregator_flag,
            )
            if noise_item.status == FalsifierStatus.FAIL:
                # Record the failure; drop hit from output
                falsifier_items.append(noise_item)
                continue

            # ── LEAD_WITHOUT_PHYSCHEM_FEASIBILITY ─────────────────────────
            feasibility_item = detect_lead_without_physchem_feasibility(
                predicted_pic50=hit.predicted_pIC50,
                esol_logs=hit.admet_panel.esol_logs,
                lipinski_violations=hit.admet_panel.lipinski_violations,
                herg_ic50_um=hit.admet_panel.hERG_IC50_uM,
                oral_bioavailability=hit.admet_panel.oral_bioavailability_prob,
                pic50_threshold=input.pic50_threshold,
            )
            falsifier_items.append(feasibility_item)
            # soft_fail — keep hit but flag

            surviving_hits.append(hit)

        # ── Step 2: SELECTIVITY_NOT_ASSESSED (aggregate) ──────────────────
        # Run against the maximum off_target_prediction_count across all hits,
        # or 0 if no hits. The falsifier spec checks per-hit, but here we also
        # check the aggregate signal: if target_panel_genes is empty the count
        # is always 0 and we should fire.
        aggregate_off_target = len(input.target_panel_genes)
        # Use highest pIC50 surviving hit for the check
        max_pic50 = max((h.predicted_pIC50 for h in surviving_hits), default=0.0)
        selectivity_item = detect_selectivity_not_assessed(
            primary_pic50=max_pic50,
            off_target_prediction_count=aggregate_off_target,
            pic50_threshold=input.pic50_threshold,
        )
        falsifier_items.append(selectivity_item)

        # ── Step 3: BENCHMARK_LEAKAGE ──────────────────────────────────────
        train_iks = train_inchikeys if train_inchikeys is not None else _STUB_TRAIN_INCHIKEYS
        test_iks = test_inchikeys if test_inchikeys is not None else set()
        leakage_item = detect_benchmark_leakage(
            train_inchikeys=train_iks,
            test_inchikeys=test_iks,
        )
        falsifier_items.append(leakage_item)

        # ── Step 4: STUB_LAUNDERING ────────────────────────────────────────
        laundering_item = detect_stub_laundering(
            backend=self.BACKEND.value,
            claim_kind="mechanism_claim",
            mechanism_escalation=False,
        )
        falsifier_items.append(laundering_item)

        # ── Step 5: CLINICAL_OVERCLAIM ─────────────────────────────────────
        output_obj = P1ScreenOutput(
            target_id=input.target_id,
            n_input_candidates=len(input.candidates),
            n_hits=len(surviving_hits),
            hits=surviving_hits,
        )
        overclaim_item = detect_clinical_overclaim(output_obj.model_dump_json())
        falsifier_items.append(overclaim_item)

        # ── Step 6: Overall falsifier status ──────────────────────────────
        any_fail = any(it.status == FalsifierStatus.FAIL for it in falsifier_items)
        overall_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS

        # ── Step 7: Confidence score ───────────────────────────────────────
        # 0.5-0.7 band; degrade if any falsifier fired
        base_score = 0.62
        if any_fail:
            base_score = max(0.5, base_score - 0.08)

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
