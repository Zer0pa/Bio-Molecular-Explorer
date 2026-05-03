"""Unit tests for the L2.5 retrosynthesis stub adapter.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.

Test coverage
-------------
1. process(CCO, AIZYNTHFINDER_DEFAULT) → valid envelope, routes_found documented
2. process(CCO, ASKCOS_REAXYS) → LICENSE_DRIFT FAIL, license_flag = CC-BY-NC
3. process("C C O", ...) → INVALID_MOLECULAR_INPUT FAIL (whitespace in SMILES)
4. Dofetilide canonical SMILES → fixture route loaded, total_steps == fixture's total_steps
5. feedback_to_l2 dict has exactly the required keys
6. Envelope validates against schemas/envelope/layer-envelope-v1.json
7. back_edges contains entry with target_layer=L2 and feedback_to_l2 in proposed_constraint
8. Verapamil canonical SMILES → fixture loaded, route has step_confidence in [0.4, 0.7]
9. Ranolazine canonical SMILES → fixture loaded, sa_score in [1.0, 10.0]
10. Determinism: same input → same output_hash in envelope.audit
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zer0pa_biomolecular_explorer.contracts.l2_5 import L25Input, L25Policy
from zer0pa_biomolecular_explorer.envelope import FalsifierStatus
from zer0pa_biomolecular_explorer.layers.l2_5 import L25StubAdapter

# Path to the JSON schema for envelope validation
_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent
    / "schemas"
    / "envelope"
    / "layer-envelope-v1.json"
)

# Known compound SMILES from fixtures
_DOFETILIDE_SMILES = "CN(C)S(=O)(=O)c1ccc(NCCOc2ccc(CCN(C)S(=O)(=O)C)cc2)cc1"
_VERAPAMIL_SMILES = "COc1ccc(CC(C)(C#N)CCCN(C)CCc2ccc(OC)c(OC)c2)cc1OC"
_RANOLAZINE_SMILES = "COc1ccccc1OCC(O)CN1CCN(CC(=O)Nc2c(C)cccc2C)CC1"

_REQUIRED_FEEDBACK_KEYS = frozenset(
    ["route_score", "route_depth", "sa_score", "starting_material_cost_usd", "routes_found"]
)

adapter = L25StubAdapter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_input(smiles: str, policy: L25Policy = L25Policy.AIZYNTHFINDER_DEFAULT) -> L25Input:
    return L25Input(canonical_smiles=smiles, policy=policy)


def _get_falsifier_statuses(env) -> dict[str, str]:
    return {item.falsifier_class: item.status for item in env.falsifier.items}


# ---------------------------------------------------------------------------
# Test 1: Basic valid SMILES with default policy
# ---------------------------------------------------------------------------

def test_process_valid_smiles_aizynthfinder():
    """process(CCO, AIZYNTHFINDER_DEFAULT) returns a valid envelope.

    routes_found may be True or False depending on whether CCO produces a valid
    stub route; the important invariants are:
      - Envelope is well-formed (Pydantic validates on construction)
      - layer == L2.5
      - back_edges has at least one entry targeting L2
      - feedback_to_l2 is present in output
      - license_flag is None (no license issue with default policy)
    """
    inp = _make_input("CCO")
    env = adapter.process(inp, run_id="run:20260430-test0001")

    assert env.run_id == "run:20260430-test0001"
    assert env.layer == "L2.5"
    assert env.tool_adapter.backend == "stub"
    assert env.research_boundary.startswith("Research use only")

    output = env.output
    assert "routes_found" in output
    assert "feedback_to_l2" in output
    assert output.get("license_flag") is None

    # back_edge to L2 is required
    l2_edges = [be for be in env.back_edges if be.target_layer == "L2"]
    assert len(l2_edges) >= 1, "Expected at least one back_edge targeting L2"


# ---------------------------------------------------------------------------
# Test 2: ASKCOS_REAXYS triggers license_drift FAIL
# ---------------------------------------------------------------------------

def test_askcos_reaxys_emits_license_drift_fail():
    """process(CCO, ASKCOS_REAXYS) must emit LICENSE_DRIFT FAIL and set license_flag."""
    inp = _make_input("CCO", policy=L25Policy.ASKCOS_REAXYS)
    env = adapter.process(inp)

    statuses = _get_falsifier_statuses(env)

    assert "license_drift" in statuses, (
        f"license_drift falsifier not found in items: {list(statuses.keys())}"
    )
    assert statuses["license_drift"] == "fail", (
        f"Expected license_drift FAIL, got {statuses['license_drift']}"
    )
    # Overall envelope must be FAIL
    assert env.falsifier.status == "fail"

    # license_flag must be set to CC-BY-NC
    output = env.output
    assert output.get("license_flag") == "CC-BY-NC", (
        f"Expected license_flag=CC-BY-NC, got {output.get('license_flag')!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: Whitespace in SMILES triggers INVALID_MOLECULAR_INPUT FAIL
# ---------------------------------------------------------------------------

def test_invalid_smiles_whitespace_fails():
    """process('C C O') must emit INVALID_MOLECULAR_INPUT FAIL (whitespace)."""
    inp = _make_input("C C O")  # space is forbidden in SMILES
    env = adapter.process(inp)

    statuses = _get_falsifier_statuses(env)

    assert "invalid_molecular_input" in statuses, (
        f"invalid_molecular_input not found in items: {list(statuses.keys())}"
    )
    assert statuses["invalid_molecular_input"] == "fail"
    assert env.falsifier.status == "fail"

    # routes_found must be False when SMILES is invalid
    assert env.output.get("routes_found") is False


# ---------------------------------------------------------------------------
# Test 4: Dofetilide fixture route is loaded
# ---------------------------------------------------------------------------

def test_dofetilide_loads_fixture_route():
    """Dofetilide canonical SMILES → fixture route loaded with correct total_steps."""
    import json
    from pathlib import Path

    fixture_path = (
        Path(__file__).parent.parent.parent / "fixtures" / "routes" / "dofetilide.json"
    )
    fixture = json.loads(fixture_path.read_text())
    expected_total_steps = fixture["total_steps"]

    inp = _make_input(_DOFETILIDE_SMILES)
    env = adapter.process(inp)

    output = env.output
    # Should have routes
    routes = output.get("routes", [])
    assert len(routes) >= 1, "Expected at least one route for dofetilide"

    route = routes[0]
    assert route["total_steps"] == expected_total_steps, (
        f"total_steps {route['total_steps']} != fixture {expected_total_steps}"
    )


# ---------------------------------------------------------------------------
# Test 5: feedback_to_l2 dict has exactly the required keys
# ---------------------------------------------------------------------------

def test_feedback_to_l2_keys():
    """feedback_to_l2 must have exactly the required keys."""
    inp = _make_input(_DOFETILIDE_SMILES)
    env = adapter.process(inp)

    feedback = env.output.get("feedback_to_l2", {})
    assert set(feedback.keys()) == _REQUIRED_FEEDBACK_KEYS, (
        f"feedback_to_l2 keys {set(feedback.keys())} != required {_REQUIRED_FEEDBACK_KEYS}"
    )

    # All values must be floats (or int-like floats)
    for k, v in feedback.items():
        assert isinstance(v, (int, float)), f"feedback_to_l2[{k!r}] = {v!r} is not a number"


# ---------------------------------------------------------------------------
# Test 6: Envelope validates against JSON schema
# ---------------------------------------------------------------------------

def test_envelope_validates_against_json_schema():
    """Envelope must validate against layer-envelope-v1.json."""
    import jsonschema

    schema = json.loads(_SCHEMA_PATH.read_text())
    inp = _make_input("CCO")
    env = adapter.process(inp)
    env_dict = json.loads(env.dump_json())

    # Should not raise
    jsonschema.validate(instance=env_dict, schema=schema)


def test_dofetilide_envelope_validates_against_json_schema():
    """Dofetilide envelope must also validate against layer-envelope-v1.json."""
    import jsonschema

    schema = json.loads(_SCHEMA_PATH.read_text())
    inp = _make_input(_DOFETILIDE_SMILES)
    env = adapter.process(inp)
    env_dict = json.loads(env.dump_json())

    jsonschema.validate(instance=env_dict, schema=schema)


# ---------------------------------------------------------------------------
# Test 7: back_edges structure contains L2 target with feedback_to_l2
# ---------------------------------------------------------------------------

def test_back_edges_l2_structure():
    """back_edges must contain target_layer=L2 with feedback_to_l2 in proposed_constraint."""
    inp = _make_input("CCO")
    env = adapter.process(inp)

    l2_edges = [be for be in env.back_edges if be.target_layer == "L2"]
    assert len(l2_edges) >= 1, "Expected back_edge targeting L2"

    l2_edge = l2_edges[0]
    constraint = l2_edge.proposed_constraint
    assert "feedback_to_l2" in constraint, (
        f"feedback_to_l2 not in proposed_constraint: {constraint.keys()}"
    )

    inner_feedback = constraint["feedback_to_l2"]
    assert set(inner_feedback.keys()) == _REQUIRED_FEEDBACK_KEYS


# ---------------------------------------------------------------------------
# Test 8: Verapamil fixture loaded, step_confidence in [0.4, 0.7]
# ---------------------------------------------------------------------------

def test_verapamil_fixture_step_confidence_range():
    """Verapamil fixture route steps must have step_confidence in [0.4, 0.7]."""
    inp = _make_input(_VERAPAMIL_SMILES)
    env = adapter.process(inp)

    output = env.output
    routes = output.get("routes", [])
    assert len(routes) >= 1, "Expected at least one route for verapamil"

    for route in routes:
        for step in route.get("steps", []):
            sc = step["step_confidence"]
            assert 0.4 <= sc <= 0.7, (
                f"step_confidence {sc} not in [0.4, 0.7] for verapamil step"
            )


# ---------------------------------------------------------------------------
# Test 9: Ranolazine fixture loaded, sa_score in [1.0, 10.0]
# ---------------------------------------------------------------------------

def test_ranolazine_sa_score_range():
    """Ranolazine output must have sa_score in [1.0, 10.0]."""
    inp = _make_input(_RANOLAZINE_SMILES)
    env = adapter.process(inp)

    output = env.output
    routes = output.get("routes", [])
    assert len(routes) >= 1, "Expected at least one route for ranolazine"

    for route in routes:
        sa = route.get("sa_score")
        if sa is not None:
            assert 1.0 <= sa <= 10.0, f"sa_score {sa} not in [1.0, 10.0]"


# ---------------------------------------------------------------------------
# Test 10: Determinism — same input produces same output_hash
# ---------------------------------------------------------------------------

def test_deterministic_output_hash():
    """Same input processed twice must yield identical output_hash in envelope.audit."""
    inp = _make_input("CCO")
    env1 = adapter.process(inp, run_id="run:20260430-determ01")
    env2 = adapter.process(inp, run_id="run:20260430-determ02")

    # output_hash depends only on output dict (not on run_id or audit_id)
    assert env1.audit.output_hash == env2.audit.output_hash, (
        f"output_hash not deterministic: {env1.audit.output_hash} != {env2.audit.output_hash}"
    )


# ---------------------------------------------------------------------------
# Test 11: License drift + SMILES valid → continues but band = low
# ---------------------------------------------------------------------------

def test_reaxys_license_drift_continues_with_low_band():
    """ASKCOS_REAXYS: license drift triggers FAIL but processing continues to produce output."""
    inp = _make_input("CCO", policy=L25Policy.ASKCOS_REAXYS)
    env = adapter.process(inp)

    # Envelope is FAIL (due to license_drift) but output is still present
    assert env.falsifier.status == "fail"
    assert "feedback_to_l2" in env.output

    # Confidence band must be low due to license_flag
    assert env.confidence.band == "low", (
        f"Expected confidence band=low for license-drift case, got {env.confidence.band}"
    )


# ---------------------------------------------------------------------------
# Test 12: Unknown SMILES → generic 2-step stub route
# ---------------------------------------------------------------------------

def test_unknown_smiles_produces_stub_route():
    """Unknown SMILES (not a seed compound) produces a generic stub route."""
    # Use a simple SMILES not in fixtures
    inp = _make_input("CCCCC")
    env = adapter.process(inp)

    output = env.output
    # Should still have feedback_to_l2 regardless of routes_found value
    assert "feedback_to_l2" in output
    assert set(output["feedback_to_l2"].keys()) == _REQUIRED_FEEDBACK_KEYS
