# Zer0pa Health — Workstream Repository

Canonical home for the Zer0pa Health work stream. Multi-agent handoff: synthesis → orchestrator → overnight executor → Runpod migration. Repo is the source of truth across machines.

## Boundary

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification. Every artifact you produce carries this boundary verbatim.

## What is in here

| Path | Purpose | Author role |
|---|---|---|
| `MODUS-OPERANDI.md` | Reusable pattern for how Zer0pa work streams are run end-to-end | Synthesis agent |
| `HANDOFF-TO-ORCHESTRATOR.md` | Health-specific brief for the next agent (the medical orchestrator) — defines what they inherit and what they must produce | Synthesis agent |
| `ORCHESTRATOR-STARTUP-PROMPT.md` | The exact prompt the user pastes into a fresh agent session to spin up the medical orchestrator | Synthesis agent |
| `source-briefs/` | Inherited research input — the two technology landscape briefs (April 2026) | External (consumer of synthesis) |
| `briefing-pack/` | Seven-doc primer for a science / medical thinking agent on the cardiac wedge (RBTE) | Synthesis agent |
| `synthesis/` | Fresh-eyes reading of the source briefs — what the briefs do not yet see, build ambition, falsification-engine reframe | Synthesis agent |
| `PRD.md` | The PRD that drives the overnight long-horizon execution on a Runpod-bound machine | Medical orchestrator |
| `pyproject.toml` + `src/zer0pa_health/` | CPU-side falsification engine implementation | Overnight executor |
| `schemas/` | JSON Schemas (envelope, reasoner tuple, …) | Overnight executor |
| `fixtures/` | Compound seeds (dofetilide/verapamil/ranolazine), negative fixtures, routes, SBML | Overnight executor |
| `kg/cardiac_seed.jsonl` | Cardiac wedge KG seed (33 nodes, 21 edges) | Overnight executor |
| `packets/` | Generated cardiac evidence packets + benchmark summary | Overnight executor |
| `tests/` | Unit + integration + plug-swap + falsification wave (768 tests as of Iteration 8) | Overnight executor |
| `runpod.config.yaml` + `docs/runpod-migration.md` | Stub-swap cutover config and procedure | Overnight executor |
| `docs/H100_COMPLETION_PLAN.md` | Enterprise-grade H100 completion plan, remaining blockers, wall-clock budget | Runpod readiness reviewer |
| `runtime/cloud_lab.config.yaml` | Cloud-lab dry-run defaults (disabled, interlocks on) | Overnight executor |

## Read order for the next agent

1. `MODUS-OPERANDI.md` — how the role chain works.
2. `HANDOFF-TO-ORCHESTRATOR.md` — what you (medical orchestrator) inherit and produce.
3. `source-briefs/01-full-technology-landscape.md` and `source-briefs/02-corrections-and-architecture.md` — original technology landscape with corrections and L2.5 retrosynthesis insertion.
4. `briefing-pack/README.md` then the six numbered docs (1-scope, 2-charter, 3-inherited, 4-current-thinking, 5-open-questions, 6-evidence-and-data-map) — the cardiac wedge from the parallel RBTE work stream.
5. `synthesis/01-fresh-eyes-on-pipeline-briefs.md` — synthesis-agent reframe of the briefs; this is the substrate for your own fresh-eyes augmentation.

## Implementation status (overnight execution, 2026-04-30, 8 iterations)

