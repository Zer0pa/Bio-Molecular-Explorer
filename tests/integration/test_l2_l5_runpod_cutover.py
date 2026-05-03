"""L2 + L5 Runpod-sim cutover acceptance tests."""

from __future__ import annotations

import json
from pathlib import Path

from zer0pa_biomolecular_explorer.contracts.l2 import L2MoleculeInput, L2PropertyInput
from zer0pa_biomolecular_explorer.contracts.l5 import L5PKModelKind, L5PKPDInput
from zer0pa_biomolecular_explorer.envelope import Backend, FalsifierStatus
from zer0pa_biomolecular_explorer.falsifiers.detectors import detect_plug_replaceability_regression
from zer0pa_biomolecular_explorer.layers.l2.adapter import L2StubAdapter
from zer0pa_biomolecular_explorer.layers.l5.adapter import L5StubAdapter
from zer0pa_biomolecular_explorer.runpod_sim import L2RunpodSimAdapter, L5RunpodSimAdapter


def _envelope_keys(env) -> dict:
    return {k: type(v).__name__ for k, v in env.output.items()}


# ---------- L2 cutover ----------


def test_l2_runpod_sim_envelope_shape_matches_stub():
    inp = L2PropertyInput(molecule=L2MoleculeInput(smiles="CCO"))
    stub = L2StubAdapter()
    sim = L2RunpodSimAdapter()
    env_stub = stub.process(inp)
    env_sim = sim.process(inp)
    res = detect_plug_replaceability_regression(_envelope_keys(env_stub), _envelope_keys(env_sim))
    assert res.status == FalsifierStatus.PASS, res.evidence


def test_l2_runpod_sim_backend_is_runpod_gpu():
    sim = L2RunpodSimAdapter()
    env = sim.process(L2PropertyInput(molecule=L2MoleculeInput(smiles="CCO")))
    assert env.tool_adapter.backend == Backend.RUNPOD_GPU.value


def test_l2_runpod_sim_invalid_smiles_still_caught():
    sim = L2RunpodSimAdapter()
    env = sim.process(L2PropertyInput(molecule=L2MoleculeInput(smiles="C C")))
    assert env.falsifier.status == FalsifierStatus.FAIL
    classes = {it.falsifier_class for it in env.falsifier.items}
    assert "invalid_molecular_input" in classes


def test_l2_runpod_sim_validates_against_jsonschema():
    import jsonschema

    schema_path = (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "envelope"
        / "layer-envelope-v1.json"
    )
    schema = json.loads(schema_path.read_text())
    sim = L2RunpodSimAdapter()
    env = sim.process(L2PropertyInput(molecule=L2MoleculeInput(smiles="CCO")))
    jsonschema.validate(json.loads(env.dump_json()), schema)


# ---------- L5 cutover ----------


def test_l5_runpod_sim_envelope_shape_matches_stub():
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
    stub = L5StubAdapter()
    sim = L5RunpodSimAdapter()
    env_stub = stub.process(inp)
    env_sim = sim.process(inp)
    res = detect_plug_replaceability_regression(_envelope_keys(env_stub), _envelope_keys(env_sim))
    assert res.status == FalsifierStatus.PASS, res.evidence


def test_l5_runpod_sim_backend_is_runpod_gpu():
    sim = L5RunpodSimAdapter()
    env = sim.process(
        L5PKPDInput(
            canonical_smiles="CCO",
            inchikey="LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
            dose_mg=0.5,
            model_kind=L5PKModelKind.ONE_COMPARTMENT,
        )
    )
    assert env.tool_adapter.backend == Backend.RUNPOD_GPU.value


def test_l5_runpod_sim_emits_cardiac_bridge():
    sim = L5RunpodSimAdapter()
    env = sim.process(
        L5PKPDInput(
            canonical_smiles="CCO",
            inchikey="LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
            dose_mg=0.5,
            model_kind=L5PKModelKind.ONE_COMPARTMENT,
        )
    )
    bridge = env.output["cardiac_bridge"]
    assert "fractional_block_at_cmax" in bridge
    assert "multi_current_balance_score" in bridge


def test_l5_runpod_sim_validates_against_jsonschema():
    import jsonschema

    schema_path = (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "envelope"
        / "layer-envelope-v1.json"
    )
    schema = json.loads(schema_path.read_text())
    sim = L5RunpodSimAdapter()
    env = sim.process(
        L5PKPDInput(
            canonical_smiles="CCO",
            inchikey="LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
            dose_mg=0.5,
            model_kind=L5PKModelKind.ONE_COMPARTMENT,
        )
    )
    jsonschema.validate(json.loads(env.dump_json()), schema)


def test_l2_l5_chained_with_runpod_sims_works():
    """L2 sim -> L5 sim: both runpod_gpu, downstream parses unchanged."""
    sim_l2 = L2RunpodSimAdapter()
    sim_l5 = L5RunpodSimAdapter()
    e_l2 = sim_l2.process(L2PropertyInput(molecule=L2MoleculeInput(smiles="CCO")))
    e_l5 = sim_l5.process(
        L5PKPDInput(
            canonical_smiles="CCO",
            inchikey="LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
            dose_mg=0.5,
            model_kind=L5PKModelKind.ONE_COMPARTMENT,
        )
    )
    assert e_l2.tool_adapter.backend == Backend.RUNPOD_GPU.value
    assert e_l5.tool_adapter.backend == Backend.RUNPOD_GPU.value
    assert e_l2.contract_version == e_l5.contract_version == "zer0pa.layer-envelope.v1"
