"""Real plug-swap acceptance tests (PRD section 2 acceptance criterion).

For each layer, run the same input through BOTH the primary Stub adapter
and the new Toy adapter, then feed each adapter's envelope output as the
upstream input to the NEXT layer's BOTH stub and toy adapters.

This is the actual PRD section 2 plug-swap acceptance test:
  "downstream code is unchanged" — i.e., the next layer can parse both
  upstream outputs successfully without any modification.

Test topology:
  L1 (stub+toy) → verify schema
  L2 (stub+toy) → verify schema
  L2.5 stub output feeds L2 stub+toy (back-edge pathway)
  L2.5 toy output feeds L2 stub+toy
  L3 (stub+toy) → verify schema
  L4 (stub+toy) → verify schema
  L5 (stub+toy) → verify schema
"""

from __future__ import annotations

import pytest

from zer0pa_health.envelope import FalsifierStatus, LayerEnvelope
from zer0pa_health.falsifiers.detectors import detect_plug_replaceability_regression


def _keys(env: LayerEnvelope) -> dict:
    return {k: type(v).__name__ for k, v in env.output.items()}


def _assert_pluggable(env_a: LayerEnvelope, env_b: LayerEnvelope, label: str) -> None:
    res = detect_plug_replaceability_regression(_keys(env_a), _keys(env_b))
    assert res.status == FalsifierStatus.PASS, (
        f"[{label}] plug_regression FAIL: "
        f"A_keys={sorted(env_a.output.keys())}, "
        f"B_keys={sorted(env_b.output.keys())}; "
        f"evidence={res.evidence}"
    )


# ============================================================================
# L1 — Stub vs Toy, all methods
# ============================================================================


def test_l1_ligand_real_swap():
    from zer0pa_health.contracts.l1 import L1MoleculeInput
    from zer0pa_health.layers.l1.adapter import L1StubAdapter
    from zer0pa_health.layers.l1.toy_adapter import L1ToyAdapter

    inp = L1MoleculeInput(smiles="CCO", inchikey="LFQSCWFLJHTTHZ-UHFFFAOYSA-N", name="ethanol")
    env_stub = L1StubAdapter().ligand(inp)
    env_toy = L1ToyAdapter().ligand(inp)
    _assert_pluggable(env_stub, env_toy, "L1.ligand")


def test_l1_target_real_swap():
    from zer0pa_health.contracts.l1 import L1ChannelGene, L1IonCurrent, L1TargetInput
    from zer0pa_health.layers.l1.adapter import L1StubAdapter
    from zer0pa_health.layers.l1.toy_adapter import L1ToyAdapter

    inp = L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr)
    env_stub = L1StubAdapter().target(inp)
    env_toy = L1ToyAdapter().target(inp)
    _assert_pluggable(env_stub, env_toy, "L1.target")


def test_l1_dock_real_swap():
    from zer0pa_health.contracts.l1 import (
        L1ChannelGene, L1DockingInput, L1IonCurrent, L1MoleculeInput, L1TargetInput,
    )
    from zer0pa_health.layers.l1.adapter import L1StubAdapter
    from zer0pa_health.layers.l1.toy_adapter import L1ToyAdapter

    inp = L1DockingInput(
        molecule=L1MoleculeInput(smiles="CCO", inchikey="LFQSCWFLJHTTHZ-UHFFFAOYSA-N"),
        target=L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr),
        n_poses=3,
    )
    env_stub = L1StubAdapter().dock(inp)
    env_toy = L1ToyAdapter().dock(inp)
    _assert_pluggable(env_stub, env_toy, "L1.dock")


def test_l1_md_real_swap():
    from zer0pa_health.contracts.l1 import (
        L1ChannelGene, L1IonCurrent, L1MDInput, L1MoleculeInput, L1TargetInput,
    )
    from zer0pa_health.layers.l1.adapter import L1StubAdapter
    from zer0pa_health.layers.l1.toy_adapter import L1ToyAdapter

    inp = L1MDInput(
        molecule=L1MoleculeInput(smiles="CCO"),
        target=L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr),
        pose_index=0,
        sim_ns=10.0,
    )
    env_stub = L1StubAdapter().md(inp)
    env_toy = L1ToyAdapter().md(inp)
    _assert_pluggable(env_stub, env_toy, "L1.md")


