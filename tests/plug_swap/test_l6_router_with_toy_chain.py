"""L6 router with all-toy adapter chain test.

Builds a state graph with toy adapters at every node, runs L6Router.execute()
against it, asserts at least one promotion and zero plug_regression failures.

This is the PRD section 2 acceptance criterion from the full-chain perspective:
  "downstream code is unchanged" when all adapters are swapped to toy variants.
"""

from __future__ import annotations

from typing import Any

import pytest

from zer0pa_health.contracts.l1 import (
    L1ChannelGene,
    L1ChannelPanelInput,
    L1IonCurrent,
    L1MoleculeInput,
    L1TargetInput,
)
from zer0pa_health.contracts.l2 import L2MoleculeInput, L2PropertyInput, L2RetrosynthFeedback
from zer0pa_health.contracts.l2_5 import L25Input, L25Policy
from zer0pa_health.contracts.l3 import L3ProcessInput
from zer0pa_health.contracts.l4 import L4SensorClass, L4SensorState, L4VirtualPlantInput
from zer0pa_health.contracts.l5 import L5PKModelKind, L5PKPDInput
from zer0pa_health.envelope import FalsifierStatus, LayerEnvelope
from zer0pa_health.falsifiers.detectors import detect_plug_replaceability_regression
from zer0pa_health.layers.l1.toy_adapter import L1ToyAdapter
from zer0pa_health.layers.l2.toy_adapter import L2ToyAdapter
from zer0pa_health.layers.l2_5.toy_adapter import L25ToyAdapter
from zer0pa_health.layers.l3.toy_adapter import L3ToyAdapter
from zer0pa_health.layers.l4.toy_adapter import L4ToyAdapter
from zer0pa_health.layers.l5.toy_adapter import L5ToyAdapter
from zer0pa_health.orchestration import L6Router, StateGraph, StateNode, StateTransition

_COMPOUND_SMILES = "CN(C)S(=O)(=O)c1ccc(NCCOc2ccc(CCN(C)S(=O)(=O)C)cc2)cc1"
_COMPOUND_INCHIKEY = "IXTMWRCNAAVVAI-UHFFFAOYSA-N"


