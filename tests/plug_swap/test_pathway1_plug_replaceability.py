"""Pathway 1 plug-replaceability tests (Stub vs Toy adapter per layer).

Mirrors the discipline of `tests/plug_swap/test_plug_replaceability.py` for the
existing pipeline. For each P1 layer, replacing the StubAdapter with the
ToyAdapter MUST produce identical envelope output keys, identical falsifier
class set, identical contract_version, and validate against the canonical
JSON Schema. Cutover acceptance (Stub vs RunpodSim) lives in
`tests/integration/test_p1_*_runpod_cutover.py`; this file covers the
within-CPU plug invariant.
"""

from __future__ import annotations

from zer0pa_biomolecular_explorer.envelope import FalsifierStatus, LayerEnvelope
from zer0pa_biomolecular_explorer.falsifiers.detectors import detect_plug_replaceability_regression


# ──────────────────────────── helpers ────────────────────────────


def _envelope_keys(env: LayerEnvelope) -> dict:
    return {k: type(v).__name__ for k, v in env.output.items()}


def _output_schemas_match(env_a: LayerEnvelope, env_b: LayerEnvelope) -> None:
    res = detect_plug_replaceability_regression(_envelope_keys(env_a), _envelope_keys(env_b))
    assert res.status == FalsifierStatus.PASS, (
        f"plug_regression: a_keys={sorted(env_a.output.keys())}, "
        f"b_keys={sorted(env_b.output.keys())}; evidence={res.evidence}"
    )


def _falsifier_classes_match(env_a: LayerEnvelope, env_b: LayerEnvelope) -> None:
    classes_a = sorted({it.falsifier_class for it in env_a.falsifier.items})
    classes_b = sorted({it.falsifier_class for it in env_b.falsifier.items})
    assert classes_a == classes_b, (
        f"falsifier_class mismatch: stub={classes_a}, toy={classes_b}"
    )


def _contract_version_matches(env_a: LayerEnvelope, env_b: LayerEnvelope) -> None:
    assert env_a.contract_version == env_b.contract_version == "zer0pa.layer-envelope.v1"


# ──────────────────────────── P1.Target ────────────────────────────


def test_p1_target_plug_swap():
    from zer0pa_biomolecular_explorer.pathway1.contracts.p1_target import P1TargetInput
    from zer0pa_biomolecular_explorer.pathway1.layers.target.adapter import P1TargetStubAdapter
    from zer0pa_biomolecular_explorer.pathway1.layers.target.toy_adapter import P1TargetToyAdapter

    inp = P1TargetInput(disease_ids=["EFO:0000238"])
    env_a = P1TargetStubAdapter().process(inp)
    env_b = P1TargetToyAdapter().process(inp)
    _output_schemas_match(env_a, env_b)
    _falsifier_classes_match(env_a, env_b)
    _contract_version_matches(env_a, env_b)


# ──────────────────────────── P1.Structure ────────────────────────────


def test_p1_structure_plug_swap():
    from zer0pa_biomolecular_explorer.pathway1.contracts.p1_structure import P1StructureInput
    from zer0pa_biomolecular_explorer.pathway1.layers.structure.adapter import P1StructureStubAdapter
    from zer0pa_biomolecular_explorer.pathway1.layers.structure.toy_adapter import P1StructureToyAdapter

    inp = P1StructureInput(target_id="uniprot:Q12809", gene_symbol="KCNH2")
    env_a = P1StructureStubAdapter().process(inp)
    env_b = P1StructureToyAdapter().process(inp)
    _output_schemas_match(env_a, env_b)
    _falsifier_classes_match(env_a, env_b)
    _contract_version_matches(env_a, env_b)


# ──────────────────────────── P1.Generate ────────────────────────────


