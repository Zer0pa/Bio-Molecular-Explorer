# Zer0pa Bio-Molecular Explorer — Pathway 1 (R&D / Drug Discovery) PRD

## Boundary

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.

## 0. Position in the System

Pathway 1 is the **front-end** of the Zer0pa Bio-Molecular Explorer pipeline. It produces ranked drug candidates that hand off into the existing cardiac safety pipeline (L1–L6 in `src/zer0pa_biomolecular_explorer/layers/`) and, in future, into other downstream verticals.

```
[disease + target class]
    │
    ▼
┌───────────────────────────────────────────────────────────────┐
│  PATHWAY 1 — R&D / Drug Discovery (this PRD)                  │
│  P1.Target   →  P1.Structure  →  P1.Generate                   │
│       └──>  P1.Screen   →  P1.Optimize  →  P1.Handoff          │
└───────────────────────────────────────────────────────────────┘
    │  P1HandoffPacket (SMILES + target + ADMET + audit_refs)
    ▼
[existing Bio-Molecular Explorer pipeline L1 cardiac wedge ... cardiac packet]
```

Source: `briefing-pack/Pathway1_RD_DrugDiscovery_PRD_Research.md` (591 lines, dense research synthesis). This PRD is the *executable* spec derived from that input — the contracts, build sequence, falsifier extensions, and acceptance gates the overnight executor must produce.

## 1. Scope and Boundary

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.

In scope:

- Pathway 1 sub-layers: P1.Target, P1.Structure, P1.Generate, P1.Screen, P1.Optimize, P1.Handoff.
- New falsifier classes covering R&D-specific failure modes (target-validation overreach, hit from noise, lead without physchem feasibility, novelty without tractability, IP/chemspace drift, AlphaFold-D leakage, benchmark leakage, pretrained hallucination, GPT-Rosalind unavailability, structure-confidence below threshold, selectivity not assessed, synthesis-route absent, confidence-tier overclaim).
- Target fixtures for the four cardiac targets (KCNH2/SCN5A/KCNQ1/CACNA1C) plus two non-cardiac targets (EGFR, BACE1) — for general-pipeline framing.
- Hit fixtures (3 per cardiac target = 12).
- Handoff packet schema that bridges Pathway 1 outputs into the existing L1 cardiac contract.
- Runpod-sim adapters for the GPU-bound P1 layers (Structure, Generate, Screen).
- End-to-end run wiring P1.Target → ... → P1.Handoff → existing L1 cardiac panel → cardiac evidence packet.

Out of scope:

- Real OpenFold3 / Boltz-2 / REINVENT 4 / DiffSBDD inference (these become Runpod adapters at cutover).
- Real Open Targets / TTD / GWAS Catalog / PubTator API integration (`backend = external_api` adapters; CPU-side returns canned outputs).
- GPT-Rosalind real API calls (Class C; CPU-side returns canned outputs through the same Reasoner Protocol used for TxGemma).
- AlphaFold DB integration as a primary structure source (Class D; we *detect* leakage but never use it).
- Wet-lab CRO submission (covered by the existing cloud-lab dry-run adapters; Pathway 1 emits the handoff dossier into them but does not submit).

## 2. Architecture Invariant

Pathway 1 inherits **every** invariant from the existing Bio-Molecular Explorer pipeline (`docs/CONVENTIONS.md`):

- Universal layer envelope `zer0pa.layer-envelope.v1` — every P1 adapter emits this shape.
- Plug-replaceability — every P1 adapter has a primary `*StubAdapter`, a deliberately-different-valued `*ToyAdapter`, and a `*RunpodSimAdapter` (where the real adapter is GPU-bound) so the cutover invariant is testable per layer.
- Falsifier preservation across the full pipeline run.
- Audit hash chain validates pre- and post- backend-flag flips.
- Boundary string verbatim on every artifact.
- Clinical-overclaim phrases sha256-prefix-hashed in evidence (never echoed).

### Enum extensions

`src/zer0pa_biomolecular_explorer/envelope.py`:

- `LayerName` adds `P1_TARGET = "P1.Target"`, `P1_STRUCTURE = "P1.Structure"`, `P1_GENERATE = "P1.Generate"`, `P1_SCREEN = "P1.Screen"`, `P1_OPTIMIZE = "P1.Optimize"`, `P1_HANDOFF = "P1.Handoff"`.
- `Backend` adds `EXTERNAL_API = "external_api"` for GPT-Rosalind, Open Targets, TTD, GWAS Catalog, PubTator, ChEMBL, etc.

