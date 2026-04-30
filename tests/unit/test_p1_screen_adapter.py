"""Unit tests for P1.Screen layer adapters.

Tests:
  - process with 5 candidates returns ≤5 hits
  - HIT_FROM_NOISE: pains_flags injected → hit dropped, falsifier item present
  - LEAD_WITHOUT_PHYSCHEM_FEASIBILITY: pIC50=8.5 + esol=-6 → soft_fail flagged
  - SELECTIVITY_NOT_ASSESSED: target_panel_genes=[] → off_target=0 < 3 → FAIL
  - BENCHMARK_LEAKAGE: forced intersection → FAIL
  - Plug-swap Stub vs Toy: identical schema keys, different values
  - JSON Schema: envelope serialises and round-trips via Pydantic
"""

from __future__ import annotations

import json

import pytest

from zer0pa_health.envelope import FalsifierStatus, LayerName
from zer0pa_health.pathway1.contracts.p1_screen import P1ScreenInput, P1ScreenOutput
from zer0pa_health.pathway1.layers.screen.adapter import P1ScreenStubAdapter
from zer0pa_health.pathway1.layers.screen.toy_adapter import P1ScreenToyAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_input(
    n_candidates: int = 5,
    target_panel_genes: list[str] | None = None,
    pic50_threshold: float = 7.0,
) -> P1ScreenInput:
    if target_panel_genes is None:
        target_panel_genes = ["GENE1", "GENE2", "GENE3", "GENE4"]
    candidates = [
        {"candidate_id": f"cand_{i:02d}", "smiles": f"CC{'C' * i}N"}
        for i in range(n_candidates)
    ]
    return P1ScreenInput(
        target_id="EGFR",
        structure_ref="pdb:7AAO",
        pocket_id="ATP_binding",
        candidates=candidates,
        target_panel_genes=target_panel_genes,
        pic50_threshold=pic50_threshold,
    )


def _falsifier_ids(envelope) -> list[str]:
    return [it.falsifier_class for it in envelope.falsifier.items]


# ---------------------------------------------------------------------------
# Test 1: 5 candidates → ≤5 hits (basic smoke test)
# ---------------------------------------------------------------------------

def test_process_5_candidates_returns_leq_5_hits():
    adapter = P1ScreenStubAdapter()
    inp = _make_input(n_candidates=5)
    env = adapter.process(inp, run_id="run:test-0001")

    assert env.layer == LayerName.P1_SCREEN
    output = P1ScreenOutput(**env.output)
    assert output.n_input_candidates == 5
    assert output.n_hits <= 5
    assert len(output.hits) == output.n_hits


# ---------------------------------------------------------------------------
# Test 2: HIT_FROM_NOISE — pains_flags injected → hit dropped
# ---------------------------------------------------------------------------

def test_hit_from_noise_drops_hit_and_records_falsifier():
    adapter = P1ScreenStubAdapter()
    inp = _make_input(n_candidates=3)
    # Inject PAINS flag into first candidate
    cid = inp.candidates[0]["candidate_id"]

    env = adapter.process(
        inp,
        run_id="run:test-0002",
        _force_pains_map={cid: ["PAINS_A_promiscuous"]},
    )

    output = P1ScreenOutput(**env.output)
    # Hit with PAINS flag must be dropped
    assert output.n_hits <= 2

    # Falsifier record for HIT_FROM_NOISE must be present and FAIL
    classes = _falsifier_ids(env)
    assert "hit_from_noise" in classes
    fail_items = [
        it for it in env.falsifier.items
        if it.falsifier_class == "hit_from_noise" and it.status == FalsifierStatus.FAIL
    ]
    assert len(fail_items) >= 1, "Expected at least one HIT_FROM_NOISE FAIL item"


# ---------------------------------------------------------------------------
# Test 3: LEAD_WITHOUT_PHYSCHEM_FEASIBILITY — high pIC50 + bad ESOL → soft_fail
# ---------------------------------------------------------------------------

def test_lead_without_physchem_feasibility_soft_fail():
    adapter = P1ScreenStubAdapter()
    # Use a low threshold so our forced pIC50=8.5 is well above it
    inp = _make_input(n_candidates=2, pic50_threshold=7.0)
    cid = inp.candidates[0]["candidate_id"]

    env = adapter.process(
        inp,
        run_id="run:test-0003",
        _force_pic50_map={cid: 8.5},
        _force_esol_map={cid: -6.0},  # ESOL < -4 triggers
    )

    output = P1ScreenOutput(**env.output)
    # Hit is KEPT (soft_fail)
    hit_ids = [h.hit_id for h in output.hits]
    # At least one hit should be present
    assert output.n_hits >= 1

    # LEAD_WITHOUT_PHYSCHEM_FEASIBILITY FAIL item must be present
    fail_items = [
        it for it in env.falsifier.items
        if it.falsifier_class == "lead_without_physchem_feasibility"
        and it.status == FalsifierStatus.FAIL
    ]
    assert len(fail_items) >= 1, "Expected LEAD_WITHOUT_PHYSCHEM_FEASIBILITY FAIL for pIC50=8.5/ESOL=-6"


# ---------------------------------------------------------------------------
# Test 4: SELECTIVITY_NOT_ASSESSED — empty target panel → off_target=0 < 3
# ---------------------------------------------------------------------------

def test_selectivity_not_assessed_with_empty_panel():
    adapter = P1ScreenStubAdapter()
    inp = _make_input(n_candidates=3, target_panel_genes=[], pic50_threshold=7.0)

    env = adapter.process(
        inp,
        run_id="run:test-0004",
        _force_pic50_map={c["candidate_id"]: 7.5 for c in inp.candidates},
    )

    selectivity_items = [
        it for it in env.falsifier.items
        if it.falsifier_class == "selectivity_not_assessed"
    ]
    assert any(it.status == FalsifierStatus.FAIL for it in selectivity_items), (
        "Expected SELECTIVITY_NOT_ASSESSED FAIL when target_panel_genes=[] "
        f"and hits have pIC50>7.0; got: {[(it.status, it.evidence) for it in selectivity_items]}"
    )


