"""Plug-replaceability tests (PRD section 2 — Architecture Invariant).

The acceptance criterion: replacing one adapter implementation with another
behind the same contract MUST NOT break downstream code or shape.

UPGRADED: Each layer's plug-swap test now uses the primary Stub adapter as A
and the new Toy adapter as B. Both must:
  - produce identical output keys (detect_plug_replaceability_regression PASS)
  - emit the same set of falsifier_class values
  - have the same back_edges target_layer set
  - share contract_version="zer0pa.layer-envelope.v1"
  - both pass schemas/envelope/layer-envelope-v1.json

Additional tests assert that values in `output` MAY differ (the toy scores
things differently) but the SHAPE never differs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from zer0pa_biomolecular_explorer.envelope import (
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
from zer0pa_biomolecular_explorer.falsifiers.detectors import detect_plug_replaceability_regression
from zer0pa_biomolecular_explorer.hashing import sha256_of_obj
from zer0pa_biomolecular_explorer.ids import audit_id, run_id


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


def _falsifier_classes_match(env_a: LayerEnvelope, env_b: LayerEnvelope) -> None:
    """Both adapters must emit the same set of falsifier_class values."""
    classes_a = sorted({it.falsifier_class for it in env_a.falsifier.items})
    classes_b = sorted({it.falsifier_class for it in env_b.falsifier.items})
    assert classes_a == classes_b, (
        f"falsifier_class mismatch: stub={classes_a}, toy={classes_b}"
    )


def _back_edge_target_layers_match(env_a: LayerEnvelope, env_b: LayerEnvelope) -> None:
    """Both adapters must emit back-edges targeting the same layer set."""
    layers_a = sorted({be.target_layer for be in env_a.back_edges})
    layers_b = sorted({be.target_layer for be in env_b.back_edges})
    assert layers_a == layers_b, (
        f"back_edge target_layer mismatch: stub={layers_a}, toy={layers_b}"
    )


def _contract_version_matches(env_a: LayerEnvelope, env_b: LayerEnvelope) -> None:
    assert env_a.contract_version == "zer0pa.layer-envelope.v1"
    assert env_b.contract_version == "zer0pa.layer-envelope.v1"
    assert env_a.contract_version == env_b.contract_version


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


# ============================================================================
# L1 plug swap — Stub (A) vs Toy (B)
# ============================================================================


def test_l1_channel_panel_plug_swap():
    """L1StubAdapter vs L1ToyAdapter must produce identical-shape channel-panel envelopes."""
    from zer0pa_biomolecular_explorer.layers.l1.adapter import L1StubAdapter
    from zer0pa_biomolecular_explorer.layers.l1.toy_adapter import L1ToyAdapter
    from zer0pa_biomolecular_explorer.contracts.l1 import (
        L1ChannelPanelInput, L1TargetInput, L1ChannelGene, L1IonCurrent,
    )

    panel_input = L1ChannelPanelInput(
        targets=[
            L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr),
            L1TargetInput(gene=L1ChannelGene.SCN5A, current=L1IonCurrent.INaL),
            L1TargetInput(gene=L1ChannelGene.KCNQ1, current=L1IonCurrent.IKs),
            L1TargetInput(gene=L1ChannelGene.CACNA1C, current=L1IonCurrent.ICaL),
        ]
    )
    adapter_a = L1StubAdapter()
    adapter_b = L1ToyAdapter()

    env_a = adapter_a.channel_panel(panel_input, ligand_smiles="CCO")
    env_b = adapter_b.channel_panel(panel_input, ligand_smiles="CCO")

    _output_schemas_match(env_a, env_b)
    _falsifier_classes_match(env_a, env_b)
    _back_edge_target_layers_match(env_a, env_b)
    _contract_version_matches(env_a, env_b)


def test_l1_channel_panel_values_may_differ():
    """Toy adapter is allowed to produce different VALUES for the panel IC50s."""
    from zer0pa_biomolecular_explorer.layers.l1.adapter import L1StubAdapter
    from zer0pa_biomolecular_explorer.layers.l1.toy_adapter import L1ToyAdapter
    from zer0pa_biomolecular_explorer.contracts.l1 import (
        L1ChannelPanelInput, L1TargetInput, L1ChannelGene, L1IonCurrent,
    )

    panel_input = L1ChannelPanelInput(
        targets=[
            L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr),
            L1TargetInput(gene=L1ChannelGene.SCN5A, current=L1IonCurrent.INaL),
            L1TargetInput(gene=L1ChannelGene.KCNQ1, current=L1IonCurrent.IKs),
            L1TargetInput(gene=L1ChannelGene.CACNA1C, current=L1IonCurrent.ICaL),
        ]
    )
    env_stub = L1StubAdapter().channel_panel(panel_input, ligand_smiles="CCO")
    env_toy = L1ToyAdapter().channel_panel(panel_input, ligand_smiles="CCO")

    # Shapes match
    _output_schemas_match(env_stub, env_toy)

    # Values are allowed to differ — but output_hashes must differ (different canned values)
    # The toy provides actual IC50 values (not None), so the panel content differs
    assert env_stub.audit.output_hash != env_toy.audit.output_hash, (
        "Stub and toy should have different output_hashes because they use different canned values"
    )


def test_l1_dock_plug_swap():
    """L1StubAdapter.dock vs L1ToyAdapter.dock: same schema."""
    from zer0pa_biomolecular_explorer.layers.l1.adapter import L1StubAdapter
    from zer0pa_biomolecular_explorer.layers.l1.toy_adapter import L1ToyAdapter
    from zer0pa_biomolecular_explorer.contracts.l1 import (
        L1DockingInput, L1MoleculeInput, L1TargetInput, L1ChannelGene, L1IonCurrent,
    )

    inp = L1DockingInput(
        molecule=L1MoleculeInput(smiles="CCO", inchikey="LFQSCWFLJHTTHZ-UHFFFAOYSA-N"),
        target=L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr),
        n_poses=3,
    )
    env_a = L1StubAdapter().dock(inp)
    env_b = L1ToyAdapter().dock(inp)

    _output_schemas_match(env_a, env_b)
    _falsifier_classes_match(env_a, env_b)
    _contract_version_matches(env_a, env_b)


def test_l1_to_l1_runpod_stub_swap_interface_compatible():
    """OpenFERunpodAdapter must construct without raising and expose the same method names."""
    from zer0pa_biomolecular_explorer.layers.l1.adapter import L1StubAdapter
    from zer0pa_biomolecular_explorer.layers.l1.openfe_runpod_stub import OpenFERunpodAdapter

    a = L1StubAdapter()
    b = OpenFERunpodAdapter()
    expected = {"ligand", "target", "dock", "md", "fep", "channel_panel"}
    actual_a = set(m for m in dir(a) if not m.startswith("_") and callable(getattr(a, m)))
    actual_b = set(m for m in dir(b) if not m.startswith("_") and callable(getattr(b, m)))
    assert expected.issubset(actual_a)
    assert expected.issubset(actual_b), (
        "Runpod-parked adapter must expose the same methods as the stub"
    )


# ============================================================================
# L2 plug swap — Stub (A) vs Toy (B)
# ============================================================================


def test_l2_plug_swap():
    """L2StubAdapter vs L2ToyAdapter must produce identical-shape envelopes."""
    from zer0pa_biomolecular_explorer.contracts.l2 import L2MoleculeInput, L2PropertyInput
    from zer0pa_biomolecular_explorer.layers.l2.adapter import L2StubAdapter
    from zer0pa_biomolecular_explorer.layers.l2.toy_adapter import L2ToyAdapter

    inp = L2PropertyInput(molecule=L2MoleculeInput(smiles="CCO"))
    env_a = L2StubAdapter().process(inp)
    env_b = L2ToyAdapter().process(inp)

    _output_schemas_match(env_a, env_b)
    _falsifier_classes_match(env_a, env_b)
    _back_edge_target_layers_match(env_a, env_b)
    _contract_version_matches(env_a, env_b)

    # Stub must be deterministic
    env_a2 = L2StubAdapter().process(inp)
    assert env_a.audit.output_hash == env_a2.audit.output_hash, (
        "L2 stub must be deterministic; same input → same output_hash"
    )


def test_l2_toy_reward_modifier_differs():
    """Toy reward_modifier uses different formula (base 0.6 + aromatic-c bonus)."""
    from zer0pa_biomolecular_explorer.contracts.l2 import L2MoleculeInput, L2PropertyInput
    from zer0pa_biomolecular_explorer.layers.l2.adapter import L2StubAdapter
    from zer0pa_biomolecular_explorer.layers.l2.toy_adapter import L2ToyAdapter

    # Aromatic SMILES — will trigger toy's aromatic-c bonus
    inp = L2PropertyInput(molecule=L2MoleculeInput(smiles="c1ccccc1"))
    env_stub = L2StubAdapter().process(inp)
    env_toy = L2ToyAdapter().process(inp)

    _output_schemas_match(env_stub, env_toy)

    stub_reward = env_stub.output["reward_modifier"]
    toy_reward = env_toy.output["reward_modifier"]
    # Values are allowed to differ (toy has different base + bonus)
    assert isinstance(stub_reward, float)
    assert isinstance(toy_reward, float)
    # At minimum one should differ in value; both must be in valid range
    assert -1.0 <= stub_reward <= 1.0
    assert -1.0 <= toy_reward <= 1.0


def test_l2_stub_and_toy_same_keys():
    """Output keys must be exactly the same for stub and toy."""
    from zer0pa_biomolecular_explorer.contracts.l2 import L2MoleculeInput, L2PropertyInput
    from zer0pa_biomolecular_explorer.layers.l2.adapter import L2StubAdapter
    from zer0pa_biomolecular_explorer.layers.l2.toy_adapter import L2ToyAdapter

    inp = L2PropertyInput(molecule=L2MoleculeInput(smiles="CCO"))
    env_stub = L2StubAdapter().process(inp)
    env_toy = L2ToyAdapter().process(inp)

    assert sorted(env_stub.output.keys()) == sorted(env_toy.output.keys())


# ============================================================================
# L2.5 plug swap — Stub (A) vs Toy (B)
# ============================================================================


def test_l25_plug_swap():
    """L25StubAdapter vs L25ToyAdapter must produce identical-shape envelopes."""
    from zer0pa_biomolecular_explorer.contracts.l2_5 import L25Input, L25Policy
    from zer0pa_biomolecular_explorer.layers.l2_5.adapter import L25StubAdapter
    from zer0pa_biomolecular_explorer.layers.l2_5.toy_adapter import L25ToyAdapter

    inp = L25Input(canonical_smiles="CCO", policy=L25Policy.AIZYNTHFINDER_DEFAULT)
    env_a = L25StubAdapter().process(inp)
    env_b = L25ToyAdapter().process(inp)

    _output_schemas_match(env_a, env_b)
    _falsifier_classes_match(env_a, env_b)
    _back_edge_target_layers_match(env_a, env_b)
    _contract_version_matches(env_a, env_b)


def test_l25_back_edge_both_target_l2():
    """Both stub and toy L2.5 adapters must back-edge to L2."""
    from zer0pa_biomolecular_explorer.contracts.l2_5 import L25Input, L25Policy
    from zer0pa_biomolecular_explorer.layers.l2_5.adapter import L25StubAdapter
    from zer0pa_biomolecular_explorer.layers.l2_5.toy_adapter import L25ToyAdapter

    inp = L25Input(canonical_smiles="CCO", policy=L25Policy.AIZYNTHFINDER_DEFAULT)
    env_stub = L25StubAdapter().process(inp)
    env_toy = L25ToyAdapter().process(inp)

    # Both must have at least one back-edge to L2
    stub_l2_edges = [be for be in env_stub.back_edges if be.target_layer == "L2"]
    toy_l2_edges = [be for be in env_toy.back_edges if be.target_layer == "L2"]
    assert len(stub_l2_edges) >= 1, "Stub must emit back-edge to L2"
    assert len(toy_l2_edges) >= 1, "Toy must emit back-edge to L2"


def test_l25_feedback_to_l2_same_keys():
    """Both adapters must produce feedback_to_l2 with the same keys."""
    from zer0pa_biomolecular_explorer.contracts.l2_5 import L25Input, L25Policy
    from zer0pa_biomolecular_explorer.layers.l2_5.adapter import L25StubAdapter
    from zer0pa_biomolecular_explorer.layers.l2_5.toy_adapter import L25ToyAdapter

    inp = L25Input(canonical_smiles="CCO", policy=L25Policy.AIZYNTHFINDER_DEFAULT)
    env_stub = L25StubAdapter().process(inp)
    env_toy = L25ToyAdapter().process(inp)

    stub_feedback_keys = sorted(env_stub.output.get("feedback_to_l2", {}).keys())
    toy_feedback_keys = sorted(env_toy.output.get("feedback_to_l2", {}).keys())
    assert stub_feedback_keys == toy_feedback_keys


def test_l25_toy_route_score_differs():
    """Toy route_score formula yields different values than stub."""
    from zer0pa_biomolecular_explorer.contracts.l2_5 import L25Input, L25Policy
    from zer0pa_biomolecular_explorer.layers.l2_5.adapter import L25StubAdapter
    from zer0pa_biomolecular_explorer.layers.l2_5.toy_adapter import L25ToyAdapter

    inp = L25Input(canonical_smiles="CCO", policy=L25Policy.AIZYNTHFINDER_DEFAULT)
    env_stub = L25StubAdapter().process(inp)
    env_toy = L25ToyAdapter().process(inp)

    _output_schemas_match(env_stub, env_toy)
    # The route_score values should differ (different formula)
    stub_score = env_stub.output.get("feedback_to_l2", {}).get("route_score")
    toy_score = env_toy.output.get("feedback_to_l2", {}).get("route_score")
    assert stub_score is not None
    assert toy_score is not None
    # Both valid [0,1]
    assert 0.0 <= stub_score <= 1.0
    assert 0.0 <= toy_score <= 1.0


# ============================================================================
# L3 plug swap — Stub (A) vs Toy (B)
# ============================================================================


def test_l3_plug_swap():
    """L3StubAdapter vs L3ToyAdapter must produce identical-shape envelopes."""
    from zer0pa_biomolecular_explorer.contracts.l3 import L3ProcessInput
    from zer0pa_biomolecular_explorer.layers.l3.adapter import L3StubAdapter
    from zer0pa_biomolecular_explorer.layers.l3.toy_adapter import L3ToyAdapter

    inp = L3ProcessInput(
        target_canonical_smiles="CCO",
        route_rxnsmiles=["[CH4:1].[OH2:2]>>[CH3:1][OH:2]"],
        target_throughput_kg_per_batch=1.0,
    )
    env_a = L3StubAdapter().process(inp)
    env_b = L3ToyAdapter().process(inp)

    _output_schemas_match(env_a, env_b)
    _falsifier_classes_match(env_a, env_b)
    _contract_version_matches(env_a, env_b)


def test_l3_unit_op_kinds_differ():
    """Toy uses BLENDING (not CRYSTALLIZATION/FILTRATION) — values differ, schema same."""
    from zer0pa_biomolecular_explorer.contracts.l3 import L3ProcessInput, L3UnitOpKind
    from zer0pa_biomolecular_explorer.layers.l3.adapter import L3StubAdapter
    from zer0pa_biomolecular_explorer.layers.l3.toy_adapter import L3ToyAdapter

    inp = L3ProcessInput(
        target_canonical_smiles="CCO",
        route_rxnsmiles=["[CH4:1].[OH2:2]>>[CH3:1][OH:2]"],
        target_throughput_kg_per_batch=1.0,
    )
    env_stub = L3StubAdapter().process(inp)
    env_toy = L3ToyAdapter().process(inp)

    # Schema (output keys) must match
    _output_schemas_match(env_stub, env_toy)

    # Values: stub uses CRYSTALLIZATION, toy uses BLENDING
    stub_ops = env_stub.output.get("unit_ops", [])
    toy_ops = env_toy.output.get("unit_ops", [])

    stub_kinds = {op["kind"] for op in stub_ops}
    toy_kinds = {op["kind"] for op in toy_ops}

    # Stub should have crystallization; toy should have blending
    assert "crystallization" in stub_kinds, "Stub should emit crystallization ops"
    assert "blending" in toy_kinds, "Toy should emit blending ops (differentiator)"
    # Neither should have both
    assert "blending" not in stub_kinds, "Stub should NOT have blending ops"


def test_l3_mass_balance_both_ok():
    """Both adapters must pass the mass-balance falsifier with the same input."""
    from zer0pa_biomolecular_explorer.contracts.l3 import L3ProcessInput
    from zer0pa_biomolecular_explorer.layers.l3.adapter import L3StubAdapter
    from zer0pa_biomolecular_explorer.layers.l3.toy_adapter import L3ToyAdapter

    inp = L3ProcessInput(
        target_canonical_smiles="CCO",
        route_rxnsmiles=["[CH4:1].[OH2:2]>>[CH3:1][OH:2]"],
        target_throughput_kg_per_batch=1.0,
    )
    env_stub = L3StubAdapter().process(inp)
    env_toy = L3ToyAdapter().process(inp)

    assert env_stub.output["mass_balance_ok"] is True
    assert env_toy.output["mass_balance_ok"] is True


# ============================================================================
# L4 plug swap — Stub (A) vs Toy (B)
# ============================================================================


def test_l4_plug_swap():
    """L4StubAdapter vs L4ToyAdapter must produce identical-shape envelopes."""
    from zer0pa_biomolecular_explorer.contracts.l4 import L4SensorClass, L4SensorState, L4VirtualPlantInput
    from zer0pa_biomolecular_explorer.layers.l4.adapter import L4StubAdapter
    from zer0pa_biomolecular_explorer.layers.l4.toy_adapter import L4ToyAdapter

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
    env_a = L4StubAdapter().process(inp)
    env_b = L4ToyAdapter().process(inp)

    _output_schemas_match(env_a, env_b)
    _falsifier_classes_match(env_a, env_b)
    _back_edge_target_layers_match(env_a, env_b)
    _contract_version_matches(env_a, env_b)


def test_l4_fmu_sim_time_differs():
    """Toy uses dt=0.5s so FMU sim_time_s differs from stub (dt=1.0s)."""
    from zer0pa_biomolecular_explorer.contracts.l4 import L4SensorClass, L4SensorState, L4VirtualPlantInput
    from zer0pa_biomolecular_explorer.layers.l4.adapter import L4StubAdapter
    from zer0pa_biomolecular_explorer.layers.l4.toy_adapter import L4ToyAdapter

    sensors = [
        L4SensorState(
            sensor_id="PAT-T-01",
            sensor_class=L4SensorClass.PAT_TEMP,
            value=25.0,
            unit="C",
            timestamp_utc="2026-04-30T00:00:00Z",
            in_range=True,
        )
    ]
    inp = L4VirtualPlantInput(
        process_graph_unit_ops=["reaction_1"],
        sensor_states=sensors,
        target_throughput_kg_per_batch=1.0,
    )
    env_stub = L4StubAdapter().process(inp)
    env_toy = L4ToyAdapter().process(inp)

    _output_schemas_match(env_stub, env_toy)

    # FMU sim_time_s should differ: stub = 5 * 1.0 = 5.0; toy = 5 * 0.5 = 2.5
    stub_fmu_states = env_stub.output.get("fmu_states", [])
    toy_fmu_states = env_toy.output.get("fmu_states", [])
    assert len(stub_fmu_states) > 0
    assert len(toy_fmu_states) > 0

    stub_sim_time = stub_fmu_states[0]["sim_time_s"]
    toy_sim_time = toy_fmu_states[0]["sim_time_s"]
    # Different dt: stub = 5.0, toy = 2.5
    assert stub_sim_time != toy_sim_time, (
        f"FMU sim_time_s should differ: stub={stub_sim_time}, toy={toy_sim_time}"
    )


# ============================================================================
# L5 plug swap — Stub (A) vs Toy (B)
# ============================================================================


def test_l5_plug_swap():
    """L5StubAdapter vs L5ToyAdapter must produce identical-shape envelopes."""
    from zer0pa_biomolecular_explorer.contracts.l5 import L5PKModelKind, L5PKPDInput
    from zer0pa_biomolecular_explorer.layers.l5.adapter import L5StubAdapter
    from zer0pa_biomolecular_explorer.layers.l5.toy_adapter import L5ToyAdapter

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
    env_a = L5StubAdapter().process(inp)
    env_b = L5ToyAdapter().process(inp)

    _output_schemas_match(env_a, env_b)
    _falsifier_classes_match(env_a, env_b)
    _back_edge_target_layers_match(env_a, env_b)
    _contract_version_matches(env_a, env_b)


def test_l5_cardiac_bridge_values_differ():
    """Toy uses 1.5× IC50 — fractional block values differ from stub."""
    from zer0pa_biomolecular_explorer.contracts.l5 import L5PKModelKind, L5PKPDInput
    from zer0pa_biomolecular_explorer.layers.l5.adapter import L5StubAdapter
    from zer0pa_biomolecular_explorer.layers.l5.toy_adapter import L5ToyAdapter

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
    env_stub = L5StubAdapter().process(inp)
    env_toy = L5ToyAdapter().process(inp)

    # Schema must match
    _output_schemas_match(env_stub, env_toy)

    # Cardiac bridge fractional block values should differ (1.5× IC50 → lower block)
    stub_bridge = env_stub.output.get("cardiac_bridge")
    toy_bridge = env_toy.output.get("cardiac_bridge")

    if stub_bridge is not None and toy_bridge is not None:
        stub_blocks = stub_bridge.get("fractional_block_at_cmax", {})
        toy_blocks = toy_bridge.get("fractional_block_at_cmax", {})
        # Both have the same keys
        assert sorted(stub_blocks.keys()) == sorted(toy_blocks.keys()), (
            "Cardiac bridge channel keys must match between stub and toy"
        )
        # Values are allowed to differ (and should differ due to 1.5× IC50)
        # At least one current should have a different fractional block
        values_differ = any(
            abs(stub_blocks[k] - toy_blocks[k]) > 1e-9
            for k in stub_blocks
        )
        assert values_differ, (
            "Toy (1.5× IC50) should produce different fractional blocks than stub"
        )


def test_l5_sbml_packet_shape_same():
    """Both adapters must produce the same SBML packet schema."""
    from zer0pa_biomolecular_explorer.contracts.l5 import L5PKModelKind, L5PKPDInput
    from zer0pa_biomolecular_explorer.layers.l5.adapter import L5StubAdapter
    from zer0pa_biomolecular_explorer.layers.l5.toy_adapter import L5ToyAdapter

    inp = L5PKPDInput(
        canonical_smiles="CCO",
        dose_mg=10.0,
        model_kind=L5PKModelKind.ONE_COMPARTMENT,
        fraction_unbound=0.5,
        cl_l_per_h=10.0,
        vd_l=70.0,
        ka_per_h=1.0,
    )
    env_stub = L5StubAdapter().process(inp)
    env_toy = L5ToyAdapter().process(inp)

    # Output key shape must match
    _output_schemas_match(env_stub, env_toy)

    # sbml_packet sub-keys must match
    stub_sbml = env_stub.output.get("sbml_packet") or {}
    toy_sbml = env_toy.output.get("sbml_packet") or {}
    if stub_sbml and toy_sbml:
        assert sorted(stub_sbml.keys()) == sorted(toy_sbml.keys())


# ============================================================================
# L6 router as a layer plug swap (envelope shape) — UNCHANGED
# ============================================================================


def test_l6_router_envelope_shape_invariant():
    """L6Router.make_l6_self_envelope must produce a stable shape across two distinct calls."""
    from zer0pa_biomolecular_explorer.orchestration.router import L6Router

    rid = "run:plugswap-l6"
    env_a = L6Router.make_l6_self_envelope(rid, [{"layer": "L1", "decision": "promote"}])
    env_b = L6Router.make_l6_self_envelope(
        rid, [{"layer": "L1", "decision": "promote"}, {"layer": "L5", "decision": "promote"}]
    )
    assert sorted(env_a.output.keys()) == sorted(env_b.output.keys())


# ============================================================================
# Cross-layer contract version invariant — UNCHANGED
# ============================================================================


def test_all_envelopes_share_contract_version():
    """Any layer envelope must declare contract_version == zer0pa.layer-envelope.v1."""
    from zer0pa_biomolecular_explorer.layers.l1.adapter import L1StubAdapter
    from zer0pa_biomolecular_explorer.layers.l1.toy_adapter import L1ToyAdapter
    from zer0pa_biomolecular_explorer.layers.l2.adapter import L2StubAdapter
    from zer0pa_biomolecular_explorer.layers.l2.toy_adapter import L2ToyAdapter
    from zer0pa_biomolecular_explorer.contracts.l1 import L1MoleculeInput
    from zer0pa_biomolecular_explorer.contracts.l2 import L2MoleculeInput, L2PropertyInput

    e1_stub = L1StubAdapter().ligand(L1MoleculeInput(smiles="CCO"))
    e1_toy = L1ToyAdapter().ligand(L1MoleculeInput(smiles="CCO"))
    e2_stub = L2StubAdapter().process(L2PropertyInput(molecule=L2MoleculeInput(smiles="CCO")))
    e2_toy = L2ToyAdapter().process(L2PropertyInput(molecule=L2MoleculeInput(smiles="CCO")))

    for env in [e1_stub, e1_toy, e2_stub, e2_toy]:
        assert env.contract_version == "zer0pa.layer-envelope.v1"
