# Handoff to the Medical Orchestrator — Health Work Stream

You are the medical orchestrator for the Zer0pa Bio-Molecular Explorer work stream. This document briefs you on what you inherit, what is expected of you, and what you produce.

## Boundary

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.

## What you inherit

### Source briefs (`source-briefs/`)

- **Brief #1 — Full Technology Landscape for Orchestrated AI Pipelines** (April 2026). Reference catalogue across L1 molecular simulation, L2 formulation design, L3 process development, L4 digital twins, L5 PKPD / systems pharmacology, L6 orchestration / AI. Datasets, models, tools, APIs with license classifications (A through E).
- **Brief #2 — Corrections, Augmentations, and Pipeline Architecture** (April 2026). Working document. Corrects six issues from Brief #1 (most notably L4 misclassification — COPASI / Tellurium are L5, L4 needs PharmaPy + OpenModelica + FMI + Eclipse Ditto; PINN drug release was a research paper, not a deployable tool — DeepXDE is the production framework; OpenFE was missing from L1 — added as MIT-licensed RBFE + ABFE comparable to Schrödinger FEP+; QSP-Copilot is a workflow accelerator, not an autonomous model generator; GPT-Rosalind is access-gated, the practical stack is Opus 4.7 + GPT-5.4 + Codex Plugin + TxGemma). Adds a **new L2.5 retrosynthesis layer** (AiZynthFinder, ASKCOS USPTO models, Chemprop forward-yield, Rxnmapper). Specifies the orchestration architecture (LangGraph + Prefect + Parsl). Provides the regulatory map (ICH M15, FDA MIDD, FDA AI / SaMD, FDA CDS FAQ). Combined master tool selection table supersedes Brief #1's Executive Map.

### Briefing pack (`briefing-pack/`)

Seven-doc primer written for a science / medical thinking agent on the cardiac wedge of the parallel **RBTE (Rosalind Bioelectric Translational Engine)** workstream. RBTE was selected from a 5-candidate opportunity matrix as the first healthcare specialisation (cardiac QT / ion-channel / drug-safety scored 31 / 25; epilepsy / extracellular-neurophysiology second 28 / 18; generic cancer, ICU, neurodegenerative deferred). The briefing pack defines:

- **01 scope and boundary** — what the portfolio is and is not, the four active falsifiers (codec-as-mechanism, noise-brittle phenotype, hERG-only overreach, clinical overclaim), failure-mode phrasings.
- **02 scientific charter** — authority question, selected wedge entities (KCNH2 / hERG, SCN5A / Nav1.5, KCNQ1 / Kv7.1, CACNA1C; multi-current ventricular repolarization balance; QT-risk drug categories), why now, why this portfolio.
- **03 inherited from brain** — Brain Phase 8 decisions: opportunity matrix, 23-node / 12-edge mechanism graph, 6-claim falsification ledger, phenotype fingerprint JSON Schema, 8A → 8F long-horizon roadmap, residual gaps Brain itself flagged.
- **04 current thinking** — operator's read on what is genuinely strong (CiPA framing, dataset choice honest, no-Docker as feature) and what is thin (audit-checkout recency gap, replay vs morphology, NaN silent bug, mechanism graph "very seed", access-gated reasoning, license posture not designed). Five next-tests in leverage order: morphology preservation benchmark; NaN / input-validation gate; multi-current evidence packets on dofetilide / verapamil / ranolazine; blind benchmark engine vs PubMed; gate the second wedge.
- **05 open questions** — 17 concrete questions for a cardiac-safety / electrophysiology / regulatory-science reviewer.
- **06 evidence and data map** — public ECG datasets (MIT-BIH / PTB-XL / PTB-XL+ / NSTDB / EDB), regulatory anchors (FDA E14 / S7B, CiPA), tooling anchors (GPT-Rosalind, Life Sciences Plugin, ~50 routes), local proof anchors (ZPE-Bio audit checkout metrics with recency caveat — MIT-BIH PRD ≤ 2.32 %, PTB-XL ≤ 5.29 %, NSTDB SNR ~60.5 dB, Sleep-EDF aggregate is 0 entries), acknowledged citation gaps, NOT-in-scope sources.

### Synthesis (`synthesis/`)

Fresh-eyes reading of the two pipeline briefs by the prior synthesis agent. Captures:

