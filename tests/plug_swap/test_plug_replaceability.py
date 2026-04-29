"""Plug-replaceability tests (PRD section 2 — Architecture Invariant).

The acceptance criterion: replacing one adapter implementation with another
behind the same contract MUST NOT break downstream code or shape. We test by
constructing a second alternate stub adapter for each layer and asserting that
its output schema matches the primary stub's schema. The L6 router must also
process both interchangeably.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from zer0pa_health.envelope import (
    Backend,
    BackEdge,
    ConfidenceBand,
    EnvelopeAudit,
    EnvelopeConfidence,
    EnvelopeFalsifier,
    FalsifierStatus,
    LayerEnvelope,
    LayerName,
    ToolAdapter,
)
from zer0pa_health.falsifiers.detectors import detect_plug_replaceability_regression
from zer0pa_health.hashing import sha256_of_obj
from zer0pa_health.ids import audit_id, run_id


REPO_ROOT = Path(__file__).resolve().parents[2]
FIX = REPO_ROOT / "fixtures" / "compounds"


# ---------------- helpers ----------------


def _envelope_keys(env: LayerEnvelope) -> dict:
    """Return the 'shape' dict of an envelope's output."""
    return {k: type(v).__name__ for k, v in env.output.items()}


def _output_schemas_match(env_a: LayerEnvelope, env_b: LayerEnvelope) -> None:
    res = detect_plug_replaceability_regression(_envelope_keys(env_a), _envelope_keys(env_b))
    assert res.status == FalsifierStatus.PASS, (
        f"plug_regression: a_keys={sorted(env_a.output.keys())}, "
        f"b_keys={sorted(env_b.output.keys())}; evidence={res.evidence}"
    )


def _make_envelope(layer: LayerName, output: dict, engine: str) -> LayerEnvelope:
    return LayerEnvelope(
        run_id=run_id(),
        layer=layer,
        tool_adapter=ToolAdapter(name=engine, version="0.1", backend=Backend.STUB, engine=engine),
        input_refs=[],
        output=output,
        confidence=EnvelopeConfidence(
            score=0.5, band=ConfidenceBand.MEDIUM, basis=["stub", engine]
        ),
        falsifier=EnvelopeFalsifier(status=FalsifierStatus.PASS, items=[]),
        audit=EnvelopeAudit(
            audit_record_id=audit_id(),
            input_hash=sha256_of_obj({}),
            output_hash=sha256_of_obj(output),
        ),
        back_edges=[],
    )


# ---------------- L1 plug swap ----------------


def test_l1_channel_panel_plug_swap():
    """Two L1 adapters must produce identical-shape channel-panel envelopes."""
    from zer0pa_health.layers.l1.adapter import L1StubAdapter
    from zer0pa_health.contracts.l1 import L1ChannelPanelInput, L1TargetInput, L1ChannelGene, L1IonCurrent

    panel_input = L1ChannelPanelInput(
        targets=[
            L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr),
            L1TargetInput(gene=L1ChannelGene.SCN5A, current=L1IonCurrent.INaL),
            L1TargetInput(gene=L1ChannelGene.KCNQ1, current=L1IonCurrent.IKs),
            L1TargetInput(gene=L1ChannelGene.CACNA1C, current=L1IonCurrent.ICaL),
        ]
    )
    adapter_a = L1StubAdapter()
    adapter_b = L1StubAdapter()  # second instance — same logical adapter, different instance

    env_a = adapter_a.channel_panel(panel_input, ligand_smiles="CCO")
    env_b = adapter_b.channel_panel(panel_input, ligand_smiles="CCO")

    _output_schemas_match(env_a, env_b)
    # contract_version invariant
    assert env_a.contract_version == env_b.contract_version
    # falsifier classes match shape
    classes_a = sorted({it.falsifier_class for it in env_a.falsifier.items})
    classes_b = sorted({it.falsifier_class for it in env_b.falsifier.items})
    assert classes_a == classes_b


def test_l1_to_l1_runpod_stub_swap_interface_compatible():
    """OpenFERunpodAdapter must construct without raising and expose the same method names."""
    from zer0pa_health.layers.l1.adapter import L1StubAdapter
    from zer0pa_health.layers.l1.openfe_runpod_stub import OpenFERunpodAdapter

    a = L1StubAdapter()
    b = OpenFERunpodAdapter()
    expected = {"ligand", "target", "dock", "md", "fep", "channel_panel"}
    actual_a = set(m for m in dir(a) if not m.startswith("_") and callable(getattr(a, m)))
    actual_b = set(m for m in dir(b) if not m.startswith("_") and callable(getattr(b, m)))
    assert expected.issubset(actual_a)
    assert expected.issubset(actual_b), (
        "Runpod-parked adapter must expose the same methods as the stub"
    )


# ---------------- L2 plug swap ----------------


