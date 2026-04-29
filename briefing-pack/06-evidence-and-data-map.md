# Evidence and Data Map

Concrete sources the engine cites or will cite. Use this when assessing whether the inherited mechanism graph is grounded enough to defend.

## Public ECG datasets (cardiac wedge)

| Dataset | What it provides | First-pass use | Source |
| --- | --- | --- | --- |
| MIT-BIH Arrhythmia Database | 48 half-hour 2-channel ambulatory ECG records, beat-level annotations | Lightweight phenotype anchor; first replay slice | https://physionet.org/content/mitdb/1.0.0/ |
| PTB-XL | 21,837 clinical 12-lead ECGs, 18,885 patients, cardiologist statements | Breadth anchor for morphology benchmark; metadata-first, no bulk local | https://physionet.org/content/ptb-xl/1.0.0/ |
| PTB-XL+ | Median beats, fiducial points, ECG feature sets, diagnostic statement metadata | Ground-truth QT / QRS / PR fiducial reference for the preservation benchmark | https://physionet.org/content/ptb-xl-plus/ |
| MIT-BIH Noise Stress (NSTDB) | Calibrated noise injected into MIT-BIH records with preserved annotations | Falsifier — phenotype must survive calibrated noise | https://physionet.org/content/nstdb/1.0.0/ |
| European ST-T Database (EDB) | Two-hour ECG records expert-annotated for ST and T-wave changes; medication and electrolyte metadata | ST / T morphology anchor and clinical-context bridge | https://physionet.org/content/edb/1.0.0/ |
| MIMIC-IV-ECG | Diagnostic ECG waveforms + cardiologist reports matched to MIMIC-IV records | **Defer** — credentialed access; outside no-credentialed-data posture | https://physionet.org/content/mimic-iv-ecg/1.0/ |
| WFDB | Open standards and software for physiologic signals / annotations | Toolchain reference | https://wfdb.io/ |

**Operational rule** — metadata and small slices first; no bulk archive download to local Mac. Bulk artifacts go to private off-machine storage when offload is needed.

## Public extracellular neurophysiology (adjacent / second wedge)

| Source | What it provides | Use |
| --- | --- | --- |
| DANDI Archive (e.g., dataset 000034) | Open neurophysiology archive, NWB-formatted | Second-wedge primary anchor, gated on cardiac loop closure |
| IBL Brain-Wide Map / waveform corpus | Bounded extracellular waveform evidence | ZPE-Neuro's existing second-target validation |
| NWB Standard | Neurophysiology data representation standard | Format constraint and proof-replay surface |
| TUH EEG / TUSZ; CHB-MIT EEG | Clinical EEG and seizure corpora | **Not in current scope** — ZPE-Neuro is extracellular, not EEG. Listed for awareness only. |

## Regulatory-science anchors (cited, not certified against)

| Anchor | What it frames | Source |
| --- | --- | --- |
| FDA E14 / S7B Q&A | Clinical and nonclinical evaluation of QT / QTc interval prolongation and proarrhythmic potential | https://www.fda.gov/regulatory-information/search-fda-guidance-documents/e14-and-s7b-clinical-and-nonclinical-evaluation-qtqtc-interval-prolongation-and-proarrhythmic |
| FDA CiPA regulatory-science action — multi-ion-channel assay reasoning | Mechanistic, model-informed cardiac safety framework around multi-current effects | https://www.fda.gov/drugs/regulatory-science-action/streamlining-analysis-ion-channel-in-vitro-assays-data-support-clinical-cardiac-safety-decision-making |
| FDA CiPA impact story | Notes hERG / QT signals alone can be overbroad; multi-current context required | https://www.fda.gov/drugs/regulatory-science-action/impact-story-improved-assessment-cardiotoxic-risk-drug-candidates-comprehensive-in-vitro-proarrhythmia |
| FDA AI / SaMD landing page | Current AI / ML medical-device framework — used to *avoid* drift into CDS | https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-software-medical-device |
| FDA CDS FAQ | Defines clinical-decision-support boundary — used to *avoid* drift into CDS | https://www.fda.gov/medical-devices/software-medical-device-samd/clinical-decision-support-software-frequently-asked-questions-faqs |
| FDA Digital Health Technologies guidance | Remote data acquisition in clinical investigations | https://www.fda.gov/regulatory-information/search-fda-guidance-documents/digital-health-technologies-remote-data-acquisition-clinical-investigations |

The portfolio cites these as research-context anchors. It does not claim alignment, certification, or compliance.

## Tooling anchors (life-science research-agent layer)

| Tool / Surface | Role | Source |
| --- | --- | --- |
| OpenAI GPT-Rosalind (research preview) | Life-science reasoning model — access-gated; upgrade path | https://openai.com/index/introducing-gpt-rosalind/ |
| OpenAI GPT-Rosalind Help Center | Operational access constraints (US Enterprise; not customer-facing) | https://help.openai.com/en/articles/20001193-introducing-gpt-rosalind-for-life-sciences-research |
| OpenAI Life Sciences Research Plugin | ~50 modular life-science skills | https://github.com/openai/plugins/tree/main/plugins/life-science-research |

Available life-science routes via plugin: ClinVar, gnomAD, Ensembl, Open Targets, GWAS Catalog, AlphaFold, UniProt, STRING, Reactome, BindingDB, ChEMBL, PubChem, PharmGKB, ClinicalTrials.gov, cBioPortal, CIViC, NCBI Entrez / PMC, bioRxiv, ArrayExpress / BioStudies, BLAST, PRIDE, ProteomeXchange, MetaboLights, MGnify.

