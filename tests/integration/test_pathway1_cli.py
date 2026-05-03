"""CLI tests for Pathway 1 commands: run-pathway1 + cutover-dryrun --layer p1."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from zer0pa_biomolecular_explorer.cli import app


def test_cli_run_pathway1_kcnh2(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["run-pathway1", "KCNH2", "--runtime", str(tmp_path), "--library-size", "10"],
    )
    assert result.exit_code == 0, result.stdout
    assert "RESEARCH USE ONLY" in result.stdout
    assert "KCNH2" in result.stdout
    assert "fired" in result.stdout  # cardiac bridge


def test_cli_run_pathway1_non_cardiac(tmp_path):
    """Non-cardiac target → l1_bridge skipped."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["run-pathway1", "EGFR", "--runtime", str(tmp_path), "--library-size", "10"],
    )
    assert result.exit_code == 0, result.stdout
    assert "EGFR" in result.stdout
    assert "skipped" in result.stdout  # cardiac bridge skipped for EGFR


def test_cli_cutover_dryrun_p1_only(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app, ["cutover-dryrun", "--runtime", str(tmp_path), "--layer", "p1"]
    )
    assert result.exit_code == 0, result.stdout
    assert "CUTOVER DRY-RUN: PASS" in result.stdout
    # All three P1 GPU-bound layers in the journal
    journal = tmp_path / "audit" / "cutover_dryrun.jsonl"
    assert journal.exists()
    lines = [line for line in journal.read_text().splitlines() if line.strip()]
    layers_journaled = {json.loads(line)["layer"] for line in lines}
    assert layers_journaled == {"P1.Structure", "P1.Generate", "P1.Screen"}


def test_cli_cutover_dryrun_all_plus_p1(tmp_path):
    """Combined sweep: existing pipeline + Pathway 1 layers."""
    runner = CliRunner()
    result = runner.invoke(
        app, ["cutover-dryrun", "--runtime", str(tmp_path), "--layer", "all+p1"]
    )
    assert result.exit_code == 0, result.stdout
    assert "CUTOVER DRY-RUN: PASS" in result.stdout
    journal = tmp_path / "audit" / "cutover_dryrun.jsonl"
    lines = [line for line in journal.read_text().splitlines() if line.strip()]
    layers_journaled = {json.loads(line)["layer"] for line in lines}
    assert layers_journaled == {"L1", "L2", "L5", "P1.Structure", "P1.Generate", "P1.Screen"}


def test_cli_cutover_dryrun_p1_structure_only(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app, ["cutover-dryrun", "--runtime", str(tmp_path), "--layer", "P1.Structure"]
    )
    assert result.exit_code == 0, result.stdout
    journal = tmp_path / "audit" / "cutover_dryrun.jsonl"
    lines = [line for line in journal.read_text().splitlines() if line.strip()]
    layers = {json.loads(line)["layer"] for line in lines}
    assert layers == {"P1.Structure"}


def test_cli_run_pathway1_writes_packets_to_disk(tmp_path):
    runner = CliRunner()
    runner.invoke(
        app,
        ["run-pathway1", "KCNH2", "--runtime", str(tmp_path), "--library-size", "10"],
    )
    packets_dir = tmp_path / "packets" / "pathway1"
    assert packets_dir.is_dir()
    # Filter to P1 handoff packets specifically — the cardiac evidence packet
    # written alongside (cardiac_evidence_packet_p1__*) has a different schema.
    handoff_packets = list(packets_dir.glob("p1_handoff__*.json"))
    assert len(handoff_packets) >= 1
    raw = json.loads(handoff_packets[0].read_text())
    assert raw["target_gene"] == "KCNH2"
    assert raw["is_cardiac_target"] is True
    assert raw["l1_channel_panel_input"] is not None
