"""Locked morphology fixture loader (Phase D.2 — operator brief 2026-04-30).

Loads per-compound morphology error arrays from `fixtures/morphology/<name>.json`
with explicit extractor provenance. NaN/inf in any fiducial array hard-stops
the run with `MorphologyFixtureError` — the cardiac packet is never assembled
on bad input.

The fixtures are LOCKED literal arrays representing the output of a research-
only PTB-XL+ extractor stub. Mechanism escalation requires replacing these
with the Runpod-real extractor.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
MORPHOLOGY_FIXTURES_DIR = REPO_ROOT / "fixtures" / "morphology"

REQUIRED_FIDUCIALS: tuple[str, ...] = ("QT", "QRS", "PR", "ST", "T_amplitude")


class MorphologyFixtureError(RuntimeError):
    """Raised on malformed or non-finite morphology fixture data — hard stop."""


def _check_finite(fiducial: str, values: list[Any]) -> list[float]:
    """Hard-stop on NaN/inf/non-numeric values in a fiducial array.

    The brief: "NaN/nonfinite must hard-stop." We refuse to feed these into
    the morphology gate at all — the run halts before the packet is assembled.
    """
    out: list[float] = []
    for i, v in enumerate(values):
        if v is None:
            raise MorphologyFixtureError(
                f"morphology fixture fiducial={fiducial!r} index={i}: None is not allowed"
            )
        try:
            f = float(v)
        except (TypeError, ValueError) as exc:
            raise MorphologyFixtureError(
                f"morphology fixture fiducial={fiducial!r} index={i}: "
                f"value {v!r} is not numeric"
            ) from exc
        if math.isnan(f) or math.isinf(f):
            raise MorphologyFixtureError(
                f"morphology fixture fiducial={fiducial!r} index={i}: "
                "NaN/inf is forbidden — hard stop"
            )
        out.append(f)
    return out


def load_morphology_fixture(compound: str) -> dict[str, Any]:
    """Load and validate a morphology fixture for `compound`.

    Returns the parsed JSON (with finite-validated arrays). Raises
    MorphologyFixtureError on missing file, missing fiducial, or NaN/inf values.

    The returned dict has shape:
      {
        "research_boundary": "...",
        "compound_inchikey": "...",
        "compound_name": "...",
        "extractor": { "name": ..., "version": ..., ... },
        "fiducials": {"QT": [...], "QRS": [...], "PR": [...], "ST": [...], "T_amplitude": [...]},
        "provenance": {...},
        "expected_morphology_gate_passes": bool,
      }
    """
    fixture_path = MORPHOLOGY_FIXTURES_DIR / f"{compound}.json"
    if not fixture_path.exists():
        raise MorphologyFixtureError(
            f"morphology fixture missing for compound={compound!r}: {fixture_path}"
        )

    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    fiducials_raw = raw.get("fiducials")
    if not isinstance(fiducials_raw, dict):
        raise MorphologyFixtureError(
            f"morphology fixture {compound}: missing or non-dict 'fiducials' key"
        )
    missing = [f for f in REQUIRED_FIDUCIALS if f not in fiducials_raw]
    if missing:
        raise MorphologyFixtureError(
            f"morphology fixture {compound}: missing required fiducials {missing}"
        )

    fiducials_clean: dict[str, list[float]] = {}
    for fid in REQUIRED_FIDUCIALS:
        arr = fiducials_raw[fid]
        if not isinstance(arr, list):
            raise MorphologyFixtureError(
                f"morphology fixture {compound}: fiducial {fid!r} must be a list"
            )
        if len(arr) == 0:
            raise MorphologyFixtureError(
                f"morphology fixture {compound}: fiducial {fid!r} is empty"
            )
        fiducials_clean[fid] = _check_finite(fid, arr)

    extractor = raw.get("extractor") or {}
    if not extractor.get("name") or not extractor.get("version"):
        raise MorphologyFixtureError(
            f"morphology fixture {compound}: extractor.name + extractor.version are required for provenance"
        )

    raw["fiducials"] = fiducials_clean
    return raw


def fixture_provenance_summary(fixture: dict[str, Any]) -> dict[str, str]:
    """Return a flat provenance summary suitable for audit/parameters records."""
    extractor = fixture.get("extractor") or {}
    provenance = fixture.get("provenance") or {}
    return {
        "extractor_name": str(extractor.get("name", "unknown")),
        "extractor_version": str(extractor.get("version", "unknown")),
        "extractor_reference_table": str(extractor.get("reference_table", "unknown")),
        "fixture_generated_at_utc": str(provenance.get("generated_at_utc", "unknown")),
        "fixture_note": str(provenance.get("note", ""))[:500],
        "fixture_compound_inchikey": str(fixture.get("compound_inchikey", "unknown")),
    }
