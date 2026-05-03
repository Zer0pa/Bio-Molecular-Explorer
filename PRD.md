# Zer0pa Bio-Molecular Explorer Overnight Execution PRD

## Boundary

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.

## Operating Mandate

This PRD is written for a long-horizon overnight execution by an Opus Max-class lead agent with Sonnet-level subagents at minimum and Opus-level subagents where the work requires high-context scientific judgment, cross-layer architecture decisions, or hard falsification reasoning. The lead agent is the chief engineer and chief scientific integrator, not a task narrator. It has an executive mandate to make reversible engineering decisions that move the system toward more performant, more dataful, more powerful, and more falsifiable outcomes.

Upon receipt of the startup prompt, the overnight executor proceeds immediately. It does not ask the user what to do next. It reads the repo, restores context from committed artifacts, plans, spawns subagents, implements, tests, runs a falsification wave, commits, pushes, and reports only when the full CPU-side pipeline and falsification wave have run or when a hard blocker prevents further progress.

Only work that actually requires GPU execution is parked for Runpod. Everything else is built locally or as a CPU-validatable stub before migration. Stubbed work must still have schemas, adapters, audit records, test fixtures, falsifiers, and cutover gates.

## 1. Scope and Boundary

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.

The first deliverable is a cardiac electrophysiology wedge, not a generic drug-discovery demo. The named seed compounds are dofetilide, verapamil, and ranolazine. The named seed genes and channels are KCNH2/hERG, SCN5A/Nav1.5, KCNQ1/Kv7.1, and CACNA1C/CaV1.2. The scientific frame is multi-current CiPA-style cardiac repolarization reasoning with FDA E14/S7B used only as regulatory-science context.

The work stream is research infrastructure for falsifiable evidence assembly. It is not a diagnostic tool, prescribing tool, clinical deployment, regulatory submission package, or drug-safety certification system. The system may assemble research evidence packets, generate hypotheses, surface contradictions, run replay and morphology tests, and produce audit trails. It must not claim that a compound is safe, unsafe, approved, clinically actionable, or regulatory-compliant.

No second wedge starts until the cardiac wedge meets the scientific, engineering, and brain-functionality gates in section 11. The governing objective is the authority metric: source-grounded, falsifiable, replayable cardiac evidence that beats PubMed plus a competent reader on the pre-registered benchmark. Local improvements that do not improve that metric are not success.

## 2. Architecture Invariant

Every layer is tool-agnostic and contract-first. Downstream components depend on versioned interfaces, not on RDKit, OpenFE, PharmaPy, OpenModelica, COPASI, TxGemma, Claude, GPT, or any other implementation detail.

The universal layer envelope is mandatory:

```json
{
  "contract_version": "zer0pa.layer-envelope.v1",
  "research_boundary": "Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.",
  "run_id": "run:...",
  "layer": "L1|L2|L2.5|L3|L4|L5|L6",
  "tool_adapter": {
    "name": "adapter name",
    "version": "adapter version",
    "backend": "stub|cpu_lite|runpod_gpu",
    "engine": "tool or model name"
  },
  "input_refs": [],
  "output": {},
  "confidence": {
    "score": 0.0,
    "band": "low|medium|high",
    "basis": []
  },
  "falsifier": {
    "status": "pass|fail|blocked|inconclusive",
    "items": []
  },
  "audit": {
    "audit_record_id": "audit:...",
    "input_hash": "sha256:...",
    "output_hash": "sha256:...",
    "source_manifest_refs": []
  },
  "back_edges": []
}
```

Canonical interface contracts:

