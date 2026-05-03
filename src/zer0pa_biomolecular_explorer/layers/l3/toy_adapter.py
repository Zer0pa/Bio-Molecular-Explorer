"""L3 toy adapter — second, deliberately-different stub for plug-replaceability testing.

Same public interface as L3StubAdapter.process() but different unit-op decomposition:
  - Non-final steps: REACTION → BLENDING → DRYING (stub: CRYSTALLIZATION → FILTRATION → DRYING)
  - Final step always has DRYING (same as stub)
  - Same mass-balance enforcement (identical arithmetic)
  - Same back_edges target (L2.5) on mass-balance failure
  - Same falsifier classes emitted

RESEARCH USE ONLY — not for clinical deployment, diagnosis, or prescribing.
"""

from __future__ import annotations

import hashlib
from typing import Any

from zer0pa_biomolecular_explorer.contracts.l3 import (
    L3MaterialFlow,
    L3ProcessInput,
    L3ProcessOutput,
    L3UnitOp,
    L3UnitOpKind,
)
from zer0pa_biomolecular_explorer.envelope import (
    Backend,
    BackEdge,
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
    detect_mass_balance_failure,
)
from zer0pa_biomolecular_explorer.hashing import sha256_of_obj
from zer0pa_biomolecular_explorer.ids import audit_id, run_id as new_run_id
from zer0pa_biomolecular_explorer.layers.l3.process_graph import unit_ops_to_dot

_ADAPTER_NAME = "l3-toy"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "toy_unit_op_blending"

# Same molar-mass assumptions as stub for mass-balance comparability
_STUB_REACTANT_MW = 200.0
_STUB_PRODUCT_MW = 250.0
_YIELD_FACTOR = 0.85

_CARDIAC_SEED_SMILES = {
    "CN(C)S(=O)(=O)c1ccc(NCCOc2ccc(CCN(C)S(=O)(=O)C)cc2)cc1",
    "COc1ccc(CCN(C)CCCC(C#N)(C(C)C)c2ccc(OC)c(OC)c2)cc1OC",
    "COc1ccc(OC)c(OC)c1OCC(=O)NCC(O)CN1CCCC1=O",
}
_CARDIAC_WEDGE_TAG = "cardiac-wedge"


