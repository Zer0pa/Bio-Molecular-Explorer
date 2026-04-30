"""Unit tests for P1HandoffStubAdapter and P1HandoffToyAdapter.

Coverage:
  - Cardiac lead (KCNH2) → is_cardiac_target=True, l1_channel_panel_input with all 4 genes
  - Non-cardiac lead (EGFR) → l1_channel_panel_input is None, is_cardiac_target=False
  - confidence_tier_overclaim trip: tier=A, distinct_models=1 → verdict="blocked"
  - synthesis_route_absent trip: sa_score=2.5, empty route_steps → verdict="blocked"
  - hERG_only_overreach trip: cardiac lead but only KCNH2 in panel → verdict="hold"
    (tested by patching the adapter's panel-build logic to produce only KCNH2)
  - clinical_overclaim trip via suggested_route: Pydantic catches the banned phrase
    before the detector runs → ValidationError raised
  - Plug-swap stub vs toy: same output schema keys
  - JSON Schema validation
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from pydantic import ValidationError

from zer0pa_health.envelope import FalsifierStatus
from zer0pa_health.pathway1.contracts.p1_handoff import P1HandoffInput, P1HandoffPacket
from zer0pa_health.pathway1.contracts.p1_optimize import P1ASKCOSRouteStep, P1OptimizedLead
from zer0pa_health.pathway1.layers.handoff import P1HandoffStubAdapter, P1HandoffToyAdapter

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent / "schemas" / "envelope" / "layer-envelope-v1.json"
)

_VALID_SMILES = "CN(C)S(=O)(=O)c1ccc(NC)cc1"

_FOUR_CARDIAC_GENES = {"KCNH2", "SCN5A", "KCNQ1", "CACNA1C"}

# Gene→current expected in the cardiac bridge
_EXPECTED_GENE_CURRENTS = {
    "KCNH2": "IKr",
    "SCN5A": "INaL",
    "KCNQ1": "IKs",
    "CACNA1C": "ICaL",
}


def _make_lead(
    *,
    lead_id: str = "lead-001",
    smiles: str = _VALID_SMILES,
    predicted_pIC50: float = 7.5,
    selectivity_score: float = 0.8,
    synthetic_accessibility: float = 3.5,
    confidence_tier: str = "B",
    distinct_models_count: int = 2,
    iteration_number: int = 1,
    askcos_route_steps: list[dict] | None = None,
    admet_panel: dict | None = None,
) -> dict[str, Any]:
    if askcos_route_steps is None:
        askcos_route_steps = [
            {"step_index": 0, "rxn_smarts": "[C:1][N:2]>>[C:1].[N:2]", "reagents": []}
        ]
    if admet_panel is None:
        admet_panel = {
            "esol_logs": -3.0,
            "lipinski_violations": 0,
            "herg_ic50_um": 15.0,
            "oral_bioavailability": 0.6,
        }
    return P1OptimizedLead(
        lead_id=lead_id,
        target_id="target-001",
        smiles=smiles,
        predicted_pIC50=predicted_pIC50,
        admet_panel=admet_panel,
        selectivity_score=selectivity_score,
        synthetic_accessibility=synthetic_accessibility,
        askcos_route_steps=askcos_route_steps,
        estimated_synthesis_steps=len(askcos_route_steps),
        iteration_number=iteration_number,
        confidence_tier=confidence_tier,
        distinct_models_count=distinct_models_count,
    ).model_dump()


def _make_handoff_input(
    *,
    target_gene: str,
    leads: list[dict] | None = None,
    audit_refs: list[str] | None = None,
) -> P1HandoffInput:
    return P1HandoffInput(
        target_id="target-001",
        target_gene=target_gene,
        leads=leads or [_make_lead()],
        pathway1_run_id="run:test-00000001",
        audit_refs=audit_refs or ["audit:ref-001"],
    )


@pytest.fixture(scope="module")
def stub_adapter() -> P1HandoffStubAdapter:
    return P1HandoffStubAdapter()


@pytest.fixture(scope="module")
def toy_adapter() -> P1HandoffToyAdapter:
    return P1HandoffToyAdapter()


@pytest.fixture(scope="module")
def envelope_schema() -> dict:
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


def validate_envelope(envelope_dict: dict, schema: dict) -> None:
    jsonschema.validate(instance=envelope_dict, schema=schema)


# ---------------------------------------------------------------------------
# Test 1: Cardiac lead → is_cardiac_target=True, l1_channel_panel_input populated
# ---------------------------------------------------------------------------

def test_cardiac_lead_panel_populated(stub_adapter: P1HandoffStubAdapter) -> None:
    """KCNH2 cardiac target → is_cardiac_target=True and all 4 genes in panel."""
    inp = _make_handoff_input(target_gene="KCNH2")
    envelope = stub_adapter.process(inp)

    output = envelope.output
    packets = output["packets"]
    assert len(packets) == 1, "expected exactly one packet"

    pkt = packets[0]
    assert pkt["is_cardiac_target"] is True
    assert pkt["l1_channel_panel_input"] is not None

    panel_targets = pkt["l1_channel_panel_input"]["targets"]
    panel_genes = {t["gene"] for t in panel_targets}
    assert panel_genes == _FOUR_CARDIAC_GENES, f"expected all 4 cardiac genes, got {panel_genes}"

    # Verify gene→current mapping
    for t in panel_targets:
        gene = t["gene"]
        expected_current = _EXPECTED_GENE_CURRENTS[gene]
        assert t["current"] == expected_current, (
            f"gene {gene}: expected current {expected_current}, got {t['current']}"
        )


# ---------------------------------------------------------------------------
# Test 2: Non-cardiac lead → l1_channel_panel_input is None
# ---------------------------------------------------------------------------

def test_non_cardiac_lead_no_panel(stub_adapter: P1HandoffStubAdapter) -> None:
    """EGFR target → is_cardiac_target=False, l1_channel_panel_input is None."""
    inp = _make_handoff_input(target_gene="EGFR")
    envelope = stub_adapter.process(inp)

    packets = envelope.output["packets"]
    pkt = packets[0]
    assert pkt["is_cardiac_target"] is False
    assert pkt["l1_channel_panel_input"] is None


# ---------------------------------------------------------------------------
# Test 3: confidence_tier_overclaim trip → verdict="blocked"
# ---------------------------------------------------------------------------

def test_confidence_tier_overclaim_blocks(stub_adapter: P1HandoffStubAdapter) -> None:
    """Tier A with only 1 model → CONFIDENCE_TIER_OVERCLAIM FAIL → verdict=blocked."""
    lead = _make_lead(confidence_tier="A", distinct_models_count=1)
    inp = _make_handoff_input(target_gene="EGFR", leads=[lead])
    envelope = stub_adapter.process(inp)

    packets = envelope.output["packets"]
    pkt = packets[0]
    assert pkt["verdict_at_handoff"] == "blocked", (
        f"expected 'blocked' but got {pkt['verdict_at_handoff']!r}"
    )

    # Confirm the specific falsifier item is FAIL
    items = envelope.falsifier.items
    tier_items = [
        item for item in items
        if item.falsifier_class == "confidence_tier_overclaim"
    ]
    assert tier_items, "expected at least one confidence_tier_overclaim falsifier item"
    assert any(item.status == FalsifierStatus.FAIL for item in tier_items)


# ---------------------------------------------------------------------------
# Test 4: synthesis_route_absent trip → verdict="blocked"
# ---------------------------------------------------------------------------

def test_synthesis_route_absent_blocks(stub_adapter: P1HandoffStubAdapter) -> None:
    """SA score <= 4.0 and no ASKCOS steps → SYNTHESIS_ROUTE_ABSENT FAIL → verdict=blocked."""
    lead = _make_lead(
        synthetic_accessibility=2.5,
        askcos_route_steps=[],
        # Use Tier B with 2 models to avoid confounding tier overclaim
        confidence_tier="B",
        distinct_models_count=2,
    )
    inp = _make_handoff_input(target_gene="EGFR", leads=[lead])
    envelope = stub_adapter.process(inp)

    packets = envelope.output["packets"]
    pkt = packets[0]
    assert pkt["verdict_at_handoff"] == "blocked", (
        f"expected 'blocked' but got {pkt['verdict_at_handoff']!r}"
    )

    items = envelope.falsifier.items
    route_items = [
        item for item in items
        if item.falsifier_class == "synthesis_route_absent"
    ]
    assert route_items, "expected at least one synthesis_route_absent falsifier item"
    assert any(item.status == FalsifierStatus.FAIL for item in route_items)


# ---------------------------------------------------------------------------
# Test 5: hERG_only_overreach trip → verdict="hold"
#
# We test this by producing a CARDIAC target (KCNH2) but hacking the lead so
# that only KCNH2 is in the panel.  We do this by monkeypatching the adapter's
# _build_cardiac_panel to return only KCNH2.  That simulates a scenario where
# only hERG is assessed and the other three genes are absent.
# ---------------------------------------------------------------------------

def test_herg_only_overreach_hold(stub_adapter: P1HandoffStubAdapter) -> None:
    """When cardiac panel has only KCNH2 (no SCN5A/KCNQ1/CACNA1C), verdict=hold."""
    import zer0pa_health.pathway1.layers.handoff.adapter as adapter_module
    from zer0pa_health.pathway1.contracts.p1_handoff import (
        P1L1ChannelPanelInput,
        P1L1ChannelPanelTarget,
    )

    original_build = adapter_module._build_cardiac_panel

    def _only_herg() -> P1L1ChannelPanelInput:
        return P1L1ChannelPanelInput(
            targets=[P1L1ChannelPanelTarget(gene="KCNH2", current="IKr")]
        )

    adapter_module._build_cardiac_panel = _only_herg  # type: ignore[assignment]
    try:
        lead = _make_lead(confidence_tier="B", distinct_models_count=2)
        inp = _make_handoff_input(target_gene="KCNH2", leads=[lead])
        envelope = stub_adapter.process(inp)
    finally:
        adapter_module._build_cardiac_panel = original_build  # type: ignore[assignment]

    packets = envelope.output["packets"]
    pkt = packets[0]
    assert pkt["verdict_at_handoff"] == "hold", (
        f"expected 'hold' for hERG-only panel, got {pkt['verdict_at_handoff']!r}"
    )

    items = envelope.falsifier.items
    herg_items = [
        item for item in items
        if item.falsifier_class == "hERG_only_overreach"
    ]
    assert herg_items, "expected hERG_only_overreach falsifier item"
    assert any(item.status == FalsifierStatus.FAIL for item in herg_items)


# ---------------------------------------------------------------------------
# Test 6: clinical_overclaim via suggested_route → Pydantic ValidationError
#
# The P1HandoffPacket validator fires BEFORE the detector would run.
# We verify that directly constructing a packet with a clinical-overclaim phrase
# raises ValidationError.
# ---------------------------------------------------------------------------

def test_suggested_route_clinical_overclaim_raises() -> None:
    """P1HandoffPacket rejects suggested_route containing a clinical-overclaim phrase."""
    with pytest.raises(ValidationError) as exc_info:
        P1HandoffPacket(
            pathway1_run_id="run:test-00000001",
            candidate_id="lead-001",
            smiles=_VALID_SMILES,
            target_id="target-001",
            target_gene="EGFR",
            predicted_pIC50=7.5,
            binding_affinity_source="stub",
            admet={},
            selectivity_score=0.8,
            synthetic_accessibility=3.5,
            estimated_synthesis_steps=2,
            # This phrase is in CLINICAL_OVERCLAIM_PHRASES → triggers validator
            suggested_route="This compound is fda approved for treating patients.",
            confidence_tier="B",
            generation_method="stub",
            iteration_number=1,
            parent_scaffold=None,
            audit_refs=["audit:ref-001"],
            verdict_at_handoff="pass",
            distinct_models_count=2,
        )
    # Confirm the right validator fired
    errors = exc_info.value.errors()
    error_fields = {e["loc"][-1] for e in errors}
    assert "suggested_route" in error_fields, (
        f"expected 'suggested_route' error, got fields: {error_fields}"
    )


# ---------------------------------------------------------------------------
# Test 7: Plug-swap stub vs toy — identical output schema keys
# ---------------------------------------------------------------------------

def test_plug_swap_stub_vs_toy(
    stub_adapter: P1HandoffStubAdapter,
    toy_adapter: P1HandoffToyAdapter,
) -> None:
    """Stub and Toy adapters produce outputs with identical top-level envelope keys."""
    inp = _make_handoff_input(target_gene="KCNH2")

    stub_env = stub_adapter.process(inp)
    toy_env = toy_adapter.process(inp)

    stub_dict = stub_env.model_dump()
    toy_dict = toy_env.model_dump()

    assert sorted(stub_dict.keys()) == sorted(toy_dict.keys()), (
        "top-level envelope keys differ between stub and toy adapters"
    )

    # Output section must also have identical keys
    stub_output_keys = sorted(stub_dict["output"].keys())
    toy_output_keys = sorted(toy_dict["output"].keys())
    assert stub_output_keys == toy_output_keys, (
        f"output keys differ: stub={stub_output_keys}, toy={toy_output_keys}"
    )

    # Per-packet keys must also match
    stub_pkt_keys = sorted(stub_dict["output"]["packets"][0].keys())
    toy_pkt_keys = sorted(toy_dict["output"]["packets"][0].keys())
    assert stub_pkt_keys == toy_pkt_keys, (
        f"packet keys differ: stub={stub_pkt_keys}, toy={toy_pkt_keys}"
    )

    # Adapters must differ in engine name
    assert stub_dict["tool_adapter"]["engine"] != toy_dict["tool_adapter"]["engine"], (
        "stub and toy adapters must have different engine names"
    )


# ---------------------------------------------------------------------------
# Test 8: JSON Schema validation
# ---------------------------------------------------------------------------

def test_json_schema_stub(
    stub_adapter: P1HandoffStubAdapter,
    envelope_schema: dict,
) -> None:
    """P1HandoffStubAdapter output validates against layer-envelope-v1.json schema."""
    inp = _make_handoff_input(target_gene="KCNH2")
    envelope = stub_adapter.process(inp)
    validate_envelope(json.loads(envelope.dump_json()), envelope_schema)


def test_json_schema_toy(
    toy_adapter: P1HandoffToyAdapter,
    envelope_schema: dict,
) -> None:
    """P1HandoffToyAdapter output validates against layer-envelope-v1.json schema."""
    inp = _make_handoff_input(target_gene="EGFR")
    envelope = toy_adapter.process(inp)
    validate_envelope(json.loads(envelope.dump_json()), envelope_schema)


# ---------------------------------------------------------------------------
# Test 9: Pass-through sanity — clean cardiac lead with all four genes → verdict=pass
# ---------------------------------------------------------------------------

def test_clean_cardiac_lead_pass(stub_adapter: P1HandoffStubAdapter) -> None:
    """A well-formed cardiac lead with valid tier/route/panel passes."""
    lead = _make_lead(
        confidence_tier="C",   # Tier C never overclaims regardless of model count
        distinct_models_count=0,
        synthetic_accessibility=5.0,  # > 4.0 → synthesis_route_absent check passes
    )
    inp = _make_handoff_input(target_gene="KCNH2", leads=[lead])
    envelope = stub_adapter.process(inp)

    pkt = envelope.output["packets"][0]
    assert pkt["verdict_at_handoff"] == "pass"
    assert pkt["is_cardiac_target"] is True
    assert pkt["l1_channel_panel_input"] is not None
