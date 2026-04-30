"""Runpod simulation adapters.

These are CPU-only adapters that PRETEND to be the GPU-real adapter at the
envelope level: same shape, different values, `tool_adapter.backend = "runpod_gpu"`.
They exist so the cutover test can flip the backend flag in runpod.config.yaml,
swap the stub adapter for the sim adapter, and verify that downstream layers
parse the envelope unchanged.

The real Runpod GPU adapters (DiffDock V2, OpenFE, OpenMM, Boltz-2, TxGemma)
will replace these sim adapters at cutover. Their envelope shape MUST be
identical; the falsification gate is `GATE_PLUG_SWAP_TEST_PASSES_WITH_REAL_ADAPTER`.
"""

from zer0pa_health.runpod_sim.l1_runpod_sim import L1RunpodSimAdapter
from zer0pa_health.runpod_sim.l2_runpod_sim import L2RunpodSimAdapter
from zer0pa_health.runpod_sim.l5_runpod_sim import L5RunpodSimAdapter
from zer0pa_health.runpod_sim.reasoner_runpod_sim import TxGemmaRunpodSimAdapter

__all__ = [
    "L1RunpodSimAdapter",
    "L2RunpodSimAdapter",
    "L5RunpodSimAdapter",
    "TxGemmaRunpodSimAdapter",
]
