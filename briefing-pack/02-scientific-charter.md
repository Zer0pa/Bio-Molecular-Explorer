# Scientific Charter

## Authority question

> Can a research engine produce reproducible, source-grounded, falsifiable phenotype-to-mechanism reasoning loops in cardiac electrophysiology and drug safety that are uniquely better than a generic frontier-model-plus-literature-search?

This is the falsification metric. "Interesting" is not a passing grade. "Plausible" is not a passing grade. A passing grade requires:

- (a) a deterministic phenotype fingerprint with stated provenance,
- (b) a sourced mechanism bridge to a channel / gene / drug entity,
- (c) a stated falsifier for the bridge,
- (d) a result a generic LLM-plus-search workflow demonstrably could not produce alone.

Without (d), the engine has no value-add over PubMed and a competent reader.

## Selected first wedge

**Cardiac QT, ion-channel, and drug-safety phenotype-to-mechanism research infrastructure.**

Concrete entities the engine reasons over:

- **ECG morphology and rhythm features** — ventricular repolarization, QT / QTc, ST / T, conduction (PR, QRS), noise robustness.
- **Cardiac ion channels and their genes** — KCNH2 / hERG (IKr); SCN5A / Nav1.5 (INa); KCNQ1 / Kv7.1 (IKs); CACNA1C (ICa,L); KCNE1 / KCNE2 accessory subunits.
- **Multi-current ventricular repolarization balance** — CiPA-style framing: torsade risk depends on the *balance* of inward and outward currents, not hERG block alone.
- **QT-risk drug categories** — research-grade categories (known / possible / conditional) over named compounds with public mechanism evidence.
- **Public ECG corpora as phenotype anchors** — MIT-BIH, PTB-XL, NSTDB, EDB, plus PTB-XL+ for fiducial reference.
- **Regulatory-science reference frames** — FDA E14 / S7B QT / QTc guidance; CiPA ion-channel framework. *Cited, not certified against.*

## Adjacent (second) wedge

**Epilepsy and extracellular-neurophysiology phenotype-to-mechanism research infrastructure**, gated on the cardiac loop reproducibly working first. Anchors: DANDI (e.g., dataset 000034), IBL waveform corpus, NWB data standard.

Important methodological constraint: ZPE-Neuro currently proves *bounded extracellular spike-event* extraction. It does not prove EEG, scalp-recording analysis, seizure prediction, or any clinical-neurophysiology-grade output. The epilepsy wedge therefore opens with neurophysiology research (channels, microcircuit mechanism, animal-model data), not clinical seizure work.

## Wedges deferred (and why)

- **Generic cancer / drug-discovery.** Strong fit for life-science LLM tooling, weak unique signal / proof anchor in the current portfolio. Reopens if a reproducible cancer / omics proof anchor enters the portfolio — not before.
- **ICU / critical-care deterioration.** Needs credentialed multi-modal data (MIMIC-IV, eICU); local proof base is missing; credentialed-data and operational constraints make it heavy. Defer.
- **Neurodegenerative digital biomarkers.** Attractive grant theme; lacks bounded disease-specific cohort and validated phenotype-extraction task in the current portfolio. Defer; revisit after a validated electrophysiology safety engine exists.

## Why now

- **GPT-Rosalind** (announced 2026-04-16) is purpose-built for life-science reasoning: hypothesis generation, experimental planning, multi-step evidence synthesis, sequence-to-function interpretation, chemistry, protein engineering, genomics.
- **OpenAI Life Sciences Research Plugin** offers ~50 modular skills: ClinVar, gnomAD, Ensembl, Open Targets, GWAS Catalog, AlphaFold, UniProt, STRING, Reactome, BindingDB, ChEMBL, PubChem, PharmGKB, ClinicalTrials.gov, cBioPortal, CIViC, NCBI / PMC, bioRxiv, ArrayExpress / BioStudies, BLAST, PRIDE, ProteomeXchange, MetaboLights, MGnify.
- **Access reality.** GPT-Rosalind is a research preview for eligible US Enterprise customers with legitimate biology research use cases; not generally available to individual researchers; not for customer-facing or external commercial applications during preview. Plan accordingly: design routes that work today on mainline frontier model + plugin pattern, and are Rosalind-upgradeable later. Treat Rosalind as an upgrade path, not a blocker.

## Why this portfolio (not just any biology lab)

The unique fit is the *intersection*:

| Capability | Where it usually lives | Where this portfolio holds it |
| --- | --- | --- |
| Deterministic bioelectric replay / feature lineage | Signal-processing teams, embedded-firmware groups | ZPE-Bio (ECG), ZPE-Neuro (extracellular spike) |
| Cross-evidence biological reasoning over genes / drugs / pathways / literature | Computational biology labs | GPT-Rosalind / Life Sciences Research Plugin |

Neither alone is rare. The combination — deterministic phenotype → mechanism bridge → falsifier → research output — is rare and is what the engine is for.

## Authority metric, restated

A research output passes if it shows source-grounded mechanism reasoning bridged to deterministic phenotype evidence with a stated falsifier and a research-only boundary, and a generic LLM-plus-search workflow could not have produced it.

It fails if any of:

- the mechanism bridge is generic literature paraphrase,
- the phenotype evidence is missing or unverified,
- no falsifier is attached,
- the output reads as a clinical or regulatory claim,
- the result is reproducible by mainline + PubMed alone (no value-add).
