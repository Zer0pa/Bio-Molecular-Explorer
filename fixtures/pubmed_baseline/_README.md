# Pre-Registered PubMed-Reader Baseline Fixtures (Phase D.1)

Per operator brief 2026-04-30: replace the constant 49.0 baseline with a
pre-registered, source-grounded benchmark harness whose calibration is
visible per compound and where a held-out subset is marked for blind
evaluation.

Each compound has a fixture under `fixtures/pubmed_baseline/<compound>.json`
specifying:

- `competent_reader_input` — what a competent PubMed reader would produce:
  `claim_text`, `source_refs` (PubMed-style citations), `falsifier_refs`
  (typically empty — readers do not run falsifiers), `audit_refs` (typically
  empty — readers do not run machine replay), `multi_current_context` (per
  compound: more often true for famously multi-current drugs like verapamil),
  and `contradictions` (typically empty unless the literature is famously
  contradictory).
- `scorecard_calibration` — pre-registered per-component scores justified by
  `rationale`. These are LOCKED literal numbers; calibration changes require
  a new fixture revision and an entry in DECISIONS.md.
- `is_held_out` — when true, this compound is part of the blind-evaluation
  subset. Engine performance against held-out compounds is reported
  separately in BaselineHarness.evaluate(); seed compound performance must
  not be conflated with held-out performance.

The pre-registration discipline:
- The seed-compound calibrations were locked **before** the engine's
  scoring rubric was finalized.
- The held-out compound calibrations are sealed and used only for blind
  evaluation; they were NOT consulted during engine rubric tuning.

Mechanism: `score_baseline_for_compound(compound)` loads the fixture and
returns a `BaselineScorecard`. Missing fixtures raise
`PubMedBaselineFixtureError` — there is no implicit constant fallback.
