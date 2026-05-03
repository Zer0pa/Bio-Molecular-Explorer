# Zer0pa Bio-Molecular Explorer

> Live window into the Zer0pa lab. Bio-Molecular Explorer is a research-only evidence pipeline, not a medical product or safety certification.

## What This Is

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification. Every artifact you produce carries this boundary verbatim.

Zer0pa Bio-Molecular Explorer turns molecular research inputs into auditable, falsifier-governed biological evidence packets. The first authority wedge is cardiac: dofetilide, verapamil, ranolazine, and held-out comparators through KCNH2, SCN5A, KCNQ1, and CACNA1C under multi-current CiPA framing. FDA E14/S7B are regulatory-science anchors only; this repo does not claim regulatory compliance.

The repo currently exposes a CPU-first scaffold with contracts, audit trails, KG records, falsifier state, Runpod-sim adapters, Pathway 1 R&D front-end stubs, and an H100 completion plan. The live top gate is not a green test count. The top gate is an L6-governed authority path where scientific evidence, audit state, KG state, falsifier ledger state, and packet export all agree.

## Pipeline Mechanics

| Field | Value |
| --- | --- |
| Architecture | FALSIFICATION_ENGINE_PIPELINE |
| Primary Wedge | Cardiac evidence: dofetilide / verapamil / ranolazine plus held-out comparators |
| Targets | KCNH2, SCN5A, KCNQ1, CACNA1C |
| Execution | Local-first L2-L6 CPU scaffold; L1 REST stubs; Runpod/H100 work replaces stubs only after authority hardening |
| Mechanics | universal layer envelopes, append-only audit log, KG, falsifier ledger, L6 router/backedge propagation, blind PubMed-reader gate |
| Open Gate | WP0 authority hardening before authoritative Runpod cutover |

## Key Metrics

| Metric | Value | Baseline |
| --- | --- | --- |
| CPU scaffold tests | 768 passing at last recorded verification | unit + integration + falsification + runpod-sim surface |
| Cardiac stub-state run | 9 / 9 seed + held-out compounds pass in recorded scaffold run | not authority until real evidence and blind scoring pass |
| Falsifier surface | 16 cardiac classes + 13 Pathway 1 R&D classes | registry + negative fixtures |
| Minimum non-toy H100 completion | 60-120 H100 hours + 40-80 engineering hours | `docs/H100_COMPLETION_PLAN.md` |

> Source: `docs/H100_COMPLETION_PLAN.md`, `docs/RUNPOD_READINESS.md`, `docs/execution-report.md`, `PRD.md`, and the 2026-05-02 blocker review reflected below.

## Repo Identity

| Field | Value |
| --- | --- |
| Identifier | Bio-Molecular Explorer |
| Repository | https://github.com/Zer0pa/Bio-Molecular-Explorer |
| Portfolio | Bio-molecular research infrastructure |
| Visibility | INTERNAL |
| Default Branch | main |
| Authority Source | `PRD.md`; `docs/H100_COMPLETION_PLAN.md`; this README blocker register |
| License | No public license file in this snapshot |

## Readiness

| Field | Value |
| --- | --- |
| Evidence posture | Work-in-progress research scaffold; not a deployable medical product |
| Current state | CPU-governed scaffold with runpod-sim cutover tests and explicit H100 completion plan |
| Top acceptance gate | L6-governed packet export with blind scientific correctness, falsifier ledger, audit, and KG reconciliation |
| H100 status | ready to begin completion work; not ready for authoritative Runpod cutover |
| Next gate | WP0 authority hardening, then H100 real-artifact replacement and falsification wave |

### Honest Blocker

The current review findings control readiness. The sovereign authority metric is not met while PubMed-reader lift is synthetic or fixture-shaped, while the user-facing cardiac run can bypass L6 authority behavior, while packet assembly can read canned panels instead of validated L1-L5 evidence envelopes, while the cardiac path can write audit rows without populating the governing `FalsifierLedger`, or while `runpod-precheck` can pass invalid Runpod states. These must close before the repo can be called authoritative on H100.

## What We Prove