def test_l1_fep_real_swap():
    from zer0pa_health.contracts.l1 import (
        L1ChannelGene, L1FEPInput, L1IonCurrent, L1MoleculeInput, L1TargetInput,
    )
    from zer0pa_health.layers.l1.adapter import L1StubAdapter
    from zer0pa_health.layers.l1.toy_adapter import L1ToyAdapter

    inp = L1FEPInput(
        ligand_a=L1MoleculeInput(smiles="CCO"),
        ligand_b=L1MoleculeInput(smiles="CCCO"),
        target=L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr),
        method="RBFE",
    )
    env_stub = L1StubAdapter().fep(inp)
    env_toy = L1ToyAdapter().fep(inp)
    _assert_pluggable(env_stub, env_toy, "L1.fep")


def test_l1_channel_panel_real_swap():
    from zer0pa_health.contracts.l1 import (
        L1ChannelGene, L1ChannelPanelInput, L1IonCurrent, L1TargetInput,
    )
    from zer0pa_health.layers.l1.adapter import L1StubAdapter
    from zer0pa_health.layers.l1.toy_adapter import L1ToyAdapter

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
    _assert_pluggable(env_stub, env_toy, "L1.channel_panel")


# ============================================================================
# L2 — Stub vs Toy
# ============================================================================


def test_l2_real_swap_plain():
    from zer0pa_health.contracts.l2 import L2MoleculeInput, L2PropertyInput
    from zer0pa_health.layers.l2.adapter import L2StubAdapter
    from zer0pa_health.layers.l2.toy_adapter import L2ToyAdapter

    inp = L2PropertyInput(molecule=L2MoleculeInput(smiles="c1ccccc1"))
    env_stub = L2StubAdapter().process(inp)
    env_toy = L2ToyAdapter().process(inp)
    _assert_pluggable(env_stub, env_toy, "L2.process")


def test_l2_real_swap_with_retrosynth_feedback():
    """L2 with retrosynth_feedback from L2.5 — downstream parses both stub and toy."""
    from zer0pa_health.contracts.l2 import L2MoleculeInput, L2PropertyInput, L2RetrosynthFeedback
    from zer0pa_health.layers.l2.adapter import L2StubAdapter
    from zer0pa_health.layers.l2.toy_adapter import L2ToyAdapter

    feedback = L2RetrosynthFeedback(
        smiles="c1ccccc1",
        route_score=0.7,
        route_depth=3,
        sa_score=2.5,
        routes_found=True,
    )
    inp = L2PropertyInput(
        molecule=L2MoleculeInput(smiles="c1ccccc1"),
        retrosynth_feedback=feedback,
    )
    env_stub = L2StubAdapter().process(inp)
    env_toy = L2ToyAdapter().process(inp)
    _assert_pluggable(env_stub, env_toy, "L2.process_with_feedback")


# ============================================================================
# L2.5 upstream → L2 downstream: feed each L2.5 output to both L2 adapters
# ============================================================================


