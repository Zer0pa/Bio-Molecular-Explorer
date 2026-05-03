"""Tests for the cutover-dryrun CLI command."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from zer0pa_biomolecular_explorer.cli import app


def test_cutover_dryrun_all_layers_pass(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app, ["cutover-dryrun", "--runtime", str(tmp_path), "--layer", "all"]
    )
    assert result.exit_code == 0, result.stdout
    assert "CUTOVER DRY-RUN: PASS" in result.stdout

    journal = tmp_path / "audit" / "cutover_dryrun.jsonl"
    assert journal.exists()
    lines = [line for line in journal.read_text().splitlines() if line.strip()]
    assert len(lines) == 3  # L1 + L2 + L5

    for line in lines:
        rec = json.loads(line)
        assert rec["verdict"] == "PASS"
        assert rec["backend_runpod_gpu"] is True
        assert rec["shape_match"] is True
        assert rec["falsifier_classes_match"] is True


def test_cutover_dryrun_single_layer_l1(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app, ["cutover-dryrun", "--runtime", str(tmp_path), "--layer", "L1"]
    )
    assert result.exit_code == 0, result.stdout
    assert "L1: shape=True" in result.stdout

    journal = tmp_path / "audit" / "cutover_dryrun.jsonl"
    lines = [line for line in journal.read_text().splitlines() if line.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["layer"] == "L1"


def test_cutover_dryrun_unknown_layer_skipped(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app, ["cutover-dryrun", "--runtime", str(tmp_path), "--layer", "L99"]
    )
    # No matching layer; nothing tested but still PASS (vacuous)
    assert result.exit_code == 0, result.stdout
    assert "SKIP L99" in result.stdout
