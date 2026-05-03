"""L3 stub adapter — process development / flowsheet layer.

Every rxnsmiles step expands into a deterministic chain:
    [REACTION -> CRYSTALLIZATION -> FILTRATION -> DRYING]

Mass balance discipline
-----------------------
- Each REACTION unit op: inputs sum to throughput_per_step_kg (reactants).
  Output product mass = sum_reactant_mass * 0.85 (15% to waste/impurity).
  The waste output accounts for the missing 15%, so the per-op balance holds.
- CRYSTALLIZATION, FILTRATION, DRYING pass-through: inputs == outputs.
  (Downstream ops carry the same product mass forward; no additional loss.)
- mass_balance_residual_kg = sum(|in_kg - out_kg|) across ALL unit ops.
  With this design residuals are 0.0 (exact arithmetic), well within 1e-3/op.
- The detect_mass_balance_failure falsifier is run on TOTALS
  (sum of all reactant inputs vs sum of all product+waste outputs).

Back-edge discipline
--------------------
- If mass_balance_ok is False, a back_edge to L2.5 is emitted with
  proposed_constraint={"reject_route": True}.

CPP/CQA risks
-------------
- "polymorph_risk"  — any crystallisation step
- "drying_temperature_sensitive"  — any drying step
- "hERG_specific_risk"  — only if target SMILES matches the cardiac-wedge
  seed compounds (dofetilide/verapamil/ranolazine) AND the run_id carries
  the "cardiac-wedge" tag.

Determinism
-----------
Same (target_canonical_smiles, route_rxnsmiles, throughput) always yields
the same output_hash. Parameters inside each unit op are derived from a
sha256 hash of the rxnsmiles, clipped to a realistic physical range.
"""

from __future__ import annotations

import hashlib
from typing import Any

from zer0pa_biomolecular_explorer.boundary import RESEARCH_BOUNDARY
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
from zer0pa_biomolecular_explorer.ids import audit_id
from zer0pa_biomolecular_explorer.ids import run_id as new_run_id
from zer0pa_biomolecular_explorer.layers.l3.process_graph import unit_ops_to_dot

_ADAPTER_NAME = "l3-stub"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "stub_unit_op_decomposition"

# Stub molar masses (g/mol) per PRD spec
_STUB_REACTANT_MW = 200.0   # g/mol
_STUB_PRODUCT_MW = 250.0    # g/mol
_YIELD_FACTOR = 0.85        # 15% to waste/impurity

# Cardiac-wedge seed SMILES (research label only; no clinical claim)
_CARDIAC_SEED_SMILES = {
    # dofetilide
    "CN(C)S(=O)(=O)c1ccc(NCCOc2ccc(CCN(C)S(=O)(=O)C)cc2)cc1",
    # verapamil
    "COc1ccc(CCN(C)CCCC(C#N)(C(C)C)c2ccc(OC)c(OC)c2)cc1OC",
    # ranolazine
    "COc1ccc(OC)c(OC)c1OCC(=O)NCC(O)CN1CCCC1=O",
}

# Cardiac-wedge run tag — present when run_id contains this substring
_CARDIAC_WEDGE_TAG = "cardiac-wedge"


# ---------------------------------------------------------------------------
# Deterministic parameter seeding
# ---------------------------------------------------------------------------