## Local proof anchors (Zer0pa-internal)

| Anchor | What it proves | Path / public location |
| --- | --- | --- |
| ZPE-Bio website claim surface | Deterministic ECG round-trip fidelity across MIT-BIH, PTB-XL, EDB, NSTDB; Python + Rust + embedded reference | `/Users/Zer0pa/Website/product-pages-uplift/data/ZPE-Bio.md` |
| ZPE-Bio public proof files | `validation/results/BENCHMARK_SUMMARY.md`, `validation/results/ptbxl/summary.json` | `Zer0pa/ZPE-Bio` GitHub main |
| MIT-BIH replay summary (audit checkout) | 48 / 48 records pass; mean PRD ~2.32 %; mean SNR ~43.3 dB | `/Users/Zer0pa/.codex-license-audit-20260422/p0/ZPE-Bio/validation/results/mitdb_python_only/mitdb_aggregate.json` |
| PTB-XL replay summary (audit checkout) | 100 / 100 entries; mean SNR ~32.0 dB; max PRD ~5.29 % | `validation/results/ptbxl/summary.json` |
| EDB replay summary (audit checkout) | 90 / 90 entries; mean SNR ~52.5 dB; max PRD ~4.34 % | `validation/results/edb/summary.json` |
| NSTDB replay summary (audit checkout) | 15 / 15 entries; mean SNR ~60.5 dB; max PRD ~1.96 % | `validation/results/nstdb/summary.json` |
| Sleep-EDF aggregate (audit checkout) | 0 entries — download failed; **not** EEG validation | `validation/results/sleep-edfx/summary.json` |
| ZPE-Neuro current authority manifest | Routes authority to 2026-03-21 release-alignment + IBL-refinement packets | `Zer0pa/ZPE-Neuro` `proofs/manifests/CURRENT_AUTHORITY_PACKET.md` |
| ZPE-Neuro DANDI 000034 evaluation | CR ~401×; 41 events; RMSE ~78.4 µV; NWB roundtrip bit-consistent | `proofs/selected_artifacts/2026-03-21_zpe_neuro_ibl_refinement/public_corpus_eval_dandi_000034_mouse412804_ecephys.json` |
| ZPE-Neuro IBL bounded second target | CR ~224×; 110 events; RMSE ~38.2 µV; NWB roundtrip bit-consistent | `public_corpus_ibl_waveform_eval.json` |

**Recency caveat** — the four ZPE-Bio replay summaries above were read from a dated audit checkout on 2026-04-22. Current `Zer0pa/ZPE-Bio` main is license-refresh-only as of 2026-04-29 commit `30c3ca99`; values likely match but are not freshly re-asserted on current main.

## Brain Phase 8 artifacts (the seed inputs)

All at `/Users/Zer0pa/orchestration-state/.gpd/phases/08-rosalind-bioelectric-translational-engine/`.

| Artifact | Role |
| --- | --- |
| `08-PRD.md` | Full product requirements document |
| `08-PLAN.md` | Executable plan; 8A done, 8B–8F open |
| `08-RESEARCH.md` | Selection narrative |
| `08-EXTERNAL-RESEARCH.md` | External research lane (GPT-Rosalind, candidate scoring, regulatory anchors) |
| `08-ZER0PA-CAPABILITY-MAP.md` | Local-evidence capability lane (independent of external research lane) |
| `08-OPPORTUNITY-MATRIX.json` | Five-candidate scored matrix |
| `rbte-phenotype-schema.json` | JSON Schema for phenotype fingerprints |
| `rbte-mechanism-graph.json` | 23-node, 12-edge seed graph |
| `rbte-falsification-ledger.json` | 6-claim ledger with active falsifiers |
| `08-VERIFICATION.md` | Verification report (JSON parse, source grounding, low-footprint, no-clinical-claim) |
| `08-SUMMARY.md` | One-page summary |

## Acknowledged gaps in the evidence base

These should be in the citation stack but are not yet integrated:

- **A current open Q-T fiducial reference extractor** — PTB-XL+ tables, or an open ECG-feature library (NeuroKit2 / ECGdeli / Wavedom) — needed to anchor the morphology benchmark.
- **A specific named-compound multi-current evidence corpus** — BindingDB / ChEMBL queried for the 3–5 chosen compounds — needed to populate the first cardiac evidence packets.
- **A current open CiPA in-silico model reference** — O'Hara-Rudy or ToR-ORd, ideally a current variant — needed if the engine is to compare predicted phenotype changes to a model.
- **An open channelopathy variant evidence layer** — ClinVar query against KCNH2 / SCN5A / KCNQ1 / CACNA1C — needed to make the gene-to-channel-to-phenotype path source-grounded rather than planned-lookup.
- **A peer-review-grade reviewer** — cardiac-safety scientist or electrophysiologist — for the boundary-and-overclaim check.

## NOT in scope (and why)

| Source | Why excluded |
| --- | --- |
| MIMIC-IV (general ICU) | Credentialed; outside no-credentialed-data posture |
| eICU-CRD | Same |
| MIMIC-IV-ECG | Same — even though ECG-specific |
| TCGA, DepMap, cBioPortal | Cancer wedge deferred; reopen if cancer becomes a wedge |
| ADNI, PPMI | Neurodegenerative wedge deferred |
| TUH EEG, CHB-MIT EEG | EEG not in scope; ZPE-Neuro is extracellular only |
| CredibleMeds full lists (republished) | License — cite-only framework |
