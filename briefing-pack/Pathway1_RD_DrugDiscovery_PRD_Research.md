# Pathway 1: R&D / Drug Discovery — PRD Research Document
**From: Zer0pa Research Layer | Architect Prime**
**Date: April 30, 2026**
**To: Agent PRD Writer → Execute**
**Classification: PRD Input — Pre-Build Research**

---

## 0. Document Purpose & Conventions

This document follows the same standards established for the Energy/Materials/Process pipelines in this thread. It is not a PRD itself — it is the research foundation from which an agent will write a PRD and begin execution.

**The five-layer pipeline covered:**
1. **Target Identification** — biological target discovery from genomic/literature/pathway data
2. **Molecule Generation** — generative design of candidate molecules
3. **In Silico Screening** — computational efficacy, toxicity, ADMET, binding affinity filtering
4. **Hit-to-Lead Refinement** — iterative ML-driven optimization
5. **Handoff Layer** — ranked candidate output format, CRO integration standards

**Licensing classes used throughout:**
- **Class A** — Permissive open source (MIT, Apache 2.0, BSD). Outputs freely commercializable.
- **Class B** — Copyleft (GPL, LGPL, CC BY-SA). Tool is restricted; computational **outputs** (molecules, predictions, ranked lists) are yours.
- **Class C** — Restricted/API-only or research-preview (free to use, but commercial deployment requires licensing). Do not embed; call via API.
- **Class D** — Non-commercial only (AlphaFold 3 weights, AlphaFold DB). Academic/research use; use Class A alternatives for production.
- **Class E** — Proprietary/commercial (Schrödinger, MOE, Glide, FEP+). Avoid for core pipeline; acceptable as benchmark comparison.

**The information token** for this pipeline changes across stages:

| Stage | Token | Format |
|-------|-------|--------|
| L1 Target ID | `{target_id, disease_id, confidence_score, evidence_type}` | JSON/TSV, HGNC/UniProt identifiers |
| L2 Structure | `{3D_pocket_coords, binding_site_residues, confidence_pLDDT}` | mmCIF / PDB format |
| L3 Generation | `{SMILES, 3D_conformation, generation_method}` | SMILES string + SDF file |
| L4 Screening | `{binding_affinity_pIC50, ADMET_profile_vector, selectivity_flag}` | CSV / JSON |
| L5 Handoff | `{ranked_candidate_list, synthesis_score, confidence_tier}` | CSV / structured JSON for CRO |

---

## 1. Business Context & Positioning

### What Is Being Sold

Speed and intelligence — compressing target-to-candidate from 3–5 years to weeks. Zer0pa is not a pharma company. It is a **research orchestration engine**: an AI-native layer that takes a target and returns ranked, validated candidates ready for wet-lab synthesis and testing.

Revenue models (based on landscape analysis):
- **Research partnership**: milestone + equity stake in candidate molecules
- **Technology licensing**: charge per candidate delivered or per screening run
- **Platform API**: biotech/pharma pays for pipeline-as-a-service
- **Co-discovery**: shared IP on candidates, royalty on downstream drug approval

### Competitive Landscape Reference

| Company | Core Technology | Status | Differentiator |
|---------|----------------|--------|----------------|
| Recursion + Exscientia (merged) | Full-stack platform, biological imaging + chemistry AI | ~$500M+ invested; 5 clinical assets | Most complete platform; closed-source |
| Insilico Medicine | Pharma.AI (Biology42 + Chemistry42) | Clinical-stage AI-native | First AI-designed drug in Phase II trial |
| Isomorphic Labs (DeepMind spin-out) | AlphaFold 3 + rational drug design | Private; partnered with Eli Lilly, Novartis | DeepMind pedigree, protein structure advantage |
| Atomwise | Structure-based deep learning | Series C | ADMET-focused screening at scale |
| AbSci | Generative biology for antibodies | Nasdaq-listed | Antibody-specific generative design |

**Zer0pa's unique angle**: domain-agnostic physics-computation philosophy + intersectional science lens. Not optimized for one therapeutic modality. Builds on the same orchestration infrastructure as the Materials and Energy pipelines. The moat is architectural breadth, not therapeutic depth.

---

## 2. Stage 1 — Target Identification

### What Happens

Agents scan genomic databases, disease pathway databases, biomedical literature, and GWAS data to identify a protein, gene, or receptor that is causally implicated in a disease and is druggable (accessible to a small molecule or biologic).

### Best-of-Breed Tool Stack