def _hash_seed(rxnsmiles: str, salt: str) -> int:
    """Return a deterministic 64-bit integer from rxnsmiles + salt."""
    digest = hashlib.sha256((rxnsmiles + "|" + salt).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _seed_float(rxnsmiles: str, salt: str, lo: float, hi: float) -> float:
    """Return a deterministic float in [lo, hi]."""
    raw = _hash_seed(rxnsmiles, salt)
    frac = (raw % 100_000) / 100_000.0
    return round(lo + frac * (hi - lo), 3)


def _rxn_parameters(rxnsmiles: str) -> dict[str, float]:
    """Deterministic stub parameters for a REACTION unit op."""
    return {
        "temp_C": _seed_float(rxnsmiles, "temp_C", 20.0, 120.0),
        "pressure_bar": _seed_float(rxnsmiles, "pressure_bar", 1.0, 5.0),
        "residence_time_h": _seed_float(rxnsmiles, "residence_time_h", 0.5, 8.0),
    }


def _cryst_parameters(rxnsmiles: str) -> dict[str, float]:
    return {
        "temp_C": _seed_float(rxnsmiles, "cryst_temp_C", 0.0, 20.0),
        "pressure_bar": 1.013,
        "residence_time_h": _seed_float(rxnsmiles, "cryst_time_h", 1.0, 6.0),
    }


def _filt_parameters(rxnsmiles: str) -> dict[str, float]:
    return {
        "temp_C": _seed_float(rxnsmiles, "filt_temp_C", 5.0, 30.0),
        "pressure_bar": _seed_float(rxnsmiles, "filt_pressure_bar", 0.5, 2.0),
        "residence_time_h": _seed_float(rxnsmiles, "filt_time_h", 0.1, 1.0),
    }


def _dry_parameters(rxnsmiles: str) -> dict[str, float]:
    return {
        "temp_C": _seed_float(rxnsmiles, "dry_temp_C", 40.0, 80.0),
        "pressure_bar": _seed_float(rxnsmiles, "dry_pressure_bar", 0.01, 0.5),
        "residence_time_h": _seed_float(rxnsmiles, "dry_time_h", 2.0, 12.0),
    }


# ---------------------------------------------------------------------------
# SMILES fragment extraction
# ---------------------------------------------------------------------------

def _parse_rxn_sides(rxnsmiles: str) -> tuple[list[str], list[str]]:
    """Split 'A.B>>C' or 'A.B>reagents>C' into (reactant_list, product_list).

    Returns lists of non-empty SMILES strings from the left and right sides.
    """
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


# ---------------------------------------------------------------------------
# Unit op construction
# ---------------------------------------------------------------------------

def _make_reaction_op(
    rxnsmiles: str,
    step_idx: int,
    throughput_kg: float,
) -> L3UnitOp:
    """REACTION unit op with deterministic mass balance.

    N reactants each receive throughput_kg/N as input.
    Product mass = total_in * 0.85; waste mass = total_in * 0.15.
    Per-op residual = 0.0 (exact by construction).
    """
    reactants, products = _parse_rxn_sides(rxnsmiles)
    if not reactants:
        reactants = ["[*]"]    # fallback fragment
    if not products:
        products = ["[*]"]

    n_reactants = len(reactants)
    mass_per_reactant = throughput_kg / n_reactants

    inputs: list[L3MaterialFlow] = []
    for smiles in reactants:
        moles = (mass_per_reactant * 1000.0) / _STUB_REACTANT_MW  # kg -> g -> mol
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
    # Use first product SMILES if available, else canonical target fragment
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


def _make_crystallization_op(
    rxnsmiles: str,
    step_idx: int,
    product_mass_kg: float,
    product_smiles: str,
) -> L3UnitOp:
    """CRYSTALLIZATION — pass-through mass (no further losses in stub)."""
    moles = (product_mass_kg * 1000.0) / _STUB_PRODUCT_MW
    flow = L3MaterialFlow(
        canonical_smiles=product_smiles,
        role="product",
        moles=round(moles, 6),
        mass_kg=round(product_mass_kg, 6),
    )
    return L3UnitOp(
        kind=L3UnitOpKind.CRYSTALLIZATION,
        name=f"step_{step_idx}_crystallization",
        inputs=[flow],
        outputs=[L3MaterialFlow(
            canonical_smiles=product_smiles,
            role="product",
            moles=round(moles, 6),
            mass_kg=round(product_mass_kg, 6),
        )],
        parameters=_cryst_parameters(rxnsmiles),
    )


def _make_filtration_op(
    rxnsmiles: str,
    step_idx: int,
    product_mass_kg: float,
    product_smiles: str,
) -> L3UnitOp:
    """FILTRATION — pass-through mass."""
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
        kind=L3UnitOpKind.FILTRATION,
        name=f"step_{step_idx}_filtration",
        inputs=[flow_in],
        outputs=[flow_out],
        parameters=_filt_parameters(rxnsmiles),
    )


def _make_drying_op(
    rxnsmiles: str,
    step_idx: int,
    product_mass_kg: float,
    product_smiles: str,
) -> L3UnitOp:
    """DRYING — pass-through mass."""
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


# ---------------------------------------------------------------------------
# Residual computation
# ---------------------------------------------------------------------------

def _op_residual_kg(op: L3UnitOp) -> float:
    """Absolute |inputs_kg - outputs_kg| for a single unit op."""
    in_kg = sum(f.mass_kg for f in op.inputs)
    out_kg = sum(f.mass_kg for f in op.outputs)
    return abs(in_kg - out_kg)


# ---------------------------------------------------------------------------
# CPP/CQA risk assessment
# ---------------------------------------------------------------------------

def _assess_cpp_cqa_risks(
    unit_ops: list[L3UnitOp],
    target_smiles: str,
    run_id: str,
) -> list[str]:
    risks: list[str] = []
    kinds = {op.kind for op in unit_ops}

    if L3UnitOpKind.CRYSTALLIZATION in kinds:
        risks.append("polymorph_risk")

    if L3UnitOpKind.DRYING in kinds:
        risks.append("drying_temperature_sensitive")

    # hERG_specific_risk only for cardiac-wedge seed compounds with cardiac tag
    is_cardiac_seed = target_smiles in _CARDIAC_SEED_SMILES
    is_cardiac_run = _CARDIAC_WEDGE_TAG in run_id
    if is_cardiac_seed and is_cardiac_run:
        risks.append("hERG_specific_risk")

    return risks


