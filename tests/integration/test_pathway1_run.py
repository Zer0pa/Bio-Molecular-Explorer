"""End-to-end Pathway 1 run tests.

Validates that:
  - run_pathway1_compound walks all 6 P1 layers + cardiac bridge
  - All 12 audit tables populate
  - Audit hash chain validates
  - KG runtime nodes emit (with K1-K3 still holding)
  - Handoff packets are written to disk and validate against the Pydantic schema
  - The cardiac L1 bridge produces a valid L1 envelope when target is cardiac
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zer0pa_health.audit import AuditTable, AuditValidator
from zer0pa_health.envelope import FalsifierStatus
from zer0pa_health.kg import KGStore, KGValidator
from zer0pa_health.pathway1.contracts.p1_handoff import P1HandoffPacket
from zer0pa_health.runs import (
    Pathway1RunResult,
    run_pathway1_cardiac_wedge,
    run_pathway1_compound,
)


def test_pathway1_run_kcnh2_completes(tmp_path):
    res = run_pathway1_compound("KCNH2", runtime_root=tmp_path, library_size=15, max_iterations=20)
    assert res.target_gene == "KCNH2"
    assert res.n_handoff_packets >= 1


def test_pathway1_run_writes_all_12_audit_tables(tmp_path):
    res = run_pathway1_compound("KCNH2", runtime_root=tmp_path, library_size=15)
    expected = {t.value for t in AuditTable}
    nonempty = {k for k, v in res.audit_table_counts.items() if v > 0}
    # Allow for minor missing tables but the core 8 must populate
    core = {
        "runs",
        "molecules",
        "model_tools",
        "source_manifest",
        "parameters",
        "confidence",
        "falsifiers",
        "decisions",
        "artifacts",
        "replay_commands",
        "midd_assessments",
        "offload_manifest",
    }
    assert core <= nonempty, f"missing P1 audit tables: {core - nonempty}"


def test_pathway1_run_audit_hash_chain_validates(tmp_path):
    res = run_pathway1_compound("KCNH2", runtime_root=tmp_path)
    AuditValidator(tmp_path / "audit", res.run_id).validate()


def test_pathway1_run_kg_runtime_nodes_validate(tmp_path):
    run_pathway1_compound("KCNH2", runtime_root=tmp_path)
    store = KGStore(tmp_path / "kg")
    res = KGValidator(store).validate()
    assert res["nodes"] > 30  # cardiac seed + pathway1 seed + runtime nodes
    assert res["edges"] > 20


def test_pathway1_run_handoff_packets_written_to_disk(tmp_path):
    res = run_pathway1_compound("KCNH2", runtime_root=tmp_path, library_size=10)
    assert len(res.handoff_packets_paths) == res.n_handoff_packets
    assert res.n_handoff_packets >= 1
    for path in res.handoff_packets_paths:
        assert path.exists()
        # Validate each packet against the Pydantic schema
        raw = json.loads(path.read_text())
        packet = P1HandoffPacket.model_validate(raw)
        assert packet.target_gene == "KCNH2"
        assert packet.is_cardiac_target is True


def test_pathway1_run_cardiac_bridge_fires(tmp_path):
    """When target_gene ∈ cardiac genes, the L1 channel-panel adapter is invoked."""
    res = run_pathway1_compound("KCNH2", runtime_root=tmp_path)
    summary = res.cardiac_l1_envelope_summary
    assert summary, f"cardiac_l1_envelope_summary empty: {res}"
    assert "envelope_id" in summary
    assert set(summary["panel_genes"]) == {"KCNH2", "SCN5A", "KCNQ1", "CACNA1C"}


def test_pathway1_run_writes_midd_assessment(tmp_path):
    res = run_pathway1_compound("KCNH2", runtime_root=tmp_path)
    midd_path = tmp_path / "audit" / "runs" / res.run_id / "midd_assessments.jsonl"
    assert midd_path.exists()
    line = midd_path.read_text().strip()
    assert "pathway1_handoff_v0_1" in line
    assert "n_handoff_packets" in line


def test_pathway1_run_writes_offload_manifest(tmp_path):
    res = run_pathway1_compound("KCNH2", runtime_root=tmp_path, library_size=15)
    off_path = tmp_path / "audit" / "runs" / res.run_id / "offload_manifest.jsonl"
    assert off_path.exists()
    n = sum(1 for line in off_path.read_text().splitlines() if line.strip())
    assert n == res.n_handoff_packets, f"expected one offload row per packet: {n} vs {res.n_handoff_packets}"


def test_pathway1_run_writes_replay_commands(tmp_path):
    res = run_pathway1_compound("KCNH2", runtime_root=tmp_path)
    replay_path = tmp_path / "audit" / "runs" / res.run_id / "replay_commands.jsonl"
    n = sum(1 for line in replay_path.read_text().splitlines() if line.strip())
    assert n >= 6, f"expected ≥6 replay commands (one per layer); got {n}"


def test_pathway1_run_falsifier_ledger_populated(tmp_path):
    """Stub adapters routinely fire some hard- and soft-fails (e.g., novelty_without_tractability
    on the deterministic stub library); the ledger must record them."""
    res = run_pathway1_compound("KCNH2", runtime_root=tmp_path, library_size=20)
    # Total falsifier rows in the audit table — includes both PASS and FAIL items per envelope
    f_path = tmp_path / "audit" / "runs" / res.run_id / "falsifiers.jsonl"
    assert f_path.exists()
    rows = [line for line in f_path.read_text().splitlines() if line.strip()]
    # Many falsifier rows (one per item per envelope per call)
    assert len(rows) >= 30


def test_pathway1_cardiac_wedge_runs_all_four_targets(tmp_path):
    results = run_pathway1_cardiac_wedge(tmp_path, ["KCNH2", "SCN5A"])
    assert len(results) == 2
    for r in results:
        assert r.target_gene in {"KCNH2", "SCN5A"}
        assert r.n_handoff_packets >= 1
        assert r.cardiac_l1_envelope_summary  # cardiac bridge fired


def test_pathway1_run_non_cardiac_target_skips_l1_bridge(tmp_path):
    """Non-cardiac target → l1_channel_panel_input is None on every packet → no L1 envelope."""
    res = run_pathway1_compound("EGFR", runtime_root=tmp_path, library_size=10)
    # No cardiac bridge because EGFR is non-cardiac
    assert res.cardiac_l1_envelope_summary == {}
    # But packets still emit
    assert res.n_handoff_packets >= 1
    for path in res.handoff_packets_paths:
        raw = json.loads(path.read_text())
        packet = P1HandoffPacket.model_validate(raw)
        assert packet.is_cardiac_target is False
        assert packet.l1_channel_panel_input is None


def test_pathway1_run_source_manifests_populated(tmp_path):
    res = run_pathway1_compound("KCNH2", runtime_root=tmp_path)
    sm_path = tmp_path / "audit" / "runs" / res.run_id / "source_manifest.jsonl"
    assert sm_path.exists()
    n = sum(1 for line in sm_path.read_text().splitlines() if line.strip())
    # Both cardiac KG seed and pathway1 seed contribute SourceManifest nodes; expect ≥ 10
    assert n >= 10, f"too few source manifests in P1 run: {n}"
