"""Falsifier detection helpers.

Each detector returns an `EnvelopeFalsifierItem` with status PASS/FAIL/etc.
Adapters call them inside their `process()` method and attach the items to
the envelope's falsifier list. The L6 router and the audit validator both
read the resulting items.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from typing import Any

from zer0pa_health.boundary import boundary_violations
from zer0pa_health.envelope import EnvelopeFalsifierItem, FalsifierStatus
from zer0pa_health.falsifiers.registry import FalsifierClass, get_definition
from zer0pa_health.ids import falsifier_id


_SMILES_FORBIDDEN = re.compile(r"[\s,;\\]")
_ALLOWED_SMILES_RE = re.compile(r"^[A-Za-z0-9@+\-\[\]\(\)=#$/\\.%:]+$")
_RXN_ATOMMAP_RE = re.compile(r":\d+\]")


def _item(
    fclass: FalsifierClass,
    status: FalsifierStatus,
    evidence: list[str] | None = None,
) -> EnvelopeFalsifierItem:
    defn = get_definition(fclass)
    return EnvelopeFalsifierItem(
        falsifier_id=falsifier_id(fclass.value),
        falsifier_class=fclass.value,
        trigger_condition=defn.trigger_condition,
        status=status,
        evidence=evidence or [],
    )


def detect_invalid_smiles(smiles: str) -> EnvelopeFalsifierItem:
    """Lightweight SMILES sanity check (no RDKit dependency)."""
    if not isinstance(smiles, str) or not smiles:
        return _item(FalsifierClass.INVALID_MOLECULAR_INPUT, FalsifierStatus.FAIL, ["empty SMILES"])
    if _SMILES_FORBIDDEN.search(smiles):
        return _item(
            FalsifierClass.INVALID_MOLECULAR_INPUT,
            FalsifierStatus.FAIL,
            [f"forbidden whitespace/punctuation in SMILES: {smiles!r}"],
        )
    if not _ALLOWED_SMILES_RE.match(smiles):
        return _item(
            FalsifierClass.INVALID_MOLECULAR_INPUT,
            FalsifierStatus.FAIL,
            [f"SMILES contains characters outside allowed set: {smiles!r}"],
        )
    if smiles.count("(") != smiles.count(")"):
        return _item(
            FalsifierClass.INVALID_MOLECULAR_INPUT,
            FalsifierStatus.FAIL,
            ["unbalanced parentheses in SMILES"],
        )
    if smiles.count("[") != smiles.count("]"):
        return _item(
            FalsifierClass.INVALID_MOLECULAR_INPUT,
            FalsifierStatus.FAIL,
            ["unbalanced brackets in SMILES"],
        )
    return _item(FalsifierClass.INVALID_MOLECULAR_INPUT, FalsifierStatus.PASS)


def detect_missing_rxnsmiles_atommap(
    rxnsmiles: str | None, atom_mapped: str | None, mapping_required: bool
) -> EnvelopeFalsifierItem:
    if not rxnsmiles or ">" not in rxnsmiles:
        return _item(
            FalsifierClass.MISSING_RXNSMILES_ATOMMAP,
            FalsifierStatus.FAIL,
            ["RXNSMILES missing or malformed (no '>')"],
        )
    if mapping_required:
        if not atom_mapped:
            return _item(
                FalsifierClass.MISSING_RXNSMILES_ATOMMAP,
                FalsifierStatus.FAIL,
                ["atom-mapped RXNSMILES required but absent"],
            )
        if not _RXN_ATOMMAP_RE.search(atom_mapped):
            return _item(
                FalsifierClass.MISSING_RXNSMILES_ATOMMAP,
                FalsifierStatus.FAIL,
                ["atom-mapped RXNSMILES present but contains no atom-map indices (':<n>]')"],
            )
    return _item(FalsifierClass.MISSING_RXNSMILES_ATOMMAP, FalsifierStatus.PASS)


def detect_mass_balance_failure(
    inputs_kg: float, outputs_kg: float, tolerance: float = 1e-3
) -> EnvelopeFalsifierItem:
    if inputs_kg <= 0 and outputs_kg <= 0:
        return _item(
            FalsifierClass.MASS_BALANCE_FAILURE,
            FalsifierStatus.FAIL,
            ["both input and output mass are zero"],
        )
    rel = abs(inputs_kg - outputs_kg) / max(abs(inputs_kg), 1e-12)
    if rel > tolerance:
        return _item(
            FalsifierClass.MASS_BALANCE_FAILURE,
            FalsifierStatus.FAIL,
            [f"relative residual {rel:.3e} exceeds tolerance {tolerance}"],
        )
    return _item(FalsifierClass.MASS_BALANCE_FAILURE, FalsifierStatus.PASS)


def detect_l4_sensor_failure(sensor_states: Iterable[Any]) -> EnvelopeFalsifierItem:
    bad = []
    for s in sensor_states:
        v = getattr(s, "value", None)
        in_range = getattr(s, "in_range", True)
        sid = getattr(s, "sensor_id", "?")
        if v is None:
            bad.append(f"{sid}:stale")
        elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            bad.append(f"{sid}:nonfinite")
        elif not in_range:
            bad.append(f"{sid}:out_of_range")
    if bad:
        return _item(FalsifierClass.L4_SENSOR_FAILURE, FalsifierStatus.FAIL, bad)
    return _item(FalsifierClass.L4_SENSOR_FAILURE, FalsifierStatus.PASS)


def detect_sbml_failure(
    sbml_packet: Any, required_species: int = 1, required_reactions: int = 1
) -> EnvelopeFalsifierItem:
    if sbml_packet is None:
        return _item(
            FalsifierClass.SBML_SCHEMA_FAILURE, FalsifierStatus.FAIL, ["SBML packet absent"]
        )
    species = getattr(sbml_packet, "species", []) or []
    reactions = getattr(sbml_packet, "reactions", []) or []
    if len(species) < required_species:
        return _item(
            FalsifierClass.SBML_SCHEMA_FAILURE,
            FalsifierStatus.FAIL,
            [f"SBML packet has {len(species)} species, need >= {required_species}"],
        )
    if len(reactions) < required_reactions:
        return _item(
            FalsifierClass.SBML_SCHEMA_FAILURE,
            FalsifierStatus.FAIL,
            [f"SBML packet has {len(reactions)} reactions, need >= {required_reactions}"],
        )
    return _item(FalsifierClass.SBML_SCHEMA_FAILURE, FalsifierStatus.PASS)


def detect_herg_only_overreach(
    panel_genes_present: list[str], explicit_absence: list[str]
) -> EnvelopeFalsifierItem:
    """Pass iff KCNH2 is present AND (SCN5A, KCNQ1, CACNA1C all present or in explicit_absence)."""
    required_companions = {"SCN5A", "KCNQ1", "CACNA1C"}
    panel = set(panel_genes_present)
    absence = set(explicit_absence)
    missing = required_companions - panel - absence
    if "KCNH2" in panel and missing:
        return _item(
            FalsifierClass.HERG_ONLY_OVERREACH,
            FalsifierStatus.FAIL,
            [
                f"KCNH2/hERG present but missing multi-current companions: {sorted(missing)}; "
                "no explicit_absence record either."
            ],
        )
    return _item(FalsifierClass.HERG_ONLY_OVERREACH, FalsifierStatus.PASS)


def detect_clinical_overclaim(text_blob: str) -> EnvelopeFalsifierItem:
    """Detect clinical-overclaim phrases without echoing them.

    Returns evidence as count + sha256 prefix per phrase, so that the audit
    record never re-stores a banned phrase (which would re-trip the validator).
    Investigators can rerun this detector locally to recover the original
    phrases — they are deterministic functions of the input text.
    """
    import hashlib

    violations = boundary_violations(text_blob)
    if violations:
        evidence: list[str] = [f"clinical_overclaim_phrase_count={len(violations)}"]
        for p in violations[:5]:
            digest = hashlib.sha256(p.encode("utf-8")).hexdigest()[:16]
            evidence.append(f"phrase_sha256_prefix={digest}")
        return _item(FalsifierClass.CLINICAL_OVERCLAIM, FalsifierStatus.FAIL, evidence)
    return _item(FalsifierClass.CLINICAL_OVERCLAIM, FalsifierStatus.PASS)


def detect_stub_laundering(
    backend: str, claim_kind: str, mechanism_escalation: bool
) -> EnvelopeFalsifierItem:
    """Trigger if backend == 'stub' AND output is being escalated to a mechanism claim."""
    if backend == "stub" and mechanism_escalation:
        return _item(
            FalsifierClass.STUB_LAUNDERING,
            FalsifierStatus.FAIL,
            [
                f"backend=stub but claim_kind={claim_kind!r} requires real simulation; "
                "confidence will be capped and provenance flagged."
            ],
        )
    return _item(FalsifierClass.STUB_LAUNDERING, FalsifierStatus.PASS)


def detect_missing_falsifier_ref(falsifier_refs: list[str]) -> EnvelopeFalsifierItem:
    if not falsifier_refs:
        return _item(
            FalsifierClass.MISSING_FALSIFIER_REF,
            FalsifierStatus.FAIL,
            ["claim/packet/tuple lacks any falsifier_ref"],
        )
    return _item(FalsifierClass.MISSING_FALSIFIER_REF, FalsifierStatus.PASS)


def detect_plug_replaceability_regression(
    schema_a_dump: dict, schema_b_dump: dict
) -> EnvelopeFalsifierItem:
    """Compare two adapter output schema dumps; FAIL if their JSON-Schema-ish shape diverges."""
    keys_a = sorted(schema_a_dump.keys())
    keys_b = sorted(schema_b_dump.keys())
    if keys_a != keys_b:
        return _item(
            FalsifierClass.PLUG_REGRESSION,
            FalsifierStatus.FAIL,
            [f"output keys differ: A={keys_a}, B={keys_b}"],
        )
    return _item(FalsifierClass.PLUG_REGRESSION, FalsifierStatus.PASS)


def detect_nan_or_nonfinite(values: Iterable[float], context: str = "") -> EnvelopeFalsifierItem:
    bad: list[str] = []
    for i, v in enumerate(values):
        if v is None:
            bad.append(f"{context}[{i}]:None")
        elif isinstance(v, float):
            if math.isnan(v):
                bad.append(f"{context}[{i}]:NaN")
            elif math.isinf(v):
                bad.append(f"{context}[{i}]:inf")
    if bad:
        return _item(
            FalsifierClass.NONFINITE_INPUT, FalsifierStatus.FAIL, bad[:10]
        )
    return _item(FalsifierClass.NONFINITE_INPUT, FalsifierStatus.PASS)


def detect_codec_as_mechanism(
    claim_text: str, basis_kinds: list[str]
) -> EnvelopeFalsifierItem:
    """If claim mentions mechanism but basis is only codec/replay metrics, FAIL."""
    text = claim_text.lower()
    mechanism_words = ("mechanism", "channel block", "explains", "causes", "drives")
    codec_only_kinds = {"prd", "snr", "rmse", "replay", "codec"}
    has_mechanism = any(w in text for w in mechanism_words)
    bases = {b.lower() for b in basis_kinds}
    if has_mechanism and bases and bases.issubset(codec_only_kinds):
        return _item(
            FalsifierClass.CODEC_AS_MECHANISM,
            FalsifierStatus.FAIL,
            [
                "mechanism claim with only codec/replay basis: "
                f"basis_kinds={sorted(bases)}"
            ],
        )
    return _item(FalsifierClass.CODEC_AS_MECHANISM, FalsifierStatus.PASS)


def detect_noise_brittle_phenotype(
    feature_clean: float, feature_noisy: float, max_relative_drift: float = 0.10
) -> EnvelopeFalsifierItem:
    """Phenotype must survive calibrated noise within a relative drift budget."""
    if feature_clean == 0:
        return _item(
            FalsifierClass.NOISE_BRITTLE_PHENOTYPE,
            FalsifierStatus.INCONCLUSIVE,
            ["clean feature is zero; cannot compute relative drift"],
        )
    drift = abs(feature_noisy - feature_clean) / abs(feature_clean)
    if drift > max_relative_drift:
        return _item(
            FalsifierClass.NOISE_BRITTLE_PHENOTYPE,
            FalsifierStatus.FAIL,
            [f"relative drift {drift:.3f} > {max_relative_drift}"],
        )
    return _item(FalsifierClass.NOISE_BRITTLE_PHENOTYPE, FalsifierStatus.PASS)


def detect_morphology_non_preservation(
    median_qt_error_ms: float,
    p95_qt_error_ms: float,
    median_threshold_ms: float = 5.0,
    p95_threshold_ms: float = 15.0,
) -> EnvelopeFalsifierItem:
    if math.isnan(median_qt_error_ms) or math.isnan(p95_qt_error_ms):
        return _item(
            FalsifierClass.MORPHOLOGY_NON_PRESERVATION,
            FalsifierStatus.FAIL,
            ["NaN morphology error — boundary failure"],
        )
    if median_qt_error_ms > median_threshold_ms or p95_qt_error_ms > p95_threshold_ms:
        return _item(
            FalsifierClass.MORPHOLOGY_NON_PRESERVATION,
            FalsifierStatus.FAIL,
            [
                f"QT median {median_qt_error_ms} ms > {median_threshold_ms} ms"
                if median_qt_error_ms > median_threshold_ms
                else f"QT 95th {p95_qt_error_ms} ms > {p95_threshold_ms} ms"
            ],
        )
    return _item(FalsifierClass.MORPHOLOGY_NON_PRESERVATION, FalsifierStatus.PASS)


def detect_pubmed_no_value_add(
    engine_score: float, baseline_score: float, threshold_lift: float = 10.0
) -> EnvelopeFalsifierItem:
    if engine_score - baseline_score < threshold_lift:
        return _item(
            FalsifierClass.PUBMED_BASELINE_NO_VALUE_ADD,
            FalsifierStatus.FAIL,
            [
                f"engine={engine_score} vs baseline={baseline_score}; "
                f"lift {engine_score - baseline_score} < required {threshold_lift}"
            ],
        )
    return _item(FalsifierClass.PUBMED_BASELINE_NO_VALUE_ADD, FalsifierStatus.PASS)


def detect_silent_falsifier_loss(
    upstream_falsifier_classes: list[str], current_falsifier_classes: list[str]
) -> EnvelopeFalsifierItem:
    upstream = set(upstream_falsifier_classes)
    current = set(current_falsifier_classes)
    lost = upstream - current
    if lost:
        return _item(
            FalsifierClass.SILENT_FALSIFIER_LOSS,
            FalsifierStatus.FAIL,
            [f"upstream falsifiers lost in current envelope: {sorted(lost)}"],
        )
    return _item(FalsifierClass.SILENT_FALSIFIER_LOSS, FalsifierStatus.PASS)


def detect_license_drift(
    tool_name: str, requested_variant: str, allowed_variants: list[str]
) -> EnvelopeFalsifierItem:
    if requested_variant not in allowed_variants:
        return _item(
            FalsifierClass.LICENSE_DRIFT,
            FalsifierStatus.FAIL,
            [
                f"{tool_name} variant={requested_variant!r} not in allowed list "
                f"{allowed_variants}; license posture not approved."
            ],
        )
    return _item(FalsifierClass.LICENSE_DRIFT, FalsifierStatus.PASS)
