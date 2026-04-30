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


# ──────────────────────────────────────────────────────────────────────────
# Pathway 1 (R&D / Drug Discovery) — 13 detectors per PATHWAY1_PRD.md §3
# ──────────────────────────────────────────────────────────────────────────


def detect_target_validation_overreach(
    genetic_evidence_score: float,
    literature_hit_count: int,
    pocket_volume_angstrom3: float | None,
    ttd_entry_present: bool,
    *,
    genetic_threshold: float = 0.3,
    literature_threshold: int = 5,
    pocket_threshold_a3: float = 300.0,
) -> EnvelopeFalsifierItem:
    """FAIL if fewer than 2 of 3 evidence pillars are satisfied.

    Pillars: (1) genetic_evidence_score >= threshold, (2) literature_hit_count >= threshold,
    (3) pocket_volume >= threshold OR ttd_entry_present.
    """
    pillars = {
        "genetic": genetic_evidence_score >= genetic_threshold,
        "literature": literature_hit_count >= literature_threshold,
        "structural": (
            (pocket_volume_angstrom3 is not None and pocket_volume_angstrom3 >= pocket_threshold_a3)
            or ttd_entry_present
        ),
    }
    satisfied = sum(pillars.values())
    if satisfied < 2:
        missing = [name for name, ok in pillars.items() if not ok]
        return _item(
            FalsifierClass.TARGET_VALIDATION_OVERREACH,
            FalsifierStatus.FAIL,
            [
                f"satisfied_pillars={satisfied}/3",
                f"missing={missing}",
                f"genetic_evidence_score={genetic_evidence_score}",
                f"literature_hit_count={literature_hit_count}",
                f"ttd_entry_present={ttd_entry_present}",
            ],
        )
    return _item(FalsifierClass.TARGET_VALIDATION_OVERREACH, FalsifierStatus.PASS)


def detect_hit_from_noise(
    smiles: str,
    sa_score: float,
    pains_flags: list[str],
    aggregator_flag: bool,
    *,
    sa_threshold: float = 6.0,
) -> EnvelopeFalsifierItem:
    """FAIL if PAINS pattern matched OR aggregator flag set OR SA score too high."""
    if pains_flags:
        return _item(
            FalsifierClass.HIT_FROM_NOISE,
            FalsifierStatus.FAIL,
            [f"pains_flags={pains_flags[:5]}", f"sa_score={sa_score}"],
        )
    if aggregator_flag:
        return _item(
            FalsifierClass.HIT_FROM_NOISE,
            FalsifierStatus.FAIL,
            ["aggregator_classification=True", f"sa_score={sa_score}"],
        )
    if sa_score > sa_threshold:
        return _item(
            FalsifierClass.HIT_FROM_NOISE,
            FalsifierStatus.FAIL,
            [f"sa_score={sa_score}>{sa_threshold}"],
        )
    return _item(FalsifierClass.HIT_FROM_NOISE, FalsifierStatus.PASS)


def detect_lead_without_physchem_feasibility(
    predicted_pic50: float,
    esol_logs: float,
    lipinski_violations: int,
    herg_ic50_um: float,
    oral_bioavailability: float,
    *,
    pic50_threshold: float = 7.0,
) -> EnvelopeFalsifierItem:
    """FAIL if pIC50 >= threshold AND any disqualifying ADMET flag is set."""
    if predicted_pic50 < pic50_threshold:
        return _item(FalsifierClass.LEAD_WITHOUT_PHYSCHEM_FEASIBILITY, FalsifierStatus.PASS)
    issues: list[str] = []
    if esol_logs < -4.0:
        issues.append(f"ESOL={esol_logs}<-4.0")
    if lipinski_violations >= 2:
        issues.append(f"lipinski_violations={lipinski_violations}>=2")
    if herg_ic50_um < 10.0:
        issues.append(f"hERG_IC50_uM={herg_ic50_um}<10.0")
    if oral_bioavailability < 0.3:
        issues.append(f"oral_bioavailability={oral_bioavailability}<0.3")
    if issues:
        return _item(
            FalsifierClass.LEAD_WITHOUT_PHYSCHEM_FEASIBILITY,
            FalsifierStatus.FAIL,
            [f"pIC50={predicted_pic50}>={pic50_threshold}", *issues],
        )
    return _item(FalsifierClass.LEAD_WITHOUT_PHYSCHEM_FEASIBILITY, FalsifierStatus.PASS)