| Tool | License | Function | Why This Pick |
|------|---------|----------|---------------|
| **Open Targets Platform 25.06** | Class A (Apache 2.0) | Systematic target–disease association scoring; integrates genetic, expression, somatic mutation, drug, and clinical data | Released April 2025; 40K+ monthly users; most complete open target scoring system; Python API via `opentargets-py` |
| **Therapeutic Target Database (TTD) 2026** | Class A (CC BY) | 306,247 target–disease associations; 2,912 targets; 10,506 perturbation profiles | January 2026 update; most up-to-date curated disease-target evidence source |
| **STRING v12** | Class B (CC BY) | Protein–protein interaction network; 68M+ proteins; 35B+ interactions | Network topology reveals non-obvious targets via graph traversal |
| **GATher** | Class A (arXiv / research) | Graph attention network (GATv3) for gene-disease link prediction from 4.4M+ edge heterogeneous graph | Novel target nomination from graph-structured evidence; 2024 paper; code available |
| **cBioPortal** | Class A (LGPL) | Interactive somatic mutation / copy number / expression visualization; 500+ studies, 35K samples | Somatic mutation evidence for oncology targets; includes LLM natural language query interface (2025) |
| **Ensembl / GENCODE** | Class A (open) | Human genome annotation; exon/transcript-level target mapping | Required reference for variant-to-gene mapping |
| **PubTator 3.0** | Class A (NLM) | Biomedical NER over PubMed; F1 > 0.90 for gene/disease/chemical entity recognition | Best open-source biomedical NER; outperforms BioBERT on gene and drug extraction |
| **BioBERT / BioGPT** | Class A (MIT) | Transformer LM fine-tuned on PubMed; relation extraction, drug-target mention detection | BioBERT for entity extraction; BioGPT for hypothesis generation from literature |
| **GPT-Rosalind (OpenAI, April 2026)** | Class C (API, research preview) | Frontier reasoning model for biology; multi-step reasoning across chemistry, genomics, protein engineering; BixBench top score; RNA sequence prediction above 95th percentile of human experts | **Do not embed — call via API.** Best-in-class for open-domain hypothesis synthesis, literature review, and experiment planning. Integrates 50+ scientific databases via Life Sciences Codex plugin. |

### Key Databases for Target Identification

| Database | Content | Access | Class |
|----------|---------|--------|-------|
| **UniProt/Swiss-Prot** | 570K+ manually curated protein entries; sequence + function | REST API, bulk download | A |
| **OMIM (Online Mendelian Inheritance in Man)** | Disease-gene causal associations | Free for research | A (research), C (commercial redistribution) |
| **GWAS Catalog** | 6,000+ genome-wide association studies, SNP-trait associations | EBI API, download | A |
| **GTEx v10** | Tissue-specific gene expression; eQTL mapping | NIH, bulk download | A (public domain) |
| **TCGA (PanCancer Atlas)** | Multi-omic cancer data; 11,000+ samples; via cBioPortal | NIH, open access | A |
| **CCLE (Cancer Cell Line Encyclopedia)** | Drug sensitivity + genomics; 1000+ cell lines | Broad Institute, free | A |
| **OpenTargets Genetics** | GWAS colocalization + gene prioritization | API + download | A |
| **Human Protein Atlas** | Protein expression in tissues and cell types | CC BY-SA | B |

### Architecture: Target Identification Agent

```
[PubMed / bioRxiv feed] → [PubTator 3.0 NER] → [Entity graph: gene-disease-compound]
                                                         ↓
[Open Targets API]  ─────────────────────────→ [Association scoring + evidence integration]
[TTD 2026 API]       ─────────────────────────→
[GWAS Catalog API]   ─────────────────────────→
                                                         ↓
                                             [GATher / STRING network expansion]
                                                         ↓
                                             [GPT-Rosalind hypothesis synthesis]
                                                         ↓
                                    [Ranked target list: {UniProt_ID, disease_IDs,
                                     genetic_evidence_score, druggability_score,
                                     novelty_flag}]
```

---

## 2. Stage 2 — Protein Structure Prediction (Enabling Layer)

This is not one of the five named stages but is the essential substrate that makes Stages 3 and 4 possible. A 3D binding pocket structure is required for structure-based drug design.

### Best-of-Breed Tool Stack

| Tool | License | Performance | Why This Pick |
|------|---------|-------------|---------------|
| **OpenFold3** | Class A (Apache 2.0) | Matches AlphaFold 3 performance; supports protein + RNA + DNA + small molecule co-folding | Released Feb 2026 by OpenFold Consortium (SandboxAQ lead contributor). `pip install openfold3`. Only AF3-class co-folding model under fully permissive commercial license. |
| **Boltz-2** | Class A (MIT, MIT/Recursion) | Joint structure **and binding affinity** prediction; 1,000× faster than FEP; first AI model approaching FEP accuracy on CASP16 affinity sub-track | June 2025 release. The most significant structural model release in 2025. Replaces the need for separate docking + FEP at early screening stage. |
| **ESM3 (open weights, 300M params)** | Class A (EvolutionaryScale open-v1) | Multimodal protein LM: sequence + structure + function. Trained on 2.78B proteins, 771B tokens | For protein representation and novel protein generation. Larger models (98B) via Forge API (Class C). |
| **ESM2 (various scales)** | Class A (Meta, MIT) | Best protein LM for sequence-to-function tasks in cold-split settings | Use when structure is not needed; fast sequence embeddings for screening |
| **RFdiffusion3** | Open (Baker Lab, commercial-permissive) | 10× faster than RFdiffusion2; atom-level diffusion; protein-protein + protein-small molecule + protein-DNA binding design | Dec 2025 release. Best for de novo binder design for a target pocket. |
| **ProteinMPNN / LigandMPNN** | Class A (Baker Lab, MIT) | Sequence design given backbone. LigandMPNN extends to non-protein atomic context (small molecules, DNA). | Required second step after RFdiffusion3 for sequence design. LigandMPNN for drug-context design. |
| **AlphaFold DB** | Class D (non-commercial) | 200M+ pre-computed structures | Use for research and reference; **do not use pre-computed structures in commercial pipeline**. Recompute with OpenFold3 for production. |

### Note on AlphaFold 3

AlphaFold 3 (DeepMind) model weights are non-commercial only (Class D). However, **OpenFold3 (Apache 2.0)** is a fully open reimplementation that matches AF3 performance and supports the same input types (protein + RNA + DNA + ligand co-folding). This is the production pick.

---

