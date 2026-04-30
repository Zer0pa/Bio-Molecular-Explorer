"""Unit tests for P1.Optimize layer adapters.

Tests cover:
- process() with 3 input hits returns 3 leads each with iteration_number >= 10
- SYNTHESIS_ROUTE_ABSENT: withheld ASKCOS route triggers FAIL falsifier
- LEAD_WITHOUT_PHYSCHEM_FEASIBILITY: hERG_IC50_uM=2.0 triggers FAIL (soft_fail)
- Plug-swap (Stub vs Toy): output keys identical, same falsifier classes present
- confidence_tier escalation: Tier A requires distinct_models_count == 3
- JSON Schema validation for both adapters
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from zer0pa_health.envelope import Backend, FalsifierStatus, LayerName
from zer0pa_health.falsifiers.registry import FalsifierClass
from zer0pa_health.pathway1.contracts.p1_optimize import P1OptimizeInput, P1TargetProductProfile
from zer0pa_health.pathway1.contracts.p1_screen import P1ADMETPanel, P1ScreenedHit
from zer0pa_health.pathway1.layers.optimize.adapter import P1OptimizeStubAdapter
from zer0pa_health.pathway1.layers.optimize.toy_adapter import P1OptimizeToyAdapter

# ---------------------------------------------------------------------------
# Schema path
# ---------------------------------------------------------------------------

_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent / "schemas" / "envelope" / "layer-envelope-v1.json"
)


@pytest.fixture(scope="module")
def envelope_schema() -> dict:
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


def validate_envelope(env_dict: dict, schema: dict) -> None:
    jsonschema.validate(instance=env_dict, schema=schema)


# ---------------------------------------------------------------------------
# Helpers — build reusable hit fixtures
# ---------------------------------------------------------------------------

def _make_admet(
    herg_ic50_um: float = 30.0,
    esol_logs: float = -2.5,
    lipinski_violations: int = 0,
    oral_bioavailability_prob: float = 0.7,
) -> P1ADMETPanel:
    return P1ADMETPanel(
        logP=2.5,
        tpsa=75.0,
        BBB_penetration_prob=0.4,
        hERG_IC50_uM=herg_ic50_um,
        hepatotox_flag=False,
        oral_bioavailability_prob=oral_bioavailability_prob,
        esol_logs=esol_logs,
        lipinski_violations=lipinski_violations,
    )


def _make_hit(
    hit_id: str,
    smiles: str,
    target_id: str = "EGFR_stub",
    predicted_pic50: float = 7.5,
    admet: P1ADMETPanel | None = None,
    sa_score: float = 3.2,
    off_target_count: int = 5,
) -> dict:
    panel = admet or _make_admet()
    hit = P1ScreenedHit(
        hit_id=hit_id,
        target_id=target_id,
        smiles=smiles,
        predicted_pIC50=predicted_pic50,
        affinity_source="Boltz-2_stub",
        admet_panel=panel,
        selectivity_score=0.85,
        synthetic_accessibility=sa_score,
        pains_flags=[],
        aggregator_flag=False,
        off_target_prediction_count=off_target_count,
        confidence_tier="B",
    )
    return hit.model_dump()


# Three canonical test hits
_HIT_A = _make_hit("hit-A", "CCOc1ccc(Nc2nccc3ccccc23)cc1", sa_score=3.0)
_HIT_B = _make_hit("hit-B", "O=C(Nc1ccc(F)cc1)c1ccc(Cl)cc1", sa_score=2.8)
_HIT_C = _make_hit("hit-C", "c1ccc2c(c1)ccc(N1CCNCC1)c2", sa_score=3.5)

_THREE_HITS = [_HIT_A, _HIT_B, _HIT_C]


def _make_input(hits: list[dict], max_iterations: int = 50) -> P1OptimizeInput:
    return P1OptimizeInput(
        target_id="EGFR_stub",
        hits=hits,
        tpp=P1TargetProductProfile(target_pic50_min=7.0),
        max_iterations=max_iterations,
    )


# ---------------------------------------------------------------------------
# Fixtures — adapters
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def stub_adapter() -> P1OptimizeStubAdapter:
    return P1OptimizeStubAdapter()


@pytest.fixture(scope="module")
def toy_adapter() -> P1OptimizeToyAdapter:
    return P1OptimizeToyAdapter()


# ---------------------------------------------------------------------------
# Test 1: 3 hits → 3 leads, iteration_number >= 10 for all
# ---------------------------------------------------------------------------

def test_three_hits_returns_three_leads(stub_adapter: P1OptimizeStubAdapter) -> None:
    """process() with 3 input hits must return exactly 3 leads."""
    inp = _make_input(_THREE_HITS)
    env = stub_adapter.process(inp)

    assert env.layer == LayerName.P1_OPTIMIZE or env.layer == "P1.Optimize"
    leads = env.output["leads"]
    assert len(leads) == 3, f"Expected 3 leads, got {len(leads)}"

    for lead in leads:
        assert lead["iteration_number"] >= 10, (
            f"iteration_number {lead['iteration_number']} < 10 for lead {lead['lead_id']}"
        )


def test_three_hits_lead_pic50_improved(stub_adapter: P1OptimizeStubAdapter) -> None:
    """Each lead pIC50 must be >= input hit pIC50 (improvement is non-negative)."""
    inp = _make_input(_THREE_HITS)
    env = stub_adapter.process(inp)
    leads = env.output["leads"]

    original_pic50 = {h["smiles"]: h["predicted_pIC50"] for h in _THREE_HITS}
    for lead in leads:
        assert lead["predicted_pIC50"] >= original_pic50[lead["smiles"]] - 1e-6, (
            f"pIC50 regressed: {lead['predicted_pIC50']} < {original_pic50[lead['smiles']]}"
        )


# ---------------------------------------------------------------------------
# Test 2: Trigger SYNTHESIS_ROUTE_ABSENT via test-only _skip_askcos flag
# ---------------------------------------------------------------------------

def test_synthesis_route_absent_triggers_fail(stub_adapter: P1OptimizeStubAdapter) -> None:
    """Withholding ASKCOS route for a synthesisable compound must produce FAIL."""
    # sa_score=3.0 <= 4.0 triggers the falsifier when route is empty
    hit = _make_hit("hit-synth", "CCOc1ccc(Nc2nccc3ccccc23)cc1", sa_score=3.0)
    inp = _make_input([hit])
    env = stub_adapter.process(inp, _skip_askcos_for_hit_indices={0})

    fclasses = {item.falsifier_class for item in env.falsifier.items}
    assert FalsifierClass.SYNTHESIS_ROUTE_ABSENT.value in fclasses, (
        "SYNTHESIS_ROUTE_ABSENT class not found in falsifier items"
    )
    synthesis_items = [
        it for it in env.falsifier.items
        if it.falsifier_class == FalsifierClass.SYNTHESIS_ROUTE_ABSENT.value
    ]
    assert any(it.status == FalsifierStatus.FAIL for it in synthesis_items), (
        "SYNTHESIS_ROUTE_ABSENT did not fire FAIL"
    )
    # Overall envelope falsifier status must also be FAIL
    assert env.falsifier.status == FalsifierStatus.FAIL


# ---------------------------------------------------------------------------
# Test 3: LEAD_WITHOUT_PHYSCHEM_FEASIBILITY with hERG_IC50_uM=2.0
# ---------------------------------------------------------------------------

def test_lead_without_physchem_feasibility_herg_triggers_fail(
    stub_adapter: P1OptimizeStubAdapter,
) -> None:
    """hERG IC50 < 10 µM on a potent compound (pIC50>=7) fires FAIL (soft_fail)."""
    bad_admet = _make_admet(herg_ic50_um=2.0)  # 2.0 < 10 µM → FAIL
    hit = _make_hit(
        "hit-herg",
        "O=C(Nc1ccc(F)cc1)c1ccc(Cl)cc1",
        predicted_pic50=7.5,  # >= 7.0 threshold
        admet=bad_admet,
    )
    inp = _make_input([hit])
    env = stub_adapter.process(inp)

    fclasses = {item.falsifier_class for item in env.falsifier.items}
    assert FalsifierClass.LEAD_WITHOUT_PHYSCHEM_FEASIBILITY.value in fclasses

    physchem_items = [
        it for it in env.falsifier.items
        if it.falsifier_class == FalsifierClass.LEAD_WITHOUT_PHYSCHEM_FEASIBILITY.value
    ]
    assert any(it.status == FalsifierStatus.FAIL for it in physchem_items), (
        "LEAD_WITHOUT_PHYSCHEM_FEASIBILITY did not fire FAIL for hERG IC50=2.0"
    )


# ---------------------------------------------------------------------------
# Test 4: confidence_tier escalation
# ---------------------------------------------------------------------------

def test_confidence_tier_a_requires_distinct_models_3(stub_adapter: P1OptimizeStubAdapter) -> None:
    """Tier A should only appear when distinct_models_count == 3."""
    inp = _make_input(_THREE_HITS, max_iterations=50)
    env = stub_adapter.process(inp)

    for lead in env.output["leads"]:
        tier = lead["confidence_tier"]
        models = lead["distinct_models_count"]
        if tier == "A":
            assert models == 3, (
                f"Tier A lead {lead['lead_id']} has distinct_models_count={models}, expected 3"
            )
        if tier == "B":
            assert models in (2, 3), (
                f"Tier B lead should have >= 2 models, got {models}"
            )


def test_confidence_tier_with_low_max_iterations(stub_adapter: P1OptimizeStubAdapter) -> None:
    """With max_iterations=15, all iteration_numbers <= 30, so models_count=2 -> Tier B."""
    inp = _make_input(_THREE_HITS, max_iterations=15)
    env = stub_adapter.process(inp)

    for lead in env.output["leads"]:
        # iteration_number in [10, 15] -> distinct_models_count=2 -> Tier B (not A)
        assert lead["iteration_number"] <= 15
        # All leads with distinct_models_count=2 should be tier B (assuming pIC50 check passes
        # but this is the models_count condition only)
        assert lead["distinct_models_count"] == 2


# ---------------------------------------------------------------------------
# Test 5: Plug-swap — Stub vs Toy output keys match
# ---------------------------------------------------------------------------

def test_plug_swap_output_keys_match(
    stub_adapter: P1OptimizeStubAdapter,
    toy_adapter: P1OptimizeToyAdapter,
) -> None:
    """Both adapters must produce outputs with identical top-level keys."""
    inp = _make_input(_THREE_HITS)
    env_stub = stub_adapter.process(inp, run_id="run:20260430-stub0001")
    env_toy = toy_adapter.process(inp, run_id="run:20260430-toy00001")

    # Top-level envelope keys
    stub_keys = sorted(env_stub.model_dump().keys())
    toy_keys = sorted(env_toy.model_dump().keys())
    assert stub_keys == toy_keys, f"Envelope key mismatch: {stub_keys} vs {toy_keys}"

    # Output dict keys
    stub_out_keys = sorted(env_stub.output.keys())
    toy_out_keys = sorted(env_toy.output.keys())
    assert stub_out_keys == toy_out_keys, (
        f"output dict key mismatch: {stub_out_keys} vs {toy_out_keys}"
    )

    # Lead dict keys (first lead)
    stub_lead_keys = sorted(env_stub.output["leads"][0].keys())
    toy_lead_keys = sorted(env_toy.output["leads"][0].keys())
    assert stub_lead_keys == toy_lead_keys, (
        f"lead key mismatch: {stub_lead_keys} vs {toy_lead_keys}"
    )


def test_plug_swap_falsifier_classes_match(
    stub_adapter: P1OptimizeStubAdapter,
    toy_adapter: P1OptimizeToyAdapter,
) -> None:
    """Both adapters must produce the same set of falsifier classes in their items."""
    inp = _make_input(_THREE_HITS)
    env_stub = stub_adapter.process(inp)
    env_toy = toy_adapter.process(inp)

    stub_classes = sorted({it.falsifier_class for it in env_stub.falsifier.items})
    toy_classes = sorted({it.falsifier_class for it in env_toy.falsifier.items})
    assert stub_classes == toy_classes, (
        f"falsifier class sets differ: stub={stub_classes} toy={toy_classes}"
    )


def test_plug_swap_both_use_cpu_lite_backend(
    stub_adapter: P1OptimizeStubAdapter,
    toy_adapter: P1OptimizeToyAdapter,
) -> None:
    """Neither adapter should use backend=stub; both must be cpu_lite."""
    inp = _make_input([_HIT_A])
    env_stub = stub_adapter.process(inp)
    env_toy = toy_adapter.process(inp)

    for env, name in [(env_stub, "stub"), (env_toy, "toy")]:
        backend = env.tool_adapter.backend
        assert backend == Backend.CPU_LITE or backend == "cpu_lite", (
            f"{name} adapter backend={backend!r}, expected cpu_lite"
        )


# ---------------------------------------------------------------------------
# Test 6: JSON Schema validation
# ---------------------------------------------------------------------------

def test_stub_adapter_envelope_validates_schema(
    stub_adapter: P1OptimizeStubAdapter,
    envelope_schema: dict,
) -> None:
    """P1OptimizeStubAdapter output must validate against the universal envelope schema."""
    inp = _make_input(_THREE_HITS)
    env = stub_adapter.process(inp)
    env_dict = env.model_dump(mode="json")
    validate_envelope(env_dict, envelope_schema)


def test_toy_adapter_envelope_validates_schema(
    toy_adapter: P1OptimizeToyAdapter,
    envelope_schema: dict,
) -> None:
    """P1OptimizeToyAdapter output must validate against the universal envelope schema."""
    inp = _make_input(_THREE_HITS)
    env = toy_adapter.process(inp)
    env_dict = env.model_dump(mode="json")
    validate_envelope(env_dict, envelope_schema)


# ---------------------------------------------------------------------------
# Test 7: Layer and backend fields on envelope
# ---------------------------------------------------------------------------

def test_stub_adapter_layer_and_backend(stub_adapter: P1OptimizeStubAdapter) -> None:
    """Envelope layer must be P1.Optimize and backend must be cpu_lite."""
    inp = _make_input([_HIT_A])
    env = stub_adapter.process(inp)

    assert env.layer == LayerName.P1_OPTIMIZE or env.layer == "P1.Optimize"
    assert env.tool_adapter.backend == Backend.CPU_LITE or env.tool_adapter.backend == "cpu_lite"


def test_stub_adapter_confidence_basis(stub_adapter: P1OptimizeStubAdapter) -> None:
    """Confidence basis must include BoTorch and REINVENT 4 markers."""
    inp = _make_input(_THREE_HITS)
    env = stub_adapter.process(inp)

    assert "stub_botorch_axEHVI" in env.confidence.basis
    assert "stub_reinvent4_rl_loop" in env.confidence.basis


def test_confidence_score_in_range(stub_adapter: P1OptimizeStubAdapter) -> None:
    """Confidence score must be in [0.6, 0.8]."""
    inp = _make_input(_THREE_HITS)
    env = stub_adapter.process(inp)

    assert 0.6 <= env.confidence.score <= 0.8, (
        f"confidence.score={env.confidence.score} outside [0.6, 0.8]"
    )


# ---------------------------------------------------------------------------
# Test 8: Determinism — same input always produces same output
# ---------------------------------------------------------------------------

def test_determinism_stub_adapter(stub_adapter: P1OptimizeStubAdapter) -> None:
    """Same input must always produce identical leads (deterministic)."""
    inp = _make_input(_THREE_HITS)
    env1 = stub_adapter.process(inp, run_id="run:20260430-det00001")
    env2 = stub_adapter.process(inp, run_id="run:20260430-det00001")

    for l1, l2 in zip(env1.output["leads"], env2.output["leads"]):
        assert l1["iteration_number"] == l2["iteration_number"]
        assert l1["predicted_pIC50"] == l2["predicted_pIC50"]
        assert l1["confidence_tier"] == l2["confidence_tier"]


# ---------------------------------------------------------------------------
# Test 9: n_input_hits and n_leads in output match
# ---------------------------------------------------------------------------

def test_output_counts_match_input(stub_adapter: P1OptimizeStubAdapter) -> None:
    """n_input_hits and n_leads in output must match actual hit count."""
    inp = _make_input(_THREE_HITS)
    env = stub_adapter.process(inp)

    assert env.output["n_input_hits"] == 3
    assert env.output["n_leads"] == 3


# ---------------------------------------------------------------------------
# Test 10: ASKCOS route steps have correct shape
# ---------------------------------------------------------------------------

def test_askcos_route_steps_shape(stub_adapter: P1OptimizeStubAdapter) -> None:
    """Each lead must have 3 ASKCOS route steps with required fields."""
    inp = _make_input([_HIT_A])
    env = stub_adapter.process(inp)
    lead = env.output["leads"][0]

    assert lead["estimated_synthesis_steps"] == 3
    steps = lead["askcos_route_steps"]
    assert len(steps) == 3

    for i, step in enumerate(steps):
        assert step["step_index"] == i
        assert ">>" in step["rxn_smarts"], "rxn_smarts must be a reaction SMARTS with '>>'"
        assert isinstance(step["reagents"], list)
