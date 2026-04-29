# Fresh-Eyes Synthesis on the Pipeline Briefs

Synthesis-agent output. Captures the operator-read on the two source briefs (`source-briefs/01-full-technology-landscape.md`, `source-briefs/02-corrections-and-architecture.md`) by Claude Opus 4.7 (1M context), 2026-04-29. Read by the medical orchestrator as the substrate for their own fresh-eyes augmentation.

## Boundary

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.

## Two reframes that change what is being built

### Reframe 1 — this is not a pipeline, it is a falsification engine

The briefs describe L1 → L2 → L2.5 → L3 → L4 → L5 with L6 orchestrating. Forward chain. Every actual drug-development decision is closed-loop: candidate fails ADMET → constrain L2 generative; synthesis too costly → constrain L2.5 cost into L2 scoring; PBPK predicts poor exposure → return to formulation; FEP says no binding → return to L2 with anti-pattern. **What the briefs call orchestration is actually back-edge propagation — turning every layer's failure into a constraint on upstream generators.**

Every layer can emit a falsifier alongside its prediction:

- DiffDock V2 confidence < 0.5 → falsifier on a binding-pose hypothesis.
- OpenFE convergence (free-energy bootstrap error > 0.5 kcal / mol) → falsifier on a binding-affinity hypothesis.
- PBPK goodness-of-fit threshold breach → falsifier on a dose-prediction hypothesis.
- AiZynthFinder route-not-found → falsifier on a synthesizability hypothesis.
- Lipinski violations > N → falsifier on a drug-likeness hypothesis.
- NSTDB calibrated-noise instability → falsifier on an ECG-phenotype hypothesis.

That is exactly the discipline the RBTE briefing pack already encodes for cardiac signal phenotypes. **Bolt the pipeline directly to the RBTE falsification ledger and the deliverable becomes the world's first open, audit-trail-shaped, falsification-first in silico drug-safety engine.**

Big pharma with Rosalind access is racing to "predict better." There are very few open players racing to "falsify cheaper with provenance." That is the publishable, fundable, defensible angle — and it makes RBTE and the Pipeline the same project wearing different hats.

### Reframe 2 — L1 to L5 are commodity. L6 is where the Cambrian moment lives

Force fields, MD engines, FEP, retrosynthesis, PBPK — all mature, all open under permissive licenses, all improving on quarterly cadence. The differentiator is intelligence-density per decision in L6, not throughput. **The actual product is not the simulation chain (everyone has access). The actual product is a multi-model, multi-agent, audit-trailed reasoning system that triages 10,000 candidates into 100 worth a human looking at, with a falsification trace per rejection.**

Compute economics:

- ~$2 / A100-hr × 30-60 GPU-min × 10K candidates ≈ $10K-$20K per virtual screen — cheap.
- Agent tokens at xhigh reasoning across multi-agent + Perplexity research per molecule ≈ $50-$200 per molecule.
- 10K candidates × $50-$200 ≈ $500K-$2M in agent spend vs $20K in GPU.

**The economics favour intelligence-per-decision over candidates-per-minute. Build for depth.**

## Ten specific things the briefs do not see

### 1. Retrosynthesis cost is not a downstream filter; it is a scoring function in L2

REINVENT 4 takes custom scoring functions. ASKCOS / AiZynthFinder score a SMILES in <1 minute. Dropping `route_depth × yield × buyability × SAScore` directly into REINVENT's reward changes the candidate distribution at the *generator*, not after. The brief positions L2.5 between L2 and L3; the higher-leverage move is to feed L2.5 *back into* L2's reward.

### 2. Boltz-2's joint structure + binding output is a confidence-decomposition engine

When structure confidence is high but binding confidence is low, the model is telling you "I know the geometry, I don't think it binds." That meta-signal is exactly what an uncertainty-aware router needs to decide "don't waste FEP on this; reroute to a different protein conformation or different pose ensemble." The brief notes the unification; it doesn't draw out that anti-correlation is a routing primitive.

