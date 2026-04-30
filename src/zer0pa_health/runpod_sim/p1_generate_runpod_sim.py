"""P1.Generate RunPod-sim adapter.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.

Same envelope shape and falsifier-class set as P1GenerateStubAdapter.
backend=runpod_gpu, engine=reinvent4_runpod_sim.
Uses different deterministic seeds (shifted pool + different Tanimoto table).
"""

from __future__ import annotations

import hashlib

from zer0pa_health.envelope import Backend, ToolAdapter
from zer0pa_health.pathway1.layers.generate.adapter import (
    P1GenerateStubAdapter,
    _SMILES_POOL,
    _ZINC22_TANIMOTO,
)

# Rotated pool (shifted by 3 positions) to simulate GPU-generated output
_RUNPOD_SMILES_POOL: tuple[str, ...] = _SMILES_POOL[3:] + _SMILES_POOL[:3]

# Different Tanimoto table (rotate + scale down slightly to simulate more novel GPU output)
_RUNPOD_ZINC22_TANIMOTO: tuple[float, ...] = tuple(
    round(t * 0.92, 4) for t in (_ZINC22_TANIMOTO[3:] + _ZINC22_TANIMOTO[:3])
)

_RUNPOD_NAME = "p1-generate-runpod-sim"
_RUNPOD_VERSION = "0.1.0"
_RUNPOD_ENGINE = "reinvent4_runpod_sim"


class P1GenerateRunpodSimAdapter(P1GenerateStubAdapter):
    """RunPod-sim adapter: GPU backend simulation with different deterministic seeds.

    backend=runpod_gpu, engine=reinvent4_runpod_sim.
    Output schema matches P1GenerateStubAdapter exactly for plug-swap safety.
    """

    NAME = _RUNPOD_NAME
    VERSION = _RUNPOD_VERSION
    ENGINE = _RUNPOD_ENGINE

    def __init__(self, *, force_ip_drift_fail: bool = False) -> None:
        super().__init__(force_ip_drift_fail=force_ip_drift_fail)
        self._tool_adapter = ToolAdapter(
            name=self.NAME,
            version=self.VERSION,
            backend=Backend.RUNPOD_GPU,
            engine=self.ENGINE,
        )

    def _backend_value(self) -> str:
        return Backend.RUNPOD_GPU.value

    def _pool(self) -> tuple[str, ...]:
        return _RUNPOD_SMILES_POOL

    def _zinc22_tanimoto_for_pool_idx(self, pool_idx: int) -> float:
        """Use runpod-specific Tanimoto table."""
        return _RUNPOD_ZINC22_TANIMOTO[pool_idx]
