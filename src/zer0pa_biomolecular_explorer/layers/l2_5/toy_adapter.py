"""L2.5 toy adapter — second, deliberately-different stub for plug-replaceability testing.

Same public interface as L25StubAdapter.process() but different route_score formula:
  - Base: 0.55 (stub uses avg_step_confidence * (1 - 0.05*n_steps))
  - Toy formula: 0.55 * (1 - 0.03 * step_count) (different penalty factor)
  - Same back_edges target (L2)
  - Same feedback_to_l2 keys
  - Same falsifier classes emitted

RESEARCH USE ONLY — not for clinical deployment, diagnosis, or prescribing.
"""

from __future__ import annotations

from typing import Any

from zer0pa_biomolecular_explorer.contracts.l2_5 import (
    L25Input,
    L25Output,
    L25Policy,
    L25ReactionStep,
    L25Route,
)
from zer0pa_biomolecular_explorer.envelope import (
    BackEdge,
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
    detect_invalid_smiles,
    detect_license_drift,
    detect_missing_rxnsmiles_atommap,
)
from zer0pa_biomolecular_explorer.hashing import sha256_of_obj
from zer0pa_biomolecular_explorer.ids import audit_id, run_id as new_run_id
from zer0pa_biomolecular_explorer.layers.l2_5.validation import validate_atom_map, validate_rxnsmiles

_ADAPTER_NAME = "l2_5-toy"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "toy_retro_v0"

_ALLOWED_POLICIES = [
    L25Policy.AIZYNTHFINDER_DEFAULT.value,
    L25Policy.ASKCOS_USPTO.value,
    L25Policy.ASKCOS_PISTACHIO.value,
    L25Policy.STUB.value,
]