- The repo has a concrete CPU-side implementation surface for L1-L6 contracts, Pathway 1 R&D contracts, audit records, KG validation, falsifier registries, and packet assembly.
- Runpod-sim adapters demonstrate the intended plug-replaceability mechanism: backend swaps should preserve envelope shape, falsifier semantics, audit shape, and downstream contracts.
- The cardiac wedge is scoped around concrete compounds and ion-channel targets rather than generic drug-discovery copy.
- The workstream has an explicit H100 plan, time budget, agent topology, and decision mandate for completing the real pipeline instead of demoing a command path.
- The public-facing posture preserves blockers and non-claims rather than converting scaffold progress into a medical or regulatory readiness narrative.

## What We Don't Claim

- No diagnosis, treatment, cure, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.
- No completed end-to-end evidence pipeline yet.
- No authoritative Runpod/H100 cutover yet.
- No sovereign PubMed-reader lift until blind scientific-correctness scoring replaces packet-shape or fixture scoring.
- No governing morphology evidence until real PTB-XL+/extractor-backed fiducial artifacts are source-manifested, audited, KG-linked, and falsified.
- No Pathway 1 authority until the cardiac authority gate passes; Pathway 1 remains an R&D front-end surface.

## Verification Status

| Code | Check | Verdict |
| --- | --- | --- |
| V_01 | Canonical live-lab README spine applied with `Pipeline Mechanics` as Zone 02 | PASS |
| V_02 | Research/medical boundary preserved verbatim | PASS |
| V_03 | Visibility unchanged; repo remains INTERNAL | PASS |
| V_04 | CPU scaffold verification recorded at 768 tests before this README-only alignment | PASS |
| V_05 | Authority-path blocker remains the governing front-door gate | BLOCKED |
| V_06 | Authoritative H100 cutover remains gated until completion evidence exists | BLOCKED |

## Proof Anchors

| Path | State |
| --- | --- |
| `PRD.md` | AUTHORITY DESIGN |
| `docs/H100_COMPLETION_PLAN.md` | H100 COMPLETION PLAN |
| `docs/RUNPOD_READINESS.md` | RUNPOD SCAFFOLD STATUS |
| `docs/execution-report.md` | EXECUTION HISTORY |
| `runpod.config.yaml` | CUTOVER CONFIG |
| `src/zer0pa_biomolecular_explorer/` | IMPLEMENTATION SURFACE |

## Repo Shape

| Field | Value |
| --- | --- |
| Proof Anchors | 6 display anchors |
| Portfolio | Bio-molecular research infrastructure |
| Authority Source | `PRD.md` plus current blocker register |
| Python Package | `zer0pa-biomolecular-explorer` |
| Pipeline Code | `src/zer0pa_biomolecular_explorer/` |
| Test Surface | `tests/` |
| Fixtures / Seeds | `fixtures/`; `kg/`; `schemas/` |
| Support Sections | H100 Plan; Blocker Register; Agent Handoff; Repository Layout; Historical Notes; Provenance |

## H100 Plan

The H100 work stream is led by an Opus Max chief-engineer agent with Sonnet-level subagents at minimum, escalating to Opus-level subagents where cross-layer scientific or systems reasoning is required. The lead agent has authority to make engineering decisions that move the pipeline toward more performant, more dataful, and more powerful outcomes, provided the boundary, interface contracts, falsifier gates, audit/KG integrity, and GitHub handoff discipline are preserved.

Budget on one H100 plus engineering effort:

| Scope | GPU / engineering budget | Calendar wall clock | Meaning |
| --- | ---: | ---: | --- |
| Final authority hardening | 0-2 GPU hours | 4-8 engineering hours | Fix blockers below; mostly CPU/code work |
| H100 environment bring-up | 1-3 GPU hours | 2-4 hours | Container, drivers, repo, secrets, artifact paths, smoke run |
| Minimal governing cardiac cutover | 60-120 GPU hours + 40-80 engineering hours | 3-5 days continuous | Replace priority L1/L2/L5/reasoner stubs for seed + held-out wedge; rerun falsification |
| Enterprise cardiac pass | 120-250 GPU hours + 80-160 engineering hours | 5-10 days continuous | Broader MD/FEP sampling, repeated seeds, artifact deltas, source/audit/KG reconciliation |
| Full Pathway 1 plus cardiac authority | 180-400 GPU hours + 120-240 engineering hours | 10-21 days continuous | Add generation/screening/structure adapters after cardiac authority passes |
| Exhaustive channel/compound sweep | 500+ GPU hours | Multi-week | Scale-out phase, not first cutover |