## 3. Stage 3 — Molecule Generation

### What Happens

Given a validated target and its 3D binding pocket structure, generate thousands of candidate small molecules or protein binders that are predicted to bind with high affinity and selectivity.

### Sub-modes

1. **De novo small molecule generation** — generate from scratch, no starting scaffold
2. **Structure-based drug design (SBDD)** — generate molecules conditioned on 3D pocket
3. **Scaffold hopping / R-group replacement** — optimize around a known chemotype
4. **Protein binder design** — generate protein or peptide therapeutics that bind a target
5. **Fragment-based design** — generate from fragment hits, link and grow

### Best-of-Breed Tool Stack

| Tool | License | Mode | Benchmark | Why This Pick |
|------|---------|------|-----------|---------------|
| **REINVENT 4** | Class A (Apache 2.0, AstraZeneca) | De novo, scaffold hop, R-group, linker, optimization | Production-tested at AstraZeneca; best open-source small molecule generator | RL + curriculum learning in one codebase; SMILES-based; plug-in scoring via `REINVENT4` plugin API |
| **DiffSBDD** | Class A (research, MIT-style) | SBDD — 3D conditional ligand generation given protein pocket | SE(3)-equivariant 3D diffusion; Nature Computational Science 2024 | Geometric equivariance is the correct physical inductive bias for pocket-conditioned generation; directly embodies Zer0pa's geometric unity principle |
| **RFdiffusion3** | Open (Baker Lab, commercial) | Protein binder design | 10× RFdiffusion2; atom-level; handles small molecule context | For therapeutic protein/peptide design against a target |
| **RFpeptides** | Open (Baker Lab) | Macrocyclic peptide design | Generates cyclic peptides binding target using only structure/sequence | Cyclic peptides are an increasingly valuable modality — higher stability, better penetration than linear peptides |
| **NVIDIA BioNeMo Framework** | Class A (Apache 2.0) | All modalities via pre-trained model fine-tuning | NVIDIA-GPU-optimized; contains protein LMs, small molecule generators, SMILES LMs | Training framework for custom generative models on domain data |
| **NVIDIA BioNeMo NIM (Generative Protein Binder Blueprint)** | Class C (NVIDIA API) | Protein binder design | Production blueprint January 2025 | Call as microservice; do not embed weights |
| **nach0** | Class A (research, open) | Multi-task encoder-decoder: molecule generation + synthesis + attribute prediction + biomedical QA | Combines chemical and biological language modalities in one model | First true multi-domain chemical+biological foundation model; relevant for cross-modal generation |

### Molecule Generation Design Principles

**The correct physical framing (from Zer0pa philosophy):**
- A drug-target interaction is a **geometric binding problem** — the molecule must fit the 3D electrostatic/steric landscape of the binding pocket
- This is isomorphic to the **shape-matching problems** in materials science (crystal structure) and physics (field-matter coupling)
- SE(3)-equivariant diffusion models (DiffSBDD, Boltz-2) are the correct architecture because they respect the physical symmetries of 3D space
- REINVENT 4's RL framing maps to Zer0pa's biocomputation/cellular-automata feedback loop: reward signal from the environment (predicted ADMET/affinity scores) drives policy improvement

---

## 4. Stage 4 — In Silico Screening

### What Happens

Filter the generated molecule library (~10K–100K candidates) down to a tractable set of ~100–500 "hits" by predicting: (a) binding affinity to target, (b) ADMET properties (absorption, distribution, metabolism, excretion, toxicity), (c) selectivity (no off-target binding), and (d) synthetic accessibility.

### Sub-task A: Binding Affinity Prediction

| Tool | License | Method | Performance | Use Case |
|------|---------|--------|-------------|----------|
| **Boltz-2** | Class A (MIT) | Joint structure + affinity (deep learning) | FEP-level accuracy at 1,000× speed; best CASP16 affinity sub-track | **Primary affinity screen** — replaces docking+FEP at early stage |
| **GNINA 1.3** | Class A (Apache 2.0) | Deep learning-augmented docking; CNN scoring; PyTorch backend (updated Feb 2025) | Outperforms AutoDock Vina in binding pose and affinity accuracy | Structure-based rescoring after initial pose generation |
| **AutoDock Vina 1.2** | Class A (Apache 2.0) | Classical force-field docking | Industry standard; fast; lower accuracy than GNINA | Ultra-large library screening (ZINC-22 scale) for fast pre-filter |
| **Uni-Mol v2** | Class A (MIT, DeepModeling) | 3D molecular representation; SE(3) transformer; pretrained on 209M conformations | SOTA on 14/15 MoleculeNet tasks; protein-ligand binding pose prediction | Molecular property embedding backbone; integrates into downstream models |

### Sub-task B: ADMET Property Prediction

| Tool | License | Coverage | Performance | Use Case |
|------|---------|----------|-------------|----------|
| **Chemprop v2** | Class A (MIT, MIT/CMU) | Any molecular property via D-MPNN; transfer learning; uncertainty quantification | 2× faster than v1; 3× less memory; SOTA on multiple MoleculeNet tasks | **Primary property prediction engine** — train custom ADMET models on proprietary assay data |
| **ADMETlab 3.0** | Class C (web server; research free, commercial requires license) | 21 physicochemical + 34 ADME + 36 toxicity endpoints; DMPNN-based | Best comprehensive ADMET coverage in one system | Use for research/validation; not for embedded production pipeline |
| **TDC ADMET Benchmark Group** | Class A (MIT) | 13 standardized ADMET classification tasks; leaderboard; splits | Standardized evaluation framework | **Use as benchmark and training data source, not a prediction tool** |
| **QW-MTL (Quantum-enhanced Multi-Task)** | Class A (research) | Joint training across all 13 TDC ADMET tasks; quantum chemical descriptors + learnable task weighting | SOTA on 12/13 TDC tasks (2025); combines quantum descriptors with deep learning | Physics-informed ADMET — aligns with Zer0pa's quantum/physics-first philosophy |
| **RDKit** | Class A (BSD) | 200+ molecular descriptors; fingerprints; Lipinski filters; synthetic accessibility score | Industry standard cheminformatics; fast; Python API | Pre-filter and feature generation layer upstream of all ML models |

