# In Silico Drug Process Development: Corrections, Augmentations, and Pipeline Architecture

## Brief #2 — Companion to the Full Technology Landscape Survey (Brief #1, April 2026)
**Prepared for Zer0pa Frontier AI Orchestration Lab | April 2026**

***

> **How to use this document**: Brief #2 patches, corrects, and extends Brief #1. It does not replace it. All six issues from the expert review are addressed with citations and verdicts. New sections add the missing Retrosynthesis layer, a corrected Digital Twins assessment, working pipeline examples, a regulatory signal map, and a full orchestration architecture specification. The Combined Master Tool Selection table at the end supersedes Brief #1's Executive Map.

***

## Section 1: Corrections and Confirmations

### Issue 1 — Layer 4 (Digital Twins): Classification Error Confirmed and Corrected

**Verdict: Error confirmed. COPASI and Tellurium are Layer 5 tools. Layer 4 requires a fundamentally different tool category.**

The classification in Brief #1 is incorrect. COPASI 4.45 is an ODE/SDE-based biochemical network simulator built on SBML — it models enzyme kinetics, metabolic flux, and signalling pathways at the molecular level. Tellurium is a Python wrapper around the RoadRunner ODE engine, also SBML-based, designed for exactly the same purpose. Both tools simulate *what reactions do* inside a cell or organism. Neither is capable of modelling *what a manufacturing plant does* — they have no concepts of equipment geometry, heat transfer, fluid dynamics, granulation, tablet compression, bioreactor gas sparging, or sensor data integration. Placing them in Layer 4 was a category error arising from loose use of the word "process."[^1][^2][^3]

**What Layer 4 actually requires** is a different class of tool: equipment-level dynamic simulation linked to real-time sensor streams, capable of predicting equipment behaviour, optimising process parameters, and running in synchrony with physical manufacturing. The review of the actual Layer 4 landscape follows.

***

#### The Open-Source Manufacturing Digital Twin Landscape for Pharma

**Eclipse Ditto** (Eclipse Public License v2.0, Class B) is the leading open-source framework for IoT digital twins. It manages the lifecycle of device-level digital twins via a REST/WebSocket API, enabling real-time sensor data to be ingested, stored, and queried as structured twin state. In a pharma manufacturing context, Ditto provides the *data integration layer* — connecting PAT (Process Analytical Technology) sensors on granulators, blenders, and bioreactors to a queryable virtual state model. It does not provide process physics simulation; it is the sensor-to-state binding layer. License: Class B (EPL v2.0 — outputs yours, redistributed framework must retain licence).[^4]

**FIWARE Orion Context Broker** (Apache 2.0, Class A) is an open-source context management platform widely used in smart manufacturing and Industry 4.0 deployments. It provides REST-based context data management for IoT-connected processes using the NGSI-v2 and NGSI-LD standards. Like Ditto, it handles the *data layer* of a digital twin rather than the physics layer. It is actively maintained by the FIWARE Foundation and has documented applications in pharmaceutical and food manufacturing environments.[^5]

**OpenModelica** (LGPL v3.0, Class B) is an open-source equation-based modelling and simulation platform implementing the Modelica language standard. It supports both steady-state and dynamic simulations, covers thermodynamics, chemical kinetics, fluid dynamics, and heat transfer in unified equation-oriented models. Crucially, it supports FMI (Functional Mock-up Interface) export and import, making it the recommended simulation engine for interoperable digital twin components. A published study explicitly demonstrated OpenModelica for chemical process unit operation simulation, creating a library of streams and unit operations within the tool. License class B: LGPL — tool is copyleft, but simulation outputs (e.g., predicted concentration profiles, temperature trajectories) are yours to commercialise.[^6][^7][^8][^9]

**The FMI Standard (Functional Mock-up Interface)** is a free, tool-neutral standard published by the Modelica Association for model exchange and co-simulation between different simulation tools. An FMU (Functional Mock-up Unit) is a compiled simulation component that can be exported from OpenModelica, AspenPlus, MATLAB/Simulink, or any FMI-compliant tool and run inside any other FMI-compatible environment. For pharmaceutical process digital twins, FMI is the *correct interoperability contract*: individual unit operation models (granulation, drying, tablet compression) can be independently developed and connected through standardised FMI interfaces. License: Free standard, no restrictions.[^10]

**AspenPlus / Aspen HYSYS** (Commercial, Class D) are the industry-standard commercial process simulators for chemical and pharmaceutical manufacturing. Both support dynamic process simulation, thermodynamics, and process optimisation. AspenPlus has documented Python COM interface connectivity — the aspenparserDLR toolbox (DLR, Python, open-source) enables programmatic access to AspenPlus simulations from Python, supporting stream and block property manipulation, simulation execution, and data export. An academic license programme exists through AspenTech's Educational Program — universities and research institutions can access AspenTech software for non-commercial research and teaching. For commercial use, a paid license is required (Class D), but outputs from licensed simulations are the user's own.[^11][^12][^13]

**PharmaPy** (MIT, Class A — **the most important overlooked tool for this layer**) is an open-source Python library from the CryPTSys group (Carnegie Mellon / Purdue lineage) specifically designed for pharmaceutical manufacturing systems analysis. It models unit operations in batch, continuous, and semi-batch modes; supports end-to-end flowsheet simulation connecting unit operations; and has a Pyomo-based optimisation interface for process parameter optimisation. This is not a generic chemical engineering tool — it is explicitly pharmaceutical-manufacturing-focused, covering crystallisation, filtration, granulation, blending, and tablet compression dynamics. License class A: MIT. Outputs are fully commercialisable.[^14][^15][^16][^17]

***

#### Is there a genuinely capable open-source manufacturing digital twin option for pharma?

**Partial yes, with an architectural caveat.** No single open-source tool provides a complete pharma manufacturing digital twin out of the box. However, the following open-architecture combination is viable for a computational lab:

| Role | Tool | License |
|------|------|---------|
| Pharma-specific process physics | PharmaPy (Python) | A (MIT) |
| General process dynamics / thermodynamics | OpenModelica or DWSIM | B (LGPL/GPL) |
| CFD for mixing, bioreactors | OpenFOAM | B (GPL) |
| DEM for granulation/tablet compression | LIGGGHTS | B (GPL) |
| Interoperability standard | FMI/FMU | Free standard |
| IoT/sensor data binding layer | Eclipse Ditto | B (EPL v2.0) |

The commercial tools (AspenPlus, Emerson DeltaV, Rockwell FactoryTalk) remain dominant in production pharma manufacturing because they bundle all these components with validated thermodynamic databases and regulatory audit trails. **For Zer0pa's pipeline, which is simulating processes in silico rather than controlling physical plants, the open architecture is sufficient.** The regulatory implications of which simulation platform outputs are accepted in submissions are covered in Section 5.

**Recommendation**: Remove COPASI and Tellurium from Layer 4. They belong in Layer 5 (see Issue 1 verdict below). Replace the Layer 4 tool selection with PharmaPy (primary), OpenModelica (equation-based dynamics), Eclipse Ditto (sensor integration), and OpenFOAM (CFD components). Retain AspenPlus as Class D commercial reference for regulatory-grade submissions.

**COPASI and Tellurium verdict**: Both should be moved to Layer 5 (PKPD/Systems Pharmacology) where they are correctly positioned as ODE-based biological network simulators that complement PK-Sim and nlmixr2. In Layer 5, COPASI handles stochastic and deterministic network simulation while Tellurium provides Python-native SBML simulation. The move is a reclassification, not a removal.

***

### Issue 2 — PINN Drug Release: Research Method Correctly Flagged, Implementation Path Clarified

**Verdict: (b) — A build-from-paper methodology, but with a production-grade PINN framework available that makes implementation tractable.**

The specific paper behind the PINN Drug Release entry in Brief #1 is: *"Drug Release Modeling using Physics-Informed Neural Networks"* (arXiv 2602.09963, submitted February 9, 2026). The paper demonstrates PINNs and Bayesian PINNs (BPINNs) for predicting drug release from planar, 1D-wrinkled, and 2D-crumpled polymer films. Key findings: 40% mean error reduction vs. classical baselines; RMSE < 0.05 achievable from only the first 6% of release time data (planar film); BPINNs provide calibrated uncertainty under noisy conditions. No associated code repository was found; it appears to be a standalone arXiv preprint without a maintained codebase as of April 2026.[^18][^19]

**Brief #1's listing was a false equivalence.** A scientist attempting to deploy "PINN Drug Release (Fick's law)" as a tool would find a research paper, not a pip-installable library. The listing should not sit alongside RDKit and DeepChem in the Executive Map.

**The production-grade PINN framework that does exist: DeepXDE**

DeepXDE (MIT license, Class A) is a production-grade scientific machine learning library for physics-informed neural networks and neural operators, maintained on GitHub with active development. It supports multiphysics problems, handles arbitrary PDEs as loss constraints, and has Python API and GPU support. Crucially, a 2025 paper in the *Journal of Chemical Information and Modeling* explicitly implemented dissolution modelling using DeepXDE, combining PINNs for physical law embedding with DNNs for molecular structure incorporation to predict dissolution profiles. This is the closest existing production implementation of PINN dissolution modelling and it uses DeepXDE as its framework.[^20][^21][^22]

**The implementation effort for a minimal PINN dissolution model with DeepXDE:**

1. Install DeepXDE (pip install deepxde)
2. Define Fick's second law as the governing PDE in DeepXDE's PDE specification syntax
3. Collect 30–50 experimental dissolution time points per formulation (standard dissolution assay output)
4. Train on the first 6% of time-series data; predict to full release horizon
5. Use BPINNs variant for uncertainty quantification under limited data

The total implementation effort is approximately 3–5 days of engineering work for a physicist comfortable with PDEs. No pharma-specific domain knowledge is required beyond understanding Fick's diffusion law — which is the same Fickian diffusion equation used in heat conduction simulation.

**Corrected classification for Executive Map:** Replace "PINN Drug Release (Fick's law) — A (research)" with "DeepXDE 1.x — physics-informed dissolution modelling framework — A (MIT) — implement against Fick's PDE using 30–50 dissolution data points."

PINN applications in pharma remain predominantly research implementations today (2026), but DeepXDE provides the engineering layer that makes them deployable. A dedicated pharmaceutical PINN dissolution library does not yet exist as a packaged product with pre-built pharmaceutical PDE libraries. Simulations Plus GastroPlus (Class D) remains the commercial standard for regulatory-grade biopharmaceutics modelling.

***