| Layer | Contract inputs | Contract outputs | Replaceable tools |
| --- | --- | --- | --- |
| L1 molecular simulation | SMILES/InChIKey, target manifests, mmCIF/PDB refs, channel panel | standardized ligand, pose, binding estimate, MD/FEP result, channel panel hypothesis | RDKit, DiffDock V2, Boltz-2, Protenix, OpenMM, OpenFE, stubs |
| L2 formulation/property | standardized molecule, descriptors, L2.5 feedback | property scores, liability flags, reward modifiers | RDKit, DeepChem, DeepXDE, REINVENT scorer, stubs |
| L2.5 retrosynthesis | canonical SMILES, policy, buyability catalogs | RXNSMILES, atom-mapped route, route confidence, feasibility feedback | AiZynthFinder, ASKCOS, Chemprop, Rxnmapper, stubs |
| L3 process | route packet, material properties, conditions | process graph, mass balance, unit ops, CPP/CQA risks | DWSIM, PharmaPy, OpenFOAM, LIGGGHTS, MFiX, stubs |
| L4 manufacturing twin | process graph, unit ops, sensor-state stubs | FMU-like unit states, digital twin readiness, manufacturability backedges | PharmaPy, OpenModelica, FMI/FMU, Eclipse Ditto, OpenFOAM, stubs |
| L5 PKPD/QSP | ADMET, formulation/process outputs, cardiac channel evidence | SBML/QSP packet, exposure-to-channel bridge, cardiac evidence inputs | PK-Sim/MoBi, nlmixr2/RxODE, COPASI, Tellurium, stubs |
| L6 orchestration | all envelopes, KG, audit, falsifier ledger | state transitions, backedges, packets, decisions, reasoner tuples | LangGraph, Prefect, Parsl, Claude, GPT, TxGemma, stubs |

Plug-replaceability acceptance test:

1. Pick one layer adapter and a golden seed request.
2. Replace its implementation with a second adapter behind the same contract.
3. Run the same request through the downstream pipeline.
4. Pass only if downstream code is unchanged, schemas validate, audit provenance records the adapter difference, falsifier state is preserved, and any scientific change is represented as output/confidence/falsifier delta rather than a broken interface.

The overnight executor must implement the plug test with at least one real swap or stub-to-stub swap per layer. The <1 day swap invariant is a product requirement, not documentation.

## 3. Falsification Engine Framing

The pipeline is a falsification engine. It is not a forward pipeline that narrates every layer as progress. Every layer emits output, confidence, falsifier, audit record, and backedges. L6 promotes, downgrades, reroutes, or blocks based on falsifier state.

Active RBTE falsifiers:

| Falsifier | Trigger | Required behavior |
| --- | --- | --- |
| Codec-as-mechanism | Replay fidelity is used as biological mechanism evidence | Block mechanism claim; allow only phenotype-integrity claim |
| Noise-brittle phenotype | Noise, missing values, or corrupted input silently pass | Hard fail; route to validation and morphology gate |
| hERG-only overreach | KCNH2/hERG is treated as standalone risk conclusion | Fail packet unless SCN5A/KCNQ1/CACNA1C context is present or explicit abstention is recorded |
| Clinical overclaim | Output implies diagnosis, treatment, prescribing, deployment, compliance, or certification | Hard fail export; write audit incident |

Pipeline-wide falsifiers:

| Falsifier | Layer scope | Trigger | Backedge |
| --- | --- | --- | --- |
| Nonfinite input | L1-L6 | NaN, infinity, invalid array, malformed SMILES/RXNSMILES/SBML/FMU | Block current layer; route to validation fixture |
| Morphology non-preservation | cardiac packet/L5/L6 | QT/QRS/PR/ST/T fiducial error exceeds gate | Route to ECG extraction/replay benchmark |
| PubMed-baseline no-value-add | L6 packet | Packet is no better than PubMed plus competent reader | Route to evidence graph, contradiction table, and falsifier expansion |
| Plug regression | all layers | Adapter swap changes downstream contract | Route to interface-contract fix before science work continues |
| Silent falsifier loss | all layers | Claim/output is promoted without falsifier ref | Hard fail CI and packet export |
| Stub laundering | L1/GPU layers | Stub output is treated as real simulation | Confidence cap and provenance flag; block mechanistic escalation |
| License drift | TxGemma/data/tools | Tool or dataset terms are assumed rather than checked | Block export/offload; route to source manifest update |

Merged claim ledger:

1. Cardiac mechanism claims require source-grounded multi-current context.
2. Codec/replay claims are morphology-integrity claims, not mechanism claims.
3. hERG/KCNH2 evidence alone cannot rank or certify proarrhythmic risk.
4. Clinical or regulatory conclusion language is forbidden.
5. Every layer output must be envelope-complete.
6. Any falsifier failure must survive summaries, commits, handoffs, and reports.
7. L2.5 feasibility must feed back into L2 scoring before promotion.
8. L4 virtual plant outputs are manufacturability hypotheses, not plant authority.
9. L5 QSP outputs are model-bounded research simulations, not dosing or treatment recommendations.
10. L6 is responsible for preserving uncertainty and routing backedges.
11. The system must beat the PubMed-reader baseline on the cardiac packet benchmark.
12. The plug-replaceability invariant is a top-level product gate.

