"""L6 router — the falsification engine's actual decision-maker.

It walks a state graph, executes each layer's handler, propagates back-edges,
preserves falsifier state across transitions (silent_falsifier_loss is checked
on every promotion), and records decisions to the audit log. The L6Router is
the one thing that should never be 'just' a forward chain — it is the
mechanism by which back-edge propagation, downgrades, and rerouting happen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from zer0pa_health.envelope import (
    BackEdge,
    Backend,
    ConfidenceBand,
    EnvelopeAudit,
    EnvelopeConfidence,
    EnvelopeFalsifier,
    FalsifierStatus,
    LayerEnvelope,
    LayerName,
    ToolAdapter,
)
from zer0pa_health.falsifiers.detectors import detect_silent_falsifier_loss
from zer0pa_health.hashing import sha256_of_obj
from zer0pa_health.ids import audit_id, run_id as new_run_id
from zer0pa_health.orchestration.state_graph import Decision, StateGraph


@dataclass
class RouterStep:
    layer: str
    decision: Decision
    envelope: LayerEnvelope
    backedges_emitted: int
    falsifier_classes_active: list[str] = field(default_factory=list)


@dataclass
class RouterReport:
    run_id: str
    steps: list[RouterStep]
    promote_count: int
    block_count: int
    backedge_count: int
    fatal_falsifiers_blocked_export: list[str]
    final_envelope: LayerEnvelope | None


class L6Router:
    def __init__(self, graph: StateGraph) -> None:
        self.graph = graph

    def execute(
        self,
        start_node: str,
        run_id: str | None = None,
        max_iters: int = 64,
        seed_input: Any = None,
    ) -> RouterReport:
        rid = run_id or new_run_id()
        steps: list[RouterStep] = []
        promote_count = 0
        block_count = 0
        backedge_count = 0
        blocked_export: list[str] = []

        prev_falsifier_classes: list[str] = []
        last_envelope: LayerEnvelope | None = None

        current = start_node
        last_input: Any = seed_input

        for iteration in range(max_iters):
            node = self.graph.node(current)
            pending_backedges = self.graph.backedges.pop_for(node.layer)
            envelope = node.handler(
                last_input,
                run_id=rid,
                pending_backedges=pending_backedges,
            )

            # silent_falsifier_loss check: were any upstream falsifier classes lost?
            current_classes = [it.falsifier_class for it in envelope.falsifier.items]
            sfl = detect_silent_falsifier_loss(prev_falsifier_classes, current_classes)
            if sfl.status == FalsifierStatus.FAIL:
                envelope.falsifier.items.append(sfl)
                # Force the envelope status to FAIL if loss detected
                envelope.falsifier.status = FalsifierStatus.FAIL

            decision = StateGraph.decision_for(envelope)
            for be in envelope.back_edges:
                self.graph.backedges.push(be)
                backedge_count += 1

            steps.append(
                RouterStep(
                    layer=node.layer,
                    decision=decision,
                    envelope=envelope,
                    backedges_emitted=len(envelope.back_edges),
                    falsifier_classes_active=current_classes,
                )
            )

            if decision == Decision.BLOCK:
                block_count += 1
                blocking = [
                    it.falsifier_class
                    for it in envelope.falsifier.items
                    if it.status == FalsifierStatus.FAIL
                ]
                blocked_export.extend(blocking)
                last_envelope = envelope
                break
            elif decision == Decision.PROMOTE:
                promote_count += 1
            elif decision == Decision.BACKEDGE:
                # back-edge already pushed; we still continue forward
                promote_count += 1
            elif decision == Decision.DOWNGRADE:
                promote_count += 1
            elif decision == Decision.REROUTE:
                # find a successor; if no successor, stop
                pass

            prev_falsifier_classes = list(set(prev_falsifier_classes + current_classes))
            last_envelope = envelope
            last_input = envelope.output

            successors = list(self.graph.successors(current, envelope))
            if not successors:
                break
            current = successors[0]

        return RouterReport(
            run_id=rid,
            steps=steps,
            promote_count=promote_count,
            block_count=block_count,
            backedge_count=backedge_count,
            fatal_falsifiers_blocked_export=blocked_export,
            final_envelope=last_envelope,
        )

    @staticmethod
    def make_l6_self_envelope(
        run_id: str, transitions: list[dict[str, Any]]
    ) -> LayerEnvelope:
        """Materialize an L6-as-layer envelope summarizing the run for audit."""
        out = {
            "run_id": run_id,
            "transitions": transitions,
            "decisions_total": len(transitions),
        }
        return LayerEnvelope(
            run_id=run_id,
            layer=LayerName.L6,
            tool_adapter=ToolAdapter(
                name="l6-router-stub", version="0.1.0", backend=Backend.STUB, engine="in-process"
            ),
            input_refs=[],
            output=out,
            confidence=EnvelopeConfidence(
                score=0.6, band=ConfidenceBand.MEDIUM, basis=["router_aggregate"]
            ),
            falsifier=EnvelopeFalsifier(status=FalsifierStatus.PASS, items=[]),
            audit=EnvelopeAudit(
                audit_record_id=audit_id(),
                input_hash=sha256_of_obj({"start": "router"}),
                output_hash=sha256_of_obj(out),
            ),
            back_edges=[],
        )