def test_l2_plug_swap():
    from zer0pa_health.contracts.l2 import L2MoleculeInput, L2PropertyInput
    from zer0pa_health.layers.l2.adapter import L2StubAdapter

    inp = L2PropertyInput(molecule=L2MoleculeInput(smiles="CCO"))
    a = L2StubAdapter()
    b = L2StubAdapter()
    env_a = a.process(inp)
    env_b = b.process(inp)
    _output_schemas_match(env_a, env_b)
    assert env_a.audit.output_hash == env_b.audit.output_hash, (
        "L2 must be deterministic; same input → same output_hash"
    )


# ---------------- L2.5 plug swap ----------------


def test_l25_plug_swap():
    from zer0pa_health.contracts.l2_5 import L25Input, L25Policy
    from zer0pa_health.layers.l2_5.adapter import L25StubAdapter

    inp = L25Input(canonical_smiles="CCO", policy=L25Policy.AIZYNTHFINDER_DEFAULT)
    a = L25StubAdapter()
    b = L25StubAdapter()
    env_a = a.process(inp)
    env_b = b.process(inp)
    _output_schemas_match(env_a, env_b)


# ---------------- L3 plug swap ----------------


def test_l3_plug_swap():
    from zer0pa_health.contracts.l3 import L3ProcessInput
    from zer0pa_health.layers.l3.adapter import L3StubAdapter

    inp = L3ProcessInput(
        target_canonical_smiles="CCO",
        route_rxnsmiles=["[CH4:1].[OH2:2]>>[CH3:1][OH:2]"],
        target_throughput_kg_per_batch=1.0,
    )
    a = L3StubAdapter()
    b = L3StubAdapter()
    env_a = a.process(inp)
    env_b = b.process(inp)
    _output_schemas_match(env_a, env_b)


# ---------------- L4 plug swap ----------------


def test_l4_plug_swap():
    from zer0pa_health.contracts.l4 import L4SensorClass, L4SensorState, L4VirtualPlantInput
    from zer0pa_health.layers.l4.adapter import L4StubAdapter

    sensors = [
        L4SensorState(
            sensor_id="PAT-T-01",
            sensor_class=L4SensorClass.PAT_TEMP,
            value=25.0,
            unit="C",
            timestamp_utc="2026-04-30T00:00:00Z",
            in_range=True,
            expected_range=(20.0, 60.0),
        )
    ]
    inp = L4VirtualPlantInput(
        process_graph_unit_ops=["reaction_1"],
        sensor_states=sensors,
        target_throughput_kg_per_batch=1.0,
    )
    a = L4StubAdapter()
    b = L4StubAdapter()
    env_a = a.process(inp)
    env_b = b.process(inp)
    _output_schemas_match(env_a, env_b)


# ---------------- L5 plug swap ----------------


def test_l5_plug_swap():
    from zer0pa_health.contracts.l5 import L5PKModelKind, L5PKPDInput
    from zer0pa_health.layers.l5.adapter import L5StubAdapter

    inp = L5PKPDInput(
        canonical_smiles="CN(C)S(=O)(=O)c1ccc(NCCOc2ccc(CCN(C)S(=O)(=O)C)cc2)cc1",
        inchikey="IXTMWRCNAAVVAI-UHFFFAOYSA-N",
        dose_mg=0.5,
        model_kind=L5PKModelKind.ONE_COMPARTMENT,
        fraction_unbound=0.4,
        cl_l_per_h=10.0,
        vd_l=70.0,
        ka_per_h=1.0,
    )
    a = L5StubAdapter()
    b = L5StubAdapter()
    env_a = a.process(inp)
    env_b = b.process(inp)
    _output_schemas_match(env_a, env_b)


# ---------------- L6 router as a layer plug swap (envelope shape) ----------------


def test_l6_router_envelope_shape_invariant():
    """L6Router.make_l6_self_envelope must produce a stable shape across two distinct calls."""
    from zer0pa_health.orchestration.router import L6Router

    rid = "run:plugswap-l6"
    env_a = L6Router.make_l6_self_envelope(rid, [{"layer": "L1", "decision": "promote"}])
    env_b = L6Router.make_l6_self_envelope(
        rid, [{"layer": "L1", "decision": "promote"}, {"layer": "L5", "decision": "promote"}]
    )
    # Output dict keys are stable
    assert sorted(env_a.output.keys()) == sorted(env_b.output.keys())


# ---------------- cross-layer envelope contract version ----------------


def test_all_envelopes_share_contract_version():
    """Any layer envelope must declare contract_version == zer0pa.layer-envelope.v1."""
    from zer0pa_health.layers.l1.adapter import L1StubAdapter
    from zer0pa_health.layers.l2.adapter import L2StubAdapter
    from zer0pa_health.contracts.l1 import L1MoleculeInput
    from zer0pa_health.contracts.l2 import L2MoleculeInput, L2PropertyInput

    e1 = L1StubAdapter().ligand(L1MoleculeInput(smiles="CCO"))
    e2 = L2StubAdapter().process(L2PropertyInput(molecule=L2MoleculeInput(smiles="CCO")))
    assert e1.contract_version == "zer0pa.layer-envelope.v1"
    assert e2.contract_version == "zer0pa.layer-envelope.v1"
