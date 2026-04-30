"""Tests for the locked morphology fixture loader (Phase D.2).

Per operator brief 2026-04-30:
  - Morphology arrays come from locked fixtures with extractor provenance.
  - NaN/inf must hard-stop (not be allowed to flow into the morphology gate).
  - Every cardiac compound used by run-cardiac must have a fixture.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zer0pa_health.packets.morphology_fixtures import (
    MORPHOLOGY_FIXTURES_DIR,
    MorphologyFixtureError,
    REQUIRED_FIDUCIALS,
    fixture_provenance_summary,
    load_morphology_fixture,
)


def test_all_seed_compounds_have_morphology_fixture():
    """Every cardiac compound run-cardiac knows about must have a locked morphology fixture."""
    from zer0pa_health.runs.cardiac_run import _DEFAULT_CMAX_uM
    for compound in _DEFAULT_CMAX_uM:
        # Will raise if missing
        fixture = load_morphology_fixture(compound)
        assert fixture["compound_name"] == compound


def test_load_dofetilide_returns_finite_arrays():
    fixture = load_morphology_fixture("dofetilide")
    for fid in REQUIRED_FIDUCIALS:
        arr = fixture["fiducials"][fid]
        assert len(arr) > 0
        # All values are finite floats
        for v in arr:
            assert isinstance(v, float)
            assert v == v  # NaN check
            assert -1e9 < v < 1e9


def test_load_missing_compound_raises(tmp_path):
    with pytest.raises(MorphologyFixtureError, match="missing"):
        load_morphology_fixture("not_a_real_compound_zz")


def test_load_with_nan_hard_stops(tmp_path, monkeypatch):
    """A fixture with NaN in any array must hard-stop the loader."""
    bad_fixture_dir = tmp_path / "morphology"
    bad_fixture_dir.mkdir()
    bad_fixture = {
        "research_boundary": "Research use only.",
        "compound_inchikey": "BAD",
        "compound_name": "bad_compound",
        "extractor": {
            "name": "test_extractor",
            "version": "0.0.0",
            "reference_table": "test",
        },
        "fiducials": {
            "QT": [1.0, "NaN", 3.0],
            "QRS": [0.5, 0.6],
            "PR": [1.0, 1.2],
            "ST": [5.0, 6.0],
            "T_amplitude": [4.0, 5.0],
        },
        "provenance": {"generated_at_utc": "2026-04-30T00:00:00Z"},
    }
    # Replace "NaN" string with actual float('nan') so json doesn't trip
    bad_fixture["fiducials"]["QT"] = [1.0, float("nan"), 3.0]

    bad_path = bad_fixture_dir / "bad_compound.json"
    bad_path.write_text(json.dumps(bad_fixture))

    monkeypatch.setattr(
        "zer0pa_health.packets.morphology_fixtures.MORPHOLOGY_FIXTURES_DIR",
        bad_fixture_dir,
    )
    with pytest.raises(MorphologyFixtureError, match="NaN/inf is forbidden"):
        load_morphology_fixture("bad_compound")


def test_load_with_inf_hard_stops(tmp_path, monkeypatch):
    bad_fixture_dir = tmp_path / "morphology"
    bad_fixture_dir.mkdir()
    bad_fixture = {
        "research_boundary": "Research use only.",
        "compound_inchikey": "BAD",
        "compound_name": "bad_inf",
        "extractor": {
            "name": "test_extractor",
            "version": "0.0.0",
            "reference_table": "test",
        },
        "fiducials": {
            "QT": [1.0, 2.0],
            "QRS": [0.5, float("inf")],
            "PR": [1.0, 1.2],
            "ST": [5.0, 6.0],
            "T_amplitude": [4.0, 5.0],
        },
        "provenance": {"generated_at_utc": "2026-04-30T00:00:00Z"},
    }
    bad_path = bad_fixture_dir / "bad_inf.json"
    bad_path.write_text(json.dumps(bad_fixture))

    monkeypatch.setattr(
        "zer0pa_health.packets.morphology_fixtures.MORPHOLOGY_FIXTURES_DIR",
        bad_fixture_dir,
    )
    with pytest.raises(MorphologyFixtureError, match="NaN/inf is forbidden"):
        load_morphology_fixture("bad_inf")


def test_fixture_missing_extractor_provenance_rejected(tmp_path, monkeypatch):
    """A fixture without extractor.name/version must be rejected — provenance is required."""
    bad_fixture_dir = tmp_path / "morphology"
    bad_fixture_dir.mkdir()
    bad_fixture = {
        "research_boundary": "Research use only.",
        "compound_inchikey": "BAD",
        "compound_name": "no_provenance",
        "extractor": {},  # missing
        "fiducials": {
            "QT": [1.0],
            "QRS": [0.5],
            "PR": [1.0],
            "ST": [5.0],
            "T_amplitude": [4.0],
        },
    }
    (bad_fixture_dir / "no_provenance.json").write_text(json.dumps(bad_fixture))
    monkeypatch.setattr(
        "zer0pa_health.packets.morphology_fixtures.MORPHOLOGY_FIXTURES_DIR",
        bad_fixture_dir,
    )
    with pytest.raises(MorphologyFixtureError, match="extractor"):
        load_morphology_fixture("no_provenance")


def test_fixture_missing_required_fiducial_rejected(tmp_path, monkeypatch):
    bad_fixture_dir = tmp_path / "morphology"
    bad_fixture_dir.mkdir()
    bad_fixture = {
        "research_boundary": "Research use only.",
        "compound_inchikey": "BAD",
        "compound_name": "missing_fid",
        "extractor": {"name": "x", "version": "0.0.0"},
        "fiducials": {
            "QT": [1.0],
            "QRS": [0.5],
            "PR": [1.0],
            # missing ST and T_amplitude
        },
    }
    (bad_fixture_dir / "missing_fid.json").write_text(json.dumps(bad_fixture))
    monkeypatch.setattr(
        "zer0pa_health.packets.morphology_fixtures.MORPHOLOGY_FIXTURES_DIR",
        bad_fixture_dir,
    )
    with pytest.raises(MorphologyFixtureError, match="missing required fiducials"):
        load_morphology_fixture("missing_fid")


def test_provenance_summary_shape():
    fixture = load_morphology_fixture("dofetilide")
    summary = fixture_provenance_summary(fixture)
    assert summary["extractor_name"]
    assert summary["extractor_version"]
    assert summary["fixture_compound_inchikey"] == "IXTMWRCNAAVVAI-UHFFFAOYSA-N"
    assert summary["fixture_generated_at_utc"]
