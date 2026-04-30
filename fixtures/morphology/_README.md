# Morphology Fixtures (Research-Only Locked Slices)

Per operator brief 2026-04-30, cardiac runs MUST consume locked morphology
fixtures with explicit extractor provenance — not synthetic arrays generated
at runtime.

Each compound has one fixture file under `fixtures/morphology/<compound>.json`
with the following invariants:

1. `research_boundary` — the locked research-only boundary string.
2. `compound_inchikey` — must match the corresponding compound fixture in
   `fixtures/compounds/`.
3. `extractor` — name, version, reference table, and notes describing how
   the arrays were produced.
4. `fiducials` — dict of fiducial-name → list[float ms] of |error| samples
   relative to a reference extractor. Required keys: `QT`, `QRS`, `PR`,
   `ST`, `T_amplitude`. Each list MUST contain only finite values; NaN/inf
   in any array hard-stops the run via
   `zer0pa_health.packets.morphology_fixtures.load_morphology_fixture`.
5. `provenance` — generated_at timestamp + free-text note documenting that
   the values are locked stub data; mechanism escalation requires the
   Runpod-real PTB-XL+ extractor.
6. `expected_morphology_gate_passes` — boolean documenting the seed
   expectation for the morphology gate against this fixture.

Mechanism escalation requires replacing these locked stub values with output
from the Runpod-real PTB-XL+ research feature extractor (or equivalent
licensed source). The CPU-side build never imports a real extractor.
