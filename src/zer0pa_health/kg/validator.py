"""KG constraint validator (PRD section 6, K1-K5)."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from zer0pa_health.kg.schema import EdgeType, NodeType
from zer0pa_health.kg.store import KGStore


class KGValidationError(RuntimeError):
    pass


_CARDIAC_KEYWORDS = (
    "qt",
    "qtc",
    "tdp",
    "torsades",
    "torsade",
    "proarrhythmia",
    "proarrhythmic",
    "cardiac safety",
    "cardiac_safety",
    "qt_prolongation",
)


class KGValidator:
    def __init__(self, store: KGStore) -> None:
        self.store = store

    def validate(self) -> dict[str, int]:
        node_by_id = {n.node_id: n for n in self.store.iter_nodes()}
        edges = list(self.store.iter_edges())

        # Build incident-edge index: node_id -> {edge_type -> [edges]}
        incident_outgoing: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        incident_incoming: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        for e in edges:
            incident_outgoing[e.source_node_id][e.edge_type.value].append(e)
            incident_incoming[e.target_node_id][e.edge_type.value].append(e)

        # K1: claim supported_for_research requires evidence + source + falsifier + audit
        for node_id, n in node_by_id.items():
            if n.node_type is NodeType.CLAIM and n.properties.get("status") == "supported_for_research":
                out = incident_outgoing[node_id]
                inc = incident_incoming[node_id]
                has_evidence = bool(inc.get(EdgeType.SUPPORTS.value))
                has_source = bool(out.get(EdgeType.HAS_SOURCE.value))
                has_falsifier = bool(out.get(EdgeType.HAS_FALSIFIER.value))
                has_audit = bool(out.get(EdgeType.HAS_AUDIT.value))
                missing = [
                    name
                    for name, ok in (
                        ("evidence_item", has_evidence),
                        ("source_manifest", has_source),
                        ("falsifier", has_falsifier),
                        ("audit_record", has_audit),
                    )
                    if not ok
                ]
                if missing:
                    raise KGValidationError(
                        f"K1 violation: claim {node_id} promoted to supported_for_research without {missing}"
                    )

        # K3: cardiac/QT/TdP claim must have multi-current framing
        for node_id, n in node_by_id.items():
            if n.node_type is NodeType.CLAIM:
                text_blob = (
                    " ".join(str(v) for v in n.properties.values()) + " " + node_id
                ).lower()
                if any(kw in text_blob for kw in _CARDIAC_KEYWORDS):
                    if not n.properties.get("multi_current_context"):
                        raise KGValidationError(
                            f"K3 violation: cardiac claim {node_id} lacks multi_current_context property"
                        )

        # Dangling-edge check
        for e in edges:
            if e.source_node_id not in node_by_id:
                raise KGValidationError(f"dangling source: edge {e.edge_id} -> {e.source_node_id}")
            if e.target_node_id not in node_by_id:
                raise KGValidationError(f"dangling target: edge {e.edge_id} -> {e.target_node_id}")

        return {
            "nodes": len(node_by_id),
            "edges": len(edges),
        }
