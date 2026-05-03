"""L2.5 stub adapter — retrosynthesis gate, license-drift detection, atom-map enforcement.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.

Adapter discipline
------------------
- backend = Backend.STUB always
- license_drift check runs FIRST: ASKCOS_REAXYS triggers FAIL + license_flag
- detect_invalid_smiles runs before route generation (fail-fast)
- Canned fixture routes loaded from fixtures/routes/<name>.json when available
- Each step validated with validate_rxnsmiles + validate_atom_map
- detect_missing_rxnsmiles_atommap emitted on the WORST step
- back_edges to L2 is structurally required (Inversion A: L2.5 -> L2 feedback)
- No clinical overclaim language in any field

Known compound routing
----------------------
The three seed compounds are detected by canonical_smiles exact match against
fixture metadata. When matched, the canned fixture route is loaded and used.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from zer0pa_biomolecular_explorer.boundary import RESEARCH_BOUNDARY
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
from zer0pa_biomolecular_explorer.ids import audit_id, falsifier_id, run_id as new_run_id
from zer0pa_biomolecular_explorer.layers.l2_5.validation import validate_atom_map, validate_rxnsmiles

_ADAPTER_NAME = "l2_5-stub"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "stub_retro"

# Allowed non-NC policies for license-drift check
_ALLOWED_POLICIES = [
    L25Policy.AIZYNTHFINDER_DEFAULT.value,
    L25Policy.ASKCOS_USPTO.value,
    L25Policy.ASKCOS_PISTACHIO.value,
    L25Policy.STUB.value,
]

_FIXTURES_DIR = Path(__file__).parent.parent.parent.parent.parent / "fixtures" / "routes"

# Canonical SMILES -> fixture filename mapping (loaded at module import)
_SMILES_TO_FIXTURE: dict[str, str] = {
    "CN(C)S(=O)(=O)c1ccc(NCCOc2ccc(CCN(C)S(=O)(=O)C)cc2)cc1": "dofetilide.json",
    "COc1ccc(CC(C)(C#N)CCCN(C)CCc2ccc(OC)c(OC)c2)cc1OC": "verapamil.json",
    "COc1ccccc1OCC(O)CN1CCN(CC(=O)Nc2c(C)cccc2C)CC1": "ranolazine.json",
}

_FIXTURE_CACHE: dict[str, dict] = {}


def _load_fixture(name: str) -> dict | None:
    """Load a route fixture JSON by filename; returns None if not found."""
    if name in _FIXTURE_CACHE:
        return _FIXTURE_CACHE[name]
    path = _FIXTURES_DIR / name
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    _FIXTURE_CACHE[name] = data
    return data


def _steps_from_fixture(fixture: dict) -> list[L25ReactionStep]:
    """Build L25ReactionStep list from a fixture dict."""
    steps = []
    for s in fixture.get("steps", []):
        steps.append(
            L25ReactionStep(
                rxnsmiles=s["rxnsmiles"],
                atom_mapped_rxnsmiles=s.get("atom_mapped_rxnsmiles"),
                template_smarts=s.get("template_smarts"),
                predicted_yield=None,
                conditions=s.get("conditions", {}),
                step_confidence=float(s["step_confidence"]),
            )
        )
    return steps


def _generic_stub_steps(canonical_smiles: str) -> list[L25ReactionStep]:
    """Generate a generic 2-step toy route.

    Uses a clearly-toy heuristic: starting material is the SMILES substring
    before the first ring-closure digit (or a trimmed version).
    This is explicitly NOT a real retrosynthetic analysis.
    """
    # Toy starting material: first 6 heavy-atom token characters of SMILES
    start_mat = canonical_smiles[:6] if len(canonical_smiles) >= 6 else canonical_smiles
    # Ensure start_mat is not empty; fallback
    if not start_mat.strip():
        start_mat = "C"

    # Step 1: toy reduction step
    step1 = L25ReactionStep(
        rxnsmiles=f"{start_mat}C>>{canonical_smiles[:max(6, len(canonical_smiles)//2)]}",
        atom_mapped_rxnsmiles=f"[CH3:1][CH2:2]>>[CH3:1][CH2:2]",
        template_smarts="[C:1]>>[C:1]",
        predicted_yield=None,
        conditions={"note": "toy_stub_step"},
        step_confidence=0.42,
    )
    # Step 2: toy coupling step
    step2 = L25ReactionStep(
        rxnsmiles=f"{canonical_smiles[:max(6, len(canonical_smiles)//2)]}>>{canonical_smiles}",
        atom_mapped_rxnsmiles=f"[CH3:1][CH2:2]>>[CH3:1][CH2:2]",
        template_smarts="[C:1]>>[C:1]",
        predicted_yield=None,
        conditions={"note": "toy_stub_step"},
        step_confidence=0.42,
    )
    return [step1, step2]


def _compute_route_score(steps: list[L25ReactionStep]) -> float:
    """Compute route_score: average step_confidence * (1 - 0.05*n_steps), clamped to [0,1]."""
    if not steps:
        return 0.0
    avg_conf = sum(s.step_confidence for s in steps) / len(steps)
    penalty = 1.0 - 0.05 * len(steps)
    score = avg_conf * max(0.0, penalty)
    return float(max(0.0, min(1.0, score)))


def _compute_sa_score(canonical_smiles: str) -> float:
    """Deterministic SA score proxy: 1.0 + len(smiles)/30.0, clamped to [1.0, 10.0]."""
    raw = 1.0 + len(canonical_smiles) / 30.0
    return float(max(1.0, min(10.0, raw)))


def _worst_step_atommap_item(
    steps: list[L25ReactionStep],
) -> EnvelopeFalsifierItem:
    """Run detect_missing_rxnsmiles_atommap on all steps; return WORST item (FAIL > PASS)."""
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
        # No steps — emit a FAIL
        worst = detect_missing_rxnsmiles_atommap(None, None, mapping_required=True)
    return worst


class L25StubAdapter:
    """CPU-side stub adapter for L2.5 retrosynthesis.

    Returns canned fixture routes for seed compounds, generic toy routes otherwise.
    Does NOT call AiZynthFinder, ASKCOS, or any network service.

    Swap to a real retrosynthesis backend by replacing this adapter — envelope
    contract is identical.

    process(input, run_id=None) -> LayerEnvelope
    """

    def process(
        self,
        input: L25Input,  # noqa: A002
        run_id: str | None = None,
    ) -> LayerEnvelope:
        """Process an L25Input and return a complete LayerEnvelope.

        Behavior:
          a) license_drift: ASKCOS_REAXYS policy triggers FAIL + license_flag=CC-BY-NC
          b) detect_invalid_smiles: fail-fast if SMILES is invalid
          c) Load canned fixture for known seed compounds; else generic 2-step toy route
          d) validate_rxnsmiles + validate_atom_map on each step; emit WORST atommap item
          e) route_score = avg_step_confidence * (1 - 0.05*n_steps)
          f) sa_score = 1.0 + len(smiles)/30.0 (clamped to [1.0, 10.0])
          g) feedback_to_l2 dict for L2RetrosynthFeedback
          h) back_edge to L2 with feedback_to_l2 payload
        """
        rid = run_id or new_run_id()
        input_dict = input.model_dump()

        items: list[EnvelopeFalsifierItem] = []
        license_flag: str | None = None

        # (a) license_drift check — ASKCOS Reaxys is CC BY-NC 4.0
        license_item = detect_license_drift(
            tool_name="ASKCOS",
            requested_variant=input.policy.value,
            allowed_variants=_ALLOWED_POLICIES,
        )
        items.append(license_item)

        if license_item.status == FalsifierStatus.FAIL:
            license_flag = "CC-BY-NC"

        # (b) SMILES validation — fail-fast
        smiles_item = detect_invalid_smiles(input.canonical_smiles)
        items.append(smiles_item)

        if smiles_item.status == FalsifierStatus.FAIL:
            # Fail-fast: build a minimal failure envelope
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

        # (c) Load fixture or generate generic stub route
        fixture_file = _SMILES_TO_FIXTURE.get(input.canonical_smiles)
        fixture: dict | None = None
        if fixture_file:
            fixture = _load_fixture(fixture_file)

        if fixture:
            steps = _steps_from_fixture(fixture)
            total_steps = fixture.get("total_steps", len(steps))
            starting_material_cost = fixture.get("starting_material_cost_usd", 50.0)
            starting_materials_inchikeys = fixture.get("starting_materials_inchikeys", [])
        else:
            steps = _generic_stub_steps(input.canonical_smiles)
            total_steps = len(steps)
            starting_material_cost = 50.0
            starting_materials_inchikeys = []

        # (d) validate each step; emit worst atommap item
        step_valid_all = True
        for step in steps:
            rxn_ok, rxn_reason = validate_rxnsmiles(step.rxnsmiles)
            if not rxn_ok:
                step_valid_all = False
            if step.atom_mapped_rxnsmiles:
                amap_ok, amap_reason = validate_atom_map(step.atom_mapped_rxnsmiles)
                if not amap_ok:
                    step_valid_all = False

        atommap_item = _worst_step_atommap_item(steps)
        items.append(atommap_item)

        routes_found = step_valid_all and len(steps) > 0

        if atommap_item.status == FalsifierStatus.FAIL:
            routes_found = False

        # (e) route_score
        route_score = _compute_route_score(steps) if routes_found else 0.0

        # (f) sa_score
        sa_score = _compute_sa_score(input.canonical_smiles)

        # Build L25Route
        route = L25Route(
            target_canonical_smiles=input.canonical_smiles,
            steps=steps,
            route_score=route_score,
            sa_score=sa_score,
            total_steps=total_steps,
            starting_materials_inchikeys=starting_materials_inchikeys,
            starting_materials_cost_usd=starting_material_cost,
        )

        # (g) feedback_to_l2 dict
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

        # Confidence band: low if license flag or low route_score; medium otherwise
        if license_flag or route_score < 0.4:
            conf_band = ConfidenceBand.LOW
            conf_score = min(route_score, 0.35)
        else:
            conf_band = ConfidenceBand.MEDIUM
            conf_score = max(0.36, min(route_score, 0.65))

        basis = ["stub_template_routes", "no_real_retro_search"]
        if license_flag:
            basis.append(f"license_flag:{license_flag}")

        # (h) back_edge to L2 with feedback_to_l2
        # Find the atommap or license_drift falsifier_id to attach (use first FAIL, else first item)
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
                "L2.5 retrosynthesis feasibility feedback for L2 scaffold scoring "
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
