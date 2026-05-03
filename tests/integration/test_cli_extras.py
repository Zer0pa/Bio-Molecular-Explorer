"""Tests for CLI extras: bundle, compare-runs, health-check."""

from __future__ import annotations

import tarfile
from pathlib import Path

from typer.testing import CliRunner

from zer0pa_biomolecular_explorer.cli import app
from zer0pa_biomolecular_explorer.runs import run_cardiac_compound


def test_cli_bundle_creates_tarball(tmp_path):
    res = run_cardiac_compound("dofetilide", runtime_root=tmp_path, cmax_unbound_uM=0.001)
    runner = CliRunner()
    result = runner.invoke(app, ["bundle", str(tmp_path), res.run_id])
    assert result.exit_code == 0, result.stdout

    safe_id = res.run_id.replace(":", "_")
    tar_path = tmp_path / "bundles" / f"{safe_id}.tar.gz"
    assert tar_path.exists()

    # Bundle has the expected structure
    with tarfile.open(tar_path, "r:gz") as tf:
        names = tf.getnames()
    # audit/runs/<rid>/runs.jsonl in bundle
    assert any(n.endswith("runs.jsonl") for n in names)
    # KG snapshot
    assert any(n.startswith("kg/") for n in names)
    # Packet
    assert any("cardiac_evidence_packet" in n for n in names)


def test_cli_compare_runs(tmp_path):
    res_a = run_cardiac_compound("dofetilide", runtime_root=tmp_path, cmax_unbound_uM=0.001)
    res_b = run_cardiac_compound("verapamil", runtime_root=tmp_path, cmax_unbound_uM=0.05)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["compare-runs", str(tmp_path), res_a.run_id, str(tmp_path), res_b.run_id],
    )
    assert result.exit_code == 0, result.stdout
    assert "table" in result.stdout
    assert "runs" in result.stdout


def test_cli_health_check_no_runtime():
    runner = CliRunner()
    result = runner.invoke(app, ["health-check"])
    assert result.exit_code == 0, result.stdout
    assert "HEALTH CHECK PASSED" in result.stdout


def test_cli_health_check_with_runtime(tmp_path):
    run_cardiac_compound("dofetilide", runtime_root=tmp_path, cmax_unbound_uM=0.001)
    runner = CliRunner()
    result = runner.invoke(app, ["health-check", "--runtime", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    assert "HEALTH CHECK PASSED" in result.stdout


def test_cli_bundle_missing_run_id_errors(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["bundle", str(tmp_path), "run:bogus"])
    assert result.exit_code == 1