# ---------------------------------------------------------------------------
# Main adapter
# ---------------------------------------------------------------------------

class L3StubAdapter:
    """CPU-side stub adapter for L3 process development / flowsheet.

    process(input, run_id=None) -> LayerEnvelope

    Behavior
    --------
    1. Validate target_canonical_smiles via detect_invalid_smiles.
    2. Each rxnsmiles becomes [REACTION, CRYSTALLIZATION, FILTRATION, DRYING].
    3. Parameters are deterministic (seeded from sha256(rxnsmiles)).
    4. Mass balance is exact by construction; detect_mass_balance_failure is
       run on the grand total (all reactant inputs vs all product+waste outputs).
    5. Back-edge to L2.5 is emitted iff mass_balance_ok == False.
    6. Confidence in 0.4–0.7 range; basis includes stub provenance labels.
    """

    def process(
        self,
        input: L3ProcessInput,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        rid = run_id or new_run_id()
        input_dict = input.model_dump()

        falsifier_items: list[EnvelopeFalsifierItem] = []

        # ------------------------------------------------------------------
        # 1. Validate target SMILES — fail-fast
        # ------------------------------------------------------------------
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

        # ------------------------------------------------------------------
        # 2. Expand each rxnsmiles into 4 unit ops
        # ------------------------------------------------------------------
        unit_ops: list[L3UnitOp] = []
        throughput = input.target_throughput_kg_per_batch

        for step_idx, rxnsmiles in enumerate(input.route_rxnsmiles):
            rxn_op = _make_reaction_op(rxnsmiles, step_idx, throughput)
            unit_ops.append(rxn_op)

            # Extract product mass and SMILES from reaction output
            product_flows = [f for f in rxn_op.outputs if f.role == "product"]
            product_mass_kg = sum(f.mass_kg for f in product_flows)
            product_smiles = (
                product_flows[0].canonical_smiles
                if product_flows and product_flows[0].canonical_smiles
                else input.target_canonical_smiles
            )

            unit_ops.append(_make_crystallization_op(rxnsmiles, step_idx, product_mass_kg, product_smiles))
            unit_ops.append(_make_filtration_op(rxnsmiles, step_idx, product_mass_kg, product_smiles))
            unit_ops.append(_make_drying_op(rxnsmiles, step_idx, product_mass_kg, product_smiles))

        # ------------------------------------------------------------------
        # 3. Mass balance residual
        # ------------------------------------------------------------------
        mass_balance_residual_kg = sum(_op_residual_kg(op) for op in unit_ops)

        # Also compute grand-total for the falsifier
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

        # ------------------------------------------------------------------
        # 4. CPP/CQA risks
        # ------------------------------------------------------------------
        cpp_cqa_risks = _assess_cpp_cqa_risks(unit_ops, input.target_canonical_smiles, rid)

        # ------------------------------------------------------------------
        # 5. Process graph DOT
        # ------------------------------------------------------------------
        process_graph_dot = unit_ops_to_dot(unit_ops)

        # ------------------------------------------------------------------
        # 6. Build output
        # ------------------------------------------------------------------
        process_output = L3ProcessOutput(
            target_canonical_smiles=input.target_canonical_smiles,
            unit_ops=unit_ops,
            mass_balance_residual_kg=round(mass_balance_residual_kg, 9),
            mass_balance_ok=mass_balance_ok,
            cpp_cqa_risks=cpp_cqa_risks,
            process_graph_dot=process_graph_dot,
        )
        output_dict = process_output.model_dump()

        # ------------------------------------------------------------------
        # 7. Back-edges
        # ------------------------------------------------------------------
        back_edges: list[BackEdge] = []
        if not mass_balance_ok:
            back_edges.append(
                BackEdge(
                    target_layer=LayerName.L2_5,
                    reason="L3 mass balance failure: route is unmanufacturable at given throughput",
                    proposed_constraint={"reject_route": True},
                    triggered_by_falsifier_id=mb_item.falsifier_id,
                )
            )

        # ------------------------------------------------------------------
        # 8. Confidence
        # ------------------------------------------------------------------
        # Score in 0.4–0.7 range; penalise if mass balance fails
        conf_score = 0.55 if mass_balance_ok else 0.42

        return self._build_envelope(
            rid=rid,
            input_dict=input_dict,
            output_dict=output_dict,
            falsifier_items=falsifier_items,
            back_edges=back_edges,
            confidence_score=conf_score,
        )

    # ------------------------------------------------------------------
    # Internal envelope builder
    # ------------------------------------------------------------------

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

        if confidence_score >= 0.6:
            band = ConfidenceBand.MEDIUM
        elif confidence_score >= 0.4:
            band = ConfidenceBand.LOW
        else:
            band = ConfidenceBand.LOW

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
                    "stub_unit_op_decomposition",
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
