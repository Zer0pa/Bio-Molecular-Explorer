"""Unit tests for L1StubAdapter.

Tests cover:
- ligand() with valid SMILES returns valid envelope with backend="stub"
- ligand() with invalid SMILES emits invalid_molecular_input FAIL
- dock() for dofetilide+KCNH2 returns 3 poses
- channel_panel() for dofetilide returns all four genes
- mechanism_escalation=True with backend=stub emits stub_laundering FAIL
- Envelope validates against schemas/envelope/layer-envelope-v1.json
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from zer0pa_health.contracts.l1 import (
    L1ChannelGene,
    L1ChannelPanelInput,
    L1DockingInput,
    L1FEPInput,
    L1IonCurrent,
    L1MDInput,
    L1MoleculeInput,
    L1TargetInput,
)
from zer0pa_health.envelope import Backend, FalsifierStatus
from zer0pa_health.layers.l1.adapter import L1StubAdapter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent / "schemas" / "envelope" / "layer-envelope-v1.json"
)

_DOFETILIDE_INCHIKEY = "IXTMWRCNAAVVAI-UHFFFAOYSA-N"
_DOFETILIDE_SMILES = "CN(C)S(=O)(=O)c1ccc(NCCOc2ccc(CCN(C)S(=O)(=O)C)cc2)cc1"

_FOUR_GENES = {"KCNH2", "SCN5A", "KCNQ1", "CACNA1C"}


@pytest.fixture(scope="module")
def adapter() -> L1StubAdapter:
    return L1StubAdapter()


@pytest.fixture(scope="module")
def envelope_schema() -> dict:
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


def validate_envelope(envelope_dict: dict, schema: dict) -> None:
    jsonschema.validate(instance=envelope_dict, schema=schema)


# ---------------------------------------------------------------------------
# Test: ligand() with valid SMILES returns backend=stub envelope
# ---------------------------------------------------------------------------

def test_ligand_valid_smiles_returns_stub_backend(adapter: L1StubAdapter, envelope_schema: dict) -> None:
    mol = L1MoleculeInput(smiles="CCO", name="ethanol")
    env = adapter.ligand(mol)

    # Backend must be stub
    assert env.tool_adapter.backend == Backend.STUB or env.tool_adapter.backend == "stub"

    # Layer must be L1
    assert env.layer == "L1" or env.layer.value == "L1"  # type: ignore[union-attr]

    # Research boundary must be present
    assert "Research use only" in env.research_boundary

    # Envelope validates against JSON schema
    env_dict = env.model_dump(mode="json")
    validate_envelope(env_dict, envelope_schema)

    # invalid_molecular_input should be PASS for valid SMILES
    smiles_items = [
        i for i in env.falsifier.items
        if i.falsifier_class == "invalid_molecular_input"
    ]
    assert len(smiles_items) >= 1
    assert smiles_items[0].status == FalsifierStatus.PASS or smiles_items[0].status == "pass"


# ---------------------------------------------------------------------------
# Test: ligand() with invalid SMILES emits FAIL for invalid_molecular_input
# ---------------------------------------------------------------------------

def test_ligand_invalid_smiles_emits_fail(adapter: L1StubAdapter, envelope_schema: dict) -> None:
    # "C C" contains a space which is forbidden by the regex validator
    mol = L1MoleculeInput(smiles="C C", name="invalid")
    env = adapter.ligand(mol)

    env_dict = env.model_dump(mode="json")
    validate_envelope(env_dict, envelope_schema)

    smiles_items = [
        i for i in env.falsifier.items
        if i.falsifier_class == "invalid_molecular_input"
    ]
    assert len(smiles_items) >= 1
    status = smiles_items[0].status
    assert status == FalsifierStatus.FAIL or status == "fail"

    # Overall falsifier status should be FAIL
    overall = env.falsifier.status
    assert overall == FalsifierStatus.FAIL or overall == "fail"


# ---------------------------------------------------------------------------
# Test: dock() for dofetilide + KCNH2 returns 3 poses
# ---------------------------------------------------------------------------

def test_dock_dofetilide_kcnh2_returns_three_poses(adapter: L1StubAdapter, envelope_schema: dict) -> None:
    mol = L1MoleculeInput(
        smiles=_DOFETILIDE_SMILES,
        inchikey=_DOFETILIDE_INCHIKEY,
        name="dofetilide",
    )
    target = L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr)
    dock_inp = L1DockingInput(molecule=mol, target=target, n_poses=3)

    env = adapter.dock(dock_inp)
    env_dict = env.model_dump(mode="json")
    validate_envelope(env_dict, envelope_schema)

    poses = env.output.get("poses", [])
    assert len(poses) == 3, f"Expected 3 poses, got {len(poses)}"

    for pose in poses:
        # Each pose must have a docking score in [-8, -5] range
        score = pose.get("estimated_binding_kcal_mol")
        assert score is not None
        assert -8.5 <= score <= -4.5, f"Pose score {score} outside expected range"
        # Confidence in [0.4, 0.7] range
        conf = pose.get("confidence")
        assert conf is not None
        assert 0.3 <= conf <= 0.75, f"Pose confidence {conf} outside expected range"
        # structure_basis must be "stub"
        assert pose.get("structure_basis") == "stub"


# ---------------------------------------------------------------------------
# Test: channel_panel() for dofetilide returns all 4 canonical genes
# ---------------------------------------------------------------------------

def test_channel_panel_dofetilide_all_four_genes(adapter: L1StubAdapter, envelope_schema: dict) -> None:
    targets = [
        L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr),
        L1TargetInput(gene=L1ChannelGene.SCN5A, current=L1IonCurrent.INa),
        L1TargetInput(gene=L1ChannelGene.KCNQ1, current=L1IonCurrent.IKs),
        L1TargetInput(gene=L1ChannelGene.CACNA1C, current=L1IonCurrent.ICaL),
    ]
    panel_inp = L1ChannelPanelInput(targets=targets)

    env = adapter.channel_panel(
        panel_inp,
        _DOFETILIDE_SMILES,
        ligand_inchikey=_DOFETILIDE_INCHIKEY,
    )

    env_dict = env.model_dump(mode="json")
    validate_envelope(env_dict, envelope_schema)

    output = env.output
    panel = output.get("panel", {})

    # All four genes must be present in the panel dict
    panel_genes = set(panel.keys())
    assert _FOUR_GENES.issubset(panel_genes), (
        f"Missing genes from panel: {_FOUR_GENES - panel_genes}"
    )

    # Explicit absence should cover genes with null values
    explicit_absence = output.get("explicit_absence", [])
    for gene in _FOUR_GENES:
        entry = panel.get(gene, {})
        if entry.get("ic50_uM") is None:
            # Should appear in panel (as null) or in explicit_absence
            assert gene in panel or gene in explicit_absence, (
                f"Gene {gene} has null value but is neither in panel nor explicit_absence"
            )

    # hERG_only_overreach falsifier item must be present
    herg_items = [
        i for i in env.falsifier.items
        if i.falsifier_class == "hERG_only_overreach"
    ]
    assert len(herg_items) >= 1, "hERG_only_overreach falsifier item missing from channel_panel"


# ---------------------------------------------------------------------------
# Test: mechanism_escalation=True emits stub_laundering FAIL
# ---------------------------------------------------------------------------

def test_mechanism_escalation_emits_stub_laundering_fail(adapter: L1StubAdapter, envelope_schema: dict) -> None:
    mol = L1MoleculeInput(smiles="CCO")
    env = adapter.ligand(mol, mechanism_escalation=True)

    env_dict = env.model_dump(mode="json")
    validate_envelope(env_dict, envelope_schema)

    stub_items = [
        i for i in env.falsifier.items
        if i.falsifier_class == "stub_laundering"
    ]
    assert len(stub_items) >= 1, "stub_laundering item missing"
    status = stub_items[0].status
    assert status == FalsifierStatus.FAIL or status == "fail", (
        f"Expected stub_laundering FAIL, got {status}"
    )

    overall = env.falsifier.status
    assert overall == FalsifierStatus.FAIL or overall == "fail"


# ---------------------------------------------------------------------------
# Test: mechanism_escalation=False (default) has stub_laundering PASS
# ---------------------------------------------------------------------------

def test_no_mechanism_escalation_has_stub_laundering_pass(adapter: L1StubAdapter) -> None:
    mol = L1MoleculeInput(smiles="CCO")
    env = adapter.ligand(mol, mechanism_escalation=False)

    stub_items = [
        i for i in env.falsifier.items
        if i.falsifier_class == "stub_laundering"
    ]
    assert len(stub_items) >= 1
    status = stub_items[0].status
    assert status == FalsifierStatus.PASS or status == "pass"


# ---------------------------------------------------------------------------
# Test: audit fields are properly populated
# ---------------------------------------------------------------------------

def test_audit_fields_present(adapter: L1StubAdapter) -> None:
    mol = L1MoleculeInput(smiles="c1ccccc1", name="benzene")
    env = adapter.ligand(mol)

    audit = env.audit
    assert audit.audit_record_id.startswith("audit:")
    assert audit.input_hash.startswith("sha256:")
    assert audit.output_hash.startswith("sha256:")
    # Hashes should be 64 hex chars after "sha256:"
    assert len(audit.input_hash) == 7 + 64  # "sha256:" + 64 chars
    assert len(audit.output_hash) == 7 + 64


# ---------------------------------------------------------------------------
# Test: run_id propagation
# ---------------------------------------------------------------------------

def test_run_id_propagation(adapter: L1StubAdapter) -> None:
    custom_run_id = "run:20260430-test0001"
    mol = L1MoleculeInput(smiles="CCO")
    env = adapter.ligand(mol, run_id=custom_run_id)
    assert env.run_id == custom_run_id


def test_run_id_auto_generated(adapter: L1StubAdapter) -> None:
    mol = L1MoleculeInput(smiles="CCO")
    env = adapter.ligand(mol)
    assert env.run_id.startswith("run:")


# ---------------------------------------------------------------------------
# Test: channel_panel mechanism_escalation=True
# ---------------------------------------------------------------------------

def test_channel_panel_mechanism_escalation_fail(adapter: L1StubAdapter, envelope_schema: dict) -> None:
    targets = [
        L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr),
        L1TargetInput(gene=L1ChannelGene.SCN5A, current=L1IonCurrent.INa),
        L1TargetInput(gene=L1ChannelGene.KCNQ1, current=L1IonCurrent.IKs),
        L1TargetInput(gene=L1ChannelGene.CACNA1C, current=L1IonCurrent.ICaL),
    ]
    panel_inp = L1ChannelPanelInput(targets=targets)

    env = adapter.channel_panel(
        panel_inp,
        _DOFETILIDE_SMILES,
        mechanism_escalation=True,
        ligand_inchikey=_DOFETILIDE_INCHIKEY,
    )
    env_dict = env.model_dump(mode="json")
    validate_envelope(env_dict, envelope_schema)

    stub_items = [
        i for i in env.falsifier.items
        if i.falsifier_class == "stub_laundering"
    ]
    assert len(stub_items) >= 1
    status = stub_items[0].status
    assert status == FalsifierStatus.FAIL or status == "fail"


# ---------------------------------------------------------------------------
# Test: fep() basic smoke test
# ---------------------------------------------------------------------------

def test_fep_basic(adapter: L1StubAdapter, envelope_schema: dict) -> None:
    verapamil_smiles = "COc1ccc(CC(C)(C#N)CCCN(C)CCc2ccc(OC)c(OC)c2)cc1OC"
    verapamil_inchikey = "SGTNSNPWRIOYBX-UHFFFAOYSA-N"

    mol_a = L1MoleculeInput(
        smiles=_DOFETILIDE_SMILES,
        inchikey=_DOFETILIDE_INCHIKEY,
    )
    mol_b = L1MoleculeInput(
        smiles=verapamil_smiles,
        inchikey=verapamil_inchikey,
    )
    target = L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr)
    fep_inp = L1FEPInput(ligand_a=mol_a, ligand_b=mol_b, target=target, method="RBFE")

    env = adapter.fep(fep_inp)
    env_dict = env.model_dump(mode="json")
    validate_envelope(env_dict, envelope_schema)

    assert "ddg_kcal_mol" in env.output
    assert "convergence_ok" in env.output


# ---------------------------------------------------------------------------
# Test: md() basic smoke test
# ---------------------------------------------------------------------------

def test_md_basic(adapter: L1StubAdapter, envelope_schema: dict) -> None:
    mol = L1MoleculeInput(
        smiles=_DOFETILIDE_SMILES,
        inchikey=_DOFETILIDE_INCHIKEY,
    )
    target = L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr)
    md_inp = L1MDInput(molecule=mol, target=target, pose_index=0, sim_ns=10.0)

    env = adapter.md(md_inp)
    env_dict = env.model_dump(mode="json")
    validate_envelope(env_dict, envelope_schema)

    assert "rmsd_nm" in env.output
    assert "convergence_metric" in env.output
    assert env.output["rmsd_nm"] >= 0
    assert 0 <= env.output["convergence_metric"] <= 1