## 4. Build Sequence

The overnight executor must front-load all CPU-side engineering before Runpod. L1 GPU tools are represented as REST stubs until Runpod exists. L2-L6 must be runnable locally with small fixtures and no bulk datasets.

Execution order:

| Phase | Owner profile | Output | Gate |
| --- | --- | --- | --- |
| 0. Repo restore | Opus Max lead | branch status, source read confirmation, worktree/subagent plan | No user questions; clean or intentionally tracked working tree |
| 1. Contracts | Opus/Sonnet interface agents | JSON Schemas, canonical IDs, envelope validators, REST shapes | All layers validate golden envelopes |
| 2. Audit/KG/falsifier core | Opus scientific integrator plus Sonnet code agents | append-only audit JSONL, KG schema, falsifier ledger | Boundary, hash chain, no dangling refs, resume-ready |
| 3. L1 stubs | Sonnet code agent | REST stubs for ligand, target, pose, binding, MD, FEP, channel panel | Canned dofetilide/verapamil/ranolazine outputs with stub provenance |
| 4. L2 property/formulation | Sonnet code agent | RDKit/DeepChem/stub scoring, DeepXDE stub, L2.5 feedback hook | Invalid SMILES fail; route feedback modifies reward |
| 5. L2.5 retrosynthesis | Sonnet code agent | route schema, AiZynthFinder/ASKCOS stubs, RXNSMILES/atom-map validator | Missing route or mapping blocks L3 |
| 6. L3 process | Sonnet code agent | route-to-process packet, mass balance, unit ops, process falsifiers | Mass balance and condition gates pass on fixtures |
| 7. L4 virtual plant | Sonnet/OpenModelica-aware agent | FMU-like state bus, Ditto sensor stub, virtual plant readiness | COPASI/Tellurium not used in L4; sensor faults produce falsifiers |
| 8. L5 PKPD/QSP | Sonnet/R agent if available | SBML/RxODE/Tellurium/COPASI-compatible stubs, cardiac bridge | SBML roundtrip and analytic one-compartment fixture pass |
| 9. L6 orchestration | Opus lead plus Sonnet agents | LangGraph state graph, Prefect flows, Parsl dispatch interface | Backedges and resume work on forced failures |
| 10. Cardiac packet | Opus scientific lead | evidence packets for three compounds | Multi-current panel, morphology gate, PubMed-baseline benchmark |
| 11. Falsification wave | Opus lead | deliberate failure run across all falsifiers | Failures are caught, audited, and propagated |
| 12. Commit/push/report | Opus lead | committed code/docs/results | GitHub contains all artifacts needed by next machine |

Per-agent decomposition:

- L1 agent owns only `layers/l1_*`, schemas, and tests for molecular stubs.
- L2 agent owns only property/formulation code and tests.
- L2.5 agent owns route contracts and feedback interface to L2.
- L3 agent owns process packet generation and mass-balance tests.
- L4 agent owns virtual plant contracts and FMU/Ditto stub interfaces.
- L5 agent owns PKPD/QSP contracts and cardiac bridge.
- L6 agent owns orchestration, state graph, workflow, dispatch, and export gates.
- KG/audit agent owns append-only stores, schema validation, resume reconstruction.
- Falsification agent owns ledger, negative fixtures, falsification wave.
- Cardiac packet agent owns seed evidence packet templates and PubMed baseline benchmark.
- Cloud-lab agent owns disabled-by-default dry-run adapters.

The lead agent must keep its own context free for cognitive intersection: architecture arbitration, scientific gap closure, falsifier design, cross-layer backedges, and innovation decisions. Routine implementation goes to Sonnet-level subagents or better.

## 5. Agent Topology

Lead: Opus Max-class chief engineer at maximum reasoning effort. It owns the authority metric, architecture, scientific coherence, subagent decomposition, final integration, and decision making. It has permission to make reasonable local decisions without user engagement when those decisions are reversible, audited, and move the system toward the PRD gates.

Subagents: Sonnet-level minimum. Use Opus-level subagents for cardiac electrophysiology interpretation, interface architecture, falsification strategy, audit/KG semantics, and any task where local coding competence is not enough. Subagents work in parallel worktrees or isolated file ownership boundaries. Each subagent must return changed files, tests run, unresolved blockers, and falsifier impacts.

