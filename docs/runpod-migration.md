# Runpod Migration — Cutover Procedure

> Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.

## Premise

The CPU-side build was completed without GPU access. Every L1 GPU-bound
function is a REST stub returning canned outputs that match the real-shape
contracts. Every L2-L6 layer runs locally with small fixtures.

**Cutover = stub-swap, not architectural rewrite.** This document is the
checklist; `runpod.config.yaml` is the source of truth for the per-adapter
backend flags and parked-work manifest.

## Pre-cutover acceptance (already met on the CPU build)

- L2-L6 run locally with fixtures (✅ — see `tests/`).
- L1 exposes REST stubs with the canonical contracts (✅ — `src/zer0pa_biomolecular_explorer/layers/l1/server.py`).
- KG, audit, falsifier ledger, contracts, packets, orchestration exist (✅).
- Falsification wave catches deliberate failures (✅ — `tests/falsification/`).
- No bulk dataset is required locally (✅ — manifests + small slices only).

## Cutover steps (mirror `runpod.config.yaml.cutover.steps`)

1. **Provision Runpod**: A100 or H100 pod with the pinned container, CUDA, driver,
   package versions, and the repo's git commit hash.
2. **Flip backend flags**: per-adapter, `backend: stub → runpod_gpu`,
   `endpoint: null → <runpod-url>`.
3. **Health + capabilities probe**: every adapter returns 200 with the canonical
   research_boundary string and the right contract_version.
4. **Re-run golden seeds**: dofetilide, verapamil, ranolazine.
5. **Validate downstream compatibility**: re-run `tests/plug_swap/` with real
   adapter as B (stub as A).
6. **Confirm real artifacts replace stubs**: pose/binding/MD/FEP outputs include
   real convergence, uncertainty, and structure-basis fields. The
   `stub_laundering` falsifier item drops to PASS once the backend is no longer
   `stub`.
7. **Compare scientific deltas**: any change to cardiac balance score, channel
   ic50 distributions, or morphology gate result is recorded as a
   `confidence/falsifier` delta in the envelope, NOT silently overwritten.
8. **Write audit records**: container hash, GPU SKU, driver/CUDA, model versions,
   cost, runtime → `audit/runs/<run_id>/{runs.jsonl, model_tools.jsonl, artifacts.jsonl}`.

## Acceptance gates (must all pass)

- `GATE_NO_DOWNSTREAM_INTERFACE_CHANGE` — no L2-L6 code change required.
- `GATE_FALSIFIER_STATE_PRESERVED` — every CPU-stub falsifier item present in
  GPU envelopes (or re-emitted).
- `GATE_RESEARCH_BOUNDARY_VERBATIM` — canonical boundary string preserved.
- `GATE_AUDIT_HASH_CHAIN_VALIDATES_PRE_AND_POST` — `AuditValidator` passes on
  both halves of the run.
- `GATE_PLUG_SWAP_TEST_PASSES_WITH_REAL_ADAPTER` — `tests/plug_swap/*` green.

## Parked-work manifest

Each parked item carries: contract_id, fixture, audit_shape, falsifier state,
the runpod_or_credential_steps to execute at cutover, and the acceptance gate.
See `runpod.config.yaml` keys under `what_stays_parked_until_runpod`.

| ID | Contract | Falsifier (until backend=runpod_gpu) | Cost |
|---|---|---|---|
| parked_l1_real_diffdock_v2 | `contracts.l1.L1DockingOutput` | `stub_laundering` ON | ~$0.05 / call |
| parked_l1_real_openfe_rbfe | `contracts.l1.L1FEPOutput` | `stub_laundering` ON | ~$6 / call (3h A100) |
| parked_l1_real_openmm_md | `contracts.l1.L1MDOutput` | `stub_laundering` ON | ~$0.30 / call |
| parked_l2_deepxde_pinn | `contracts.l2.L2DissolutionOutput` | `stub_laundering` ON | ~$0.02 / call |
| parked_reasoner_txgemma_27b | `reasoner.adapter.ReasonerAdapter` | `license_drift` PENDING | ~$0.20 / call |

## Cost envelope estimate (research budget guidance only)

- Stub mode: $0.
- Per-compound full pipeline at GPU: ~$8.
- Cardiac wedge × 3: ~$24.
- Held-out benchmark × 6: ~$48.

Re-quote at cutover and write actual cost to `audit/artifacts.jsonl`.

## Reversibility

The cutover is reversible: flip `backend: runpod_gpu → stub` and
`endpoint: <url> → null` in `runpod.config.yaml`. The CPU stubs are never
deleted; they remain the ground state and the only state that runs without
external credentials. The system is a "Runpod-optional" engine; not a
"Runpod-required" engine.
