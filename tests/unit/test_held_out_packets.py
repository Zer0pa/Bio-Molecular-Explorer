"""Tests for the six held-out cardiac compound fixtures and packet assembly.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from zer0pa_health.boundary import RESEARCH_BOUNDARY
from zer0pa_health.packets import CardiacPacketAssembler, PacketVerdict
from zer0pa_health.packets.assembler import AssemblerInputs

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "fixtures" / "compounds"
SCHEMA_PATH = REPO_ROOT / "schemas" / "fixtures" / "compound.schema.json"

HELD_OUT_NAMES = [
    "quinidine",
    "moxifloxacin",
    "diltiazem",
    "sotalol",
    "mexiletine",
    "lidocaine",
]

KNOWN_COMPOUNDS = {"dofetilide", "verapamil", "ranolazine"}
ALL_FOUR_CHANNELS = {
    "KCNH2_hERG_IKr",
    "SCN5A_Nav1_5_INa_INaL",
    "KCNQ1_Kv7_1_IKs",
    "CACNA1C_CaV1_2_ICaL",
}


@pytest.fixture(scope="module")
def compound_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


@pytest.fixture(scope="module")
def held_out_fixtures() -> list[tuple[str, dict]]:
    result = []
    for name in HELD_OUT_NAMES:
        fp = FIXTURE_DIR / f"{name}.json"
        assert fp.exists(), f"Missing held-out fixture: {fp}"
        data = json.loads(fp.read_text())
        result.append((name, data))
    return result


def test_exactly_six_held_out_fixtures():
    """Confirm exactly 6 held-out compound fixtures exist."""
    held_out = [
        fp
        for fp in FIXTURE_DIR.glob("*.json")
        if fp.stem not in KNOWN_COMPOUNDS
    ]
    assert len(held_out) == 6, (
        f"Expected exactly 6 held-out fixtures, found {len(held_out)}: "
        f"{[fp.stem for fp in held_out]}"
    )


def test_held_out_names_match_expected(held_out_fixtures):
    """Held-out fixture names match the specified set."""
    names = {name for name, _ in held_out_fixtures}
    assert names == set(HELD_OUT_NAMES)


@pytest.mark.parametrize("name", HELD_OUT_NAMES)
def test_fixture_validates_against_schema(name, compound_schema):
    """Each held-out fixture validates against schemas/fixtures/compound.schema.json."""
    fp = FIXTURE_DIR / f"{name}.json"
    data = json.loads(fp.read_text())
    # Should not raise
    jsonschema.validate(data, compound_schema)


@pytest.mark.parametrize("name", HELD_OUT_NAMES)
def test_fixture_has_canonical_boundary(name):
    """Each held-out fixture carries the canonical RESEARCH_BOUNDARY string verbatim."""
    fp = FIXTURE_DIR / f"{name}.json"
    data = json.loads(fp.read_text())
    assert data["research_boundary"] == RESEARCH_BOUNDARY


@pytest.mark.parametrize("name", HELD_OUT_NAMES)
def test_fixture_has_all_four_channels(name):
    """Each held-out fixture has all four required channel panel entries."""
    fp = FIXTURE_DIR / f"{name}.json"
    data = json.loads(fp.read_text())
    panel = data["channel_panel_canned"]
    assert set(panel.keys()) == ALL_FOUR_CHANNELS, (
        f"{name}: panel keys {set(panel.keys())} != required {ALL_FOUR_CHANNELS}"
    )


@pytest.mark.parametrize("name", HELD_OUT_NAMES)
def test_fixture_null_channels_have_explicit_absence(name):
    """Every channel with ic50_uM=null must carry explicit_absence."""
    fp = FIXTURE_DIR / f"{name}.json"
    data = json.loads(fp.read_text())
    panel = data["channel_panel_canned"]
    for channel_key, entry in panel.items():
        if entry["ic50_uM"] is None:
            assert "explicit_absence" in entry, (
                f"{name}.{channel_key}: ic50_uM is null but no explicit_absence field"
            )
            assert entry["explicit_absence"], (
                f"{name}.{channel_key}: explicit_absence is empty"
            )


@pytest.mark.parametrize("name", HELD_OUT_NAMES)
def test_assemble_packet_returns_expected_verdict(name):
    """CardiacPacketAssembler.assemble() returns the expected_packet_verdict from the fixture."""
    fp = FIXTURE_DIR / f"{name}.json"
    fixture = json.loads(fp.read_text())
    expected_str = fixture["expected_packet_verdict"]
    expected_verdict = PacketVerdict(expected_str)

    assembler = CardiacPacketAssembler()
    inputs = AssemblerInputs(compound_fixture_path=fp)
    packet, diagnostics = assembler.assemble(inputs)

    assert packet.verdict == expected_verdict, (
        f"{name}: expected verdict={expected_verdict!r}, got {packet.verdict!r}; "
        f"diagnostics={diagnostics}"
    )


@pytest.mark.parametrize("name", HELD_OUT_NAMES)
def test_assembled_packet_has_all_four_channel_members(name):
    """Assembled packet's channel_panel has a member for each of the four required channels."""
    fp = FIXTURE_DIR / f"{name}.json"
    assembler = CardiacPacketAssembler()
    inputs = AssemblerInputs(compound_fixture_path=fp)
    packet, _ = assembler.assemble(inputs)

    panel = packet.channel_panel
    assert panel.KCNH2_hERG_IKr is not None, f"{name}: KCNH2_hERG_IKr missing"
    assert panel.SCN5A_Nav1_5_INa_INaL is not None, f"{name}: SCN5A_Nav1_5_INa_INaL missing"
    assert panel.KCNQ1_Kv7_1_IKs is not None, f"{name}: KCNQ1_Kv7_1_IKs missing"
    assert panel.CACNA1C_CaV1_2_ICaL is not None, f"{name}: CACNA1C_CaV1_2_ICaL missing"


@pytest.mark.parametrize("name", HELD_OUT_NAMES)
def test_assembled_packet_preserves_boundary_string(name):
    """Assembled packet.research_boundary matches the canonical RESEARCH_BOUNDARY verbatim."""
    fp = FIXTURE_DIR / f"{name}.json"
    assembler = CardiacPacketAssembler()
    inputs = AssemblerInputs(compound_fixture_path=fp)
    packet, _ = assembler.assemble(inputs)
    assert packet.research_boundary == RESEARCH_BOUNDARY


@pytest.mark.parametrize("name", HELD_OUT_NAMES)
def test_assembled_packet_has_falsifiers(name):
    """Assembled packet has at least one falsifier entry."""
    fp = FIXTURE_DIR / f"{name}.json"
    assembler = CardiacPacketAssembler()
    inputs = AssemblerInputs(compound_fixture_path=fp)
    packet, _ = assembler.assemble(inputs)
    assert len(packet.falsifiers) >= 1, f"{name}: no falsifiers in assembled packet"


@pytest.mark.parametrize("name", HELD_OUT_NAMES)
def test_assembled_packet_has_claims_with_refs(name):
    """Assembled packet has at least one claim with falsifier_refs and audit_refs."""
    fp = FIXTURE_DIR / f"{name}.json"
    assembler = CardiacPacketAssembler()
    inputs = AssemblerInputs(compound_fixture_path=fp)
    packet, _ = assembler.assemble(inputs)
    assert len(packet.claims) >= 1, f"{name}: no claims in assembled packet"
    claim = packet.claims[0]
    assert len(claim.falsifier_refs) >= 1, f"{name}: claim missing falsifier_refs"
    assert len(claim.audit_refs) >= 1, f"{name}: claim missing audit_refs"
