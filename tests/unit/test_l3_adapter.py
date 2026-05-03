"""Unit tests for L3StubAdapter and process_graph.

Tests cover:
- process(target="CCO", route=["[CH4:1]>>[CH3:1]O"], throughput=1.0) produces
  at least 4 unit ops (REACTION -> CRYSTALLIZATION -> FILTRATION -> DRYING).
- mass_balance_residual_kg < 1e-3 on the deterministic stub.
- Multi-step route (3 rxnsmiles) yields exactly 12 unit ops.
- Invalid target SMILES "C C" returns FAIL envelope.
- Forced mass-balance break triggers MASS_BALANCE_FAILURE FAIL and a back_edge to L2.5.
- process_graph.py: DOT output contains "digraph" header and at least one "->" edge.
- Envelope validates against the canonical JSON Schema (layer-envelope-v1.json).
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from zer0pa_biomolecular_explorer.contracts.l3 import L3ProcessInput, L3UnitOp, L3UnitOpKind
from zer0pa_biomolecular_explorer.envelope import FalsifierStatus, LayerName
from zer0pa_biomolecular_explorer.falsifiers.registry import FalsifierClass
from zer0pa_biomolecular_explorer.layers.l3 import L3StubAdapter
from zer0pa_biomolecular_explorer.layers.l3.process_graph import unit_ops_to_dot

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent / "schemas" / "envelope" / "layer-envelope-v1.json"
)

_SIMPLE_TARGET = "CCO"
_SIMPLE_ROUTE = ["[CH4:1]>>[CH3:1]O"]
_MULTI_ROUTE = [
    "[CH4:1]>>[CH3:1]O",
    "[CH3:1]O.[Br:2][CH3:3]>>[CH3:1]O[CH3:3]",
    "[c:1]1[cH:2][cH:3][cH:4][cH:5][cH:6]1>>[c:1]1[cH:2][cH:3][cH:4][cH:5][cH:6]1O",
]


@pytest.fixture(scope="module")
def adapter() -> L3StubAdapter:
    return L3StubAdapter()


@pytest.fixture(scope="module")
def envelope_schema() -> dict:
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


def _validate_envelope(env_dict: dict, schema: dict) -> None:
    jsonschema.validate(instance=env_dict, schema=schema)


# ---------------------------------------------------------------------------
# Test 1: single-step route produces >= 4 unit ops (REACTION, CRYST, FILT, DRY)
# ---------------------------------------------------------------------------

def test_single_step_produces_four_unit_ops(adapter: L3StubAdapter, envelope_schema: dict) -> None:
    inp = L3ProcessInput(
        target_canonical_smiles=_SIMPLE_TARGET,
        route_rxnsmiles=_SIMPLE_ROUTE,
        target_throughput_kg_per_batch=1.0,
    )
    env = adapter.process(inp)

    unit_ops = env.output["unit_ops"]
    assert len(unit_ops) >= 4, f"Expected >= 4 unit ops, got {len(unit_ops)}"

    kinds = [op["kind"] for op in unit_ops]
    assert "reaction" in kinds
    assert "crystallization" in kinds
    assert "filtration" in kinds
    assert "drying" in kinds


def test_single_step_op_sequence_order(adapter: L3StubAdapter) -> None:
    inp = L3ProcessInput(
        target_canonical_smiles=_SIMPLE_TARGET,
        route_rxnsmiles=_SIMPLE_ROUTE,
        target_throughput_kg_per_batch=1.0,
    )
    env = adapter.process(inp)
    kinds = [op["kind"] for op in env.output["unit_ops"]]
    assert kinds[:4] == ["reaction", "crystallization", "filtration", "drying"]


# ---------------------------------------------------------------------------
# Test 2: mass_balance_residual_kg is within tolerance
# ---------------------------------------------------------------------------

def test_mass_balance_residual_within_tolerance(adapter: L3StubAdapter) -> None:
    inp = L3ProcessInput(
        target_canonical_smiles=_SIMPLE_TARGET,
        route_rxnsmiles=_SIMPLE_ROUTE,
        target_throughput_kg_per_batch=1.0,
    )
    env = adapter.process(inp)
    residual = env.output["mass_balance_residual_kg"]
    # Tolerance is 1e-3 kg per unit op; with 4 ops that is 4e-3 max.
    # Stub design yields exact balance so residual should be ~0.
    assert residual < 1e-3, f"mass_balance_residual_kg={residual} exceeds 1e-3"
    assert env.output["mass_balance_ok"] is True


# ---------------------------------------------------------------------------
# Test 3: multi-step route (3 rxnsmiles) yields 12 unit ops
# ---------------------------------------------------------------------------

def test_multi_step_route_yields_12_unit_ops(adapter: L3StubAdapter) -> None:
    inp = L3ProcessInput(
        target_canonical_smiles=_SIMPLE_TARGET,
        route_rxnsmiles=_MULTI_ROUTE,
        target_throughput_kg_per_batch=2.0,
    )
    env = adapter.process(inp)
    unit_ops = env.output["unit_ops"]
    assert len(unit_ops) == 12, f"Expected 12 unit ops for 3-step route, got {len(unit_ops)}"


# ---------------------------------------------------------------------------
# Test 4: invalid target SMILES "C C" returns FAIL envelope
# ---------------------------------------------------------------------------

def test_invalid_target_smiles_returns_fail(adapter: L3StubAdapter, envelope_schema: dict) -> None:
    inp = L3ProcessInput(
        target_canonical_smiles="C C",   # space is forbidden
        route_rxnsmiles=_SIMPLE_ROUTE,
        target_throughput_kg_per_batch=1.0,
    )
    env = adapter.process(inp)

    # Top-level falsifier status must be FAIL
    assert env.falsifier.status == FalsifierStatus.FAIL or env.falsifier.status == "fail"

    # Find the invalid_molecular_input item
    fail_classes = [item.falsifier_class for item in env.falsifier.items
                    if item.status in (FalsifierStatus.FAIL, "fail")]
    assert FalsifierClass.INVALID_MOLECULAR_INPUT.value in fail_classes, (
        f"Expected invalid_molecular_input FAIL; got classes: {fail_classes}"
    )

    # No unit ops should be emitted on fail-fast
    assert env.output["unit_ops"] == []

    # Envelope must still validate against schema
    env_dict = env.model_dump(mode="json")
    _validate_envelope(env_dict, envelope_schema)


# ---------------------------------------------------------------------------
# Test 5: forced mass-balance break triggers MASS_BALANCE_FAILURE and back_edge
# ---------------------------------------------------------------------------

def test_forced_mass_balance_failure_emits_backedge(adapter: L3StubAdapter, monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatch detect_mass_balance_failure to always return FAIL, simulating
    a deliberately broken stub."""
    from zer0pa_biomolecular_explorer.envelope import EnvelopeFalsifierItem
    from zer0pa_biomolecular_explorer.ids import falsifier_id
    from zer0pa_biomolecular_explorer.falsifiers.registry import get_definition

    def _fake_mass_balance(inputs_kg, outputs_kg, tolerance=1e-3) -> EnvelopeFalsifierItem:
        defn = get_definition(FalsifierClass.MASS_BALANCE_FAILURE)
        return EnvelopeFalsifierItem(
            falsifier_id=falsifier_id(FalsifierClass.MASS_BALANCE_FAILURE.value),
            falsifier_class=FalsifierClass.MASS_BALANCE_FAILURE.value,
            trigger_condition=defn.trigger_condition,
            status=FalsifierStatus.FAIL,
            evidence=["forced_failure_for_test: inputs_kg != outputs_kg beyond tolerance"],
        )

    import zer0pa_biomolecular_explorer.layers.l3.adapter as adapter_mod
    monkeypatch.setattr(adapter_mod, "detect_mass_balance_failure", _fake_mass_balance)

    inp = L3ProcessInput(
        target_canonical_smiles=_SIMPLE_TARGET,
        route_rxnsmiles=_SIMPLE_ROUTE,
        target_throughput_kg_per_batch=1.0,
    )
    env = adapter.process(inp)

    # Overall falsifier must be FAIL
    assert env.falsifier.status in (FalsifierStatus.FAIL, "fail")

    # MASS_BALANCE_FAILURE item must be in the list
    mass_balance_items = [
        item for item in env.falsifier.items
        if item.falsifier_class == FalsifierClass.MASS_BALANCE_FAILURE.value
        and item.status in (FalsifierStatus.FAIL, "fail")
    ]
    assert mass_balance_items, "Expected MASS_BALANCE_FAILURE FAIL item in falsifier.items"

    # Back-edge to L2.5 must be emitted
    back_edge_targets = [be.target_layer for be in env.back_edges]
    assert LayerName.L2_5 in back_edge_targets or "L2.5" in back_edge_targets, (
        f"Expected back_edge to L2.5; got targets: {back_edge_targets}"
    )

    # Back-edge must carry reject_route constraint
    l25_edges = [
        be for be in env.back_edges
        if be.target_layer in (LayerName.L2_5, "L2.5")
    ]
    assert l25_edges[0].proposed_constraint.get("reject_route") is True, (
        "back_edge to L2.5 must have proposed_constraint={'reject_route': True}"
    )


