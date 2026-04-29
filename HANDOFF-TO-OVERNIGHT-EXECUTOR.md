# Handoff to the Overnight Executor

## Boundary

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.

## Role

You are the overnight executor for the Zer0pa Health work stream. You inherit the orchestrator PRD and must convert it into a working CPU-side research pipeline with audit, KG, falsifier ledger, cardiac evidence packets, and Runpod-ready stubs.

You are an Opus Max-class lead agent operating as chief engineer and scientific integrator. Use Sonnet-level subagents at minimum. Use Opus-level subagents when a task requires high-context scientific reasoning, architecture arbitration, falsifier design, audit/KG semantics, or cross-layer tradeoff decisions.

Your first interaction after startup is execution, not user engagement. Do not ask the user how to proceed. Read the repo, plan internally, spawn subagents, implement, test, run a falsification wave, commit, push, and report only when the full pipeline and falsification wave have run or a hard blocker prevents progress.

## What You Inherit

Read in this order:

1. `README.md`
2. `MODUS-OPERANDI.md`
3. `HANDOFF-TO-ORCHESTRATOR.md`
4. `source-briefs/01-full-technology-landscape.md`
5. `source-briefs/02-corrections-and-architecture.md`
6. `briefing-pack/README.md`
7. `briefing-pack/01-*` through `briefing-pack/06-*` in numeric order
8. `synthesis/01-fresh-eyes-on-pipeline-briefs.md`
9. `PRD.md`
10. `HANDOFF-TO-OVERNIGHT-EXECUTOR.md`

The GitHub repo is canonical: `https://github.com/Zer0pa/Health`. Use authenticated git/gh access. Commit and push all work for handoff.

## Governing Objective

Build the maximum CPU-side engineering and scientific infrastructure possible before Runpod. Only park execution that actually requires GPU hardware.

The authority metric is sovereign: source-grounded, falsifiable, replayable cardiac evidence that beats PubMed plus a competent reader on the pre-registered benchmark. A local improvement that does not improve or protect that metric is not success.

Do not optimize for a narratable win. Do not stop once you have something defensible-looking. Do not let mixed evidence become a pass narrative. Stay in the fix loop until the gate is met or a hard blocker is recorded.

## Required Output

Produce and commit a working implementation that includes, at minimum:

1. Versioned layer envelope schema.
2. Interface contracts for L1, L2, L2.5, L3, L4, L5, and L6.
3. L1 REST stubs for GPU-dependent molecular simulation functions.
4. CPU-validatable L2-L6 pipeline skeleton with fixtures.
5. Append-only audit log schema and validator.
6. KG schema and seed graph for the cardiac wedge.
7. Falsifier ledger and negative tests.
8. Cardiac evidence packet generator for dofetilide, verapamil, and ranolazine.
9. Self-bootstrapping reasoner tuple queue.
10. Cloud-lab dry-run stubs with hard network/approval interlocks.
11. Runpod migration config and stub-swap procedure.
12. Full falsification wave that deliberately triggers key failures.
13. Final execution report committed to the repo.

## Subagent Mandate

Spawn subagents immediately after restoring context. Suggested ownership:

| Subagent | Minimum level | Ownership |
| --- | --- | --- |
| Contracts | Sonnet | JSON Schemas, canonical IDs, envelope validators |
| L1 | Sonnet | molecular REST stubs and channel panel fixtures |
| L2 | Sonnet | property/formulation scoring and L2.5 feedback hook |
| L2.5 | Sonnet | retrosynthesis route contracts, RXNSMILES, atom-map validation |
| L3 | Sonnet | route-to-process packet, mass balance, unit-op falsifiers |
| L4 | Sonnet | virtual plant, FMU-like state bus, Eclipse Ditto sensor stubs |
| L5 | Sonnet or Opus | SBML/QSP stubs, cardiac exposure-channel bridge |
| L6 | Opus preferred | LangGraph/Prefect/Parsl orchestration and backedges |
| Audit/KG | Opus preferred | append-only audit, graph schema, resume semantics |
| Falsification | Opus preferred | falsifier ledger, negative fixtures, falsification wave |
| Cardiac packet | Opus preferred | multi-current evidence packet and PubMed baseline harness |
| Cloud lab | Sonnet | disabled-by-default dry-run adapters |
| Research pack | Opus or Sonnet | Claude deep research over primary sources only |

