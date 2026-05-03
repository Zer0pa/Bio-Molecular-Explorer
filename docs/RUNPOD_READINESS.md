# Runpod Readiness Gate

> Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.

## Purpose

This document declares which subsystems are **governing** the Runpod-readiness verdict and which are **non-governing** (built but quarantined from the authority gate). Conflating the two is the corruption pattern this document exists to prevent.

The brief from the operator (2026-04-30): "Mark Pathway 1 as non-governing until cardiac authority gate passes. Do not delete it; quarantine its claims from Runpod readiness."

## Governing subsystems (cardiac authority path)

These MUST pass for Runpod readiness to be claimed:

| Subsystem | Authority responsibility |
|---|---|
| `src/zer0pa_biomolecular_explorer/envelope.py` | Universal envelope contract — any drift kills the cutover |
| `src/zer0pa_biomolecular_explorer/contracts/{l1,l2,l2_5,l3,l4,l5,l6}.py` | Per-layer interface contracts |
| `src/zer0pa_biomolecular_explorer/audit/` | Append-only JSONL + hash chain + validator |
| `src/zer0pa_biomolecular_explorer/kg/` | Schema + store + K1-K5 validator |
| `src/zer0pa_biomolecular_explorer/falsifiers/{registry,ledger,detectors}.py` | Falsifier registry + ledger + detector functions |
| `src/zer0pa_biomolecular_explorer/orchestration/{state_graph,router,flow,dispatch}.py` | L6 router (the falsification engine itself) |
| `src/zer0pa_biomolecular_explorer/layers/{l1..l5}/` | Stub adapters for L1-L5 (cardiac path) |
| `src/zer0pa_biomolecular_explorer/runs/cardiac_run.py` + `runs/l6_orchestrated_run.py` | End-to-end run drivers |
| `src/zer0pa_biomolecular_explorer/packets/` | CardiacPacketAssembler + morphology gate + benchmark harness |
| `src/zer0pa_biomolecular_explorer/runpod_sim/{l1,l2,l5}_runpod_sim.py` + `reasoner_runpod_sim.py` | CPU-side simulations of the GPU-real adapters |
| `src/zer0pa_biomolecular_explorer/cli.py` (cardiac commands) | run-cardiac, validate-audit, validate-kg, validate-packet, runpod-precheck, cutover-dryrun (without --layer p1) |
| `tests/falsification/test_falsification_wave.py` | The 11+5 cardiac-side wave; failures block Runpod |

The cardiac authority gate is the question: does the cardiac wedge produce source-grounded, falsifiable, replayable evidence packets that beat a real PubMed-reader baseline by the pre-registered margin, with falsifier state preserved through every layer transition?

## Non-governing subsystems (Pathway 1 R&D front-end)

These are BUILT and TESTED but **do NOT count toward Runpod readiness** until the cardiac authority gate is independently satisfied.

| Subsystem | Status |
|---|---|
| `src/zer0pa_biomolecular_explorer/pathway1/` | Pathway 1 implementation (Target / Structure / Generate / Screen / Optimize / Handoff) |
| `src/zer0pa_biomolecular_explorer/runpod_sim/p1_*_runpod_sim.py` | Pathway 1 GPU-bound runpod-sim adapters |
| `tests/falsification/test_falsification_wave_pathway1.py` | The 13 R&D-specific falsifier triggers |
| `tests/integration/test_p1_*.py` | Pathway 1 integration tests |
| `tests/integration/test_pathway1_*.py` | Pathway 1 end-to-end + CLI |
| `runs/pathway1_run.py` | Pathway 1 end-to-end runner |
| `briefing-pack/Pathway1_RD_DrugDiscovery_PRD_Research.md` + `PATHWAY1_PRD.md` | Pathway 1 PRDs |

Why quarantined:

- Pathway 1 layer outputs include stub canned values for tools (REINVENT 4, DiffSBDD, Boltz-2 affinity, Chemprop ADMET, GNINA) that are GPU-bound and license-flagged.
- Pathway 1 candidates flow into the cardiac wedge via the `P1HandoffPacket → L1ChannelPanelInput` bridge, but the cardiac wedge itself is the authority surface.
- Until cardiac authority is independently validated, any "Runpod readiness" claim that includes Pathway 1's surface area would be circular: Pathway 1 outputs feed the cardiac wedge, so a defective cardiac wedge would be masked by Pathway 1's apparent passes.

## Verdict logic

`zer0pa-biomolecular-explorer runpod-precheck` returns:

- **0** (pass) iff every governing-subsystem stub-state acceptance gate is met AND every governing-subsystem cutover-state declaration is internally consistent.
- **non-zero** (block) when:
  - A `runpod_gpu` or `external_api` adapter has `endpoint: null`.
  - A `runpod_gpu` adapter has no `gpu_sku_min` declared.
  - A `cpu_lite` adapter is incorrectly flagged as `runpod_gpu`.
  - The cardiac falsification wave reports any FAIL that is not paired with a backedge_target.
  - A claimed cutover state lacks a `pre_cutover_state` annotation.
  - Any P1 layer claims `runpod_gpu` cutover without a corresponding cardiac-path acceptance gate having passed first.

When `runpod-precheck` exits 0, the result is "stub-state internally consistent". When it exits non-zero, real blockers exist.

## How to lift the quarantine

The cardiac authority gate must independently satisfy:

1. `tests/falsification/test_falsification_wave.py` — every trigger caught/audited/routed/preserved.
2. `tests/plug_swap/test_plug_replaceability.py` — Stub vs Toy + Stub vs Runpod-sim shape stability across L1-L5.
3. `tests/integration/test_cardiac_run.py` — `run_cardiac_compound()` writes all 12 audit tables; KG K1-K5 hold; reasoner tuple emitted.
4. `tests/integration/test_l6_router_run.py` — L6 router governs the run; falsifier FAIL blocks/reroutes before packet export.
5. `tests/integration/test_runpod_cutover.py` — Stub→RunpodSim envelope shape stable on L1, L2, L5.
6. The cardiac packet PubMed-reader baseline benchmark uses source-grounded expected claims (NOT a fixed 49.0 placeholder).
7. Cardiac packets are assembled from validated L1-L5 envelopes (NOT from `channel_panel_canned` fixtures).

When all seven pass, the quarantine on Pathway 1 may be reviewed. Until then, Pathway 1 is augmentation, not authority.

## Code-level enforcement

- `cli.py:runpod-precheck` rejects P1 layer cutover claims when the cardiac authority gate is not satisfied (this PR / iteration).
- `cli.py:run-cardiac` is the canonical entry point for authority-path runs. `run-pathway1` is documented as research/exploration, not authority.
- `docs/CONVENTIONS.md` §15 makes the non-governing status explicit.
- `docs/DECISIONS.md` D-028 records this decision.