- **Tests**: 768 passing (unit + integration + plug-swap + falsification wave + cardiac packet + Runpod cutover acceptance + L6 router backedge re-execution + reasoner sim + dispatcher sim + Pathway 1 R&D front-end + P1 → L1 → CardiacEvidencePacket end-to-end + L6 governance block-export gate + K1-K5 KG constraints + locked morphology fixtures + per-compound PubMed baselines + plug-swap signature/audit-shape hardening).
- **Pipelines**: TWO ends — front-end (Pathway 1 R&D / Drug Discovery) + back-end (cardiac safety wedge).
- **Layers**: L1 (REST stubs + canned outputs for the cardiac wedge), L2 (property/formulation with L2.5 back-edge), L2.5 (retrosynthesis with RXNSMILES + atom-map validators), L3 (process + mass balance), L4 (FMU/Ditto sensor twin), L5 (PKPD + cardiac exposure-channel bridge), L6 (LangGraph-shaped router with silent_falsifier_loss preservation).
- **Cross-cutting**: universal layer envelope (Pydantic + JSON Schema), append-only audit log with hash chain, KG with cardiac seed (33 nodes, 21 edges), 16-class falsifier registry with 13 detectors, falsifier ledger, self-bootstrapping reasoner with PRD-shaped tuples and clinical-overclaim self-policing, cloud-lab dry-run adapters (Strateos/Emerald/Arctoris) with hard interlocks.
- **Cardiac wedge deliverable**: governing authority-path runs use `zer0pa-health run-cardiac` and validated L1-L5 envelopes. Legacy script-generated packet artifacts are non-governing until updated to the same path. The seed wedge currently produces dofetilide PASS / verapamil PASS / ranolazine PASS with per-compound PubMed-baseline lift in the ~50 point range.
- **Plug-replaceability**: nine tests covering all six layers + L6 router + cross-layer contract version invariant. Pass.
- **Falsification wave**: every named trigger (invalid SMILES, missing RXNSMILES/atom-map, mass balance, L4 sensor, SBML, hERG-only, clinical-overclaim, stub-laundering, missing falsifier ref, plug regression, NaN ECG, codec-as-mechanism, noise-brittle phenotype, license drift, silent falsifier loss, PubMed no-value-add) caught, audited, routed, and preserved in the ledger. Pass.
- **Runpod migration scaffold**: `runpod.config.yaml` + `docs/runpod-migration.md` define the intended stub-swap procedure. Backend flag flip per adapter is the target migration mechanism after the H100 blockers below are closed.
- **Cutover demonstrated in code**: L1, L2, L5 GPU-bound layers, the TxGemma reasoner, and the Parsl-shaped dispatcher all have CPU-side `*RunpodSimAdapter` / `RunpodSimDispatcher` implementations that satisfy the same Protocols as the real GPU adapters will. `zer0pa-health cutover-dryrun` flips all layers in one command and verifies envelope shape + falsifier classes + backend flag are stable in runpod-sim mode only.
- **L6 closed-loop routing**: the router doesn't just walk forward — it re-executes upstream layers when a back-edge is propagated, capped per-layer (budget=2) and globally (max=12), with `is_reexecution` flag on the step record.
- **CLI**: `zer0pa-health {run-cardiac, run-pathway1, validate-audit, validate-kg, validate-packet, runpod-precheck, graph-export, bundle, compare-runs, health-check, export-finetune-corpus, cutover-dryrun}` are all wired and tested. `cutover-dryrun --layer all+p1` exercises every GPU-bound adapter swap in one shot.

### Pathway 1 (R&D / Drug Discovery front-end)

- **Layers**: P1.Target (target identification → UniProt + druggability), P1.Structure (OpenFold3 / Boltz-2 stubs → mmCIF + binding pocket), P1.Generate (REINVENT 4 / DiffSBDD stubs → candidate library), P1.Screen (Boltz-2 affinity + Chemprop ADMET + selectivity + SA score → ranked hits), P1.Optimize (BoTorch + Ax + REINVENT 4 RL on CPU → optimized leads), P1.Handoff (CRO-ready dossier; cardiac targets get an `l1_channel_panel_input` block).
- **Falsifier registry +13 R&D classes**: target_validation_overreach, hit_from_noise, lead_without_physchem_feasibility, novelty_without_tractability, ip_chemspace_drift, alphafold_d_leakage, benchmark_leakage, pretrained_hallucination, gpt_rosalind_unavailable, structure_confidence_below_threshold, selectivity_not_assessed, synthesis_route_absent, confidence_tier_overclaim. **Sanitization extended**: AlphaFold AF IDs, leaked InChIKeys, and Enamine catalogue SMILES are sha256-prefix-hashed in evidence; never echoed verbatim.
- **6 target fixtures + 12 hit fixtures + 18 negative fixtures** + JSON Schemas. Cardiac targets (KCNH2/SCN5A/KCNQ1/CACNA1C) bridge into the existing cardiac wedge; non-cardiac (EGFR/BACE1) framing for general-pipeline.
- **KG seed extension** (`kg/pathway1_seed.jsonl`, +17 nodes / +13 edges). Combined cardiac+P1 KG: 50 nodes, 35 edges. K1-K5 hold.
- **End-to-end runner** (`runs/pathway1_run.py`): walks all 6 P1 layers, bridges into existing L1 cardiac panel, writes all 12 audit tables, emits handoff packets, emits a reasoner tuple, and assembles a `CardiacEvidencePacket` from the leading P1 candidate. Smoke result for KCNH2: engine score 96.25 / baseline 49.0 / lift +47.25.
- **Cutover acceptance**: `P1StructureRunpodSimAdapter`, `P1GenerateRunpodSimAdapter`, `P1ScreenRunpodSimAdapter` mirror the existing pipeline's runpod-sim pattern. `cutover-dryrun --layer p1` PASSES.

## Iteration 8 (2026-04-30) — Authority-path defects addressed in scaffold

The 2026-05-01 H100 review below is controlling where it identifies residual edge blockers. Do not treat this historical iteration summary as authoritative Runpod readiness.

Twelve operator-brief items closed; details in `docs/execution-report.md` and DECISIONS D-030 through D-038. Highlights:

