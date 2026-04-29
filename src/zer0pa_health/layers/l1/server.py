"""L1 stub FastAPI server.

Run locally via:
    python -m zer0pa_health.layers.l1.server
    zer0pa-l1-stub

Environment overrides:
    ZER0PA_L1_STUB_HOST   (default 127.0.0.1)
    ZER0PA_L1_STUB_PORT   (default 8081)

Research use only — this server returns stub molecular simulation outputs.
Not for clinical use, diagnosis, treatment, or prescribing.
"""

from __future__ import annotations

import os
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, ValidationError

from zer0pa_health.boundary import RESEARCH_BOUNDARY
from zer0pa_health.contracts.l1 import (
    L1ChannelPanelInput,
    L1DockingInput,
    L1FEPInput,
    L1MDInput,
    L1MoleculeInput,
    L1TargetInput,
)
from zer0pa_health.layers.l1.adapter import L1StubAdapter

app = FastAPI(
    title="Zer0pa L1 Molecular Simulation Stub Server",
    description=(
        "Research use only. Stub outputs for L1 molecular simulation. "
        "Not for clinical use, diagnosis, treatment, or prescribing."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

_adapter = L1StubAdapter()

_ENDPOINTS = [
    "GET /health",
    "GET /capabilities",
    "POST /v1/l1/ligand",
    "POST /v1/l1/target",
    "POST /v1/l1/dock",
    "POST /v1/l1/md",
    "POST /v1/l1/fep",
    "POST /v1/l1/channel_panel",
]


# ---------------------------------------------------------------------------
# Exception handler for ValidationError
# ---------------------------------------------------------------------------

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Return structured 400 without echoing raw input (prompt-injection mitigation)."""
    errors = []
    for e in exc.errors():
        errors.append(
            {
                "loc": list(e.get("loc", [])),
                "msg": e.get("msg", "validation error"),
                "type": e.get("type", "value_error"),
            }
        )
    return JSONResponse(
        status_code=400,
        content={
            "error": "validation_error",
            "detail": errors,
            "research_boundary": RESEARCH_BOUNDARY,
        },
    )


# ---------------------------------------------------------------------------
# GET endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "backend": "stub"}


@app.get("/capabilities")
async def capabilities() -> dict[str, Any]:
    return {
        "adapter": "l1-stub",
        "version": "0.1.0",
        "endpoints": _ENDPOINTS,
        "backend": "stub",
        "research_boundary": RESEARCH_BOUNDARY,
    }


# ---------------------------------------------------------------------------
# POST endpoints
# ---------------------------------------------------------------------------

@app.post("/v1/l1/ligand")
async def ligand_endpoint(body: L1MoleculeInput) -> dict[str, Any]:
    """Standardise ligand (stub). Returns LayerEnvelope JSON."""
    envelope = _adapter.ligand(body)
    return envelope.model_dump(mode="json")


@app.post("/v1/l1/target")
async def target_endpoint(body: L1TargetInput) -> dict[str, Any]:
    """Resolve target (stub). Returns LayerEnvelope JSON."""
    envelope = _adapter.target(body)
    return envelope.model_dump(mode="json")


@app.post("/v1/l1/dock")
async def dock_endpoint(body: L1DockingInput) -> dict[str, Any]:
    """Docking (stub). Returns LayerEnvelope JSON."""
    envelope = _adapter.dock(body)
    return envelope.model_dump(mode="json")


@app.post("/v1/l1/md")
async def md_endpoint(body: L1MDInput) -> dict[str, Any]:
    """MD simulation (stub). Returns LayerEnvelope JSON."""
    envelope = _adapter.md(body)
    return envelope.model_dump(mode="json")


@app.post("/v1/l1/fep")
async def fep_endpoint(body: L1FEPInput) -> dict[str, Any]:
    """FEP simulation (stub). Returns LayerEnvelope JSON."""
    envelope = _adapter.fep(body)
    return envelope.model_dump(mode="json")


class ChannelPanelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: L1ChannelPanelInput
    ligand_smiles: str
    ligand_inchikey: str | None = None
    mechanism_escalation: bool = False


@app.post("/v1/l1/channel_panel")
async def channel_panel_endpoint(body: ChannelPanelRequest) -> dict[str, Any]:
    """Multi-current channel panel (stub). Returns LayerEnvelope JSON."""
    envelope = _adapter.channel_panel(
        body.input,
        body.ligand_smiles,
        mechanism_escalation=body.mechanism_escalation,
        ligand_inchikey=body.ligand_inchikey,
    )
    return envelope.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    """Run the L1 stub server. Used as pyproject.scripts entry point."""
    host = os.environ.get("ZER0PA_L1_STUB_HOST", "127.0.0.1")
    port = int(os.environ.get("ZER0PA_L1_STUB_PORT", "8081"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
