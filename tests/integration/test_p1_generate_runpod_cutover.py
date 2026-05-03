"""Integration test: P1.Generate stub vs RunPod-sim shape match.

Verifies that swapping from P1GenerateStubAdapter to P1GenerateRunpodSimAdapter
produces envelopes with identical output schemas, identical falsifier-class sets,
and compatible confidence/layer metadata. This is the cutover-acceptance gate.
"""

from __future__ import annotations

import json

import pytest

from zer0pa_biomolecular_explorer.envelope import FalsifierStatus, LayerName
from zer0pa_biomolecular_explorer.falsifiers.registry import FalsifierClass
from zer0pa_biomolecular_explorer.pathway1.contracts.p1_generate import P1GenerateInput
from zer0pa_biomolecular_explorer.pathway1.layers.generate.adapter import P1GenerateStubAdapter
from zer0pa_biomolecular_explorer.runpod_sim.p1_generate_runpod_sim import P1GenerateRunpodSimAdapter


# ── Helpers ────────────────────────────────────────────────────────────────────

def _input(library_size: int = 10, mode: str = "sbdd") -> P1GenerateInput:  # noqa: PLR0913
    return P1GenerateInput(
        target_id="TGT-CUTOVER-001",
        structure_ref="struct-cutover-001",
        pocket_id="pocket-B",
        mode=mode,
        library_size=library_size,
    )


def _falsifier_classes(env) -> set[str]:
    return {it.falsifier_class for it in env.falsifier.items}


# ── Test 1: Output schema keys match ──────────────────────────────────────────

def test_output_schema_keys_match():
    stub = P1GenerateStubAdapter()
    runpod = P1GenerateRunpodSimAdapter()
    inp = _input(library_size=10)

    env_stub = stub.process(inp, run_id="run:cutover-001")
    env_runpod = runpod.process(inp, run_id="run:cutover-002")

    assert set(env_stub.output.keys()) == set(env_runpod.output.keys()), (
        f"Output key mismatch:\n  stub={sorted(env_stub.output.keys())}\n"
        f"  runpod={sorted(env_runpod.output.keys())}"
    )


def test_candidate_field_keys_match():
    stub = P1GenerateStubAdapter()
    runpod = P1GenerateRunpodSimAdapter()
    inp = _input(library_size=10)

    env_stub = stub.process(inp, run_id="run:cutover-003")
    env_runpod = runpod.process(inp, run_id="run:cutover-004")

    stub_cands = env_stub.output["candidates"]
    runpod_cands = env_runpod.output["candidates"]

    assert len(stub_cands) > 0, "Stub produced zero candidates"
    assert len(runpod_cands) > 0, "RunPod sim produced zero candidates"

    stub_keys = set(stub_cands[0].keys())
    runpod_keys = set(runpod_cands[0].keys())
    assert stub_keys == runpod_keys, (
        f"Candidate field mismatch:\n  stub={sorted(stub_keys)}\n  runpod={sorted(runpod_keys)}"
    )


# ── Test 2: Falsifier-class set matches ────────────────────────────────────────

def test_falsifier_class_set_matches():
    stub = P1GenerateStubAdapter()
    runpod = P1GenerateRunpodSimAdapter()
    inp = _input(library_size=10)

    env_stub = stub.process(inp, run_id="run:cutover-005")
    env_runpod = runpod.process(inp, run_id="run:cutover-006")

    stub_classes = _falsifier_classes(env_stub)
    runpod_classes = _falsifier_classes(env_runpod)

    assert stub_classes == runpod_classes, (
        f"Falsifier class set mismatch:\n  stub={sorted(stub_classes)}\n"
        f"  runpod={sorted(runpod_classes)}"
    )


# ── Test 3: Layer name same ────────────────────────────────────────────────────

def test_layer_name_same():
    stub = P1GenerateStubAdapter()
    runpod = P1GenerateRunpodSimAdapter()
    inp = _input()

    env_stub = stub.process(inp, run_id="run:cutover-007")
    env_runpod = runpod.process(inp, run_id="run:cutover-008")

    assert env_stub.layer == env_runpod.layer == LayerName.P1_GENERATE.value


# ── Test 4: Backend differs (stub vs runpod_gpu) ──────────────────────────────

def test_backend_differs():
    stub = P1GenerateStubAdapter()
    runpod = P1GenerateRunpodSimAdapter()
    inp = _input(library_size=10)

    env_stub = stub.process(inp, run_id="run:cutover-009")
    env_runpod = runpod.process(inp, run_id="run:cutover-010")

    assert env_stub.tool_adapter.backend == "stub"
    assert env_runpod.tool_adapter.backend == "runpod_gpu"
    assert env_stub.output["backend_used"] == "stub"
    assert env_runpod.output["backend_used"] == "runpod_gpu"


# ── Test 5: RunPod uses different SMILES pool ─────────────────────────────────

def test_runpod_uses_different_smiles_pool():
    stub = P1GenerateStubAdapter()
    runpod = P1GenerateRunpodSimAdapter()
    inp = _input(library_size=10)

    env_stub = stub.process(inp, run_id="run:cutover-011")
    env_runpod = runpod.process(inp, run_id="run:cutover-012")

    stub_smiles = {c["smiles"] for c in env_stub.output["candidates"]}
    runpod_smiles = {c["smiles"] for c in env_runpod.output["candidates"]}

    assert stub_smiles != runpod_smiles, (
        "RunPod-sim should use a rotated pool giving different SMILES"
    )


# ── Test 6: JSON round-trip works for both ────────────────────────────────────

def test_json_roundtrip_both_adapters():
    for AdapterCls, run_id_suffix, expected_backend in [
        (P1GenerateStubAdapter, "013", "stub"),
        (P1GenerateRunpodSimAdapter, "014", "runpod_gpu"),
    ]:
        adapter = AdapterCls()
        env = adapter.process(_input(library_size=10), run_id=f"run:cutover-{run_id_suffix}")
        json_str = env.dump_json()
        data = json.loads(json_str)

        assert data["contract_version"] == "zer0pa.layer-envelope.v1"
        assert data["layer"] == "P1.Generate"
        assert data["tool_adapter"]["backend"] == expected_backend
        assert isinstance(data["output"]["candidates"], list)


# ── Test 7: library_size_actual matches between adapters ─────────────────────

def test_library_size_actual_matches():
    stub = P1GenerateStubAdapter()
    runpod = P1GenerateRunpodSimAdapter()
    inp = _input(library_size=15)

    env_stub = stub.process(inp, run_id="run:cutover-015")
    env_runpod = runpod.process(inp, run_id="run:cutover-016")

    assert env_stub.output["library_size_actual"] == env_runpod.output["library_size_actual"], (
        "library_size_actual must match between stub and runpod-sim for the same input"
    )


# ── Test 8: Engine name differs ──────────────────────────────────────────────

def test_engine_name_differs():
    stub = P1GenerateStubAdapter()
    runpod = P1GenerateRunpodSimAdapter()
    inp = _input()

    env_stub = stub.process(inp, run_id="run:cutover-017")
    env_runpod = runpod.process(inp, run_id="run:cutover-018")

    assert env_stub.tool_adapter.engine != env_runpod.tool_adapter.engine
    assert env_runpod.tool_adapter.engine == "reinvent4_runpod_sim"


# ── Test 9: Confidence band is LOW for stub (score 0.55) ─────────────────────

def test_confidence_score_stub():
    stub = P1GenerateStubAdapter()
    env = stub.process(_input(), run_id="run:cutover-019")
    assert env.confidence.score == 0.55
    assert env.confidence.band == "low"
