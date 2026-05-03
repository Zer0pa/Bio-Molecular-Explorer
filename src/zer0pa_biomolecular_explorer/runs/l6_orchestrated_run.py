"""L6Router-driven cardiac wedge run.

Demonstrates real falsification-engine routing: each layer is a node in a
state graph; the router walks edges, propagates back-edges between layers,
records decisions, and preserves falsifier state. This is what the PRD
section 5 calls "the falsification engine's actual decision-maker".

Use `run_cardiac_via_l6_router(compound)` instead of `run_cardiac_compound(compound)`
when you want the router-decision audit log (decisions.jsonl populated with
promote/downgrade/reroute/block per transition) and backedge propagation visible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from zer0pa_biomolecular_explorer.audit import AuditTable, AuditWriter
from zer0pa_biomolecular_explorer.contracts.l1 import (
    L1ChannelGene,
    L1ChannelPanelInput,
    L1IonCurrent,
    L1MoleculeInput,
    L1TargetInput,
)
from zer0pa_biomolecular_explorer.contracts.l2 import L2MoleculeInput, L2PropertyInput, L2RetrosynthFeedback
from zer0pa_biomolecular_explorer.contracts.l2_5 import L25Input, L25Policy
from zer0pa_biomolecular_explorer.contracts.l3 import L3ProcessInput
from zer0pa_biomolecular_explorer.contracts.l4 import L4SensorClass, L4SensorState, L4VirtualPlantInput
from zer0pa_biomolecular_explorer.contracts.l5 import L5PKModelKind, L5PKPDInput
from zer0pa_biomolecular_explorer.envelope import LayerEnvelope
from zer0pa_biomolecular_explorer.ids import run_id as new_run_id
from zer0pa_biomolecular_explorer.layers.l1.adapter import L1StubAdapter
from zer0pa_biomolecular_explorer.layers.l2.adapter import L2StubAdapter
from zer0pa_biomolecular_explorer.layers.l2_5.adapter import L25StubAdapter
from zer0pa_biomolecular_explorer.layers.l3.adapter import L3StubAdapter
from zer0pa_biomolecular_explorer.layers.l4.adapter import L4StubAdapter
from zer0pa_biomolecular_explorer.layers.l5.adapter import L5StubAdapter
from zer0pa_biomolecular_explorer.orchestration import L6Router, StateGraph, StateNode, StateTransition


@dataclass
class L6RunResult:
    run_id: str
    compound: str
    transitions: list[dict[str, Any]] = field(default_factory=list)
    promote_count: int = 0
    block_count: int = 0
    backedges_propagated: int = 0
    fatal_falsifiers_blocked: list[str] = field(default_factory=list)


def _build_l6_state_graph(
    compound_smiles: str,
    compound_inchikey: str,
    cmax_unbound_uM: float = 0.001,
) -> StateGraph:
    """Wire the cardiac wedge as a LangGraph-shaped state graph.

    Nodes: l1 (channel panel) -> l25 (retrosynth) -> l2 (property+L2.5 feedback)
        -> l3 (process) -> l4 (virtual plant) -> l5 (PKPD + cardiac bridge).
    Edges: gated on prior envelope's falsifier status (skip-if-blocked).
    """
    l1 = L1StubAdapter()
    l2 = L2StubAdapter()
    l25 = L25StubAdapter()
    l3 = L3StubAdapter()
    l4 = L4StubAdapter()
    l5 = L5StubAdapter()

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
        env = l1.channel_panel(panel_input, ligand_smiles=compound_smiles, run_id=run_id)
        state["l1_env"] = env
        return env

    def h_l25(_inp: Any, run_id: str, pending_backedges: list) -> LayerEnvelope:  # noqa: ARG001
        env = l25.process(L25Input(canonical_smiles=compound_smiles, policy=L25Policy.STUB), run_id=run_id)
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


def run_cardiac_via_l6_router(
    compound: str,
    *,
    runtime_root: Path,
    smiles: str,
    inchikey: str,
    cmax_unbound_uM: float = 0.001,
) -> L6RunResult:
    """Run a compound through the L6 state graph; record decisions per transition."""
    rid = new_run_id()
    audit_root = runtime_root / "audit"
    audit_root.mkdir(parents=True, exist_ok=True)

    aw = AuditWriter(audit_root, rid)
    aw.append(
        AuditTable.RUNS,
        {
            "run_id": rid,
            "executor_identity": "l6-router-orchestrated-run",
            "environment": {"compound": compound, "router": "L6Router/StateGraph"},
        },
    )

    graph = _build_l6_state_graph(smiles, inchikey, cmax_unbound_uM)
    router = L6Router(graph)
    report = router.execute(start_node="l1", run_id=rid, max_iters=64)

    transitions: list[dict[str, Any]] = []
    for step in report.steps:
        decision = step.decision.value
        transitions.append(
            {
                "layer": step.layer,
                "decision": decision,
                "active_falsifiers": step.falsifier_classes_active,
                "backedges_emitted": step.backedges_emitted,
            }
        )
        aw.append(
            AuditTable.DECISIONS,
            {
                "run_id": rid,
                "decision_id": f"decision:l6_router:{step.layer}:{rid}",
                "actor": "l6_router",
                "decision_kind": decision,
                "rationale": (
                    f"L6 router decision for {step.layer}: "
                    f"falsifier_classes_active={step.falsifier_classes_active}; "
                    f"backedges_emitted={step.backedges_emitted}"
                ),
                "triggered_by": [
                    it.falsifier_id for it in step.envelope.falsifier.items if it.falsifier_id
                ][:5],
            },
        )

    return L6RunResult(
        run_id=rid,
        compound=compound,
        transitions=transitions,
        promote_count=report.promote_count,
        block_count=report.block_count,
        backedges_propagated=report.backedge_count,
        fatal_falsifiers_blocked=list(report.fatal_falsifiers_blocked_export),
    )
