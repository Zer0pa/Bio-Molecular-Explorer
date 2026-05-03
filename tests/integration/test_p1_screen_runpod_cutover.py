"""Integration test: P1.Screen stub vs RunPod-sim shape match (cutover acceptance).

Verifies that swapping P1ScreenStubAdapter for P1ScreenRunpodSimAdapter:
  1. Preserves the top-level LayerEnvelope schema
  2. Preserves the output dict keys (P1ScreenOutput shape)
  3. Preserves the falsifier class set
  4. Changes the backend (stub → runpod_gpu)
  5. Changes the engine string
  6. Both produce valid P1ScreenOutput parseable from envelope.output
"""

from __future__ import annotations

import pytest

from zer0pa_biomolecular_explorer.envelope import Backend, FalsifierStatus, LayerName
from zer0pa_biomolecular_explorer.pathway1.contracts.p1_screen import P1ScreenInput, P1ScreenOutput
from zer0pa_biomolecular_explorer.pathway1.layers.screen.adapter import P1ScreenStubAdapter
from zer0pa_biomolecular_explorer.runpod_sim.p1_screen_runpod_sim import P1ScreenRunpodSimAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_input(n: int = 4, target_panel_genes: list[str] | None = None) -> P1ScreenInput:
    if target_panel_genes is None:
        target_panel_genes = ["GENE_A", "GENE_B", "GENE_C", "GENE_D"]
    return P1ScreenInput(
        target_id="BRAF",
        structure_ref="pdb:6PP9",
        pocket_id="kinase_domain",
        candidates=[
            {"candidate_id": f"mol_{i:03d}", "smiles": f"c1ccccc1{'N' * (i + 1)}"}
            for i in range(n)
        ],
        target_panel_genes=target_panel_genes,
        pic50_threshold=7.0,
    )


# ---------------------------------------------------------------------------
# Test 1: Envelope schema keys match between stub and runpod_sim
# ---------------------------------------------------------------------------

def test_envelope_schema_keys_match():
    stub = P1ScreenStubAdapter()
    runpod = P1ScreenRunpodSimAdapter()

    inp = _make_input()
    stub_env = stub.process(inp, run_id="run:cutover-stub")
    runpod_env = runpod.process(inp, run_id="run:cutover-runpod")

    stub_keys = sorted(stub_env.model_dump().keys())
    runpod_keys = sorted(runpod_env.model_dump().keys())
    assert stub_keys == runpod_keys, (
        f"Top-level schema key mismatch:\nstub={stub_keys}\nrunpod={runpod_keys}"
    )


# ---------------------------------------------------------------------------
# Test 2: Output dict keys match (P1ScreenOutput shape)
# ---------------------------------------------------------------------------

def test_output_dict_keys_match():
    stub = P1ScreenStubAdapter()
    runpod = P1ScreenRunpodSimAdapter()

    inp = _make_input()
    stub_env = stub.process(inp, run_id="run:cutover-out-stub")
    runpod_env = runpod.process(inp, run_id="run:cutover-out-runpod")

    stub_out_keys = sorted(stub_env.output.keys())
    runpod_out_keys = sorted(runpod_env.output.keys())
    assert stub_out_keys == runpod_out_keys, (
        f"output dict keys differ:\nstub={stub_out_keys}\nrunpod={runpod_out_keys}"
    )


# ---------------------------------------------------------------------------
# Test 3: Both output parseable as P1ScreenOutput
# ---------------------------------------------------------------------------

def test_both_outputs_parse_as_p1_screen_output():
    stub = P1ScreenStubAdapter()
    runpod = P1ScreenRunpodSimAdapter()

    inp = _make_input()

    for adapter, label in [(stub, "stub"), (runpod, "runpod_sim")]:
        env = adapter.process(inp, run_id=f"run:cutover-parse-{label}")
        output = P1ScreenOutput(**env.output)
        assert output.target_id == "BRAF", f"{label}: wrong target_id"
        assert output.n_input_candidates == 4, f"{label}: wrong n_input_candidates"
        assert output.n_hits == len(output.hits), f"{label}: n_hits mismatch"
        for hit in output.hits:
            assert hit.confidence_tier in ("A", "B", "C"), f"{label}: invalid tier"
            assert 4.0 <= hit.predicted_pIC50 <= 12.0, f"{label}: pIC50 out of range"


