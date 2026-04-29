# Open Questions for a Science / Medical Reviewer

Questions where reviewer expertise (cardiac safety, electrophysiology, regulatory science, computational biology) can move the project forward fastest. Each question is paired with the artifact it would shape and the falsifier it would help close or open.

## Cardiac mechanism graph completeness

### Q1 — Is the named channel panel the right minimum?

Inherited panel: KCNH2 / hERG (IKr), SCN5A / Nav1.5 (INa), KCNQ1 / Kv7.1 (IKs), CACNA1C (ICa,L), KCNE1 / KCNE2 accessory subunits.

Open: do we need to add KCNJ2 (Kir2.1, IK1), HCN4 (If, sinoatrial pacemaking), late INa (INaL) as a distinct entity, or RyR2 (calcium handling, CPVT-relevant) for a usefully complete cardiac-safety frame?

- **Shapes** — mechanism-graph node set; entity normalization for evidence routing.
- **Falsifier** — closes hERG-only-overreach risk if the panel is complete; opens it if the panel is wrong.

### Q2 — Where is the multi-current "balance" relationship best modelled in current literature?

The seed graph cites FDA-linked CiPA material. Is there a more current open authority — a specific O'Hara-Rudy or ToR-ORd model variant, or a recent CiPA-2 paper — that should be cited for the balance edge?

- **Shapes** — `multi-current ventricular repolarization balance` mechanism node; `CiPA multi-ion-channel assay / model family` assay node.

### Q3 — Drug-context node — which named compounds first?

The graph names a `QT-risk drug category` node but no specific compounds. Which 3–5 compounds form the right minimum for a multi-current evidence packet? Current operator suggestion: dofetilide (high TdP risk), verapamil (hERG-block + ICa,L-block, low TdP), ranolazine (multi-channel, INaL), moxifloxacin (positive control in clinical QT), sotalol (class III).

- **Shapes** — mechanism graph compound nodes; first three falsification-ledger entries.

## Phenotype feature schema

### Q4 — Which fiducials should the morphology benchmark target first?

Inherited candidates: QT, QTc, QRS duration, PR interval, ST level, T-wave amplitude / asymmetry, T-peak-to-T-end. Which are tightest as research-grade benchmarks given PTB-XL+ feature tables? Which are too operator-dependent to use without standardisation?

### Q5 — What QT correction is the reviewer's preferred default?

Bazett, Fridericia, Framingham, Hodges, individual? Each has known biases at extreme heart rates. Single inherited default is not yet committed. The choice changes the morphology benchmark's threshold tractability.

### Q6 — Single-lead vs. 12-lead?

MIT-BIH is two-channel ambulatory; PTB-XL is 12-lead clinical. Are we committing to a 12-lead-only morphology benchmark, or is a single-lead baseline acceptable first? This shapes which records can be used in the first benchmark.

### Q7 — Pre-registered preservation thresholds?

Operator working figure: median absolute QT-interval error ≤ 5 ms; 95th-percentile ≤ 15 ms vs. an open reference extractor. Tighter? Looser? Per-lead or aggregated? Reviewer's preferred bound determines the test's pass / fail line before execution.

## Evidence routing and license boundaries

### Q8 — PharmGKB, ChEMBL, BindingDB, ClinVar — cite-only or ingest?

Each has different license / use constraints. The portfolio plan does not yet specify route-by-route license posture. A reviewer with experience republishing biomedical evidence can shape this.

### Q9 — CredibleMeds taxonomy — used how?

Cite-only for taxonomy framing? Or maintain our own internal taxonomy aligned to CiPA categories? CredibleMeds explicitly should not be re-published; the falsification ledger's evidence-source policy needs the reviewer's preferred answer.

### Q10 — Blind benchmark for "engine vs. PubMed" — how operationalised?

Inherited intent: "GPT-Rosalind / mainline-plus-plugin must materially improve over standard web / literature workflows on a blind QT evidence-packet benchmark." How is "materially improve" operationalised? Specificity of cited mechanism? Compound-channel mapping accuracy? Time-to-equivalent-packet? Mechanism-edge novelty (rate of edges a baseline reader missed)?

## Regulatory framing

### Q11 — Is anything in the inherited charter at risk of being read as CDS under current FDA framing?

The portfolio is research infrastructure, not clinical decision support. A regulatory-science reviewer can pressure-test the *phrasing patterns* of generated outputs (not just the disclaimer) against FDA's CDS FAQ.

### Q12 — Does the CiPA in-silico framing imply assay-framework alignment that a regulator would treat as compliance work?

This is more about reception than intent. A reviewer with FDA-side experience can flag where the language drifts.

## Adjacent (epilepsy / neurophysiology)

### Q13 — Which 1–2 falsifiable extracellular-neurophysiology mechanism hypotheses cleanly open the second wedge?

ZPE-Neuro is bounded extracellular spike-event extraction (DANDI 000034 + IBL waveform), not EEG. A reviewer's guidance shapes when (and whether) the second wedge starts and what its first falsifiable claim is.

### Q14 — Are there channel-level mechanism nodes that bridge cardiac and epilepsy?

Examples: Nav1.6 / SCN8A in cortical excitability; KCNQ2 / KCNQ3 in neonatal epilepsy as known channelopathies. If a channel family meaningfully appears in *both* wedges, that becomes a real cross-wedge knowledge-graph win — and an argument for keeping the wedges in the same portfolio rather than separate projects.

## Engine-level

### Q15 — What single output in 4 weeks would the reviewer point at and say "this is genuinely useful, not a paraphrase"?

The most consequential question. The reviewer's answer becomes the first publishable (internally) deliverable and the operationalisation of "value-add over a competent reader with PubMed."

### Q16 — What outputs would the reviewer treat as an active red flag for overclaiming?

Phrasings, structures, framings to disallow up front. The reviewer's red-flag list joins the boundary failure-mode list in `01-scope-and-boundary.md`.

### Q17 — Where do we recruit the reviewer pool?

Internal? External cardiac-safety scientist? Channel biophysicist? Clinical electrophysiologist with regulatory exposure? The reviewer pool itself is open; a recommendation here would unblock the blind benchmark in Q10.
