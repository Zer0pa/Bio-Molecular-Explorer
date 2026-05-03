"""L2 DeepXDE Runpod GPU adapter — PARKED skeleton.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.

This module is a PARKED adapter skeleton. It defines the interface for the
real DeepXDE PDE-solve adapter that runs on Runpod GPU, but raises
RuntimeError when called because the GPU container is not yet provisioned.

GPU requirements
----------------
- Container: deepxde_runpod_adapter image (see runpod.config.yaml)
- GPU: NVIDIA A100 or A10G (40+ GB VRAM recommended for PDE solve)
- Runtime: DeepXDE >= 1.10, PyTorch >= 2.1, CUDA 12.x
- Network: Runpod serverless endpoint; auth via RUNPOD_API_KEY env var

Swap path (when GPU container is ready)
-----------------------------------------
1. Implement the body of L2DeepXDERunpodAdapter.process() using the Runpod
   REST client (httpx or runpod SDK).
2. The envelope contract and method signatures must remain identical to
   L2StubAdapter.process() (PRD section 2 plug-replaceability invariant).
3. Set backend=Backend.RUNPOD_GPU and engine="DeepXDE_v1" in the ToolAdapter.
4. Remove this RuntimeError guard once integration tests pass.

Dissolution physics (future)
------------------------------
The real adapter will solve the Noyes-Whitney / diffusion PDE using DeepXDE's
physics-informed neural network framework. The PDE encodes Fickian diffusion
with a concentration-dependent dissolution driving force. Dose, particle size
distribution, and excipient parameters are boundary conditions.
"""

from __future__ import annotations

from zer0pa_biomolecular_explorer.contracts.l2 import L2PropertyInput
from zer0pa_biomolecular_explorer.envelope import LayerEnvelope


class L2DeepXDERunpodAdapter:
    """Parked L2 DeepXDE Runpod GPU adapter.

    Interface matches L2StubAdapter.process() exactly. Raises RuntimeError
    until the GPU container is provisioned and this skeleton is implemented.

    See runpod.config.yaml for container spec and GPU requirements.
    """

    NAME = "L2DeepXDERunpodAdapter"
    VERSION = "0.1.0-parked"
    ENGINE = "DeepXDE_v1_parked"

    def process(
        self,
        input: L2PropertyInput,
        run_id: str | None = None,
        *,
        mechanism_escalation: bool = False,
    ) -> LayerEnvelope:
        """Process a molecule through the DeepXDE Runpod PDE-solve pipeline.

        PARKED — raises RuntimeError until GPU container is provisioned.

        GPU requirements:
            NVIDIA A100 or A10G (40+ GB VRAM), DeepXDE >= 1.10, PyTorch >= 2.1,
            CUDA 12.x, Runpod serverless endpoint (RUNPOD_API_KEY env var required).

        Raises
        ------
        RuntimeError
            Always, until the GPU container is ready and this adapter is
            implemented.
        """
        raise RuntimeError(
            "L2 DeepXDE Runpod adapter parked: requires DeepXDE+PyTorch GPU container; "
            "see runpod.config.yaml"
        )