### Sub-task C: Selectivity / Off-Target Screening

| Tool | License | Coverage | Use Case |
|------|---------|----------|----------|
| **CHEMBL 36 + Chemprop** | Class A (ChEMBL CC BY-SA / Chemprop MIT) | Activity data for 15,000+ protein targets | Train selectivity models; screen against off-target panel |
| **Guide to Pharmacology (GtoPdb) 2024** | Class A (CC BY-SA) | 3,039 protein targets; 12,163 ligands; expert-curated | Known selectivity profiles and pharmacology reference |
| **Kinase panel models** | Class A (research) | Kinase-specific ADMET + selectivity; ESM-2-based missense mutation ATP affinity | Required for any kinase program |

### Sub-task D: Synthetic Accessibility

| Tool | License | Function |
|------|---------|----------|
| **RDKit SA Score** | Class A (BSD) | Synthetic accessibility score 1–10; fast; embedded in REINVENT 4 |
| **ASKCOS (MIT)** | Class A (MIT) | Retrosynthetic planning; reaction prediction; route scoring |
| **SynRoute / AiZynth (AstraZeneca open)** | Class A / B | Retrosynthesis; integrated into REINVENT 4 scoring |

### Screening Architecture

```
[Generated molecule library: 10K–100K SMILES]
         ↓
[RDKit pre-filter: MW, logP, TPSA, SA score, Lipinski/Veber rules]
         ↓
[Boltz-2 affinity screen: predicted pIC50 vs. target]
         ↓
[GNINA 1.3 pose refinement: top 5K by affinity]
         ↓
[Chemprop v2 ADMET panel: absorption, BBB, CYP, hERG, hepatotox]
         ↓
[Selectivity screen: Chemprop against ChEMBL off-target panel]
         ↓
[ASKCOS synthesizability filter: estimated step count + route availability]
         ↓
[Output: 100–500 ranked hits with multi-parameter score]
```

---

## 5. Stage 5 — Hit-to-Lead Refinement

### What Happens

The top hits from screening undergo iterative optimization. An agent designs new analogues of the hits, predicts their properties, selects the best, and repeats — a design-predict-optimize loop. This continues until a candidate meets the target product profile (TPP).

### Design Philosophy (Zer0pa-specific framing)

This stage maps directly to **reinforcement learning / active learning** — the same framework used in the battery optimization loop (PyBaMM + PyBOP) and the materials active learning loop (BoTorch). The agent is the policy; the scoring function is the reward; the chemical space is the environment.

The information-theoretic framing: each iteration maximally reduces uncertainty about the optimal candidate, guided by the mutual information between molecular structure and the property profile.

### Best-of-Breed Tool Stack

| Tool | License | Role |
|------|---------|------|
| **REINVENT 4** | Class A (Apache 2.0) | Core RL optimization engine; multi-objective scoring; scaffold decoration, R-group replacement, molecule optimization modes |
| **BoTorch + Ax** | Class A (MIT, Meta) | Bayesian optimization; multi-objective Pareto frontier; Gaussian process surrogate models; same stack as Energy/Materials verticals |
| **Chemprop v2** | Class A (MIT) | Property prediction oracle for the optimization loop; custom-trained on project-specific assay data |
| **Boltz-2** | Class A (MIT) | Affinity oracle within the optimization loop; updated pose prediction per new candidate |
| **ASKCOS** | Class A (MIT) | Retrosynthesis oracle; filters candidates by synthetic feasibility |
| **LigandMPNN** | Class A (Baker Lab) | For peptide/protein binder optimization: redesign binding residues conditioned on small-molecule context |

### Optimization Loop Architecture

```
[REINVENT 4 generator: produce N new analogues per iteration]
         ↓
[Chemprop v2: predict ADMET panel (fast, <100ms/molecule)]
         ↓
[Boltz-2: predict binding affinity (medium, ~1s/molecule)]
         ↓
[BoTorch/Ax: update surrogate model; compute EI/EHVI acquisition]
         ↓
[Select top-K candidates for next generation]
         ↓
[Repeat 50–200 iterations]
         ↓
[Output: top 10–50 optimized leads]
```

**Loop convergence metric**: multi-parameter optimization score combining:
- Predicted pIC50 ≥ target (e.g., 7.0)
- QED (drug-likeness) ≥ 0.6
- SA score ≤ 4.0
- hERG inhibition IC50 > 30 µM (safety threshold)
- Solubility (ESOL predicted) ≥ target

---

## 6. Stage 6 — Handoff Layer (CRO Integration)

### What the Pipeline Delivers

A structured candidate dossier per molecule, machine-readable and human-interpretable:

```json
{
  "candidate_id": "ZP-0042",
  "smiles": "Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc1nccc(-c2cnnc(N)c2)n1",
  "target": "UniProt:P00533 (EGFR)",
  "predicted_pIC50": 8.2,
  "binding_affinity_source": "Boltz-2",
  "admet": {
    "BBB_penetration": 0.82,
    "hERG_IC50_uM": ">30",
    "hepatotoxicity": "low",
    "oral_bioavailability": 0.71
  },
  "selectivity_score": 0.89,
  "synthetic_accessibility": 2.8,
  "estimated_synthesis_steps": 4,
  "suggested_route": "Buchwald-Hartwig + amide coupling",
  "confidence_tier": "A",
  "generation_method": "REINVENT4_RL + DiffSBDD",
  "iteration_number": 127,
  "parent_scaffold": "imatinib-derived"
}
```

### CRO Handoff Standards

| Standard | Requirement | Tool |
|----------|------------|------|
| Structure format | SDF file + SMILES string | RDKit |
| Synthesis route | ASKCOS multi-step route with reaction SMARTS | ASKCOS |
| Confidence tier | A (confirmed by ≥3 independent models), B (2 models), C (1 model) | Ensemble scoring |
| Vendor availability | Cross-reference against ZINC-22 / Enamine REAL Space for purchasable analogues | ZINC-22 API |
| Regulatory pre-screening | PAINS filters, aggregator flags, structural alerts | RDKit + FAF-Drugs4 |

---

## 7. Datasets and Data Sources

### Primary Molecular and Bioactivity Data

| Dataset | Content | Size | License | Access |
|---------|---------|------|---------|--------|
| **ChEMBL 36** | Curated bioactivity: IC50, Ki, Kd; extracted from medicinal chemistry literature; 2.4M+ compounds, 15K+ protein targets | 36 releases, latest July 2025 | Class B (CC BY-SA 3.0) | EBI API, bulk SQL download; Python `chembl_webresource_client` |
| **PubChem 2025** | 119M+ compounds; 1.5M+ bioassay records; integrated MarkerDB, GDSC, Pharos; new RDF co-occurrence graph | 119M compounds, 300M substance records | Class A (public domain, NIH) | REST API, FTP, PubChemPy Python library |
| **ZINC-22** | 37B+ make-on-demand purchasable molecules; 4.5B 3D-ready conformations (pH-specific); Enamine REAL Space (29B) + WuXi GalaXi (2.5B) | 37B+ molecules | Class A (UCSF, free) | CartBlanche API; subset downloads by lead-likeness |
| **Protein Data Bank (PDB)** | 220K+ 3D macromolecular structures; co-crystallized drug-protein complexes; essential for SBDD | 220K+ structures | Class A (CC0, wwPDB) | REST API; bulk rsync; PyMOL / BioPython integration |
| **AlphaFold DB (EMBL-EBI)** | 200M+ predicted protein structures; updated with complex predictions (proteins+ligands) via EMBL/NVIDIA/SNU collaboration | 200M+ structures | Class D (non-commercial) | Web portal + bulk FTP; **use OpenFold3 for production** |
| **Therapeutics Data Commons (TDC) v2** | 100+ AI-ready datasets; 50+ learning tasks; single-cell context integration; ADMET group (13 tasks, leaderboards) | Multiple curated datasets | Class A (MIT, Harvard) | `pip install PyTDC`; 3-line data loading |
| **Enamine REAL Space** | 29B make-on-demand molecules; synthesizable in ~3 weeks; primary source for ZINC-22 | 29B+ | Commercial (free for virtual screening if purchasing compounds) | Enamine API; CartBlanche |
| **BindingDB** | Measured binding affinities (IC50, Ki, Kd, EC50); 3M+ entries; protein-ligand pairs | 3M+ measurements | Class A (CC BY 3.0) | Download, REST API |
| **DrugBank 6.0** | FDA-approved + investigational drugs; pharmacokinetics, targets, interactions; 15K+ drugs | 15K+ drugs | Class C (research free; commercial requires license) | XML download, API |

### Genomic and Target Data

| Dataset | Content | License |
|---------|---------|---------|
| **Open Targets v25.06** | Disease-target evidence scores integrating genetics, expression, somatic, text mining, animal models | Class A (Apache 2.0) |
| **GWAS Catalog (EBI)** | 6,000+ GWAS studies; 300K+ variant-trait associations; downloadable | Class A (EBI, open) |
| **GTEx v10** | Tissue-specific eQTL; 54 tissues; 1,000+ individuals | Class A (NIH, dbGaP open access) |
| **TCGA Pan-Cancer Atlas** | Multi-omic; somatic mutations, CNV, expression, methylation; 11,000+ tumours | Class A (NIH, open) |
| **Human Protein Atlas v23** | Protein expression in 44 tissues and 80+ cell types; IHC + RNA | Class B (CC BY-SA 4.0) |
| **TTD 2026** | 2,912 targets; 306K disease associations; 10,506 perturbation profiles | Class A (CC BY) |
| **UniProtKB / Swiss-Prot** | 570K+ manually reviewed proteins; function, localization, PTMs, interactions | Class A (CC BY 4.0) |

### Pretraining and Foundation Model Datasets

| Dataset | Content | Use Case |
|---------|---------|----------|
| **ZINC-22 3D conformers** | 4.5B ready-to-dock conformations | Molecular generation pretraining |
| **Enamine REAL Space SMILES** | 29B synthesizable molecules | Generative model pretraining |
| **PDB structures** | 220K cocrystal complexes | Structure-based model training |
| **ChEMBL assay data** | 2.4M compound-activity pairs | ADMET and affinity model training |
| **TDC ADMET benchmark** | 13 standardized tasks, leaderboard splits | ADMET model validation |
| **ESM pretraining data** | 2.78B natural proteins + 771B tokens | Protein foundation model (use pre-trained) |
| **M3-20M** | 20M multi-modal molecules (1D SMILES + 2D graph + 3D structure + text); 71× larger than prior sets | Multimodal molecular LM training |

