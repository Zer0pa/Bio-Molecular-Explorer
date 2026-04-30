"""Unit tests for P1StructureStubAdapter and P1StructureToyAdapter.

Tests cover:
- process(target_id=uniprot:Q12809) returns valid envelope with pocket populated
- process with pdb_ref_hint="AF-P00533-F1" on normal path: AF leakage PASSES
  (because openfold3_run_id is auto-set to "stub:run:<rid>", not None)
- _process_af_db_leak_case with pdb_ref_hint="AF-P00533-F1": FAIL (uniprot_af_id set,
  openfold3_run_id=None, structure_source_tag="alphafold_db_precomputed")
- Forced alphafold_db_precomputed path triggers detector and envelope falsifier.status=FAIL
- Plug-swap: Stub vs Toy output keys match, falsifier classes match
- JSON Schema validation
- Determinism: same input → same output_hash
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from zer0pa_health.envelope import Backend, FalsifierStatus
from zer0pa_health.pathway1.contracts.p1_structure import P1StructureInput
from zer0pa_health.pathway1.layers.structure import P1StructureStubAdapter, P1StructureToyAdapter

_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent / "schemas" / "envelope" / "layer-envelope-v1.json"
)

_TARGET_ID = "uniprot:Q12809"
_GENE = "KCNH2"
_AF_HINT = "AF-P00533-F1"


@pytest.fixture(scope="module")
def schema() -> dict:
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def stub_adapter() -> P1StructureStubAdapter:
    return P1StructureStubAdapter()


@pytest.fixture(scope="module")
def toy_adapter() -> P1StructureToyAdapter:
    return P1StructureToyAdapter()


def _make_input(*, target_id: str = _TARGET_ID, gene: str = _GENE, pdb_hint: str | None = None) -> P1StructureInput:
    return P1StructureInput(
        target_id=target_id,
        gene_symbol=gene,
        sequence=None,
        pdb_ref_hint=pdb_hint,
    )


# ---------------------------------------------------------------------------
# 1. Normal process() returns valid envelope with pocket
# ---------------------------------------------------------------------------

def test_process_returns_valid_envelope(stub_adapter: P1StructureStubAdapter, schema: dict) -> None:
    inp = _make_input()
    env = stub_adapter.process(inp)

    # Layer must be P1.Structure
    assert env.layer == "P1.Structure" or str(env.layer) == "P1.Structure"

    # Backend must be stub
    assert env.tool_adapter.backend == Backend.STUB.value or env.tool_adapter.backend == Backend.STUB

    # run_id must be present
    assert env.run_id.startswith("run:")

    # Research boundary present
    assert "Research use only" in env.research_boundary

    # JSON Schema validation
    env_dict = env.model_dump(mode="json")
    jsonschema.validate(instance=env_dict, schema=schema)

    # Output must have dossier with pocket
    dossier = env.output["dossier"]
    assert dossier["target_id"] == _TARGET_ID
    assert dossier["gene_symbol"] == _GENE
    assert dossier["structure_source_tag"] == "stub"
    pocket = dossier["pocket"]
    assert len(pocket["binding_site_residues"]) >= 8
    assert 350.0 <= pocket["pocket_volume_angstrom3"] <= 450.0
    assert pocket["pocket_label"] == "stub_inner_cavity"

    # pLDDT values in expected ranges
    assert 70.0 <= dossier["mean_plddt"] <= 92.0
    assert 65.0 <= dossier["binding_site_mean_plddt"] <= 88.0

    # openfold3_run_id should be a stub-run string
    assert dossier["openfold3_run_id"].startswith("stub:run:")

    # uniprot_af_id should be None
    assert dossier["uniprot_af_id"] is None


# ---------------------------------------------------------------------------
# 2. Normal process() with pdb_ref_hint=AF pattern → AF leakage PASSES
# ---------------------------------------------------------------------------

def test_process_af_hint_normal_path_leakage_passes(stub_adapter: P1StructureStubAdapter) -> None:
    """On normal path, even with an AF pdb_ref_hint, openfold3_run_id is auto-set
    so detect_alphafold_d_leakage must PASS (not trigger).
    """
    inp = _make_input(pdb_hint=_AF_HINT)
    env = stub_adapter.process(inp)

    af_items = [it for it in env.falsifier.items if it.falsifier_class == "alphafold_d_leakage"]
    assert len(af_items) >= 1, "alphafold_d_leakage item missing"
    status = af_items[0].status
    assert status in (FalsifierStatus.PASS, "pass"), (
        f"Expected alphafold_d_leakage PASS on normal path, got {status}"
    )


# ---------------------------------------------------------------------------
# 3. _process_af_db_leak_case with AF hint → AF leakage FAILS
# ---------------------------------------------------------------------------

def test_af_db_leak_case_fails(stub_adapter: P1StructureStubAdapter) -> None:
    """The forced AF DB path must trip the alphafold_d_leakage detector (FAIL)."""
    inp = _make_input(pdb_hint=_AF_HINT)
    env = stub_adapter._process_af_db_leak_case(inp)

    dossier = env.output["dossier"]
    # structure_source_tag must be alphafold_db_precomputed
    assert dossier["structure_source_tag"] == "alphafold_db_precomputed"
    # openfold3_run_id must be None
    assert dossier["openfold3_run_id"] is None
    # uniprot_af_id must match the AF pattern
    assert dossier["uniprot_af_id"] == _AF_HINT

    # alphafold_d_leakage must be FAIL
    af_items = [it for it in env.falsifier.items if it.falsifier_class == "alphafold_d_leakage"]
    assert len(af_items) >= 1, "alphafold_d_leakage item missing in leak case"
    assert af_items[0].status in (FalsifierStatus.FAIL, "fail"), (
        f"Expected alphafold_d_leakage FAIL, got {af_items[0].status}"
    )

    # Overall envelope falsifier.status must be FAIL
    assert env.falsifier.status in (FalsifierStatus.FAIL, "fail"), (
        f"Expected overall FAIL, got {env.falsifier.status}"
    )


# ---------------------------------------------------------------------------
# 4. Forced alphafold_db_precomputed — envelope falsifier.status=FAIL
# ---------------------------------------------------------------------------

def test_af_db_precomputed_forced_envelope_fail(stub_adapter: P1StructureStubAdapter, schema: dict) -> None:
    """Verify schema still validates even when falsifier.status=FAIL."""
    inp = _make_input(pdb_hint=_AF_HINT)
    env = stub_adapter._process_af_db_leak_case(inp)
    env_dict = env.model_dump(mode="json")
    jsonschema.validate(instance=env_dict, schema=schema)
    assert env_dict["falsifier"]["status"] == "fail"


# ---------------------------------------------------------------------------
# 5. Plug-swap: Stub vs Toy output keys match, falsifier classes match
# ---------------------------------------------------------------------------

def test_stub_vs_toy_output_keys_match(stub_adapter: P1StructureStubAdapter, toy_adapter: P1StructureToyAdapter) -> None:
    inp = _make_input()
    env_stub = stub_adapter.process(inp)
    env_toy = toy_adapter.process(inp)

    # Output keys must match
    keys_stub = sorted(env_stub.output.keys())
    keys_toy = sorted(env_toy.output.keys())
    assert keys_stub == keys_toy, f"Output key mismatch: stub={keys_stub}, toy={keys_toy}"

    # Dossier keys must match
    dossier_keys_stub = sorted(env_stub.output["dossier"].keys())
    dossier_keys_toy = sorted(env_toy.output["dossier"].keys())
    assert dossier_keys_stub == dossier_keys_toy, (
        f"Dossier key mismatch: stub={dossier_keys_stub}, toy={dossier_keys_toy}"
    )

    # Pocket keys must match
    pocket_keys_stub = sorted(env_stub.output["dossier"]["pocket"].keys())
    pocket_keys_toy = sorted(env_toy.output["dossier"]["pocket"].keys())
    assert pocket_keys_stub == pocket_keys_toy, (
        f"Pocket key mismatch: stub={pocket_keys_stub}, toy={pocket_keys_toy}"
    )


def test_stub_vs_toy_falsifier_classes_match(stub_adapter: P1StructureStubAdapter, toy_adapter: P1StructureToyAdapter) -> None:
    inp = _make_input()
    env_stub = stub_adapter.process(inp)
    env_toy = toy_adapter.process(inp)

    classes_stub = {it.falsifier_class for it in env_stub.falsifier.items}
    classes_toy = {it.falsifier_class for it in env_toy.falsifier.items}
    assert classes_stub == classes_toy, (
        f"Falsifier class mismatch: stub={classes_stub}, toy={classes_toy}"
    )


def test_stub_vs_toy_different_values(stub_adapter: P1StructureStubAdapter, toy_adapter: P1StructureToyAdapter) -> None:
    """Stub and Toy must produce different numeric values (different seeds)."""
    inp = _make_input()
    env_stub = stub_adapter.process(inp, run_id="run:20260430-test0001")
    env_toy = toy_adapter.process(inp, run_id="run:20260430-test0001")

    plddt_stub = env_stub.output["dossier"]["mean_plddt"]
    plddt_toy = env_toy.output["dossier"]["mean_plddt"]
    assert plddt_stub != plddt_toy, "Stub and Toy should produce different pLDDT values"


# ---------------------------------------------------------------------------
# 6. Determinism: same input → same output_hash
# ---------------------------------------------------------------------------

def test_determinism_same_input_same_output_hash(stub_adapter: P1StructureStubAdapter) -> None:
    inp = _make_input()
    env1 = stub_adapter.process(inp, run_id="run:20260430-determinism01")
    env2 = stub_adapter.process(inp, run_id="run:20260430-determinism01")
    assert env1.audit.output_hash == env2.audit.output_hash, (
        f"output_hash differs for same input: {env1.audit.output_hash} vs {env2.audit.output_hash}"
    )


def test_determinism_toy_same_input(toy_adapter: P1StructureToyAdapter) -> None:
    inp = _make_input()
    env1 = toy_adapter.process(inp, run_id="run:20260430-toy-det01")
    env2 = toy_adapter.process(inp, run_id="run:20260430-toy-det01")
    assert env1.audit.output_hash == env2.audit.output_hash


# ---------------------------------------------------------------------------
# 7. Required falsifier classes are present
# ---------------------------------------------------------------------------

def test_required_falsifier_classes_present(stub_adapter: P1StructureStubAdapter) -> None:
    inp = _make_input()
    env = stub_adapter.process(inp)
    classes = {it.falsifier_class for it in env.falsifier.items}
    required = {"alphafold_d_leakage", "structure_confidence_below_threshold", "stub_laundering", "clinical_overclaim"}
    missing = required - classes
    assert not missing, f"Missing falsifier classes: {missing}"


# ---------------------------------------------------------------------------
# 8. stub_laundering PASSES on normal stub path (mechanism_escalation=False)
# ---------------------------------------------------------------------------

def test_stub_laundering_passes_normal_path(stub_adapter: P1StructureStubAdapter) -> None:
    inp = _make_input()
    env = stub_adapter.process(inp)
    stub_items = [it for it in env.falsifier.items if it.falsifier_class == "stub_laundering"]
    assert len(stub_items) >= 1
    assert stub_items[0].status in (FalsifierStatus.PASS, "pass"), (
        f"stub_laundering should PASS on normal path, got {stub_items[0].status}"
    )


# ---------------------------------------------------------------------------
# 9. run_id propagation
# ---------------------------------------------------------------------------

def test_run_id_propagation(stub_adapter: P1StructureStubAdapter) -> None:
    custom_run_id = "run:20260430-custom0001"
    inp = _make_input()
    env = stub_adapter.process(inp, run_id=custom_run_id)
    assert env.run_id == custom_run_id


def test_run_id_auto_generated(stub_adapter: P1StructureStubAdapter) -> None:
    inp = _make_input()
    env = stub_adapter.process(inp)
    assert env.run_id.startswith("run:")


# ---------------------------------------------------------------------------
# 10. Audit fields are populated
# ---------------------------------------------------------------------------

def test_audit_fields_populated(stub_adapter: P1StructureStubAdapter) -> None:
    inp = _make_input()
    env = stub_adapter.process(inp)
    assert env.audit.audit_record_id.startswith("audit:")
    assert env.audit.input_hash.startswith("sha256:")
    assert env.audit.output_hash.startswith("sha256:")
    assert len(env.audit.input_hash) == 71  # "sha256:" (7) + 64 hex chars
    assert len(env.audit.output_hash) == 71