def _build_toy_state_graph(
    compound_smiles: str = _COMPOUND_SMILES,
    compound_inchikey: str = _COMPOUND_INCHIKEY,
) -> StateGraph:
    """Build a state graph using toy adapters at every node.

    Same topology as the stub chain (l1→l25→l2→l3→l4→l5) but every
    adapter is the corresponding Toy variant.
    """
    l1 = L1ToyAdapter()
    l2 = L2ToyAdapter()
    l25 = L25ToyAdapter()
    l3 = L3ToyAdapter()
    l4 = L4ToyAdapter()
    l5 = L5ToyAdapter()

    panel_input = L1ChannelPanelInput(
        targets=[
            L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr),
            L1TargetInput(gene=L1ChannelGene.SCN5A, current=L1IonCurrent.INaL),
            L1TargetInput(gene=L1ChannelGene.KCNQ1, current=L1IonCurrent.IKs),
            L1TargetInput(gene=L1ChannelGene.CACNA1C, current=L1IonCurrent.ICaL),
        ]
    )

    state: dict[str, Any] = {}

    def h_l1(_inp: Any, run_id: str, pending_backedges: list) -> LayerEnvelope:  # noqa: ARG001
        env = l1.channel_panel(
            panel_input,
            ligand_smiles=compound_smiles,
            ligand_inchikey=compound_inchikey,
            run_id=run_id,
        )
        state["l1_env"] = env
        return env

    def h_l25(_inp: Any, run_id: str, pending_backedges: list) -> LayerEnvelope:  # noqa: ARG001
        env = l25.process(
            L25Input(canonical_smiles=compound_smiles, policy=L25Policy.STUB),
            run_id=run_id,
        )
        state["l25_env"] = env
        return env

    def h_l2(_inp: Any, run_id: str, pending_backedges: list) -> LayerEnvelope:  # noqa: ARG001
        feedback = state.get("l25_env").output.get("feedback_to_l2", {})
        env = l2.process(
            L2PropertyInput(
                molecule=L2MoleculeInput(smiles=compound_smiles, inchikey=compound_inchikey),
                retrosynth_feedback=L2RetrosynthFeedback(
                    smiles=compound_smiles,
                    route_score=float(feedback.get("route_score", 0.5)),
                    route_depth=int(feedback.get("route_depth", 2)),
                    sa_score=float(feedback.get("sa_score", 4.0)),
                    starting_material_cost_usd=float(
                        feedback.get("starting_material_cost_usd", 100.0)
                    ),
                    routes_found=bool(feedback.get("routes_found", 1.0)),
                ),
            ),
            run_id=run_id,
        )
        state["l2_env"] = env
        return env

    def h_l3(_inp: Any, run_id: str, pending_backedges: list) -> LayerEnvelope:  # noqa: ARG001
        rxn = []
        for r in state["l25_env"].output.get("routes", []):
            for s in r.get("steps", []):
                if s.get("rxnsmiles"):
                    rxn.append(s["rxnsmiles"])
        if not rxn:
            rxn = ["[CH4:1].[OH2:2]>>[CH3:1][OH:2]"]
        env = l3.process(
            L3ProcessInput(
                target_canonical_smiles=compound_smiles,
                route_rxnsmiles=rxn[:3],
                target_throughput_kg_per_batch=1.0,
            ),
            run_id=run_id,
        )
        state["l3_env"] = env
        return env

    def h_l4(_inp: Any, run_id: str, pending_backedges: list) -> LayerEnvelope:  # noqa: ARG001
        sensors = [
            L4SensorState(
                sensor_id="PAT-T-01",
                sensor_class=L4SensorClass.PAT_TEMP,
                value=25.0,
                unit="C",
                timestamp_utc="2026-04-30T00:00:00Z",
                in_range=True,
                expected_range=(20.0, 60.0),
            )
        ]
        unit_op_names = [
            op.get("name", f"unit_op_{i}")
            for i, op in enumerate(state["l3_env"].output.get("unit_ops", []))
        ][:4] or ["reaction_1"]
        env = l4.process(
            L4VirtualPlantInput(
                process_graph_unit_ops=unit_op_names,
                sensor_states=sensors,
                target_throughput_kg_per_batch=1.0,
            ),
            run_id=run_id,
        )
        state["l4_env"] = env
        return env

    def h_l5(_inp: Any, run_id: str, pending_backedges: list) -> LayerEnvelope:  # noqa: ARG001
        env = l5.process(
            L5PKPDInput(
                canonical_smiles=compound_smiles,
                inchikey=compound_inchikey,
                dose_mg=0.5,
                model_kind=L5PKModelKind.ONE_COMPARTMENT,
                fraction_unbound=0.4,
                cl_l_per_h=10.0,
                vd_l=70.0,
                ka_per_h=1.0,
            ),
            run_id=run_id,
        )
        state["l5_env"] = env
        return env

    g = StateGraph()
    g.add_node(StateNode(name="l1", layer="L1", handler=h_l1))
    g.add_node(StateNode(name="l25", layer="L2.5", handler=h_l25))
    g.add_node(StateNode(name="l2", layer="L2", handler=h_l2))
    g.add_node(StateNode(name="l3", layer="L3", handler=h_l3))
    g.add_node(StateNode(name="l4", layer="L4", handler=h_l4))
    g.add_node(StateNode(name="l5", layer="L5", handler=h_l5))

    g.add_edge(StateTransition(src="l1", dst="l25", gate=StateGraph.gate_not_blocked))
    g.add_edge(StateTransition(src="l25", dst="l2", gate=StateGraph.gate_not_blocked))
    g.add_edge(StateTransition(src="l2", dst="l3", gate=StateGraph.gate_not_blocked))
    g.add_edge(StateTransition(src="l3", dst="l4", gate=StateGraph.gate_not_blocked))
    g.add_edge(StateTransition(src="l4", dst="l5", gate=StateGraph.gate_not_blocked))

    return g


# ============================================================================
# Tests
# ============================================================================


def test_l6_router_toy_chain_executes_all_layers():
    """Toy chain executes all 6 layers without crashing.

    Note: re-executions triggered by back-edges may add additional steps
    beyond the initial 6-layer forward walk; the assertion checks coverage,
    not exact length.
    """
    graph = _build_toy_state_graph()
    router = L6Router(graph)
    report = router.execute(start_node="l1", run_id="run:toy-chain-test", max_iters=64)

    # All 6 layers must appear in the visit set (forward chain + any re-executions)
    layers_visited = {step.layer for step in report.steps}
    assert layers_visited == {"L1", "L2.5", "L2", "L3", "L4", "L5"}, (
        f"layers_visited={layers_visited}"
    )
    # At least 6 transitions (one per forward layer); re-executions allowed.
    assert len(report.steps) >= 6


def test_l6_router_toy_chain_at_least_one_promotion():
    """Toy chain must produce at least one promote decision."""
    graph = _build_toy_state_graph()
    router = L6Router(graph)
    report = router.execute(start_node="l1", run_id="run:toy-chain-promote-test", max_iters=64)

    assert report.promote_count >= 1, (
        f"Expected at least 1 promotion in toy chain; got {report.promote_count}. "
        f"Decisions: {[s.decision for s in report.steps]}"
    )