`src/zer0pa_biomolecular_explorer/kg/schema.py`:

- `NodeType` adds `TARGET`, `HIT`, `LEAD`, `GENERATIVE_PROPOSAL`, `DISEASE`, `BINDING_POCKET`.
- `EdgeType` adds `ENCODES_TARGET`, `HAS_DISEASE_ASSOCIATION`, `HAS_BINDING_POCKET`.

`schemas/envelope/layer-envelope-v1.json` enum lists are extended to match.

### Per-layer contracts (`src/zer0pa_biomolecular_explorer/pathway1/contracts/`)

| Layer | Inputs | Outputs |
|---|---|---|
| **P1.Target** | disease IDs (EFO/Orphanet), gene class hint | `P1TargetDossier` (target_id, gene_symbol, druggability, evidence pillars) |
| **P1.Structure** | `P1TargetDossier`, optional PDB ref | `P1StructureDossier` (mmCIF/PDB ref, binding pocket, pLDDT, structure_basis) |
| **P1.Generate** | `P1StructureDossier`, mode (de_novo / sbdd / scaffold_hop / linker / binder), library_size | `P1CandidateLibrary` (list of SMILES + generation_method + provenance) |
| **P1.Screen** | `P1CandidateLibrary`, target panel | `P1ScreenedHits` (ranked SMILES + predicted_pIC50 + ADMET + selectivity + SA score) |
| **P1.Optimize** | `P1ScreenedHits`, target product profile (TPP) | `P1OptimizedLeads` (list of leads + iteration_number + confidence_tier) |
| **P1.Handoff** | `P1OptimizedLeads`, cardiac context flag | `P1HandoffPacket` (CRO-ready dossier; cardiac targets get an `l1_channel_panel_input` block) |

### Plug-replaceability acceptance test (per layer)

For each P1 layer, replacing the StubAdapter with the ToyAdapter or the RunpodSimAdapter (where present) MUST:

1. Produce identical output keys (`detect_plug_replaceability_regression == PASS`).
2. Emit the same set of falsifier classes (PASS/FAIL outcomes can differ).
3. Preserve `contract_version = zer0pa.layer-envelope.v1`.
4. Validate against the canonical envelope JSON Schema.

## 3. Falsification Engine Framing

Pathway 1 inherits the existing 16 falsifier classes plus adds 13 R&D-specific classes (full spec in `docs/CONVENTIONS.md` §"Falsifier registry — Pathway 1 extension"):

| New class | Severity | Layer scope |
|---|---|---|
| `target_validation_overreach` | hard_fail | P1.Target |
| `hit_from_noise` | hard_fail | P1.Generate, P1.Screen |
| `lead_without_physchem_feasibility` | soft_fail | P1.Screen, P1.Optimize |
| `novelty_without_tractability` | hard_fail | P1.Generate, P1.Screen |
| `ip_chemspace_drift` | block_export | P1.Generate, P1.Optimize, P1.Handoff |
| `alphafold_d_leakage` | block_export | P1.Structure (and any layer that consumes it) |
| `benchmark_leakage` | hard_fail | P1.Screen, P1.Optimize |
| `pretrained_hallucination` | hard_fail | P1.Generate |
| `gpt_rosalind_unavailable` | soft_fail | P1.Target |
| `structure_confidence_below_threshold` | confidence_cap | P1.Structure |
| `selectivity_not_assessed` | soft_fail | P1.Screen, P1.Optimize |
| `synthesis_route_absent` | hard_fail | P1.Optimize, P1.Handoff |
| `confidence_tier_overclaim` | hard_fail | P1.Handoff |

### Existing falsifiers reused unchanged (9)

`invalid_molecular_input`, `nonfinite_input`, `clinical_overclaim`, `license_drift`, `stub_laundering`, `missing_falsifier_ref`, `silent_falsifier_loss`, `plug_regression`, `pubmed_baseline_no_value_add`.

### Existing falsifiers NOT applicable to Pathway 1 (8)

`codec_as_mechanism`, `noise_brittle_phenotype`, `hERG_only_overreach` (cardiac-specific; the *handoff* preserves it for downstream), `mass_balance_failure`, `l4_sensor_failure`, `sbml_schema_failure`, `morphology_non_preservation`, `missing_rxnsmiles_atommap` (P1 reuses ASKCOS but at the route-step level; the existing detector still applies if mapping is requested).

### Sanitization discipline

The audit validator already rejects records that contain banned phrases verbatim. Pathway 1 extends this with three additional sanitization rules:

- `detect_alphafold_d_leakage` records `af_id_sha256_prefix=` (16-hex) — never the raw `AF-{UniProt}-F{n}` ID.
- `detect_benchmark_leakage` records `leaked_inchikey_sha256_prefix=` for up to 5 leaked compounds — never the raw InChIKey.
- `detect_ip_chemspace_drift` records `catalogue_id` and `tanimoto` — never the raw matched commercial SMILES.

## 4. Build Sequence

Pathway 1 is built CPU-first. Adapters are stubs that return canned outputs from the seed fixtures; the real GPU adapters slot in at Runpod cutover. Per-iteration breakdown:

| Iteration | Owner | Output | Gate |
|---|---|---|---|
| 6.1 | Lead | This PRD + foundations enum extensions + new detectors + 13 new falsifier classes | All existing tests still pass; new detectors green |
| 6.2 | Lead | P1 contracts (Pydantic + JSON Schema), `pathway1/__init__.py` package layout | Contracts import cleanly; round-trip tests green |
| 6.3 | Sonnet subagent (one per layer) | `P1TargetStubAdapter`, `P1StructureStubAdapter`, `P1GenerateStubAdapter`, `P1ScreenStubAdapter`, `P1OptimizeStubAdapter`, `P1HandoffStubAdapter` + per-layer `*ToyAdapter` | Each layer's plug-swap test passes |
| 6.4 | Sonnet subagent | Target fixtures (6) + hit fixtures (12) + negative fixtures (7) + KG seed extension | KG validates after extension; fixtures load |
| 6.5 | Sonnet subagent | RunpodSim adapters for P1.Structure, P1.Generate, P1.Screen | Cutover-acceptance tests green per layer |
| 6.6 | Lead | `runs/pathway1_run.py` end-to-end runner; CLI `run-pathway1`; extend cutover-dryrun and health-check | Full P1.Target → ... → P1.Handoff → existing L1 → cardiac packet test green |
| 6.7 | Lead | Falsification wave extension (13 new triggers + sanitization checks) | All triggers caught/audited/routed/preserved |
| 6.8 | Lead | CONVENTIONS.md + DECISIONS.md (D-020+) + execution-report.md "Iteration 6" section + commit + push | All tests green; audit validator passes; runpod-precheck green |

## 5. Agent Topology

Lead (Opus): writes the PRD, locks contracts, designs falsifier extensions, integrates the cardiac handoff bridge, runs the falsification wave, commits.

Sonnet subagents in parallel:

- One per P1 layer for adapter implementation (6 in flight).
- One for fixtures + KG seed extension.
- One for the RunpodSim adapters.
- One for cutover-dryrun extension and per-layer cutover acceptance tests.

GPT-Rosalind, OpenAI Life Sciences Codex, Open Targets, TTD, GWAS Catalog, PubTator, ChEMBL, BindingDB, ZINC-22 — all are EXTERNAL_API backends. CPU-side returns canned outputs through the same `*StubAdapter` pattern. At cutover, the adapter binds to the real API endpoint via `endpoint:` in `runpod.config.yaml` (extended with `external_api:` section).

## 6. Audit-Trail Spec

Pathway 1 extends the existing 12 audit tables with no new tables. Per-run population:

| Table | P1 contribution |
|---|---|
| `runs.jsonl` | one entry per P1 run (executor identity, environment) |
| `molecules.jsonl` | one entry per generated/screened molecule that survives to handoff |
| `model_tools.jsonl` | one entry per P1 adapter invocation (e.g., `adapter:p1.generate:reinvent4_stub:0.1`) |
| `source_manifest.jsonl` | one entry per P1 source manifest referenced (Open Targets, TTD, ChEMBL, PDB, ZINC-22, ...) |
| `parameters.jsonl` | one entry per layer with the call parameters |
| `confidence.jsonl` | one entry per envelope (score + decomposition) |
| `falsifiers.jsonl` | one entry per emitted falsifier item across all P1 layers |
| `decisions.jsonl` | one entry per L6Router decision when running through the router |
| `artifacts.jsonl` | one entry per generated artifact (envelope dump, candidate dossier, KG node bundle) |
| `replay_commands.jsonl` | one entry per layer with the deterministic replay command |
| `offload_manifest.jsonl` | one entry per artifact that would offload to Architect-Prime HF dataset |
| `midd_assessments.jsonl` | one entry per `P1HandoffPacket` (qualification basis includes engine_score / lift / multi-current preservation) |

