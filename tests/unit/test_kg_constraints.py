"""Unit tests for KG constraints K1-K5 (PRD section 6, Phase D.3).

These exercise the validator on hand-built KGStores. The cardiac run
integration tests cover the run-time path; these tests cover the constraint
logic in isolation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from zer0pa_health.kg import (
    EdgeType,
    KGEdge,
    KGNode,
    KGStore,
    KGValidationError,
    KGValidator,
    NodeType,
)


def _empty_store(tmp_path: Path) -> KGStore:
    return KGStore(tmp_path / "kg")


# ---------------- K1: claim provenance ----------------


def test_k1_claim_supported_for_research_requires_audit_record_typed_node(tmp_path):
    """K1 strengthening (Phase D.3): the HAS_AUDIT target must be of NodeType.AUDIT_RECORD,
    not OUTPUT_ENVELOPE (the previous reuse hack).
    """
    store = _empty_store(tmp_path)
    store.add_node(KGNode(node_id="Claim:c1", node_type=NodeType.CLAIM, properties={
        "status": "supported_for_research",
        "multi_current_context": True,
    }))
    store.add_node(KGNode(node_id="EvidenceItem:e1", node_type=NodeType.EVIDENCE_ITEM, properties={}))
    store.add_node(KGNode(node_id="SourceManifest:s1", node_type=NodeType.SOURCE_MANIFEST, properties={}))
    store.add_node(KGNode(node_id="Falsifier:f1", node_type=NodeType.FALSIFIER, properties={
        "falsifier_class": "hERG_only_overreach",
        "status": "pass",
    }))
    # Use the WRONG node type (OUTPUT_ENVELOPE) for the audit pointer
    store.add_node(KGNode(node_id="OutputEnvelope:bad", node_type=NodeType.OUTPUT_ENVELOPE, properties={}))
    store.add_edge(KGEdge(edge_id="e1", edge_type=EdgeType.SUPPORTS, source_node_id="EvidenceItem:e1", target_node_id="Claim:c1"))
    store.add_edge(KGEdge(edge_id="e2", edge_type=EdgeType.HAS_SOURCE, source_node_id="Claim:c1", target_node_id="SourceManifest:s1"))
    store.add_edge(KGEdge(edge_id="e3", edge_type=EdgeType.HAS_FALSIFIER, source_node_id="Claim:c1", target_node_id="Falsifier:f1"))
    store.add_edge(KGEdge(edge_id="e4", edge_type=EdgeType.HAS_AUDIT, source_node_id="Claim:c1", target_node_id="OutputEnvelope:bad"))

    with pytest.raises(KGValidationError, match="K1 violation"):
        KGValidator(store).validate()


def test_k1_passes_with_proper_audit_record_node(tmp_path):
    store = _empty_store(tmp_path)
    store.add_node(KGNode(node_id="Claim:c1", node_type=NodeType.CLAIM, properties={
        "status": "supported_for_research",
        "multi_current_context": True,
    }))
    store.add_node(KGNode(node_id="EvidenceItem:e1", node_type=NodeType.EVIDENCE_ITEM, properties={}))
    store.add_node(KGNode(node_id="SourceManifest:s1", node_type=NodeType.SOURCE_MANIFEST, properties={}))
    store.add_node(KGNode(node_id="Falsifier:f1", node_type=NodeType.FALSIFIER, properties={
        "falsifier_class": "hERG_only_overreach",
        "status": "pass",
    }))
    # Use the CORRECT node type
    store.add_node(KGNode(node_id="AuditRecord:ar1", node_type=NodeType.AUDIT_RECORD, properties={}))
    store.add_edge(KGEdge(edge_id="e1", edge_type=EdgeType.SUPPORTS, source_node_id="EvidenceItem:e1", target_node_id="Claim:c1"))
    store.add_edge(KGEdge(edge_id="e2", edge_type=EdgeType.HAS_SOURCE, source_node_id="Claim:c1", target_node_id="SourceManifest:s1"))
    store.add_edge(KGEdge(edge_id="e3", edge_type=EdgeType.HAS_FALSIFIER, source_node_id="Claim:c1", target_node_id="Falsifier:f1"))
    store.add_edge(KGEdge(edge_id="e4", edge_type=EdgeType.HAS_AUDIT, source_node_id="Claim:c1", target_node_id="AuditRecord:ar1"))

    counts = KGValidator(store).validate()
    assert counts["nodes"] == 5


# ---------------- K2: codec is not a mechanism ----------------


def test_k2_codec_only_falsifier_blocks_supported_status(tmp_path):
    """If a SUPPORTED_FOR_RESEARCH claim's only HAS_FALSIFIER target is a
    codec_as_mechanism FAIL, K2 must reject — codec/replay metric is not a mechanism.
    """
    store = _empty_store(tmp_path)
    store.add_node(KGNode(node_id="Claim:c1", node_type=NodeType.CLAIM, properties={
        "status": "supported_for_research",
        "multi_current_context": True,
    }))
    store.add_node(KGNode(node_id="EvidenceItem:e1", node_type=NodeType.EVIDENCE_ITEM, properties={}))
    store.add_node(KGNode(node_id="SourceManifest:s1", node_type=NodeType.SOURCE_MANIFEST, properties={}))
    store.add_node(KGNode(node_id="Falsifier:codec", node_type=NodeType.FALSIFIER, properties={
        "falsifier_class": "codec_as_mechanism",
        "status": "fail",
    }))
    store.add_node(KGNode(node_id="AuditRecord:ar1", node_type=NodeType.AUDIT_RECORD, properties={}))
    store.add_edge(KGEdge(edge_id="e1", edge_type=EdgeType.SUPPORTS, source_node_id="EvidenceItem:e1", target_node_id="Claim:c1"))
    store.add_edge(KGEdge(edge_id="e2", edge_type=EdgeType.HAS_SOURCE, source_node_id="Claim:c1", target_node_id="SourceManifest:s1"))
    store.add_edge(KGEdge(edge_id="e3", edge_type=EdgeType.HAS_FALSIFIER, source_node_id="Claim:c1", target_node_id="Falsifier:codec"))
    store.add_edge(KGEdge(edge_id="e4", edge_type=EdgeType.HAS_AUDIT, source_node_id="Claim:c1", target_node_id="AuditRecord:ar1"))

    with pytest.raises(KGValidationError, match="K2 violation"):
        KGValidator(store).validate()


def test_k2_codec_plus_real_falsifier_passes(tmp_path):
    """K2 only fails when the ONLY falsifier evidence is codec_as_mechanism FAIL.
    A claim with both a codec FAIL and a real-mechanism falsifier is allowed.
    """
    store = _empty_store(tmp_path)
    store.add_node(KGNode(node_id="Claim:c1", node_type=NodeType.CLAIM, properties={
        "status": "supported_for_research",
        "multi_current_context": True,
    }))
    store.add_node(KGNode(node_id="EvidenceItem:e1", node_type=NodeType.EVIDENCE_ITEM, properties={}))
    store.add_node(KGNode(node_id="SourceManifest:s1", node_type=NodeType.SOURCE_MANIFEST, properties={}))
    store.add_node(KGNode(node_id="Falsifier:codec", node_type=NodeType.FALSIFIER, properties={
        "falsifier_class": "codec_as_mechanism",
        "status": "fail",
    }))
    store.add_node(KGNode(node_id="Falsifier:real", node_type=NodeType.FALSIFIER, properties={
        "falsifier_class": "hERG_only_overreach",
        "status": "pass",
    }))
    store.add_node(KGNode(node_id="AuditRecord:ar1", node_type=NodeType.AUDIT_RECORD, properties={}))
    store.add_edge(KGEdge(edge_id="e1", edge_type=EdgeType.SUPPORTS, source_node_id="EvidenceItem:e1", target_node_id="Claim:c1"))
    store.add_edge(KGEdge(edge_id="e2", edge_type=EdgeType.HAS_SOURCE, source_node_id="Claim:c1", target_node_id="SourceManifest:s1"))
    store.add_edge(KGEdge(edge_id="e3a", edge_type=EdgeType.HAS_FALSIFIER, source_node_id="Claim:c1", target_node_id="Falsifier:codec"))
    store.add_edge(KGEdge(edge_id="e3b", edge_type=EdgeType.HAS_FALSIFIER, source_node_id="Claim:c1", target_node_id="Falsifier:real"))
    store.add_edge(KGEdge(edge_id="e4", edge_type=EdgeType.HAS_AUDIT, source_node_id="Claim:c1", target_node_id="AuditRecord:ar1"))

    KGValidator(store).validate()  # should not raise


# ---------------- K4: every layer L1-L6 represented ----------------


def test_k4_validate_cardiac_requires_all_layers(tmp_path):
    store = _empty_store(tmp_path)
    # Only L1, L5 envelopes present — should fail K4 on cardiac validation.
    for layer in ("L1", "L5"):
        store.add_node(KGNode(
            node_id=f"OutputEnvelope:{layer}:foo",
            node_type=NodeType.OUTPUT_ENVELOPE,
            properties={"layer": layer},
        ))

    with pytest.raises(KGValidationError, match="K4 violation"):
        KGValidator(store).validate_cardiac()


def test_k4_validate_default_skips_layer_coverage(tmp_path):
    """Generic validate() (no enforce_layer_coverage) does NOT require all layers."""
    store = _empty_store(tmp_path)
    store.add_node(KGNode(
        node_id="OutputEnvelope:L1:foo",
        node_type=NodeType.OUTPUT_ENVELOPE,
        properties={"layer": "L1"},
    ))
    KGValidator(store).validate()  # no raise


def test_k4_validate_cardiac_passes_with_full_layer_set(tmp_path):
    store = _empty_store(tmp_path)
    for layer in ("L1", "L2.5", "L2", "L3", "L4", "L5", "L6"):
        store.add_node(KGNode(
            node_id=f"OutputEnvelope:{layer}:foo",
            node_type=NodeType.OUTPUT_ENVELOPE,
            properties={"layer": layer},
        ))
    KGValidator(store).validate_cardiac()  # no raise


# ---------------- K5: episodes are not evidence ----------------


def test_k5_episode_supports_claim_rejected(tmp_path):
    """K5: an Episode node may not be the source of a SUPPORTS edge into a Claim."""
    store = _empty_store(tmp_path)
    store.add_node(KGNode(node_id="Claim:c1", node_type=NodeType.CLAIM, properties={"status": "proposed"}))
    store.add_node(KGNode(node_id="Episode:ep1", node_type=NodeType.EPISODE, properties={}))
    store.add_edge(KGEdge(
        edge_id="bad", edge_type=EdgeType.SUPPORTS,
        source_node_id="Episode:ep1", target_node_id="Claim:c1",
    ))

    with pytest.raises(KGValidationError, match="K5 violation"):
        KGValidator(store).validate()
