# Zer0pa Health Pipeline — Conventions

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.

---

## 1. Directory Layout

```
Health. Pipeline/
├── src/zer0pa_health/         # Main Python package (see §3)
├── tests/
│   ├── unit/                  # Unit tests per module
│   ├── integration/           # End-to-end pipeline tests
│   ├── falsification/         # Falsification wave (PRD §11)
│   └── plug_swap/             # Plug-replaceability tests
├── fixtures/
│   ├── compounds/             # Cardiac compound fixtures (JSON); validate against compound.schema.json
│   ├── negative/              # Deliberate failure fixtures for falsifier tests
│   ├── canned/, channels/, ecg/, fmu/, packets/, routes/, sbml/
├── schemas/
│   ├── envelope/              # layer-envelope-v1.json (JSON Schema 2020-12)
│   ├── packets/               # cardiac-evidence-packet schema
│   ├── reasoner/              # reasoner-tuple-v1.json
│   └── fixtures/              # compound.schema.json (written by subagent-2)
├── kg/                        # Knowledge graph: cardiac_seed.jsonl (33 nodes, 21 edges)
├── packets/                   # Generated cardiac evidence packets (JSON)
├── audit/                     # Append-only JSONL audit logs (runs, molecules, …)
├── docs/                      # This file + execution-report.md + DECISIONS.md
├── runtime/                   # cloud_lab.config.yaml
├── briefing-pack/             # Context briefs (read-only after handoff)
├── scripts/                   # generate_cardiac_packets.py, etc.
└── pyproject.toml             # Single source for dependencies + test config
```

All paths are repo-relative. Never reference absolute local paths in committed code.

---

## 2. Python Version

**Python 3.11** (enforced in pyproject.toml). Virtual env at `.venv/` (not committed).

Install: `python3.11 -m venv .venv && .venv/bin/pip install -e .[test]`

Test: `.venv/bin/python -m pytest -q`  (target: all tests green in < 2 s on CPU)

---

## 3. Package Layout

```
src/zer0pa_health/
├── boundary.py          # RESEARCH_BOUNDARY const + CLINICAL_OVERCLAIM_PHRASES + detectors
├── envelope.py          # LayerEnvelope (PRD §2 universal envelope)
├── ids.py               # ID generation: run_id, audit_id, packet_id, …
├── hashing.py           # sha256 hash-chain helpers (GENESIS_HASH, hash_chain_link)
├── audit/               # AuditWriter, AuditValidator, AuditValidationError, 12 record types
├── contracts/           # Per-layer Pydantic contracts (L1-L6 input/output shapes)
├── falsifiers/          # FalsifierRegistry, FalsifierLedger, 16 detect_* functions
├── kg/                  # KG schema (K1-K5 constraints), KGStore, KGValidator
├── layers/              # Adapters: l1/ l2/ l2_5/ l3/ l4/ l5/ l6/
├── packets/             # CardiacPacketAssembler, morphology_gate, PubMed harness
├── reasoner/            # Tuple schema, ReasonerQueue, ReasonerAdapter, L6Router
├── cloud_lab/           # Strateos, Emerald, Arctoris dry-run stubs
└── orchestration/       # Prefect + LangGraph + Parsl dispatch interfaces
```

---

## 4. Envelope / Contract Relationship

**Envelope** (`LayerEnvelope`) is the universal shape every layer emits:
`contract_version | research_boundary | run_id | layer | tool_adapter | output | confidence | falsifier | audit | back_edges`

**Contract** (in `contracts/`) constrains the `output` dict for a specific layer. The envelope is the chassis; the contract is the per-layer cargo spec.

- Every `output` dict must be validatable against its layer contract.
- Envelopes are emitted by adapters, consumed by L6 Router and audit trail.
- Envelope `research_boundary` must equal `RESEARCH_BOUNDARY` verbatim (Pydantic validator enforces this).

---

## 5. Falsifier Registry

16 falsifier classes are registered in `falsifiers/registry.py`. Each entry has:
`id | name | trigger_condition | backedge_target | description`

Key falsifiers for cardiac wedge:
- `herg_only_overreach` — KCNH2 present but SCN5A/KCNQ1/CACNA1C absent without `explicit_absence`
- `clinical_overclaim` — Any record contains a phrase from `CLINICAL_OVERCLAIM_PHRASES`
- `stub_laundering` — Backend=stub but output escalated to mechanism claim
- `noise_brittle_phenotype` — Phenotype claim does not survive NSTDB-style noise

Any new compound fixture **must** pass the `herg_only_overreach` check — every channel without `ic50_uM` must carry `explicit_absence`.

Falsifier evidence for clinical-overclaim **must never store** the offending phrase verbatim; use `sha256_prefix` encoding (see §10).

---

## 6. KG Schema Constraints (K1-K5)

All KG nodes and edges live in `kg/cardiac_seed.jsonl`:

| ID | Constraint |
|----|-----------|
| K1 | Every node has `node_id`, `node_type`, `label`, `research_boundary` |
| K2 | Every edge has `edge_id`, `source`, `target`, `rel`, `research_boundary`, `evidence_ids` |
| K3 | No dangling edges (source/target must be registered node_ids) |
| K4 | `evidence_ids` must reference real source manifest IDs or be empty list |
| K5 | `research_boundary` on every node and edge must equal `RESEARCH_BOUNDARY` verbatim |