- **Two reframes that change what is being built**: (1) this is a falsification engine, not a forward pipeline — every layer can emit (output, confidence, falsifier) and the agent's job is back-edge propagation; (2) L1-L5 are commodity, L6 is where the Cambrian moment lives — differentiator is intelligence-density per decision, not throughput.
- **Ten specific things the briefs do not see**: retrosynthesis cost as L2 scoring function (not downstream filter); Boltz-2's joint output as confidence-decomposition engine; TxGemma fine-tuned on lab's own simulation outputs as the Rosalind moat; audit trail (not approved tool) as regulatory acceptance; L4 first as virtual plant before any synthesis route emerges; cloud-lab API integration (Strateos / Emerald / Arctoris) for closed-loop wet-bounded work; Anthropic Agent SDK + Claude Code subagents as 2026-shaped meta-orchestration; agent-token spend changes economics (intelligence-per-decision over candidates-per-minute); cardiac wedge as defensible first scope; plug-replaceability as the actual product.
- **Build ambition** with multi-agent topology, six-week local-first sequence, agent-token cost shape, and Runpod migration as stub-swap.
- **Twelve-section PRD outline** for the orchestrator to expand.

## What you must do

Write `PRD.md` at the top of this repo. The PRD specifies a long-horizon overnight execution by a separate set of overnight-executor agents on a different machine that will eventually have Runpod GPU access.

### Apply recursive fresh eyes

Do not paraphrase the prior synthesis. Apply your own fresh eyes:

- Where is the prior synthesis still incomplete?
- What gaps does it leave that you can close?
- What innovations does it invite that you can specify?
- What interface contracts must be locked that the synthesis only sketched?
- What failure modes need explicit recovery patterns?
- What deep research lookups would unlock strategic decisions?

If your PRD is not substantively richer than the synthesis it inherited from, you have not done your job.

### Spawn sub-agents

You are not expected to do this alone. Spawn sub-agents in parallel worktrees for at minimum:

- Per-layer specification (L1 / L2 / L2.5 / L3 / L4 / L5 / L6).
- Falsification ledger expansion — RBTE's 6 claims plus pipeline-wide layer-by-layer falsifiers.
- Audit-trail schema — ICH M15-shaped per-molecule provenance log.
- Tool-agnostic interface contracts — the plug-replaceability acceptance criterion.
- Cardiac specialisation evidence packet — dofetilide / verapamil / ranolazine as the first three named compounds.
- Cloud-lab integration option — Strateos / Emerald / Arctoris API stubs in L6.
- Self-bootstrapping reasoner — TxGemma fine-tuning queue from day one; (input, output, falsifier, ground-truth) tuple flow.
- KG schema — episodic memory writing from day one; the lab's own corpus as the moat.

### Use deep research at stuck points

