"""Tests for the cardiac evidence packet (PRD section 7)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from zer0pa_health.packets import (
    BaselineHarness,
    CardiacPacketAssembler,
    PacketVerdict,
    morphology_gate,
    score_baseline_for_compound,
    score_packet,
)
from zer0pa_health.packets.assembler import AssemblerInputs
from zer0pa_health.packets.morphology_gate import MorphologyResult


REPO_ROOT = Path(__file__).resolve().parents[2]
FIX = REPO_ROOT / "fixtures" / "compounds"


# ---------------- morphology gate ----------------


def test_morphology_qt_pass():
    res = morphology_gate("QT", [1.0, 2.0, 3.0, 4.0, 5.0])
    assert res.passed is True
    assert res.median_abs_error_ms == 3.0
    assert not res.nan_or_nonfinite_present


def test_morphology_qt_fail_on_p95():
    # median is 5 ms but p95 is high
    res = morphology_gate("QT", [1.0, 2.0, 3.0, 4.0, 5.0, 25.0])
    assert res.passed is False
    assert res.p95_abs_error_ms > res.p95_threshold_ms


def test_morphology_nan_blocks():
    res = morphology_gate("QT", [1.0, float("nan"), 3.0])
    assert res.passed is False
    assert res.nan_or_nonfinite_present is True


def test_morphology_inf_blocks():
    res = morphology_gate("QT", [1.0, float("inf"), 3.0])
    assert res.passed is False
    assert res.nan_or_nonfinite_present is True


def test_morphology_unknown_fiducial_requires_thresholds():
    with pytest.raises(ValueError):
        morphology_gate("UNKNOWN", [1.0])


# ---------------- packet assembly ----------------


def test_assemble_dofetilide_packet():
    asm = CardiacPacketAssembler()
    inputs = AssemblerInputs(
        compound_fixture_path=FIX / "dofetilide.json",
        cmax_unbound_uM=0.001,
        morphology_errors_ms={"QT": [1.0, 2.0, 3.0, 2.5]},
    )
    packet, diag = asm.assemble(inputs)
    assert packet.compound.name == "dofetilide"
    assert packet.verdict == PacketVerdict.PASS
    assert packet.channel_panel.KCNH2_hERG_IKr.ic50_uM is not None
    assert packet.channel_panel.SCN5A_Nav1_5_INa_INaL.explicit_absence is not None
    assert packet.ecg_morphology_bridge.multi_current_balance_score is not None
    # IKr block dominant for dofetilide → balance score positive
    assert packet.ecg_morphology_bridge.multi_current_balance_score > 0
    # Required falsifier classes present
    klasses = {f["falsifier_class"] for f in packet.falsifiers}
    assert {"hERG_only_overreach", "clinical_overclaim", "codec_as_mechanism"} <= klasses


def test_assemble_verapamil_packet_balance_lower_than_dofetilide():
    asm = CardiacPacketAssembler()
    dofet, _ = asm.assemble(
        AssemblerInputs(
            compound_fixture_path=FIX / "dofetilide.json",
            cmax_unbound_uM=0.001,
            morphology_errors_ms={"QT": [1.0, 2.0, 3.0]},
        )
    )
    verap, _ = asm.assemble(
        AssemblerInputs(
            compound_fixture_path=FIX / "verapamil.json",
            cmax_unbound_uM=0.05,  # higher therapeutic exposure
            morphology_errors_ms={"QT": [1.0, 2.0, 3.0]},
        )
    )
    assert verap.compound.name == "verapamil"
    # Verapamil's ICaL block compensates → balance score lower than dofetilide
    assert (
        verap.ecg_morphology_bridge.multi_current_balance_score
        < dofet.ecg_morphology_bridge.multi_current_balance_score
    )
    # Verapamil packet must include the contradiction (low TdP despite hERG block)
    assert any("verapamil" in c.contradiction_id for c in verap.contradictions)


def test_assemble_ranolazine_engages_INaL():
    asm = CardiacPacketAssembler()
    packet, _ = asm.assemble(
        AssemblerInputs(
            compound_fixture_path=FIX / "ranolazine.json",
            cmax_unbound_uM=2.0,
            morphology_errors_ms={"QT": [1.0, 2.5, 3.5]},
        )
    )
    inaL = packet.channel_panel.SCN5A_Nav1_5_INa_INaL
    assert inaL.ic50_uM is not None
    assert inaL.confidence > 0.0
    # Multi-current claim text mentions INaL
    assert any("INaL" in c.text or "late-INa" in c.text for c in packet.claims)


def test_packet_pubmed_baseline_pass():
    asm = CardiacPacketAssembler()
    packet, _ = asm.assemble(
        AssemblerInputs(
            compound_fixture_path=FIX / "dofetilide.json",
            cmax_unbound_uM=0.001,
            morphology_errors_ms={"QT": [1.0, 2.0, 3.0, 2.5]},
        )
    )
    engine = score_packet(packet)
    baseline = score_baseline_for_compound(packet.compound.name)
    assert engine.total >= 60.0  # CPU-side stub should at least clear baseline by some margin
    # Lift over baseline must be positive on this stub (audit_replay + falsifier_coverage are big wins)
    assert engine.total - baseline.total > 0.0
    # Required falsifier coverage at least 75% (3 of 4 cardiac falsifiers present + missing_falsifier_ref)
    assert engine.falsifier_coverage >= 75.0


def test_baseline_harness_returns_one_row_per_packet():
    asm = CardiacPacketAssembler()
    packets = []
    for c in ("dofetilide", "verapamil", "ranolazine"):
        p, _ = asm.assemble(
            AssemblerInputs(
                compound_fixture_path=FIX / f"{c}.json",
                cmax_unbound_uM=0.005,
                morphology_errors_ms={"QT": [1.0, 2.0, 3.0]},
            )
        )
        packets.append(p)
    rows = BaselineHarness().evaluate(packets)
    assert len(rows) == 3
    # Engine totals must be deterministic
    asm2 = CardiacPacketAssembler()
    rows2 = BaselineHarness().evaluate(
        [
            asm2.assemble(
                AssemblerInputs(
                    compound_fixture_path=FIX / f"{c}.json",
                    cmax_unbound_uM=0.005,
                    morphology_errors_ms={"QT": [1.0, 2.0, 3.0]},
                )
            )[0]
            for c in ("dofetilide", "verapamil", "ranolazine")
        ]
    )
    for r1, r2 in zip(rows, rows2):
        assert math.isclose(r1[0].total, r2[0].total, rel_tol=1e-9)


def test_packet_clinical_overclaim_blocks_export():
    """Construct a malformed claim text with a banned phrase; Pydantic must reject it."""
    from zer0pa_health.packets.schema import PacketClaim

    with pytest.raises(ValueError):
        PacketClaim(
            claim_id="claim:bad",
            text="This compound is FDA approved for ventricular arrhythmia.",
            multi_current_context=True,
            source_refs=["source:any"],
            falsifier_refs=["falsifier:any"],
            audit_refs=["audit:any"],
            confidence_band="high",
        )


def test_packet_verdict_blocked_when_morphology_nan():
    asm = CardiacPacketAssembler()
    packet, _ = asm.assemble(
        AssemblerInputs(
            compound_fixture_path=FIX / "dofetilide.json",
            cmax_unbound_uM=0.001,
            morphology_errors_ms={"QT": [1.0, float("nan"), 3.0]},
        )
    )
    # The morphology falsifier should fail because median/p95 are NaN
    morph_f = next(
        (f for f in packet.falsifiers if f["falsifier_class"] == "morphology_non_preservation"),
        None,
    )
    assert morph_f is not None
    assert morph_f["status"] == "fail"
    assert packet.verdict == PacketVerdict.FAIL
