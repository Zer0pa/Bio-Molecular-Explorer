# Zer0pa Health — Workstream Repository

Canonical home for the Zer0pa Health work stream. Multi-agent handoff: synthesis → orchestrator → overnight executor → Runpod migration. Repo is the source of truth across machines.

## Boundary

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification. Every artifact in this repository carries this boundary.

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
| `tests/` | Unit + integration + plug-swap + falsification wave (333 tests) | Overnight executor |
| `runpod.config.yaml` + `docs/runpod-migration.md` | Stub-swap cutover config and procedure | Overnight executor |
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
- **Cardiac wedge deliverable**: three packets (dofetilide PASS / verapamil PASS / ranolazine PASS) generated via `scripts/generate_cardiac_packets.py`; balance score signs match the multi-current story (dofetilide +0.17 IKr-pure outward, verapamil −0.24 ICaL compensates, ranolazine −0.11 INaL-dominant). PubMed-baseline lift: ~47-51 points above competent-reader baseline.
- **Plug-replaceability**: nine tests covering all six layers + L6 router + cross-layer contract version invariant. Pass.
- **Falsification wave**: every named trigger (invalid SMILES, missing RXNSMILES/atom-map, mass balance, L4 sensor, SBML, hERG-only, clinical-overclaim, stub-laundering, missing falsifier ref, plug regression, NaN ECG, codec-as-mechanism, noise-brittle phenotype, license drift, silent falsifier loss, PubMed no-value-add) caught, audited, routed, and preserved in the ledger. Pass.
- **Runpod migration**: `runpod.config.yaml` + `docs/runpod-migration.md` define the stub-swap procedure; backend flag flip per adapter is the entire migration.
- **Cutover demonstrated in code**: L1, L2, L5 GPU-bound layers, the TxGemma reasoner, and the Parsl-shaped dispatcher all have CPU-side `*RunpodSimAdapter` / `RunpodSimDispatcher` implementations that satisfy the same Protocols as the real GPU adapters will. `zer0pa-health cutover-dryrun` flips all layers in one command and verifies envelope shape + falsifier classes + backend flag are stable.
- **L6 closed-loop routing**: the router doesn't just walk forward — it re-executes upstream layers when a back-edge is propagated, capped per-layer (budget=2) and globally (max=12), with `is_reexecution` flag on the step record.
- **CLI**: `zer0pa-health {run-cardiac, run-pathway1, validate-audit, validate-kg, validate-packet, runpod-precheck, graph-export, bundle, compare-runs, health-check, export-finetune-corpus, cutover-dryrun}` are all wired and tested. `cutover-dryrun --layer all+p1` exercises every GPU-bound adapter swap in one shot.

### Pathway 1 (R&D / Drug Discovery front-end)

- **Layers**: P1.Target (target identification → UniProt + druggability), P1.Structure (OpenFold3 / Boltz-2 stubs → mmCIF + binding pocket), P1.Generate (REINVENT 4 / DiffSBDD stubs → candidate library), P1.Screen (Boltz-2 affinity + Chemprop ADMET + selectivity + SA score → ranked hits), P1.Optimize (BoTorch + Ax + REINVENT 4 RL on CPU → optimized leads), P1.Handoff (CRO-ready dossier; cardiac targets get an `l1_channel_panel_input` block).
- **Falsifier registry +13 R&D classes**: target_validation_overreach, hit_from_noise, lead_without_physchem_feasibility, novelty_without_tractability, ip_chemspace_drift, alphafold_d_leakage, benchmark_leakage, pretrained_hallucination, gpt_rosalind_unavailable, structure_confidence_below_threshold, selectivity_not_assessed, synthesis_route_absent, confidence_tier_overclaim. **Sanitization extended**: AlphaFold AF IDs, leaked InChIKeys, and Enamine catalogue SMILES are sha256-prefix-hashed in evidence; never echoed verbatim.
- **6 target fixtures + 12 hit fixtures + 18 negative fixtures** + JSON Schemas. Cardiac targets (KCNH2/SCN5A/KCNQ1/CACNA1C) bridge into the existing cardiac wedge; non-cardiac (EGFR/BACE1) framing for general-pipeline.
- **KG seed extension** (`kg/pathway1_seed.jsonl`, +17 nodes / +13 edges). Combined cardiac+P1 KG: 50 nodes, 35 edges. K1-K5 hold.
- **End-to-end runner** (`runs/pathway1_run.py`): walks all 6 P1 layers, bridges into existing L1 cardiac panel, writes all 12 audit tables, emits handoff packets, emits a reasoner tuple, and assembles a `CardiacEvidencePacket` from the leading P1 candidate. Smoke result for KCNH2: engine score 96.25 / baseline 49.0 / lift +47.25.
- **Cutover acceptance**: `P1StructureRunpodSimAdapter`, `P1GenerateRunpodSimAdapter`, `P1ScreenRunpodSimAdapter` mirror the existing pipeline's runpod-sim pattern. `cutover-dryrun --layer p1` PASSES.

## Iteration 8 (2026-04-30) — Authority-path defects fixed

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

## Provenance

- Initial commit: 2026-04-29.
- Upstream: Brain Phase 8 (Rosalind Bioelectric Translational Engine selection) at `/Users/Zer0pa/orchestration-state/.gpd/phases/08-rosalind-bioelectric-translational-engine/`. Summarised faithfully in `briefing-pack/03-inherited-from-brain.md`; raw artifacts can be requested if the orchestrator needs more depth than the briefing pack carries.
- Synthesis agent: Claude Opus 4.7 (1M context).
- Medical orchestrator: produced `PRD.md`.
- Overnight executor: Claude Opus 4.7 lead with Sonnet subagents (L1/L2/L2.5/L3/L4/L5/reasoner/cloud-lab).
