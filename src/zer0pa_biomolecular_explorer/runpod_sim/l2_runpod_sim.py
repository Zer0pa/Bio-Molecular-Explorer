"""L2 Runpod-sim adapter — simulates the GPU-real L2 (DeepXDE PINN) adapter.

Same interface as L2StubAdapter, `backend=runpod_gpu`, deterministic canned
values that mimic what the GPU adapter would return. The cutover-acceptance
test can flip L2 from stub to runpod_gpu via this sim with no downstream change.
"""

from __future__ import annotations

import hashlib
from typing import Any

from zer0pa_biomolecular_explorer.contracts.l2 import L2PropertyInput
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
    detect_invalid_smiles,
    detect_nan_or_nonfinite,
    detect_stub_laundering,
)
from zer0pa_biomolecular_explorer.hashing import sha256_of_obj
from zer0pa_biomolecular_explorer.ids import audit_id, run_id as new_run_id


def _seed(*parts: str, lo: float, hi: float) -> float:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    n = int(h[:8], 16) / 0xFFFFFFFF
    return lo + (hi - lo) * n


class L2RunpodSimAdapter:
    """L2 GPU-real simulation for cutover acceptance.

    Same interface as L2StubAdapter but `backend=runpod_gpu` and the descriptor
    proxies are computed from a different deterministic formula (mimicking
    "the GPU just gave us better numbers"). Output schema MUST match L2StubAdapter
    exactly so downstream layers (L3, L5) parse unchanged.
    """

    NAME = "l2-runpod-sim"
    VERSION = "0.1.0"
    ENGINE = "deepxde_pinn_runpod_sim"

    def __init__(self) -> None:
        self._adapter = ToolAdapter(
            name=self.NAME,
            version=self.VERSION,
            backend=Backend.RUNPOD_GPU,
            engine=self.ENGINE,
        )

    def process(
        self,
        inp: L2PropertyInput,
        *,
        run_id: str | None = None,
        mechanism_escalation: bool = False,
    ) -> LayerEnvelope:
        rid = run_id or new_run_id()
        smiles = inp.molecule.smiles
        smiles_check = detect_invalid_smiles(smiles)

        if smiles_check.status == FalsifierStatus.FAIL:
            output: dict[str, Any] = {
                "smiles": smiles,
                "canonical_smiles": "",
                "inchikey": None,
                "descriptors": {},
                "admet_scores": {},
                "liability_flags": [],
                "reward_modifier": 0.0,
                "valid_smiles": False,
            }
            falsifiers = [
                smiles_check,
                detect_stub_laundering(
                    Backend.RUNPOD_GPU.value, "mechanism_claim", mechanism_escalation
                ),
                detect_nan_or_nonfinite([], "l2_runpod_sim_invalid"),
                detect_clinical_overclaim(""),
            ]
            return self._envelope(
                rid,
                output,
                falsifiers,
                confidence_score=0.0,
                confidence_basis=["invalid_input"],
            )

        # Mock GPU-quality descriptors: more precise than the stub
        canonical = smiles  # GPU adapter would canonicalize via RDKit; sim returns input
        mol_weight = _seed(smiles, "mw", lo=200.0, hi=550.0)
        logp = _seed(smiles, "logp", lo=0.5, hi=4.5)
        tpsa = _seed(smiles, "tpsa", lo=40.0, hi=120.0)
        hia_prob = _seed(smiles, "hia", lo=0.65, hi=0.95)

        liability_flags: list[str] = []
        if mol_weight > 500:
            liability_flags.append("lipinski_violation")

        # Reward calculation similar to stub (so plug-swap tests pass)
        feedback = inp.retrosynth_feedback
        reward = 0.6  # GPU adapters report higher base reward
        if feedback is not None and not feedback.routes_found:
            reward -= 0.4
        if feedback is not None and feedback.route_score is not None:
            reward -= (1.0 - feedback.route_score) * 0.2
        reward -= 0.05 * len(liability_flags)
        reward = max(-1.0, min(1.0, reward))

        output = {
            "smiles": smiles,
            "canonical_smiles": canonical,
            "inchikey": inp.molecule.inchikey,
            "descriptors": {
                "mol_weight": mol_weight,
                "logP": logp,
                "tpsa": tpsa,
            },
            "admet_scores": {"hia_prob": hia_prob, "logP": logp, "tpsa": tpsa},
            "liability_flags": liability_flags,
            "reward_modifier": reward,
            "valid_smiles": True,
        }
        falsifiers = [
            smiles_check,
            detect_stub_laundering(
                Backend.RUNPOD_GPU.value, "mechanism_claim", mechanism_escalation
            ),
            detect_nan_or_nonfinite(
                [mol_weight, logp, tpsa, hia_prob, reward], "l2_runpod_sim_descriptors"
            ),
            detect_clinical_overclaim(str(output)),
        ]
        return self._envelope(
            rid,
            output,
            falsifiers,
            confidence_score=0.78,
            confidence_basis=["runpod_deepxde_pinn_descriptors"],
        )

    def _envelope(
        self,
        run_id: str,
        output: dict[str, Any],
        falsifier_items: list[EnvelopeFalsifierItem],
        *,
        confidence_score: float,
        confidence_basis: list[str],
    ) -> LayerEnvelope:
        any_fail = any(it.status == FalsifierStatus.FAIL for it in falsifier_items)
        return LayerEnvelope(
            run_id=run_id,
            layer=LayerName.L2,
            tool_adapter=self._adapter,
            input_refs=[],
            output=output,
            confidence=EnvelopeConfidence(
                score=confidence_score,
                band=ConfidenceBand.HIGH if confidence_score >= 0.7 else ConfidenceBand.MEDIUM,
                basis=confidence_basis,
            ),
            falsifier=EnvelopeFalsifier(
                status=FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS,
                items=falsifier_items,
            ),
            audit=EnvelopeAudit(
                audit_record_id=audit_id(),
                input_hash=sha256_of_obj(output),
                output_hash=sha256_of_obj(output),
            ),
            back_edges=[],
        )
