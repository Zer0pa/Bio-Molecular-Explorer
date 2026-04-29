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

## Implementation status (overnight execution, 2026-04-30)

- **Tests**: 333 passing (unit + integration + plug-swap + falsification wave + cardiac packet).
- **Layers**: L1 (REST stubs + canned outputs for the cardiac wedge), L2 (property/formulation with L2.5 back-edge), L2.5 (retrosynthesis with RXNSMILES + atom-map validators), L3 (process + mass balance), L4 (FMU/Ditto sensor twin), L5 (PKPD + cardiac exposure-channel bridge), L6 (LangGraph-shaped router with silent_falsifier_loss preservation).
- **Cross-cutting**: universal layer envelope (Pydantic + JSON Schema), append-only audit log with hash chain, KG with cardiac seed (33 nodes, 21 edges), 16-class falsifier registry with 13 detectors, falsifier ledger, self-bootstrapping reasoner with PRD-shaped tuples and clinical-overclaim self-policing, cloud-lab dry-run adapters (Strateos/Emerald/Arctoris) with hard interlocks.
- **Cardiac wedge deliverable**: three packets (dofetilide PASS / verapamil PASS / ranolazine PASS) generated via `scripts/generate_cardiac_packets.py`; balance score signs match the multi-current story (dofetilide +0.17 IKr-pure outward, verapamil −0.24 ICaL compensates, ranolazine −0.11 INaL-dominant). PubMed-baseline lift: ~47-51 points above competent-reader baseline.
- **Plug-replaceability**: nine tests covering all six layers + L6 router + cross-layer contract version invariant. Pass.
- **Falsification wave**: every named trigger (invalid SMILES, missing RXNSMILES/atom-map, mass balance, L4 sensor, SBML, hERG-only, clinical-overclaim, stub-laundering, missing falsifier ref, plug regression, NaN ECG, codec-as-mechanism, noise-brittle phenotype, license drift, silent falsifier loss, PubMed no-value-add) caught, audited, routed, and preserved in the ledger. Pass.
- **Runpod migration**: `runpod.config.yaml` + `docs/runpod-migration.md` define the stub-swap procedure; backend flag flip per adapter is the entire migration.

## Provenance

- Initial commit: 2026-04-29.
- Upstream: Brain Phase 8 (Rosalind Bioelectric Translational Engine selection) at `/Users/Zer0pa/orchestration-state/.gpd/phases/08-rosalind-bioelectric-translational-engine/`. Summarised faithfully in `briefing-pack/03-inherited-from-brain.md`; raw artifacts can be requested if the orchestrator needs more depth than the briefing pack carries.
- Synthesis agent: Claude Opus 4.7 (1M context).
- Medical orchestrator: produced `PRD.md`.
- Overnight executor: Claude Opus 4.7 lead with Sonnet subagents (L1/L2/L2.5/L3/L4/L5/reasoner/cloud-lab).