# ---------------------------------------------------------------------------
# Test 4: Falsifier class sets match
# ---------------------------------------------------------------------------

def test_falsifier_class_sets_match():
    stub = P1ScreenStubAdapter()
    runpod = P1ScreenRunpodSimAdapter()

    inp = _make_input()
    stub_env = stub.process(inp, run_id="run:cutover-fc-stub")
    runpod_env = runpod.process(inp, run_id="run:cutover-fc-runpod")

    stub_classes = sorted({it.falsifier_class for it in stub_env.falsifier.items})
    runpod_classes = sorted({it.falsifier_class for it in runpod_env.falsifier.items})
    assert stub_classes == runpod_classes, (
        f"Falsifier class sets differ:\nstub={stub_classes}\nrunpod={runpod_classes}"
    )


# ---------------------------------------------------------------------------
# Test 5: Backend changes stub → runpod_gpu
# ---------------------------------------------------------------------------

def test_backend_changes_on_cutover():
    stub = P1ScreenStubAdapter()
    runpod = P1ScreenRunpodSimAdapter()

    inp = _make_input()
    stub_env = stub.process(inp, run_id="run:cutover-be-stub")
    runpod_env = runpod.process(inp, run_id="run:cutover-be-runpod")

    assert stub_env.tool_adapter.backend == Backend.STUB.value
    assert runpod_env.tool_adapter.backend == Backend.RUNPOD_GPU.value


# ---------------------------------------------------------------------------
# Test 6: Engine strings differ
# ---------------------------------------------------------------------------

def test_engine_strings_differ():
    stub = P1ScreenStubAdapter()
    runpod = P1ScreenRunpodSimAdapter()

    inp = _make_input()
    stub_env = stub.process(inp, run_id="run:cutover-eng-stub")
    runpod_env = runpod.process(inp, run_id="run:cutover-eng-runpod")

    assert stub_env.tool_adapter.engine != runpod_env.tool_adapter.engine


# ---------------------------------------------------------------------------
# Test 7: Layer is P1_SCREEN on both
# ---------------------------------------------------------------------------

def test_layer_is_p1_screen_on_both():
    stub = P1ScreenStubAdapter()
    runpod = P1ScreenRunpodSimAdapter()

    inp = _make_input()
    for adapter, label in [(stub, "stub"), (runpod, "runpod_sim")]:
        env = adapter.process(inp, run_id=f"run:cutover-layer-{label}")
        assert env.layer == LayerName.P1_SCREEN, (
            f"{label}: expected P1_SCREEN, got {env.layer!r}"
        )


# ---------------------------------------------------------------------------
# Test 8: Values differ between stub and runpod_sim (different seeds)
# ---------------------------------------------------------------------------

def test_values_differ_between_stub_and_runpod_sim():
    stub = P1ScreenStubAdapter()
    runpod = P1ScreenRunpodSimAdapter()

    inp = _make_input()
    stub_env = stub.process(inp, run_id="run:cutover-val-stub")
    runpod_env = runpod.process(inp, run_id="run:cutover-val-runpod")

    # output_hash should differ (different seed → different values)
    assert stub_env.audit.output_hash != runpod_env.audit.output_hash, (
        "Expected different output_hash for stub vs runpod_sim (different deterministic seeds)"
    )


# ---------------------------------------------------------------------------
# Test 9: hit_id keys present in hits
# ---------------------------------------------------------------------------

def test_hits_have_required_fields():
    runpod = P1ScreenRunpodSimAdapter()
    inp = _make_input(n=3)
    env = runpod.process(inp, run_id="run:cutover-fields")
    output = P1ScreenOutput(**env.output)

    for hit in output.hits:
        assert hit.hit_id, "hit_id must be non-empty"
        assert hit.smiles, "smiles must be non-empty"
        assert hit.target_id == "BRAF"
        assert hit.affinity_source == "Boltz-2_stub"
        assert hit.off_target_prediction_count == len(inp.target_panel_genes)
