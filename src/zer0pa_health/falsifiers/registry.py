"""Falsifier definition registry.

Combines PRD section 3 RBTE falsifiers + pipeline-wide falsifiers.
Ledger entries reference these classes; detectors return items shaped to them.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class FalsifierClass(str, Enum):
    # RBTE active falsifiers
    CODEC_AS_MECHANISM = "codec_as_mechanism"
    NOISE_BRITTLE_PHENOTYPE = "noise_brittle_phenotype"
    HERG_ONLY_OVERREACH = "hERG_only_overreach"
    CLINICAL_OVERCLAIM = "clinical_overclaim"

    # Pipeline-wide falsifiers
    NONFINITE_INPUT = "nonfinite_input"
    INVALID_MOLECULAR_INPUT = "invalid_molecular_input"
    MISSING_RXNSMILES_ATOMMAP = "missing_rxnsmiles_atommap"
    MASS_BALANCE_FAILURE = "mass_balance_failure"
    L4_SENSOR_FAILURE = "l4_sensor_failure"
    SBML_SCHEMA_FAILURE = "sbml_schema_failure"
    MORPHOLOGY_NON_PRESERVATION = "morphology_non_preservation"
    PUBMED_BASELINE_NO_VALUE_ADD = "pubmed_baseline_no_value_add"
    PLUG_REGRESSION = "plug_regression"
    SILENT_FALSIFIER_LOSS = "silent_falsifier_loss"
    STUB_LAUNDERING = "stub_laundering"
    LICENSE_DRIFT = "license_drift"
    MISSING_FALSIFIER_REF = "missing_falsifier_ref"

    # Pathway 1 — R&D / Drug Discovery extensions (PATHWAY1_PRD.md §3)
    TARGET_VALIDATION_OVERREACH = "target_validation_overreach"
    HIT_FROM_NOISE = "hit_from_noise"
    LEAD_WITHOUT_PHYSCHEM_FEASIBILITY = "lead_without_physchem_feasibility"
    NOVELTY_WITHOUT_TRACTABILITY = "novelty_without_tractability"
    IP_CHEMSPACE_DRIFT = "ip_chemspace_drift"
    ALPHAFOLD_D_LEAKAGE = "alphafold_d_leakage"
    BENCHMARK_LEAKAGE = "benchmark_leakage"
    PRETRAINED_HALLUCINATION = "pretrained_hallucination"
    GPT_ROSALIND_UNAVAILABLE = "gpt_rosalind_unavailable"
    STRUCTURE_CONFIDENCE_BELOW_THRESHOLD = "structure_confidence_below_threshold"
    SELECTIVITY_NOT_ASSESSED = "selectivity_not_assessed"
    SYNTHESIS_ROUTE_ABSENT = "synthesis_route_absent"
    CONFIDENCE_TIER_OVERCLAIM = "confidence_tier_overclaim"


class FalsifierDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    falsifier_class: FalsifierClass
    layer_scope: list[str]
    trigger_condition: str
    backedge_target: str | None = None
    severity: str  # hard_fail | soft_fail | confidence_cap | block_export
    notes: str = ""


REGISTRY: dict[FalsifierClass, FalsifierDefinition] = {
    FalsifierClass.CODEC_AS_MECHANISM: FalsifierDefinition(
        falsifier_class=FalsifierClass.CODEC_AS_MECHANISM,
        layer_scope=["L5", "L6", "cardiac_packet"],
        trigger_condition="Replay/codec metric (PRD, SNR, RMSE) is used as biological mechanism evidence",
        backedge_target="claim_demotion_to_phenotype_integrity_only",
        severity="hard_fail",
        notes="Block mechanism claim; allow only phenotype-integrity claim. RBTE F1.",
    ),
    FalsifierClass.NOISE_BRITTLE_PHENOTYPE: FalsifierDefinition(
        falsifier_class=FalsifierClass.NOISE_BRITTLE_PHENOTYPE,
        layer_scope=["cardiac_packet", "L5", "L6"],
        trigger_condition="Phenotype claim does not survive calibrated noise (NSTDB-style)",
        backedge_target="route_to_validation_and_morphology_gate",
        severity="hard_fail",
        notes="RBTE F2.",
    ),
    FalsifierClass.HERG_ONLY_OVERREACH: FalsifierDefinition(
        falsifier_class=FalsifierClass.HERG_ONLY_OVERREACH,
        layer_scope=["L1", "L5", "L6", "cardiac_packet"],
        trigger_condition="KCNH2/hERG treated as standalone risk conclusion without SCN5A/KCNQ1/CACNA1C context or explicit absence",
        backedge_target="L1_request_multi_current_panel",
        severity="hard_fail",
        notes="RBTE F3. Verapamil is the canonical refuter case.",
    ),
    FalsifierClass.CLINICAL_OVERCLAIM: FalsifierDefinition(
        falsifier_class=FalsifierClass.CLINICAL_OVERCLAIM,
        layer_scope=["L1", "L2", "L2.5", "L3", "L4", "L5", "L6", "cardiac_packet", "audit", "kg"],
        trigger_condition="Output implies diagnosis, treatment, prescribing, deployment, compliance, or certification",
        backedge_target="block_export_and_write_audit_incident",
        severity="block_export",
        notes="RBTE F4. Boundary-violating language blocks export by hard rule.",
    ),
    FalsifierClass.NONFINITE_INPUT: FalsifierDefinition(
        falsifier_class=FalsifierClass.NONFINITE_INPUT,
        layer_scope=["L1", "L2", "L2.5", "L3", "L4", "L5", "L6"],
        trigger_condition="NaN, infinity, invalid array, or otherwise non-finite numeric inputs",
        backedge_target="route_to_validation_fixture",
        severity="hard_fail",
        notes="ZPE-Bio NaN silent-failure precedent: NaN must never silently pass.",
    ),
    FalsifierClass.INVALID_MOLECULAR_INPUT: FalsifierDefinition(
        falsifier_class=FalsifierClass.INVALID_MOLECULAR_INPUT,
        layer_scope=["L1", "L2"],
        trigger_condition="SMILES does not parse, or InChIKey malformed",
        backedge_target="reject_input_with_diagnostic",
        severity="hard_fail",
    ),
    FalsifierClass.MISSING_RXNSMILES_ATOMMAP: FalsifierDefinition(
        falsifier_class=FalsifierClass.MISSING_RXNSMILES_ATOMMAP,
        layer_scope=["L2.5"],
        trigger_condition="L2.5 route step lacks RXNSMILES, or has RXNSMILES but no atom-mapping when mapping was requested",
        backedge_target="L25_re_emit_with_rxnmapper",
        severity="hard_fail",
    ),
    FalsifierClass.MASS_BALANCE_FAILURE: FalsifierDefinition(
        falsifier_class=FalsifierClass.MASS_BALANCE_FAILURE,
        layer_scope=["L3"],
        trigger_condition="L3 unit-op mass balance residual exceeds tolerance (default 1e-3 kg/kg)",
        backedge_target="L3_revise_unit_op_or_route",
        severity="hard_fail",
    ),
    FalsifierClass.L4_SENSOR_FAILURE: FalsifierDefinition(
        falsifier_class=FalsifierClass.L4_SENSOR_FAILURE,
        layer_scope=["L4"],
        trigger_condition="Sensor stale, missing, or out-of-range",
        backedge_target="L4_flag_unit_op_unmanufacturable",
        severity="hard_fail",
    ),
    FalsifierClass.SBML_SCHEMA_FAILURE: FalsifierDefinition(
        falsifier_class=FalsifierClass.SBML_SCHEMA_FAILURE,
        layer_scope=["L5"],
        trigger_condition="L5 SBML packet missing required species/reactions/parameters or roundtrip fails",
        backedge_target="L5_re_emit_with_minimal_packet",
        severity="hard_fail",
    ),
    FalsifierClass.MORPHOLOGY_NON_PRESERVATION: FalsifierDefinition(
        falsifier_class=FalsifierClass.MORPHOLOGY_NON_PRESERVATION,
        layer_scope=["cardiac_packet"],
        trigger_condition="QT/QRS/PR/ST/T fiducial error exceeds gate (median 5 ms / 95th-pct 15 ms for QT)",
        backedge_target="route_to_ECG_extraction_replay_benchmark",
        severity="hard_fail",
    ),
    FalsifierClass.PUBMED_BASELINE_NO_VALUE_ADD: FalsifierDefinition(
        falsifier_class=FalsifierClass.PUBMED_BASELINE_NO_VALUE_ADD,
        layer_scope=["L6", "cardiac_packet"],
        trigger_condition="Engine packet not at least 10 points above PubMed-reader baseline on the pre-registered benchmark",
        backedge_target="route_to_evidence_graph_contradictions_falsifier_expansion",
        severity="hard_fail",
    ),
    FalsifierClass.PLUG_REGRESSION: FalsifierDefinition(
        falsifier_class=FalsifierClass.PLUG_REGRESSION,
        layer_scope=["L1", "L2", "L2.5", "L3", "L4", "L5", "L6"],
        trigger_condition="Adapter swap changes downstream contract or breaks downstream parse",
        backedge_target="interface_contract_fix_required_before_science_continues",
        severity="hard_fail",
    ),
    FalsifierClass.SILENT_FALSIFIER_LOSS: FalsifierDefinition(
        falsifier_class=FalsifierClass.SILENT_FALSIFIER_LOSS,
        layer_scope=["L1", "L2", "L2.5", "L3", "L4", "L5", "L6", "cardiac_packet", "audit"],
        trigger_condition="Output/claim is promoted without falsifier ref",
        backedge_target="hard_fail_CI_and_packet_export",
        severity="block_export",
    ),
    FalsifierClass.STUB_LAUNDERING: FalsifierDefinition(
        falsifier_class=FalsifierClass.STUB_LAUNDERING,
        layer_scope=["L1", "L6", "cardiac_packet"],
        trigger_condition="Stub output is treated as real simulation (e.g., backend=stub but mechanism claim is escalated)",
        backedge_target="confidence_cap_and_provenance_flag_block_mechanism_escalation",
        severity="confidence_cap",
    ),
    FalsifierClass.LICENSE_DRIFT: FalsifierDefinition(
        falsifier_class=FalsifierClass.LICENSE_DRIFT,
        layer_scope=["L1", "L2", "L2.5", "L5", "L6"],
        trigger_condition="Tool/dataset terms assumed rather than checked; or non-commercial model variant used without governance",
        backedge_target="block_export_or_offload_route_to_source_manifest_update",
        severity="block_export",
        notes="ASKCOS Reaxys, TxGemma terms, Chai-1 self-host all carry license risk.",
    ),
    FalsifierClass.MISSING_FALSIFIER_REF: FalsifierDefinition(
        falsifier_class=FalsifierClass.MISSING_FALSIFIER_REF,
        layer_scope=["cardiac_packet", "L6", "kg", "reasoner"],
        trigger_condition="Claim/packet/tuple is asserted without referencing at least one falsifier",
        backedge_target="hard_fail_CI",
        severity="hard_fail",
    ),
    # ── Pathway 1 — R&D / Drug Discovery falsifiers ──────────────────────────
    FalsifierClass.TARGET_VALIDATION_OVERREACH: FalsifierDefinition(
        falsifier_class=FalsifierClass.TARGET_VALIDATION_OVERREACH,
        layer_scope=["P1.Target"],
        trigger_condition=(
            "Target promoted as druggable without all 3 evidence pillars: genetic "
            "(Open Targets/GWAS), literature (PubTator hits), structural (pocket volume or TTD entry)"
        ),
        backedge_target="P1_Target_request_expanded_evidence_panel",
        severity="hard_fail",
        notes="Single-source targets fail; all three pillars must be present or explicitly absent with justification.",
    ),
    FalsifierClass.HIT_FROM_NOISE: FalsifierDefinition(
        falsifier_class=FalsifierClass.HIT_FROM_NOISE,
        layer_scope=["P1.Generate", "P1.Screen"],
        trigger_condition="Candidate matches PAINS pattern, SA score > 6.0, or known aggregator scaffold",
        backedge_target="P1_Generate_exclude_scaffold_and_regenerate",
        severity="hard_fail",
        notes="PAINS and aggregators inflate apparent hit rates; block before any affinity score is acted on.",
    ),
    FalsifierClass.LEAD_WITHOUT_PHYSCHEM_FEASIBILITY: FalsifierDefinition(
        falsifier_class=FalsifierClass.LEAD_WITHOUT_PHYSCHEM_FEASIBILITY,
        layer_scope=["P1.Screen", "P1.Optimize"],
        trigger_condition=(
            "predicted_pIC50 >= 7.0 but ESOL < -4 OR Lipinski violations >= 2 OR hERG IC50 < 10 µM "
            "OR oral_bioavailability < 0.3"
        ),
        backedge_target="P1_Optimize_penalize_scaffold_and_trigger_optimization",
        severity="soft_fail",
        notes="Affinity alone does not make a lead. Soft-fail to allow refinement; hard-block at handoff.",
    ),
    FalsifierClass.NOVELTY_WITHOUT_TRACTABILITY: FalsifierDefinition(
        falsifier_class=FalsifierClass.NOVELTY_WITHOUT_TRACTABILITY,
        layer_scope=["P1.Generate", "P1.Screen"],
        trigger_condition=(
            "max_chembl_tanimoto < 0.4 (novel) AND (sa_score > 4.5 OR askcos_step_count is None OR > 8)"
        ),
        backedge_target="P1_Generate_reweight_generator_toward_synthesizable_space",
        severity="hard_fail",
        notes="Novelty without synthesizability is chemical fiction.",
    ),
    FalsifierClass.IP_CHEMSPACE_DRIFT: FalsifierDefinition(
        falsifier_class=FalsifierClass.IP_CHEMSPACE_DRIFT,
        layer_scope=["P1.Generate", "P1.Optimize", "P1.Handoff"],
        trigger_condition=(
            "Candidate has Tanimoto >= 0.95 to a ZINC-22/Enamine REAL Space catalogued molecule, "
            "without a documented purchase agreement reference"
        ),
        backedge_target="block_export_and_write_audit_incident",
        severity="block_export",
        notes="Enamine REAL is free for screening; commercial deliverables require purchase agreement.",
    ),
    FalsifierClass.ALPHAFOLD_D_LEAKAGE: FalsifierDefinition(
        falsifier_class=FalsifierClass.ALPHAFOLD_D_LEAKAGE,
        layer_scope=["P1.Structure", "P1.Generate", "P1.Screen", "P1.Optimize", "P1.Handoff"],
        trigger_condition=(
            "Envelope contains structure_source_tag='alphafold_db_precomputed' OR uniprot_af_id "
            "matches AF-{UniProt}-F{n} pattern without an OpenFold3 recompute provenance ref"
        ),
        backedge_target="block_export_and_write_audit_incident",
        severity="block_export",
        notes="AlphaFold DB is Class D non-commercial; production must use OpenFold3 recompute.",
    ),
    FalsifierClass.BENCHMARK_LEAKAGE: FalsifierDefinition(
        falsifier_class=FalsifierClass.BENCHMARK_LEAKAGE,
        layer_scope=["P1.Screen", "P1.Optimize"],
        trigger_condition=(
            "Training-set InChIKeys intersect with TDC ADMET (or any pre-registered) test-split InChIKeys"
        ),
        backedge_target="P1_Screen_retrain_with_clean_split_and_revalidate",
        severity="hard_fail",
        notes="Test-split leakage inflates ADMET accuracy and invalidates downstream confidence.",
    ),
    FalsifierClass.PRETRAINED_HALLUCINATION: FalsifierDefinition(
        falsifier_class=FalsifierClass.PRETRAINED_HALLUCINATION,
        layer_scope=["P1.Generate"],
        trigger_condition=(
            "Generated SMILES fails sanitization, has non-organic atoms outside whitelist, or "
            "contains valence-impossible patterns"
        ),
        backedge_target="P1_Generate_discard_molecule_and_resample",
        severity="hard_fail",
        notes="Generative models can produce chemically impossible structures under distribution shift.",
    ),
    FalsifierClass.GPT_ROSALIND_UNAVAILABLE: FalsifierDefinition(
        falsifier_class=FalsifierClass.GPT_ROSALIND_UNAVAILABLE,
        layer_scope=["P1.Target"],
        trigger_condition=(
            "GPT-Rosalind API returns non-200 status (rate-limit/region-lock/gated) or times out"
        ),
        backedge_target="P1_Target_fallback_to_biogpt_and_flag_incomplete_reasoning",
        severity="soft_fail",
        notes="Class C research preview; degrade to BioGPT/BioBERT fallback with confidence cap.",
    ),
    FalsifierClass.STRUCTURE_CONFIDENCE_BELOW_THRESHOLD: FalsifierDefinition(
        falsifier_class=FalsifierClass.STRUCTURE_CONFIDENCE_BELOW_THRESHOLD,
        layer_scope=["P1.Structure"],
        trigger_condition="Mean pLDDT over binding-site residues < 70.0",
        backedge_target="P1_Structure_request_experimental_structure_or_ensemble_sampling",
        severity="confidence_cap",
        notes="pLDDT 70 is the canonical confidence threshold; binding-site-local stricter than global.",
    ),
    FalsifierClass.SELECTIVITY_NOT_ASSESSED: FalsifierDefinition(
        falsifier_class=FalsifierClass.SELECTIVITY_NOT_ASSESSED,
        layer_scope=["P1.Screen", "P1.Optimize"],
        trigger_condition=(
            "Candidate exits L4 with primary pIC50 >= 7.0 but fewer than 3 off-target predictions logged"
        ),
        backedge_target="P1_Screen_run_selectivity_panel_before_L5_promotion",
        severity="soft_fail",
        notes="A potent compound without selectivity data is undeliverable to a CRO.",
    ),
    FalsifierClass.SYNTHESIS_ROUTE_ABSENT: FalsifierDefinition(
        falsifier_class=FalsifierClass.SYNTHESIS_ROUTE_ABSENT,
        layer_scope=["P1.Optimize", "P1.Handoff"],
        trigger_condition="SA score <= 4.0 (synthesizable) but no ASKCOS route generated/attached",
        backedge_target="P1_Handoff_run_askcos_before_export",
        severity="hard_fail",
        notes="CRO handoff requires an ASKCOS multi-step route, not just an SA score.",
    ),
    FalsifierClass.CONFIDENCE_TIER_OVERCLAIM: FalsifierDefinition(
        falsifier_class=FalsifierClass.CONFIDENCE_TIER_OVERCLAIM,
        layer_scope=["P1.Handoff"],
        trigger_condition="Tier A claimed but distinct_model_count < 3, or Tier B with count < 2",
        backedge_target="P1_Handoff_downgrade_confidence_tier_or_run_missing_models",
        severity="hard_fail",
        notes="Tier A is a verifiable claim about ensemble agreement; falsifiable error if overclaimed.",
    ),
}


def get_definition(cls: FalsifierClass) -> FalsifierDefinition:
    return REGISTRY[cls]


def list_definitions() -> list[FalsifierDefinition]:
    return list(REGISTRY.values())