# ---------------------------------------------------------------------------
# Test 6: process_graph DOT output has "digraph" header and "->" edge
# ---------------------------------------------------------------------------

def test_process_graph_dot_has_digraph_and_edge(adapter: L3StubAdapter) -> None:
    inp = L3ProcessInput(
        target_canonical_smiles=_SIMPLE_TARGET,
        route_rxnsmiles=_SIMPLE_ROUTE,
        target_throughput_kg_per_batch=1.0,
    )
    env = adapter.process(inp)
    dot = env.output.get("process_graph_dot", "")
    assert dot, "process_graph_dot should not be empty"
    assert "digraph" in dot, f"DOT output missing 'digraph' keyword:\n{dot}"
    assert "->" in dot, f"DOT output has no edges ('->') for a 4-op sequence:\n{dot}"


def test_process_graph_unit_ops_to_dot_directly() -> None:
    """Test the standalone unit_ops_to_dot function directly."""
    from zer0pa_biomolecular_explorer.contracts.l3 import L3MaterialFlow

    ops = [
        L3UnitOp(
            kind=L3UnitOpKind.REACTION,
            name="step_0_reaction",
            inputs=[L3MaterialFlow(canonical_smiles="CCO", role="reactant", moles=5.0, mass_kg=1.0)],
            outputs=[L3MaterialFlow(canonical_smiles="CC", role="product", moles=4.0, mass_kg=0.85)],
        ),
        L3UnitOp(
            kind=L3UnitOpKind.CRYSTALLIZATION,
            name="step_0_crystallization",
            inputs=[L3MaterialFlow(canonical_smiles="CC", role="product", moles=4.0, mass_kg=0.85)],
            outputs=[L3MaterialFlow(canonical_smiles="CC", role="product", moles=4.0, mass_kg=0.85)],
        ),
    ]
    dot = unit_ops_to_dot(ops)
    assert "digraph" in dot
    assert "n0 -> n1" in dot


