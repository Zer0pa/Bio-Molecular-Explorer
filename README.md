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
| `PRD.md` (to be written) | The PRD that drives the overnight long-horizon execution on a Runpod-bound machine | Medical orchestrator |
| `phases/` (to be written) | Per-phase artifacts when execution begins | Overnight executor |

## Read order for the next agent

1. `MODUS-OPERANDI.md` — how the role chain works.
2. `HANDOFF-TO-ORCHESTRATOR.md` — what you (medical orchestrator) inherit and produce.
3. `source-briefs/01-full-technology-landscape.md` and `source-briefs/02-corrections-and-architecture.md` — original technology landscape with corrections and L2.5 retrosynthesis insertion.
4. `briefing-pack/README.md` then the six numbered docs (1-scope, 2-charter, 3-inherited, 4-current-thinking, 5-open-questions, 6-evidence-and-data-map) — the cardiac wedge from the parallel RBTE work stream.
5. `synthesis/01-fresh-eyes-on-pipeline-briefs.md` — synthesis-agent reframe of the briefs; this is the substrate for your own fresh-eyes augmentation.

## Provenance

- Initial commit: 2026-04-29.
- Upstream: Brain Phase 8 (Rosalind Bioelectric Translational Engine selection) at `/Users/Zer0pa/orchestration-state/.gpd/phases/08-rosalind-bioelectric-translational-engine/`. Summarised faithfully in `briefing-pack/03-inherited-from-brain.md`; raw artifacts can be requested if the orchestrator needs more depth than the briefing pack carries.
- Synthesis agent: Claude Opus 4.7 (1M context).
- Next agent: medical orchestrator (writes `PRD.md`).
- Following: overnight executor on a Runpod-bound machine.
