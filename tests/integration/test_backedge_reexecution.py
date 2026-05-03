"""Forced backedge re-execution test.

Demonstrates the L6Router actually does closed-loop work: when a layer
emits a back_edge to an upstream layer, the router re-executes that
upstream layer (with the constraint visible in its `pending_backedges`
arg) before completing the run. This is the falsification engine in
action — back-edge propagation as code, not just diagram.
"""

from __future__ import annotations

from typing import Any

import pytest

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
from zer0pa_biomolecular_explorer.hashing import sha256_of_obj
from zer0pa_biomolecular_explorer.ids import audit_id
from zer0pa_biomolecular_explorer.orchestration import L6Router, StateGraph, StateNode, StateTransition


# ----------------- helpers -----------------


def _basic_envelope(
    layer: LayerName,
    *,
    output: dict[str, Any],
    run_id: str,
    falsifier_status: FalsifierStatus = FalsifierStatus.PASS,
    falsifier_items: list[EnvelopeFalsifierItem] | None = None,
    back_edges: list[BackEdge] | None = None,
    engine: str = "stub",
) -> LayerEnvelope:
    return LayerEnvelope(
        run_id=run_id,
        layer=layer,
        tool_adapter=ToolAdapter(name=engine, version="0.1", backend=Backend.STUB, engine=engine),
        input_refs=[],
        output=output,
        confidence=EnvelopeConfidence(
            score=0.6, band=ConfidenceBand.MEDIUM, basis=["unit_test_stub"]
        ),
        falsifier=EnvelopeFalsifier(status=falsifier_status, items=falsifier_items or []),
        audit=EnvelopeAudit(
            audit_record_id=audit_id(),
            input_hash=sha256_of_obj(output),
            output_hash=sha256_of_obj(output),
        ),
        back_edges=back_edges or [],
    )


# ----------------- forced backedge: L2 emits back_edge to L1 -----------------


def test_router_re_runs_upstream_when_backedge_propagated():
    """L1 -> L2; L2 emits a back_edge to L1; router re-runs L1 with the constraint visible."""
    rid = "run:test-backedge-reex"
    l1_call_log: list[dict[str, Any]] = []

    def h_l1(_inp: Any, run_id: str, pending_backedges: list[BackEdge]) -> LayerEnvelope:
        # Record what backedges (if any) the router fed us
        l1_call_log.append(
            {
                "n_pending": len(pending_backedges),
                "constraints": [be.proposed_constraint for be in pending_backedges],
            }
        )
        return _basic_envelope(
            LayerName.L1,
            output={"call_index": len(l1_call_log)},
            run_id=run_id,
        )

    def h_l2(_inp: Any, run_id: str, pending_backedges: list[BackEdge]) -> LayerEnvelope:
        # L2 always emits a back_edge to L1 with a constraint
        return _basic_envelope(
            LayerName.L2,
            output={"l2_passed": True},
            run_id=run_id,
            back_edges=[
                BackEdge(
                    target_layer=LayerName.L1,
                    reason="L2 wants L1 to refresh the panel",
                    proposed_constraint={"refresh": True, "reason": "test"},
                )
            ],
        )

    g = StateGraph()
    g.add_node(StateNode(name="l1", layer="L1", handler=h_l1))
    g.add_node(StateNode(name="l2", layer="L2", handler=h_l2))
    g.add_edge(StateTransition(src="l1", dst="l2"))

    report = L6Router(g).execute(start_node="l1", run_id=rid)

    # L1 must have been called at least twice: once forward, once after back-edge
    assert len(l1_call_log) >= 2, f"l1 calls: {l1_call_log}"
    # The second call must have received the proposed constraint
    second_call = l1_call_log[1]
    assert second_call["n_pending"] == 1
    assert second_call["constraints"] == [{"refresh": True, "reason": "test"}]
    # Router report reflects re-execution
    assert report.backedge_reexecutions >= 1
    # Steps include a re-execution flagged step
    rerun_steps = [s for s in report.steps if s.is_reexecution]
    assert len(rerun_steps) >= 1
    assert rerun_steps[0].layer == "L1"