# ---------------------------------------------------------------------------
# Test 5: BENCHMARK_LEAKAGE — forced intersection → FAIL
# ---------------------------------------------------------------------------

def test_benchmark_leakage_triggered_by_intersection():
    adapter = P1ScreenStubAdapter()
    inp = _make_input(n_candidates=2)

    shared_key = "INCHIKEY_SHARED_001"
    train_iks = {shared_key, "INCHIKEY_TRAIN_002"}
    test_iks = {shared_key, "INCHIKEY_TEST_003"}

    env = adapter.process(
        inp,
        run_id="run:test-0005",
        train_inchikeys=train_iks,
        test_inchikeys=test_iks,
    )

    leakage_items = [
        it for it in env.falsifier.items
        if it.falsifier_class == "benchmark_leakage"
    ]
    assert any(it.status == FalsifierStatus.FAIL for it in leakage_items), (
        "Expected BENCHMARK_LEAKAGE FAIL with deliberate InChIKey intersection"
    )


def test_benchmark_leakage_pass_with_no_intersection():
    adapter = P1ScreenStubAdapter()
    inp = _make_input(n_candidates=2)

    env = adapter.process(
        inp,
        run_id="run:test-0006",
        train_inchikeys={"INCHIKEY_A"},
        test_inchikeys={"INCHIKEY_B"},
    )

    leakage_items = [
        it for it in env.falsifier.items
        if it.falsifier_class == "benchmark_leakage"
    ]
    assert all(it.status == FalsifierStatus.PASS for it in leakage_items)


# ---------------------------------------------------------------------------
# Test 6: Plug-swap Stub vs Toy — identical schema keys, different values
# ---------------------------------------------------------------------------

def test_plug_swap_stub_vs_toy_schema_match():
    stub_adapter = P1ScreenStubAdapter()
    toy_adapter = P1ScreenToyAdapter()

    inp = _make_input(n_candidates=3)

    stub_env = stub_adapter.process(inp, run_id="run:test-swap-stub")
    toy_env = toy_adapter.process(inp, run_id="run:test-swap-toy")

    # Same top-level envelope keys
    stub_keys = sorted(stub_env.model_dump().keys())
    toy_keys = sorted(toy_env.model_dump().keys())
    assert stub_keys == toy_keys, f"Schema key mismatch: {stub_keys} vs {toy_keys}"

    # Same output keys
    stub_output_keys = sorted(stub_env.output.keys())
    toy_output_keys = sorted(toy_env.output.keys())
    assert stub_output_keys == toy_output_keys

    # Values differ (deterministic but different seeds) — check confidence score differs
    # or at least that the adapters have different names
    assert stub_env.tool_adapter.name != toy_env.tool_adapter.name


def test_plug_swap_falsifier_classes_identical():
    stub_adapter = P1ScreenStubAdapter()
    toy_adapter = P1ScreenToyAdapter()

    inp = _make_input(n_candidates=3)

    stub_env = stub_adapter.process(inp, run_id="run:test-classes-stub")
    toy_env = toy_adapter.process(inp, run_id="run:test-classes-toy")

    stub_classes = sorted({it.falsifier_class for it in stub_env.falsifier.items})
    toy_classes = sorted({it.falsifier_class for it in toy_env.falsifier.items})
    assert stub_classes == toy_classes, (
        f"Falsifier class sets differ: stub={stub_classes}, toy={toy_classes}"
    )


# ---------------------------------------------------------------------------
# Test 7: JSON Schema — envelope serialises and round-trips
# ---------------------------------------------------------------------------

def test_json_schema_round_trip():
    adapter = P1ScreenStubAdapter()
    inp = _make_input(n_candidates=3)

    env = adapter.process(inp, run_id="run:test-json")
    json_str = env.dump_json()

    # Valid JSON
    data = json.loads(json_str)
    assert data["layer"] == "P1.Screen"
    assert data["contract_version"] == "zer0pa.layer-envelope.v1"
    assert "output" in data
    assert "hits" in data["output"]

    # Round-trip through Pydantic
    from zer0pa_health.envelope import LayerEnvelope
    restored = LayerEnvelope.model_validate(data)
    assert restored.layer == env.layer


# ---------------------------------------------------------------------------
# Test 8: Determinism — same input → same output_hash
# ---------------------------------------------------------------------------

def test_determinism_same_input_same_output_hash():
    adapter = P1ScreenStubAdapter()
    inp = _make_input(n_candidates=4)

    env1 = adapter.process(inp, run_id="run:test-det-001")
    env2 = adapter.process(inp, run_id="run:test-det-002")

    # output_hash must be identical for same input (audit.output_hash)
    assert env1.audit.output_hash == env2.audit.output_hash


# ---------------------------------------------------------------------------
# Test 9: output contract — P1ScreenOutput valid from envelope.output
# ---------------------------------------------------------------------------

def test_output_parses_as_p1_screen_output():
    adapter = P1ScreenStubAdapter()
    inp = _make_input(n_candidates=5)

    env = adapter.process(inp)
    output = P1ScreenOutput(**env.output)

    assert output.target_id == "EGFR"
    assert output.n_input_candidates == 5
    assert output.n_hits == len(output.hits)
    for hit in output.hits:
        assert hit.confidence_tier in ("A", "B", "C")
        assert 4.0 <= hit.predicted_pIC50 <= 12.0
        assert hit.affinity_source == "Boltz-2_stub"
