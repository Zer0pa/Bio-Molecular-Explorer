"""The Falsification Wave (PRD section 11; OVERNIGHT-EXECUTOR-STARTUP-PROMPT).

Deliberately triggers each named falsifier and verifies the system:
  1. CATCHES the failure (FAIL status emitted)
  2. AUDITS it (audit record written + falsifier ledger entry)
  3. ROUTES it (back-edge proposed OR export blocked)
  4. PRESERVES it (survives envelope/packet/ledger across summaries)

The 11 named triggers (PRD overnight executor startup prompt):
  - invalid molecular input (SMILES)
  - missing RXNSMILES / atom mapping
  - mass-balance failure
  - L4 sensor stale/out-of-range
  - SBML/schema failure
  - hERG-only overreach
  - clinical-overclaim phrase
  - stub-laundering attempt
  - missing falsifier ref
  - plug-replaceability regression
  - NaN/nonfinite ECG or morphology input

Plus four additional pipeline-wide falsifiers (codec_as_mechanism,
noise_brittle_phenotype, license_drift, silent_falsifier_loss) we exercise
to demonstrate the full registry is alive.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from zer0pa_health.audit import (
    AUDIT_TABLE_FILES,
    AuditTable,
    AuditValidator,
    AuditWriter,
)
from zer0pa_health.envelope import FalsifierStatus
from zer0pa_health.falsifiers import (
    FalsifierClass,
    FalsifierLedger,
    detect_clinical_overclaim,
    detect_codec_as_mechanism,
    detect_invalid_smiles,
    detect_l4_sensor_failure,
    detect_license_drift,
    detect_mass_balance_failure,
    detect_missing_falsifier_ref,
    detect_missing_rxnsmiles_atommap,
    detect_morphology_non_preservation,
    detect_nan_or_nonfinite,
    detect_noise_brittle_phenotype,
    detect_plug_replaceability_regression,
    detect_pubmed_no_value_add,
    detect_sbml_failure,
    detect_silent_falsifier_loss,
    detect_stub_laundering,
    detect_herg_only_overreach,
)
from zer0pa_health.ids import run_id


REPO_ROOT = Path(__file__).resolve().parents[2]
NEG = REPO_ROOT / "fixtures" / "negative"
COMP = REPO_ROOT / "fixtures" / "compounds"


# ---------------- common scaffolding ----------------


@pytest.fixture
def wave_run(tmp_path):
    """Provide a fresh audit dir, ledger, and run_id for each trigger."""
    rid = run_id()
    aw = AuditWriter(tmp_path / "audit", rid)
    aw.append(
        AuditTable.RUNS,
        {
            "run_id": rid,
            "executor_identity": "falsification-wave",
            "environment": {"mode": "deliberate_failure"},
        },
    )
    led = FalsifierLedger(tmp_path / "audit" / "runs" / rid / "falsifier_ledger.jsonl")
    return rid, aw, led, tmp_path


# ---------------- trigger 1: invalid molecular input ----------------


def test_trigger_invalid_smiles(wave_run):
    rid, aw, led, _ = wave_run
    fixture = json.loads((NEG / "invalid_smiles.json").read_text())

    item = detect_invalid_smiles(fixture["smiles"])
    assert item.status == FalsifierStatus.FAIL, "must catch whitespace-in-SMILES"

    # AUDIT
    led.emit(rid, FalsifierClass.INVALID_MOLECULAR_INPUT, "L1", FalsifierStatus.FAIL,
             evidence=item.evidence)
    aw.append(AuditTable.FALSIFIERS, {
        "run_id": rid,
        "falsifier_id": item.falsifier_id,
        "falsifier_class": item.falsifier_class,
        "layer_scope": ["L1", "L2"],
        "trigger_condition": item.trigger_condition,
        "status": item.status.value,
        "evidence": item.evidence,
    })
    AuditValidator(aw.run_dir.parents[1], rid).validate()  # must still validate

    # PRESERVE: the ledger contains exactly one FAIL of this class
    counts = led.fail_count_by_class()
    assert counts[FalsifierClass.INVALID_MOLECULAR_INPUT.value] == 1


# ---------------- trigger 2: missing RXNSMILES / atom mapping ----------------


def test_trigger_missing_rxnsmiles_atommap(wave_run):
    rid, aw, led, _ = wave_run
    fixture_a = json.loads((NEG / "missing_rxnsmiles.json").read_text())
    fixture_b = json.loads((NEG / "missing_atommap.json").read_text())

    item_a = detect_missing_rxnsmiles_atommap(
        fixture_a["rxnsmiles"], fixture_a["atom_mapped_rxnsmiles"], fixture_a["mapping_required"]
    )
    item_b = detect_missing_rxnsmiles_atommap(
        fixture_b["rxnsmiles"], fixture_b["atom_mapped_rxnsmiles"], fixture_b["mapping_required"]
    )
    assert item_a.status == FalsifierStatus.FAIL
    assert item_b.status == FalsifierStatus.FAIL

    led.emit(rid, FalsifierClass.MISSING_RXNSMILES_ATOMMAP, "L2.5", FalsifierStatus.FAIL,
             evidence=item_a.evidence + item_b.evidence)
    counts = led.fail_count_by_class()
    assert counts[FalsifierClass.MISSING_RXNSMILES_ATOMMAP.value] == 1


# ---------------- trigger 3: mass-balance failure ----------------


def test_trigger_mass_balance_failure(wave_run):
    rid, aw, led, _ = wave_run
    fixture = json.loads((NEG / "mass_balance_break.json").read_text())
    item = detect_mass_balance_failure(
        fixture["inputs_kg"], fixture["outputs_kg"], fixture["tolerance"]
    )
    assert item.status == FalsifierStatus.FAIL

    led.emit(rid, FalsifierClass.MASS_BALANCE_FAILURE, "L3", FalsifierStatus.FAIL,
             evidence=item.evidence)
    assert led.fail_count_by_class()[FalsifierClass.MASS_BALANCE_FAILURE.value] == 1


# ---------------- trigger 4: L4 sensor failure ----------------


def test_trigger_l4_sensor_failure(wave_run):
    rid, aw, led, _ = wave_run
    fixture = json.loads((NEG / "l4_sensor_stale.json").read_text())

    # Build sensor objects matching the detector's expected attribute interface
    class _S:
        def __init__(self, d):
            self.sensor_id = d["sensor_id"]
            self.value = d["value"]
            self.in_range = d["in_range"]

    sensors = [_S(s) for s in fixture["sensors"]]
    item = detect_l4_sensor_failure(sensors)
    assert item.status == FalsifierStatus.FAIL
    assert any("stale" in e or "out_of_range" in e for e in item.evidence)

    led.emit(rid, FalsifierClass.L4_SENSOR_FAILURE, "L4", FalsifierStatus.FAIL,
             evidence=item.evidence)
    assert led.fail_count_by_class()[FalsifierClass.L4_SENSOR_FAILURE.value] == 1


# ---------------- trigger 5: SBML schema failure ----------------


def test_trigger_sbml_failure(wave_run):
    rid, aw, led, _ = wave_run
    fixture = json.loads((NEG / "sbml_no_species.json").read_text())

    class _Pkt:
        species = fixture["sbml_packet"]["species"]
        reactions = fixture["sbml_packet"]["reactions"]
        parameters = fixture["sbml_packet"]["parameters"]

    item = detect_sbml_failure(_Pkt(), required_species=1, required_reactions=1)
    assert item.status == FalsifierStatus.FAIL

    led.emit(rid, FalsifierClass.SBML_SCHEMA_FAILURE, "L5", FalsifierStatus.FAIL,
             evidence=item.evidence)
    assert led.fail_count_by_class()[FalsifierClass.SBML_SCHEMA_FAILURE.value] == 1


# ---------------- trigger 6: hERG-only overreach ----------------


def test_trigger_herg_only_overreach(wave_run):
    rid, aw, led, _ = wave_run
    fixture = json.loads((NEG / "herg_only_panel.json").read_text())
    item = detect_herg_only_overreach(fixture["panel_genes_present"], fixture["explicit_absence"])
    assert item.status == FalsifierStatus.FAIL
    assert "SCN5A" in str(item.evidence) or "KCNQ1" in str(item.evidence) or "CACNA1C" in str(item.evidence)

    led.emit(rid, FalsifierClass.HERG_ONLY_OVERREACH, "L1", FalsifierStatus.FAIL,
             evidence=item.evidence)
    assert led.fail_count_by_class()[FalsifierClass.HERG_ONLY_OVERREACH.value] == 1


# ---------------- trigger 7: clinical overclaim phrase ----------------


def test_trigger_clinical_overclaim(wave_run):
    rid, aw, led, _ = wave_run
    fixture = json.loads((NEG / "clinical_overclaim_text.json").read_text())
    item = detect_clinical_overclaim(fixture["text"])
    assert item.status == FalsifierStatus.FAIL
    assert len(item.evidence) >= 1  # at least one banned phrase caught

    # Must not be exportable: simulate the audit validator catching it on a record
    led.emit(rid, FalsifierClass.CLINICAL_OVERCLAIM, "L6", FalsifierStatus.FAIL,
             evidence=item.evidence)
    # AUDIT: the validator hard-fails on banned phrases inside any record's text blob
    # We do NOT write a record containing the banned phrase (that's the point — it's blocked).
    assert led.fail_count_by_class()[FalsifierClass.CLINICAL_OVERCLAIM.value] == 1


# ---------------- trigger 8: stub-laundering attempt ----------------


def test_trigger_stub_laundering(wave_run):
    rid, aw, led, _ = wave_run
    fixture = json.loads((NEG / "stub_laundering.json").read_text())
    item = detect_stub_laundering(
        fixture["backend"], fixture["claim_kind"], fixture["mechanism_escalation"]
    )
    assert item.status == FalsifierStatus.FAIL
    led.emit(rid, FalsifierClass.STUB_LAUNDERING, "L1", FalsifierStatus.FAIL,
             evidence=item.evidence)
    assert led.fail_count_by_class()[FalsifierClass.STUB_LAUNDERING.value] == 1


# ---------------- trigger 9: missing falsifier ref ----------------


def test_trigger_missing_falsifier_ref(wave_run):
    rid, aw, led, _ = wave_run
    item = detect_missing_falsifier_ref([])
    assert item.status == FalsifierStatus.FAIL
    led.emit(rid, FalsifierClass.MISSING_FALSIFIER_REF, "cardiac_packet", FalsifierStatus.FAIL,
             evidence=item.evidence)
    assert led.fail_count_by_class()[FalsifierClass.MISSING_FALSIFIER_REF.value] == 1


# ---------------- trigger 10: plug-replaceability regression ----------------


def test_trigger_plug_regression(wave_run):
    rid, aw, led, _ = wave_run
    fixture = json.loads((NEG / "plug_regression.json").read_text())
    item = detect_plug_replaceability_regression(fixture["schema_a_dump"], fixture["schema_b_dump"])
    assert item.status == FalsifierStatus.FAIL
    led.emit(rid, FalsifierClass.PLUG_REGRESSION, "L2", FalsifierStatus.FAIL,
             evidence=item.evidence)
    assert led.fail_count_by_class()[FalsifierClass.PLUG_REGRESSION.value] == 1


# ---------------- trigger 11: NaN/nonfinite ECG / morphology input ----------------


def test_trigger_nonfinite_morphology(wave_run):
    rid, aw, led, _ = wave_run
    fixture = json.loads((NEG / "nan_ecg_input.json").read_text())
    raw = fixture["ecg_features_ms"]
    parsed = []
    for k, v in raw.items():
        if v is None:
            parsed.append(None)
        elif isinstance(v, str):
            if v.lower() == "nan":
                parsed.append(float("nan"))
            elif v.lower() in ("infinity", "inf", "+inf"):
                parsed.append(float("inf"))
            else:
                parsed.append(float(v))
        else:
            parsed.append(float(v))
    finite_only = [v for v in parsed if v is not None and not math.isnan(v) and not math.isinf(v)]

    nonfinite_item = detect_nan_or_nonfinite(parsed, "ecg_features")
    assert nonfinite_item.status == FalsifierStatus.FAIL

    morph_item = detect_morphology_non_preservation(
        median_qt_error_ms=parsed[0] if parsed[0] is not None else float("nan"),
        p95_qt_error_ms=parsed[1] if parsed[1] is not None else float("nan"),
    )
    assert morph_item.status == FalsifierStatus.FAIL

    led.emit(rid, FalsifierClass.NONFINITE_INPUT, "cardiac_packet", FalsifierStatus.FAIL,
             evidence=nonfinite_item.evidence)
    led.emit(rid, FalsifierClass.MORPHOLOGY_NON_PRESERVATION, "cardiac_packet", FalsifierStatus.FAIL,
             evidence=morph_item.evidence)
    counts = led.fail_count_by_class()
    assert counts[FalsifierClass.NONFINITE_INPUT.value] == 1
    assert counts[FalsifierClass.MORPHOLOGY_NON_PRESERVATION.value] == 1


# ---------------- bonus triggers (registry coverage) ----------------


def test_trigger_codec_as_mechanism(wave_run):
    rid, aw, led, _ = wave_run
    item = detect_codec_as_mechanism(
        "this codec metric explains the channel block mechanism", ["prd", "snr", "rmse"]
    )
    assert item.status == FalsifierStatus.FAIL
    led.emit(rid, FalsifierClass.CODEC_AS_MECHANISM, "cardiac_packet", FalsifierStatus.FAIL,
             evidence=item.evidence)
    assert led.fail_count_by_class()[FalsifierClass.CODEC_AS_MECHANISM.value] == 1


def test_trigger_noise_brittle_phenotype(wave_run):
    rid, aw, led, _ = wave_run
    item = detect_noise_brittle_phenotype(
        feature_clean=400.0, feature_noisy=480.0, max_relative_drift=0.10
    )
    assert item.status == FalsifierStatus.FAIL
    led.emit(rid, FalsifierClass.NOISE_BRITTLE_PHENOTYPE, "cardiac_packet", FalsifierStatus.FAIL,
             evidence=item.evidence)
    assert led.fail_count_by_class()[FalsifierClass.NOISE_BRITTLE_PHENOTYPE.value] == 1


def test_trigger_license_drift(wave_run):
    rid, aw, led, _ = wave_run
    item = detect_license_drift("ASKCOS", "reaxys", ["uspto", "pistachio"])
    assert item.status == FalsifierStatus.FAIL
    led.emit(rid, FalsifierClass.LICENSE_DRIFT, "L2.5", FalsifierStatus.FAIL,
             evidence=item.evidence)
    assert led.fail_count_by_class()[FalsifierClass.LICENSE_DRIFT.value] == 1


def test_trigger_silent_falsifier_loss(wave_run):
    rid, aw, led, _ = wave_run
    fixture = json.loads((NEG / "silent_falsifier_loss.json").read_text())
    item = detect_silent_falsifier_loss(
        fixture["upstream_falsifier_classes"], fixture["current_falsifier_classes"]
    )
    assert item.status == FalsifierStatus.FAIL
    led.emit(rid, FalsifierClass.SILENT_FALSIFIER_LOSS, "L6", FalsifierStatus.FAIL,
             evidence=item.evidence)
    assert led.fail_count_by_class()[FalsifierClass.SILENT_FALSIFIER_LOSS.value] == 1


def test_trigger_pubmed_baseline_no_value_add(wave_run):
    rid, aw, led, _ = wave_run
    item = detect_pubmed_no_value_add(engine_score=55.0, baseline_score=49.0, threshold_lift=10.0)
    assert item.status == FalsifierStatus.FAIL
    led.emit(rid, FalsifierClass.PUBMED_BASELINE_NO_VALUE_ADD, "cardiac_packet",
             FalsifierStatus.FAIL, evidence=item.evidence)
    assert led.fail_count_by_class()[FalsifierClass.PUBMED_BASELINE_NO_VALUE_ADD.value] == 1


# ---------------- aggregate wave summary ----------------


def test_full_wave_aggregate_audit_validates(tmp_path):
    """Run the full wave through one shared AuditWriter and verify the audit log validates."""
    rid = run_id()
    aw = AuditWriter(tmp_path / "audit", rid)
    aw.append(
        AuditTable.RUNS,
        {
            "run_id": rid,
            "executor_identity": "falsification-wave-aggregate",
            "environment": {"mode": "all_triggers"},
        },
    )
    led = FalsifierLedger(tmp_path / "audit" / "runs" / rid / "falsifier_ledger.jsonl")

    triggers = [
        ("invalid_smiles", FalsifierClass.INVALID_MOLECULAR_INPUT,
         lambda: detect_invalid_smiles("C C")),
        ("missing_rxnsmiles", FalsifierClass.MISSING_RXNSMILES_ATOMMAP,
         lambda: detect_missing_rxnsmiles_atommap(None, None, True)),
        ("mass_balance", FalsifierClass.MASS_BALANCE_FAILURE,
         lambda: detect_mass_balance_failure(10.0, 12.0)),
        ("sbml", FalsifierClass.SBML_SCHEMA_FAILURE,
         lambda: detect_sbml_failure(None)),
        ("herg_only", FalsifierClass.HERG_ONLY_OVERREACH,
         lambda: detect_herg_only_overreach(["KCNH2"], [])),
        ("overclaim", FalsifierClass.CLINICAL_OVERCLAIM,
         lambda: detect_clinical_overclaim("This compound is FDA approved for atrial fibrillation.")),
        ("stub_laundering", FalsifierClass.STUB_LAUNDERING,
         lambda: detect_stub_laundering("stub", "mechanism_claim", True)),
        ("missing_falsifier_ref", FalsifierClass.MISSING_FALSIFIER_REF,
         lambda: detect_missing_falsifier_ref([])),
        ("plug_regression", FalsifierClass.PLUG_REGRESSION,
         lambda: detect_plug_replaceability_regression(
             {"a": 1, "b": 2}, {"a": 1, "c": 3}
         )),
        ("nonfinite", FalsifierClass.NONFINITE_INPUT,
         lambda: detect_nan_or_nonfinite([float("nan")], "ecg")),
        ("morphology", FalsifierClass.MORPHOLOGY_NON_PRESERVATION,
         lambda: detect_morphology_non_preservation(
             median_qt_error_ms=10.0, p95_qt_error_ms=25.0
         )),
        ("codec_as_mechanism", FalsifierClass.CODEC_AS_MECHANISM,
         lambda: detect_codec_as_mechanism("mechanism explained by codec", ["prd", "rmse"])),
        ("noise_brittle", FalsifierClass.NOISE_BRITTLE_PHENOTYPE,
         lambda: detect_noise_brittle_phenotype(400.0, 480.0)),
        ("license_drift", FalsifierClass.LICENSE_DRIFT,
         lambda: detect_license_drift("ASKCOS", "reaxys", ["uspto", "pistachio"])),
        ("silent_loss", FalsifierClass.SILENT_FALSIFIER_LOSS,
         lambda: detect_silent_falsifier_loss(
             ["hERG_only_overreach", "stub_laundering"], []
         )),
        ("pubmed_no_lift", FalsifierClass.PUBMED_BASELINE_NO_VALUE_ADD,
         lambda: detect_pubmed_no_value_add(55.0, 49.0)),
    ]

    caught = []
    audited = []
    preserved_in_ledger = []
    routed_backedge_targets = []

    for name, fclass, run in triggers:
        item = run()
        # CATCH
        if item.status == FalsifierStatus.FAIL:
            caught.append(name)
        # AUDIT (audit table + ledger)
        led.emit(rid, fclass, "wave", FalsifierStatus.FAIL, evidence=item.evidence)
        aw.append(
            AuditTable.FALSIFIERS,
            {
                "run_id": rid,
                "falsifier_id": item.falsifier_id,
                "falsifier_class": item.falsifier_class,
                "layer_scope": ["wave"],
                "trigger_condition": item.trigger_condition,
                "status": "fail",
                "evidence": item.evidence,
            },
        )
        audited.append(name)
        # ROUTE: each definition has a backedge_target
        from zer0pa_health.falsifiers.registry import REGISTRY
        target = REGISTRY[fclass].backedge_target
        if target:
            routed_backedge_targets.append((name, target))

    # PRESERVE: read the ledger back; counts must match the trigger list
    counts = led.fail_count_by_class()
    for name, fclass, _ in triggers:
        assert counts.get(fclass.value, 0) >= 1, (
            f"{name} FAIL not preserved in ledger (class={fclass.value})"
        )
        preserved_in_ledger.append(name)

    # AUDIT validator must still pass
    AuditValidator(tmp_path / "audit", rid).validate()

    # Acceptance: caught == audited == preserved == routed (count match — minus those
    # with backedge_target=None, which still must be caught/audited/preserved).
    assert len(caught) == len(triggers)
    assert len(audited) == len(triggers)
    assert len(preserved_in_ledger) == len(triggers)
    # Every trigger has a backedge_target in our REGISTRY
    assert len(routed_backedge_targets) == len(triggers), (
        "every falsifier class should have a backedge_target wired in REGISTRY"
    )
