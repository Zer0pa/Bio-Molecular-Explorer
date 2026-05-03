"""Unit tests for P1.Generate layer adapters.

Tests:
- process(library_size=10) returns 10 candidates
- scaffold_hop mode sets parent_scaffold on every candidate
- PRETRAINED_HALLUCINATION: injecting iron atom drops candidate
- IP_CHEMSPACE_DRIFT: force_ip_drift_fail=True triggers FAIL on all candidates
- Plug-swap Stub vs Toy: same envelope shape and falsifier-class set
- JSON Schema / Pydantic round-trip validation
"""

from __future__ import annotations

import json

import pytest

from zer0pa_biomolecular_explorer.envelope import FalsifierStatus, LayerName
from zer0pa_biomolecular_explorer.falsifiers.registry import FalsifierClass
from zer0pa_biomolecular_explorer.pathway1.contracts.p1_generate import P1GenerateInput
from zer0pa_biomolecular_explorer.pathway1.layers.generate.adapter import (
    P1GenerateStubAdapter,
    _SMILES_POOL,
)
from zer0pa_biomolecular_explorer.pathway1.layers.generate.toy_adapter import P1GenerateToyAdapter


# ── Helpers ────────────────────────────────────────────────────────────────────

def _basic_input(
    library_size: int = 10,
    mode: str = "sbdd",
    seed_scaffold: str | None = None,
) -> P1GenerateInput:
    return P1GenerateInput(
        target_id="TGT-TEST-001",
        structure_ref="struct-ref-001",
        pocket_id="pocket-A",
        mode=mode,
        library_size=library_size,
        seed_scaffold_smiles=seed_scaffold,
    )


def _falsifier_classes_in_envelope(envelope) -> set[str]:
    return {item.falsifier_class for item in envelope.falsifier.items}


# ── Test 1: library_size=10 → 10 candidates ───────────────────────────────────

def test_process_returns_10_candidates():
    adapter = P1GenerateStubAdapter()
    inp = _basic_input(library_size=10)
    env = adapter.process(inp, run_id="run:test-001")

    assert env.layer == LayerName.P1_GENERATE.value
    output = env.output
    assert output["library_size_actual"] == 10
    assert len(output["candidates"]) == 10


def test_candidate_ids_are_deterministic():
    adapter = P1GenerateStubAdapter()
    inp = _basic_input(library_size=10)
    env1 = adapter.process(inp, run_id="run:test-002")
    env2 = adapter.process(inp, run_id="run:test-003")
    ids1 = [c["candidate_id"] for c in env1.output["candidates"]]
    ids2 = [c["candidate_id"] for c in env2.output["candidates"]]
    assert ids1 == ids2, "Candidate IDs must be deterministic given the same input"


# ── Test 2: scaffold_hop sets parent_scaffold ──────────────────────────────────

def test_scaffold_hop_sets_parent_scaffold():
    adapter = P1GenerateStubAdapter()
    inp = _basic_input(library_size=10, mode="scaffold_hop", seed_scaffold="CCO")
    env = adapter.process(inp, run_id="run:test-004")
    candidates = env.output["candidates"]
    for c in candidates:
        assert c["parent_scaffold"] == "CCO", (
            f"Expected parent_scaffold='CCO', got {c['parent_scaffold']!r}"
        )


def test_sbdd_mode_no_parent_scaffold():
    adapter = P1GenerateStubAdapter()
    inp = _basic_input(library_size=10, mode="sbdd")
    env = adapter.process(inp, run_id="run:test-005")
    for c in env.output["candidates"]:
        assert c["parent_scaffold"] is None


# ── Test 3: PRETRAINED_HALLUCINATION — iron atom triggers drop ─────────────────

class _HallucinatingStubAdapter(P1GenerateStubAdapter):
    """Injects [Fe] into the first candidate SMILES to trigger PRETRAINED_HALLUCINATION."""

    def _maybe_inject_hallucination(self, smiles: str, idx: int, seed: str) -> str:
        if idx == 0:
            return smiles + "[Fe]"  # non-organic atom → detector FAILS
        return smiles