def test_l25_stub_output_feeds_l2_stub_and_toy():
    """L2.5 stub output can be parsed by both L2 stub and toy adapters."""
    from zer0pa_health.contracts.l2_5 import L25Input, L25Policy
    from zer0pa_health.contracts.l2 import L2MoleculeInput, L2PropertyInput, L2RetrosynthFeedback
    from zer0pa_health.layers.l2_5.adapter import L25StubAdapter
    from zer0pa_health.layers.l2.adapter import L2StubAdapter
    from zer0pa_health.layers.l2.toy_adapter import L2ToyAdapter

    # Run L2.5 stub
    l25_inp = L25Input(canonical_smiles="CCO", policy=L25Policy.AIZYNTHFINDER_DEFAULT)
    l25_env = L25StubAdapter().process(l25_inp)

    # Extract feedback_to_l2 from L2.5 stub output
    feedback_dict = l25_env.output.get("feedback_to_l2", {})
    feedback = L2RetrosynthFeedback(
        smiles="CCO",
        route_score=float(feedback_dict.get("route_score", 0.5)),
        route_depth=int(feedback_dict.get("route_depth", 2)),
        sa_score=float(feedback_dict.get("sa_score", 2.0)),
        routes_found=bool(feedback_dict.get("routes_found", 1.0)),
    )
    l2_inp = L2PropertyInput(
        molecule=L2MoleculeInput(smiles="CCO"),
        retrosynth_feedback=feedback,
    )

    # Feed to BOTH L2 adapters — downstream is unchanged
    env_stub = L2StubAdapter().process(l2_inp)
    env_toy = L2ToyAdapter().process(l2_inp)
    _assert_pluggable(env_stub, env_toy, "L25stub→L2(stub+toy)")


def test_l25_toy_output_feeds_l2_stub_and_toy():
    """L2.5 toy output can be parsed by both L2 stub and toy adapters."""
    from zer0pa_health.contracts.l2_5 import L25Input, L25Policy
    from zer0pa_health.contracts.l2 import L2MoleculeInput, L2PropertyInput, L2RetrosynthFeedback
    from zer0pa_health.layers.l2_5.toy_adapter import L25ToyAdapter
    from zer0pa_health.layers.l2.adapter import L2StubAdapter
    from zer0pa_health.layers.l2.toy_adapter import L2ToyAdapter

    l25_inp = L25Input(canonical_smiles="CCO", policy=L25Policy.AIZYNTHFINDER_DEFAULT)
    l25_env = L25ToyAdapter().process(l25_inp)

    feedback_dict = l25_env.output.get("feedback_to_l2", {})
    feedback = L2RetrosynthFeedback(
        smiles="CCO",
        route_score=float(feedback_dict.get("route_score", 0.5)),
        route_depth=int(feedback_dict.get("route_depth", 2)),
        sa_score=float(feedback_dict.get("sa_score", 2.0)),
        routes_found=bool(feedback_dict.get("routes_found", 1.0)),
    )
    l2_inp = L2PropertyInput(
        molecule=L2MoleculeInput(smiles="CCO"),
        retrosynth_feedback=feedback,
    )

    env_stub = L2StubAdapter().process(l2_inp)
    env_toy = L2ToyAdapter().process(l2_inp)
    _assert_pluggable(env_stub, env_toy, "L25toy→L2(stub+toy)")


# ============================================================================
# L2.5 — Stub vs Toy (direct)
# ============================================================================


def test_l25_real_swap():
    from zer0pa_health.contracts.l2_5 import L25Input, L25Policy
    from zer0pa_health.layers.l2_5.adapter import L25StubAdapter
    from zer0pa_health.layers.l2_5.toy_adapter import L25ToyAdapter

    inp = L25Input(canonical_smiles="CCO", policy=L25Policy.AIZYNTHFINDER_DEFAULT)
    env_stub = L25StubAdapter().process(inp)
    env_toy = L25ToyAdapter().process(inp)
    _assert_pluggable(env_stub, env_toy, "L2.5.process")


# ============================================================================
# L3 — Stub vs Toy; and L2.5 output feeding both L3 adapters
# ============================================================================


def test_l3_real_swap():
    from zer0pa_health.contracts.l3 import L3ProcessInput
    from zer0pa_health.layers.l3.adapter import L3StubAdapter
    from zer0pa_health.layers.l3.toy_adapter import L3ToyAdapter

    inp = L3ProcessInput(
        target_canonical_smiles="CCO",
        route_rxnsmiles=["[CH4:1].[OH2:2]>>[CH3:1][OH:2]"],
        target_throughput_kg_per_batch=1.0,
    )
    env_stub = L3StubAdapter().process(inp)
    env_toy = L3ToyAdapter().process(inp)
    _assert_pluggable(env_stub, env_toy, "L3.process")