Detailed plan: [`docs/H100_COMPLETION_PLAN.md`](docs/H100_COMPLETION_PLAN.md).

## Blocker Register

These are current authority blockers for the next engineering pass:

1. PubMed-reader lift must become a blind scientific-correctness gate, not a hard-coded or packet-shape proxy.
2. The user-facing cardiac CLI path must prove L6 governs packet generation and downstream promotion.
3. Packet assembly must consume validated L1-L5 evidence envelopes, not canned fixture panels.
4. The cardiac run must populate the governing `FalsifierLedger`, not only write audit rows.
5. `runpod-precheck` must fail invalid real-cutover states, including endpoint, GPU SKU, backend, and quarantined Pathway 1 cases.
6. Terminal L6 failures, unresolved `REROUTE`, late-layer FAIL state, orphan KG falsifiers, and `HAS_FALSIFIER` divergence must all block authority promotion.

## Agent Handoff

Read in this order when taking over the lane:

1. `PRD.md` - governing product and architecture requirements.
2. `docs/H100_COMPLETION_PLAN.md` - H100 budget, WP0-WP5, agent topology, and acceptance gates.
3. `HANDOFF-TO-OVERNIGHT-EXECUTOR.md` and `OVERNIGHT-EXECUTOR-STARTUP-PROMPT.md` - execution role and startup behavior.
4. `docs/RUNPOD_READINESS.md` and `docs/runpod-migration.md` - stub-swap and Runpod readiness surface.
5. `docs/DECISIONS.md` and `docs/CONVENTIONS.md` - decision ledger and cross-layer conventions.
6. `source-briefs/`, `briefing-pack/`, and `synthesis/` - inherited research context and cardiac wedge briefing.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `PRD.md` | Medical orchestrator PRD for long-horizon execution |
| `PATHWAY1_PRD.md` | Pathway 1 R&D front-end PRD |
| `src/zer0pa_biomolecular_explorer/` | CPU-side contracts, layers, orchestration, audit, KG, falsifiers, packets, reasoner, runpod-sim |
| `tests/` | Unit, integration, plug-swap, falsification, packet, KG, and Runpod-sim tests |
| `fixtures/` | Compound, negative, morphology, PubMed-baseline, route, SBML, and Pathway 1 fixtures |
| `kg/` | Cardiac and Pathway 1 KG seed files |
| `schemas/` | JSON schemas for envelopes, fixtures, and reasoner tuples |
| `docs/` | H100 plan, Runpod readiness, decisions, conventions, and execution report |
| `packets/` | Historical generated packet artifacts; non-governing until aligned to current authority path |
| `runtime/` | Cloud-lab dry-run defaults with interlocks on |

## Historical Notes

The previous implementation record reported 768 passing tests, a runpod-sim cutover surface, L1-L6 CPU contracts, Pathway 1 R&D stubs, cardiac packet generation, KG checks, and falsification-wave coverage. Treat those as scaffold evidence, not as final authority. The 2026-05-02 blocker register above controls current readiness.

This repository was previously named `Zer0pa/Health` (historical). Renamed to `Zer0pa/Bio-Molecular-Explorer` on 2026-05-03 as a clean pre-public rename. No compatibility aliases remain for `zer0pa-health` or `zer0pa_health`.

## Provenance

- Initial commit: 2026-04-29.
- Front-door alignment: 2026-05-02, using the orchestration-state lane-agent guidance dated 2026-05-02.
- Rename to Bio-Molecular Explorer: 2026-05-03.
- Upstream cardiac wedge context: Brain Phase 8 / Rosalind Bioelectric Translational Engine briefing pack.
- Medical orchestrator: produced `PRD.md`.
- Overnight executor: built the CPU scaffold, tests, Runpod-sim adapters, audit/KG/falsifier surface, and H100 completion artifacts.