Research escalation: use Claude deep research capability and Claude subagent research packs. When current external evidence is needed, spawn a research subagent to gather primary-source material, summarize the decision impact, and write source manifests. Prefer official and primary sources for FDA E14/S7B, CiPA, ICH M15, TxGemma terms, OpenFE, LangGraph, Prefect, Parsl, PhysioNet/PTB-XL+, and cloud-lab vendor API posture.

Reasoner candidate: TxGemma 27B may be used as a domain critique and self-bootstrapping candidate only behind a replaceable `ReasonerAdapter`. It is not authority. Current terms must be verified and recorded before use, and all TxGemma-derived tuples are internal research-only unless governance explicitly approves more.

Orchestration trio:

- LangGraph: state graph, confidence routing, falsifier routing, backedges.
- Prefect: task execution, retries, caching, logging, resumability.
- Parsl: long-running local, Runpod, or HPC dispatch behind a stable execution interface.

KG and episodic memory run from day one. Every meaningful decision creates an `Episode`; every scientific assertion requires evidence, falsifier, audit, and source refs before promotion.

## 6. Audit-Trail Spec

The audit trail is ICH M15-shaped research provenance. It is not a claim of ICH, FDA, regulatory, or drug-safety compliance. The current ICH M15 Step 4 final guideline is used as a structural reference for model-informed evidence discipline, traceability, and decision context.

Append-only JSONL tables under `audit/`:

| File | Purpose |
| --- | --- |
| `runs.jsonl` | run metadata, executor identity, git commit, environment |
| `molecules.jsonl` | molecule IDs, InChIKey, SMILES, source refs |
| `model_tools.jsonl` | tool/model/adapter versions and license flags |
| `source_manifest.jsonl` | source locators, retrieval timestamps, hashes, license, source class |
| `parameters.jsonl` | explicit parameters and defaults used by adapters |
| `confidence.jsonl` | confidence decomposition and calibration basis |
| `falsifiers.jsonl` | falsifier definition, trigger, status, evidence |
| `decisions.jsonl` | L6 routing decisions, backedges, human-independent choices |
| `artifacts.jsonl` | artifact paths, hashes, size, offload refs |
| `replay_commands.jsonl` | deterministic or best-effort replay commands |
| `offload_manifest.jsonl` | private HF dataset refs for bulk offload, no secrets |
| `midd_assessments.jsonl` | MIDD-shaped research assessment records, no compliance claim |

Every row includes `schema_version`, `created_at_utc`, `research_boundary`, `record_hash`, and `prev_record_hash`. The validator fails on missing boundary, malformed hash chain, dangling refs, secrets, PHI, unsupported bulk local files, or clinical/regulatory conclusion language.

KG model:

- Node types: `Compound`, `Gene`, `Channel`, `IonCurrent`, `PhenotypeFeature`, `AssayModel`, `DatasetManifest`, `SourceManifest`, `EvidenceItem`, `Claim`, `Falsifier`, `Layer`, `ToolAdapter`, `InterfaceContract`, `OutputEnvelope`, `AuditRecord`, `EvidencePacket`, `Episode`, `ReasonerTuple`, `AcceptanceGate`.
- Edge types: `ENCODES`, `MEDIATES_CURRENT`, `MODULATES`, `AFFECTS_FEATURE`, `SUPPORTS`, `CONTRADICTS`, `QUALIFIES`, `HAS_SOURCE`, `HAS_FALSIFIER`, `GENERATED_BY`, `HAS_AUDIT`, `CONSUMES_CONTRACT`, `PRODUCES_CONTRACT`, `MEMBER_OF_PACKET`, `TRIGGERS_BACKEDGE`, `DERIVES_TUPLE`, `SUPERSEDES`.

Hard KG constraints:

1. No `Claim` may be `SUPPORTED_FOR_RESEARCH` unless it has at least one `EvidenceItem`, one `SourceManifest`, one `Falsifier`, and one `AuditRecord`.
2. No mechanism edge may be source-grounded if its only evidence is a codec/replay metric.
3. Any claim touching QT, TdP, proarrhythmia, or cardiac safety context must include multi-current framing or fail the hERG-only falsifier.
4. Every layer output must exist as an `OutputEnvelope`.
5. `Episode` nodes support resume and learning, but cannot serve as scientific evidence by themselves.

## 7. Cardiac Wedge First Deliverable

The first deliverable is `CardiacEvidencePacket-v0.1` for dofetilide, verapamil, and ranolazine.