def detect_novelty_without_tractability(
    max_chembl_tanimoto: float,
    sa_score: float,
    askcos_step_count: int | None,
    *,
    novelty_tanimoto_threshold: float = 0.4,
    sa_threshold: float = 4.5,
    max_steps: int = 8,
) -> EnvelopeFalsifierItem:
    """FAIL if scaffold is novel (low Tanimoto to ChEMBL) AND tractability fails."""
    is_novel = max_chembl_tanimoto < novelty_tanimoto_threshold
    if not is_novel:
        return _item(FalsifierClass.NOVELTY_WITHOUT_TRACTABILITY, FalsifierStatus.PASS)
    issues: list[str] = []
    if sa_score > sa_threshold:
        issues.append(f"sa_score={sa_score}>{sa_threshold}")
    if askcos_step_count is None:
        issues.append("askcos_step_count=None (route not generated)")
    elif askcos_step_count > max_steps:
        issues.append(f"askcos_step_count={askcos_step_count}>{max_steps}")
    if issues:
        return _item(
            FalsifierClass.NOVELTY_WITHOUT_TRACTABILITY,
            FalsifierStatus.FAIL,
            [f"max_chembl_tanimoto={max_chembl_tanimoto}<{novelty_tanimoto_threshold}", *issues],
        )
    return _item(FalsifierClass.NOVELTY_WITHOUT_TRACTABILITY, FalsifierStatus.PASS)


def detect_ip_chemspace_drift(
    candidate_smiles: str,
    best_zinc22_tanimoto: float,
    zinc22_catalogue_id: str | None,
    purchase_agreement_ref: str | None,
    *,
    tanimoto_threshold: float = 0.95,
) -> EnvelopeFalsifierItem:
    """FAIL if candidate is near-exact match to a catalogued commercial molecule
    without a documented purchase agreement.

    Sanitization: never echoes the matched commercial SMILES; logs catalogue_id and
    Tanimoto only.
    """
    if best_zinc22_tanimoto >= tanimoto_threshold and purchase_agreement_ref is None:
        return _item(
            FalsifierClass.IP_CHEMSPACE_DRIFT,
            FalsifierStatus.FAIL,
            [
                f"catalogue_id={zinc22_catalogue_id}",
                f"tanimoto={best_zinc22_tanimoto:.4f}>={tanimoto_threshold}",
                "purchase_agreement_ref=None",
            ],
        )
    return _item(FalsifierClass.IP_CHEMSPACE_DRIFT, FalsifierStatus.PASS)


def detect_alphafold_d_leakage(
    structure_source_tag: str,
    uniprot_af_id: str | None,
    openfold3_run_id: str | None,
) -> EnvelopeFalsifierItem:
    """FAIL if AlphaFold DB pre-computed structure is used without OpenFold3 recompute provenance.

    Sanitization: AF IDs are sha256-prefix-hashed in evidence; never echoed verbatim.
    """
    import hashlib
    import re

    af_pattern = re.compile(r"^AF-[A-Z0-9]+-F\d+$")
    is_af_db = (
        structure_source_tag == "alphafold_db_precomputed"
        or (uniprot_af_id is not None and af_pattern.match(uniprot_af_id) is not None)
    )
    if is_af_db and openfold3_run_id is None:
        evidence = ["structure_source_alphafold_db_precomputed", "openfold3_run_id=None"]
        if uniprot_af_id:
            digest = hashlib.sha256(uniprot_af_id.encode("utf-8")).hexdigest()[:16]
            evidence.append(f"af_id_sha256_prefix={digest}")
        return _item(FalsifierClass.ALPHAFOLD_D_LEAKAGE, FalsifierStatus.FAIL, evidence)
    return _item(FalsifierClass.ALPHAFOLD_D_LEAKAGE, FalsifierStatus.PASS)


