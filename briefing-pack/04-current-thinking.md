# Current Thinking (Operator Read)

This is the operator's synthesis as of 2026-04-29 — where the inherited reasoning is strong, where it is thin, and what a science / medical reviewer should pressure-test. It is not Brain output. It is opinionated and meant to be challenged.

## What is genuinely strong about the inherited charter

1. **The wedge is unusual in a useful way.** Most life-science-LLM projects either lack a deterministic signal layer (so they devolve into literature-paraphrase) or lack cross-evidence reasoning (so they devolve into pure signal processing). The cardiac QT / ion-channel / drug-safety frame is one of the few wedges where both layers are needed and both are within reach.

2. **The boundary is named in a falsifiable way.** "Research-only" is often hand-waved. Here the four active falsifiers are concrete: codec-as-mechanism, noise-brittle phenotype, hERG-only overreach, clinical overclaim. Each has a defined trigger. That is rarer than it looks in AI-bio efforts.

3. **The CiPA framing is correct.** Anchoring to the multi-current balance picture (rather than hERG IC50 alone) is what current cardiac-safety regulatory science actually expects. The seed graph already encodes this with a `requires_context` edge from KCNH2 / hERG to the multi-current balance node, plus an `hERG-only-overreach` falsifier. This puts the project on the right side of CiPA-2-era thinking, not 2005-era thinking.

4. **The dataset choice is honest.** MIT-BIH (small, open, classic), PTB-XL (large, 12-lead, cardiologist-annotated), NSTDB (calibrated noise — used as a *falsifier*, not a benchmark to win), EDB (ST / T morphology with medication / electrolyte metadata). These are the right four for a phenotype-bridge engine. PTB-XL+ adds median beats and fiducial points — which is what the morphology gap actually needs.

5. **No-Docker / no-bulk-local is a feature, not a constraint.** It forces manifest-first thinking, which is exactly the right discipline for a research-infrastructure layer that other agents will inherit. If the prototype required a Docker environment to render, the methodology would already have failed.

## Where the inherited reasoning is thin

1. **The strongest ZPE-Bio metrics were read from a dated audit checkout, not a fresh main reproduction.** The Brain's capability map flagged this. Headline numbers — MIT-BIH PRD ≤ 2.32%, PTB-XL PRD ≤ 5.29%, NSTDB SNR ~60.5 dB — come from `/Users/Zer0pa/.codex-license-audit-20260422/p0/ZPE-Bio/`, not a current `Zer0pa/ZPE-Bio` main run. Public proof files exist on main but their *values* have not been re-asserted against current main. This is a recency gap, not a falsity claim. A science reviewer should treat the PRD numbers as indicative-pending-rerun.

2. **The proof base is replay / integrity-side, not morphology-side.** ZPE-Bio currently proves "we can compress and reconstruct the ECG with bounded error." It does not prove "we can extract a QT / QTc / QRS / PR fiducial that agrees with a cardiologist or with PTB-XL+ feature tables." The cardiac wedge requires the latter. The Brain acknowledges this as a gap; in operator's view it is the single most consequential next-test priority.

3. **The NaN silent-bug is more than a hygiene issue.** ZPE-Bio's recorded behaviour is that NaN inputs can produce silently incorrect reconstruction with PRD reported as 0.0. For a phenotype fingerprint, this means a record with even one NaN sample could yield a fingerprint that *looks* perfectly preserved while encoding nothing. Until upstream input validation rejects NaN, the phenotype fingerprint cannot be trusted on uncurated public data. This should gate any morphology benchmark, not just any clinical posture.

4. **The mechanism graph is honest about being a seed, but it is *very* seed.** Three planned-lookup gene / channel nodes (only KCNH2 is source-grounded). One source-grounded mechanism node (multi-current balance). One regulatory-science assay framing (CiPA). No specific QT-prolonging compounds named. No assay data integrated. A science reviewer reading this graph alone would not learn anything about cardiac risk that they did not already know. The graph is a *frame*, not yet a contribution.

5. **GPT-Rosalind is access-gated. The plan acknowledges this, but does not yet have a concrete fallback that proves the methodology on mainline + plugin alone.** If the access falsifier — "mainline-plus-plugin does not materially improve over standard web / literature workflows on a blind QT evidence-packet benchmark" — triggers, the whole engine concept is in question. Not the cardiac wedge specifically, but the value-add of the engine over a competent human researcher with PubMed.

6. **CredibleMeds / PharmGKB / ChEMBL / BindingDB integration is sketched but not designed.** These are the right tools for cross-evidence cardiac-safety reasoning. They each have license / use constraints (CredibleMeds explicitly should not be re-published; PharmGKB has license tiers). The plan does not yet specify which routes are read-only-citation vs. ingest, or how license boundaries are honoured. A reviewer with regulatory experience should pressure-test this.