Packet schema:

```json
{
  "packet_id": "packet:cardiac:compound:v0.1",
  "research_boundary": "Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.",
  "compound": {},
  "source_manifest_refs": [],
  "channel_panel": {
    "KCNH2_hERG_IKr": {},
    "SCN5A_Nav1_5_INa_INaL": {},
    "KCNQ1_Kv7_1_IKs": {},
    "CACNA1C_CaV1_2_ICaL": {}
  },
  "multi_current_interpretation": {},
  "ecg_morphology_bridge": {},
  "claims": [],
  "contradictions": [],
  "falsifiers": [],
  "audit_refs": [],
  "engine_value_add": {},
  "verdict": "pass|fail|inconclusive|blocked"
}
```

Compound-specific expectations:

- Dofetilide is the IKr/hERG positive-control reference. It must still include SCN5A, KCNQ1, and CACNA1C context or explicit absence records.
- Verapamil is the hERG-overreach refuter. A packet that ranks verapamil like dofetilide because of hERG signal alone fails.
- Ranolazine is a multi-current and late sodium context test. A packet that collapses ranolazine into a single QT paragraph fails.

Morphology gate:

- Median absolute QT error <= 5 ms versus locked reference extractor/table.
- 95th percentile QT error <= 15 ms.
- Analogous QRS, PR, ST/T morphology thresholds must be defined before pass.
- Any NaN, nonfinite, silent interpolation, or missing fiducial handling failure blocks the packet.

PubMed-reader benchmark:

- Build a blind benchmark with held-out cardiac compounds such as quinidine, moxifloxacin, diltiazem, sotalol, mexiletine, and lidocaine, subject to source availability.
- Establish a competent-reader baseline from PubMed-style source reading.
- Pass requires the engine to score at least 80/100 on claim correctness, source grounding, falsifier coverage, contradiction handling, and audit replay, and at least 10 points above baseline.
- Better prose does not count. Extra data, machine-valid graph structure, contradiction surfacing, replayability, and falsifier quality count.

The packet must produce what PubMed plus a competent reader does not: a rerunnable source manifest, machine-valid graph, explicit contradiction table, falsifier ledger, local morphology linkage, audit trail, and next-experiment backedges.

## 8. Self-Bootstrapping Reasoner

The self-bootstrapping reasoner is an internal learning loop. It converts every reasoner interaction into a reusable training or evaluation tuple without making the model an authority.

Canonical tuple:

```json
{
  "tuple_id": "tuple:...",
  "schema_version": "reasoner_tuple.v1",
  "created_at_utc": "ISO-8601",
  "run_id": "run:...",
  "task_type": "evidence_packet|mechanism_bridge|falsifier_generation|conflict_resolution|audit_summary|route_selection",
  "input": {
    "question": "specific task",
    "entities": {
      "compounds": [],
      "genes": [],
      "currents": [],
      "phenotypes": []
    },
    "context_pack_refs": [],
    "constraints": {
      "authority_order": ["source_anchor", "curated_literature", "local_benchmark", "simulation", "kg_inference", "model_output"],
      "forbidden_outputs": ["diagnosis", "treatment", "prescribing", "clinical_certification", "regulatory_compliance_claim"],
      "required_caveats": ["research_only", "multi_current_context", "falsifier_required"]
    }
  },
  "output": {
    "claims": [],
    "abstentions": [],
    "kg_edge_proposals": [],
    "next_actions": []
  },
  "falsifier": {
    "falsifier_id": "falsifier:...",
    "class": "source_conflict|multi_current_overreach|phenotype_mismatch|audit_gap|clinical_overclaim|adapter_regression",
    "trigger_condition": "explicit condition",
    "status": "pending|passed|failed|inconclusive"
  },
  "ground_truth": {
    "status": "available|pending|not_available|not_applicable",
    "type": "source_anchor|curated_literature|local_benchmark|human_adjudication|simulation_golden",
    "source_refs": []
  },
  "audit": {
    "prompt_hash": "sha256:...",
    "context_hash": "sha256:...",
    "output_hash": "sha256:...",
    "license_flags": []
  }
}
```

Day-one flow:

1. L6 assembles a context pack from KG, audit, source manifests, prior envelopes, and falsifier state.
2. `ReasonerAdapter` calls Claude, GPT, TxGemma, or a stub behind the same contract.
3. The reasoner returns structured claims, confidence, abstentions, proposed graph edges, and falsifiers.
4. The falsifier ledger receives one entry per claim.
5. KG promotion is blocked unless evidence, source, falsifier, audit, and confidence decomposition are present.
6. Corpus writer appends the tuple to a private internal queue.
7. Fine-tune positives require passed or adjudicated falsifiers. Failed and overclaiming outputs become negative examples.

Six-month moat:

- Thousands of audit-linked cardiac wedge tuples.
- Negative examples for hERG-only overreach, clinical overclaim, unsupported mechanism bridges, stub laundering, source conflict, and morphology failures.
- Evaluation sets that compare TxGemma, Claude, GPT, small local models, and future reasoners on the same authority metric.
- A KG that records not just claims, but why claims were accepted, rejected, superseded, or routed backward.

Model improvement is accepted only if claim-level correctness, falsifier quality, source grounding, and benchmark score improve. Fluency, confidence, or longer explanations do not count.

## 9. Cloud-Lab Option

Cloud-lab integration is optional and disabled by default. It is a vendor-neutral L6 extension, not a requirement for the first CPU-side build.

Default config:

```yaml
cloud_lab:
  enabled: false
  mode: dry_run
  allow_network_submit: false
  max_budget_usd: 0
  require_user_approval_token: true
```

Adapter interface:

- `capabilities()`
- `validate_protocol(protocol)`
- `quote(protocol)`
- `stage(protocol)`
- `submit(protocol, approval_token)`
- `poll_status(job_id)`
- `fetch_results(job_id)`

Supported vendors are represented as stubs for Strateos, Emerald Cloud Lab, Arctoris, and Synthace-style planning. Public API depth varies, so no live endpoint is assumed until source manifests confirm it.

Closed-loop pattern:

1. Simulation or evidence packet proposes a bounded research hypothesis.
2. L6 drafts a protocol in dry-run form.
3. Boundary/material/safety/budget/network gates run.
4. User approval token is required before any real submission path is reachable.
5. Vendor result is normalized into audit, KG, and falsifier updates.
6. Failed wet-lab results update falsifiers. They are not narrated as success.

Blocked classes include clinical work, human diagnosis, treatment, prescribing, regulated safety certification, PHI, controlled or hazardous material handling beyond approved constraints, and any autonomous wet-lab execution.

## 10. Runpod Migration Plan

Runpod migration is a stub-swap procedure. It must not trigger an architectural rewrite.

Pre-Runpod completion requirements:

- L2-L6 run locally on CPU with fixtures.
- L1 exposes REST stubs with the same contracts expected from GPU tools.
- KG, audit, falsifier ledger, contracts, packets, and orchestration exist.
- The falsification wave has run and caught deliberate failures.
- No bulk dataset is required locally.

GPU candidates:

| Capability | GPU tool candidates | Pre-GPU state |
| --- | --- | --- |
| Docking/pose | DiffDock V2, Boltz-2, Protenix | L1 pose REST stub and fixtures |
| MD | OpenMM | L1 MD stub with convergence fields |
| RBFE/ABFE | OpenFE | L1 FEP stub with uncertainty/convergence fields |
| Protein/complex confidence | Boltz-2/Protenix | confidence decomposition schema |
| Domain reasoner | TxGemma 27B quant/full | adapter and tuple schema |

Cutover steps:

1. Provision Runpod with pinned container, CUDA, driver, package, and git commit metadata.
2. Set adapter backend from `stub` or `cpu_lite` to `runpod_gpu`.
3. Run `/health` and `/capabilities` for each remote adapter.
4. Re-run golden seeds: dofetilide, verapamil, ranolazine.
5. Validate identical schemas and downstream compatibility.
6. Confirm real artifacts replace stub artifacts and include convergence metrics.
7. Compare scientific deltas through confidence/falsifier fields.
8. Write audit records with container hash, GPU SKU, cost, runtime, driver/CUDA versions, model/tool versions.

Cutover passes only if no downstream interface changes are needed and falsifier state is preserved.

## 11. Acceptance Gates

Scientific gates:

- Cardiac seed packets exist for dofetilide, verapamil, and ranolazine.
- Full channel/current panel is present or explicit absence/planned-lookup status is recorded.
- hERG-only conclusions fail.
- Codec/replay metrics are not mechanism evidence.
- Morphology gates are defined and NaN/nonfinite input hard-stops.
- Every scientific claim has source, confidence, falsifier, audit, and KG refs.
- Packet beats PubMed plus competent reader by the pre-registered benchmark.
- No output crosses the research boundary.