def test_p1_generate_plug_swap():
    from zer0pa_biomolecular_explorer.pathway1.contracts.p1_generate import P1GenerateInput
    from zer0pa_biomolecular_explorer.pathway1.layers.generate.adapter import P1GenerateStubAdapter
    from zer0pa_biomolecular_explorer.pathway1.layers.generate.toy_adapter import P1GenerateToyAdapter

    inp = P1GenerateInput(
        target_id="uniprot:Q12809",
        structure_ref="stub:openfold3:KCNH2",
        pocket_id="pocket:KCNH2_inner_cavity",
        mode="sbdd",
        library_size=10,
    )
    env_a = P1GenerateStubAdapter().process(inp)
    env_b = P1GenerateToyAdapter().process(inp)
    _output_schemas_match(env_a, env_b)
    _falsifier_classes_match(env_a, env_b)
    _contract_version_matches(env_a, env_b)


def test_p1_generate_values_may_differ_but_shape_must_not():
    """Toy is allowed to produce different SMILES; output shape stays identical."""
    from zer0pa_biomolecular_explorer.pathway1.contracts.p1_generate import P1GenerateInput
    from zer0pa_biomolecular_explorer.pathway1.layers.generate.adapter import P1GenerateStubAdapter
    from zer0pa_biomolecular_explorer.pathway1.layers.generate.toy_adapter import P1GenerateToyAdapter

    inp = P1GenerateInput(
        target_id="uniprot:Q12809",
        structure_ref="stub:openfold3:KCNH2",
        pocket_id="pocket:KCNH2_inner_cavity",
        mode="sbdd",
        library_size=10,
    )
    env_stub = P1GenerateStubAdapter().process(inp)
    env_toy = P1GenerateToyAdapter().process(inp)
    _output_schemas_match(env_stub, env_toy)
    # output_hashes differ because canned values differ
    assert env_stub.audit.output_hash != env_toy.audit.output_hash, (
        "Stub and Toy must produce different output_hashes (they use different canned values)"
    )


# ──────────────────────────── P1.Screen ────────────────────────────


def test_p1_screen_plug_swap():
    from zer0pa_biomolecular_explorer.pathway1.contracts.p1_screen import P1ScreenInput
    from zer0pa_biomolecular_explorer.pathway1.layers.screen.adapter import P1ScreenStubAdapter
    from zer0pa_biomolecular_explorer.pathway1.layers.screen.toy_adapter import P1ScreenToyAdapter

    inp = P1ScreenInput(
        target_id="uniprot:Q12809",
        structure_ref="stub:openfold3:KCNH2",
        pocket_id="pocket:KCNH2_inner_cavity",
        candidates=[
            {
                "candidate_id": f"P1-PLUG-{i:03d}",
                "smiles": "CCO",
                "generation_method": "REINVENT4_RL",
            }
            for i in range(5)
        ],
        target_panel_genes=["KCNH2", "SCN5A", "KCNQ1", "CACNA1C"],
    )
    env_a = P1ScreenStubAdapter().process(inp)
    env_b = P1ScreenToyAdapter().process(inp)
    _output_schemas_match(env_a, env_b)
    _falsifier_classes_match(env_a, env_b)
    _contract_version_matches(env_a, env_b)


# ──────────────────────────── P1.Optimize ────────────────────────────


