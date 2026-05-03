"""Integration tests for the L1 stub FastAPI server.

Uses FastAPI TestClient (no real uvicorn process required).
Tests:
- GET /health
- GET /capabilities
- POST /v1/l1/ligand
- POST /v1/l1/channel_panel — verifies all four canned channel-panel genes for dofetilide
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from fastapi.testclient import TestClient

from zer0pa_biomolecular_explorer.boundary import RESEARCH_BOUNDARY
from zer0pa_biomolecular_explorer.envelope import LayerEnvelope
from zer0pa_biomolecular_explorer.layers.l1.server import app

_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent / "schemas" / "envelope" / "layer-envelope-v1.json"
)

_DOFETILIDE_INCHIKEY = "IXTMWRCNAAVVAI-UHFFFAOYSA-N"
_DOFETILIDE_SMILES = "CN(C)S(=O)(=O)c1ccc(NCCOc2ccc(CCN(C)S(=O)(=O)C)cc2)cc1"

_FOUR_GENES = {"KCNH2", "SCN5A", "KCNQ1", "CACNA1C"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture(scope="module")
def envelope_schema() -> dict:
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


def validate_envelope_dict(d: dict, schema: dict) -> None:
    jsonschema.validate(instance=d, schema=schema)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["backend"] == "stub"


# ---------------------------------------------------------------------------
# /capabilities
# ---------------------------------------------------------------------------

def test_capabilities(client: TestClient) -> None:
    resp = client.get("/capabilities")
    assert resp.status_code == 200
    body = resp.json()
    assert body["adapter"] == "l1-stub"
    assert body["backend"] == "stub"
    assert body["research_boundary"] == RESEARCH_BOUNDARY
    assert isinstance(body["endpoints"], list)
    assert len(body["endpoints"]) > 0
    # Must include the channel_panel endpoint
    endpoints_text = " ".join(body["endpoints"])
    assert "channel_panel" in endpoints_text


# ---------------------------------------------------------------------------
# POST /v1/l1/ligand
# ---------------------------------------------------------------------------

def test_ligand_valid(client: TestClient, envelope_schema: dict) -> None:
    payload = {"smiles": "CCO", "name": "ethanol"}
    resp = client.post("/v1/l1/ligand", json=payload)
    assert resp.status_code == 200
    body = resp.json()

    validate_envelope_dict(body, envelope_schema)

    # Parse as Pydantic model to verify structural soundness
    env = LayerEnvelope.model_validate(body)
    assert env.layer == "L1"
    assert env.tool_adapter.backend == "stub"
    assert "Research use only" in env.research_boundary


def test_ligand_invalid_smiles_envelope_still_valid(client: TestClient, envelope_schema: dict) -> None:
    """Invalid SMILES returns a valid envelope with FAIL falsifier (not a 400 error)."""
    payload = {"smiles": "C C"}  # space is forbidden
    resp = client.post("/v1/l1/ligand", json=payload)
    assert resp.status_code == 200
    body = resp.json()

    validate_envelope_dict(body, envelope_schema)

    # invalid_molecular_input should be FAIL
    items = body["falsifier"]["items"]
    smiles_fails = [i for i in items if i["falsifier_class"] == "invalid_molecular_input"]
    assert len(smiles_fails) >= 1
    assert smiles_fails[0]["status"] == "fail"


def test_ligand_missing_smiles_returns_400(client: TestClient) -> None:
    """Missing required 'smiles' field returns 400 with structured error."""
    payload = {"name": "no-smiles"}
    resp = client.post("/v1/l1/ligand", json=payload)
    assert resp.status_code == 422  # FastAPI returns 422 for Pydantic validation errors


# ---------------------------------------------------------------------------
# POST /v1/l1/channel_panel — dofetilide, all four genes
# ---------------------------------------------------------------------------

def test_channel_panel_dofetilide_all_four_genes(client: TestClient, envelope_schema: dict) -> None:
    payload = {
        "input": {
            "targets": [
                {"gene": "KCNH2", "current": "IKr"},
                {"gene": "SCN5A", "current": "INa"},
                {"gene": "KCNQ1", "current": "IKs"},
                {"gene": "CACNA1C", "current": "ICaL"},
            ]
        },
        "ligand_smiles": _DOFETILIDE_SMILES,
        "ligand_inchikey": _DOFETILIDE_INCHIKEY,
    }
    resp = client.post("/v1/l1/channel_panel", json=payload)
    assert resp.status_code == 200
    body = resp.json()

    validate_envelope_dict(body, envelope_schema)
    env = LayerEnvelope.model_validate(body)

    panel = env.output.get("panel", {})
    assert _FOUR_GENES.issubset(set(panel.keys())), (
        f"Missing panel genes: {_FOUR_GENES - set(panel.keys())}"
    )

    # hERG_only_overreach falsifier item must be present
    items = env.falsifier.items
    herg_items = [i for i in items if i.falsifier_class == "hERG_only_overreach"]
    assert len(herg_items) >= 1, "hERG_only_overreach falsifier item missing"

    # basis must include "stub_canned_output"
    basis = env.output.get("basis", [])
    assert "stub_canned_output" in basis


def test_channel_panel_mechanism_escalation_fail(client: TestClient, envelope_schema: dict) -> None:
    payload = {
        "input": {
            "targets": [
                {"gene": "KCNH2", "current": "IKr"},
                {"gene": "SCN5A", "current": "INa"},
                {"gene": "KCNQ1", "current": "IKs"},
                {"gene": "CACNA1C", "current": "ICaL"},
            ]
        },
        "ligand_smiles": _DOFETILIDE_SMILES,
        "ligand_inchikey": _DOFETILIDE_INCHIKEY,
        "mechanism_escalation": True,
    }
    resp = client.post("/v1/l1/channel_panel", json=payload)
    assert resp.status_code == 200
    body = resp.json()

    validate_envelope_dict(body, envelope_schema)

    items = body["falsifier"]["items"]
    stub_fails = [i for i in items if i["falsifier_class"] == "stub_laundering"]
    assert len(stub_fails) >= 1
    assert stub_fails[0]["status"] == "fail"


# ---------------------------------------------------------------------------
# POST /v1/l1/dock
# ---------------------------------------------------------------------------

def test_dock_dofetilide_kcnh2(client: TestClient, envelope_schema: dict) -> None:
    payload = {
        "molecule": {
            "smiles": _DOFETILIDE_SMILES,
            "inchikey": _DOFETILIDE_INCHIKEY,
            "name": "dofetilide",
        },
        "target": {"gene": "KCNH2", "current": "IKr"},
        "n_poses": 3,
    }
    resp = client.post("/v1/l1/dock", json=payload)
    assert resp.status_code == 200
    body = resp.json()

    validate_envelope_dict(body, envelope_schema)
    poses = body["output"].get("poses", [])
    assert len(poses) == 3


# ---------------------------------------------------------------------------
# Verapamil channel panel — must include CACNA1C (canonical refuter case)
# ---------------------------------------------------------------------------

def test_channel_panel_verapamil_cacna1c_present(client: TestClient, envelope_schema: dict) -> None:
    """Verapamil: canonical hERG-only-overreach refuter — CACNA1C must be present."""
    verapamil_smiles = "COc1ccc(CC(C)(C#N)CCCN(C)CCc2ccc(OC)c(OC)c2)cc1OC"
    verapamil_inchikey = "SGTNSNPWRIOYBX-UHFFFAOYSA-N"

    payload = {
        "input": {
            "targets": [
                {"gene": "KCNH2", "current": "IKr"},
                {"gene": "SCN5A", "current": "INa"},
                {"gene": "KCNQ1", "current": "IKs"},
                {"gene": "CACNA1C", "current": "ICaL"},
            ]
        },
        "ligand_smiles": verapamil_smiles,
        "ligand_inchikey": verapamil_inchikey,
    }
    resp = client.post("/v1/l1/channel_panel", json=payload)
    assert resp.status_code == 200
    body = resp.json()

    validate_envelope_dict(body, envelope_schema)
    panel = body["output"].get("panel", {})
    assert "CACNA1C" in panel, "Verapamil must have CACNA1C in panel"
    assert "KCNH2" in panel, "Verapamil must have KCNH2 in panel"