Engineering gates:

- CPU-only build runs end to end from seed molecules through L6 packet generation.
- L1 GPU-dependent functions are REST stubs, not absent TODOs.
- Every layer has schema validation, fixtures, negative tests, and one plug-swap test.
- Audit hash chain validates.
- KG has no dangling refs and can reconstruct current state.
- Prefect resume works after an injected failure.
- LangGraph backedges route at least one forced falsifier failure.
- Parsl interface can dispatch a no-op local job and record provenance.
- No Docker is required on the originating Mac.
- No bulk local datasets are downloaded.

Brain-functionality gates:

- A new agent can clone the repo and reconstruct state from `README.md`, `MODUS-OPERANDI.md`, this PRD, handoff docs, audit logs, KG files, and committed tests.
- The lead agent can identify unresolved falsifiers and next actions without chat history.
- The system preserves failed evidence and contradictions instead of summarizing them away.
- Decisions are recorded with enough context for later agents to challenge or supersede them.

Failure rule: any regression on the authority metric is failure, regardless of secondary wins. The executor must stay in the fix loop instead of converting mixed evidence into a pass narrative.

## 12. Open Questions for the User and Next Agent

User-level innovation questions:

1. Which held-out cardiac compounds should define the first blind benchmark beyond the suggested quinidine, moxifloxacin, diltiazem, sotalol, mexiletine, and lidocaine?
2. Who or what acts as the competent-reader baseline reviewer for the first PubMed benchmark?
3. What private Hugging Face dataset name should receive offloaded manifests and larger artifacts under Architect-Prime?
4. What Runpod GPU budget and SKU ceiling should the migration plan assume?
5. Should the first morphology gate use PTB-XL+ fiducials only, or include MIT-BIH/ECGdeli/NeuroKit2 cross-checks immediately?
6. Should the channel panel expand in the first wedge to KCNJ2/IK1, HCN4/If, KCNE modifiers, or RyR2, or only record them as planned extensions?
7. What level of TxGemma terms review is required before internal fine-tuning experiments?
8. Which cloud-lab vendor, if any, should be treated as the first real integration target after dry-run stubs?

Next-agent implementation questions:

1. Does the repo already contain preferred code layout conventions, or should the executor create `contracts/`, `layers/`, `orchestration/`, `audit/`, `kg/`, and `tests/`?
2. Which language stack is fastest for the CPU-side build: Python-first with FastAPI/Pydantic/Pytest, or a split Python/TypeScript toolchain?
3. Which minimal ECG fixture should be checked in as a tiny slice without violating the no-bulk constraint?
4. How should source manifests represent licensed or access-gated material that cannot be redistributed?
5. What exact threshold defines the PubMed-reader score components?

## Research Lookups Already Reflected

- [ICH M15 Step 4 final guideline](https://database.ich.org/sites/default/files/ICH_M15_Step4_Final_Guideline_2026_0129.pdf), adopted January 29, 2026: used only to shape research provenance and model-informed evidence discipline.
- [FDA E14/S7B Q&A](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/e14-and-s7b-clinical-and-nonclinical-evaluation-qtqtc-interval-prolongation-and-proarrhythmic): used only as regulatory-science context for QT/QTc framing.
- [FDA CiPA/ion-channel regulatory-science page](https://www.fda.gov/drugs/regulatory-science-action/streamlining-analysis-ion-channel-in-vitro-assays-data-support-clinical-cardiac-safety-decision-making): used only as multi-current regulatory-science context.
- [TxGemma model card](https://developers.google.com/health-ai-developer-foundations/txgemma/model-card) and Health AI Developer Foundations terms: used to correct the assumption that TxGemma is simply governed by Gemma 2 terms.
- [PTB-XL+ PhysioNet reference](https://physionet.org/content/ptb-xl-plus/1.0.1/): used to motivate the cardiac morphology benchmark.
- LangGraph, Prefect, and Parsl official docs: used to separate routing, workflow execution, and compute dispatch responsibilities.

## Final Executor Rule

The overnight executor is expected to push the frontier inside the research boundary. It must use subagents aggressively, solve problems on the fly, make audited engineering decisions, build the most complete CPU-side pipeline possible, and park only GPU-exclusive execution for Runpod. It reports when the full pipeline plus falsification wave is done, not when it has a narratable partial win.
