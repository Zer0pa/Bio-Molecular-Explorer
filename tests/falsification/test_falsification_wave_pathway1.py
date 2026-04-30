"""Pathway 1 falsification wave extension.

Deliberately triggers each of the 13 new R&D-specific falsifier classes and
verifies the system catches, audits, routes, and preserves each. Mirrors the
discipline of the existing falsification wave (tests/falsification/test_falsification_wave.py)
plus adds sanitization checks: AlphaFold AF IDs, leaked InChIKeys, and
Enamine catalogue SMILES must NOT appear verbatim in the audit ledger.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from zer0pa_health.audit import (
    AuditTable,
    AuditValidator,
    AuditWriter,
)
from zer0pa_health.envelope import FalsifierStatus
from zer0pa_health.falsifiers import (
    FalsifierClass,
    FalsifierLedger,
    detect_alphafold_d_leakage,
    detect_benchmark_leakage,
    detect_confidence_tier_overclaim,
    detect_gpt_rosalind_unavailable,
    detect_hit_from_noise,
    detect_ip_chemspace_drift,
    detect_lead_without_physchem_feasibility,
    detect_novelty_without_tractability,
    detect_pretrained_hallucination,
    detect_selectivity_not_assessed,
    detect_structure_confidence_below_threshold,
    detect_synthesis_route_absent,
    detect_target_validation_overreach,
)
from zer0pa_health.falsifiers.registry import REGISTRY
from zer0pa_health.ids import run_id


REPO_ROOT = Path(__file__).resolve().parents[2]


# ──────────────────────────────────────────────────────────────────────────
# Per-class triggers
# ──────────────────────────────────────────────────────────────────────────


@pytest.fixture
def wave_run(tmp_path):
    rid = run_id()
    aw = AuditWriter(tmp_path / "audit", rid)
    aw.append(
        AuditTable.RUNS,
        {
            "run_id": rid,
            "executor_identity": "p1-falsification-wave",
            "environment": {"mode": "deliberate_failure"},
        },
    )
    led = FalsifierLedger(tmp_path / "audit" / "runs" / rid / "falsifier_ledger.jsonl")
    return rid, aw, led, tmp_path


def _emit_and_audit(led, aw, rid, fclass: FalsifierClass, item):
    """Helper: emit to ledger + write to audit/falsifiers.jsonl."""
    led.emit(rid, fclass, "p1.wave", FalsifierStatus.FAIL, evidence=item.evidence)
    aw.append(
        AuditTable.FALSIFIERS,
        {
            "run_id": rid,
            "falsifier_id": item.falsifier_id,
            "falsifier_class": item.falsifier_class,
            "layer_scope": ["p1.wave"],
            "trigger_condition": item.trigger_condition,
            "status": "fail",
            "evidence": list(item.evidence),
        },
    )


def test_p1_wave_target_validation_overreach(wave_run):
    rid, aw, led, tmp = wave_run
    item = detect_target_validation_overreach(0.1, 1, None, False)
    assert item.status == FalsifierStatus.FAIL
    _emit_and_audit(led, aw, rid, FalsifierClass.TARGET_VALIDATION_OVERREACH, item)
    assert REGISTRY[FalsifierClass.TARGET_VALIDATION_OVERREACH].backedge_target is not None
    AuditValidator(tmp / "audit", rid).validate()


def test_p1_wave_hit_from_noise(wave_run):
    rid, aw, led, tmp = wave_run
    item = detect_hit_from_noise("CCO", 3.0, ["catechol_PAINS"], False)
    assert item.status == FalsifierStatus.FAIL
    _emit_and_audit(led, aw, rid, FalsifierClass.HIT_FROM_NOISE, item)
    AuditValidator(tmp / "audit", rid).validate()


def test_p1_wave_lead_without_physchem_feasibility(wave_run):
    rid, aw, led, tmp = wave_run
    item = detect_lead_without_physchem_feasibility(8.5, -6.0, 3, 2.0, 0.1)
    assert item.status == FalsifierStatus.FAIL
    _emit_and_audit(led, aw, rid, FalsifierClass.LEAD_WITHOUT_PHYSCHEM_FEASIBILITY, item)
    assert REGISTRY[FalsifierClass.LEAD_WITHOUT_PHYSCHEM_FEASIBILITY].severity == "soft_fail"


def test_p1_wave_novelty_without_tractability(wave_run):
    rid, aw, led, tmp = wave_run
    item = detect_novelty_without_tractability(0.2, 6.5, None)
    assert item.status == FalsifierStatus.FAIL
    _emit_and_audit(led, aw, rid, FalsifierClass.NOVELTY_WITHOUT_TRACTABILITY, item)


def test_p1_wave_ip_chemspace_drift_sanitization(wave_run):
    """Sanitization: catalogue ID may appear in evidence; matched commercial SMILES must NOT."""
    rid, aw, led, tmp = wave_run
    secret_smiles = "SECRETCHEM_CCOc1ccc2nc(S(N)(=O)=O)sc2c1"
    item = detect_ip_chemspace_drift(secret_smiles, 0.97, "ZINC000653378050", None)
    assert item.status == FalsifierStatus.FAIL
    # Catalogue ID is OK in evidence
    assert any("ZINC000653378050" in e for e in item.evidence)
    # Raw matched commercial SMILES must NOT be in evidence
    assert not any("SECRETCHEM_CCOc1ccc" in e for e in item.evidence)
    _emit_and_audit(led, aw, rid, FalsifierClass.IP_CHEMSPACE_DRIFT, item)
    AuditValidator(tmp / "audit", rid).validate()


def test_p1_wave_alphafold_d_leakage_sanitization(wave_run):
    """Sanitization: AF IDs are sha256-prefix-hashed; never echoed verbatim."""
    rid, aw, led, tmp = wave_run
    raw_af_id = "AF-P00533-F1"
    item = detect_alphafold_d_leakage("alphafold_db_precomputed", raw_af_id, None)
    assert item.status == FalsifierStatus.FAIL
    # Raw AF ID must NOT appear verbatim in evidence
    assert not any(raw_af_id in e for e in item.evidence)
    # sha256 prefix must appear
    expected_prefix = hashlib.sha256(raw_af_id.encode()).hexdigest()[:16]
    assert any(expected_prefix in e for e in item.evidence)
    _emit_and_audit(led, aw, rid, FalsifierClass.ALPHAFOLD_D_LEAKAGE, item)
    AuditValidator(tmp / "audit", rid).validate()
    assert REGISTRY[FalsifierClass.ALPHAFOLD_D_LEAKAGE].severity == "block_export"


def test_p1_wave_benchmark_leakage_sanitization(wave_run):
    """Sanitization: leaked InChIKeys are sha256-prefix-hashed; never echoed verbatim."""
    rid, aw, led, tmp = wave_run
    leaked_ik = "QNAYBMKLOCPYGJ-REOHCLBHSA-N"
    item = detect_benchmark_leakage(
        train_inchikeys={leaked_ik, "LEJRLSZVESQKJK-UHFFFAOYSA-N"},
        test_inchikeys={leaked_ik},
    )
    assert item.status == FalsifierStatus.FAIL
    # Raw InChIKey must NOT appear verbatim
    assert not any(leaked_ik in e for e in item.evidence)
    # leakage_count must appear
    assert any("leakage_count=1" in e for e in item.evidence)
    # sha256 prefix must appear
    expected_prefix = hashlib.sha256(leaked_ik.encode()).hexdigest()[:16]
    assert any(expected_prefix in e for e in item.evidence)
    _emit_and_audit(led, aw, rid, FalsifierClass.BENCHMARK_LEAKAGE, item)
    AuditValidator(tmp / "audit", rid).validate()


def test_p1_wave_pretrained_hallucination_nonorganic(wave_run):
    rid, aw, led, tmp = wave_run
    item = detect_pretrained_hallucination("C1CC[Fe]1C(=O)N", "DiffSBDD")
    assert item.status == FalsifierStatus.FAIL
    assert any("Fe" in e or "non_organic" in e for e in item.evidence)
    _emit_and_audit(led, aw, rid, FalsifierClass.PRETRAINED_HALLUCINATION, item)


def test_p1_wave_pretrained_hallucination_valence(wave_run):
    rid, aw, led, tmp = wave_run
    item = detect_pretrained_hallucination("C(C)(C)(C)(C)C", "REINVENT4")
    assert item.status == FalsifierStatus.FAIL
    assert any("valence" in e.lower() or "5+" in e for e in item.evidence)


def test_p1_wave_gpt_rosalind_unavailable(wave_run):
    rid, aw, led, tmp = wave_run
    item = detect_gpt_rosalind_unavailable(429, "biogpt", False)
    assert item.status == FalsifierStatus.FAIL
    assert REGISTRY[FalsifierClass.GPT_ROSALIND_UNAVAILABLE].severity == "soft_fail"
    _emit_and_audit(led, aw, rid, FalsifierClass.GPT_ROSALIND_UNAVAILABLE, item)


def test_p1_wave_structure_confidence_below_threshold(wave_run):
    rid, aw, led, tmp = wave_run
    item = detect_structure_confidence_below_threshold(52.3)
    assert item.status == FalsifierStatus.FAIL
    assert REGISTRY[FalsifierClass.STRUCTURE_CONFIDENCE_BELOW_THRESHOLD].severity == "confidence_cap"
    assert any("52.3" in e for e in item.evidence)
    _emit_and_audit(led, aw, rid, FalsifierClass.STRUCTURE_CONFIDENCE_BELOW_THRESHOLD, item)


def test_p1_wave_selectivity_not_assessed(wave_run):
    rid, aw, led, tmp = wave_run
    item = detect_selectivity_not_assessed(8.0, 1)
    assert item.status == FalsifierStatus.FAIL
    _emit_and_audit(led, aw, rid, FalsifierClass.SELECTIVITY_NOT_ASSESSED, item)


def test_p1_wave_synthesis_route_absent(wave_run):
    rid, aw, led, tmp = wave_run
    item = detect_synthesis_route_absent(2.5, None)
    assert item.status == FalsifierStatus.FAIL
    _emit_and_audit(led, aw, rid, FalsifierClass.SYNTHESIS_ROUTE_ABSENT, item)


def test_p1_wave_confidence_tier_overclaim(wave_run):
    rid, aw, led, tmp = wave_run
    # Tier A claimed with only 1 model
    item_a = detect_confidence_tier_overclaim("A", 1)
    assert item_a.status == FalsifierStatus.FAIL
    _emit_and_audit(led, aw, rid, FalsifierClass.CONFIDENCE_TIER_OVERCLAIM, item_a)
    # Tier B claimed with 0 models
    item_b = detect_confidence_tier_overclaim("B", 0)
    assert item_b.status == FalsifierStatus.FAIL
    _emit_and_audit(led, aw, rid, FalsifierClass.CONFIDENCE_TIER_OVERCLAIM, item_b)


# ──────────────────────────────────────────────────────────────────────────
# Aggregate wave: all 13 P1 triggers in one run, audit validates
# ──────────────────────────────────────────────────────────────────────────


def test_p1_aggregate_wave_all_caught_audited_routed_preserved(tmp_path):
    rid = run_id()
    aw = AuditWriter(tmp_path / "audit", rid)
    aw.append(
        AuditTable.RUNS,
        {
            "run_id": rid,
            "executor_identity": "p1-aggregate-wave",
            "environment": {"mode": "all_p1_triggers"},
        },
    )
    led = FalsifierLedger(tmp_path / "audit" / "runs" / rid / "falsifier_ledger.jsonl")

    triggers = [
        ("target_validation_overreach", FalsifierClass.TARGET_VALIDATION_OVERREACH,
         lambda: detect_target_validation_overreach(0.1, 1, None, False)),
        ("hit_from_noise", FalsifierClass.HIT_FROM_NOISE,
         lambda: detect_hit_from_noise("CCO", 3.0, ["pains_A"], False)),
        ("lead_without_physchem_feasibility", FalsifierClass.LEAD_WITHOUT_PHYSCHEM_FEASIBILITY,
         lambda: detect_lead_without_physchem_feasibility(8.5, -6.0, 3, 2.0, 0.1)),
        ("novelty_without_tractability", FalsifierClass.NOVELTY_WITHOUT_TRACTABILITY,
         lambda: detect_novelty_without_tractability(0.2, 6.5, None)),
        ("ip_chemspace_drift", FalsifierClass.IP_CHEMSPACE_DRIFT,
         lambda: detect_ip_chemspace_drift("CCO", 0.97, "ZINC000001", None)),
        ("alphafold_d_leakage", FalsifierClass.ALPHAFOLD_D_LEAKAGE,
         lambda: detect_alphafold_d_leakage("alphafold_db_precomputed", "AF-P00533-F1", None)),
        ("benchmark_leakage", FalsifierClass.BENCHMARK_LEAKAGE,
         lambda: detect_benchmark_leakage({"AAA-BBB-N", "CCC-DDD-N"}, {"AAA-BBB-N"})),
        ("pretrained_hallucination", FalsifierClass.PRETRAINED_HALLUCINATION,
         lambda: detect_pretrained_hallucination("C1CC[Fe]1", "DiffSBDD")),
        ("gpt_rosalind_unavailable", FalsifierClass.GPT_ROSALIND_UNAVAILABLE,
         lambda: detect_gpt_rosalind_unavailable(429, "biogpt")),
        ("structure_confidence_below_threshold", FalsifierClass.STRUCTURE_CONFIDENCE_BELOW_THRESHOLD,
         lambda: detect_structure_confidence_below_threshold(52.0)),
        ("selectivity_not_assessed", FalsifierClass.SELECTIVITY_NOT_ASSESSED,
         lambda: detect_selectivity_not_assessed(8.0, 1)),
        ("synthesis_route_absent", FalsifierClass.SYNTHESIS_ROUTE_ABSENT,
         lambda: detect_synthesis_route_absent(2.5, None)),
        ("confidence_tier_overclaim", FalsifierClass.CONFIDENCE_TIER_OVERCLAIM,
         lambda: detect_confidence_tier_overclaim("A", 1)),
    ]

    caught: list[str] = []
    routed: list[tuple[str, str]] = []

    for name, fclass, runfn in triggers:
        item = runfn()
        if item.status == FalsifierStatus.FAIL:
            caught.append(name)
        led.emit(rid, fclass, "p1.aggregate", FalsifierStatus.FAIL, evidence=item.evidence)
        aw.append(
            AuditTable.FALSIFIERS,
            {
                "run_id": rid,
                "falsifier_id": item.falsifier_id,
                "falsifier_class": item.falsifier_class,
                "layer_scope": ["p1.aggregate"],
                "trigger_condition": item.trigger_condition,
                "status": "fail",
                "evidence": list(item.evidence),
            },
        )
        target = REGISTRY[fclass].backedge_target
        if target:
            routed.append((name, target))

    counts = led.fail_count_by_class()
    for name, fclass, _ in triggers:
        assert counts.get(fclass.value, 0) >= 1, (
            f"{name} FAIL not preserved in ledger (class={fclass.value})"
        )

    AuditValidator(tmp_path / "audit", rid).validate()

    assert len(caught) == len(triggers)
    assert len(routed) == len(triggers), "every P1 falsifier must declare a backedge_target"


def test_p1_wave_combined_with_existing_wave(tmp_path):
    """Combined: existing 16-class wave + P1 13-class wave run on the same audit log."""
    from zer0pa_health.falsifiers import (
        detect_invalid_smiles,
        detect_clinical_overclaim,
        detect_herg_only_overreach,
    )

    rid = run_id()
    aw = AuditWriter(tmp_path / "audit", rid)
    aw.append(
        AuditTable.RUNS,
        {"run_id": rid, "executor_identity": "combined-wave", "environment": {}},
    )
    led = FalsifierLedger(tmp_path / "audit" / "runs" / rid / "falsifier_ledger.jsonl")

    combined_triggers = [
        ("invalid_smiles", FalsifierClass.INVALID_MOLECULAR_INPUT,
         lambda: detect_invalid_smiles("C C")),
        ("clinical_overclaim", FalsifierClass.CLINICAL_OVERCLAIM,
         lambda: detect_clinical_overclaim("This compound is FDA approved.")),
        ("herg_only", FalsifierClass.HERG_ONLY_OVERREACH,
         lambda: detect_herg_only_overreach(["KCNH2"], [])),
        ("p1_target_validation_overreach", FalsifierClass.TARGET_VALIDATION_OVERREACH,
         lambda: detect_target_validation_overreach(0.1, 1, None, False)),
        ("p1_hit_from_noise", FalsifierClass.HIT_FROM_NOISE,
         lambda: detect_hit_from_noise("CCO", 3.0, ["pains"], False)),
    ]
    for name, fclass, runfn in combined_triggers:
        item = runfn()
        led.emit(rid, fclass, "combined", FalsifierStatus.FAIL, evidence=item.evidence)
        aw.append(
            AuditTable.FALSIFIERS,
            {
                "run_id": rid,
                "falsifier_id": item.falsifier_id,
                "falsifier_class": item.falsifier_class,
                "layer_scope": ["combined"],
                "trigger_condition": item.trigger_condition,
                "status": "fail",
                "evidence": list(item.evidence),
            },
        )
    AuditValidator(tmp_path / "audit", rid).validate()
    counts = led.fail_count_by_class()
    assert counts.get(FalsifierClass.INVALID_MOLECULAR_INPUT.value, 0) >= 1
    assert counts.get(FalsifierClass.TARGET_VALIDATION_OVERREACH.value, 0) >= 1
