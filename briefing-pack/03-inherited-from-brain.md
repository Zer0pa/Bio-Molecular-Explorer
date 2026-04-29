# Inherited from the Brain (Phase 8)

This document summarises what the parent ("Brain") project decided in its Phase 8 selection-and-charter work, dated 2026-04-29. The Brain artifacts live at `/Users/Zer0pa/orchestration-state/.gpd/phases/08-rosalind-bioelectric-translational-engine/`. This portfolio inherits those artifacts as starting material.

Voice in this document: factual recall of what the Brain decided. Pressure-testing those decisions belongs in `04-current-thinking.md`.

## Brain's decision

Phase 8 in the Brain was a *selection* phase — its job was to decide which high-stakes healthcare problem the portfolio is uniquely placed to pursue. The decision:

- **Selected** — Rosalind Bioelectric Translational Engine (RBTE). First wedge: cardiac QT / ion-channel / drug-safety phenotype-to-mechanism research infrastructure.
- **Adjacent (second)** — epilepsy / extracellular-neurophysiology, contingent on the cardiac loop reproducibly working.
- **Not selected as first wedge** — generic cancer / drug-discovery, ICU deterioration, neurodegenerative digital biomarkers.

## Opportunity-matrix scoring

Five candidates were scored across seven axes (clinical stakes, Zer0pa fit, public data availability, life-science-LLM fit, falsifiability, no-Docker / low-footprint feasibility, regulatory-risk inverse). Two matrices were produced — internal (positive-axes-sum) and external (positive-axes-sum minus regulatory-risk). They agree on ranking.

| Candidate | Internal total | External decision score | Verdict |
| --- | ---: | ---: | --- |
| Cardiac QT / ion-channel / drug-safety | 31 | 25 | **Selected first** |
| Epilepsy / extracellular-neurophysiology | 28 | 18 | Adjacent second |
| Generic cancer / drug-discovery | 23 | 21 | Defer |
| ICU / critical-care deterioration | 22 | 16 | Defer |
| Neurodegenerative digital biomarkers | 22 | 16 | Defer |

The dominant tie-breaker for cardiac was *unique* fit: ZPE-Bio already has deterministic ECG replay / feature lineage on MIT-BIH / PTB-XL / NSTDB / EDB, and FDA E14 / S7B + CiPA define a concrete regulatory-science frame around QT / proarrhythmia. Cancer scored higher on life-science-LLM fit but lower on unique-asset fit; ICU scored lower on operational feasibility under no-credentialed-data constraints.

## Mechanism graph (seed) — 23 nodes, 12 edges

**Phenotype features (signal-side)**

| Node | Status | Description |
| --- | --- | --- |
| QT / QTc repolarization phenotype | planned | ECG repolarization features as bridge to ion-channel and drug-safety evidence |
| ST / T morphology phenotype | planned | ST and T-wave change features anchored to EDB metadata and PTB-XL label families |
| Noise-robust rhythm phenotype | planned | Arrhythmia / rhythm features that must survive calibrated NSTDB noise stress |
| Spike-event burst phenotype | secondary | Extracellular spike-event family for the later DANDI / IBL neurophysiology wedge |

**Genes / channels**

| Node | Status |
| --- | --- |
| KCNH2 / hERG (IKr) | source-grounded (FDA-linked CiPA material) |
| SCN5A / Nav1.5 (INa) | planned lookup |
| KCNQ1 / Kv7.1 (IKs) | planned lookup |

**Mechanism / assay framing**

- Multi-current ventricular repolarization balance — CiPA-style; torsade risk depends on the balance of inward and outward ion-channel currents, not hERG alone. *source-grounded.*
- CiPA multi-ion-channel assay / model family — research framework integrating multi-channel effects and in silico ventricular myocyte modelling. *source-grounded.*

**Drug class**

- QT-risk drug category — research category for compounds with known / possible / conditional torsade / QT-risk evidence. *source-grounded.* (No specific named compounds yet; this is a class node.)

**Evidence sources**

- ZPE-Bio proof surface (local).
- ZPE-Neuro proof surface (local).
- MIT-BIH, PTB-XL, NSTDB, EDB (public ECG datasets, PhysioNet).
- FDA E14 / S7B QT / QTc guidance (regulatory science).
- FDA-linked CiPA open-format material (regulatory science).
- DANDI / NWB neurophysiology archive and standard.

**Active falsifiers**

| Falsifier | Trigger |
| --- | --- |
| Codec metric does not imply mechanism | Any claim that compression ratio / event ratio / replay integrity alone proves disease mechanism. |
| Noise stress breaks phenotype | Rhythm / morphology claim that does not survive NSTDB-style calibrated noise. |
| hERG-only overreach | Simplistic hERG-only risk story when multi-current evidence or low-torsade hERG-blocker counter-examples exist. |
| Clinical overclaim | Output reads as diagnosis, treatment, cure, prescribing, clinical deployment, regulatory compliance, or drug-safety certification. |

**Edges of note**

- `ZPE-Bio supports QT / QTc phenotype as seed` (local proof summary, not full mechanism proof).
- `EDB supports ST / T morphology phenotype` (dataset is expert-annotated for ST / T changes).
- `NSTDB provides noise-stress falsifier` (calibrated noise with known beat annotations).
- `QT / QTc → KCNH2 / hERG` via FDA-linked CiPA material (hERG block → delayed repolarization → QT prolongation).
- `KCNH2 / hERG requires multi-current balance context` (CiPA notes torsade risk depends on multi-current balance).
- `ZPE-Bio is *falsified by* codec-not-mechanism` (local proof supports replay, not mechanism).

## Falsification ledger (seed) — 6 claims

