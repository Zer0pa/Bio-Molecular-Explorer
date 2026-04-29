"""L2 property / formulation / ADMET layer adapter.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.

Adapter hierarchy
-----------------
L2StubAdapter           — CPU-side, string-heuristic proxies, backend=stub (default)
L2DeepXDERunpodAdapter  — Parked; requires DeepXDE + PyTorch GPU container
                           (raises RuntimeError until provisioned; see parked_runpod.py)

Public API
----------
L2StubAdapter       Main adapter. process(input, run_id, *, mechanism_escalation) -> LayerEnvelope
score_property      Functional entry-point for raw descriptor + ADMET dict (no envelope)

Swap is controlled by backend flag only; LayerEnvelope contract is identical
between adapters (PRD section 2 plug-replaceability invariant).
"""

from zer0pa_health.layers.l2.adapter import L2StubAdapter, score_property
from zer0pa_health.layers.l2.dissolution import dissolution_pinn_stub
from zer0pa_health.layers.l2.parked_runpod import L2DeepXDERunpodAdapter

__all__ = [
    "L2StubAdapter",
    "score_property",
    "dissolution_pinn_stub",
    "L2DeepXDERunpodAdapter",
]