def test_process_graph_empty_ops() -> None:
    dot = unit_ops_to_dot([])
    assert "digraph" in dot
    assert "->" not in dot  # empty graph has no edges


# ---------------------------------------------------------------------------
# Test 7: Envelope validates against JSON Schema
# ---------------------------------------------------------------------------

def test_envelope_validates_against_schema(adapter: L3StubAdapter, envelope_schema: dict) -> None:
    inp = L3ProcessInput(
        target_canonical_smiles=_SIMPLE_TARGET,
        route_rxnsmiles=_SIMPLE_ROUTE,
        target_throughput_kg_per_batch=1.0,
    )
    env = adapter.process(inp)
    env_dict = env.model_dump(mode="json")
    _validate_envelope(env_dict, envelope_schema)


# ---------------------------------------------------------------------------
# Test 8: Determinism — same inputs yield same output_hash
# ---------------------------------------------------------------------------

def test_determinism_same_inputs_same_output_hash(adapter: L3StubAdapter) -> None:
    inp = L3ProcessInput(
        target_canonical_smiles=_SIMPLE_TARGET,
        route_rxnsmiles=_SIMPLE_ROUTE,
        target_throughput_kg_per_batch=1.0,
    )
    # Use a fixed run_id to control the only non-deterministic element
    env_a = adapter.process(inp, run_id="run:test-determinism-001")
    env_b = adapter.process(inp, run_id="run:test-determinism-001")
    assert env_a.audit.output_hash == env_b.audit.output_hash, (
        "Same inputs should produce the same output_hash"
    )


# ---------------------------------------------------------------------------
# Test 9: CPP/CQA risks — polymorph_risk and drying_temperature_sensitive
# ---------------------------------------------------------------------------

def test_cpp_cqa_risks_contain_polymorph_and_drying(adapter: L3StubAdapter) -> None:
    inp = L3ProcessInput(
        target_canonical_smiles=_SIMPLE_TARGET,
        route_rxnsmiles=_SIMPLE_ROUTE,
        target_throughput_kg_per_batch=1.0,
    )
    env = adapter.process(inp)
    risks = env.output["cpp_cqa_risks"]
    assert "polymorph_risk" in risks, f"Expected polymorph_risk in {risks}"
    assert "drying_temperature_sensitive" in risks, f"Expected drying_temperature_sensitive in {risks}"


# ---------------------------------------------------------------------------
# Test 10: hERG_specific_risk emitted only for cardiac-wedge tagged run
# ---------------------------------------------------------------------------

def test_herg_specific_risk_only_for_cardiac_wedge_run(adapter: L3StubAdapter) -> None:
    dofetilide_smiles = "CN(C)S(=O)(=O)c1ccc(NCCOc2ccc(CCN(C)S(=O)(=O)C)cc2)cc1"

    # Without cardiac-wedge tag
    inp = L3ProcessInput(
        target_canonical_smiles=dofetilide_smiles,
        route_rxnsmiles=_SIMPLE_ROUTE,
        target_throughput_kg_per_batch=1.0,
    )
    env_no_tag = adapter.process(inp, run_id="run:no-tag-20260430")
    assert "hERG_specific_risk" not in env_no_tag.output["cpp_cqa_risks"]

    # With cardiac-wedge tag
    env_with_tag = adapter.process(inp, run_id="run:cardiac-wedge-20260430")
    assert "hERG_specific_risk" in env_with_tag.output["cpp_cqa_risks"]
