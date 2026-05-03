"""Parked OpenFE Runpod GPU adapter for L1 molecular simulation.

This module parks the GPU-backed adapter implementation.
Constructing the class is valid; all simulation methods raise RuntimeError
to prevent accidental use without a provisioned GPU container.

Cutover procedure
-----------------
When a RunPod GPU container is available:
    1. Follow runpod.config.yaml (repo root) for container configuration.
    2. Replace this module's method bodies with real OpenFE/OpenMM calls.
    3. Set backend="runpod_gpu" in ToolAdapter (instead of "stub").
    4. Update the zer0pa-l1-stub entry point or add zer0pa-l1-runpod.
    5. Re-run the full test suite; all tests must pass with real outputs.
    6. The envelope contract (LayerEnvelope) is IDENTICAL — no downstream
       changes required. Swap is purely a backend flag.

GPU resource requirements
--------------------------
- CUDA 12.x driver (minimum)
- NVIDIA A100 / H100 recommended (32 GB VRAM minimum for FEP)
- OpenMM >= 8.1 (GPU-accelerated MD engine)
- OpenFE >= 1.0 (alchemical FEP protocol)
- Docker image: openfe/openfe:latest (or pinned tag per runpod.config.yaml)
- Host memory: 64 GB minimum for large complex FEP perturbations

Research use only. Not for clinical deployment.
"""

from __future__ import annotations

from zer0pa_biomolecular_explorer.contracts.l1 import (
    L1ChannelPanelInput,
    L1DockingInput,
    L1FEPInput,
    L1MDInput,
    L1MoleculeInput,
    L1TargetInput,
)
from zer0pa_biomolecular_explorer.envelope import LayerEnvelope

_PARKED_MSG = (
    "OpenFE Runpod adapter parked: requires GPU container; see runpod.config.yaml"
)


class OpenFERunpodAdapter:
    """Parked GPU-backed L1 adapter. Identical interface to L1StubAdapter.

    Constructing this class succeeds. All simulation methods raise RuntimeError
    until a GPU container is provisioned and the adapter is implemented.

    GPU requirements:
        - CUDA 12.x
        - OpenMM >= 8.1
        - OpenFE >= 1.0
        - A100/H100 GPU (32 GB VRAM minimum)

    Cutover procedure path: runpod.config.yaml (repo root)

    Backend value when operational: "runpod_gpu"
    (Backend.RUNPOD_GPU from envelope.py — swap is a flag change only).
    """

    def __init__(self) -> None:
        # Construction is intentionally valid.
        # Set during container startup:
        self._backend_ready: bool = False

    def ligand(
        self,
        inp: L1MoleculeInput,
        *,
        mechanism_escalation: bool = False,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        raise RuntimeError(_PARKED_MSG)

    def target(
        self,
        inp: L1TargetInput,
        *,
        mechanism_escalation: bool = False,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        raise RuntimeError(_PARKED_MSG)

    def dock(
        self,
        inp: L1DockingInput,
        *,
        mechanism_escalation: bool = False,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        raise RuntimeError(_PARKED_MSG)

    def md(
        self,
        inp: L1MDInput,
        *,
        mechanism_escalation: bool = False,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        raise RuntimeError(_PARKED_MSG)

    def fep(
        self,
        inp: L1FEPInput,
        *,
        mechanism_escalation: bool = False,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        raise RuntimeError(_PARKED_MSG)

    def channel_panel(
        self,
        inp: L1ChannelPanelInput,
        ligand_smiles: str,
        *,
        mechanism_escalation: bool = False,
        run_id: str | None = None,
        ligand_inchikey: str | None = None,
    ) -> LayerEnvelope:
        raise RuntimeError(_PARKED_MSG)