def test_pretrained_hallucination_drops_candidate():
    adapter = _HallucinatingStubAdapter()
    inp = _basic_input(library_size=10)
    env = adapter.process(inp, run_id="run:test-006")

    output = env.output
    # dropped_count must be at least 1
    assert output["dropped_count"] >= 1
    # library_size_actual must be < 10
    assert output["library_size_actual"] < 10

    # The overall envelope falsifier must be FAIL (hallucination FAIL propagates)
    assert env.falsifier.status == FalsifierStatus.FAIL.value

    # PRETRAINED_HALLUCINATION must appear in falsifier items with status FAIL
    hall_items = [
        it for it in env.falsifier.items
        if it.falsifier_class == FalsifierClass.PRETRAINED_HALLUCINATION.value
        and it.status == FalsifierStatus.FAIL.value
    ]
    assert len(hall_items) >= 1, "Expected at least one PRETRAINED_HALLUCINATION FAIL item"


def test_pretrained_hallucination_fail_evidence_mentions_atom():
    adapter = _HallucinatingStubAdapter()
    inp = _basic_input(library_size=10)
    env = adapter.process(inp, run_id="run:test-007")
    hall_fails = [
        it for it in env.falsifier.items
        if it.falsifier_class == FalsifierClass.PRETRAINED_HALLUCINATION.value
        and it.status == FalsifierStatus.FAIL.value
    ]
    assert hall_fails, "No PRETRAINED_HALLUCINATION FAIL found"
    evidence = " ".join(hall_fails[0].evidence)
    assert "Fe" in evidence or "non_organic_atom" in evidence


# ── Test 4: IP_CHEMSPACE_DRIFT via force flag ──────────────────────────────────

def test_ip_chemspace_drift_triggered_by_force_flag():
    adapter = P1GenerateStubAdapter(force_ip_drift_fail=True)
    inp = _basic_input(library_size=10)
    env = adapter.process(inp, run_id="run:test-008")

    # All IP drift checks should be FAIL
    ip_items = [
        it for it in env.falsifier.items
        if it.falsifier_class == FalsifierClass.IP_CHEMSPACE_DRIFT.value
    ]
    assert len(ip_items) > 0, "No IP_CHEMSPACE_DRIFT items found"
    for item in ip_items:
        assert item.status == FalsifierStatus.FAIL.value, (
            f"Expected FAIL, got {item.status} for {item}"
        )


def test_ip_chemspace_drift_passes_normally():
    adapter = P1GenerateStubAdapter(force_ip_drift_fail=False)
    inp = _basic_input(library_size=10)
    env = adapter.process(inp, run_id="run:test-009")
    # First 5 pool entries have Tanimoto well below 0.95 → all PASS
    ip_items = [
        it for it in env.falsifier.items
        if it.falsifier_class == FalsifierClass.IP_CHEMSPACE_DRIFT.value
    ]
    assert any(it.status == FalsifierStatus.PASS.value for it in ip_items)


# ── Test 5: Plug-swap Stub vs Toy — shape and falsifier-class set match ────────

def test_plug_swap_stub_vs_toy_same_output_shape():
    stub = P1GenerateStubAdapter()
    toy = P1GenerateToyAdapter()
    inp = _basic_input(library_size=10)
    env_stub = stub.process(inp, run_id="run:test-010")
    env_toy = toy.process(inp, run_id="run:test-011")

    # Both envelopes must have the same top-level output keys
    assert set(env_stub.output.keys()) == set(env_toy.output.keys()), (
        f"Output key mismatch: stub={set(env_stub.output.keys())} toy={set(env_toy.output.keys())}"
    )

    # Both must have same library_size_actual
    assert env_stub.output["library_size_actual"] == env_toy.output["library_size_actual"]

    # Each candidate in both envelopes must have the same field set
    if env_stub.output["candidates"] and env_toy.output["candidates"]:
        stub_cand_keys = set(env_stub.output["candidates"][0].keys())
        toy_cand_keys = set(env_toy.output["candidates"][0].keys())
        assert stub_cand_keys == toy_cand_keys, (
            f"Candidate key mismatch: stub={stub_cand_keys} toy={toy_cand_keys}"
        )