---

## 8. Full Stack — Best-of-Breed Picks by Layer

| Layer | Tool | License | Notes |
|-------|------|---------|-------|
| Target scoring | Open Targets Platform 25.06 | A | Apache 2.0; Python API |
| Target database | TTD 2026 | A | REST API; updated January 2026 |
| Literature mining | PubTator 3.0 | A | Best NER; F1 > 0.90 |
| Literature reasoning | GPT-Rosalind (API) | C | Do not embed; call via OpenAI Life Sciences Codex API |
| Protein LM | ESM2 (sequence only) | A | Meta/MIT; fast embeddings |
| Protein generative LM | ESM3-sm-open (300M) | A | EvolutionaryScale; local deploy |
| Structure prediction | OpenFold3 | A | **THE pick** — Apache 2.0; AF3-class; commercial-safe |
| Structure + affinity | Boltz-2 | A | **THE pick** — MIT; 1000× faster than FEP; affinity prediction |
| Protein binder design | RFdiffusion3 | Open (commercial) | Baker Lab; Dec 2025; atom-level diffusion |
| Sequence design | LigandMPNN | A | Baker Lab; handles small-molecule context |
| Small molecule generation | REINVENT 4 | A | Apache 2.0; AstraZeneca production tool |
| Structure-based generation | DiffSBDD | A (research) | SE(3)-equivariant; pocket-conditioned |
| Property prediction | Chemprop v2 | A | MIT; D-MPNN; 2× faster, 3× less memory than v1 |
| 3D molecular representation | Uni-Mol v2 | A | MIT; SE(3) transformer; SOTA on 14/15 MoleculeNet |
| Docking (fast screen) | AutoDock Vina 1.2 | A | Apache 2.0; ZINC-22 scale |
| Docking (accurate) | GNINA 1.3 | A | Apache 2.0; deep learning; Feb 2025; covalent support |
| ADMET prediction | Chemprop v2 (custom-trained) | A | Train on TDC ADMET datasets |
| ADMET benchmark | TDC ADMET Group | A | Use for model validation only |
| Retrosynthesis | ASKCOS | A | MIT; programmatic API |
| Multi-objective optimization | BoTorch + Ax | A | Meta/MIT; same stack as Materials/Energy |
| Cheminformatics | RDKit | A | BSD-3; all fingerprints, filters, descriptors |
| Orchestration | LangGraph v1.0 | A | MIT; stateful graph agents; human-in-the-loop |
| Workflow management | AiiDA 2.8 | A | MIT; provenance-tracking; same as Materials vertical |
| Compound database | ZINC-22 | A | UCSF; 37B purchasable compounds |
| Bioactivity data | ChEMBL 36 | B | CC BY-SA; outputs (ML models, predictions) are yours |
| Chemical data | PubChem 2025 | A | NIH public domain |
| Structure database | PDB | A | CC0 |

---

## 9. Intersectional Science Lens

### How Zer0pa's Existing Domains Map to Drug Discovery

| Zer0pa Domain | Equivalent in Drug Discovery | Concrete Application |
|---------------|------------------------------|---------------------|
| **Information theory** | Binding entropy / free energy decomposition | ΔG = ΔH - TΔS: entropy of binding is the computational quantity connecting info theory to ligand binding; mutual information maximization as exploration strategy |
| **Computational physics** | Quantum chemistry (DFT, QM/MM) for electronic structure of binding pockets; molecular dynamics for conformational sampling | PySCF / CP2K for high-fidelity binding site calculations (same tools as Materials L1) |
| **Geometric unity** | SE(3)-equivariant architectures (DiffSBDD, GNINA, ESM3) respect the rotational/translational symmetry group of 3D molecular space | The same geometric inductive bias that governs crystal structure prediction governs protein-ligand docking |
| **Biocomputation / cellular automata** | REINVENT 4's RL loop: molecule population as CA-like state; reward signal as local rule | Chemical space exploration = CA rule evolution; Boltzmann sampling = thermal CA |
| **Cognitive theory** | Active learning oracle selection = Bayesian agent with posterior beliefs over chemical space | BoTorch acquisition functions are formalized epistemology |

### New Domains Entered in This Vertical

| New Domain | Core Concepts | Tools | Connection to Existing Domains |
|-----------|---------------|-------|-------------------------------|
| **Medicinal Chemistry** | Lipinski rules, bioisosterism, SAR (structure-activity relationship), lead optimization | REINVENT 4, RDKit, Chemprop | Pattern in chemistry = pattern from nature principle; SAR is an empirical field ripe for information-theoretic compression |
| **Structural Biology** | Protein folding, binding pocket geometry, conformational ensembles, allosteric sites | OpenFold3, Boltz-2, PDB | Protein folding is a geometric problem in SE(3) space — exact same mathematics as materials crystal structure prediction |
| **Pharmacology** | Dose-response curves, receptor pharmacology, Ki/IC50/EC50, selectivity, polypharmacology | ChEMBL, BindingDB, GtoPdb | The dose-response sigmoid is the logistic function — same saturation dynamics as information-theoretic channel capacity |
| **Genomics / Genetics** | GWAS, variant-to-function mapping, Mendelian randomization (causal target validation), CRISPR screens | Open Targets, GWAS Catalog, TCGA | Causality in genomics = causality in dynamical systems; Granger causality between genetic variants and phenotypes |
| **Biochemistry** | Enzyme kinetics (Michaelis-Menten), metabolic pathways, protein-protein interactions | UniProt, STRING, KEGG | Michaelis-Menten kinetics maps to the same saturation differential equations as battery Butler-Volmer — same physical class |
| **Toxicology** | ADMET, hERG cardiotoxicity, hepatotoxicity, mutagenicity (Ames test), reproductive toxicity | TDC, ADMETlab 3.0 | Toxicity prediction = pattern recognition in chemical space; multi-task learning across toxicity endpoints is mathematically equivalent to MTL in any other domain |