### 3. TxGemma 27B fine-tuned on the lab's own simulation outputs is the path to a Rosalind-equivalent moat

Brief #2 mentions this in passing. Every (input → simulation → output) tuple from L1-L5 is a fine-tuning pair. After 6 months of operating the pipeline on a focused wedge (cardiac / QT / ion-channel), the lab has a private fine-tuning corpus more valuable than any public ChEMBL slice for that domain. **Self-bootstrapping reasoning.** The pipeline architecture should be designed to emit (input, output, falsifier, ground-truth-when-available) tuples to a fine-tuning queue from day one. Every run trains tomorrow's reasoner.

### 4. Audit trail is regulatory acceptance — not approved tools

ICH M15 (final January 2026) says "documented model qualification," not "use Simcyp." The pipeline's deterministic audit log per molecule run (which version of which tool, hash of inputs, confidence score, falsifier checked) is what *makes* a model qualifiable later. **Build audit-trail-shaped from L1 — every node emits structured provenance — and you ship something a regulator can audit even if you used PK-Sim instead of NONMEM.** This is the GPD / falsification discipline applied to drug development. Nobody else open ships this shape.

### 5. L4 manufacturing digital twin is the most counter-intuitive lab-without-a-plant advantage

Big pharma builds L4 because they have plants. A computational lab with no plant does not need L4 — and that is the gap. **Build a complete virtual-plant in PharmaPy + OpenModelica + FMI before any synthesis route emerges.** When a candidate clears L1-L2.5, the virtual plant tells you immediately whether the candidate's synthesis route can be made at scale, what the bottleneck unit operation is, and what the cost-of-goods looks like. Genentech / Moderna has to align their plant + their AI. We can build the AI-native virtual plant first.

### 6. Cloud labs change "in silico" into "in silico + bounded wet-lab"

Strateos, Emerald Cloud Lab, Arctoris, Synthace expose synthesis and assay execution as REST APIs. The agent framework already speaks REST. **L6 can issue `synthesize_compound(SMILES) → run_dissolution_assay(formulation) → return_data` as tool calls.** Suddenly the pipeline closes the loop with real wet-lab data without owning a wet lab. The March 2026 JACS paper on closed-loop COF synthesis (350 % crystallinity improvement) is exactly this pattern. The brief assumes pure simulation; the frontier is simulation + remote-execution closed loop.

### 7. The brief lists agent frameworks (LangGraph, CrewAI, AutoGen) — it does not mention the meta-orchestration pattern

Anthropic Agent SDK + Claude Code subagents + parallel worktrees + persistent memory. That is a layer above LangGraph. **L6 should be: Opus 4.7 strategic planner spawning GPT-5+ sub-agents per pipeline layer running in parallel worktrees, each calling LangGraph state-graphs for its own internal flow, all writing to a shared private KG, with Perplexity / Gemini deep-research as tools at stuck points.** That is a 2026-shaped orchestration. Brief #2's L6 is 2024-shaped.

### 8. Compute estimate misses the agent-token cost line

~$50-$200 / molecule in agent reasoning at xhigh-effort multi-agent, vs ~$1-$2 / molecule in GPU. Across 10K candidates that is $500K-$2M in agent spend vs $20K in GPU. **The architecture should optimise for one really smart triage agent reasoning over all 6 layers per molecule, not 100 dumb forward runs.** This inverts the brief's compute optimisation framing.

### 9. The cardiac wedge from RBTE gives the Pipeline a defensible first scope

