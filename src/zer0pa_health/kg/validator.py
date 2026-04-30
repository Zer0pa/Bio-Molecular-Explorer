"""KG constraint validator (PRD section 6, K1-K5).

K1: A Claim may not be SUPPORTED_FOR_RESEARCH unless it has at least one EvidenceItem,
    one SourceManifest, one Falsifier, and one AuditRecord.
K2: A mechanism edge may not be source-grounded if its only evidence is a codec/replay
    metric. Operationally: if a Claim's only HAS_FALSIFIER edge is to a `codec_as_mechanism`
    falsifier with FAIL status, the claim cannot be SUPPORTED_FOR_RESEARCH.
K3: Any Claim touching QT, TdP, proarrhythmia, or cardiac safety MUST include multi-current
    framing or fail the hERG-only falsifier.
K4: Every layer Output must exist as an OutputEnvelope node. The layer set L1-L6 must be
    represented in any cardiac run.
K5: Episode nodes support resume and learning, but cannot serve as scientific evidence
    on their own — they may not have outgoing SUPPORTS edges to a Claim.
"""

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


# Cardiac runs must show every layer L1-L6 represented as an OutputEnvelope node.
_REQUIRED_CARDIAC_LAYERS: frozenset[str] = frozenset({"L1", "L2.5", "L2", "L3", "L4", "L5", "L6"})


class KGValidator:
    def __init__(self, store: KGStore) -> None:
        self.store = store

    def validate(self, *, enforce_layer_coverage: bool = False) -> dict[str, int]:
        """Run K1-K5 plus dangling-edge check.

        Parameters
        ----------
        enforce_layer_coverage:
            When True, K4 requires every layer in `_REQUIRED_CARDIAC_LAYERS`
            to appear as an OutputEnvelope. The default is False so generic
            KG fixtures (which may not have all layers) still validate; the
            cardiac run flips this on via `validate_cardiac()`.
        """
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
                # K1 strengthening (Phase D.3): HAS_AUDIT must point to a node of
                # NodeType.AUDIT_RECORD specifically (not the OUTPUT_ENVELOPE
                # reuse hack used pre-2026-04-30).
                has_audit_records = [
                    e for e in out.get(EdgeType.HAS_AUDIT.value, [])
                    if (
                        e.target_node_id in node_by_id
                        and node_by_id[e.target_node_id].node_type is NodeType.AUDIT_RECORD
                    )
                ]
                has_audit = bool(has_audit_records)
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

        # K2: codec-not-mechanism — a SUPPORTED_FOR_RESEARCH claim cannot rest
        # solely on codec_as_mechanism evidence. We check the falsifier targets:
        # if every HAS_FALSIFIER target node is a Falsifier with falsifier_class
        # == "codec_as_mechanism" AND status FAIL, the claim must NOT be
        # SUPPORTED_FOR_RESEARCH.
        for node_id, n in node_by_id.items():
            if (
                n.node_type is NodeType.CLAIM
                and n.properties.get("status") == "supported_for_research"
            ):
                falsifier_targets = [
                    node_by_id.get(e.target_node_id)
                    for e in incident_outgoing[node_id].get(EdgeType.HAS_FALSIFIER.value, [])
                ]
                falsifier_targets = [t for t in falsifier_targets if t is not None]
                if falsifier_targets and all(
                    t.node_type is NodeType.FALSIFIER
                    and t.properties.get("falsifier_class") == "codec_as_mechanism"
                    and t.properties.get("status") == "fail"
                    for t in falsifier_targets
                ):
                    raise KGValidationError(
                        f"K2 violation: claim {node_id} cannot be supported_for_research when "
                        "its only falsifier evidence is a codec_as_mechanism FAIL "
                        "(codec/replay metric is not a mechanism)"
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

        # K4: every layer L1-L6 must be represented as an OutputEnvelope (cardiac runs only).
        if enforce_layer_coverage:
            envelope_layers: set[str] = set()
            for n in node_by_id.values():
                if n.node_type is NodeType.OUTPUT_ENVELOPE:
                    layer = n.properties.get("layer")
                    if isinstance(layer, str):
                        envelope_layers.add(layer)
            missing_layers = _REQUIRED_CARDIAC_LAYERS - envelope_layers
            if missing_layers:
                raise KGValidationError(
                    f"K4 violation: cardiac run KG missing OutputEnvelope nodes for layers "
                    f"{sorted(missing_layers)}; envelopes present: {sorted(envelope_layers)}"
                )

        # K5: Episode nodes cannot directly support a Claim.
        for e in edges:
            if e.edge_type is EdgeType.SUPPORTS:
                src = node_by_id.get(e.source_node_id)
                if src is not None and src.node_type is NodeType.EPISODE:
                    raise KGValidationError(
                        f"K5 violation: Episode node {src.node_id} may not directly SUPPORTS a Claim "
                        f"(edge {e.edge_id}); episodes are scaffolding for resume/learning, "
                        "not scientific evidence."
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

    def validate_cardiac(self) -> dict[str, int]:
        """Cardiac-run-specific validation: K1-K5 plus K4 layer coverage L1-L6."""
        return self.validate(enforce_layer_coverage=True)