Status taxonomy: SUPPORTED_FOR_RESEARCH, SUPPORTED_WITH_LIMIT, REJECTED_AS_FIRST_WEDGE, SUPPORTED_BY_ENVIRONMENT.

| ID | Claim | Status | Confidence | Falsifier |
| --- | --- | --- | --- | --- |
| rbte-claim-001 | First healthcare project should be cardiac QT / ion-channel / drug-safety, not generic drug discovery | SUPPORTED_FOR_RESEARCH | medium-high | ZPE-Bio cannot support a lightweight phenotype fingerprint, or all mechanism edges remain generic literature summaries |
| rbte-claim-002 | Deterministic ECG replay supports phenotype integrity but does not by itself prove cardiac disease mechanism | SUPPORTED_WITH_LIMIT | high | Any output treats compression ratio, event ratio, SNR, PRD, RMSE, or replay hash as sufficient biological mechanism evidence |
| rbte-claim-003 | hERG / KCNH2-only is insufficient for torsade-risk research; multi-current and context-dependent mechanisms required | SUPPORTED_FOR_RESEARCH | medium | Mechanism graph ranks hERG alone as definitive risk explanation without multi-channel or clinical-context caveats |
| rbte-claim-004 | Epilepsy / extracellular-neurophysiology should be the second wedge, not the first | SUPPORTED_WITH_LIMIT | medium | ZPE-Neuro adds a second independent neurophysiology task with stronger mechanism grounding than the cardiac wedge |
| rbte-claim-005 | Generic cancer / drug-discovery deferred — strong life-science-LLM fit, weak local proof fit | REJECTED_AS_FIRST_WEDGE | medium-high | A reproducible cancer / omics repo with verified target-prioritization or assay evidence enters the portfolio |
| rbte-claim-006 | First prototype must run as lightweight manifests / schemas without Docker or bulk local downloads | SUPPORTED_BY_ENVIRONMENT | high | Prototype requires Docker, broad cloning, or large raw-data mirroring before it can render or verify |

## Phenotype fingerprint schema (seed)

A JSON Schema for "RBTE Bioelectric Phenotype Fingerprint" exists, with restrictive constraints by design:

- **modality** enum: `ecg`, `eeg`, `extracellular_spike`, `mixed_bioelectric`.
- **source** object: must include dataset, record_id, source_url, local_artifact, and `bulk_data_local: false` (const) — bulk data is never local.
- **provenance** object: repo, commit / snapshot, proof anchor, codec / extractor.
- **feature_families** enum: `rhythm`, `st_t_morphology`, `qt_repolarization`, `conduction`, `noise_robustness`, `spike_event`, `burst_structure`, `spectral`.
- **value_status** enum: `measured`, `imported_from_proof`, `metadata_only`, `planned`.
- **biological_interpretation_status** enum: `source_grounded`, `inference`, `unverified`, `rejected`.
- **mechanism_hints** entity_type enum: `ion_channel`, `gene`, `drug_or_compound`, `assay`, `disease_or_phenotype`, `dataset`.
- **falsification_hooks** required (minItems 1); effect enum: `reject_feature`, `downgrade_hypothesis`, `force_replay`, `stop_clinical_claim`.
- **safety_boundary** const: the verbatim research-only string.

The schema *cannot* represent a phenotype without provenance, source URL, mechanism-interpretation status, and at least one falsification hook.

## Long-horizon roadmap (Brain's framing)

The Brain's PRD outlines six sub-phases for RBTE execution. The Brain has completed the first.

| Sub-phase | Status | Scope |
| --- | --- | --- |
| 8A — Product definition and graph seed | Done in Brain | PRD, opportunity matrix, mechanism graph seed, falsification ledger, phenotype schema |
| 8B — Lightweight public-data replay | Open | Small MIT-BIH proof slice; PTB-XL metadata schema; NSTDB robustness path; EDB ST / T metadata path; no bulk local download |
| 8C — Life-science evidence routing | Open | Entity normalization for KCNH2 / SCN5A / KCNQ1 / CACNA1C / named QT-risk drugs; routes for literature, PharmGKB, ChEMBL, PubChem, ClinVar-class evidence; source-grounded mechanism summaries |
| 8D — Knowledge-Brain integration | Open | RBTE section on the science-facing surface; mechanism graph as scientific structure; admin / process suppressed by default |
| 8E — HF portability | Open | Small private dataset for schemas, manifests, proof summaries; raw datasets external / offloaded |
| 8F — Rosalind upgrade | Access-gated | Replace mainline + plugin tasks with Rosalind-specific runs once access exists; record model / access state; compare Rosalind outputs to mainline outputs via the falsification ledger |

This portfolio takes 8B–8F as its execution corridor.

## Residual gaps Brain itself flagged

| Gap | What it means |
| --- | --- |
| GPT-Rosalind access not yet held | First execution must use mainline frontier models + Life Sciences Research Plugin pattern |
| Current-main ZPE-Bio replay not re-run | Strongest proof metrics are from a dated audit checkout, not a fresh-main reproduction |
| Morphology gap | Existing ZPE-Bio proof is replay / integrity-side, not QT / QRS / PR / ST / T morphology — needs a dedicated feature schema and benchmark |
| ZPE-Bio NaN silent failure | NaN inputs can produce silently incorrect reconstruction with PRD reported as 0.0 — hard blocker for any regulated posture; also distorts phenotype fingerprints if NaN inputs are not rejected upstream |
| Sleep-EDF aggregate is 0 entries | Failed download — *not* EEG validation evidence |
| Public root `.gpd/STATE.md` absent on `Zer0pa/ZPE-Bio` and `Zer0pa/ZPE-Neuro` | Phase-state continuity across repos relies on proof manifests and orchestration-state directory |
| Repo-count drift | `STATE.md` says 23 public repos; current `gh api` and website dashboard say 24 — recency artefact, not science |
