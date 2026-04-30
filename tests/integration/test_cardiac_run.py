"""End-to-end cardiac run tests.

Exercises run_cardiac_compound() and run_cardiac_wedge(), checking that:
  - All 12 audit tables are populated
  - The audit hash chain validates
  - The KG runtime nodes/edges are emitted
  - The reasoner queue gets a tuple
  - The packet is generated and re-validates
  - The PubMed lift is reported
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from zer0pa_health.audit import AuditValidator
from zer0pa_health.cli import app
from zer0pa_health.kg import KGStore, KGValidator
from zer0pa_health.packets import CardiacEvidencePacket
from zer0pa_health.reasoner.queue import ReasonerQueue
from zer0pa_health.runs import run_cardiac_compound, run_cardiac_wedge


def test_run_cardiac_compound_writes_all_audit_tables(tmp_path):
    res = run_cardiac_compound("dofetilide", runtime_root=tmp_path, cmax_unbound_uM=0.001)
    expected = {
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
        "offload_manifest",
        "midd_assessments",
    }
    assert expected <= set(res.audit_table_counts.keys())
    # All 12 tables should have at least one row except offload_manifest (one) and midd_assessments (one)
    nonempty = {t for t, n in res.audit_table_counts.items() if n > 0}
    assert expected <= nonempty, f"empty tables: {expected - nonempty}"


def test_run_cardiac_compound_audit_validates(tmp_path):
    res = run_cardiac_compound("dofetilide", runtime_root=tmp_path, cmax_unbound_uM=0.001)
    counts = AuditValidator(tmp_path / "audit", res.run_id).validate()
    # Validator returns per-table counts; runs.jsonl must have exactly 1 entry
    assert counts.get("runs", 0) == 1
    assert counts.get("molecules", 0) == 1


def test_run_cardiac_compound_kg_runtime_writes(tmp_path):
    res = run_cardiac_compound("verapamil", runtime_root=tmp_path, cmax_unbound_uM=0.05)
    store = KGStore(tmp_path / "kg")
    KGValidator(store).validate()
    # Runtime nodes: at least 6 OutputEnvelopes (one per layer L1, L2, L2.5, L3, L4, L5)
    # plus 6 ToolAdapters, 1 Compound, 1 EvidencePacket, ≥1 Claim, 1 ReasonerTuple
    assert res.kg_runtime_nodes >= 14, f"got {res.kg_runtime_nodes} runtime nodes"
    assert res.kg_runtime_edges >= 2


def test_run_cardiac_compound_reasoner_tuple_emitted(tmp_path):
    res = run_cardiac_compound("ranolazine", runtime_root=tmp_path, cmax_unbound_uM=2.0)
    queue = ReasonerQueue(queue_path=tmp_path / "reasoner_queue", run_id=res.run_id)
    tuples = list(queue.iter())
    assert len(tuples) == 1
    t = tuples[0]
    assert t.run_id == res.run_id
    assert t.task_type.value in {
        "evidence_packet",
        "mechanism_bridge",
        "falsifier_generation",
        "conflict_resolution",
        "audit_summary",
        "route_selection",
    }


def test_run_cardiac_compound_packet_is_loadable(tmp_path):
    res = run_cardiac_compound("dofetilide", runtime_root=tmp_path, cmax_unbound_uM=0.001)
    raw = res.packet_path.read_text()
    packet = CardiacEvidencePacket.model_validate_json(raw)
    assert packet.compound.name == "dofetilide"
    assert packet.verdict.value == "pass"
    assert packet.research_boundary.startswith("Research use only")


def test_run_cardiac_wedge_three_compounds(tmp_path):
    results = run_cardiac_wedge(tmp_path, ["dofetilide", "verapamil", "ranolazine"])
    assert len(results) == 3
    names = [r.compound for r in results]
    assert sorted(names) == ["dofetilide", "ranolazine", "verapamil"]
    # All three must verdict=pass per the seed packet expectations
    for r in results:
        assert r.packet_verdict == "pass", f"{r.compound} verdict {r.packet_verdict}"
        assert r.pubmed_lift > 10.0


def test_cli_run_cardiac_dofetilide(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app, ["run-cardiac", "dofetilide", "--runtime", str(tmp_path)]
    )
    assert result.exit_code == 0, result.stdout
    assert "RESEARCH USE ONLY" in result.stdout
    assert "dofetilide" in result.stdout
    assert "pass" in result.stdout


def test_cli_runpod_precheck():
    runner = CliRunner()
    result = runner.invoke(app, ["runpod-precheck"])
    assert result.exit_code == 0, result.stdout
    assert "Acceptance gates declared" in result.stdout


def test_cli_validate_packet(tmp_path):
    """Generate a packet via the runner, then validate it via the CLI."""
    res = run_cardiac_compound("dofetilide", runtime_root=tmp_path, cmax_unbound_uM=0.001)
    runner = CliRunner()
    result = runner.invoke(app, ["validate-packet", str(res.packet_path)])
    assert result.exit_code == 0, result.stdout
    assert '"verdict": "pass"' in result.stdout
    assert "lift" in result.stdout


def test_cli_validate_kg_runtime(tmp_path):
    run_cardiac_compound("dofetilide", runtime_root=tmp_path, cmax_unbound_uM=0.001)
    runner = CliRunner()
    result = runner.invoke(app, ["validate-kg", str(tmp_path)])
    assert result.exit_code == 0, result.stdout


def test_cli_graph_export(tmp_path):
    run_cardiac_compound("dofetilide", runtime_root=tmp_path, cmax_unbound_uM=0.001)
    runner = CliRunner()
    out_dot = tmp_path / "kg.dot"
    result = runner.invoke(
        app, ["graph-export", str(tmp_path / "kg"), "--out", str(out_dot)]
    )
    assert result.exit_code == 0, result.stdout
    assert out_dot.exists()
    content = out_dot.read_text()
    assert "digraph zer0pa_health_kg" in content
    assert " -> " in content


def test_cli_validate_audit(tmp_path):
    res = run_cardiac_compound("dofetilide", runtime_root=tmp_path, cmax_unbound_uM=0.001)
    runner = CliRunner()
    result = runner.invoke(
        app, ["validate-audit", str(tmp_path), res.run_id]
    )
    assert result.exit_code == 0, result.stdout
    assert "runs" in result.stdout


def test_run_cardiac_compound_replay_commands_present(tmp_path):
    """Per PRD section 11: replay_commands.jsonl must be populated per run."""
    res = run_cardiac_compound("dofetilide", runtime_root=tmp_path, cmax_unbound_uM=0.001)
    replay_path = tmp_path / "audit" / "runs" / res.run_id / "replay_commands.jsonl"
    assert replay_path.exists()
    n_lines = sum(1 for line in replay_path.read_text().splitlines() if line.strip())
    assert n_lines >= 6  # at least one per layer (L1, L2, L2.5, L3, L4, L5)


def test_run_cardiac_compound_midd_assessment_present(tmp_path):
    res = run_cardiac_compound("dofetilide", runtime_root=tmp_path, cmax_unbound_uM=0.001)
    midd_path = tmp_path / "audit" / "runs" / res.run_id / "midd_assessments.jsonl"
    assert midd_path.exists()
    line = midd_path.read_text().strip()
    assert "engine_score" in line
    assert "pubmed_lift" in line


def test_run_cardiac_compound_offload_manifest_present(tmp_path):
    res = run_cardiac_compound("dofetilide", runtime_root=tmp_path, cmax_unbound_uM=0.001)
    off_path = tmp_path / "audit" / "runs" / res.run_id / "offload_manifest.jsonl"
    assert off_path.exists()
    line = off_path.read_text().strip()
    assert "Architect-Prime" in line


def test_run_cardiac_source_manifest_populated_from_kg_seed(tmp_path):
    """Per PRD section 6: every run must populate source_manifest.jsonl."""
    res = run_cardiac_compound("dofetilide", runtime_root=tmp_path, cmax_unbound_uM=0.001)
    sm_path = tmp_path / "audit" / "runs" / res.run_id / "source_manifest.jsonl"
    assert sm_path.exists()
    n = sum(1 for line in sm_path.read_text().splitlines() if line.strip())
    # cardiac_seed has 6 SourceManifest nodes — every one should be reflected
    assert n >= 5, f"expected >= 5 source manifest entries, got {n}"