### Issue 3 — Retrosynthesis Layer: Confirmed Missing, Now Fully Specified

**Verdict: Structural gap confirmed. This section constitutes the full specification — see Section 2.**

The pipeline does move directly from molecular simulation (L1) to formulation/process design without addressing how a designed molecule would actually be synthesised. This is not merely an academic omission. In a real orchestration pipeline, a generative model producing a novel molecule SMILES must be immediately followed by a synthesis feasibility check — otherwise the entire downstream chain is speculative. Full Layer 2.5 specification in Section 2 below.

***

### Issue 4 — OpenFE Missing from Layer 1: Confirmed Omission, Now Corrected

**Verdict: OpenFE is a production-ready, commercially deployable alternative to Schrödinger FEP+. It must be added to Layer 1.**

**OpenFE v1.7.0** (released October 2025, MIT license, Class A) is the open-source consortium answer to the industry's dependence on Schrödinger FEP+ for relative binding free energy calculations. It is developed by the Open Free Energy Consortium with industry partners including pharmaceutical companies.[^23][^24]

**Benchmark performance:** A large-scale collaborative assessment preprint (December 2025) benchmarked OpenFE on over 1,700 ligands across both public and private protein-ligand datasets in collaboration with industry partners. The result: *"OpenFE shows robust performance, generates reproducible results, and achieves sufficient throughput"* for large-scale industrial applications. A separate Open Molecular Software Foundation review (March 2026) explicitly describes OpenFE as having achieved industrial application readiness. The March 2025 internal review notes that *"OpenFE and FEP+ have similar accuracy but not always on the same edges"* — meaning the two are comparable in prediction quality.[^25][^26][^27][^24]

**v1.7.0 specific improvements:**
- Added SepTop (Separated Topologies) protocol: enables scaffold hopping without atom mapping, combining two ABFE calculations in opposite directions[^23]
- Added Absolute Binding Free Energy (ABFE) protocol: alchemical ligand removal from binding site[^23]
- ~2x performance improvement since v1.0: ~3 hours per perturbation (down from ~6 hours) using OpenMM 8.2 and updated default settings[^23]
- Installation: `conda install -c conda-forge openfe` or Docker/Singularity images[^23]

**RBFE vs. ABFE distinction:**
- **RBFE (Relative Binding Free Energy)**: Predicts the *difference* in binding affinity between two similar ligands by alchemically transforming one into the other. This is the standard method for lead optimisation — comparing analogues in a congeneric series. OpenFE RBFE uses hybrid topology or SepTop protocols.[^28][^23]
- **ABFE (Absolute Binding Free Energy)**: Predicts the *absolute* binding affinity of a single ligand by alchemically removing it from its protein binding site. More computationally expensive but applicable to scaffold hopping. Now supported in OpenFE v1.7. The new open-source Felis toolkit (March 2026) achieves ABFE performance comparable to RBFE methods at scale across 43 targets and 859 ligands.[^29][^23]

**Complementary open-source FEP tools:**

| Tool | Type | License | Key Feature | GPU Support |
|------|------|---------|------------|-------------|
| **OpenFE v1.7** | RBFE + ABFE | MIT (A) | Industry-benchmark accuracy, scaffold hopping | NVIDIA MPS accelerated |
| **TIES 2.0** | RBFE dual-topology | LGPL (B) | UCL/Manchester, NAMD + OpenMM support | CUDA |
| **PMX** | RBFE/ABFE setup/analysis | LGPL (B) | GROMACS integration, alchemical transformation setup | Via GROMACS |
| **ALCHEMD** (Dec 2025) | RBFE | Open-source (A) | 10–20 predictions/day on desktop GPU, automated | Commodity GPU |
| **QligFEP v2.1** (Feb 2026) | RBFE | Open-source (A) | Spherical boundary conditions, <1h per perturbation, <$1 AWS | Yes |

ALCHEMD achieves MUE = 0.86 kcal/mol with R² = 0.60 on the Merck KGaA benchmark set using only 29.3 ns average simulation time per ligand pair — 4–8× faster than conventional protocols, running on desktop-class GPUs.[^30]

**License classification:** OpenFE = Class A (MIT). Outputs are fully commercialisable. No FEP+ license required for a commercial pipeline. **Priority level for Layer 1: High. OpenFE should be listed as the primary open-source FEP tool**, with Schrödinger FEP+ as the commercial Class D reference.

***

### Issue 5 — QSP-Copilot: Correctly Identified as Research Implementation, More Nuanced Than Stated

**Verdict: (b) — A real, maintained, open-access platform, but with specific limitations that make it a workflow accelerator, not a fully autonomous model generator.**

**Full citation:** Saini A, Farnoud A. "QSP-Copilot: An AI-Augmented Platform for Accelerating Quantitative Systems Pharmacology Model Development." *CPT: Pharmacometrics & Systems Pharmacology.* 2025 Nov;14(11):1775–1786. doi: 10.1002/psp4.70127. Epub 2025 Oct 29. PMID: 41159846. Affiliation: Boehringer Ingelheim Pharma GmbH & Co. KG, Biberach, Germany.[^31][^32]

**GitHub repository:** https://github.com/QSP-Copilot/QSP-Copilot — freely accessible Streamlit web application, actively maintained. Additional demonstration repositories: https://github.com/QSP-Copilot/GaucherDisease and https://github.com/QSP-Copilot/BloodCoagulationPathways.[^33][^32]

**LLMs tested:** GPT-4o (general knowledge synthesis), Claude Sonnet (complex reasoning tasks), TxGemma (domain-specific biological entity recognition). Model selection is dynamically optimised by the orchestration layer based on task requirements.[^32]

**Quantitative performance on biological entity extraction:**
- Blood coagulation (10 papers, 44 pages): Precision 99.1%, Recall 93.8%, F1 96.4%. Processing time: 17 minutes.[^32]
- Gaucher disease (9 papers, 39 pages): Precision 100.0%, Recall 86.1%, F1 92.5%. Processing time: 14 minutes.[^32]
- Variability noted: GPT-4o-mini outperforms GPT-3.5-Turbo and GPT-4.1-nano on extraction completeness due to context window differences.[^32]

**Output formats:** SBML, mrgsolve (v1.0.9), RxODE (v2.0.12), Python SciPy `solve_ivp`. All outputs follow MIASE guidelines for reproducibility.[^32]

**Current limitations (as stated by authors):**
1. Generated base models lack cellular dynamics (proliferation, apoptosis) — to be added in future versions
2. Parameters and initial conditions use placeholder values — no automated parameter estimation yet
3. Free tier supports <5 PDFs and <10 ODE equations; enterprise deployment requires AWS infrastructure[^32]
4. Model construction is at Stage 2–3 of the QSP workflow (literature extraction, biological entity network, base ODE structure) — Stage 4 (parameterisation), Stage 5 (validation), and Stage 6 (application) remain manual[^32]

**Replication:** Two demonstration cases are fully documented and reproducible from GitHub. No independent replication by groups outside Boehringer Ingelheim was found as of April 2026.

**Corrected classification for Brief #1:** QSP-Copilot should be described as: *"a production-accessible research platform (Streamlit web app, GitHub-hosted) that automates the literature synthesis and base model structure generation phases of QSP model development, reducing this specific phase by ~40%. It is not a complete autonomous QSP model generator — parameter estimation and model validation remain manual. Appropriate for use as a Layer 6 → Layer 5 connection that handles biological entity extraction and ODE scaffolding, with human expert completion of parameterisation."*

**License classification:** Class E (unclear) — GitHub repository is open but no explicit MIT/Apache license is declared in the repository. The Streamlit application is freely accessible. Commercial use of the code would require clarification from Boehringer Ingelheim.

***

### Issue 6 — GPT-Rosalind Access Gap: Equivalence Claim Decomposed, Practical Stack Specified

**Verdict: The Brief #1 equivalence claim is approximately correct for database connectivity but incorrect for domain-specialised scientific reasoning. The gap is real but bridgeable with open-weight alternatives.**

#### What GPT-Rosalind offers that GPT-5.4 + Codex Plugin does not

GPT-Rosalind is OpenAI's first vertical, science-tuned reasoning model, released April 16, 2026. Its differentiators are:[^34][^35]

1. **Specialised fine-tuning on life sciences corpora**: Rosalind has been trained or RLHF-tuned specifically on biological research tasks — protein structure reasoning, reaction pathway inference, pharmacokinetic interpretation. GPT-5.4 is a general-purpose model that accesses this knowledge at inference time without the inductive biases of specialised training.[^35][^34]

2. **LABBench2 benchmark (2026)**: On this 1,900-task biology research benchmark, Rosalind outperforms GPT-5.4 on 6 of 11 task families, with the largest gains in CloningQA (molecular cloning reasoning), protein biology tasks, and genomics analysis. GPT-5.4 retains parity or leads on tasks involving literature synthesis and general scientific writing.[^34]

3. **BixBench**: 0.751 pass@1 vs GPT-5.4's 0.732. The gap is meaningful but not orders of magnitude.[^35][^34]

4. **Native context**: Rosalind has been fine-tuned to interpret simulation outputs (PDB files, SMILES strings, SBML models) as scientific objects rather than arbitrary text tokens. This reduces prompt engineering overhead for simulation-adjacent tasks.

**What the Codex Life Sciences Plugin provides (immediately accessible):** 50+ biological database connections — AlphaFold DB, PubMed/NCBI, UniProt, PRIDE, Ensembl, and others — as native tool calls in the ChatGPT and API interface. This is the *database connectivity layer*. It does not provide specialised scientific reasoning — it provides structured data retrieval that any model can then reason over.[^34]