def detect_benchmark_leakage(
    train_inchikeys: set[str],
    test_inchikeys: set[str],
) -> EnvelopeFalsifierItem:
    """FAIL if training set intersects a held-out test split (TDC ADMET, etc.).

    Sanitization: leaked InChIKeys are sha256-prefix-hashed; never echoed verbatim.
    """
    import hashlib

    leaked = sorted(train_inchikeys & test_inchikeys)
    if leaked:
        evidence = [f"leakage_count={len(leaked)}"]
        for ik in leaked[:5]:
            digest = hashlib.sha256(ik.encode("utf-8")).hexdigest()[:16]
            evidence.append(f"leaked_inchikey_sha256_prefix={digest}")
        return _item(FalsifierClass.BENCHMARK_LEAKAGE, FalsifierStatus.FAIL, evidence)
    return _item(FalsifierClass.BENCHMARK_LEAKAGE, FalsifierStatus.PASS)


_ALLOWED_ORGANIC_ATOMS = frozenset({"C", "N", "O", "S", "P", "F", "Cl", "Br", "I", "H"})


def detect_pretrained_hallucination(
    smiles: str,
    generation_method: str,
    *,
    allowed_atoms: frozenset[str] | None = None,
) -> EnvelopeFalsifierItem:
    """FAIL on chemically impossible SMILES (broken brackets/parens, non-organic atoms,
    obvious valence breaks)."""
    if not isinstance(smiles, str) or not smiles:
        return _item(
            FalsifierClass.PRETRAINED_HALLUCINATION,
            FalsifierStatus.FAIL,
            ["empty SMILES"],
        )
    if smiles.count("(") != smiles.count(")") or smiles.count("[") != smiles.count("]"):
        return _item(
            FalsifierClass.PRETRAINED_HALLUCINATION,
            FalsifierStatus.FAIL,
            [
                f"unbalanced bracket/paren in SMILES",
                f"generation_method={generation_method}",
            ],
        )
    allowed = allowed_atoms or _ALLOWED_ORGANIC_ATOMS
    # Bracketed atoms: extract inside [ ... ]
    import re

    bracketed = re.findall(r"\[([A-Z][a-z]?)", smiles)
    for atom in bracketed:
        if atom not in allowed:
            return _item(
                FalsifierClass.PRETRAINED_HALLUCINATION,
                FalsifierStatus.FAIL,
                [
                    f"non_organic_atom={atom!r}",
                    f"allowed_whitelist={sorted(allowed)}",
                    f"generation_method={generation_method}",
                ],
            )
    # Heuristic valence break: same atom with 5 explicit bonds in a ring closure pattern
    # e.g., C(C)(C)(C)(C)C — five branches off carbon
    if re.search(r"C\(C\)\(C\)\(C\)\(C\)", smiles):
        return _item(
            FalsifierClass.PRETRAINED_HALLUCINATION,
            FalsifierStatus.FAIL,
            [
                "valence_break_heuristic: 5+ explicit bonds on carbon",
                f"generation_method={generation_method}",
            ],
        )
    return _item(FalsifierClass.PRETRAINED_HALLUCINATION, FalsifierStatus.PASS)


def detect_gpt_rosalind_unavailable(
    api_http_status: int | None,
    fallback_used: str | None,
    timeout_occurred: bool = False,
) -> EnvelopeFalsifierItem:
    """soft_fail (FAIL status) if GPT-Rosalind API is unreachable or non-2xx."""
    if api_http_status is None or timeout_occurred:
        return _item(
            FalsifierClass.GPT_ROSALIND_UNAVAILABLE,
            FalsifierStatus.FAIL,
            [
                "api_http_status=None_or_timeout",
                f"timeout_occurred={timeout_occurred}",
                f"fallback_used={fallback_used or 'none'}",
            ],
        )
    if api_http_status not in (200, 201):
        return _item(
            FalsifierClass.GPT_ROSALIND_UNAVAILABLE,
            FalsifierStatus.FAIL,
            [
                f"api_http_status={api_http_status}",
                f"fallback_used={fallback_used or 'none'}",
            ],
        )
    return _item(FalsifierClass.GPT_ROSALIND_UNAVAILABLE, FalsifierStatus.PASS)