Validator: `KGValidator(store).validate()` in `kg/validator.py`. Run on any KG mutation.

---

## 7. Audit Hash Chain

12 tables in `audit/` (runs, molecules, model_tools, source_manifest, parameters, confidence, falsifiers, decisions, artifacts, replay_commands, offload_manifest, midd_assessments).

Hash chain per table per run:
```
record_hash = sha256(prev_record_hash || canonical_json(payload_excluding_record_hash))
Genesis prev_record_hash = sha256("GENESIS:zer0pa_health_audit_v1")
```

Rules:
- `AuditWriter.append()` is the **only** legitimate writer. Never write JSONL lines directly.
- `AuditValidator.validate()` must pass before any run is considered complete.
- PHI markers (`patient_name`, `ssn`, `dob:`, `mrn:`, `date_of_birth`) → hard reject.
- Secret markers (`api_key=`, `bearer `, `aws_secret`, `private_key`, `password=`) → hard reject.
- Bulk local paths (`.parquet`, `.h5`, `data/raw/`) → must have `offload_ref` pointing to HF dataset.
- `research_boundary` drift → hard reject.

---

## 8. Clinical-Overclaim Sanitization Rule

When `detect_clinical_overclaim()` fires, evidence is stored as:
```json
{ "clinical_overclaim_phrase_count": N, "phrase_sha256_prefix": "<16-char hex>" }
```

**Never store the offending phrase verbatim** in any audit record — doing so would re-trip the validator on every subsequent read. The sha256 prefix preserves traceability: investigators can re-run `detect_clinical_overclaim(original_text)` to recover the phrases deterministically.

---

## 9. Backend Flag Flip as Cutover

Every GPU-bound adapter has a `backend: Backend` field. The transition from stub to real computation is a **flag flip, not an architectural rewrite**:

- `Backend.STUB` → returns canned outputs, emits `stub_laundering: PASS` (non-mechanism use)
- `Backend.RUNPOD_GPU` → delegates to Runpod REST endpoint, same envelope shape

The `stub_laundering` falsifier triggers FAIL only when `backend=stub AND claim escalates to mechanism`. Non-mechanism research use with stub backend is allowed.

Parked GPU items: DiffDock V2 (L1), OpenFE RBFE (L1), OpenMM MD (L1), DeepXDE PINN (L2), TxGemma 27B (reasoner).

---

## 10. RDKit Deferred to Runpod

RDKit is **not installed** in the originating Mac `.venv`. SMILES validation uses lightweight regex (`falsifiers/detectors.py::detect_invalid_smiles`). Canonical SMILES normalization is best-effort (literature values in fixtures).

When GPU backend activates: `pip install -e .[chem]` adds RDKit as an optional extra. The `chem` extra is listed in `pyproject.toml` but not in the default `[test]` extra.

---

## 11. No Docker on Originating Mac

The pipeline runs without Docker. All dependencies are pure Python or pip-installable. The only external service dependency is Runpod (deferred). Cloud-lab stubs (Strateos, Emerald, Arctoris) are dry-run only.

---

## 12. No Bulk Local Datasets

The repo contains only:
- Small fixture JSON files (< 10 KB each)
- KG seed JSONL (< 50 KB)
- Schemas and source-manifest metadata

Bulk data (`.parquet`, `.hdf5`, raw ECG) must be offloaded to the private HF dataset (`Architect-Prime/zer0pa-health-cardiac-v0`) and referenced by `offload_ref` in the artifacts audit table. The `.gitignore` blocks `*.parquet`, `*.h5`, and `data/raw/`.

---

## 13. License-Class Definitions

| Class | Meaning | Examples |
|-------|---------|---------|
| A | Public domain / CC0 | PubChem, ChEMBL open subsets |
| B | Creative Commons (CC-BY / CC-BY-SA) | Some PubMed open-access content |
| C | Research-only / non-commercial academic | Most model weights (TxGemma) |
| D | Commercial restrictive (SaaS API terms) | Reaxys, SciFinder |
| E | Proprietary / internal | Internal assay data |

License class is recorded on every `model_tools` and `source_manifest` audit record. Class D/E tooling triggers `license_drift` falsifier review before export.

---

## 14. Compound Fixture Convention

All compound fixtures in `fixtures/compounds/` must:
1. Pass JSON Schema validation against `schemas/fixtures/compound.schema.json`
2. Carry `research_boundary` verbatim
3. Have all four channels: `KCNH2_hERG_IKr`, `SCN5A_Nav1_5_INa_INaL`, `KCNQ1_Kv7_1_IKs`, `CACNA1C_CaV1_2_ICaL`
4. Set `explicit_absence` on any channel where `ic50_uM` is null
5. Set `expected_packet_verdict: "pass"` when all four channels are covered (value or explicit_absence)
6. State `stub_provenance_note` explaining the data source

IC50 values in stub fixtures are literature estimates, not assay results. All must be superseded by Runpod-real outputs at cutover.

---

*Last updated: 2026-04-30 by Sonnet subagent-2 (CPU-side gap closure)*