Audit hash chain validates as a single chain across the merged P1 + cardiac run.

## 7. Cardiac-Wedge Bridge (P1.Handoff → existing L1)

The `P1HandoffPacket` carries an optional `l1_channel_panel_input` block. When the target is one of the cardiac genes (KCNH2, SCN5A, KCNQ1, CACNA1C), the field is required and populated automatically by the Handoff adapter. This block matches the existing `L1ChannelPanelInput` Pydantic schema exactly, so the existing cardiac wedge consumes it without modification.

For non-cardiac targets (EGFR, BACE1 in the seed fixtures), `l1_channel_panel_input` is `null`. The downstream consumer routes such candidates to a future general-target wedge (out of scope for this iteration; the handoff is recorded but not consumed by L1).

The bridge enforces:

- For cardiac targets, the Handoff adapter populates KCNH2 in the panel by default plus at least one counterbalancing current (INaL or ICaL). Failure to do so triggers `hERG_only_overreach` in the existing detector.
- The Handoff adapter never lowers the confidence_tier or drops a falsifier item that the upstream P1 layers emitted (`silent_falsifier_loss` guard).

## 8. Self-Bootstrapping Reasoner

Reuses the existing `ReasonerAdapter` Protocol (`src/zer0pa_biomolecular_explorer/reasoner/`). The Pathway 1 reasoner-tuple emission happens at three points:

- **P1.Target hypothesis synthesis**: GPT-Rosalind (or `StubReasonerBackend` on CPU) produces a tuple per disease/target class, writing `task_type=route_selection`.
- **P1.Optimize iteration narration**: optional reasoner tuple per BoTorch acquisition step, `task_type=conflict_resolution` if multi-objective tradeoffs are surfaced.
- **P1.Handoff value-add justification**: a tuple per packet, `task_type=evidence_packet`, recording why this candidate cleared the gates and what it adds over a PubMed-reader baseline.

Tuples written to `reasoner_queue/runs/<rid>/tuples.jsonl`. Existing `export-finetune-corpus` CLI handles them without change.

## 9. Cloud-Lab Bridge

The existing `cloud_lab/` adapters (Strateos, Emerald, Arctoris) are dry-run-by-default. Pathway 1 adds an emission point at P1.Handoff: when `cloud_lab.enabled = True` AND a candidate has `confidence_tier = A` AND target ∈ {KCNH2, SCN5A, KCNQ1, CACNA1C}, the Handoff adapter emits a `validate_protocol` call against the configured vendor with the candidate dossier as the protocol body. The existing interlocks (NetworkSubmitDisabled, ApprovalTokenRequired, BudgetExceeded, BlockedClass) gate any actual submission. CPU-side stub returns `{"valid": true, "blocked": false, "issues": []}` without contacting the vendor.

## 10. Runpod Migration Plan

Per-adapter cutover positioning:

| Adapter | Backend at CPU build | Backend at cutover | Real GPU tool |
|---|---|---|---|
| `P1TargetStub` | stub | external_api | Open Targets / TTD / GWAS Catalog / PubTator REST |
| `P1TargetReasoner` | stub (StubReasonerBackend) | external_api | GPT-Rosalind via OpenAI Life Sciences Codex |
| `P1StructureOpenFold3` | stub | runpod_gpu | OpenFold3 (Apache 2.0) on A100/H100 |
| `P1StructureBoltz2` | stub | runpod_gpu | Boltz-2 (MIT) on A100 |
| `P1GenerateReinvent4` | stub | runpod_gpu | REINVENT 4 with neural backbone on A100 |
| `P1GenerateDiffSBDD` | stub | runpod_gpu | DiffSBDD on A100 |
| `P1ScreenChemprop` | stub | runpod_gpu | Chemprop v2 inference at library scale |
| `P1ScreenGNINA` | stub | runpod_gpu | GNINA 1.3 docking on A100 |
| `P1ScreenAffinity_Boltz2` | stub | runpod_gpu | Boltz-2 affinity pass |
| `P1OptimizeBoTorch` | cpu_lite | cpu_lite | BoTorch + Ax (CPU; Pareto over Pathway-1-specific objectives) |
| `P1HandoffComposer` | stub | cpu_lite | RDKit + ZINC-22 lookup (CPU-friendly) |

`runpod.config.yaml` extended with `external_api` section listing GPT-Rosalind, Open Targets, TTD, GWAS Catalog, PubTator, ChEMBL, BindingDB, ZINC-22, with `endpoint:` placeholders and `license_class` flags.