A "general drug development pipeline" competes with Insilico Medicine, Schrödinger, Recursion. A "cardiac QT / proarrhythmia / ion-channel drug-safety in silico falsification engine" has very few open competitors. The existing FDA E14 / S7B + CiPA regulatory framing, the existing ZPE-Bio ECG proof anchors, the existing falsifiers (codec-not-mechanism, noise-brittle, hERG-only-overreach, clinical-overclaim), the existing public ECG datasets (MIT-BIH / PTB-XL / NSTDB / EDB), the existing channel panel (KCNH2 / SCN5A / KCNQ1 / CACNA1C), the existing named compounds (dofetilide / verapamil / ranolazine) — **all of this is already in the RBTE briefing pack and slots directly as the Pipeline's first specialised application.** Do not ship a generic pipeline. Ship a cardiac-specialised one that *generalises*.

### 10. The plug-replaceability is the real architectural product

Force fields will change every quarter. Structure-prediction models every six months. Reasoning models every three. Retrosynthesis algorithms continuously. **The architecture's product is not "OpenMM + Boltz-2 + AiZynthFinder + REINVENT 4 + LangGraph." It is "swap any layer's tool in <1 day with no downstream breakage."** Ship strict interface contracts (SMILES → 3D, 3D → docking pose, pose → binding ΔG, ΔG → ADMET, ADMET → route, route → flowsheet, flowsheet → PK), make the tool selection per layer pluggable, and the pipeline survives the next four frontier releases instead of being rebuilt. **Tool-agnostic at every layer is the actual differentiator.**

## What "maximal unfettered ambition" looks like for the build

Given Opus 4.7 + GPT-5+ + sub-agents + Perplexity / Gemini deep research, what is genuinely buildable in 4-6 weeks before any GPU access?