When a sub-agent reaches an unknown that requires up-to-date external evidence (current best CiPA model variant, latest OpenFE protocol, current TxGemma fine-tuning best practice for therapeutics, regulatory implication of a specific design choice, ICH M15 audit-log shape that meets the FDA's current MIDD expectation), call out to Perplexity Pro / Gemini Advanced deep research as a tool. Surface the strategic ones to the user — those are innovation points.

### Maximally front-load pre-Runpod engineering

The PRD must specify what every overnight-executor agent does without GPU access. **Acceptance criterion**: when the Runpod machine comes online, the entire CPU-side of the pipeline is complete and GPU layers are stubs ready to be swapped. The cutover must be a config-flag-shaped change, not an architectural rewrite.

## What you produce

A single `PRD.md` at the top level of the repo with these twelve sections at minimum:

1. **Scope and boundary** — verbatim research-only boundary; explicit cardiac-first specialisation with general-pipeline-second framing; what the work stream is and is not.
2. **Architecture invariant** — tool-agnostic at every layer; interface contracts (SMILES, mmCIF / PDB, RXNSMILES, SBML, FMI, JSON Schema function calls); plug-replaceability acceptance test ("swap MD engine in 1 day with no downstream breakage").
3. **Falsification engine framing** — every layer emits (output, confidence, falsifier, audit record); back-edge propagation specified per layer transition; RBTE 6-claim ledger merged with pipeline-wide layer falsifiers; failure-mode phrasing list extended.
4. **Build sequence** — L2-L6 local-first on Mac; L1 as REST stubs returning canned outputs; per-overnight-executor-agent decomposition; the order in which layers come online; the test cases that gate each layer's acceptance.
5. **Agent topology** — Opus 4.7 strategic planner; GPT-5+ heavy code; sub-agents per layer in parallel worktrees; TxGemma 27B as domain-reasoner tool; Perplexity / Gemini deep research as stuck-point tools; private knowledge graph schema with episodic memory writing from day one.
6. **Audit-trail spec** — ICH M15-shaped per-molecule provenance log; KG schema (nodes, edges, hyperedges); what every layer logs; how the audit log proves regulatory-acceptability shape (the trail not the tool).
7. **Cardiac wedge first deliverable** — dofetilide / verapamil / ranolazine seed evidence packet; how multi-current evidence packet generation is specified; what the engine produces that PubMed plus a competent reader cannot; pre-registered acceptance thresholds (e.g., median absolute QT-interval error ≤ 5 ms vs open reference extractor; 95th percentile ≤ 15 ms).
8. **Self-bootstrapping reasoner** — TxGemma 27B fine-tuning queue wired from day one; how (input, output, falsifier, ground-truth-when-available) tuples flow to a private fine-tuning corpus; what a 6-month-of-operation private corpus looks like and why it is the moat.
9. **Cloud-lab option** — REST API stubs for Strateos / Emerald / Arctoris in L6; how the simulation-only pipeline becomes a closed-loop simulation + bounded-wet-lab pipeline as a config flag; closed-loop pattern from JACS COF synthesis March 2026 (350 % crystallinity improvement) as the architectural reference.
10. **Runpod migration plan** — exact stub-swap procedure; per-layer GPU requirements (OpenMM, OpenFE, DiffDock V2, Boltz-2, Protenix); cost shape; cutover acceptance gates.
11. **Acceptance gates** — scientific gate (falsifier coverage, source grounding, no clinical claim); engineering gate (CPU-only build runs end-to-end; plug-swap test passes); brain-functionality gate (next-agent state reconstructible from repo + KG + audit log without conversation history).
12. **Open questions for the user / for the next agent** — explicitly. What you could not resolve. What requires user innovation input. What the overnight executor needs that you could not prefigure.

## Constraints

- **Mac storage tight on the originating machine** (~20 GiB free) — bulk artifacts go to private Hugging Face dataset under Architect-Prime when offload is needed; HF token at `~/.cache/huggingface/token` on the originating machine.
- **No Docker on the originating Mac** — overnight executor agents may use Docker on Runpod or wherever they run.
- **No bulk local datasets** — manifests + metadata + small slices only.
- **GitHub canonical** — all sub-agent work commits back to `Zer0pa/Bio-Molecular-Explorer` before PRD finalisation.
- **No clinical deployment, regulatory submission, or drug-safety certification claims** — research infrastructure only.
- **No re-deriving what RBTE briefing pack already settled** — read it first; build on it.

## Authorities and tooling (use what your environment makes available)

- GitHub auth: `Zer0pa-Architect-Prime` on the originating machine; cross-machine, the user provides.
- HF token: at `~/.cache/huggingface/token` on the originating machine; cross-machine, the user provides.
- Anthropic Opus 4.7 + Claude Code SDK or Anthropic Console — primary planning and code review at maximum reasoning effort.
- OpenAI GPT-5+ (5.4 today, 5.5 when available) at xhigh reasoning — primary heavy-code generator.
- Perplexity Pro / Gemini Advanced — stuck-point and innovation-point deep research.
- TxGemma 27B (open-weight, Gemma 2 terms — verify) — domain reasoner; CPU-quantised for dev.
- LangGraph + Prefect + Parsl as the orchestration trio per Brief #2.
- LangGraph state-graph for L6 internal flow; Prefect for workflow execution / scheduling / retry / monitoring; Parsl for async dispatch of long-running simulation jobs to GPU / HPC.

## Where the PRD lands and what comes next

Commit `PRD.md` to the top level of `Zer0pa/Bio-Molecular-Explorer`. After the PRD is final, write `HANDOFF-TO-OVERNIGHT-EXECUTOR.md` describing what the overnight-executor agent inherits, what it produces, and the constraints / authorities it operates under. That handoff document mirrors the structure of this one.

The user will then trigger the overnight execution on a separate Runpod-bound machine using a startup prompt analogous to `ORCHESTRATOR-STARTUP-PROMPT.md`.

## Success looks like

- A PRD that the overnight executor can decompose into parallel sub-streams without further user input.
- Every interface contract locked. Every falsifier specified. Every acceptance gate measurable.
- A clear cardiac-wedge first deliverable that closes the engine vs PubMed gap on three named compounds.
- A clear plug-replaceability test that proves the architecture survives the next four frontier-model releases.
- Open questions explicitly listed so the user can innovate on the strategic ones without re-reading everything.
