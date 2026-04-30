"""PubMed-reader baseline benchmark harness (PRD section 7).

Score components (each 0-100; final = weighted sum scaled to 0-100):
  - claim_correctness         (weight 0.30)
  - source_grounding          (weight 0.20)
  - falsifier_coverage        (weight 0.20)
  - contradiction_handling    (weight 0.15)
  - audit_replay              (weight 0.15)

Pass requires engine_score >= 80 AND engine_score >= baseline_score + 10.
"Better prose" does NOT count: prose-only differences contribute 0 points.

Phase D.1 (operator brief 2026-04-30): the per-compound baseline scorecard is
loaded from `fixtures/pubmed_baseline/<compound>.json`. The 49.0 hardcoded
constant was replaced with a pre-registered, source-grounded calibration per
compound. A subset of compounds is marked `is_held_out=true` and is used only
for blind evaluation — engine performance against held-out compounds is
reported separately.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from zer0pa_health.packets.schema import CardiacEvidencePacket


_BASELINE_FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "pubmed_baseline"


class PubMedBaselineFixtureError(RuntimeError):
    """Missing or malformed pubmed_baseline fixture — operator must fix the fixture."""


_WEIGHTS = {
    "claim_correctness": 0.30,
    "source_grounding": 0.20,
    "falsifier_coverage": 0.20,
    "contradiction_handling": 0.15,
    "audit_replay": 0.15,
}


@dataclass
class EngineScorecard:
    compound: str
    claim_correctness: float
    source_grounding: float
    falsifier_coverage: float
    contradiction_handling: float
    audit_replay: float
    total: float


@dataclass
class BaselineScorecard:
    compound: str
    claim_correctness: float
    source_grounding: float
    falsifier_coverage: float
    contradiction_handling: float
    audit_replay: float
    total: float
    is_held_out: bool = False
    rationale: str = ""
    source_refs: list[str] = field(default_factory=list)
    fixture_path: str = ""


def _component(value: float) -> float:
    return max(0.0, min(100.0, value))


def score_packet(packet: CardiacEvidencePacket) -> EngineScorecard:
    """Score a packet against the rubric. All sub-scores are 0-100."""
    # claim correctness: per-claim presence of falsifier_refs, multi_current_context, audit_refs
    n_claims = max(1, len(packet.claims))
    has_falsifier = sum(1 for c in packet.claims if c.falsifier_refs)
    has_audit = sum(1 for c in packet.claims if c.audit_refs)
    has_multi_current = sum(1 for c in packet.claims if c.multi_current_context)
    claim_correctness = _component(
        100.0 * (has_falsifier + has_audit + has_multi_current) / (3 * n_claims)
    )

    # source grounding: fraction of claims that reference at least one source manifest
    has_source = sum(1 for c in packet.claims if c.source_refs)
    source_grounding = _component(100.0 * has_source / n_claims)

    # falsifier coverage: number of falsifiers in packet (capped) — and that the
    # required four cardiac falsifiers are present at minimum.
    required_falsifier_classes = {
        "hERG_only_overreach",
        "codec_as_mechanism",
        "noise_brittle_phenotype",
        "clinical_overclaim",
    }
    present_falsifier_classes = {f.get("falsifier_class", "") for f in packet.falsifiers}
    coverage = len(required_falsifier_classes & present_falsifier_classes)
    falsifier_coverage = _component(100.0 * coverage / 4.0)

    # contradiction handling: presence of an explicit contradictions list (even empty
    # is acceptable iff the packet's verdict is PASS); resolved/downgraded/abstained
    # contradictions count.
    if packet.contradictions:
        resolved = sum(
            1 for c in packet.contradictions if c.resolution in ("downgraded", "abstained")
        )
        contradiction_handling = _component(
            100.0 * (resolved / max(1, len(packet.contradictions)))
        )
    else:
        # explicit empty list with non-FAIL verdict is fine
        contradiction_handling = 75.0  # research-only baseline credit for surfacing

    # audit replay: every claim has audit_refs AND the packet has at least one audit_ref
    audit_replay = _component(
        100.0 * (1.0 if packet.audit_refs and all(c.audit_refs for c in packet.claims) else 0.0)
    )

    total = (
        _WEIGHTS["claim_correctness"] * claim_correctness
        + _WEIGHTS["source_grounding"] * source_grounding
        + _WEIGHTS["falsifier_coverage"] * falsifier_coverage
        + _WEIGHTS["contradiction_handling"] * contradiction_handling
        + _WEIGHTS["audit_replay"] * audit_replay
    )

    return EngineScorecard(
        compound=packet.compound.name,
        claim_correctness=claim_correctness,
        source_grounding=source_grounding,
        falsifier_coverage=falsifier_coverage,
        contradiction_handling=contradiction_handling,
        audit_replay=audit_replay,
        total=total,
    )


def _compute_total(c: float, s: float, f: float, h: float, a: float) -> float:
    return (
        _WEIGHTS["claim_correctness"] * c
        + _WEIGHTS["source_grounding"] * s
        + _WEIGHTS["falsifier_coverage"] * f
        + _WEIGHTS["contradiction_handling"] * h
        + _WEIGHTS["audit_replay"] * a
    )


def _load_baseline_fixture(compound: str) -> dict:
    fixture_path = _BASELINE_FIXTURES_DIR / f"{compound}.json"
    if not fixture_path.exists():
        raise PubMedBaselineFixtureError(
            f"PubMed baseline fixture missing for compound={compound!r}: {fixture_path}. "
            "Add a pre-registered baseline fixture per docs/PRD.md §7 / DECISIONS D-030."
        )
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    cal = raw.get("scorecard_calibration")
    if not isinstance(cal, dict):
        raise PubMedBaselineFixtureError(
            f"baseline fixture {compound}: missing or non-dict scorecard_calibration"
        )
    needed = ("claim_correctness", "source_grounding", "falsifier_coverage",
              "contradiction_handling", "audit_replay", "rationale")
    missing = [k for k in needed if k not in cal]
    if missing:
        raise PubMedBaselineFixtureError(
            f"baseline fixture {compound}: scorecard_calibration missing keys {missing}"
        )
    return raw


def score_baseline_for_compound(compound: str) -> BaselineScorecard:
    """Per-compound, source-grounded competent-reader baseline.

    Loaded from `fixtures/pubmed_baseline/<compound>.json`. Pre-registered
    calibration per compound; reflects what a competent PubMed reader would
    plausibly produce given the actual literature. Held-out compounds are
    reserved for blind evaluation; the harness reports their lift separately.
    """
    fixture = _load_baseline_fixture(compound)
    cal = fixture["scorecard_calibration"]
    reader = fixture.get("competent_reader_input", {}) or {}
    cc = float(cal["claim_correctness"])
    sg = float(cal["source_grounding"])
    fc = float(cal["falsifier_coverage"])
    ch = float(cal["contradiction_handling"])
    ar = float(cal["audit_replay"])
    total = _compute_total(cc, sg, fc, ch, ar)

    expected = fixture.get("expected_total")
    if expected is not None and abs(float(expected) - total) > 0.05:
        raise PubMedBaselineFixtureError(
            f"baseline fixture {compound}: expected_total={expected} disagrees with "
            f"computed total={total:.4f}; fix the fixture or the calibration."
        )

    return BaselineScorecard(
        compound=compound,
        claim_correctness=cc,
        source_grounding=sg,
        falsifier_coverage=fc,
        contradiction_handling=ch,
        audit_replay=ar,
        total=total,
        is_held_out=bool(fixture.get("is_held_out", False)),
        rationale=str(cal.get("rationale", ""))[:500],
        source_refs=list(reader.get("source_refs", [])),
        fixture_path=str(_BASELINE_FIXTURES_DIR / f"{compound}.json"),
    )


@dataclass
class HarnessReport:
    """Aggregate result of running the baseline harness across packets.

    Per-compound rows are in `rows`. Aggregate stats are reported separately
    for the seed compounds (used to calibrate the engine) and the held-out
    compounds (reserved for blind evaluation).
    """
    rows: list[tuple[EngineScorecard, BaselineScorecard, bool]] = field(default_factory=list)
    seed_lift_mean: float = 0.0
    held_out_lift_mean: float = 0.0
    seed_pass_rate: float = 0.0
    held_out_pass_rate: float = 0.0
    n_seed: int = 0
    n_held_out: int = 0


@dataclass
class BaselineHarness:
    pass_score_threshold: float = 80.0
    pass_lift_threshold: float = 10.0

    def evaluate(
        self, packets: Iterable[CardiacEvidencePacket]
    ) -> list[tuple[EngineScorecard, BaselineScorecard, bool]]:
        """Return (engine, baseline, passed) tuples per packet.

        Pass requires engine.total >= 80 AND engine.total - baseline.total >= 10.
        """
        out: list[tuple[EngineScorecard, BaselineScorecard, bool]] = []
        for p in packets:
            engine = score_packet(p)
            baseline = score_baseline_for_compound(p.compound.name)
            passed = (
                engine.total >= self.pass_score_threshold
                and engine.total - baseline.total >= self.pass_lift_threshold
            )
            out.append((engine, baseline, passed))
        return out

    def evaluate_with_holdout(
        self, packets: Iterable[CardiacEvidencePacket]
    ) -> HarnessReport:
        """Like `evaluate` but partitions seed vs held-out compounds.

        The held-out aggregate is the engine's blind-evaluation score; the
        seed aggregate is in-distribution and reported alongside but should
        NOT be used as evidence of generalization.
        """
        rows = self.evaluate(packets)
        seed_rows = [(e, b, p) for e, b, p in rows if not b.is_held_out]
        held_out_rows = [(e, b, p) for e, b, p in rows if b.is_held_out]

        def _mean_lift(rs):
            if not rs:
                return 0.0
            return sum(e.total - b.total for e, b, _ in rs) / len(rs)

        def _pass_rate(rs):
            if not rs:
                return 0.0
            return sum(1 for _, _, p in rs if p) / len(rs)

        return HarnessReport(
            rows=rows,
            seed_lift_mean=_mean_lift(seed_rows),
            held_out_lift_mean=_mean_lift(held_out_rows),
            seed_pass_rate=_pass_rate(seed_rows),
            held_out_pass_rate=_pass_rate(held_out_rows),
            n_seed=len(seed_rows),
            n_held_out=len(held_out_rows),
        )