- **Week 0** — Opus drafts PRD; user reviews; lock.
- **Week 1** — repo skeleton; private KG schema (RBTE mechanism graph + falsification ledger + every tool's I / O contracts as nodes); audit-log spec; Anthropic Agent SDK + LangGraph + Prefect + Parsl orchestration scaffold; episodic memory wired to write-only KG.
- **Weeks 2-4 (parallel sub-agent worktrees)** — six layer-specialist agents:
  - **L2 (CPU)**: RDKit + DeepChem + DeepXDE PINN dissolution + REINVENT 4 with retrosynthesis-aware reward (the L2.5 feedback closure).
  - **L2.5 (CPU)**: AiZynthFinder + ASKCOS USPTO models + Chemprop forward-yield + Rxnmapper. Emits cost / depth / SAScore signals to L2.
  - **L3 (CPU)**: DWSIM + PharmaPy unit operations + OpenFOAM / LIGGGHTS as small canned-output stubs.
  - **L4 (CPU)**: full virtual plant — PharmaPy flowsheet + OpenModelica equation-based + FMI bus + Eclipse Ditto stub for sensor binding. **Contrarian leverage; build before any candidate lands.**
  - **L5 (CPU)**: PK-Sim Python wrapper + nlmixr2 R-bridge + Tellurium + COPASI + QSP-Copilot reference reimplementation under clean license.
  - **L6 (CPU)**: meta-orchestrator. Opus strategic planner. GPT-5+ calculation engine. TxGemma 27B inference (CPU-quantised for dev; GPU on Runpod later). Tool schemas for every layer. Falsification-aware router with Boltz-2-style confidence-decomposition logic.
- **Weeks 5-6** — L1 stubs (REST endpoints returning canned OpenMM / OpenFE / DiffDock V2 / Boltz-2 / Protenix outputs); end-to-end mock runs on the cardiac wedge test cases (dofetilide, verapamil, ranolazine); falsification ledger v1 wired in; KG accumulating its first 100-1000 episodic decision records; audit log proven ICH M15-shaped. **This is the entire pipeline running end-to-end on a Mac with no GPU.**
- **Runpod migration** — containerise L1 stubs; replace stubs with real GPU inference behind the same REST contracts; flip a config flag; pipeline runs real simulations. Days, not months. The whole point of building L2-L6 first is that GPU comes online into a known-good system.

The agents do this. Opus plans and reviews. GPT-5+ writes the heavy code. Sub-agents work in parallel worktrees. Perplexity / Gemini get called at scientific stuck points and the user weighs in at innovation points. Episodic memory captures every decision so context doesn't bleed across sub-agents.

## Twelve-section PRD outline (handed to the medical orchestrator for expansion)

1. Scope and boundary — verbatim research-only boundary; explicit cardiac-first specialisation with general-pipeline-second framing.
2. Architecture invariant — tool-agnostic at every layer; SMILES / PDB / RXNSMILES / SBML / FMI as the contract surface; every node emits (output, confidence, falsifier, audit record).
3. Build sequence — L2-L6 local-first on Mac; L1 as REST stubs; Runpod migration as a stub-swap.
4. Agent topology — Opus planner + GPT-5+ calc + sub-agents in worktrees + TxGemma domain reasoner + Perplexity / Gemini deep-research tools + private KG with episodic memory.
5. Falsification ledger — every layer's failure modes mapped to RBTE-style falsifiers; back-edge propagation specified per layer transition.
6. Audit-trail shape — ICH M15-aware structure; deterministic provenance per molecule run; KG as system-of-record.
7. Cardiac first specialised wedge — dofetilide / verapamil / ranolazine seed evidence packet (positive control + low-TdP-hERG-blocker + multi-channel reference).
8. Self-bootstrapping reasoner — TxGemma 27B fine-tuning queue wired into the audit log from day one.
9. Cloud-lab option — Strateos / Emerald API stubs in L6 so wet-lab closure is a config flag, not a rewrite.
10. Plug-replaceability test — "swap MD engine in 1 day" written as an acceptance criterion.
11. Acceptance gates — scientific gate (falsifier coverage, source grounding, no clinical claim); engineering gate (CPU-only build runs end-to-end; plug-swap test passes); brain-functionality gate (next agent picks up state from KG and audit log).
12. Open questions for the user / for the next agent — explicitly.

The non-obvious section is #1 + #7. **The Pipeline does not need to be a general drug pipeline first. The cardiac wedge is the right first specialisation, and it slots directly onto everything RBTE already has.** General drug pipelines are crowded; open audit-trailed cardiac falsification engines are not.

## What the orchestrator should pressure-test before locking the PRD

- **Is the cardiac-first specialisation the right scope?** Or does the orchestrator's fresh eyes see a cleaner first wedge that still uses the RBTE assets but reaches further? (The synthesis agent committed to cardiac; the orchestrator can confirm or amend.)
- **Are the three named compounds — dofetilide / verapamil / ranolazine — the right minimum panel?** Or should the orchestrator add (e.g., moxifloxacin as a clinical positive control, sotalol as class III)?
- **What does "the engine produces what PubMed plus a competent reader cannot" actually look like as a deliverable?** The most consequential acceptance criterion. The synthesis agent left it as a question; the orchestrator should propose at least three concrete forms.
- **Is LangGraph + Prefect + Parsl + Anthropic Agent SDK the right meta-orchestration stack?** Or is there a stronger 2026-current pattern the orchestrator's deep-research surfaces?
- **What is the first unit of (input, output, falsifier, ground-truth) that flows to the TxGemma fine-tuning queue?** Concrete shape, not aspiration.
- **What is the audit log's first regulatory-acceptable schema?** ICH M15 lays out qualification documentation; what is the minimal structure a regulator could read?

These are the questions where deep research and recursive fresh eyes are most valuable.

## Provenance

- Synthesis agent: Claude Opus 4.7 (1M context).
- Source: `source-briefs/01-full-technology-landscape.md`, `source-briefs/02-corrections-and-architecture.md`, `briefing-pack/` (RBTE 7-doc primer), Brain Phase 8 artifacts at `/Users/Zer0pa/orchestration-state/.gpd/phases/08-rosalind-bioelectric-translational-engine/` on the originating machine.
- Date: 2026-04-29.
- Next role: medical orchestrator (writes `PRD.md`).
