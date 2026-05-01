# H100 Completion Plan

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification. Every artifact you produce carries this boundary verbatim.

## Operating Stance

This is not a demo plan. Green tests and synthetic packets do not complete the work stream. Completion means the governing cardiac path no longer depends on toy evidence, every GPU artifact is tied to an audit/KG/falsifier record, and packet export is controlled by L6 rather than by narrative success.

The H100 is for completing the enterprise pipeline, not for producing a visual proof that a command can run. Pathway 1 remains non-governing until the cardiac authority path passes with real artifacts.

## Current State

Current HEAD at review time: `a8ea6e8`.

Verified locally:

- `pytest -q`: 768 passing.
- `zer0pa-health health-check`: passing.
- `zer0pa-health runpod-precheck`: 19 stub-ready layers, 0 blockers, 0 structural defects in default stub-state.
- `zer0pa-health cutover-dryrun --layer all+p1`: passing against runpod-sim adapters.
- `zer0pa-health run-cardiac all+held-out`: 9 compounds pass in stub-state; audit and KG validation pass.

This is not sufficient for final Runpod cutover. It means the scaffold can be taken to H100 and completed.

## Remaining Non-Negotiable Blockers

1. Terminal L6 FAIL/REROUTE leakage:
   - Any unresolved failing falsifier at terminal layer must block packet export.
   - Packet export must require zero unresolved FAIL state, not only `block_count > 0`.

2. Runpod precheck enforcement:
   - `runpod-precheck` must return nonzero for missing `gpu_sku_min`, invalid `external_api`, null endpoints in real cutover state, and quarantined P1 `runpod_gpu` claims.
   - The readiness document and CLI behavior must agree.

3. Audit/ledger/KG reconciliation:
   - KG-only orphan `Falsifier` nodes must fail reconciliation.
   - `HAS_FALSIFIER` edges must reconcile to audit and ledger rows.
   - audit, ledger, and KG cannot be three partially overlapping truths.

4. Morphology evidence:
   - Current morphology fixtures are locked stub arrays.
   - Real PTB-XL+/extractor-backed fiducial data must be introduced before morphology is counted as governing evidence.
   - Until then morphology can be a replay-shape gate, not a real scientific pass.

5. Legacy contradiction cleanup:
   - `scripts/generate_cardiac_packets.py` must use the governing L1-envelope assembly path or be marked non-governing.
   - Committed `packets/summary.json` must not report stale fixed-baseline results.

6. Sovereign PubMed-reader gate:
   - PubMed lift must be evaluated as blind scientific correctness against locked claims and evidence, not by packet completeness or known fixture structure.
   - Fixture-backed baselines remain regression checks until a blind scoring procedure exists.
   - The scoring artifact must identify which claims were correct, which were unsupported, and which falsifiers should have fired.

## H100 Work Packages

### WP0: Authority Hardening

GPU need: none to minimal.

Tasks:

- Fix L6 terminal FAIL/REROUTE export blocking.
- Harden `runpod-precheck`.
- Harden audit/KG/ledger reconciliation.
- Remove or quarantine stale packet scripts/artifacts.
- Add regression tests for all fixes.

Acceptance:

- Injected L5 terminal FAIL, terminal L6 FAIL, unresolved REROUTE, and late-layer FAIL state each block packet export.
- Blocked runs produce no packet artifact, return a nonzero CLI exit, and record `block_reason` plus zero unresolved FAIL state in the final authority summary.
- `runpod-precheck` returns nonzero for missing `gpu_sku_min`, invalid `external_api`, null real-cutover endpoints, and quarantined P1 `runpod_gpu` claims.
- Orphan KG falsifier nodes and orphan/missing `HAS_FALSIFIER` edges fail reconciliation.
- PubMed-reader score cannot pass from packet structure alone.
- `scripts/generate_cardiac_packets.py` is either migrated to the governing `run-cardiac` authority path or marked non-governing in-code and in docs.
- `packets/summary.json` is regenerated from the governing authority path, quarantined, or removed from authority reporting.
- Full suite green.

Wall clock: 4-8 engineering hours.
H100 active time: 0-2 hours, only for final environment smoke.

### WP1: H100 Environment Bring-Up

Tasks:

- Clone repo on H100 machine.
- Pin git commit, Python version, CUDA, driver, container/base image.
- Install package and run full tests.
- Configure artifact root and private HF dataset or equivalent offload target.
- Record H100 SKU, driver, CUDA, package versions, git commit, and container hash in audit artifacts.

Acceptance:

- `pytest -q`, `health-check`, `runpod-precheck`, and `cutover-dryrun` pass on H100.
- No local bulk data lands in the repo.
- Secrets are not written to tracked files.

Wall clock: 2-4 hours.
H100 active time: 1-3 hours.

### WP2: Real L1 Cardiac Evidence

Tasks:

- Replace L1 structure/docking stubs for KCNH2, SCN5A, KCNQ1, CACNA1C where target structures are available or explicitly source-manifested.
- Run docking/pose or structure confidence for dofetilide, verapamil, ranolazine, and the held-out compounds.
- Add OpenMM short equilibration where it changes evidence quality.
- Add limited OpenFE/RBFE/ABFE for selected compound/channel pairs where it is meaningful.
- Preserve stub-vs-real deltas as confidence/falsifier changes, not silent overwrites.

Acceptance:

- Real artifacts replace stub markers for selected L1 calls.
- L1 envelopes validate unchanged.
- Downstream L2-L6 code does not change.
- `stub_laundering` drops only for genuinely real artifact paths.
- Falsification wave passes after real L1 replacement.

H100 active time:

- Structure/docking priority set: 8-20 hours.
- OpenMM short equilibration priority set: 12-36 hours.
- OpenFE limited seed pairs: 18-45 hours.

### WP3: Real Morphology Evidence

Tasks:

- Replace locked morphology stubs with real extractor-backed QT/QRS/PR/ST/T fiducial error slices.
- Source-manifest PTB-XL+/extractor provenance.
- Keep local data as small slices or manifests; offload bulk artifacts.
- Run NaN/nonfinite, noise, and morphology preservation falsifiers on real slices.

Acceptance:

- Morphology evidence includes source dataset IDs, extractor name/version, replay command, split/held-out discipline, and artifact manifest.
- Morphology fixture provenance no longer says "stub" for governing runs, and that wording is backed by real artifact paths rather than renamed replay arrays.
- All fiducials are represented.
- NaN/nonfinite hard-stops before packet assembly.
- Audit rows, KG nodes/edges, falsifier state, and source manifests link to every governing morphology artifact.
- Morphology is allowed into governing packet evidence only after this pass.

Wall clock: 6-12 engineering hours.
H100 active time: 0-6 hours, depending on extractor implementation.

### WP4: L2/L5/Reasoner GPU Replacement

Tasks:

- Replace DeepXDE dissolution stub where relevant.
- Replace or augment L5 PKPD/QSP stubs where GPU-backed model execution is justified.
- Bring up TxGemma 27B or selected domain reasoner only after license/terms are recorded.
- Keep reasoner non-authoritative: it critiques and proposes, it does not decide.

Acceptance:

- Same contracts and reasoner tuple schema.
- Audit records include model/weight/version/license flags.
- No clinical/regulatory language leaks into outputs.
- Fine-tune/export queue remains internal research-only.

H100 active time: 4-14 hours for first governing replacement pass.

### WP5: Full Governing Rerun

Tasks:

- Run seed wedge: dofetilide, verapamil, ranolazine.
- Run held-out set: quinidine, moxifloxacin, diltiazem, sotalol, mexiletine, lidocaine.
- Run full falsification wave after real artifacts are present.
- Validate audit, KG, ledger reconciliation.
- Compare CPU-stub vs H100-real packet deltas.
- Produce a Runpod cutover report.

Acceptance:

- All governing packets are produced by L6-governed path.
- No unresolved FAIL state survives to export.
- KG K1-K5 pass.
- audit/ledger/KG reconciliation passes.
- PubMed-reader lift remains above threshold under blind scientific-correctness scoring; fixture-backed scores are reported separately as regression checks only.
- Real artifact deltas are visible and falsifiable.

H100 active time: 8-24 hours, depending on how many real L1/L5 calls are included.

## Wall-Clock Budget

Assuming one H100 is already provisioned:

| Scope | H100 active time | Calendar wall clock | Completion meaning |
|---|---:|---:|---|
| WP0 only | 0-2 hours | 4-8 hours | Removes last readiness blockers but no real GPU evidence |
| H100 smoke plus one real adapter | 6-16 hours | 1 day | Confirms cutover mechanics with one real artifact class |
| Minimal governing cardiac completion | 60-120 hours | 3-5 days continuous | Seed + held-out wedge with priority real artifacts and falsification rerun |
| Enterprise cardiac completion | 120-250 hours | 5-10 days continuous | Broader sampling, repeated runs, robust deltas, stronger morphology/source evidence |
| Full Pathway 1 plus cardiac pipeline | 180-400 hours | 10-21 days continuous | Front-end generation/screening added after cardiac authority passes |
| Exhaustive sweep | 500+ hours | Multi-week | Scale-out phase, not first cutover |

The minimum non-toy governing cardiac path is therefore **60-120 H100-hours plus 40-80 engineering hours**. That engineering budget covers WP0/WP1/WP3 hardening, real adapter integration, source manifests, audit/KG/falsifier wiring, full-rerun debugging, and cutover reporting. Anything less is setup or partial adapter validation, not completion.

## Next Agent Instruction

Do not optimize for a narratable win. Do not report "Runpod ready" because stubs and runpod-sim pass. Complete WP0 first, then use H100 to retire named parked artifacts from the governing cardiac path. Every real H100 artifact must have:

- envelope,
- audit rows,
- KG nodes/edges,
- falsifier state,
- source manifest,
- replay or rerun command,
- cost/runtime/GPU provenance,
- CPU-stub vs H100-real delta.

If an artifact cannot meet that bar, it remains parked and non-governing.