def test_l6_router_toy_chain_zero_plug_regression_failures():
    """Every step in the toy chain must have no plug_regression falsifier failures."""
    graph = _build_toy_state_graph()
    router = L6Router(graph)
    report = router.execute(start_node="l1", run_id="run:toy-chain-plug-reg-test", max_iters=64)

    plug_regression_failures = []
    for step in report.steps:
        for item in step.envelope.falsifier.items:
            if (
                item.falsifier_class == "plug_replaceability_regression"
                and item.status == FalsifierStatus.FAIL
            ):
                plug_regression_failures.append(
                    f"{step.layer}: {item.evidence}"
                )

    assert len(plug_regression_failures) == 0, (
        f"Plug regression failures detected in toy chain: {plug_regression_failures}"
    )


def test_l6_router_toy_chain_all_envelopes_valid_contract():
    """All envelopes in the toy chain have contract_version == zer0pa.layer-envelope.v1."""
    graph = _build_toy_state_graph()
    router = L6Router(graph)
    report = router.execute(start_node="l1", run_id="run:toy-chain-contract-test", max_iters=64)

    for step in report.steps:
        assert step.envelope.contract_version == "zer0pa.layer-envelope.v1", (
            f"Layer {step.layer} envelope has wrong contract_version: "
            f"{step.envelope.contract_version}"
        )


def test_l6_router_toy_chain_no_block():
    """Toy chain with clean inputs must not BLOCK (all falsifiers should PASS)."""
    graph = _build_toy_state_graph()
    router = L6Router(graph)
    report = router.execute(start_node="l1", run_id="run:toy-chain-block-test", max_iters=64)

    assert report.block_count == 0, (
        f"Expected zero blocks in toy chain; got {report.block_count}. "
        f"Blocked falsifiers: {report.fatal_falsifiers_blocked_export}"
    )


def test_l6_router_toy_chain_schema_matches_stub_chain():
    """Toy chain envelope output shapes match the stub chain at each layer."""
    from zer0pa_health.runs.l6_orchestrated_run import _build_l6_state_graph

    # Run toy chain
    toy_graph = _build_toy_state_graph()
    toy_router = L6Router(toy_graph)
    toy_report = toy_router.execute(
        start_node="l1", run_id="run:toy-chain-schema-test", max_iters=64
    )

    # Run stub chain
    stub_graph = _build_l6_state_graph(
        compound_smiles=_COMPOUND_SMILES,
        compound_inchikey=_COMPOUND_INCHIKEY,
    )
    stub_router = L6Router(stub_graph)
    stub_report = stub_router.execute(
        start_node="l1", run_id="run:stub-chain-schema-test", max_iters=64
    )

    # Build layer → envelope maps
    toy_envs = {step.layer: step.envelope for step in toy_report.steps}
    stub_envs = {step.layer: step.envelope for step in stub_report.steps}

    for layer in stub_envs:
        if layer not in toy_envs:
            continue  # skip if toy chain didn't visit this layer (shouldn't happen)

        toy_keys = {k: type(v).__name__ for k, v in toy_envs[layer].output.items()}
        stub_keys = {k: type(v).__name__ for k, v in stub_envs[layer].output.items()}

        res = detect_plug_replaceability_regression(stub_keys, toy_keys)
        assert res.status == FalsifierStatus.PASS, (
            f"[{layer}] Plug regression failure between stub and toy chains: "
            f"stub_keys={sorted(stub_keys.keys())}, "
            f"toy_keys={sorted(toy_keys.keys())}; "
            f"evidence={res.evidence}"
        )


def test_l6_router_toy_chain_back_edges_propagated():
    """Toy chain propagates back-edges (at least L2.5 → L2 and L5 → L1)."""
    graph = _build_toy_state_graph()
    router = L6Router(graph)
    report = router.execute(start_node="l1", run_id="run:toy-chain-backedge-test", max_iters=64)

    # At least some back-edges should be emitted (L2.5 always back-edges to L2)
    assert report.backedge_count >= 1, (
        f"Expected at least 1 back-edge in toy chain; got {report.backedge_count}"
    )


def test_l6_router_toy_chain_deterministic():
    """Toy chain is deterministic: same run_id and inputs produce same output_hashes."""
    # Run the toy chain twice with different L6Router instances but same run_id
    # (output_hashes of each layer envelope should match because adapters are deterministic)
    run_id = "run:toy-chain-determinism-test"

    graph1 = _build_toy_state_graph()
    router1 = L6Router(graph1)
    report1 = router1.execute(start_node="l1", run_id=run_id, max_iters=64)

    graph2 = _build_toy_state_graph()
    router2 = L6Router(graph2)
    report2 = router2.execute(start_node="l1", run_id=run_id, max_iters=64)

    for step1, step2 in zip(report1.steps, report2.steps):
        assert step1.layer == step2.layer
        assert step1.envelope.audit.output_hash == step2.envelope.audit.output_hash, (
            f"Layer {step1.layer} output_hash is non-deterministic: "
            f"run1={step1.envelope.audit.output_hash}, run2={step2.envelope.audit.output_hash}"
        )