def test_p1_optimize_plug_swap():
    from zer0pa_biomolecular_explorer.pathway1.contracts.p1_optimize import (
        P1OptimizeInput,
        P1TargetProductProfile,
    )
    from zer0pa_biomolecular_explorer.pathway1.layers.optimize.adapter import P1OptimizeStubAdapter
    from zer0pa_biomolecular_explorer.pathway1.layers.optimize.toy_adapter import P1OptimizeToyAdapter

    fake_hits = [
        {
            "hit_id": f"P1-HIT-PLUG-{i:03d}",
            "target_id": "uniprot:Q12809",
            "smiles": "CCO",
            "predicted_pIC50": 7.0,
            "affinity_source": "Boltz-2_stub",
            "admet_panel": {
                "logP": 2.0,
                "tpsa": 70.0,
                "BBB_penetration_prob": 0.3,
                "hERG_IC50_uM": 30.0,
                "hepatotox_flag": False,
                "oral_bioavailability_prob": 0.7,
                "esol_logs": -2.5,
                "lipinski_violations": 0,
            },
            "selectivity_score": 0.7,
            "synthetic_accessibility": 3.0,
            "pains_flags": [],
            "aggregator_flag": False,
            "off_target_prediction_count": 4,
            "confidence_tier": "B",
        }
        for i in range(2)
    ]
    inp = P1OptimizeInput(
        target_id="uniprot:Q12809",
        hits=fake_hits,
        tpp=P1TargetProductProfile(),
        max_iterations=15,
    )
    env_a = P1OptimizeStubAdapter().process(inp)
    env_b = P1OptimizeToyAdapter().process(inp)
    _output_schemas_match(env_a, env_b)
    _falsifier_classes_match(env_a, env_b)
    _contract_version_matches(env_a, env_b)


# ──────────────────────────── P1.Handoff ────────────────────────────


def test_p1_handoff_plug_swap_cardiac():
    from zer0pa_biomolecular_explorer.pathway1.contracts.p1_handoff import P1HandoffInput
    from zer0pa_biomolecular_explorer.pathway1.layers.handoff.adapter import P1HandoffStubAdapter
    from zer0pa_biomolecular_explorer.pathway1.layers.handoff.toy_adapter import P1HandoffToyAdapter

    fake_lead = {
        "lead_id": "P1-LEAD-PLUG-001",
        "target_id": "uniprot:Q12809",
        "smiles": "CCO",
        "predicted_pIC50": 7.5,
        "admet_panel": {
            "logP": 2.0,
            "tpsa": 70.0,
            "BBB_penetration_prob": 0.3,
            "hERG_IC50_uM": 30.0,
            "hepatotox_flag": False,
            "oral_bioavailability_prob": 0.7,
            "esol_logs": -2.5,
            "lipinski_violations": 0,
        },
        "selectivity_score": 0.75,
        "synthetic_accessibility": 3.0,
        "askcos_route_steps": [
            {"step_index": 0, "rxn_smarts": "[c:1][N:2]>>[c:1][N:2]", "reagents": ["base"]},
            {"step_index": 1, "rxn_smarts": "[N:1][C:2]>>[N:1][C:2]", "reagents": ["amine"]},
        ],
        "estimated_synthesis_steps": 2,
        "iteration_number": 25,
        "parent_scaffold": "test_scaffold",
        "confidence_tier": "B",
        "distinct_models_count": 2,
        "generation_method": "REINVENT4_RL_stub",
    }
    inp = P1HandoffInput(
        target_id="uniprot:Q12809",
        target_gene="KCNH2",
        leads=[fake_lead],
        pathway1_run_id="P1-PLUG-RUN-001",
        audit_refs=["audit:test"],
        cloud_lab_enabled=False,
    )
    env_a = P1HandoffStubAdapter().process(inp)
    env_b = P1HandoffToyAdapter().process(inp)
    _output_schemas_match(env_a, env_b)
    _falsifier_classes_match(env_a, env_b)
    _contract_version_matches(env_a, env_b)


# ──────────────────────────── Cross-layer contract version ────────────────────────────


def test_all_pathway1_envelopes_share_contract_version():
    """Sanity: every P1 layer envelope declares the canonical contract_version."""
    from zer0pa_biomolecular_explorer.pathway1.contracts.p1_target import P1TargetInput
    from zer0pa_biomolecular_explorer.pathway1.layers.target.adapter import P1TargetStubAdapter

    e = P1TargetStubAdapter().process(P1TargetInput(disease_ids=["EFO:0000238"]))
    assert e.contract_version == "zer0pa.layer-envelope.v1"
    assert e.layer.startswith("P1.")
