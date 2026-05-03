"""Tests for the export-finetune-corpus CLI command."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from zer0pa_biomolecular_explorer.cli import app
from zer0pa_biomolecular_explorer.runs import run_cardiac_compound


def test_export_finetune_corpus_writes_jsonl(tmp_path):
    # Generate a few cardiac runs first
    for compound in ("dofetilide", "verapamil"):
        run_cardiac_compound(compound, runtime_root=tmp_path, cmax_unbound_uM=0.001)

    out = tmp_path / "corpus.jsonl"
    runner = CliRunner()
    result = runner.invoke(
        app, ["export-finetune-corpus", str(tmp_path), "--out", str(out)]
    )
    assert result.exit_code == 0, result.stdout
    assert out.exists()

    # Stub reasoner tuples without curated ground-truth are not yet
    # corpus-eligible (PRD section 8: positives require ground_truth.status=available
    # or ground_truth.type=human_adjudication; negatives require failed/clinical_overclaim).
    # The stub emits passed+pending tuples — neither positive nor negative.
    # The corpus file may legitimately be empty until curated tuples arrive.
    lines = [line for line in out.read_text().splitlines() if line.strip()]
    for line in lines:
        rec = json.loads(line)
        assert rec["split"] in {"positive", "negative"}
        assert "tuple" in rec
        assert "tuple_id" in rec["tuple"]
    # The summary line must report numerical positives/negatives counts.
    assert "positives:" in result.stdout
    assert "negatives:" in result.stdout


def test_export_finetune_corpus_missing_dir_errors(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app, ["export-finetune-corpus", str(tmp_path), "--out", str(tmp_path / "x.jsonl")]
    )
    assert result.exit_code == 1


def test_export_finetune_corpus_summary_stdout(tmp_path):
    # Generate a run
    run_cardiac_compound("dofetilide", runtime_root=tmp_path, cmax_unbound_uM=0.001)
    out = tmp_path / "corpus.jsonl"
    runner = CliRunner()
    result = runner.invoke(
        app, ["export-finetune-corpus", str(tmp_path), "--out", str(out)]
    )
    assert result.exit_code == 0, result.stdout
    assert "positives" in result.stdout
    assert "negatives" in result.stdout
