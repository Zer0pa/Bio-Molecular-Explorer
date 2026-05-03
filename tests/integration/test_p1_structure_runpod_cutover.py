"""P1.Structure runpod cutover acceptance test.

Verifies that swapping P1StructureStubAdapter for P1StructureRunpodSimAdapter
does NOT break the downstream pipeline:
- Output shape matches (detect_plug_replaceability_regression PASS)
- Falsifier class set matches
- backend=runpod_gpu on sim adapter
- stub_laundering PASSES on sim (backend != stub)
- structure_source_tag="openfold3" on sim (not "stub")
- mean_plddt on sim >= 80 (GPU produces higher confidence)
"""

from __future__ import annotations

from zer0pa_biomolecular_explorer.envelope import Backend, FalsifierStatus
from zer0pa_biomolecular_explorer.falsifiers.detectors import detect_plug_replaceability_regression
from zer0pa_biomolecular_explorer.pathway1.contracts.p1_structure import P1StructureInput
from zer0pa_biomolecular_explorer.pathway1.layers.structure import P1StructureStubAdapter
from zer0pa_biomolecular_explorer.runpod_sim.p1_structure_runpod_sim import P1StructureRunpodSimAdapter

_TARGET_ID = "uniprot:Q12809"
_GENE = "KCNH2"


def _make_input() -> P1StructureInput:
    return P1StructureInput(
        target_id=_TARGET_ID,
        gene_symbol=_GENE,
        sequence=None,
        pdb_ref_hint=None,
    )


def _envelope_keys(env) -> dict:
    return {k: type(v).__name__ for k, v in env.output.items()}


# ---------------------------------------------------------------------------
# 1. Shape match — detect_plug_replaceability_regression PASS
# ---------------------------------------------------------------------------

def test_runpod_sim_shape_matches_stub() -> None:
    """Stub and RunpodSim must produce identical output key shapes."""
    inp = _make_input()
    stub = P1StructureStubAdapter()
    sim = P1StructureRunpodSimAdapter()

    env_stub = stub.process(inp)
    env_sim = sim.process(inp)

    result = detect_plug_replaceability_regression(_envelope_keys(env_stub), _envelope_keys(env_sim))
    assert result.status in (FalsifierStatus.PASS, "pass"), (
        f"Shape regression detected: {result.evidence}"
    )


# ---------------------------------------------------------------------------
# 2. Falsifier class set matches
# ---------------------------------------------------------------------------

def test_runpod_sim_falsifier_classes_match_stub() -> None:
    inp = _make_input()
    stub = P1StructureStubAdapter()
    sim = P1StructureRunpodSimAdapter()

    env_stub = stub.process(inp)
    env_sim = sim.process(inp)

    classes_stub = {it.falsifier_class for it in env_stub.falsifier.items}
    classes_sim = {it.falsifier_class for it in env_sim.falsifier.items}
    assert classes_stub == classes_sim, (
        f"Falsifier class mismatch: stub={classes_stub}, sim={classes_sim}"
    )


# ---------------------------------------------------------------------------
# 3. backend=runpod_gpu on sim
# ---------------------------------------------------------------------------

def test_runpod_sim_backend_is_runpod_gpu() -> None:
    sim = P1StructureRunpodSimAdapter()
    env = sim.process(_make_input())
    assert env.tool_adapter.backend == Backend.RUNPOD_GPU.value, (
        f"Expected runpod_gpu, got {env.tool_adapter.backend}"
    )


# ---------------------------------------------------------------------------
# 4. stub_laundering PASSES on runpod_sim
# ---------------------------------------------------------------------------

def test_runpod_sim_stub_laundering_passes() -> None:
    sim = P1StructureRunpodSimAdapter()
    env = sim.process(_make_input())
    stub_items = [it for it in env.falsifier.items if it.falsifier_class == "stub_laundering"]
    assert len(stub_items) >= 1
    for it in stub_items:
        assert it.status in (FalsifierStatus.PASS, "pass"), (
            f"stub_laundering FAIL on runpod_sim backend — should be PASS"
        )


# ---------------------------------------------------------------------------
# 5. structure_source_tag="openfold3" on sim (not "stub")
# ---------------------------------------------------------------------------

def test_runpod_sim_structure_source_tag_is_openfold3() -> None:
    sim = P1StructureRunpodSimAdapter()
    env = sim.process(_make_input())
    dossier = env.output["dossier"]
    assert dossier["structure_source_tag"] == "openfold3", (
        f"Expected 'openfold3', got {dossier['structure_source_tag']}"
    )


# ---------------------------------------------------------------------------
# 6. Stub structure_source_tag="stub" (not "openfold3")
# ---------------------------------------------------------------------------

def test_stub_structure_source_tag_is_stub() -> None:
    stub = P1StructureStubAdapter()
    env = stub.process(_make_input())
    dossier = env.output["dossier"]
    assert dossier["structure_source_tag"] == "stub", (
        f"Expected 'stub', got {dossier['structure_source_tag']}"
    )


# ---------------------------------------------------------------------------
# 7. RunpodSim mean_plddt >= 80
# ---------------------------------------------------------------------------

def test_runpod_sim_plddt_higher_than_stub() -> None:
    sim = P1StructureRunpodSimAdapter()
    env = sim.process(_make_input())
    dossier = env.output["dossier"]
    assert dossier["mean_plddt"] >= 80.0, (
        f"RunpodSim mean_plddt {dossier['mean_plddt']} < 80"
    )
    assert dossier["binding_site_mean_plddt"] >= 80.0, (
        f"RunpodSim binding_site_mean_plddt {dossier['binding_site_mean_plddt']} < 80"
    )


# ---------------------------------------------------------------------------
# 8. RunpodSim openfold3_run_id starts with "runpod_sim:run:"
# ---------------------------------------------------------------------------

def test_runpod_sim_openfold3_run_id_format() -> None:
    sim = P1StructureRunpodSimAdapter()
    env = sim.process(_make_input())
    dossier = env.output["dossier"]
    assert dossier["openfold3_run_id"].startswith("runpod_sim:run:"), (
        f"openfold3_run_id {dossier['openfold3_run_id']!r} doesn't start with 'runpod_sim:run:'"
    )


# ---------------------------------------------------------------------------
# 9. contract_version matches across both adapters
# ---------------------------------------------------------------------------

def test_contract_version_matches() -> None:
    stub = P1StructureStubAdapter()
    sim = P1StructureRunpodSimAdapter()
    env_stub = stub.process(_make_input())
    env_sim = sim.process(_make_input())
    assert env_stub.contract_version == env_sim.contract_version == "zer0pa.layer-envelope.v1"


# ---------------------------------------------------------------------------
# 10. RunpodSim confidence >= 0.85
# ---------------------------------------------------------------------------

def test_runpod_sim_confidence_high() -> None:
    sim = P1StructureRunpodSimAdapter()
    env = sim.process(_make_input())
    assert env.confidence.score >= 0.85, (
        f"RunpodSim confidence {env.confidence.score} < 0.85"
    )