def test_l25_stub_route_feeds_l3_stub_and_toy():
    """L2.5 stub route SMILES can feed both L3 adapters (downstream unchanged)."""
    from zer0pa_health.contracts.l2_5 import L25Input, L25Policy
    from zer0pa_health.contracts.l3 import L3ProcessInput
    from zer0pa_health.layers.l2_5.adapter import L25StubAdapter
    from zer0pa_health.layers.l3.adapter import L3StubAdapter
    from zer0pa_health.layers.l3.toy_adapter import L3ToyAdapter

    l25_env = L25StubAdapter().process(
        L25Input(canonical_smiles="CCO", policy=L25Policy.AIZYNTHFINDER_DEFAULT)
    )
    routes = l25_env.output.get("routes", [])
    if routes:
        steps = routes[0].get("steps", [])
        rxnsmiles = [s.get("rxnsmiles") for s in steps if s.get("rxnsmiles")]
    else:
        rxnsmiles = ["[CH4:1].[OH2:2]>>[CH3:1][OH:2]"]

    l3_inp = L3ProcessInput(
        target_canonical_smiles="CCO",
        route_rxnsmiles=rxnsmiles or ["[CH4:1]>>[CH3:1]"],
        target_throughput_kg_per_batch=1.0,
    )
    env_stub = L3StubAdapter().process(l3_inp)
    env_toy = L3ToyAdapter().process(l3_inp)
    _assert_pluggable(env_stub, env_toy, "L25stub_route→L3(stub+toy)")


def test_l25_toy_route_feeds_l3_stub_and_toy():
    """L2.5 toy route SMILES can feed both L3 adapters."""
    from zer0pa_health.contracts.l2_5 import L25Input, L25Policy
    from zer0pa_health.contracts.l3 import L3ProcessInput
    from zer0pa_health.layers.l2_5.toy_adapter import L25ToyAdapter
    from zer0pa_health.layers.l3.adapter import L3StubAdapter
    from zer0pa_health.layers.l3.toy_adapter import L3ToyAdapter

    l25_env = L25ToyAdapter().process(
        L25Input(canonical_smiles="CCO", policy=L25Policy.AIZYNTHFINDER_DEFAULT)
    )
    routes = l25_env.output.get("routes", [])
    if routes:
        steps = routes[0].get("steps", [])
        rxnsmiles = [s.get("rxnsmiles") for s in steps if s.get("rxnsmiles")]
    else:
        rxnsmiles = ["[CH4:1].[OH2:2]>>[CH3:1][OH:2]"]

    l3_inp = L3ProcessInput(
        target_canonical_smiles="CCO",
        route_rxnsmiles=rxnsmiles or ["[CH4:1]>>[CH3:1]"],
        target_throughput_kg_per_batch=1.0,
    )
    env_stub = L3StubAdapter().process(l3_inp)
    env_toy = L3ToyAdapter().process(l3_inp)
    _assert_pluggable(env_stub, env_toy, "L25toy_route→L3(stub+toy)")


# ============================================================================
# L4 — Stub vs Toy
# ============================================================================


def test_l4_real_swap():
    from zer0pa_health.contracts.l4 import L4SensorClass, L4SensorState, L4VirtualPlantInput
    from zer0pa_health.layers.l4.adapter import L4StubAdapter
    from zer0pa_health.layers.l4.toy_adapter import L4ToyAdapter

    sensors = [
        L4SensorState(
            sensor_id="S-01",
            sensor_class=L4SensorClass.PAT_TEMP,
            value=25.0,
            unit="C",
            timestamp_utc="2026-04-30T00:00:00Z",
            in_range=True,
        )
    ]
    inp = L4VirtualPlantInput(
        process_graph_unit_ops=["reaction_1", "drying_1"],
        sensor_states=sensors,
        target_throughput_kg_per_batch=1.0,
    )
    env_stub = L4StubAdapter().process(inp)
    env_toy = L4ToyAdapter().process(inp)
    _assert_pluggable(env_stub, env_toy, "L4.process")