def test_router_caps_re_executions_per_layer():
    """The router must NOT loop forever on a layer that always emits back-edges to itself's upstream."""
    rid = "run:test-backedge-cap"
    l1_call_count = 0

    def h_l1(_inp: Any, run_id: str, pending_backedges: list[BackEdge]) -> LayerEnvelope:  # noqa: ARG001
        nonlocal l1_call_count
        l1_call_count += 1
        return _basic_envelope(LayerName.L1, output={}, run_id=run_id)

    def h_l2(_inp: Any, run_id: str, pending_backedges: list[BackEdge]) -> LayerEnvelope:  # noqa: ARG001
        # L2 always emits a fresh back_edge to L1 — would loop forever without a cap
        return _basic_envelope(
            LayerName.L2,
            output={},
            run_id=run_id,
            back_edges=[
                BackEdge(
                    target_layer=LayerName.L1,
                    reason="loop test",
                    proposed_constraint={"i": 1},
                )
            ],
        )

    g = StateGraph()
    g.add_node(StateNode(name="l1", layer="L1", handler=h_l1))
    g.add_node(StateNode(name="l2", layer="L2", handler=h_l2))
    g.add_edge(StateTransition(src="l1", dst="l2"))

    report = L6Router(g).execute(start_node="l1", run_id=rid)

    # Per-layer budget = 2 means at most 2 re-executions of L1 → 1 forward + 2 reruns = 3 calls max
    assert l1_call_count <= 3, f"L1 was called {l1_call_count} times — budget breached"
    assert report.backedge_reexecutions <= 12  # global cap


def test_router_back_edge_to_unknown_layer_is_drained_without_crash():
    """If a back_edge targets a layer that's not in the graph, the router drains it cleanly."""
    rid = "run:test-backedge-orphan"

    def h_l1(_inp: Any, run_id: str, pending_backedges: list[BackEdge]) -> LayerEnvelope:  # noqa: ARG001
        return _basic_envelope(
            LayerName.L1,
            output={},
            run_id=run_id,
            back_edges=[
                BackEdge(
                    target_layer=LayerName.L4,  # L4 not in this graph
                    reason="orphan",
                    proposed_constraint={"x": 1},
                )
            ],
        )

    g = StateGraph()
    g.add_node(StateNode(name="l1", layer="L1", handler=h_l1))

    report = L6Router(g).execute(start_node="l1", run_id=rid)

    # Run completes; orphan backedge does not crash the router
    assert report.backedge_count >= 1
    # No re-execution (no node with layer L4)
    assert report.backedge_reexecutions == 0


def test_router_re_execution_is_recorded_to_steps_with_is_reexecution_flag():
    """Re-execution steps are flagged so callers can distinguish forward vs back-edge-driven runs."""
    rid = "run:test-backedge-flag"
    call_count = 0

    def h_l1(_inp: Any, run_id: str, pending_backedges: list[BackEdge]) -> LayerEnvelope:  # noqa: ARG001
        nonlocal call_count
        call_count += 1
        return _basic_envelope(LayerName.L1, output={"call": call_count}, run_id=run_id)

    def h_l2(_inp: Any, run_id: str, pending_backedges: list[BackEdge]) -> LayerEnvelope:  # noqa: ARG001
        return _basic_envelope(
            LayerName.L2,
            output={},
            run_id=run_id,
            back_edges=[
                BackEdge(
                    target_layer=LayerName.L1,
                    reason="rerun L1",
                    proposed_constraint={"refresh": True},
                )
            ],
        )

    g = StateGraph()
    g.add_node(StateNode(name="l1", layer="L1", handler=h_l1))
    g.add_node(StateNode(name="l2", layer="L2", handler=h_l2))
    g.add_edge(StateTransition(src="l1", dst="l2"))

    report = L6Router(g).execute(start_node="l1", run_id=rid)

    forward_steps = [s for s in report.steps if not s.is_reexecution]
    rerun_steps = [s for s in report.steps if s.is_reexecution]
    assert len(forward_steps) == 2  # L1 + L2 forward
    assert len(rerun_steps) >= 1  # at least one L1 rerun
    assert all(s.layer == "L1" for s in rerun_steps)
