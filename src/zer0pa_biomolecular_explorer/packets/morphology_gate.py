"""Morphology gate (PRD section 7).

Pre-registered thresholds:
  - Median absolute QT error <= 5 ms vs locked reference extractor/table
  - 95th percentile QT error <= 15 ms
  - Analogous QRS, PR, ST/T morphology thresholds
  - Any NaN, nonfinite, silent interpolation, or missing fiducial blocks the packet.

Implementation note: this module is deterministic and pure. The reference
extractor is treated as a locked external (PTB-XL+ feature tables); we accept
arrays of `error_ms` per fiducial as input and report the gate result.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass
class MorphologyResult:
    fiducial: str  # "QT" | "QRS" | "PR" | "ST" | "T_amplitude"
    median_abs_error_ms: float
    p95_abs_error_ms: float
    n_samples: int
    nan_or_nonfinite_present: bool
    median_threshold_ms: float
    p95_threshold_ms: float
    passed: bool


_DEFAULT_THRESHOLDS = {
    "QT": (5.0, 15.0),
    "QRS": (3.0, 8.0),
    "PR": (4.0, 12.0),
    "ST": (15.0, 40.0),  # uV-shaped, but kept as ms-equivalent threshold per PRD
    "T_amplitude": (10.0, 25.0),
}


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = (len(sorted_vals) - 1) * (pct / 100.0)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return sorted_vals[int(idx)]
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def morphology_gate(
    fiducial: str,
    errors_ms: Sequence[float],
    median_threshold_ms: float | None = None,
    p95_threshold_ms: float | None = None,
) -> MorphologyResult:
    """Run the morphology gate on an array of |fiducial - reference| errors in ms.

    NaN or nonfinite anywhere in the input → automatic FAIL.
    """
    if fiducial not in _DEFAULT_THRESHOLDS and (
        median_threshold_ms is None or p95_threshold_ms is None
    ):
        raise ValueError(f"unknown fiducial {fiducial!r}; pass thresholds explicitly.")

    if median_threshold_ms is None or p95_threshold_ms is None:
        median_threshold_ms, p95_threshold_ms = _DEFAULT_THRESHOLDS[fiducial]

    abs_errors = [abs(e) for e in errors_ms]
    nan_present = any(
        e is None or (isinstance(e, float) and (math.isnan(e) or math.isinf(e)))
        for e in errors_ms
    )

    if nan_present or not abs_errors:
        return MorphologyResult(
            fiducial=fiducial,
            median_abs_error_ms=float("nan"),
            p95_abs_error_ms=float("nan"),
            n_samples=len(errors_ms),
            nan_or_nonfinite_present=True,
            median_threshold_ms=median_threshold_ms,
            p95_threshold_ms=p95_threshold_ms,
            passed=False,
        )

    sorted_errs = sorted(abs_errors)
    median = _percentile(sorted_errs, 50.0)
    p95 = _percentile(sorted_errs, 95.0)
    passed = median <= median_threshold_ms and p95 <= p95_threshold_ms

    return MorphologyResult(
        fiducial=fiducial,
        median_abs_error_ms=median,
        p95_abs_error_ms=p95,
        n_samples=len(errors_ms),
        nan_or_nonfinite_present=False,
        median_threshold_ms=median_threshold_ms,
        p95_threshold_ms=p95_threshold_ms,
        passed=passed,
    )