def detect_structure_confidence_below_threshold(
    binding_site_mean_plddt: float,
    *,
    plddt_threshold: float = 70.0,
    structure_source: str = "openfold3",
) -> EnvelopeFalsifierItem:
    """confidence_cap (FAIL status) if binding-site mean pLDDT below threshold."""
    if binding_site_mean_plddt < plddt_threshold:
        return _item(
            FalsifierClass.STRUCTURE_CONFIDENCE_BELOW_THRESHOLD,
            FalsifierStatus.FAIL,
            [
                f"binding_site_mean_plddt={binding_site_mean_plddt}<{plddt_threshold}",
                f"structure_source={structure_source}",
            ],
        )
    return _item(FalsifierClass.STRUCTURE_CONFIDENCE_BELOW_THRESHOLD, FalsifierStatus.PASS)


def detect_selectivity_not_assessed(
    primary_pic50: float,
    off_target_prediction_count: int,
    *,
    pic50_threshold: float = 7.0,
    min_off_target_count: int = 3,
) -> EnvelopeFalsifierItem:
    """soft_fail (FAIL status) if potent compound has insufficient off-target screening."""
    if primary_pic50 >= pic50_threshold and off_target_prediction_count < min_off_target_count:
        return _item(
            FalsifierClass.SELECTIVITY_NOT_ASSESSED,
            FalsifierStatus.FAIL,
            [
                f"primary_pic50={primary_pic50}>={pic50_threshold}",
                f"off_target_prediction_count={off_target_prediction_count}<{min_off_target_count}",
            ],
        )
    return _item(FalsifierClass.SELECTIVITY_NOT_ASSESSED, FalsifierStatus.PASS)


def detect_synthesis_route_absent(
    sa_score: float,
    askcos_route_steps: list | None,
    *,
    sa_threshold: float = 4.0,
) -> EnvelopeFalsifierItem:
    """FAIL if SA score indicates synthesizable but no ASKCOS route was generated/attached."""
    if sa_score <= sa_threshold and (askcos_route_steps is None or len(askcos_route_steps) == 0):
        return _item(
            FalsifierClass.SYNTHESIS_ROUTE_ABSENT,
            FalsifierStatus.FAIL,
            [
                f"sa_score={sa_score}<={sa_threshold}",
                f"askcos_route_steps={'None' if askcos_route_steps is None else 'empty'}",
            ],
        )
    return _item(FalsifierClass.SYNTHESIS_ROUTE_ABSENT, FalsifierStatus.PASS)


def detect_confidence_tier_overclaim(
    assigned_tier: str,
    distinct_model_count: int,
) -> EnvelopeFalsifierItem:
    """FAIL on Tier A with < 3 models, or Tier B with < 2 models."""
    tier = assigned_tier.upper()
    if tier == "A" and distinct_model_count < 3:
        return _item(
            FalsifierClass.CONFIDENCE_TIER_OVERCLAIM,
            FalsifierStatus.FAIL,
            [f"assigned_tier=A but distinct_model_count={distinct_model_count}<3"],
        )
    if tier == "B" and distinct_model_count < 2:
        return _item(
            FalsifierClass.CONFIDENCE_TIER_OVERCLAIM,
            FalsifierStatus.FAIL,
            [f"assigned_tier=B but distinct_model_count={distinct_model_count}<2"],
        )
    return _item(FalsifierClass.CONFIDENCE_TIER_OVERCLAIM, FalsifierStatus.PASS)
