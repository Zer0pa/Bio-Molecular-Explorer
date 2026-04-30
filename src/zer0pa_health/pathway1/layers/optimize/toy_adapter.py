"""P1.Optimize toy adapter — gradient-style improvement schedule.

Unlike the stub adapter (step-jump proportional to iteration ratio), this
adapter uses a smooth sigmoid-shaped improvement curve that mimics a gradient
descent optimiser converging on a local optimum. The envelope shape, falsifier
suite, and contract are identical to P1OptimizeStubAdapter; only the
deterministic improvement schedule differs.

This adapter is useful for plug-swap tests and for exercising the confidence
tier escalation logic under a different numeric trajectory.

Backend: cpu_lite (same rationale as adapter.py — BoTorch EHVI is CPU-native).
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

from zer0pa_health.boundary import RESEARCH_BOUNDARY
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
    detect_lead_without_physchem_feasibility,
    detect_novelty_without_tractability,
    detect_selectivity_not_assessed,
    detect_stub_laundering,
    detect_synthesis_route_absent,
)
from zer0pa_health.hashing import sha256_of_obj
from zer0pa_health.ids import audit_id
from zer0pa_health.ids import run_id as new_run_id
from zer0pa_health.pathway1.contracts.p1_optimize import (
    P1ASKCOSRouteStep,
    P1OptimizeInput,
    P1OptimizeOutput,
    P1OptimizedLead,
)
from zer0pa_health.pathway1.contracts.p1_screen import P1ScreenedHit

_ADAPTER_NAME = "p1-optimize-toy"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "toy_gradient_botorch"

_STUB_ROUTE_STEPS = [
    P1ASKCOSRouteStep(
        step_index=0,
        rxn_smarts="[c:1][NH2:2]>>[c:1][N:2]C(=O)OCC",
        reagents=["Boc2O", "Et3N"],
    ),
    P1ASKCOSRouteStep(
        step_index=1,
        rxn_smarts="[c:1][N:2]C(=O)OCC>>[c:1][N:2]",
        reagents=["TFA", "DCM"],
    ),
    P1ASKCOSRouteStep(
        step_index=2,
        rxn_smarts="[c:1][N:2]>>[c:1][N:2][c:3]",
        reagents=["Pd(OAc)2", "Xphos", "Cs2CO3"],
    ),
]


def _det_int(smiles: str, target_id: str, lo: int, hi: int) -> int:
    digest = hashlib.sha256(f"{smiles}|{target_id}|toy".encode()).digest()
    span = hi - lo + 1
    return lo + (int.from_bytes(digest[:4], "big") % span)


def _det_float(smiles: str, target_id: str, lo: float, hi: float, salt: str = "") -> float:
    digest = hashlib.sha256(f"{smiles}|{target_id}|toy|{salt}".encode()).digest()
    raw = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF
    return lo + raw * (hi - lo)


def _sigmoid_delta(iteration_number: int, max_iterations: int) -> float:
    """Sigmoid-shaped improvement: slow start, fast middle, plateau near max.

    Returns a delta in [0.0, 1.0].
    """
    x = (iteration_number / max(max_iterations, 1)) * 12.0 - 6.0  # centre at mid
    sigmoid = 1.0 / (1.0 + math.exp(-x))
    return round(sigmoid, 6)


def _optimize_one_hit(
    hit: P1ScreenedHit,
    max_iterations: int,
    tpp_target_pic50_min: float,
    *,
    skip_askcos: bool = False,
) -> tuple[P1OptimizedLead, list[EnvelopeFalsifierItem]]:
    smiles = hit.smiles
    target_id = hit.target_id

    iteration_number = _det_int(smiles, target_id, 10, max_iterations)
    delta_pic50 = _sigmoid_delta(iteration_number, max_iterations)
    new_pic50 = min(12.0, round(hit.predicted_pIC50 + delta_pic50, 4))

    distinct_models_count = 3 if iteration_number > 30 else 2

    if distinct_models_count == 3 and new_pic50 >= tpp_target_pic50_min:
        confidence_tier = "A"
    elif distinct_models_count == 2:
        confidence_tier = "B"
    else:
        confidence_tier = "C"

    if skip_askcos:
        askcos_route_steps: list[P1ASKCOSRouteStep] = []
    else:
        askcos_route_steps = list(_STUB_ROUTE_STEPS)

    estimated_synthesis_steps = len(askcos_route_steps)

    lead_id = f"lead:{target_id}:{hashlib.sha256(smiles.encode()).hexdigest()[:8]}"
    lead = P1OptimizedLead(
        lead_id=lead_id,
        target_id=target_id,
        smiles=smiles,
        predicted_pIC50=new_pic50,
        admet_panel=hit.admet_panel.model_dump(),
        selectivity_score=hit.selectivity_score,
        synthetic_accessibility=hit.synthetic_accessibility,
        askcos_route_steps=askcos_route_steps,
        estimated_synthesis_steps=estimated_synthesis_steps,
        iteration_number=iteration_number,
        parent_scaffold=None,
        confidence_tier=confidence_tier,
        distinct_models_count=distinct_models_count,
    )

    items: list[EnvelopeFalsifierItem] = []

    admet = hit.admet_panel
    physchem_item = detect_lead_without_physchem_feasibility(
        predicted_pic50=new_pic50,
        esol_logs=admet.esol_logs,
        lipinski_violations=admet.lipinski_violations,
        herg_ic50_um=admet.hERG_IC50_uM,
        oral_bioavailability=admet.oral_bioavailability_prob,
    )
    items.append(physchem_item)

    off_target_count = hit.off_target_prediction_count
    selectivity_item = detect_selectivity_not_assessed(
        primary_pic50=new_pic50,
        off_target_prediction_count=off_target_count,
    )
    items.append(selectivity_item)

    synthesis_item = detect_synthesis_route_absent(
        sa_score=hit.synthetic_accessibility,
        askcos_route_steps=[s.model_dump() for s in askcos_route_steps],
    )
    items.append(synthesis_item)

    stub_tanimoto = _det_float(smiles, target_id, 0.20, 0.70, salt="tanimoto")
    novelty_item = detect_novelty_without_tractability(
        max_chembl_tanimoto=stub_tanimoto,
        sa_score=hit.synthetic_accessibility,
        askcos_step_count=estimated_synthesis_steps if not skip_askcos else None,
    )
    items.append(novelty_item)

    return lead, items


class P1OptimizeToyAdapter:
    """P1.Optimize toy adapter with sigmoid gradient-style improvement schedule.

    The improvement schedule uses a sigmoid curve rather than a linear step-jump,
    mimicking the convergence behaviour of a real gradient-based optimiser.
    Envelope contract is identical to P1OptimizeStubAdapter; plug-swap tests
    verify this.

    Backend: cpu_lite (BoTorch runs on CPU; no GPU required for this layer).
    """

    def process(
        self,
        inp: P1OptimizeInput,
        *,
        run_id: str | None = None,
        _skip_askcos_for_hit_indices: set[int] | None = None,
    ) -> LayerEnvelope:
        rid = run_id or new_run_id()
        input_dict = inp.model_dump()
        skip_set = _skip_askcos_for_hit_indices or set()

        tpp = inp.tpp
        leads: list[P1OptimizedLead] = []
        all_items: list[EnvelopeFalsifierItem] = []

        for idx, hit_dict in enumerate(inp.hits):
            hit = P1ScreenedHit.model_validate(hit_dict)
            skip_askcos = idx in skip_set
            lead, items = _optimize_one_hit(
                hit,
                inp.max_iterations,
                tpp.target_pic50_min,
                skip_askcos=skip_askcos,
            )
            leads.append(lead)
            all_items.extend(items)

        stub_item = detect_stub_laundering(
            backend="cpu_lite",
            claim_kind="hit_to_lead_optimization",
            mechanism_escalation=False,
        )
        all_items.append(stub_item)

        text_blob = f"{RESEARCH_BOUNDARY} {inp.target_id}"
        overclaim_item = detect_clinical_overclaim(text_blob)
        all_items.append(overclaim_item)

        max_iter_used = max((l.iteration_number for l in leads), default=0)
        output_obj = P1OptimizeOutput(
            target_id=inp.target_id,
            n_input_hits=len(inp.hits),
            n_leads=len(leads),
            iterations_used=max_iter_used,
            leads=leads,
            tpp_used=tpp,
        )
        output_dict: dict[str, Any] = output_obj.model_dump()

        n_tier_a = sum(1 for l in leads if l.confidence_tier == "A")
        confidence_score = round(0.6 + 0.2 * (n_tier_a / max(len(leads), 1)), 4)
        confidence_band = ConfidenceBand.MEDIUM if confidence_score < 0.75 else ConfidenceBand.HIGH

        any_fail = any(it.status == FalsifierStatus.FAIL for it in all_items)
        envelope_falsifier_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS

        return LayerEnvelope(
            run_id=rid,
            layer=LayerName.P1_OPTIMIZE,
            tool_adapter=ToolAdapter(
                name=_ADAPTER_NAME,
                version=_ADAPTER_VERSION,
                backend=Backend.CPU_LITE,
                engine=_ENGINE,
            ),
            input_refs=[],
            output=output_dict,
            confidence=EnvelopeConfidence(
                score=confidence_score,
                band=confidence_band,
                basis=["stub_botorch_axEHVI", "stub_reinvent4_rl_loop"],
            ),
            falsifier=EnvelopeFalsifier(
                status=envelope_falsifier_status,
                items=all_items,
            ),
            audit=EnvelopeAudit(
                audit_record_id=audit_id(),
                input_hash=sha256_of_obj(input_dict),
                output_hash=sha256_of_obj(output_dict),
                source_manifest_refs=[],
            ),
            back_edges=[],
        )
