"""Unit tests for the L2 property/formulation/ADMET stub adapter.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.

Test coverage
-------------
1. process("CCO") returns valid envelope with reward_modifier in [-1.0, 1.0]
2. process invalid SMILES "C C" → falsifier FAIL, confidence 0.0
3. process with retrosynth_feedback routes_found=False → reward_modifier reduced
   (Inversion A back-edge propagation)
4. dissolution_pinn_stub for IR_tablet, dose_mg=10 → fractions increasing in [0,1]
5. mechanism_escalation=True → stub_laundering FAIL
6. Envelope validates against schemas/envelope/layer-envelope-v1.json
7. Determinism: process("CCO") twice → identical descriptor and ADMET dicts
8. Determinism: same input → same output_hash in envelope.audit
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zer0pa_health.contracts.l2 import (
    L2DissolutionInput,
    L2MoleculeInput,
    L2PropertyInput,
    L2RetrosynthFeedback,
)
from zer0pa_health.envelope import FalsifierStatus
from zer0pa_health.layers.l2 import L2StubAdapter, dissolution_pinn_stub, score_property

# Path to the JSON schema for envelope validation
_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent
    / "schemas"
    / "envelope"
    / "layer-envelope-v1.json"
)

adapter = L2StubAdapter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_input(smiles: str, retrosynth_feedback=None) -> L2PropertyInput:
    return L2PropertyInput(
        molecule=L2MoleculeInput(smiles=smiles),
        retrosynth_feedback=retrosynth_feedback,
    )


def _make_retrosynth(
    routes_found: bool,
    route_score: float = 0.0,
    route_depth: int = 0,
    sa_score: float = 8.0,
    starting_material_cost_usd: float = 10000.0,
) -> L2RetrosynthFeedback:
    return L2RetrosynthFeedback(
        smiles="CCO",
        routes_found=routes_found,
        route_score=route_score,
        route_depth=route_depth,
        sa_score=sa_score,
        starting_material_cost_usd=starting_material_cost_usd,
    )


# ---------------------------------------------------------------------------
# Test 1: Basic valid SMILES produces a valid envelope
# ---------------------------------------------------------------------------

def test_process_valid_smiles_returns_envelope():
    """process('CCO') returns a valid LayerEnvelope with reward_modifier in [-1, 1]."""
    inp = _make_input("CCO")
    env = adapter.process(inp, run_id="run:20260430-test0001")

    # Must be a LayerEnvelope (pydantic model validates on construction)
    assert env.run_id == "run:20260430-test0001"
    assert env.layer == "L2"
    assert env.tool_adapter.backend == "stub"
    assert env.research_boundary.startswith("Research use only")

    output = env.output
    assert "reward_modifier" in output
    reward = output["reward_modifier"]
    assert -1.0 <= reward <= 1.0, f"reward_modifier {reward} out of [-1, 1]"

    # Confidence score must be in 0.4-0.6 band
    assert 0.4 <= env.confidence.score <= 0.6, (
        f"confidence.score {env.confidence.score} not in [0.4, 0.6]"
    )

    # basis must include 'stub_descriptor_proxies'
    assert "stub_descriptor_proxies" in env.confidence.basis

    # valid_smiles should be True for 'CCO'
    assert output["valid_smiles"] is True


# ---------------------------------------------------------------------------
# Test 2: Invalid SMILES triggers FAIL with confidence 0.0
# ---------------------------------------------------------------------------

def test_process_invalid_smiles_fails():
    """process('C C') → falsifier FAIL, confidence 0.0 (whitespace in SMILES)."""
    inp = _make_input("C C")  # space is forbidden
    env = adapter.process(inp)

    assert env.falsifier.status == "fail", (
        f"Expected falsifier FAIL for invalid SMILES, got {env.falsifier.status}"
    )
    assert env.confidence.score == 0.0, (
        f"Expected confidence 0.0 for invalid SMILES, got {env.confidence.score}"
    )
    assert env.output["valid_smiles"] is False

    # Should have the invalid_molecular_input falsifier
    fclasses = [item.falsifier_class for item in env.falsifier.items]
    assert "invalid_molecular_input" in fclasses


# ---------------------------------------------------------------------------
# Test 3: Back-edge propagation — routes_found=False reduces reward_modifier
# ---------------------------------------------------------------------------

def test_retrosynth_feedback_reduces_reward():
    """Retrosynth back-edge (routes_found=False) must reduce reward_modifier."""
    # Baseline: no feedback
    inp_base = _make_input("CCO")
    env_base = adapter.process(inp_base, run_id="run:20260430-test0003a")
    reward_base = env_base.output["reward_modifier"]

    # With feedback: routes_found=False, route_score=0.0
    feedback = _make_retrosynth(
        routes_found=False,
        route_score=0.0,
        route_depth=0,
        sa_score=8.0,
        starting_material_cost_usd=10000.0,
    )
    inp_fb = _make_input("CCO", retrosynth_feedback=feedback)
    env_fb = adapter.process(inp_fb, run_id="run:20260430-test0003b")
    reward_fb = env_fb.output["reward_modifier"]

    # routes_found=False subtracts 0.4; route_score=0.0 subtracts 0.2 more
    assert reward_fb < reward_base, (
        f"Back-edge did not reduce reward: base={reward_base}, feedback={reward_fb}"
    )
    # Specific expected: 0.5 - 0.4 (no routes) - 0.2 (1-0.0)*0.2 = -0.1
    expected_fb = max(-1.0, min(1.0, 0.5 - 0.4 - 0.2))
    assert abs(reward_fb - expected_fb) < 1e-9, (
        f"reward_modifier={reward_fb} expected {expected_fb}"
    )


# ---------------------------------------------------------------------------
# Test 4: Dissolution stub for IR_tablet
# ---------------------------------------------------------------------------

def test_dissolution_ir_tablet_increasing_in_range():
    """IR_tablet dissolution at 30/60/120 min is increasing and in [0, 1]."""
    inp = L2DissolutionInput(
        molecule=L2MoleculeInput(smiles="CCO"),
        formulation="IR_tablet",
        dose_mg=10.0,
    )
    out = dissolution_pinn_stub(inp)

    f30 = out.fraction_dissolved_at_30min
    f60 = out.fraction_dissolved_at_60min
    f120 = out.fraction_dissolved_at_120min

    assert 0.0 <= f30 <= 1.0, f"f30={f30} not in [0, 1]"
    assert 0.0 <= f60 <= 1.0, f"f60={f60} not in [0, 1]"
    assert 0.0 <= f120 <= 1.0, f"f120={f120} not in [0, 1]"

    assert f30 < f60, f"Dissolution not increasing: f30={f30} >= f60={f60}"
    assert f60 < f120, f"Dissolution not increasing: f60={f60} >= f120={f120}"

    assert out.pinn_basis == "DeepXDE_stub"
    assert out.formulation == "IR_tablet"
    assert out.dose_mg == 10.0


# ---------------------------------------------------------------------------
# Test 5: mechanism_escalation=True triggers stub_laundering FAIL
# ---------------------------------------------------------------------------

def test_mechanism_escalation_triggers_stub_laundering():
    """mechanism_escalation=True must produce a stub_laundering FAIL falsifier."""
    inp = _make_input("CCO")
    env = adapter.process(inp, mechanism_escalation=True)

    fclasses = [item.falsifier_class for item in env.falsifier.items]
    statuses = {item.falsifier_class: item.status for item in env.falsifier.items}

    assert "stub_laundering" in fclasses, (
        f"stub_laundering falsifier not found in items: {fclasses}"
    )
    assert statuses["stub_laundering"] == "fail", (
        f"stub_laundering status is {statuses['stub_laundering']}, expected 'fail'"
    )
    # Overall envelope should be FAIL
    assert env.falsifier.status == "fail"


# ---------------------------------------------------------------------------
# Test 6: Envelope validates against JSON schema
# ---------------------------------------------------------------------------

def test_envelope_validates_against_json_schema():
    """Envelope from process('CCO') must validate against layer-envelope-v1.json."""
    import jsonschema

    schema = json.loads(_SCHEMA_PATH.read_text())
    inp = _make_input("CCO")
    env = adapter.process(inp)
    env_dict = json.loads(env.dump_json())

    # Should not raise
    jsonschema.validate(instance=env_dict, schema=schema)


# ---------------------------------------------------------------------------
# Test 7: Determinism of descriptors and ADMET scores
# ---------------------------------------------------------------------------

def test_process_deterministic_scores():
    """Same SMILES processed twice must yield identical descriptor and ADMET dicts."""
    inp = _make_input("CCO")
    env1 = adapter.process(inp)
    env2 = adapter.process(inp)

    desc1 = env1.output["descriptors"]
    desc2 = env2.output["descriptors"]
    admet1 = env1.output["admet_scores"]
    admet2 = env2.output["admet_scores"]

    assert desc1 == desc2, f"Descriptors not deterministic: {desc1} vs {desc2}"
    assert admet1 == admet2, f"ADMET scores not deterministic: {admet1} vs {admet2}"

    # Also check score_property is deterministic
    scores_a = score_property("CCO")
    scores_b = score_property("CCO")
    assert scores_a == scores_b, f"score_property not deterministic: {scores_a} vs {scores_b}"


# ---------------------------------------------------------------------------
# Test 8: Determinism of output_hash (same input → same output_hash)
# ---------------------------------------------------------------------------

def test_process_deterministic_output_hash():
    """Same input must yield the same output_hash in envelope.audit (cache-key property)."""
    inp = _make_input("CCO")
    env1 = adapter.process(inp, run_id="run:20260430-det001")
    env2 = adapter.process(inp, run_id="run:20260430-det001")

    assert env1.audit.output_hash == env2.audit.output_hash, (
        f"output_hash not deterministic: "
        f"{env1.audit.output_hash} vs {env2.audit.output_hash}"
    )


# ---------------------------------------------------------------------------
# Additional: test all formulation types for dissolution
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("formulation", ["IR_tablet", "ER_tablet", "capsule", "solution", "suspension"])
def test_dissolution_all_formulations_valid(formulation: str):
    """All formulation types return valid, increasing dissolution fractions."""
    inp = L2DissolutionInput(
        molecule=L2MoleculeInput(smiles="CCO"),
        formulation=formulation,
        dose_mg=100.0,
    )
    out = dissolution_pinn_stub(inp)

    assert 0.0 <= out.fraction_dissolved_at_30min <= 1.0
    assert 0.0 <= out.fraction_dissolved_at_60min <= 1.0
    assert 0.0 <= out.fraction_dissolved_at_120min <= 1.0
    assert out.fraction_dissolved_at_30min <= out.fraction_dissolved_at_60min
    assert out.fraction_dissolved_at_60min <= out.fraction_dissolved_at_120min


# ---------------------------------------------------------------------------
# Additional: parked runpod adapter raises RuntimeError
# ---------------------------------------------------------------------------

def test_parked_runpod_raises():
    """L2DeepXDERunpodAdapter.process() must raise RuntimeError (parked)."""
    from zer0pa_health.layers.l2 import L2DeepXDERunpodAdapter

    parked = L2DeepXDERunpodAdapter()
    inp = _make_input("CCO")
    with pytest.raises(RuntimeError, match="parked"):
        parked.process(inp)


# ---------------------------------------------------------------------------
# Additional: verify SMILES validity passes for fixture compounds
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("smiles,name", [
    ("CN(C)S(=O)(=O)c1ccc(NCCOc2ccc(CCN(C)S(=O)(=O)C)cc2)cc1", "dofetilide"),
    ("COc1ccc(CC(C)(C#N)CCCN(C)CCc2ccc(OC)c(OC)c2)cc1OC", "verapamil"),
    ("COc1ccccc1OCC(O)CN1CCN(CC(=O)Nc2c(C)cccc2C)CC1", "ranolazine"),
])
def test_fixture_compounds_pass_smiles_validation(smiles: str, name: str):
    """Fixture compound SMILES must pass SMILES validation and return valid envelope."""
    inp = _make_input(smiles)
    env = adapter.process(inp)

    assert env.output["valid_smiles"] is True, f"{name} SMILES failed validation"
    fclasses = {item.falsifier_class: item.status for item in env.falsifier.items}
    assert fclasses.get("invalid_molecular_input") == "pass", (
        f"{name}: expected invalid_molecular_input PASS"
    )