**What GPT-5.4 + Codex Plugin can provide:** All 50 database connections (same as Rosalind), general scientific reasoning at GPT-5 level (BixBench 0.732, close to Rosalind's 0.751), function/tool-calling for Python tool schemas, and full API access globally.[^34]

**The specific gap:** Rosalind's advantage is most pronounced in tasks requiring *implicit biological reasoning* — interpreting a protein structure and inferring likely binding partners, reading a PK curve and reasoning about likely metabolic pathway, or parsing an MD trajectory and identifying mechanistically significant conformational changes. These tasks benefit from the specialised training distribution that GPT-5.4 lacks.

***

#### Claude Opus 4.7 as the Accessible Alternative

Claude Opus 4.7 (Anthropic, released April 15, 2026) is **globally accessible via API** — available through api.anthropic.com, Amazon Bedrock, Google Cloud Vertex AI, and Microsoft Foundry, with no US geographic restriction. It is not US-gated. The model achieves 87.6% on SWE-bench Verified (coding), introduces an "xhigh" effort tier for deep reasoning, and has improved multimodal capabilities for dense scientific documents.[^36][^37][^38]

Benchmark comparisons with Rosalind on scientific tasks are indirect. One community test raised Opus 4.6 from 65.3% to 92.0% on a scientific task benchmark with domain-specific prompting — which would place it above Rosalind's published BixBench score if that improvement generalised. No published head-to-head comparison of Opus 4.7 vs. Rosalind on LABBench2 or BixBench exists as of April 2026.[^39]

**Anthropic's AI Safety posture on biology:** The company moved Opus 4 to AI Safety Level 3 following red-team research on biosecurity. This may impose additional guardrails on certain molecular synthesis queries that do not affect Rosalind under its enterprise access controls.[^34]

***

#### Open-Weight Alternatives for Scientific Reasoning

**TxGemma** (Google DeepMind, released March 2025) is the most important open-weight model for Zer0pa's use case. It is built on Gemma 2 (2B, 9B, 27B variants), fine-tuned specifically for therapeutic development tasks across small molecules, proteins, nucleic acids, diseases, and cell lines. It handles molecular property prediction, drug-target interaction reasoning, and can serve as a conversational agent for drug discovery tasks. It was integrated into QSP-Copilot (Issue 5 above) for biological entity recognition, confirming its utility in the pipeline. Fine-tuning notebooks are available on Google's GitHub.[^40][^41][^42][^43]

**TxGemma license:** Based on Gemma 2 terms — permits commercial use and fine-tuning, with restrictions on using the model to compete directly with Google AI products or for applications that violate applicable laws. For a non-competing AI orchestration lab, the Gemma 2 terms are broadly permissive. Gemma 4 shifted to Apache 2.0 (April 2026) but TxGemma is built on Gemma 2 terms — check current terms before commercial deployment. **Classification: Class E (mixed/requires verification)** — use is broadly permitted but confirm with current Gemma 2 terms.[^44][^45]

**IBM Chemistry Foundation Model** (open-sourced March 2025): encoder-decoder architecture pre-trained on 91 million SMILES samples. Designed for molecular property prediction and generation rather than scientific reasoning. Less relevant for the reasoning layer but valuable as a molecule-level encoder in the pipeline.[^46]

***

#### Practical Orchestration Stack for a Non-US-Gated Lab

| Capability | Tool | Access |
|-----------|------|--------|
| Database retrieval (50+ bio DBs) | Codex Life Sciences Plugin (free) | Global, ChatGPT Plus or API |
| General scientific reasoning + tool-calling | GPT-5.4 via OpenAI API | Global via API |
| Deep scientific reasoning (alternative) | Claude Opus 4.7 | Global via API |
| Domain-specialised therapeutic reasoning | TxGemma 27B (self-hosted) | Global, Class E |
| Rosalind-equivalent reasoning (self-built) | TxGemma 27B fine-tuned on scientific simulation tasks | Build path available |

**Gap assessment:** The Rosalind gap — specialised reasoning on protein structures, reaction mechanisms, and simulation outputs — is real but not insurmountable. Fine-tuning TxGemma 27B on scientific simulation input-output pairs (protein structure reasoning tasks, PKPD interpretation tasks) would replicate the bulk of Rosalind's advantage at a fraction of the cost and with full self-hosting control. This is the recommended path for Zer0pa given the lab's fine-tuning and orchestration infrastructure.

**Recommendation:** Do not design the pipeline around Rosalind access (US-gated). Design it around GPT-5.4/Opus 4.7 as primary reasoning engines with Codex Plugin for database connectivity, and begin a TxGemma fine-tuning programme on simulation reasoning tasks as the path to Rosalind-equivalent capability.

***

## Section 2: New Pipeline Layer — Retrosynthesis (Layer 2.5)

### Layer 2.5: Retrosynthesis and Synthesis Planning

**Position in pipeline:** Between Layer 1 (molecular simulation, docking, structure confirmation) and Layer 3 (process development, flowsheet simulation). Triggered when a molecule candidate has passed binding affinity and initial ADMET screens and requires a manufacturable synthesis route.

**What happens here:** A target molecule SMILES is submitted to a retrosynthesis engine, which recursively breaks the molecule into precursor molecules until all precursors are commercially available starting materials. The output is a synthesis tree — a directed graph of chemical reactions, each step annotated with proposed reagents, conditions, and predicted yield. The synthesis tree is then evaluated for commercial viability (cost of starting materials, number of steps, synthetic complexity), and the best routes are passed to Layer 3 for process-scale modelling.

**Inputs:** SMILES string from Layer 1 output (molecule from generative design, or docking hit confirmed by structure prediction)
**Outputs:** RXNSMILES-encoded synthesis routes (reactants>>products), with step counts, starting material costs, predicted yields, and recommended reaction conditions. Standard output format: RXNSMILES + JSON metadata.

***

#### Layer 2.5 Tool Catalogue

**AiZynthFinder 4.3** (MIT license, Class A) — AstraZeneca's open-source retrosynthesis planning tool using Monte Carlo Tree Search guided by a neural network policy trained on reaction templates. Active development with v4.3 achieving 73% coverage on the 50K ChEMBL benchmark. The 2024 v4.0 paper documents three years of industrial application improvements: filter policies, multiple one-step model support, scoring framework, and additional search algorithms. Human-guided planning via natural language prompting was added in 2025. The eUCT and dUCT enhancements (2025, integrated into AI4Green) reduce computation time by up to 50% for heavy molecules (500–800 Da) and solve 600–900 additional molecules in 150s time-constrained searches.[^47][^48][^49]

- **Interface:** Python API (`aizynthfinder` package), CLI, Docker
- **Performance:** ~73% route-finding rate on ChEMBL 50K (default); enhanced with eUCT/dUCT
- **License:** MIT (A) — outputs fully commercialisable
- **Industrial use:** 3+ years in production at AstraZeneca; used by Janssen for library synthesis feasibility screening[^50][^47]
- **GPU support:** Not required for template-based search; condition recommendation models benefit from GPU

**ASKCOS v2** (MIT license, Class A — *with one exception*) — MIT MLPDS Consortium's comprehensive open-source computer-aided synthesis planning suite. More complete than AiZynthFinder in scope: includes four one-step retrosynthesis model types (template-based, Transformer, Graph2SMILES, Retrosim), automatic multi-step planning (MCTS, Retro*), reaction condition recommendation, forward reaction outcome prediction, impurity prediction, solubility prediction, and QM descriptor prediction.[^51][^52][^50]

License note: All code is MIT-licensed via GitLab (gitlab.com/mlpds_mit/askcosv2). **Exception:** models trained on CAS Content data are MLPDS-consortium-only; the 2016 Reaxys model is CC BY-NC 4.0 (non-commercial). All other models (Pistachio, USPTO, enzyme) are MIT. For a commercial pipeline, use the USPTO-trained or Pistachio models, not the Reaxys NC model.[^51]

- **Interface:** Web UI, REST API, Python API modules, Docker deployment, CLI
- **Performance:** Top-1 accuracy on USPTO-50K: Transformer w/aug 53.2%, Graph2SMILES 52.9%, Template relevance 45.2%[^51]
- **License:** Class A (MIT) for commercial models; Class C for Reaxys NC model — use USPTO/Pistachio variants
- **Industrial adoption:** Used at Pfizer, Syngenta, Novartis, Bristol Myers Squibb, dozens of MLPDS members[^51]
- **2025.07 release:** Active maintenance confirmed[^53]

**Syntheseus** (MIT license, Class A) — Microsoft Research benchmarking framework for retrosynthesis algorithm evaluation, not a deployment tool. Establishes best practices for consistent evaluation, exposes systematic benchmarking shortcomings in prior literature (rankings change with proper evaluation), and provides a standardised Python library for running and comparing retrosynthesis models. Its value to an orchestration lab: use Syntheseus to evaluate and compare custom-trained retrosynthesis models before deploying them in production. Not a planning tool; a quality assurance tool.[^54][^55]

**IBM RXN for Chemistry** (Partially open — Class E) — IBM's AI-powered synthesis planning platform using Molecular Transformer for forward/retro prediction. The `rxn4chemistry` Python wrapper is open-source on GitHub. The platform integrates Thieme Science of Synthesis data for enhanced predictions. Free tier available for academic/non-commercial use; commercial API access requires IBM enterprise agreement. The RoboRXN variant connects to automated laboratory hardware. For an orchestration pipeline: IBM RXN is accessible for prototyping via the Python wrapper; commercial deployment terms require IBM negotiation.[^56][^57][^58][^59]

**Chemprop v2** (MIT license, Class A) — MIT's message-passing neural network framework for molecular property prediction. In the retrosynthesis layer, Chemprop is used for **forward reaction yield prediction** — given a proposed reaction step from AiZynthFinder/ASKCOS, predict whether it will proceed and at what yield. Chemprop v2 (2025 release) is fully modular, GPU-accelerated, and Python-native. License class A; outputs fully commercialisable.[^60][^61][^62]

**Rxnmapper** (MIT license, Class A) — reaction atom-mapping tool from IBM/MIT. Essential for standardising RXNSMILES outputs from retrosynthesis tools into consistent atom-mapped reaction SMARTS for Layer 3 consumption. MIT licensed, Python API.[^51]

***

#### Data Format Standard for Layer 2.5 Output

The recommended output format for the retrosynthesis layer is **RXNSMILES** (reactants>>products notation using standard SMILES), augmented with:
- Reaction SMARTS for template-based steps (enables Layer 3 to identify reaction classes for kinetics modelling)
- Atom mapping via rxnmapper (enables tracking of which atoms in the product came from which reactants)
- Condition predictions (solvent, catalyst, temperature) from ASKCOS condition recommender
- Predicted yield from Chemprop forward predictor (optional but valuable for route scoring)
- JSON metadata: step count, starting material costs (from eMolecules/Sigma-Aldrich buyability check), synthetic complexity score (SCScore)

**Interface contract between Layer 1 and Layer 2.5:** SMILES string (molecule candidate) + optional constraints (available reagents, excluded reaction types, maximum step count)
**Interface contract between Layer 2.5 and Layer 3:** RXNSMILES synthesis route + step-by-step reaction conditions + predicted yields → these become the input for kinetics modelling and flowsheet design in DWSIM/OpenModelica

***

#### Layer 2.5 License Summary

| Tool | License Class | Commercial Output? |
|------|--------------|-------------------|
| AiZynthFinder 4.3 | A (MIT) | Yes |
| ASKCOS v2 (USPTO models) | A (MIT) | Yes |
| ASKCOS v2 (Reaxys model) | C (CC BY-NC 4.0) | **No** |
| Syntheseus (eval framework) | A (MIT) | Yes |
| IBM RXN (Python wrapper) | E (API terms) | Requires IBM agreement |
| Chemprop v2 | A (MIT) | Yes |
| Rxnmapper | A (MIT) | Yes |

***

## Section 3: Augmented Layer 4 — Manufacturing Digital Twins

The corrected Layer 4 tool selection, replacing the erroneous COPASI/Tellurium entries from Brief #1:

| Tool | Function | License Class | Python API | GPU | Commercialisable Outputs |
|------|---------|--------------|-----------|-----|------------------------|
| **PharmaPy** | Pharma-specific unit operation + flowsheet simulation | A (MIT) | Native | No | Yes |
| **OpenModelica** | Equation-based dynamic process simulation + FMI export | B (LGPL) | Via Python OM API | No | Yes |
| **DWSIM v9.0** | Chemical process flowsheet simulator (already in L3) | B (GPL) | COM interface | No | Yes |
| **OpenFOAM v12** | CFD for bioreactors, mixing, spray drying | B (GPL) | PyFoam | Via MPI | Yes |
| **LIGGGHTS** | DEM for granulation, tablet coating, powder flow | B (GPL) | Python | No | Yes |
| **Eclipse Ditto** | IoT digital twin data binding / sensor integration | B (EPL v2.0) | REST/WebSocket | N/A | Yes |
| **FMI Standard** | Model exchange / co-simulation interoperability | Free standard | pythonfmu | N/A | N/A |
| **AspenPlus** | Full process simulation (commercial reference) | D (Commercial) | COM/aspenparserDLR | Via solver | Yes (with license) |
| **QbDVision** | Digital CMC QbD SaaS (Brief #1 entry — retain) | D (Commercial SaaS) | REST API | N/A | Yes (outputs yours) |

**Architecture note:** In a production-grade pharma digital twin, **FMI is the integration bus**. PharmaPy models of individual unit operations are compiled to FMUs; OpenModelica handles the dynamic systems integration; Eclipse Ditto binds PAT sensor data to the virtual twin state; OpenFOAM provides CFD sub-models for mixing-sensitive operations. This multi-tool FMI-connected architecture is the correct open-source equivalent to the commercial Siemens/AspenTech integrated platforms.

**COPASI and Tellurium (moved from Layer 4 to Layer 5):** These tools are now correctly positioned in Layer 5 alongside PK-Sim and nlmixr2 as ODE-based biological network simulators for systems pharmacology and QSP modelling. In Layer 5, COPASI handles stochastic/deterministic biochemical network simulation (Gillespie and ODE), while Tellurium/RoadRunner provides Python-native SBML simulation for PKPD model execution.

***

## Section 4: Working Pipeline Examples

### 4.1 TeachOpenCADD — Complete End-to-End Tutorial Pipeline

**Coverage:** Layers 1–5 (partial). 28+ Jupyter notebook tutorials covering: ChEMBL data acquisition → ADMET filtering → molecular similarity virtual screening → docking → protein-ligand interaction analysis → molecular dynamics simulation → kinase similarity analysis.[^63][^64]

**Tools used at each handoff:**
- L1 structure/docking: PDB acquisition → AutoDock Vina via T015, OpenMM via T019–T020
- L2 ADMET: RDKit + custom filters via T002–T003
- Cheminformatics: ChEMBL API, PubChem API, RDKit, scikit-learn
- Data formats at handoffs: SMILES (molecule IDs) → SDF (3D structures) → PDB (protein complexes) → DCD (MD trajectories)

**Limitations:** Tutorial-grade, not production-grade. Workflows are sequential Jupyter notebooks, not programmatic DAG pipelines. No retrosynthesis integration. No PBPK layer. Excellent for understanding handoff data formats and tool APIs before building orchestrated equivalents.

**License:** MIT (Class A). Actively maintained — latest version 2026.4.0.post1.[^64]
**Repository:** github.com/volkamerlab/teachopencadd[^65]

***

### 4.2 NVIDIA BioNeMo Generative Virtual Screening Blueprint

**Coverage:** Layers 1–2 (molecular design through binding affinity prediction). Chains: **GenMol** (masked diffusion for molecule generation) → **DiffDock V2** (protein-ligand docking) → property filtering → ranked candidate output.[^66][^67][^68]

**Tools and data formats:**
- Input: Target protein SMILES/PDB + chemical constraints
- GenMol: generates drug-like SMILES candidates
- DiffDock V2: batch-docking, blind docking (no predefined pocket), outputs binding pose PDB + confidence score
- Output: Ranked list of candidates with predicted binding poses

**Infrastructure:** REST API NIMs (deployable locally on NVIDIA GPU or via DGX Cloud), Docker containers, reference code on GitHub (NVIDIA-BioNeMo-blueprints/generative-virtual-screening). Batch processing natively supported.[^66]

**License:** BioNeMo framework Apache 2.0; NIM inference requires NVIDIA AI Enterprise license for production deployment (free trial at build.nvidia.com). Class E for production commercial use.[^66]

**Bottlenecks:** DiffDock V2 batch docking time scales with number of ligands and target complexity. For a 10,000-molecule virtual screen: expect ~1–5 GPU-hours on A100.

***

### 4.3 NVIDIA BioNeMo Protein Binder Design Blueprint

**Coverage:** Layer 1 (protein structure and protein-protein interaction design). A 4-step orchestrated chain:[^69][^70]

1. **AlphaFold2** → predicted structure of target protein
2. **RFdiffusion** → diffusion-based generation of candidate binder conformations around target epitope
3. **ProteinMPNN** → sequence design for candidate conformations
4. **AlphaFold2-multimer** → validation of designed binder-target complex stability

**Data formats at handoffs:** Target SMILES/FASTA → PDB (after AF2) → 3D backbone coordinates (RFdiffusion) → FASTA sequences (ProteinMPNN) → complex PDB + confidence score (AF2-multimer)

**License:** Same as above (BioNeMo E). But individual component licenses are more open: AF2 (Apache 2.0 for open variants), RFdiffusion (BSD), ProteinMPNN (MIT).

***

### 4.4 MELLODDY — Federated Learning Across Pharma Companies

**Coverage:** Layer 2 (ADMET), with reach into Layer 5 (pharmacokinetics)

**Architecture:** MELLODDY used federated learning across 10 pharmaceutical companies (Merck KGaA, Pfizer, Novartis, AstraZeneca, Bayer, Janssen, Boehringer Ingelheim, GSK, Eli Lilly, F. Hoffmann-La Roche) on a combined dataset of 2.6+ billion experimental data points covering 21+ million compounds and 40,000+ assays. No raw data left individual company servers — gradients were aggregated using Owkin's federated learning platform.[^71][^72]

**Results:** Aggregated improvements on QSAR classification and regression models, particularly for PK and safety panel assay subsets. The approach demonstrates that federated models trained on 10× more data produce meaningfully better ADMET predictions than any individual company's siloed models.[^72]

**Relevance for Zer0pa:** MELLODDY is not open-source deployable infrastructure, but it demonstrates the data architecture pattern. The Korea extension (K-MELLODDY, April 2024 – December 2028, $25M budget) is building a Federated ADMET Model (FAM) using the same architecture. The published JCIM paper (2023) describes the platform architecture and results in detail.[^73][^72]

***

### 4.5 OpenAD Toolkit — IBM's Open Chemistry Agent

**Coverage:** Layer 6 → Layers 1–2 (orchestration of molecular AI tools)

IBM's Open Accelerated Discovery toolkit provides an intuitive command-line and programmatic interface to multiple AI models and services for scientific discovery. It is designed as an agent-accessible tool wrapper — analogous to what Zer0pa would build, but pre-built for chemistry tasks.[^74]

**Repository:** github.com/acceleratedscience/open-ad-toolkit
**License:** Appears to be Apache 2.0 (Class A — verify in repo)
**Limitations:** IBM-centric tool integrations. More relevant as architectural reference than direct deployment dependency.

***

### 4.6 LangGraph + Parsl — LLM Agent Connected to HPC MD Simulations

A February 2025 paper (arXiv 2502.12280) demonstrates the specific pattern of connecting LangGraph/LangChain tool-calling to Parsl (a Python parallel scripting library) to submit molecular dynamics simulation jobs to HPC clusters. The LLM agent formulates the MD setup (protein structure selection, simulation conditions) as tool calls; Parsl distributes the jobs across GPU nodes. This is the most concrete published implementation of the *exact* architecture Zer0pa needs for Layer 6 → Layer 1 orchestration.[^75]

**Key architectural finding:** LangGraph provides the agent state and tool-calling logic; Parsl handles the async execution of long-running simulation jobs on compute infrastructure. The two are loosely coupled via Python function wrapping. This pattern scales to any simulation engine that exposes a Python API.

***

## Section 5: Regulatory Signal Map

The ICH M15 guideline (final, January 29, 2026) establishes the globally harmonised framework for Model-Informed Drug Development (MIDD), covering all computational modelling and simulation methods across FDA, EMA, PMDA, Health Canada, and TGA regulatory jurisdictions. This is the most significant recent regulatory development for computational drug pipelines — MIDD has shifted from best practice to globally harmonised regulatory expectation.[^76][^77]

| Computational Method | Regulatory Status | Key Guidance | Tools Explicitly Recognised | Notes |
|---------------------|------------------|--------------|----------------------------|-------|
| **PBPK modelling** | Fully accepted: pivotal evidence | ICH M15 (2026), FDA MIDD guidance, EMA PBPK Guideline (2016) | Simcyp (Certara), GastroPlus, PK-Sim (OSP) | 26.5% of FDA-approved drugs 2020–2024 included PBPK as pivotal evidence[^78]; EMA routinely accepts in MAAs[^79] |
| **Population PK (PopPK)** | Gold standard for dose selection | ICH M15, FDA MIDD Paired Meeting Program | NONMEM (D), nlmixr2 (A), Monolix (D) | NONMEM is the regulatory gold standard; nlmixr2 OSP-community validated[^80] |
| **QSP modelling** | Accepted with qualification | ICH M15, EMA Qualified Model guidance | No tool explicitly mandated | QSP submissions to FDA nearly doubled in 5 years[^32]; qualification required for pivotal use |
| **PKPD modelling** | Standard regulatory tool | ICH M15 | NONMEM, PK-Sim/MoBi, Phoenix | Mechanistic PKPD accepted for dose regimen optimisation |
| **In silico toxicology (QSAR-based)** | Acceptable for ICH M7 mutagenicity | ICH M7 guidance | Derek Nexus (D), SARAH Nexus (D), Toxtree (A/C) | Commercial tools (Derek, SARAH) have explicit regulatory precedent; open-source tools require additional validation documentation |
| **Virtual bioequivalence (PBPK-based)** | Conditionally accepted for generic drugs | EMA 2023 commentary on complex generics | Simcyp, GastroPlus | EMA has proposed conditions for PBPK to waive clinical bioequivalence studies[^81][^82] |
| **Digital twins (QbD)** | Accepted as part of Quality by Design (QbD) | ICH Q8/Q9/Q10 | QbDVision (D), custom process models | Process models in QbD submissions accepted; real-time manufacturing digital twins for PAT are supported under FDA PAT guidance |
| **In silico clinical trials (virtual populations)** | Emerging acceptance | ICH M15, FDA MIDD Paired Meeting | Model-specific qualification required | Virtual patient populations can support, but not replace, clinical data under current guidance |
| **Molecular docking (binding prediction)** | Acceptable as supporting evidence | Not explicitly regulated | Not tool-specific | Docking results accepted as mechanistic support; not accepted as standalone binding affinity evidence |

**Critical insight for pipeline design:** PK-Sim (OSP Suite, GPL) outputs have been used in successful regulatory submissions and are accepted by regulatory agencies. The OSP Community Conference (October 2024, Novartis Basel, 100+ attendees from 40+ institutions) demonstrated the open-source PBPK community's regulatory credibility. This is the primary open-source regulatory pathway. For ADMET prediction outputs: open-source tools (DeepChem, pkCSM, SwissADME) are acceptable as supporting evidence in regulatory dossiers but carry lower weight than commercially validated platforms (GastroPlus, Simcyp, ADMET Predictor) without additional validation documentation.[^80]

***

## Section 6: Orchestration Architecture Specification

### 6.1 Multi-Agent Framework Selection

Based on a comparison of the four leading frameworks (LangGraph, CrewAI, AutoGen, OpenAgents) for scientific simulation pipeline use cases:[^83][^84][^85][^86]

| Framework | Architecture | Best For | Scientific Simulation Fit |
|-----------|-------------|---------|--------------------------|
| **LangGraph** | Stateful graph (nodes = agents/tools, edges = transitions) | Long-running stateful workflows, conditional branching, durable execution | **Highest** — graph model maps directly to multi-step simulation pipelines with branching on confidence scores |
| **CrewAI** | Role-based agent teams | Structured role collaboration (Chemist, Modeller, Analyst agents) | High — useful for modelling agent topology but less flexible for conditional graph logic |
| **AutoGen** | Conversational multi-agent | Human-in-the-loop, natural language adaptation | Medium — good for interactive refinement but not optimal for fully automated pipelines |
| **OpenAgents SDK** | General agent SDK | Enterprise deployment, tool calling | Medium — well-maintained but less specialised for scientific workflows |

**Recommendation: LangGraph as the primary agent framework.** For scientific simulation pipelines where tasks have variable runtimes (seconds for ADMET to hours for FEP), conditional execution (only run FEP if docking confidence > threshold), and durable state (pause pipeline on simulation failure, resume with fallback), LangGraph's stateful graph architecture is the correct abstraction. LinkedIn and agentic AI practitioners explicitly identify LangGraph as the optimal choice for long-running agents with external tool dependencies as of 2026.[^87][^75]

**Hybrid recommended architecture:** LangGraph (agent state + tool dispatch) + **Prefect** (workflow execution, scheduling, monitoring, failure handling) + **Parsl** (async dispatch of long-running simulation jobs to GPU/HPC). Prefect handles the production workflow concerns (retries, logging, alerting) that LangGraph does not; Parsl bridges Python function calls to distributed compute.[^75]

***

### 6.2 Scientific Agent Frameworks

**ChemGraph** (June 2025) is the most complete LLM-based agentic framework specifically for computational chemistry workflows. It chains GNN-based foundation models (for accurate calculations) with LLMs (for task planning and natural language understanding), covering molecular structure generation, single-point energy, geometry optimisation, vibrational analysis, and thermochemistry. Evaluated across 13 benchmark tasks; smaller LLMs (GPT-4o-mini, Claude-3.5-haiku, Qwen2.5-14B) handle simple workflows while larger models are needed for complex multi-step tasks. This is the architectural reference for Zer0pa's Layer 6 → Layer 1 integration.[^88]

**CACTUS** (Chemistry Agent Connecting Tool Usage to Science) and **ChemCrow** are the two most-cited open-source chemistry agent architectures as of April 2026. Both wrap domain-specific tools (RDKit, ASKCOS, Chemprop) as LLM tool schemas. ChemCrow (MIT) is pip-installable; CACTUS is newer with broader benchmarking.[^88]

***

### 6.3 Tool-Calling Architecture Specification

The recommended tool schema pattern for wrapping simulation engines is the **JSON Schema function specification** standard, compatible with all major LLM APIs:

```json
{
  "name": "run_docking",
  "description": "Dock a ligand SMILES against a target protein PDB using DiffDock V2",
  "parameters": {
    "type": "object",
    "properties": {
      "ligand_smiles": {"type": "string", "description": "SMILES string of ligand"},
      "protein_pdb_id": {"type": "string", "description": "PDB ID or file path"},
      "confidence_threshold": {"type": "number", "default": 0.5}
    },
    "required": ["ligand_smiles", "protein_pdb_id"]
  }
}
```

**OpenAI function calling vs. Anthropic tool_use:** Both are functionally equivalent for scientific pipeline use. OpenAI's JSON schema format and Anthropic's tool_use block format are both reliable for structured output from simulation-adjacent tasks. Anthropic's tool_use is slightly more verbose but has comparable latency and reliability for long-context scientific data. Either is acceptable as the primary LLM API. For a non-US-gated lab, Anthropic Opus 4.7 + tool_use is the recommended primary LLM API given global accessibility.[^75]

***

### 6.4 Simulation Result Caching and Memoisation

For expensive MD and FEP simulations, caching by molecular content hash prevents redundant computation:

**Recommended caching pattern:**
1. Canonicalise input molecule using RDKit `Chem.MolToSmiles(Chem.MolFromSmiles(smiles), canonical=True)` to produce a canonical SMILES key
2. Hash the canonical SMILES + simulation parameters (force field, temperature, timestep) using SHA-256 to generate a cache key
3. Check cache (Redis, DynamoDB, or file-based SQLite) before submitting simulation job
4. On cache hit, retrieve stored simulation outputs and skip computation
5. Store results in structured format (HDF5 for trajectory data, JSON for scalar outputs)

The MD-HM framework (published 2021) formally validates the memoisation-based approach for MD, demonstrating average 7.6× speedup using pattern-match-based computation replacement. For an orchestration pipeline, application-level SMILES-hash caching is simpler to implement and equally effective for repeated molecule queries.[^89][^90]

**Prefect built-in caching:** Prefect natively supports task-level result caching with configurable cache keys and expiry, directly applicable to simulation task outputs.[^91]

***

### 6.5 Compute Cost Benchmarks (Approximate, Single Molecule, A100 GPU)

| Pipeline Stage | Tool | Approximate GPU Time | CPU Fallback? |
|---------------|------|--------------------|-|
| Structure prediction | Boltz-2 / Protenix | 3–10 min (GPU) | No (hours on CPU) |
| Protein-ligand docking | DiffDock V2 | 1–5 min per ligand | Yes (slower) |
| ADMET prediction | DeepChem (inference) | < 10 seconds | Yes |
| Retrosynthesis | AiZynthFinder / ASKCOS | < 1 min (CPU, template-based) | CPU-native |
| Dissolution PINN (DeepXDE) | DeepXDE | 1–2 hours training, seconds inference | Yes |
| PBPK simulation | PK-Sim | Seconds to minutes | CPU-native |
| RBFE (binding affinity) | OpenFE v1.7 | ~3 hours per ligand pair | No |
| Process flowsheet | DWSIM / PharmaPy | Minutes (CPU) | CPU-native |
| CFD (bioreactor/mixing) | OpenFOAM | Hours to days (problem size dependent) | MPI parallel |

**Minimum viable pipeline (one molecule, Layers 1–5 excluding FEP):** ~30–60 GPU-minutes total for structure → docking → ADMET → retrosynthesis → PBPK. FEP adds ~3 hours per ligand pair if binding affinity precision is required. This is the cost profile for a single candidate; virtual screening over 10,000 candidates requires horizontal GPU scaling.

***

### 6.6 Error Propagation and Uncertainty-Aware Routing

Simulation outputs carry inherent uncertainty that must propagate through the pipeline rather than being silently ignored:

**Recommended uncertainty-aware routing pattern:**
- Each simulation tool should emit a confidence/quality score alongside its primary output
- The LangGraph agent reads this score and routes to one of three paths:
  - **High confidence (above threshold):** Proceed to next layer
  - **Medium confidence (warn threshold):** Proceed with uncertainty flag, log for human review
  - **Low confidence / error:** Trigger fallback protocol (try alternative tool, reduce scope, or halt and report)
- Specific thresholds: DiffDock confidence score > 0.5 for docking acceptance; OpenFE convergence criterion (free energy bootstrapped error < 0.5 kcal/mol); PBPK model validation metric (goodness-of-fit on observed PK data)

**Failure mode taxonomy for scientific pipelines:**
1. *Tool failure*: simulation engine crash / convergence failure → retry with fallback tool
2. *Low-confidence output*: tool succeeds but confidence below threshold → flag, proceed with warning or reroute
3. *Physical impossibility*: docking produces steric clashes > threshold, molecule has >5 Lipinski violations → prune candidate, return to Layer 1
4. *Data format mismatch*: SMILES parsing error, PDB missing residues → preprocessing error, reraise with structured error message

The Parsl-based HPC integration (arXiv 2502.12280) demonstrates how async simulation task failures can be caught, logged, and handled within a LangGraph workflow without crashing the entire pipeline.[^75]

***

## Section 7: Combined Master Tool Selection

**This table supersedes Brief #1's Executive Map. It incorporates all corrections (Issues 1–6), the new Layer 2.5 (Retrosynthesis), corrected Layer 4, and all tool additions.**

| Layer | Primary Tool | Function | License Class | Interface | Commercial Outputs |
|-------|-------------|---------|--------------|-----------|-------------------|
| **L1: Molecular Simulation** | OpenMM 8.5 | GPU MD engine, ML potential integration | A (MIT) | Python | Yes |
| **L1** | GROMACS 2025 | Production MD, biopolymers | B (LGPL) | gmxapi Python | Yes |
| **L1** | MACE-MP / Allegro-FM | Equivariant NN force fields | A (MIT/Apache) | Python pip | Yes |
| **L1** | DeePMD-kit v3 | ML interatomic potentials, GROMACS integration | B (LGPL) | Python | Yes |
| **L1: Docking** | DiffDock V2 | Diffusion generative docking | A (MIT) | BioNeMo REST / Python | Yes |
| **L1: Docking** | Uni-Mol Docking v2 | 3D pretrained docking | A (MIT) | Python | Yes |
| **L1: FEP** | **OpenFE v1.7** *(new)* | RBFE + ABFE, comparable accuracy to FEP+ | A (MIT) | conda / Python | Yes |
| **L1: FEP** | **ALCHEMD** *(new)* | Automated RBFE on desktop GPU | A (open-source) | Python | Yes |
| **L1: QM** | Psi4 | Python-native QM, DFT | A (BSD) | Python | Yes |
| **L1: QM** | PySCF | Python-native QC, ML potential training data | A (Apache 2.0) | Python | Yes |
| **L1: Structure** | Boltz-2 / Protenix | Biomolecular structure + binding affinity | A (MIT/Apache) | Python / HF | Yes |
| **L1: Structure** | OpenFold3 | Full open AF3-class co-folding stack | A (Apache 2.0) | Python | Yes |
| **L2: Formulation** | RDKit 2025.09 | Cheminformatics, property prediction | A (BSD) | Python | Yes |
| **L2** | DeepChem 2.8 | ML ADMET, dissolution, SE3-equivariant | A (MIT) | Python | Yes |
| **L2** | DeepXDE 1.x *(replaces PINN entry)* | PINN dissolution modelling (Fick's law) | A (MIT) | Python | Yes |
| **L2** | Uni-Mol (DP) | 3D molecular property prediction | A (MIT) | Python / HF | Yes |
| **L2.5: Retrosynthesis** *(new layer)* | AiZynthFinder 4.3 | MCTS retrosynthesis, 73% ChEMBL coverage | A (MIT) | Python / CLI | Yes |
| **L2.5** | ASKCOS v2 (USPTO models) | Comprehensive CASP suite + condition recommendation | A (MIT) | REST API / Python | Yes |
| **L2.5** | Chemprop v2 | Forward reaction yield prediction | A (MIT) | Python | Yes |
| **L2.5** | Rxnmapper | Atom mapping for RXNSMILES | A (MIT) | Python | Yes |
| **L3: Process Dev** | DWSIM v9.0 | Open-source chemical process simulator | B (GPL) | Python COM | Yes |
| **L3** | OpenFOAM v12 | CFD: mixing, spray drying, bioreactors | B (GPL) | Python (PyFoam) | Yes |
| **L3** | LIGGGHTS / MFiX | DEM: granulation, tablet compression, powder flow | B / A (GPL/PD) | Python | Yes |
| **L3** | PharmaPy *(promoted from L4)* | Pharmaceutical manufacturing unit operations | A (MIT) | Python | Yes |
| **L4: Digital Twins** | **PharmaPy** *(corrected primary)* | Pharma-specific process physics + flowsheet | A (MIT) | Python | Yes |
| **L4** | **OpenModelica** *(replaces COPASI)* | Equation-based dynamic simulation + FMI export | B (LGPL) | Python OM API | Yes |
| **L4** | **Eclipse Ditto** *(new)* | IoT/PAT sensor digital twin data binding | B (EPL v2.0) | REST / WebSocket | Yes |
| **L4** | OpenFOAM (CFD components) | Bioreactor characterisation, heat transfer | B (GPL) | PyFoam | Yes |
| **L4** | QbDVision (SaaS, commercial) | Digital CMC QbD platform | D (Commercial) | REST API | Yes |
| **L4** | AspenPlus (commercial reference) | Full process simulation, regulatory-grade | D (Commercial) | COM Python | Yes (with license) |
| **L5: PKPD** | PK-Sim / MoBi (OSP Suite) | Full-body PBPK, regulatory-accepted | A (GPL) | R/MATLAB toolbox | Yes |
| **L5** | nlmixr2 / RxODE | Population PKPD, NONMEM-compatible | A (GPL) | R | Yes |
| **L5** | **COPASI 4.45** *(moved from L4)* | ODE/SDE biochemical network simulation | A (Artistic 2.0) | Python | Yes |
| **L5** | **Tellurium / RoadRunner** *(moved from L4)* | Python SBML simulation, ODE systems | A (Apache 2.0) | Python | Yes |
| **L5** | QSP-Copilot | Literature → SBML/mrgsolve model scaffolding | E (open, unspecified license) | Streamlit web / GitHub | Verify |
| **L6: Orchestration** | LangGraph *(upgraded from Prefect primary)* | Stateful agent graph, conditional branching | A (Apache 2.0) | Python | Yes |
| **L6** | Prefect | Workflow execution, scheduling, retries, monitoring | A (Apache 2.0) | Python | Yes |
| **L6** | Parsl | Async HPC/GPU job dispatch from Python | A (Apache 2.0) | Python | Yes |
| **L6** | Nextflow | Genomics/bioinformatics sub-workflows | A (Apache 2.0) | Groovy DSL | Yes |
| **L6: Reasoning** | GPT-5.4 + Codex Life Sciences Plugin | General scientific reasoning + 50 DB tool calls | E (API terms) | REST API | Outputs yours |
| **L6: Reasoning** | Claude Opus 4.7 | Deep scientific reasoning, globally accessible | E (API terms) | REST API (global) | Outputs yours |
| **L6: Reasoning** | TxGemma 27B *(new)* | Open-weight therapeutics-focused LLM | E (Gemma 2 terms) | Python / HF self-host | Verify terms |
| **L6: Chemistry agents** | ASKCOS v2 (as tool schema) | Retrosynthesis + condition prediction | A (MIT) | REST API | Yes |
| **L6: Chemistry agents** | ChemGraph *(new)* | LLM agent for computational chemistry workflows | Open-source | Python | Yes |

***

## Licensing Risk Flags

1. **ASKCOS v2 Reaxys model (CC BY-NC 4.0):** The 2016 Reaxys-trained template model in ASKCOS is non-commercial. Using the USPTO or Pistachio-trained models instead eliminates this restriction. The pipeline should default to non-NC models.[^51]

2. **TxGemma (Gemma 2 terms, not Apache 2.0):** Unlike Gemma 4 (Apache 2.0), TxGemma is built on Gemma 2 terms which include Google use restrictions. Verify current terms at ai.google.dev/gemma/terms before commercial deployment. Gemma 4 (Apache 2.0) may be fine-tunable as an alternative base once domain-specific fine-tuning data is available.[^45][^44]

3. **QSP-Copilot (no explicit license in GitHub repository):** The Streamlit app is open-access but the repository does not declare an OSI-approved license as of April 2026. Using the code in a commercial pipeline creates IP ambiguity. Recommended: use QSP-Copilot as a reference architecture and implement equivalent functionality under a clear open-source licence, or obtain written clarification from Boehringer Ingelheim.[^33]

4. **OpenFE SepTop dependencies:** The SepTop protocol in v1.7 introduces ABFE-style calculations that may overlap with patented alchemical transformation methods in commercial tools. OpenFE's MIT licence covers the software code; consult patent landscape before commercialising specific alchemical workflow implementations.[^23]

5. **AlphaFold 3 (Google DeepMind, restricted academic):** As noted in Brief #1, AF3 is Class C (non-commercial). OpenFold3 (Apache 2.0), Protenix (Apache 2.0), and Boltz-2 (MIT) fully supersede it for commercial pipelines.[^92][^93][^94]

6. **NAMD 3.0 (Special license):** As noted in Brief #1, NAMD requires a separate academic/commercial licence and is not freely commercial. GROMACS (LGPL) or OpenMM (MIT) are the recommended commercial alternatives for production MD.

7. **IBM RXN for Chemistry API (commercial terms):** The Python wrapper (rxn4chemistry) is open-source, but the underlying API service has commercial usage terms. Free academic tier available. For commercial pipeline use, negotiate with IBM or use AiZynthFinder/ASKCOS instead.[^59]

***

*End of Brief #2 — Companion Document*

*This document supersedes Brief #1's Executive Map (Section 7) and corrects Sections corresponding to Issues 1–6. All other sections of Brief #1 remain valid and should be read in conjunction with this document.*

---

## References

1. [A Review of Topological Data Analysis and Topological Deep ... - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12690590/) - The paper explores TDA's transformative impact across diverse domains, including biomolecular stabil...

2. [Quantum Computing in Drug Discovery Techniques, Challenges ...](https://pubmed.ncbi.nlm.nih.gov/40873222/) - Quantum computing holds great potential in drug discovery and development, offering accelerated, mor...

3. [Entropy–enthalpy transduction caused by conformational shifts can ...](https://www.pnas.org/doi/10.1073/pnas.1213180109) - Moreover, information on changes in entropy and enthalpy can usefully guide the design of improved d...

4. [Eclipse Ditto™ • open source framework for digital twins in the IoT](https://eclipse.dev/ditto/) - Eclipse Ditto is an open source framework helping you to build digital twins of devices connected to...

5. [Digital Twins - Transforming the Future of Pharma Manufacturing](https://tsquality.ch/digital-twins-transforming-the-future-of-pharma-manufacturing/) - Discover how digital twins are revolutionizing pharmaceutical manufacturing by enhancing efficiency,...

6. [FMI and TLM-Based Simulation and Co-simulation of External Models](https://openmodelica.org/doc/OpenModelicaUsersGuide/v1.15.0/fmitlm.html) - The new standard for model exchange and co-simulation with Functional Mockup Interface (FMI) allows ...

7. [Functional Mock-up Interface - FMI — OpenModelica User's Guide ...](https://openmodelica.org/doc/OpenModelicaUsersGuide/latest/fmitlm.html) - The Functional Mock-up Interface (FMI) Standard for model exchange and co-simulation allows export, ...

8. [[PDF] Chemical Process Simulation Using OpenModelica - Priyam Nayak](https://priyamnayak.com/files/unit-operations.pdf) - OpenModelica is based on the Modelica language,4,5 which enforces equation- oriented simulation stra...

9. [Chemical Process Simulation Using OpenModelica - Academia.edu](https://www.academia.edu/79576942/Chemical_Process_Simulation_Using_OpenModelica) - The equation-oriented general-purpose simulator OpenModelica provides a convenient, extendible model...

10. [Functional Mock-up Interface (FMI)](https://fmi-standard.org) - The Functional Mock-up Interface is a free standard that defines a container and an interface to exc...

11. [[PDF] aspenarserDLR - A Python-AspenPlus Interface](https://elib.dlr.de/221583/1/aspenparserdlr.pdf) - The toolbox enables automatic extraction and management of key simulation components such as streams...

12. [Academic Program for Education - AspenTech](https://www.aspentech.com/en/academic-program-for-education) - Students can access a wide range of knowledge content right from within our products: articles, vide...

13. [Aspen Plus | Leading Process Simulation Software - AspenTech](https://www.aspentech.com/en/products/engineering/aspen-plus) - Aspen Plus advances the performance of chemical processes using the best-in-class simulation softwar...

14. [Simulation-optimization framework for the digital design of pharmaceutical processes using Pyomo and PharmaPy.](https://pmc.ncbi.nlm.nih.gov/articles/PMC10765421/) - The problem of performing model-based process design and optimization in the pharmaceutical industry...

15. [CryPTSys/PharmaPy - GitHub](https://github.com/CryPTSys/PharmaPy) - PharmaPy is a pythonic library for the analysis of pharmaceutical manufacturing systems. It allows t...

16. [PharmaPy: An object-oriented tool for the development of hybrid ...](https://www.sciencedirect.com/science/article/abs/pii/S0098135421001861) - This paper introduces, PharmaPy, a Python-based modelling platform for pharmaceutical manufacturing ...

17. [[PDF] Process analysis of end-to-end continuous pharmaceutical ...](https://psecommunity.org/wp-content/plugins/wpor/includes/file/2506/LAPSE-2025.0571-1v1.pdf) - The enhanced PharmaPy framework will act as a compli- mentary open-source platform to existing comme...

18. [Drug Release Modeling using Physics-Informed Neural Networks](https://arxiv.org/html/2602.09963v1) - Classical models fit the data, but the PINN model's flexibility allows it to accommodate the nuanced...

19. [[PDF] Drug Release Modeling using Physics-Informed Neural Networks](https://arxiv.org/pdf/2602.09963.pdf) - PINNs bring greater precision and robustness to drug delivery predictions, which can drastically red...

20. [Machine Learning Based Quantitative Structure–Dissolution Profile ...](https://pubs.acs.org/doi/10.1021/acs.jcim.5c00197) - We employed DeepXDE, (64) a recently developed package tailored for PINN problems. Properly defining...

21. [DeepXDE — DeepXDE 0.1.dev1+gb8d69c431 documentation](https://deepxde.readthedocs.io) - DeepXDE is a library for scientific machine learning and physics-informed learning. DeepXDE includes...

22. [lululxvi/deepxde: A library for scientific machine learning ... - GitHub](https://github.com/lululxvi/deepxde) - DeepXDE is a library for scientific machine learning and physics-informed learning. DeepXDE includes...

23. [openfe v1.7.0: SepTop, ABFEs, faster simulations, and more!](https://openfree.energy/science/update/2025/10/23/release-v1.7/) - Using SepTop, you can calculate the difference in binding free energy between two ligands by essenti...

24. [The Open Molecular Software Foundation (OMSF) and the Growing ...](https://pubs.acs.org/doi/10.1021/acs.jcim.5c03137) - The Open Free Energy project (OpenFE) is an industry-funded project develops high-quality, open tool...

25. [Large-scale collaborative assessment of binding free energy ...](https://chemrxiv.org/doi/10.26434/chemrxiv-2025-7sthd) - Overall, these benchmark results are encouraging and indicate that OpenFE is ready for large-scale i...

26. [Preprint available: Large-scale collaborative assessment of binding ...](https://openfree.energy/science/update/publication/2025/12/19/benchmarking/) - Across over 1,700 ligands, OpenFE shows robust performance, generates reproducible results, and achi...

27. [[PDF] Open Free Energy March 2025 - Zenodo](https://zenodo.org/records/15116149/files/OpenFE_Update_March_2025.pdf?download=1) - Most outliers come from the charge annihilation subset and Merck eg5. Page 9. OpenFE and FEP+ have s...

28. [TIES 2.0: A Dual-Topology Open Source Relative Binding Free ...](https://pubs.acs.org/doi/abs/10.1021/acs.jcim.2c01596) - TIES, Thermodynamic Integration with Enhanced Sampling, is a dual-topology approach to RBFE calculat...

29. [Development and large-scale benchmarks of a protein–ligand ...](https://arxiv.org/html/2603.22274v1) - In this work, we presented Felis, an automated and scalable open-source toolkit for high-throughput ...

30. [ALCHEMD: Bridging Accessibility and Accuracy in Automated Relative Binding Free Energy Workflows.](https://pubs.acs.org/doi/10.1021/acs.jctc.5c01857) - Alchemical free energy perturbation (FEP) has emerged as one of the most accurate computational meth...

31. [QSP-Copilot: An AI-Augmented Platform for Accelerating ... - PubMed](https://pubmed.ncbi.nlm.nih.gov/41159846/) - 2025 Nov;14(11):1775-1786. doi: 10.1002/psp4.70127. Epub 2025 Oct 29. Authors. Anuraag Saini , Ali F...

32. [QSP‐Copilot: An AI‐Augmented Platform for Accelerating ... - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12625087/) - Quantitative Systems Pharmacology (QSP) is a powerful approach to provide decision‐making support th...

33. [QSP-Copilot - GitHub](https://github.com/QSP-Copilot/QSP-Copilot) - QSP-Copilot is an advanced, AI-driven platform designed to accelerate the development, validation, a...

34. [GPT-Rosalind: OpenAI's 2026 Life Sciences AI Model](https://nerdleveltech.com/openai-gpt-rosalind-life-sciences-drug-discovery) - On April 16, 2026, OpenAI introduced GPT-Rosalind, its first frontier reasoning model built exclusiv...

35. [Introducing GPT-Rosalind for life sciences research - OpenAI](https://openai.com/index/introducing-gpt-rosalind/) - OpenAI introduces GPT-Rosalind, a frontier reasoning model built to accelerate drug discovery, genom...

36. [Opus 4.7 & GPT-Rosalind: The Rise of Specialized Super-Models](https://www.youtube.com/watch?v=AwIgQqjJp4c) - From Claude Opus 4.7's 87.6% coding score to GPT-Rosalind accelerating drug discovery, the era of 'g...

37. [Introducing Claude Opus 4.7 - Anthropic](https://www.anthropic.com/news/claude-opus-4-7) - On our 93-task coding benchmark, Claude Opus 4.7 lifted resolution by 13% over Opus 4.6, including f...

38. [Claude Opus 4.7 - Anthropic](https://www.anthropic.com/claude/opus) - To get started, use claude-opus-4-7 via the Claude API. For workloads that need to run in the US, US...

39. [GPT‑Rosalind for life sciences research - Hacker News](https://news.ycombinator.com/item?id=47798244) - I couldn't find official results for Anthropic models, but I found a project taking Opus 4.6 from 65...

40. [TxGemma model card | Health AI Developer Foundations](https://developers.google.com/health-ai-developer-foundations/txgemma/model-card) - TxGemma is a collection of lightweight, state-of-the-art, open language models built upon Gemma 2, f...

41. [TxGemma - Google DeepMind](https://deepmind.google/models/gemma/txgemma/) - TxGemma is a collection of open models designed to improve the efficiency of therapeutic development...

42. [[PDF] TxGemma: Efficient and Agentic LLMs for Therapeutics - arXiv](https://arxiv.org/pdf/2504.06196.pdf) - Enabling Innovative Research with Open Models: Understanding the prevalence of proprietary data in t...

43. [[TxGemma]Finetune_with_Hugging_Face.ipynb - GitHub](https://github.com/google-gemini/gemma-cookbook/blob/main/TxGemma/%5BTxGemma%5DFinetune_with_Hugging_Face.ipynb) - This notebook demonstrates fine-tuning TxGemma models to generalize to new therapeutic development t...

44. [Gemma Terms of Use | Google AI for Developers](https://ai.google.dev/gemma/terms) - The terms below apply to Gemma models listed in the Appendix at bottom of this page. For Gemma 4 ter...

45. [What Is Gemma 4's Apache 2.0 License? Why It Matters More Than ...](https://www.mindstudio.ai/blog/gemma-4-apache-2-license-commercial-use/) - Gemma 4 ships under Apache 2.0—not a custom restricted license. Here's what that means for commercia...

46. [Open-source large-scale foundation model for chemistry](https://research.ibm.com/publications/open-source-large-scale-foundation-model-for-chemistry) - We introduce a novel family of large-scale encoder-decoder chemical foundation models, pre-trained o...

47. [AiZynthFinder 4.0: developments based on learnings from 3 years of industrial application](https://pmc.ncbi.nlm.nih.gov/articles/PMC11112899/) - We present an updated overview of the AiZynthFinder package for retrosynthesis planning. Since the f...

48. [Enhancing Monte Carlo Tree Search for Retrosynthesis](https://pubs.acs.org/doi/10.1021/acs.jcim.5c00417) - For primary testing, AiZynthFinder version 4.3 was used. The literature benchmark for the 50K ChEMBL...

49. [Human-guided synthesis planning via prompting - ScienceDirect](https://www.sciencedirect.com/org/science/article/pii/S2041652025011010) - Here, we present a novel strategy in AiZynthFinder for human-guided multistep retrosynthesis via pro...

50. [ASKCOS: an open source software suite for synthesis planning](https://arxiv.org/html/2501.01835) - The advancement of machine learning and the availability of large-scale
reaction datasets have accel...

51. [ASKCOS: an open source software suite for synthesis planning - arXiv](https://arxiv.org/html/2501.01835v1) - Here, we detail the newest version of ASKCOS, an open source software suite for synthesis planning t...

52. [ASKCOS: Open-Source, Data-Driven Synthesis Planning](https://pubs.acs.org/doi/10.1021/acs.accounts.5c00155) - All of the code associated with ASKCOS is fully open sourced under MIT licenses and is available at ...

53. [2025.07 Release Notes - ASKCOS - MIT](https://askcos-docs.mit.edu/release-notes/7.2-ASKCOS-v2/09-2025.07-Release-Notes.html) - Upgrade Information ​. ASKCOSv2 can be easily upgraded by following the instructions here. Member co...

54. [Re-evaluating Retrosynthesis Algorithms with Syntheseus](http://arxiv.org/pdf/2310.19796.pdf) - ...appearance of
steady progress, we argue that imperfect benchmarks and inconsistent
comparisons ma...

55. [Re-evaluating Retrosynthesis Algorithms with Syntheseus - Microsoft](https://www.microsoft.com/en-us/research/publication/re-evaluating-retrosynthesis-algorithms-with-syntheseus/) - We present a synthesis planning library with an extensive benchmarking framework, called syntheseus,...

56. [Science of Synthesis on IBM RXN for Chemistry](https://science-of-synthesis-datasets.thieme.com/science-of-synthesis-ibm-rxn-chemistry/) - IBM RXN for Chemistry with integrated Thieme Science of Synthesis data allows users to make more acc...

57. [IBM RXN for Chemistry](https://rxn.app.accelerate.science/rxn/) - We use cookies and other tracking technologies to improve your browsing experience on our website, t...

58. [IBM RXN for Chemistry](https://rxn.res.ibm.com/rxn/robo-rxn/welcome) - Trained to learn the art of synthetic organic chemistry, it automates synthesis procedures by conver...

59. [Python wrapper for the IBM RXN for Chemistry API - GitHub](https://github.com/rxn4chemistry/rxn4chemistry) - A python wrapper to access the API of the IBM RXN for Chemistry website. Install From PYPI: pip inst...

60. [Chemprop - GitHub](https://github.com/chemprop/chemprop) - License: MIT Downloads. Chemprop is a repository containing message passing neural networks for mole...

61. [Chemprop v2: An Efficient, Modular Machine Learning Package for ...](https://chemrxiv.org/doi/10.26434/chemrxiv-2025-4p1nr) - Accurate prediction of molecular properties is essential for computational design in many areas of c...

62. [Chemprop v2: An Efficient, Modular Machine Learning Package for ...](https://pubs.acs.org/doi/10.1021/acs.jcim.5c02332) - chemprop v2 is available under the open-source MIT License on GitHub, github.com/chemprop/chemprop, ...

63. [TeachOpenCADD - Drug Design Org](https://drugdesign.org/tutorials/teachopencadd/) - TeachOpenCADD is a resource to teach computer-aided drug design (cheminformatics and structural-bioi...

64. [TeachOpenCADD 2026.4.0.post1 documentation](https://projects.volkamerlab.org/teachopencadd/) - TeachOpenCADD is a teaching platform developed by students for students, which provides teaching mat...

65. [TeachOpenCADD: a teaching platform for computer-aided ... - GitHub](https://github.com/volkamerlab/teachopencadd) - TeachOpenCADD: a teaching platform for computer-aided drug design (CADD) using open source packages ...

66. [NVIDIA-BioNeMo-blueprints/generative-virtual-screening - GitHub](https://github.com/NVIDIA-BioNeMo-blueprints/generative-virtual-screening) - GenMol (replaces MolMIM) applies a fragment-based scheme of generation, allowing for a controlled ge...

67. [AI-Powered Molecular Docking: From DiffDock and BioNeMo to the ...](https://www.sapiosciences.com/blog/ai-powered-molecular-docking-from-diffdock-and-bionemo-to-the-next-generation-of-drug-discovery/) - Unlock the future of drug discovery with AI powered molecular docking, enhancing accuracy and reduci...

68. [Build A Generative Virtual Screening Pipeline Blueprint by NVIDIA](https://build.nvidia.com/nvidia/generative-virtual-screening-for-drug-discovery/nim) - This blueprint shows how generative AI and accelerated NIM microservices can design optimized small ...

69. [NVIDIA BioNeMo Explained: Generative AI in Drug Discovery](https://intuitionlabs.ai/articles/nvidia-bionemo-drug-discovery) - Updated 2026: Learn what NVIDIA BioNeMo is and how it accelerates drug discovery. This guide explain...

70. [Accelerating Molecular Design with AI: BioNeMo at the Frontier of ...](https://www.marvik.ai/blog/accelerating-molecular-design-with-ai-bionemo-at-the-frontier-of-biotech) - BioNeMo provides a blueprint combining AlphaFold, RFdiffusion, ProteinMPNN, and AlphaFold-Multimer f...

71. [MELLODDY: Cross-pharma Federated Learning at Unprecedented ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC11005050/) - Cross-pharma federated learning at unprecedented scale unlocks benefits in QSAR without compromising...

72. [MELLODDY: Cross-pharma Federated Learning at Unprecedented ...](https://pubs.acs.org/doi/10.1021/acs.jcim.3c00799) - In the landmark MELLODDY project, indeed, each of ten pharmaceutical companies realized aggregated i...

73. [Korea Machine Learning Ledger Orchestration For Drug Discovery](https://kmelloddy.org/english) - MELLODDY Project, which involved leading pharmaceutical companies like Merck, Pfizer, Novartis, and ...

74. [acceleratedscience/openad-toolkit: Open Accelerated ... - GitHub](https://github.com/acceleratedscience/open-ad-toolkit) - OpenAD is an intuitive toolkit that simplifies access to a variety of AI models and services for sci...

75. [Connecting Large Language Model Agent to High Performance Computing
  Resource](http://arxiv.org/pdf/2502.12280.pdf) - ...Language Model agent workflow enables the LLM to invoke tool
functions to increase the performanc...

76. [New ICH M15 Guideline sets harmonised framework for MIDD](https://www.regulatoryrapporteur.org/industry-news/new-ich-m15-guideline-sets-harmonised-framework-for-midd/1060.article) - Under M15, MIDD is defined as the strategic use of computational modelling and simulation (M&S) meth...

77. [FINAL ICH M15 Guideline: Key Implications for MIDD - Certara](https://www.certara.com/blog/redefining-regulatory-strategy-with-midd-insights-from-the-draft-ich-m15-guidance/) - With the adoption of the ICH M15 guideline in January 2026, MIDD has moved from best practice to glo...

78. [The Evolution and Future Directions of PBPK Modeling in FDA ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12655628/) - Between 2020 and 2024, the FDA approved 245 new drugs, 65 NDAs/BLAs (26.5%) submitted PBPK models as...

79. [Current Use of Physiologically Based Pharmacokinetic modeling in New Medicinal Product Approvals at EMA](https://pmc.ncbi.nlm.nih.gov/articles/PMC11835421/) - ...Based Pharmacokinetic (PBPK) Models are routinely used in drug development and therefore appear f...

80. [Harnessing Open-Source Solutions: Insights From the First Open Systems Pharmacology (OSP) Community Conference.](https://pmc.ncbi.nlm.nih.gov/articles/PMC12072215/) - ...into a diverse network of stakeholders committed to advancing open-source solutions for model-inf...

81. [Using mechanistic models to support development of complex generic drug products: European Medicines Agency perspective](https://pmc.ncbi.nlm.nih.gov/articles/PMC10196408/) - Model-informed drug development (MIDD) approaches receive wide regulatory acceptance in the European...

82. [Advancements in Virtual Bioequivalence: A Systematic Review of Computational Methods and Regulatory Perspectives in the Pharmaceutical Industry](https://pmc.ncbi.nlm.nih.gov/articles/PMC11597508/) - ...using key terms and Boolean operators ensured that extensive coverage was achieved. We adhered to...

83. [CrewAI vs LangGraph vs AutoGen: Choosing the Right Multi-Agent ...](https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen) - In this tutorial, I will walk you through a detailed comparison of three leading multi-agent AI fram...

84. [CrewAI vs LangGraph vs AutoGen vs OpenAgents (2026)](https://openagents.org/blog/posts/2026-02-23-open-source-ai-agent-frameworks-compared) - In this guide, we compare four of the most prominent open source AI agent frameworks — CrewAI, LangG...

85. [LangGraph vs CrewAI vs AutoGen: The Complete Multi-Agent AI ...](https://dev.to/pockit_tools/langgraph-vs-crewai-vs-autogen-the-complete-multi-agent-ai-orchestration-guide-for-2026-2d63) - This guide will give you the clarity you need. We'll dissect each framework's architecture, compare ...

86. [Best Multi-Agent Frameworks in 2026: LangGraph, CrewAI, OpenAI ...](https://gurusup.com/blog/best-multi-agent-frameworks-2026) - Compare the 6 leading multi-agent frameworks: OpenAI Agents SDK, LangGraph, CrewAI, AutoGen/AG2, Goo...

87. [Top AI Agent Frameworks for 2026: LangChain, CrewAI, AutoGen ...](https://www.linkedin.com/posts/sid-k09_ai-aiagents-llm-activity-7422657800725622786-rNun) - LangGraph's stateful planning is spot on for long-running agents, but the real headache hits when th...

88. [ChemGraph: An Agentic Framework for Computational Chemistry Workflows](https://arxiv.org/abs/2506.06363) - Atomistic simulations are essential tools in chemistry and materials science, accelerating the disco...

89. [[PDF] MD-HM: Memoization-based Molecular Dynamics Simulations on ...](https://par.nsf.gov/servlets/purl/10277325) - Molecular dynamics (MD) simulation computes the interaction between a collection of particles. It is...

90. [MD-HM: memoization-based molecular dynamics simulations on big ...](https://dl.acm.org/doi/abs/10.1145/3447818.3460365) - We introduce MD-HM, a memoization-based MD simulation framework customized for the big memory system...

91. [A Cloud-based Multi-Agentic Workflow for Science](https://arxiv.org/abs/2601.12607) - As Large Language Models (LLMs) become ubiquitous across various scientific domains, their lack of a...

92. [in vivo pharmacokinetic modeling of vericiguat - ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0928098725001885) - This manuscript introduces a novel, free and open-source Physiologically based biopharmaceutics mode...

93. [Pharma's Virtual Future: Digital Twins in R&D ,Manufacturing ...](https://www.linkedin.com/pulse/pharmas-virtual-future-digital-twins-rd-manufacturing-uday-shetty-z4xzf) - This report provides a scientific analysis of Digital Twin (DT) technology within the pharmaceutical...

94. [The transformative impact of AI-enabled AlphaFold 3 - PMC - NIH](https://pmc.ncbi.nlm.nih.gov/articles/PMC13099841/) - The AlphaFold Protein Structure Database (AFDB) provides open access to hundreds of millions of high...