- **L6 router governs `run-cardiac`** — falsifier FAIL produces a router BLOCK that prevents packet export; CLI exits 2 on block.
- **Cardiac packet is assembled from validated L1 envelopes**, not from `fixture["channel_panel_canned"]`. `require_envelope=True` for production runs.
- **`FalsifierLedger` mirror is mandatory**; `reconcile_ledger_audit_kg` raises on audit/ledger/KG divergence.
- **K1-K5 enforced** — true `NodeType.AUDIT_RECORD`; K2 codec-not-mechanism, K4 layer-coverage L1-L6, K5 episode-no-evidence all enforced via `KGValidator.validate_cardiac()`.
- **Locked morphology fixtures** under `fixtures/morphology/` with extractor provenance; NaN/inf hard-stop via `MorphologyFixtureError`.
- **Per-compound PubMed baselines** under `fixtures/pubmed_baseline/`; held-out subset (moxifloxacin / diltiazem / mexiletine / lidocaine) reserved for blind evaluation; constant 49.0 baseline replaced.
- **Plug-swap hardening** — adapter signatures, audit-shape sha256:64-hex format, nested schema compatibility, falsifier-class preservation between Stub and Toy.
- **`runpod-precheck` exits 3 on adapter blockers, 4 on structural defects**; parked-work fixture files exist on disk under `fixtures/canned/{l1,l2,reasoner}/`.
- **Pathway 1 quarantined** (D-028); P1 cardiac packet uses no calibrated baseline; ADMET hERG IC50 marked as informational only, not channel-panel evidence.

## H100 Completion Status (2026-05-01)

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification. Every artifact you produce carries this boundary verbatim.

This repository is **not complete end-to-end** and must not be treated as a demo-grade success. The current state is a CPU-governed scaffold with strong contracts, audit, KG, falsifiers, and Runpod-sim cutover tests. The H100 should now be used to complete the governing pipeline by replacing named stubs with real artifacts and proving that falsifier behavior, audit state, KG state, and downstream packet generation survive the swap.

Execution mandate: the H100 work stream is led by an Opus Max chief-engineer agent with Sonnet-level subagents at minimum, escalating to Opus-level subagents where cross-layer scientific or systems reasoning is required. The lead agent has authority to make engineering decisions that move the pipeline toward more performant, more dataful, and more powerful outcomes, provided the boundary, interface contracts, falsifier gates, audit/KG integrity, and GitHub handoff discipline are preserved.

Current verification on `a8ea6e8`:

- `pytest -q`: 768 passing.
- `zer0pa-health health-check`: passing.
- `zer0pa-health runpod-precheck`: stub-state internally consistent.
- `zer0pa-health cutover-dryrun --layer all+p1`: passing against runpod-sim adapters.
- `zer0pa-health run-cardiac all+held-out`: 9/9 passing in stub-state with audit/KG validation.

Remaining blockers before authoritative Runpod cutover:

1. Terminal L6 failures must block packet export even when represented as unresolved `REROUTE` or late-layer FAIL state.
2. `runpod-precheck` must reject every invalid cutover state, including missing `gpu_sku_min`, invalid `external_api`, and quarantined P1 `runpod_gpu` claims.
3. Audit/ledger/KG reconciliation must fail on KG-only orphan falsifiers and `HAS_FALSIFIER` divergence.
4. Morphology fixtures are locked replay stubs, not real PTB-XL+/extractor evidence. Real morphology evidence must replace or explicitly remain non-governing.
5. PubMed-reader lift must become a blind scientific-correctness gate, not a packet-shape or fixture-scoring proxy.
6. Legacy packet scripts and committed packet summaries must not contradict the governing `run-cardiac` authority path.

Budget on one H100 plus engineering effort:

| Scope | GPU / engineering budget | Calendar wall clock | Meaning |
|---|---:|---:|---|
| Final authority hardening | 0-2 GPU hours | 4-8 engineering hours | Fix blockers above; mostly CPU/code work |
| H100 environment bring-up | 1-3 GPU hours | 2-4 hours | Container, drivers, repo, secrets, artifact paths, smoke run |
| Minimal governing cardiac cutover | 60-120 GPU hours + 40-80 engineering hours | 3-5 days continuous | Replace priority L1/L2/L5/reasoner stubs for seed + held-out wedge; rerun falsification |
| Enterprise cardiac pass | 120-250 GPU hours + 80-160 engineering hours | 5-10 days continuous | Broader MD/FEP sampling, repeated seeds, artifact deltas, source/audit/KG reconciliation |
| Full Pathway 1 plus cardiac authority | 180-400 GPU hours + 120-240 engineering hours | 10-21 days continuous | Adds generation/screening/structure adapters; P1 remains non-governing until cardiac gate passes |
| Exhaustive channel/compound sweep | 500+ GPU hours | Multi-week | Scale-out phase, not first cutover |

Detailed plan: [`docs/H100_COMPLETION_PLAN.md`](docs/H100_COMPLETION_PLAN.md).

## Provenance

- Initial commit: 2026-04-29.
- Upstream: Brain Phase 8 (Rosalind Bioelectric Translational Engine selection) at `/Users/Zer0pa/orchestration-state/.gpd/phases/08-rosalind-bioelectric-translational-engine/`. Summarised faithfully in `briefing-pack/03-inherited-from-brain.md`; raw artifacts can be requested if the orchestrator needs more depth than the briefing pack carries.
- Synthesis agent: Claude Opus 4.7 (1M context).
- Medical orchestrator: produced `PRD.md`.
- Overnight executor: Claude Opus 4.7 lead with Sonnet subagents (L1/L2/L2.5/L3/L4/L5/reasoner/cloud-lab).