### The Intersectional Signal Pattern

The fundamental physical unification across these domains:

**Every binding/interaction event is an energy minimization problem in a high-dimensional space.**

- Drug-protein binding: minimize ΔG = ΔH - TΔS
- Crystal formation: minimize lattice energy
- Plasma confinement: minimize MHD energy functional
- Neural learning: minimize loss function (free energy in variational Bayes)

The mathematical structure is identical. This is not metaphor — it is the same optimization problem in different notation. An ML architecture that learns energy minimization for one domain transfers representational power to another. This is the core of the Zer0pa cross-domain moat.

**Information token unification insight**: SMILES encodes a molecule the same way a genome sequence encodes a protein, the same way a crystal composition vector encodes a material. The token is a compressed description of a physical object. The pipeline is: **token → structure → property → function**. All three verticals (pharma, materials, energy) share this canonical form.

---

## 10. Frontier Watch — 2025–2026 Developments Changing the Field

| Development | Date | Impact |
|-------------|------|--------|
| **GPT-Rosalind** (OpenAI) | April 2026 | First frontier reasoning model for biology. Tops BixBench; 95th+ percentile on RNA task vs. human experts. Integrates 50+ scientific databases. Research preview — watch for GA. |
| **Boltz-2** (MIT/Recursion) | June 2025 | First AI model approaching FEP accuracy for binding affinity at 1,000× speed. Changes the economics of hit-to-lead screening. MIT license. |
| **OpenFold3** (SandboxAQ + consortium) | February 2026 | AF3-class co-folding under Apache 2.0. Removes the non-commercial constraint of AF3. Critical unblocking for production pipelines. |
| **RFdiffusion3** (Baker Lab) | December 2025 | 10× faster than predecessor. Atom-level diffusion. Commercial-permissive. Protein binder design now tractable at industrial scale. |
| **NVIDIA BioNeMo expansion** | January 2026 | Full open platform with new RNA structure models; $1B Eli Lilly partnership. 2026 described as "biology's transformer moment" by NVIDIA. |
| **Chemprop v2** | December 2025 | Ground-up rewrite; 2× faster, 3× less memory; multi-GPU; full Python API. Production-grade open ADMET engine. |
| **NVIDIA Accelerating Drug Discovery** | 2026 | Artificial (whole-lab orchestration) integrates BioNeMo + robotic SDL; self-driving lab architecture published April 2025. |
| **Quantum-enhanced ADMET (QW-MTL)** | September 2025 | First joint multi-task training across all 13 TDC ADMET tasks using quantum chemical descriptors. SOTA on 12/13. Physics-informed ADMET. |

---

## 11. Architecture Sketch — Full Pipeline

```
═══════════════════════════════════════════════════════════════════
 ZER0PA PATHWAY 1: DRUG DISCOVERY PIPELINE
═══════════════════════════════════════════════════════════════════

 INPUT: Disease indication + biological target class

 ┌─────────────────────────────────────────┐
 │ STAGE 1: TARGET IDENTIFICATION           │
 │  Open Targets 25.06 + TTD 2026          │
 │  PubTator 3.0 NER + BioBERT extraction  │
 │  GATher graph attention target ranking  │
 │  GPT-Rosalind hypothesis synthesis (API)│
 │  OUTPUT: {UniProt_ID, confidence, evidence} │
 └────────────────┬────────────────────────┘
                  ↓
 ┌─────────────────────────────────────────┐
 │ ENABLING: STRUCTURE PREDICTION           │
 │  OpenFold3 (Apache 2.0) — primary       │
 │  Boltz-2 (MIT) — structure + affinity   │
 │  ESM3-sm (open) — protein representation│
 │  OUTPUT: {3D_pocket, binding_residues}  │
 └────────────────┬────────────────────────┘
                  ↓
 ┌─────────────────────────────────────────┐
 │ STAGE 2: MOLECULE GENERATION            │
 │  REINVENT 4 (Apache 2.0) — de novo RL  │
 │  DiffSBDD (MIT) — 3D pocket-conditioned │
 │  RFdiffusion3 — protein binder design   │
 │  BioNeMo Framework — custom models      │
 │  OUTPUT: 10K–100K candidate SMILES      │
 └────────────────┬────────────────────────┘
                  ↓
 ┌─────────────────────────────────────────┐
 │ STAGE 3: IN SILICO SCREENING            │
 │  RDKit pre-filter (Lipinski/SA score)   │
 │  Boltz-2 affinity prediction            │
 │  GNINA 1.3 pose + rescoring             │
 │  Chemprop v2 ADMET panel (13 tasks)     │
 │  Selectivity: ChEMBL off-target panel   │
 │  ASKCOS synthesizability filter         │
 │  OUTPUT: 100–500 ranked hits            │
 └────────────────┬────────────────────────┘
                  ↓
 ┌─────────────────────────────────────────┐
 │ STAGE 4: HIT-TO-LEAD REFINEMENT         │
 │  REINVENT 4 (RL optimization loop)      │
 │  BoTorch + Ax (Bayesian multi-objective) │
 │  Chemprop v2 oracle (fast ADMET)        │
 │  Boltz-2 oracle (affinity per iteration)│
 │  ASKCOS (synthesizability gate)         │
 │  OUTPUT: 10–50 optimized lead candidates│
 └────────────────┬────────────────────────┘
                  ↓
 ┌─────────────────────────────────────────┐
 │ STAGE 5: HANDOFF LAYER                  │
 │  Structured JSON candidate dossier      │
 │  ZINC-22 purchasable analogue lookup    │
 │  PAINS / structural alert filter        │
 │  CRO-ready SDF + synthesis route        │
 │  OUTPUT: Ranked candidate package       │
 └─────────────────────────────────────────┘

 ORCHESTRATION: LangGraph v1.0 (MIT) + AiiDA 2.8 (MIT)
 OPTIMIZATION:  BoTorch + Ax (Meta, MIT)
 COMPUTE:       NVIDIA GPU (BioNeMo NIM) or CPU-only for small runs
```

