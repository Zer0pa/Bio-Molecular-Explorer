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
}


def get_definition(cls: FalsifierClass) -> FalsifierDefinition:
    return REGISTRY[cls]


def list_definitions() -> list[FalsifierDefinition]:
    return list(REGISTRY.values())