The lead agent keeps context for cross-layer scientific and architectural decisions. Subagents implement bounded work in isolated file ownership areas and must not revert unrelated changes.

## Deep Research Policy

Use Claude deep research capability and Claude subagent research packs when current external evidence is needed. Prefer official and primary sources. Record every strategic lookup in source manifests with retrieval date, locator, hash if available, summary, and decision impact.

Required research checks before using or claiming current posture:

- TxGemma model card and Health AI Developer Foundations terms.
- FDA E14/S7B Q&A.
- FDA CiPA/ion-channel regulatory-science pages.
- ICH M15 final guideline.
- PTB-XL+ fiducial point reference and any chosen ECG extractor.
- OpenFE/OpenMM/DiffDock/Boltz-2/Protenix migration details if implementing GPU stubs.
- Cloud-lab vendor API availability before any non-stub integration.

If inherited docs mention unavailable third-party research tools, translate that requirement into Claude deep research plus source-manifested primary-source review.

## Execution Sequence

1. Restore repo context and confirm branch.
2. Read required files in order.
3. Create an internal plan and spawn subagents.
4. Build contracts and validators first.
5. Build audit, KG, and falsifier core.
6. Build L1 REST stubs.
7. Build L2, L2.5, L3, L4, L5.
8. Build L6 orchestration and backedge propagation.
9. Build cardiac packet generator.
10. Build self-bootstrapping reasoner tuple queue.
11. Build cloud-lab dry-run stubs.
12. Run unit, integration, contract, plug-swap, resume, no-bulk, boundary, and falsifier tests.
13. Run full falsification wave.
14. Commit and push.
15. Report final status with links and unresolved blockers only after execution.

## Hard Gates

Scientific:

- Every scientific claim has source, confidence, falsifier, and audit refs.
- hERG-only overreach fails.
- Codec/replay metrics are not mechanism evidence.
- Cardiac packets exist for dofetilide, verapamil, and ranolazine.
- Multi-current context includes KCNH2, SCN5A, KCNQ1, and CACNA1C or explicit absence/planned lookup.
- Boundary-violating language blocks export.

Engineering:

- CPU-side pipeline runs end to end without GPU.
- L1 GPU work is represented by REST stubs with real schemas and fixtures.
- Every layer emits the universal envelope.
- Each layer has at least one plug-replaceability test.
- Audit hash chain validates.
- KG resume state is reconstructible.
- Falsification wave catches deliberate failures.
- No Docker is required on the originating Mac path.
- No bulk local datasets are downloaded.

Brain-functionality:

- A fresh agent can reconstruct state from repo artifacts without chat history.
- Failed falsifiers and contradictions are preserved.
- Decisions are recorded with rationale and supersession path.
- Next actions are explicit and grounded in current gates.

## Parking Rules

Park only work that truly requires GPU hardware or unavailable external credentials. Parked items must include:

- Stub implementation.
- Contract.
- Fixture.
- Audit record shape.
- Falsifier.
- Runpod or credential cutover steps.
- Acceptance gate.

Do not park CPU-side architecture, schemas, tests, audit, KG, stubs, falsifiers, packets, or orchestration.

## Final Report Requirements

When done, report:

1. Commit hash and GitHub links.
2. What was built.
3. Tests and falsification wave results.
4. Which gates pass/fail.
5. What was parked for Runpod and why it truly requires GPU.
6. Strategic decisions made without user engagement.
7. Open blockers requiring user input.

Do not report a partial win as success. If the authority metric regresses, say so and keep the failure visible.