`zer0pa-biomolecular-explorer cutover-dryrun --layer p1` flips the P1 GPU-bound adapters from stub to runpod_sim, validates envelope shape stable, falsifier classes preserved, and writes per-layer journal records.

Cutover acceptance gates (per layer): `GATE_P1_<LAYER>_PLUG_SWAP_PASSES_WITH_REAL_ADAPTER`.

## 11. Acceptance Gates

Scientific gates:

- Six target fixtures present (4 cardiac + 2 non-cardiac); all validate against `schemas/fixtures/pathway1_target.schema.json`.
- Twelve hit fixtures present (3 per cardiac target); all validate against `schemas/fixtures/pathway1_hit.schema.json`.
- Pathway 1 runs the full end-to-end chain on all four cardiac targets; each produces a `P1HandoffPacket` with `verdict_at_handoff` ∈ {pass, hold, blocked}.
- The cardiac targets' handoff packets carry `l1_channel_panel_input` populated with all four cardiac genes (or explicit_absence per gene).
- The Handoff packet for each cardiac target, when fed into the existing cardiac wedge, produces a `cardiac_evidence_packet` with the same `verdict=pass` discipline as the seed dofetilide/verapamil/ranolazine packets.
- Every claim in the Handoff packet has `falsifier_refs` and `audit_refs` (Pydantic `min_length=1`).
- `pubmed_baseline_no_value_add` test: the P1 run generates ≥ 10 points lift over the canned baseline.

Engineering gates:

- All previously-passing tests still pass (507 baseline).
- Pathway 1 adds at least 100 new tests (unit + integration + plug_swap + falsification).
- Falsification wave extension catches every new R&D-specific class.
- Plug-swap test passes for every P1 layer (Stub vs Toy minimum; Stub vs RunpodSim where applicable).
- Cutover-dryrun --layer p1 passes (envelope shape stable, falsifier classes match across stub/runpod_sim).
- Audit hash chain validates pre-and-post for the merged P1 + cardiac run.
- KG validator passes after extension (K1–K5 hold; no dangling refs).
- `health-check` passes.

Brain-functionality gates:

- A fresh agent can reconstruct Pathway 1 state from `PATHWAY1_PRD.md` + `briefing-pack/Pathway1_RD_DrugDiscovery_PRD_Research.md` + `docs/CONVENTIONS.md` + `docs/DECISIONS.md` + `docs/execution-report.md` (Iteration 6 section) + the audit log + the KG.
- Pathway 1 decisions get rows D-020 onwards in `docs/DECISIONS.md`.
- Failed falsifiers and contradictions preserved across the full P1 + cardiac run.

## 12. Open Questions for the User

1. **Held-out target compounds for the P1 blind benchmark**: the existing benchmark covers 9 cardiac compounds. For Pathway 1 we need a held-out *target* set: e.g., known kinase targets (CDK4/6, BTK, JAK2) for general-pipeline framing. Confirm or revise.
2. **GPT-Rosalind access**: Class C research preview. Do we have authenticated access today, or do all P1.Target reasoner calls stay on `StubReasonerBackend` for now?
3. **Open Targets / TTD / PubTator API**: the CPU-side stubs return canned outputs. When do we wire the real REST clients? (They're CPU-friendly, just network-bound.)
4. **Enamine REAL Space access**: do we have a purchase agreement for the commercial-use compounds we will inevitably touch? `ip_chemspace_drift` blocks export until this is in writing.
5. **AiiDA vs existing audit**: the integration analysis recommended deferring AiiDA. Confirm — or we add AiiDA as a parallel store now.
6. **Confidence-tier model panel**: tier A requires ≥ 3 independent models. Today we have stubs of Boltz-2, Chemprop, GNINA. Confirm these are the canonical panel.
7. **Non-cardiac handoff destination**: for EGFR / BACE1 candidates, the handoff packet has no L1 cardiac panel. Where do they go? (Future general-target wedge; currently they accumulate in `packets/runs/non_cardiac/`.)
8. **CRO vendor selection**: cloud-lab adapters cover Strateos/Emerald/Arctoris. For Pathway 1 wet-lab handoff, which vendor is the first real target? (Affects the `P1HandoffPacket.cloud_lab_quote_ref` field.)

## Final Executor Rule

Same as the existing pipeline (`PRD.md`): no narratable wins, no green-flag rush, no abandoning the build because one falsifier surfaced a real data quality gap. Honor the trigger; fix the data, not the falsifier; document in DECISIONS.md.

Boundary verbatim on every artifact:

> Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.