def _toy_generic_steps(canonical_smiles: str) -> list[L25ReactionStep]:
    """Generate a generic 3-step toy route (different from stub's 2-step).

    Toy differentiator: 3 steps instead of 2.
    """
    start_mat = canonical_smiles[:6] if len(canonical_smiles) >= 6 else canonical_smiles
    if not start_mat.strip():
        start_mat = "C"

    mid_smiles = canonical_smiles[:max(6, len(canonical_smiles) // 2)]

    step1 = L25ReactionStep(
        rxnsmiles=f"{start_mat}C>>{mid_smiles}",
        atom_mapped_rxnsmiles="[CH3:1][CH2:2]>>[CH3:1][CH2:2]",
        template_smarts="[C:1]>>[C:1]",
        predicted_yield=None,
        conditions={"note": "toy_step_1"},
        step_confidence=0.50,  # different from stub (0.42)
    )
    step2 = L25ReactionStep(
        rxnsmiles=f"{mid_smiles}>>{mid_smiles}O",
        atom_mapped_rxnsmiles="[CH3:1][CH2:2]>>[CH3:1][CH2:2]",
        template_smarts="[C:1]>>[C:1]",
        predicted_yield=None,
        conditions={"note": "toy_step_2"},
        step_confidence=0.48,
    )
    step3 = L25ReactionStep(
        rxnsmiles=f"{mid_smiles}O>>{canonical_smiles}",
        atom_mapped_rxnsmiles="[CH3:1][CH2:2]>>[CH3:1][CH2:2]",
        template_smarts="[C:1]>>[C:1]",
        predicted_yield=None,
        conditions={"note": "toy_step_3"},
        step_confidence=0.45,
    )
    return [step1, step2, step3]


def _compute_toy_route_score(steps: list[L25ReactionStep]) -> float:
    """TOY route_score formula: 0.55 × (1 - 0.03 × n_steps), clamped [0,1].

    Stub formula: avg_step_confidence × (1 - 0.05 × n_steps)
    Toy formula:  0.55 × (1 - 0.03 × n_steps)  [different base + penalty]
    """
    if not steps:
        return 0.0
    penalty = 1.0 - 0.03 * len(steps)  # different penalty factor (stub: 0.05)
    score = 0.55 * max(0.0, penalty)   # different base (stub: avg_step_confidence)
    return float(max(0.0, min(1.0, score)))


def _compute_sa_score(canonical_smiles: str) -> float:
    """Same SA score proxy as stub: 1.0 + len(smiles)/30.0, clamped [1.0, 10.0]."""
    raw = 1.0 + len(canonical_smiles) / 30.0
    return float(max(1.0, min(10.0, raw)))


def _worst_step_atommap_item(steps: list[L25ReactionStep]) -> EnvelopeFalsifierItem:
    worst: EnvelopeFalsifierItem | None = None
    for step in steps:
        item = detect_missing_rxnsmiles_atommap(
            rxnsmiles=step.rxnsmiles,
            atom_mapped=step.atom_mapped_rxnsmiles,
            mapping_required=True,
        )
        if worst is None or (
            item.status == FalsifierStatus.FAIL and worst.status != FalsifierStatus.FAIL
        ):
            worst = item
    if worst is None:
        worst = detect_missing_rxnsmiles_atommap(None, None, mapping_required=True)
    return worst


class L25ToyAdapter:
    """L2.5 toy adapter — different route_score formula, identical schema.

    process(input, run_id=None) -> LayerEnvelope
    Same interface as L25StubAdapter.
    """

    def process(
        self,
        input: L25Input,  # noqa: A002
        run_id: str | None = None,
    ) -> LayerEnvelope:
        rid = run_id or new_run_id()
        input_dict = input.model_dump()

        items: list[EnvelopeFalsifierItem] = []
        license_flag: str | None = None

        # (a) license_drift check
        license_item = detect_license_drift(
            tool_name="ASKCOS",
            requested_variant=input.policy.value,
            allowed_variants=_ALLOWED_POLICIES,
        )
        items.append(license_item)

        if license_item.status == FalsifierStatus.FAIL:
            license_flag = "CC-BY-NC"

        # (b) SMILES validation
        smiles_item = detect_invalid_smiles(input.canonical_smiles)
        items.append(smiles_item)

        if smiles_item.status == FalsifierStatus.FAIL:
            output_dict = self._failure_output(
                canonical_smiles=input.canonical_smiles,
                policy=input.policy,
                license_flag=license_flag,
                reason="invalid_molecular_input",
            )
            return self._build_envelope(
                rid=rid,
                input_dict=input_dict,
                output_dict=output_dict,
                items=items,
                route_score=0.0,
                license_flag=license_flag,
            )

        # (c) Generate toy 3-step route
        steps = _toy_generic_steps(input.canonical_smiles)
        total_steps = len(steps)
        starting_material_cost = 60.0  # different from stub (50.0)
        starting_materials_inchikeys: list[str] = []

        # (d) validate steps; emit worst atommap item
        step_valid_all = True
        for step in steps:
            rxn_ok, _ = validate_rxnsmiles(step.rxnsmiles)
            if not rxn_ok:
                step_valid_all = False
            if step.atom_mapped_rxnsmiles:
                amap_ok, _ = validate_atom_map(step.atom_mapped_rxnsmiles)
                if not amap_ok:
                    step_valid_all = False

        atommap_item = _worst_step_atommap_item(steps)
        items.append(atommap_item)

        routes_found = step_valid_all and len(steps) > 0
        if atommap_item.status == FalsifierStatus.FAIL:
            routes_found = False

        # (e) TOY route_score
        route_score = _compute_toy_route_score(steps) if routes_found else 0.0

        # (f) sa_score
        sa_score = _compute_sa_score(input.canonical_smiles)

        route = L25Route(
            target_canonical_smiles=input.canonical_smiles,
            steps=steps,
            route_score=route_score,
            sa_score=sa_score,
            total_steps=total_steps,
            starting_materials_inchikeys=starting_materials_inchikeys,
            starting_materials_cost_usd=starting_material_cost,
        )

        # (g) feedback_to_l2 — SAME KEYS as stub
        feedback_to_l2: dict[str, float] = {
            "route_score": round(route_score, 4),
            "route_depth": float(total_steps),
            "sa_score": round(sa_score, 4),
            "starting_material_cost_usd": float(starting_material_cost),
            "routes_found": 1.0 if routes_found else 0.0,
        }

        output = L25Output(
            target_canonical_smiles=input.canonical_smiles,
            routes=[route] if routes_found else [],
            routes_found=routes_found,
            policy_used=input.policy,
            license_flag=license_flag,
            feedback_to_l2=feedback_to_l2,
        )
        output_dict = output.model_dump()

        return self._build_envelope(
            rid=rid,
            input_dict=input_dict,
            output_dict=output_dict,
            items=items,
            route_score=route_score,
            license_flag=license_flag,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _failure_output(
        self,
        canonical_smiles: str,
        policy: L25Policy,
        license_flag: str | None,
        reason: str,
    ) -> dict[str, Any]:
        feedback_to_l2: dict[str, float] = {
            "route_score": 0.0,
            "route_depth": 0.0,
            "sa_score": 1.0,
            "starting_material_cost_usd": 0.0,
            "routes_found": 0.0,
        }
        return {
            "target_canonical_smiles": canonical_smiles,
            "routes": [],
            "routes_found": False,
            "policy_used": policy.value,
            "license_flag": license_flag,
            "feedback_to_l2": feedback_to_l2,
            "failure_reason": reason,
        }

    def _build_envelope(
        self,
        *,
        rid: str,
        input_dict: dict[str, Any],
        output_dict: dict[str, Any],
        items: list[EnvelopeFalsifierItem],
        route_score: float,
        license_flag: str | None,
    ) -> LayerEnvelope:
        any_fail = any(item.status == FalsifierStatus.FAIL for item in items)
        falsifier_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS

        if license_flag or route_score < 0.4:
            conf_band = ConfidenceBand.LOW
            conf_score = min(route_score, 0.35)
        else:
            conf_band = ConfidenceBand.MEDIUM
            conf_score = max(0.36, min(route_score, 0.65))

        basis = ["toy_template_routes", "no_real_retro_search"]
        if license_flag:
            basis.append(f"license_flag:{license_flag}")

        back_edge_falsifier_id: str | None = None
        for _item in items:
            if _item.status == FalsifierStatus.FAIL:
                back_edge_falsifier_id = _item.falsifier_id
                break
        if back_edge_falsifier_id is None and items:
            back_edge_falsifier_id = items[-1].falsifier_id

        feedback = output_dict.get("feedback_to_l2", {})
        back_edge = BackEdge(
            target_layer=LayerName.L2,
            reason=(
                "L2.5 toy retrosynthesis feasibility feedback for L2 scaffold scoring "
                "(Inversion A: back-edge before forward pass)"
            ),
            proposed_constraint={"feedback_to_l2": feedback},
            triggered_by_falsifier_id=back_edge_falsifier_id,
        )

        return LayerEnvelope(
            run_id=rid,
            layer=LayerName.L2_5,
            tool_adapter=ToolAdapter(
                name=_ADAPTER_NAME,
                version=_ADAPTER_VERSION,
                backend=Backend.STUB,
                engine=_ENGINE,
            ),
            input_refs=[],
            output=output_dict,
            confidence=EnvelopeConfidence(
                score=conf_score,
                band=conf_band,
                basis=basis,
            ),
            falsifier=EnvelopeFalsifier(
                status=falsifier_status,
                items=items,
            ),
            audit=EnvelopeAudit(
                audit_record_id=audit_id(),
                input_hash=sha256_of_obj(input_dict),
                output_hash=sha256_of_obj(output_dict),
                source_manifest_refs=[],
            ),
            back_edges=[back_edge],
        )
