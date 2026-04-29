"""Falsifier registry + ledger (PRD section 3 — Falsification Engine Framing).

The falsifier ledger is the spine of this system. Every layer emits falsifier
items in its envelope; the L6 router uses them to promote/downgrade/reroute/block.
The ledger persists per-run as JSONL and survives summaries/commits/handoffs.

PRD merged claim ledger requirement #6: any falsifier failure must survive
summaries, commits, handoffs, and reports.
"""

from zer0pa_health.falsifiers.registry import (
    FalsifierClass,
    FalsifierDefinition,
    REGISTRY,
    get_definition,
    list_definitions,
)
from zer0pa_health.falsifiers.ledger import FalsifierLedger
from zer0pa_health.falsifiers.detectors import (
    detect_invalid_smiles,
    detect_missing_rxnsmiles_atommap,
    detect_mass_balance_failure,
    detect_l4_sensor_failure,
    detect_sbml_failure,
    detect_herg_only_overreach,
    detect_clinical_overclaim,
    detect_stub_laundering,
    detect_missing_falsifier_ref,
    detect_plug_replaceability_regression,
    detect_nan_or_nonfinite,
    detect_codec_as_mechanism,
    detect_noise_brittle_phenotype,
    detect_morphology_non_preservation,
    detect_pubmed_no_value_add,
    detect_silent_falsifier_loss,
    detect_license_drift,
)

__all__ = [
    "FalsifierClass",
    "FalsifierDefinition",
    "REGISTRY",
    "get_definition",
    "list_definitions",
    "FalsifierLedger",
    "detect_invalid_smiles",
    "detect_missing_rxnsmiles_atommap",
    "detect_mass_balance_failure",
    "detect_l4_sensor_failure",
    "detect_sbml_failure",
    "detect_herg_only_overreach",
    "detect_clinical_overclaim",
    "detect_stub_laundering",
    "detect_missing_falsifier_ref",
    "detect_plug_replaceability_regression",
    "detect_nan_or_nonfinite",
    "detect_codec_as_mechanism",
    "detect_noise_brittle_phenotype",
    "detect_morphology_non_preservation",
    "detect_pubmed_no_value_add",
    "detect_silent_falsifier_loss",
    "detect_license_drift",
]