7. **Repo-count drift is a tiny example of a bigger recency-discipline question.** Brain `STATE.md` said 23, current `gh` says 24. That single drift is harmless. But it points to a pattern: the Brain's snapshots can disagree with live truth even when only days old. The portfolio's evidence pipeline must assume external sources drift faster than the local mirror, and design re-validation passes accordingly.

## What I think should be tested next, in order of leverage

### 1. Morphology preservation benchmark (highest leverage)

The single most consequential gate. Procedure:

- Take a small slice (e.g., 10–50 records each) of MIT-BIH, PTB-XL, PTB-XL+, EDB.
- Pre-register thresholds before running. A defensible starting set: median absolute QT-interval error ≤ 5 ms, 95th-percentile ≤ 15 ms vs. an open reference extractor; analogous bounds for QRS duration, PR interval, ST level, T-amplitude.
- Run ZPE-Bio replay on each slice.
- Extract QT / QRS / PR fiducials *from the reconstructed signal* — not from the raw — using an open extractor (e.g., NeuroKit2, ECGdeli, or PTB-XL+ feature tables).
- Compare to ground-truth fiducials.

If preservation passes, the phenotype layer is real and the cardiac wedge has its first contribution. If it fails, the cardiac wedge is in trouble — not because ZPE-Bio is bad, but because *this* claim was untested.

### 2. NaN / input-validation gate

Add an upstream validator that rejects NaN / inf / empty / non-finite samples before they reach ZPE-Bio. Document the rejection. The phenotype fingerprint becomes trustworthy only after this gate is in place. This is small engineering effort; high methodological value.

### 3. CiPA-style multi-current evidence packet on three named compounds

Pick three compounds with strong public regulatory data and well-studied multi-current effects:

- **Dofetilide** — high torsade risk; clean IKr blocker; the textbook positive case.
- **Verapamil** — IKr blocker but *low* torsade risk because of compensating ICa,L block; the textbook hERG-only-overreach refuter.
- **Ranolazine** — multi-channel; INaL involvement is the headline; the textbook "multi-current matters" case.

Generate evidence packets that link compound → multi-channel effect → expected ECG morphology change. Each packet must reach the *known public regulatory reading* of the compound. If the engine cannot reach the known reading using mainline + plugin, it has no value-add over PubMed and the access falsifier is real.

### 4. Falsifier on the engine itself, not just the claims

Run a blind QT evidence-packet benchmark: a senior cardiac-safety scientist (or a strong proxy) writes the expected packet content for a held-out compound; the engine writes its own; compare. The Brain mentions a blind benchmark but does not yet design one. A science reviewer can shape the design.

### 5. Gate the second wedge

Do not start the epilepsy / extracellular wedge until items 1–3 close on cardiac. The temptation is to broaden; the risk is to broaden before the first loop is reproducible. The roadmap is clear about this; it just has to be enforced.

## Biases I want a reviewer to challenge

- **Anchoring to ECG just because we have ECG.** Maybe the strongest *use* of GPT-Rosalind-style reasoning is somewhere our current proof base does not yet reach — e.g., variant-to-channelopathy reasoning where the signal layer is patch-clamp data we don't host. Worth a sanity check: does the ECG anchor genuinely add unique value, or does it just give us comfort?

- **CiPA as settled science.** CiPA is a research framework, not a closed scientific question. A reviewer with current cardiac-safety expertise may flag that recent literature has added or revised currents (late INa contributions, IK1 stability dynamics, role of intracellular calcium handling). The graph should evolve.

- **"Falsification first" used as a license to add unfalsifiable framing later.** The four active falsifiers are good. As the graph grows, every new edge needs its own falsifier, or a documented "no falsifier yet, used as inference only" tag. Drift is the failure mode.

- **Treating "research-only" as immunity.** A research output that *looks* like a clinical recommendation is still a clinical recommendation in effect. The boundary block helps a reviewer; it does not protect a reader who skim-reads. A reviewer should pressure-test the phrasing patterns, not just the disclaimer presence.

- **Underweighting NaN / edge-case failure modes because the headline metrics look good.** PRD ≤ 2.32% on MIT-BIH is a great number. It tells us almost nothing about what happens to a record with three NaN samples in lead V4, or a record with a 30-second amplifier-saturation flat patch. Real signal data has these.

## What I would not do (yet)

- Sign anyone up to a research collaboration outside the portfolio. The methodology is not yet reproducibly demonstrated on a single compound.
- Make any private storage public. The boundary block plus internal review should sit in front of any de-gating.
- Promise GPT-Rosalind value-add. Until access exists and a blind benchmark runs, the value-add is hypothesised, not measured.
- Expand to EEG / scalp neurophysiology. ZPE-Bio Sleep-EDF aggregate is empty; ZPE-Neuro is extracellular only. Either expansion would create an apparent capability that does not exist.
- Ingest credentialed clinical data (MIMIC-IV, MIMIC-IV-ECG, eICU) at this stage. The portfolio's research-only posture is much easier to maintain on open ECG corpora.
- Republish CredibleMeds risk lists. Cite-only.