def test_plug_swap_stub_vs_toy_same_falsifier_class_set():
    stub = P1GenerateStubAdapter()
    toy = P1GenerateToyAdapter()
    inp = _basic_input(library_size=10)
    env_stub = stub.process(inp, run_id="run:test-012")
    env_toy = toy.process(inp, run_id="run:test-013")

    stub_classes = _falsifier_classes_in_envelope(env_stub)
    toy_classes = _falsifier_classes_in_envelope(env_toy)
    assert stub_classes == toy_classes, (
        f"Falsifier class set mismatch:\n  stub={sorted(stub_classes)}\n  toy={sorted(toy_classes)}"
    )


def test_plug_swap_toy_uses_different_smiles():
    stub = P1GenerateStubAdapter()
    toy = P1GenerateToyAdapter()
    inp = _basic_input(library_size=10)
    env_stub = stub.process(inp, run_id="run:test-014")
    env_toy = toy.process(inp, run_id="run:test-015")

    stub_smiles = {c["smiles"] for c in env_stub.output["candidates"]}
    toy_smiles = {c["smiles"] for c in env_toy.output["candidates"]}
    # Rotated pool means at least some SMILES differ
    assert stub_smiles != toy_smiles, "Toy adapter should use different SMILES pool"


# ── Test 6: JSON Schema / Pydantic round-trip ─────────────────────────────────

def test_envelope_json_roundtrip():
    adapter = P1GenerateStubAdapter()
    inp = _basic_input(library_size=10)
    env = adapter.process(inp, run_id="run:test-016")

    json_str = env.dump_json()
    data = json.loads(json_str)

    assert data["contract_version"] == "zer0pa.layer-envelope.v1"
    assert data["layer"] == "P1.Generate"
    assert data["tool_adapter"]["backend"] == "stub"
    assert data["confidence"]["score"] == 0.55
    assert "candidates" in data["output"]
    assert isinstance(data["output"]["candidates"], list)


def test_envelope_required_fields_present():
    adapter = P1GenerateStubAdapter()
    inp = _basic_input(library_size=10)
    env = adapter.process(inp, run_id="run:test-017")

    assert env.run_id == "run:test-017"
    assert env.layer == LayerName.P1_GENERATE.value
    assert env.confidence.score == 0.55
    assert env.confidence.basis == ["stub_canned_smiles_pool"]
    assert env.tool_adapter.backend == "stub"
    assert env.tool_adapter.engine == "stub_canned_smiles_pool"


# ── Test 7: novelty_without_tractability fires on some candidates ──────────────

def test_novelty_without_tractability_appears_in_items():
    adapter = P1GenerateStubAdapter()
    # library_size=20 covers all 20 pool entries, some of which are novel+intractable
    inp = _basic_input(library_size=20)
    env = adapter.process(inp, run_id="run:test-018")
    nov_classes = {
        it.falsifier_class for it in env.falsifier.items
        if it.falsifier_class == FalsifierClass.NOVELTY_WITHOUT_TRACTABILITY.value
    }
    assert FalsifierClass.NOVELTY_WITHOUT_TRACTABILITY.value in nov_classes


# ── Test 8: stub_laundering and clinical_overclaim always appear ───────────────

def test_stub_laundering_in_items():
    adapter = P1GenerateStubAdapter()
    env = adapter.process(_basic_input(), run_id="run:test-019")
    classes = _falsifier_classes_in_envelope(env)
    assert FalsifierClass.STUB_LAUNDERING.value in classes


def test_clinical_overclaim_in_items():
    adapter = P1GenerateStubAdapter()
    env = adapter.process(_basic_input(), run_id="run:test-020")
    classes = _falsifier_classes_in_envelope(env)
    assert FalsifierClass.CLINICAL_OVERCLAIM.value in classes


# ── Test 9: library_size capped at 50 ─────────────────────────────────────────

def test_library_size_capped_at_50():
    adapter = P1GenerateStubAdapter()
    inp = _basic_input(library_size=50)
    env = adapter.process(inp, run_id="run:test-021")
    # With no hallucination injections, should get exactly 50
    assert env.output["library_size_actual"] == 50


def test_candidate_generation_method_matches_mode():
    adapter = P1GenerateStubAdapter()
    for mode in ("de_novo", "sbdd", "linker", "fragment_grow", "binder_design"):
        inp = _basic_input(library_size=10, mode=mode)
        env = adapter.process(inp, run_id=f"run:test-mode-{mode}")
        for c in env.output["candidates"]:
            assert c["generation_method"] == mode