---

## 12. Licensing Summary and Commercial Strategy

### What Is Freely Commercializable (Class A outputs)

- All predictions made by Chemprop v2 (MIT)
- All molecular structures generated by REINVENT 4 (Apache 2.0)
- All docking results from AutoDock Vina / GNINA (Apache 2.0)
- All candidate structures generated by DiffSBDD (MIT-style)
- All protein designs from RFdiffusion3 / ProteinMPNN (Baker Lab commercial-permissive)
- All structures predicted by OpenFold3 (Apache 2.0)
- All structures and affinity predictions from Boltz-2 (MIT)

### What Requires Careful Handling (Class B)

- ChEMBL data (CC BY-SA): training models on ChEMBL data does NOT create a copyleft obligation on the trained model or its predictions — only on redistribution of the database itself
- Human Protein Atlas (CC BY-SA): same — using as training data does not restrict outputs
- BoTorch / LangGraph (MIT): no restrictions on commercial use of pipeline outputs

### What To Avoid Embedding (Class C / D)

- AlphaFold 3 weights: Class D (non-commercial). Replace with OpenFold3 (Class A)
- ADMETlab 3.0: Class C web service. Use for benchmarking only; production ADMET via Chemprop v2
- GPT-Rosalind: Class C research preview. Call via API; do not attempt to replicate
- DrugBank commercial use requires license

### The Open-Source Pipeline + Commercialize Outputs Strategy

This pipeline is fully viable under the Zer0pa model:
1. All core tools (REINVENT 4, Chemprop v2, GNINA, OpenFold3, Boltz-2, RDKit) are Class A
2. Data sources (ChEMBL, PubChem, PDB, ZINC-22) are Class A or B with output-safe terms
3. **The drug candidates generated are the commercial output** — they belong to whoever commissions the pipeline run
4. The orchestration infrastructure (LangGraph + AiiDA + BoTorch) is Class A throughout
5. Open-sourcing the pipeline itself creates no restriction on selling the candidate outputs

**Recommended structure**: Open-source the orchestration framework; license the trained property prediction models (Chemprop v2 fine-tuned on proprietary assay data); commercialize candidate delivery.

---

## 13. PRD Agent Instructions

The agent writing the PRD from this document should:

1. **Use the six-layer naming convention** from the Energy/Materials pipelines: L1 (Target), L2 (Structure), L3 (Generation), L4 (Screening), L5 (Optimization), L6 (Orchestration). Note this pipeline has a slightly different structure from process development — L2 (structure prediction) is an enabling layer, not a named commercial stage.

2. **Preserve the information token definition** from Section 0. Every agent output must be typed against this token schema.

3. **Treat Boltz-2 as the single most important tool pick** in this pipeline. It replaces the traditional docking → FEP two-step with a single model at 1,000× speed and FEP-level accuracy. This is the key pipeline compression moment.

4. **Treat GPT-Rosalind as a remote oracle**, not an embedded component. All target identification reasoning and hypothesis generation should route through the OpenAI Life Sciences Codex API. The pipeline should be designed to swap this out when a Zer0pa fine-tuned model becomes available.

5. **Design the REINVENT 4 scoring function** as the primary integration point. Every property model (Chemprop v2 ADMET models, Boltz-2 affinity predictor, ASKCOS synthesizability) should be registered as a scoring component in REINVENT 4's plugin API. This is the correct architecture — REINVENT 4 as the loop controller, all oracles as scoring plugins.

6. **Use BoTorch for multi-objective Bayesian optimization** with the same configuration as the battery/materials pipeline. The acquisition function is Expected Hypervolume Improvement (EHVI) over a Pareto frontier of: pIC50, QED, SA score, hERG safety, solubility. This maps directly to BoTorch's `qEHVI` implementation.

7. **Explicitly log all candidate provenance via AiiDA.** Every molecule generated, every score predicted, every optimization step must be stored in the AiiDA provenance graph for audit and reproducibility — required for CRO handoff credibility.

8. **Build the handoff format first.** The CRO handoff JSON schema (Section 6) should be the output contract from which the entire pipeline is designed backward. This is how the pipeline stays commercially grounded.

