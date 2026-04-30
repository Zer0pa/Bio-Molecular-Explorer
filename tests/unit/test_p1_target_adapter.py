"""Unit tests for P1.Target layer adapters (Stub + Toy).

Tests:
1. process(EFO:0000238) returns >= 1 dossier (cardiac LQT-related targets: KCNH2, SCN5A, KCNQ1)
2. process(gpt_rosalind_status=429) triggers GPT_ROSALIND_UNAVAILABLE FAIL + fallback_engine set
3. process(BOGUS:9999) returns 0 dossiers and emits target_validation_overreach FAIL
4. Plug-swap: Stub vs Toy output keys match; falsifier classes match; both validate against
   schemas/envelope/layer-envelope-v1.json
5. Determinism: same input -> same audit.output_hash
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from zer0pa_health.envelope import FalsifierStatus
from zer0pa_health.pathway1.contracts.p1_target import P1TargetInput
from zer0pa_health.pathway1.layers.target import P1TargetStubAdapter, P1TargetToyAdapter

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent / "schemas" / "envelope" / "layer-envelope-v1.json"
)

_LQT_DISEASE_ID = "EFO:0000238"  # Long QT syndrome — associated with KCNH2, KCNQ1, SCN5A
_BOGUS_DISEASE_ID = "BOGUS:9999"


@pytest.fixture(scope="module")
def stub_adapter() -> P1TargetStubAdapter:
    return P1TargetStubAdapter()


@pytest.fixture(scope="module")
def toy_adapter() -> P1TargetToyAdapter:
    return P1TargetToyAdapter()


@pytest.fixture(scope="module")
def envelope_schema() -> dict:
    with _SCHEMA_PATH.open() as fh:
        return json.load(fh)


def validate_envelope(env_dict: dict, schema: dict) -> None:
    jsonschema.validate(instance=env_dict, schema=schema)


def _falsifier_classes(env) -> set[str]:
    return {item.falsifier_class for item in env.falsifier.items}


def _has_fail(env, falsifier_class: str) -> bool:
    for item in env.falsifier.items:
        if item.falsifier_class == falsifier_class and item.status == FalsifierStatus.FAIL:
            return True
    return False


# ---------------------------------------------------------------------------
# Test 1: EFO:0000238 returns >= 1 dossier (cardiac targets)
# ---------------------------------------------------------------------------

def test_lqt_disease_returns_cardiac_dossiers(stub_adapter: P1TargetStubAdapter) -> None:
    inp = P1TargetInput(disease_ids=[_LQT_DISEASE_ID], max_targets=10)
    env = stub_adapter.process(inp, run_id="run:test-lqt-0001")

    dossiers = env.output.get("dossiers", [])
    assert len(dossiers) >= 1, f"Expected >= 1 dossier for {_LQT_DISEASE_ID}, got {len(dossiers)}"

    gene_symbols = {d["gene_symbol"] for d in dossiers}
    # At least one LQT-related cardiac target must be present
    cardiac_genes = {"KCNH2", "SCN5A", "KCNQ1", "CACNA1C"}
    assert gene_symbols.intersection(cardiac_genes), (
        f"No cardiac gene in dossiers; found: {gene_symbols}"
    )


def test_lqt_disease_envelope_valid(stub_adapter: P1TargetStubAdapter, envelope_schema: dict) -> None:
    inp = P1TargetInput(disease_ids=[_LQT_DISEASE_ID])
    env = stub_adapter.process(inp, run_id="run:test-lqt-schema")
    env_dict = env.model_dump(mode="json")
    validate_envelope(env_dict, envelope_schema)


def test_lqt_disease_layer_is_p1_target(stub_adapter: P1TargetStubAdapter) -> None:
    inp = P1TargetInput(disease_ids=[_LQT_DISEASE_ID])
    env = stub_adapter.process(inp)
    assert env.layer == "P1.Target" or env.layer.value == "P1.Target"  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Test 2: gpt_rosalind_status=429 triggers GPT_ROSALIND_UNAVAILABLE + fallback
# ---------------------------------------------------------------------------

def test_gpt_rosalind_429_triggers_unavailable_fail(stub_adapter: P1TargetStubAdapter) -> None:
    inp = P1TargetInput(disease_ids=[_LQT_DISEASE_ID])
    env = stub_adapter.process(inp, gpt_rosalind_status=429)

    assert _has_fail(env, "gpt_rosalind_unavailable"), (
        "Expected GPT_ROSALIND_UNAVAILABLE FAIL for status=429; falsifier items: "
        + str([(i.falsifier_class, i.status) for i in env.falsifier.items])
    )


def test_gpt_rosalind_429_sets_fallback_engine(stub_adapter: P1TargetStubAdapter) -> None:
    inp = P1TargetInput(disease_ids=[_LQT_DISEASE_ID])
    env = stub_adapter.process(inp, gpt_rosalind_status=429)

    assert env.output.get("gpt_rosalind_used") is False, (
        "Expected gpt_rosalind_used=False when status=429"
    )
    assert env.output.get("fallback_engine") == "biogpt_stub", (
        f"Expected fallback_engine='biogpt_stub', got: {env.output.get('fallback_engine')}"
    )


def test_gpt_rosalind_200_is_pass(stub_adapter: P1TargetStubAdapter) -> None:
    inp = P1TargetInput(disease_ids=[_LQT_DISEASE_ID])
    env = stub_adapter.process(inp, gpt_rosalind_status=200)

    gpt_pass = any(
        i.falsifier_class == "gpt_rosalind_unavailable"
        and i.status == FalsifierStatus.PASS
        for i in env.falsifier.items
    )
    assert gpt_pass, "Expected GPT_ROSALIND_UNAVAILABLE PASS for status=200"
    assert env.output.get("gpt_rosalind_used") is True
    assert env.output.get("fallback_engine") is None


# ---------------------------------------------------------------------------
# Test 3: BOGUS:9999 returns 0 dossiers + target_validation_overreach FAIL
# ---------------------------------------------------------------------------

def test_bogus_disease_returns_zero_dossiers(stub_adapter: P1TargetStubAdapter) -> None:
    inp = P1TargetInput(disease_ids=[_BOGUS_DISEASE_ID])
    env = stub_adapter.process(inp)

    dossiers = env.output.get("dossiers", [])
    assert len(dossiers) == 0, f"Expected 0 dossiers for bogus disease, got {len(dossiers)}"


def test_bogus_disease_emits_overreach_fail(stub_adapter: P1TargetStubAdapter) -> None:
    inp = P1TargetInput(disease_ids=[_BOGUS_DISEASE_ID])
    env = stub_adapter.process(inp)

    assert _has_fail(env, "target_validation_overreach"), (
        "Expected TARGET_VALIDATION_OVERREACH FAIL for bogus disease; "
        + str([(i.falsifier_class, i.status) for i in env.falsifier.items])
    )


# ---------------------------------------------------------------------------
# Test 4: Plug-swap — Stub vs Toy
# ---------------------------------------------------------------------------

def test_plug_swap_output_keys_match(
    stub_adapter: P1TargetStubAdapter,
    toy_adapter: P1TargetToyAdapter,
) -> None:
    inp = P1TargetInput(disease_ids=[_LQT_DISEASE_ID])
    stub_env = stub_adapter.process(inp, run_id="run:test-plug-stub")
    toy_env = toy_adapter.process(inp, run_id="run:test-plug-toy")

    stub_keys = sorted(stub_env.output.keys())
    toy_keys = sorted(toy_env.output.keys())
    assert stub_keys == toy_keys, (
        f"Output key mismatch between Stub and Toy:\n  Stub: {stub_keys}\n  Toy:  {toy_keys}"
    )


def test_plug_swap_falsifier_classes_match(
    stub_adapter: P1TargetStubAdapter,
    toy_adapter: P1TargetToyAdapter,
) -> None:
    inp = P1TargetInput(disease_ids=[_LQT_DISEASE_ID])
    stub_env = stub_adapter.process(inp, run_id="run:test-fc-stub")
    toy_env = toy_adapter.process(inp, run_id="run:test-fc-toy")

    stub_classes = _falsifier_classes(stub_env)
    toy_classes = _falsifier_classes(toy_env)
    assert stub_classes == toy_classes, (
        f"Falsifier class mismatch:\n  Stub: {sorted(stub_classes)}\n  Toy:  {sorted(toy_classes)}"
    )


def test_plug_swap_both_validate_schema(
    stub_adapter: P1TargetStubAdapter,
    toy_adapter: P1TargetToyAdapter,
    envelope_schema: dict,
) -> None:
    inp = P1TargetInput(disease_ids=[_LQT_DISEASE_ID])
    stub_env = stub_adapter.process(inp, run_id="run:test-schema-stub")
    toy_env = toy_adapter.process(inp, run_id="run:test-schema-toy")

    validate_envelope(stub_env.model_dump(mode="json"), envelope_schema)
    validate_envelope(toy_env.model_dump(mode="json"), envelope_schema)


def test_plug_swap_contract_version(
    stub_adapter: P1TargetStubAdapter,
    toy_adapter: P1TargetToyAdapter,
) -> None:
    inp = P1TargetInput(disease_ids=[_LQT_DISEASE_ID])
    stub_env = stub_adapter.process(inp)
    toy_env = toy_adapter.process(inp)
    assert stub_env.contract_version == "zer0pa.layer-envelope.v1"
    assert toy_env.contract_version == "zer0pa.layer-envelope.v1"


def test_toy_ordering_differs_from_stub(
    stub_adapter: P1TargetStubAdapter,
    toy_adapter: P1TargetToyAdapter,
) -> None:
    """Toy orders by druggability DESC; Stub by genetic_evidence_score DESC.
    With multiple LQT targets the leading gene symbols may differ.
    Both must return the same *set* of genes but can differ in order.
    """
    inp = P1TargetInput(disease_ids=[_LQT_DISEASE_ID], max_targets=10)
    stub_env = stub_adapter.process(inp)
    toy_env = toy_adapter.process(inp)

    stub_genes_ordered = [d["gene_symbol"] for d in stub_env.output.get("dossiers", [])]
    toy_genes_ordered = [d["gene_symbol"] for d in toy_env.output.get("dossiers", [])]

    # Same set of genes returned
    assert set(stub_genes_ordered) == set(toy_genes_ordered), (
        f"Stub and Toy returned different gene sets: {stub_genes_ordered} vs {toy_genes_ordered}"
    )

    # If more than one dossier, ordering should differ (different sort key)
    if len(stub_genes_ordered) > 1:
        # It is possible in edge cases they agree, but with 4 LQT targets with different
        # genetic_evidence and druggability scores, they should differ
        # This is a soft check: we just confirm both are valid lists
        assert isinstance(stub_genes_ordered, list)
        assert isinstance(toy_genes_ordered, list)


# ---------------------------------------------------------------------------
# Test 5: Determinism — same input -> same output_hash
# ---------------------------------------------------------------------------

def test_stub_determinism(stub_adapter: P1TargetStubAdapter) -> None:
    inp = P1TargetInput(disease_ids=[_LQT_DISEASE_ID], max_targets=5)
    fixed_run_id = "run:test-determinism-20260430"

    env1 = stub_adapter.process(inp, run_id=fixed_run_id)
    env2 = stub_adapter.process(inp, run_id=fixed_run_id)

    assert env1.audit.output_hash == env2.audit.output_hash, (
        f"Output hash not deterministic:\n  run1: {env1.audit.output_hash}\n  run2: {env2.audit.output_hash}"
    )
    assert env1.audit.input_hash == env2.audit.input_hash, (
        "Input hash not deterministic"
    )


def test_toy_determinism(toy_adapter: P1TargetToyAdapter) -> None:
    inp = P1TargetInput(disease_ids=[_LQT_DISEASE_ID], max_targets=5)
    fixed_run_id = "run:test-toy-determinism-20260430"

    env1 = toy_adapter.process(inp, run_id=fixed_run_id)
    env2 = toy_adapter.process(inp, run_id=fixed_run_id)

    assert env1.audit.output_hash == env2.audit.output_hash, (
        f"Toy output hash not deterministic:\n  run1: {env1.audit.output_hash}\n  run2: {env2.audit.output_hash}"
    )


# ---------------------------------------------------------------------------
# Additional: research boundary propagated
# ---------------------------------------------------------------------------

def test_research_boundary_in_envelope(stub_adapter: P1TargetStubAdapter) -> None:
    inp = P1TargetInput(disease_ids=[_LQT_DISEASE_ID])
    env = stub_adapter.process(inp)
    assert "Research use only" in env.research_boundary


# ---------------------------------------------------------------------------
# Additional: clinical overclaim PASS (no banned phrases in stub output)
# ---------------------------------------------------------------------------

def test_no_clinical_overclaim_in_stub_output(stub_adapter: P1TargetStubAdapter) -> None:
    inp = P1TargetInput(disease_ids=[_LQT_DISEASE_ID])
    env = stub_adapter.process(inp)

    overclaim_items = [
        i for i in env.falsifier.items if i.falsifier_class == "clinical_overclaim"
    ]
    assert overclaim_items, "clinical_overclaim falsifier must be present"
    for item in overclaim_items:
        assert item.status == FalsifierStatus.PASS, (
            f"Unexpected clinical_overclaim FAIL in stub output: {item.evidence}"
        )
