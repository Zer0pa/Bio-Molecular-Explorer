"""LangGraph-shaped state graph.

This is a minimal in-process state graph; LangGraph (langgraph package) binds
into the same protocol. It supports:
  - layer nodes with adapter call-points
  - conditional edges based on falsifier status / confidence band
  - explicit back-edge queue (per PRD section 3 — back-edge propagation)
  - decision recording (promote/downgrade/reroute/block/hold)
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable

from zer0pa_health.envelope import (
    BackEdge,
    EnvelopeFalsifierItem,
    FalsifierStatus,
    LayerEnvelope,
)


class Decision(str, Enum):
    PROMOTE = "promote"
    DOWNGRADE = "downgrade"
    REROUTE = "reroute"
    BLOCK = "block"
    BACKEDGE = "backedge"
    HOLD = "hold"


@dataclass
class StateNode:
    """A node in the L6 state graph — typically a single layer."""

    name: str
    layer: str  # "L1" | "L2" | "L2.5" | "L3" | "L4" | "L5" | "L6"
    handler: Callable[..., LayerEnvelope]


@dataclass
class StateTransition:
    """A directed edge with an optional gate that reads the prior envelope."""

    src: str
    dst: str
    gate: Callable[[LayerEnvelope], bool] = field(default_factory=lambda: (lambda env: True))


class BackEdgeQueue:
    """Per-target-layer FIFO of pending back-edges."""

    def __init__(self) -> None:
        self._q: dict[str, deque[BackEdge]] = defaultdict(deque)

    def push(self, edge: BackEdge) -> None:
        self._q[edge.target_layer].append(edge)

    def pop_for(self, layer: str) -> list[BackEdge]:
        out: list[BackEdge] = []
        while self._q.get(layer):
            out.append(self._q[layer].popleft())
        return out

    def pending(self) -> dict[str, int]:
        return {k: len(v) for k, v in self._q.items() if v}


class StateGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, StateNode] = {}
        self._edges: list[StateTransition] = []
        self.backedges = BackEdgeQueue()

    def add_node(self, node: StateNode) -> None:
        if node.name in self._nodes:
            raise KeyError(f"node {node.name!r} already registered")
        self._nodes[node.name] = node

    def add_edge(self, edge: StateTransition) -> None:
        if edge.src not in self._nodes:
            raise KeyError(f"edge src {edge.src!r} not in nodes")
        if edge.dst not in self._nodes:
            raise KeyError(f"edge dst {edge.dst!r} not in nodes")
        self._edges.append(edge)

    def node(self, name: str) -> StateNode:
        return self._nodes[name]

    def successors(self, name: str, last_envelope: LayerEnvelope) -> Iterable[str]:
        for e in self._edges:
            if e.src == name and e.gate(last_envelope):
                yield e.dst

    def nodes_by_layer(self, layer: str) -> list[StateNode]:
        """Return all registered nodes whose `layer` field matches the given layer string."""
        return [n for n in self._nodes.values() if n.layer == layer]

    @staticmethod
    def gate_pass_only(env: LayerEnvelope) -> bool:
        return env.falsifier.status == FalsifierStatus.PASS

    @staticmethod
    def gate_not_blocked(env: LayerEnvelope) -> bool:
        return env.falsifier.status != FalsifierStatus.BLOCKED

    @staticmethod
    def decision_for(env: LayerEnvelope) -> Decision:
        items: list[EnvelopeFalsifierItem] = list(env.falsifier.items)
        # block_export severity: any clinical_overclaim / silent_falsifier_loss FAIL
        for it in items:
            if it.status == FalsifierStatus.FAIL and it.falsifier_class in {
                "clinical_overclaim",
                "silent_falsifier_loss",
                "license_drift",
            }:
                return Decision.BLOCK
        if env.falsifier.status == FalsifierStatus.FAIL:
            return Decision.REROUTE
        if env.falsifier.status == FalsifierStatus.BLOCKED:
            return Decision.BLOCK
        if env.confidence.band == "low":
            return Decision.DOWNGRADE
        if env.back_edges:
            return Decision.BACKEDGE
        return Decision.PROMOTE