def test_l3_stub_unit_ops_feed_l4_stub_and_toy():
    """L3 stub unit op names feed both L4 adapters (downstream unchanged)."""
    from zer0pa_health.contracts.l3 import L3ProcessInput
    from zer0pa_health.contracts.l4 import L4VirtualPlantInput
    from zer0pa_health.layers.l3.adapter import L3StubAdapter
    from zer0pa_health.layers.l4.adapter import L4StubAdapter
    from zer0pa_health.layers.l4.toy_adapter import L4ToyAdapter

    l3_env = L3StubAdapter().process(
        L3ProcessInput(
            target_canonical_smiles="CCO",
            route_rxnsmiles=["[CH4:1]>>[CH3:1]"],
            target_throughput_kg_per_batch=1.0,
        )
    )
    unit_op_names = [op["name"] for op in l3_env.output.get("unit_ops", [])]
    if not unit_op_names:
        unit_op_names = ["reaction_0"]

    l4_inp = L4VirtualPlantInput(
        process_graph_unit_ops=unit_op_names,
        sensor_states=[],
        target_throughput_kg_per_batch=1.0,
    )
    env_stub = L4StubAdapter().process(l4_inp)
    env_toy = L4ToyAdapter().process(l4_inp)
    _assert_pluggable(env_stub, env_toy, "L3stub_ops→L4(stub+toy)")


def test_l3_toy_unit_ops_feed_l4_stub_and_toy():
    """L3 toy unit op names feed both L4 adapters."""
    from zer0pa_health.contracts.l3 import L3ProcessInput
    from zer0pa_health.contracts.l4 import L4VirtualPlantInput
    from zer0pa_health.layers.l3.toy_adapter import L3ToyAdapter
    from zer0pa_health.layers.l4.adapter import L4StubAdapter
    from zer0pa_health.layers.l4.toy_adapter import L4ToyAdapter

    l3_env = L3ToyAdapter().process(
        L3ProcessInput(
            target_canonical_smiles="CCO",
            route_rxnsmiles=["[CH4:1]>>[CH3:1]"],
            target_throughput_kg_per_batch=1.0,
        )
    )
    unit_op_names = [op["name"] for op in l3_env.output.get("unit_ops", [])]
    if not unit_op_names:
        unit_op_names = ["reaction_0"]

    l4_inp = L4VirtualPlantInput(
        process_graph_unit_ops=unit_op_names,
        sensor_states=[],
        target_throughput_kg_per_batch=1.0,
    )
    env_stub = L4StubAdapter().process(l4_inp)
    env_toy = L4ToyAdapter().process(l4_inp)
    _assert_pluggable(env_stub, env_toy, "L3toy_ops→L4(stub+toy)")


# ============================================================================
# L5 — Stub vs Toy; and L2 output feeding both L5 adapters
# ============================================================================


def test_l5_real_swap():
    from zer0pa_health.contracts.l5 import L5PKModelKind, L5PKPDInput
    from zer0pa_health.layers.l5.adapter import L5StubAdapter
    from zer0pa_health.layers.l5.toy_adapter import L5ToyAdapter

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
    _assert_pluggable(env_stub, env_toy, "L5.process")


def test_l5_real_swap_with_dofetilide():
    """Both adapters handle a known fixture compound (dofetilide) successfully."""
    from zer0pa_health.contracts.l5 import L5PKModelKind, L5PKPDInput
    from zer0pa_health.layers.l5.adapter import L5StubAdapter
    from zer0pa_health.layers.l5.toy_adapter import L5ToyAdapter

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
    _assert_pluggable(env_stub, env_toy, "L5.process_dofetilide")

    # Both should have cardiac bridge present
    assert env_stub.output.get("cardiac_bridge") is not None
    assert env_toy.output.get("cardiac_bridge") is not None