def _hash_seed(rxnsmiles: str, salt: str) -> int:
    digest = hashlib.sha256((rxnsmiles + "|" + salt).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _seed_float(rxnsmiles: str, salt: str, lo: float, hi: float) -> float:
    raw = _hash_seed(rxnsmiles, salt)
    frac = (raw % 100_000) / 100_000.0
    return round(lo + frac * (hi - lo), 3)


def _rxn_parameters(rxnsmiles: str) -> dict[str, float]:
    return {
        "temp_C": _seed_float(rxnsmiles, "toy_temp_C", 25.0, 100.0),   # different range
        "pressure_bar": _seed_float(rxnsmiles, "toy_pressure_bar", 1.0, 4.0),
        "residence_time_h": _seed_float(rxnsmiles, "toy_residence_h", 1.0, 6.0),
    }


def _blending_parameters(rxnsmiles: str) -> dict[str, float]:
    """BLENDING op parameters — toy differentiator vs stub's CRYSTALLIZATION."""
    return {
        "temp_C": _seed_float(rxnsmiles, "toy_blend_temp_C", 15.0, 35.0),
        "pressure_bar": 1.013,
        "residence_time_h": _seed_float(rxnsmiles, "toy_blend_time_h", 0.25, 2.0),
    }


def _dry_parameters(rxnsmiles: str) -> dict[str, float]:
    return {
        "temp_C": _seed_float(rxnsmiles, "toy_dry_temp_C", 45.0, 75.0),
        "pressure_bar": _seed_float(rxnsmiles, "toy_dry_pressure_bar", 0.02, 0.4),
        "residence_time_h": _seed_float(rxnsmiles, "toy_dry_time_h", 1.5, 8.0),
    }


def _parse_rxn_sides(rxnsmiles: str) -> tuple[list[str], list[str]]:
    parts = rxnsmiles.split(">")
    if len(parts) == 3:
        reactants_str, _reagents, products_str = parts
    elif len(parts) == 2:
        reactants_str, products_str = parts
    else:
        reactants_str = rxnsmiles
        products_str = ""
    reactants = [s.strip() for s in reactants_str.split(".") if s.strip()]
    products = [s.strip() for s in products_str.split(".") if s.strip()]
    return reactants, products


def _make_reaction_op(rxnsmiles: str, step_idx: int, throughput_kg: float) -> L3UnitOp:
    reactants, products = _parse_rxn_sides(rxnsmiles)
    if not reactants:
        reactants = ["[*]"]
    if not products:
        products = ["[*]"]

    n_reactants = len(reactants)
    mass_per_reactant = throughput_kg / n_reactants

    inputs: list[L3MaterialFlow] = []
    for smiles in reactants:
        moles = (mass_per_reactant * 1000.0) / _STUB_REACTANT_MW
        inputs.append(
            L3MaterialFlow(
                canonical_smiles=smiles,
                role="reactant",
                moles=round(moles, 6),
                mass_kg=round(mass_per_reactant, 6),
            )
        )

    total_in_kg = throughput_kg
    product_mass_kg = round(total_in_kg * _YIELD_FACTOR, 6)
    waste_mass_kg = round(total_in_kg - product_mass_kg, 6)

    outputs: list[L3MaterialFlow] = []
    product_smiles = products[0] if products else "[*]"
    product_moles = (product_mass_kg * 1000.0) / _STUB_PRODUCT_MW
    outputs.append(
        L3MaterialFlow(
            canonical_smiles=product_smiles,
            role="product",
            moles=round(product_moles, 6),
            mass_kg=product_mass_kg,
        )
    )
    if waste_mass_kg > 0:
        outputs.append(
            L3MaterialFlow(
                canonical_smiles=None,
                role="waste",
                moles=round((waste_mass_kg * 1000.0) / _STUB_REACTANT_MW, 6),
                mass_kg=waste_mass_kg,
            )
        )

    return L3UnitOp(
        kind=L3UnitOpKind.REACTION,
        name=f"step_{step_idx}_reaction",
        inputs=inputs,
        outputs=outputs,
        parameters=_rxn_parameters(rxnsmiles),
    )


def _make_blending_op(
    rxnsmiles: str, step_idx: int, product_mass_kg: float, product_smiles: str
) -> L3UnitOp:
    """BLENDING — pass-through mass (toy differentiator: uses BLENDING not CRYSTALLIZATION)."""
    moles = (product_mass_kg * 1000.0) / _STUB_PRODUCT_MW
    flow = L3MaterialFlow(
        canonical_smiles=product_smiles,
        role="product",
        moles=round(moles, 6),
        mass_kg=round(product_mass_kg, 6),
    )
    return L3UnitOp(
        kind=L3UnitOpKind.BLENDING,
        name=f"step_{step_idx}_blending",
        inputs=[flow],
        outputs=[
            L3MaterialFlow(
                canonical_smiles=product_smiles,
                role="product",
                moles=round(moles, 6),
                mass_kg=round(product_mass_kg, 6),
            )
        ],
        parameters=_blending_parameters(rxnsmiles),
    )


def _make_drying_op(
    rxnsmiles: str, step_idx: int, product_mass_kg: float, product_smiles: str
) -> L3UnitOp:
    """DRYING — pass-through mass (same as stub)."""
    moles = (product_mass_kg * 1000.0) / _STUB_PRODUCT_MW
    flow_in = L3MaterialFlow(
        canonical_smiles=product_smiles,
        role="product",
        moles=round(moles, 6),
        mass_kg=round(product_mass_kg, 6),
    )
    flow_out = L3MaterialFlow(
        canonical_smiles=product_smiles,
        role="product",
        moles=round(moles, 6),
        mass_kg=round(product_mass_kg, 6),
    )
    return L3UnitOp(
        kind=L3UnitOpKind.DRYING,
        name=f"step_{step_idx}_drying",
        inputs=[flow_in],
        outputs=[flow_out],
        parameters=_dry_parameters(rxnsmiles),
    )


def _op_residual_kg(op: L3UnitOp) -> float:
    in_kg = sum(f.mass_kg for f in op.inputs)
    out_kg = sum(f.mass_kg for f in op.outputs)
    return abs(in_kg - out_kg)


def _assess_cpp_cqa_risks(
    unit_ops: list[L3UnitOp], target_smiles: str, run_id: str
) -> list[str]:
    risks: list[str] = []
    kinds = {op.kind for op in unit_ops}

    # Toy uses BLENDING instead of CRYSTALLIZATION → no polymorph_risk
    # (this is a deliberate value difference; schema is same: list[str])
    if L3UnitOpKind.BLENDING in kinds:
        risks.append("blending_uniformity_risk")  # toy-specific risk label

    if L3UnitOpKind.DRYING in kinds:
        risks.append("drying_temperature_sensitive")  # same as stub

    is_cardiac_seed = target_smiles in _CARDIAC_SEED_SMILES
    is_cardiac_run = _CARDIAC_WEDGE_TAG in run_id
    if is_cardiac_seed and is_cardiac_run:
        risks.append("hERG_specific_risk")

    return risks


class L3ToyAdapter:
    """L3 toy adapter — BLENDING+DRYING instead of CRYSTALLIZATION+FILTRATION+DRYING.

    process(input, run_id=None) -> LayerEnvelope
    Same interface as L3StubAdapter.

    Toy differentiators:
      - Unit-op chain per rxnsmiles: REACTION → BLENDING → DRYING (stub: REACTION → CRYST → FILT → DRYING)
      - CPP/CQA risks: "blending_uniformity_risk" instead of "polymorph_risk" for non-crystallization
      - Different parameter ranges for REACTION and DRYING ops
    """

    def process(
        self,
        input: L3ProcessInput,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        rid = run_id or new_run_id()
        input_dict = input.model_dump()

        falsifier_items: list[EnvelopeFalsifierItem] = []

        # 1. Validate target SMILES
        smiles_item = detect_invalid_smiles(input.target_canonical_smiles)
        falsifier_items.append(smiles_item)

        if smiles_item.status == FalsifierStatus.FAIL:
            output_dict: dict[str, Any] = {
                "target_canonical_smiles": input.target_canonical_smiles,
                "unit_ops": [],
                "mass_balance_residual_kg": 0.0,
                "mass_balance_ok": False,
                "cpp_cqa_risks": [],
                "process_graph_dot": None,
            }
            return self._build_envelope(
                rid=rid,
                input_dict=input_dict,
                output_dict=output_dict,
                falsifier_items=falsifier_items,
                back_edges=[],
                confidence_score=0.0,
            )

        # 2. Expand each rxnsmiles into 3 unit ops: REACTION → BLENDING → DRYING
        unit_ops: list[L3UnitOp] = []
        throughput = input.target_throughput_kg_per_batch

        for step_idx, rxnsmiles in enumerate(input.route_rxnsmiles):
            rxn_op = _make_reaction_op(rxnsmiles, step_idx, throughput)
            unit_ops.append(rxn_op)

            product_flows = [f for f in rxn_op.outputs if f.role == "product"]
            product_mass_kg = sum(f.mass_kg for f in product_flows)
            product_smiles = (
                product_flows[0].canonical_smiles
                if product_flows and product_flows[0].canonical_smiles
                else input.target_canonical_smiles
            )

            unit_ops.append(_make_blending_op(rxnsmiles, step_idx, product_mass_kg, product_smiles))
            unit_ops.append(_make_drying_op(rxnsmiles, step_idx, product_mass_kg, product_smiles))

        # 3. Mass balance residual
        mass_balance_residual_kg = sum(_op_residual_kg(op) for op in unit_ops)

        total_in_kg = sum(
            sum(f.mass_kg for f in op.inputs)
            for op in unit_ops
            if op.kind == L3UnitOpKind.REACTION
        )
        total_out_kg = sum(
            sum(f.mass_kg for f in op.outputs)
            for op in unit_ops
            if op.kind == L3UnitOpKind.REACTION
        )
        mb_item = detect_mass_balance_failure(total_in_kg, total_out_kg, tolerance=1e-3)
        falsifier_items.append(mb_item)

        mass_balance_ok = mb_item.status == FalsifierStatus.PASS

        # 4. CPP/CQA risks
        cpp_cqa_risks = _assess_cpp_cqa_risks(unit_ops, input.target_canonical_smiles, rid)

        # 5. Process graph DOT
        process_graph_dot = unit_ops_to_dot(unit_ops)

        # 6. Build output
        process_output = L3ProcessOutput(
            target_canonical_smiles=input.target_canonical_smiles,
            unit_ops=unit_ops,
            mass_balance_residual_kg=round(mass_balance_residual_kg, 9),
            mass_balance_ok=mass_balance_ok,
            cpp_cqa_risks=cpp_cqa_risks,
            process_graph_dot=process_graph_dot,
        )
        output_dict = process_output.model_dump()

        # 7. Back-edges
        back_edges: list[BackEdge] = []
        if not mass_balance_ok:
            back_edges.append(
                BackEdge(
                    target_layer=LayerName.L2_5,
                    reason="L3 toy: mass balance failure — route is unmanufacturable at given throughput",
                    proposed_constraint={"reject_route": True},
                    triggered_by_falsifier_id=mb_item.falsifier_id,
                )
            )

        conf_score = 0.52 if mass_balance_ok else 0.40

        return self._build_envelope(
            rid=rid,
            input_dict=input_dict,
            output_dict=output_dict,
            falsifier_items=falsifier_items,
            back_edges=back_edges,
            confidence_score=conf_score,
        )

    def _build_envelope(
        self,
        *,
        rid: str,
        input_dict: dict[str, Any],
        output_dict: dict[str, Any],
        falsifier_items: list[EnvelopeFalsifierItem],
        back_edges: list[BackEdge],
        confidence_score: float,
    ) -> LayerEnvelope:
        any_fail = any(item.status == FalsifierStatus.FAIL for item in falsifier_items)
        falsifier_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS

        band = ConfidenceBand.MEDIUM if confidence_score >= 0.5 else ConfidenceBand.LOW

        return LayerEnvelope(
            run_id=rid,
            layer=LayerName.L3,
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
                band=band,
                basis=[
                    "toy_unit_op_blending_decomposition",
                    "deterministic_molar_mass_assumptions",
                ],
            ),
            falsifier=EnvelopeFalsifier(
                status=falsifier_status,
                items=falsifier_items,
            ),
            audit=EnvelopeAudit(
                audit_record_id=audit_id(),
                input_hash=sha256_of_obj(input_dict),
                output_hash=sha256_of_obj(output_dict),
                source_manifest_refs=[],
            ),
            back_edges=back_edges,
        )
