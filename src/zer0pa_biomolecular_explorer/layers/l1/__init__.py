"""L1 molecular simulation layer — stub adapter, canned outputs, and REST server.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.

Adapter hierarchy
-----------------
L1StubAdapter        — CPU-side, canned outputs, backend=stub  (default, always available)
OpenFERunpodAdapter  — Parked; requires GPU container (see runpod.config.yaml)

Swap is controlled by backend flag only; envelope contract is identical.
"""

from zer0pa_biomolecular_explorer.layers.l1.adapter import L1StubAdapter
from zer0pa_biomolecular_explorer.layers.l1.canned import (
    canned_channel_panel,
    canned_pose,
    canned_binding,
    canned_md,
    canned_fep,
)

__all__ = [
    "L1StubAdapter",
    "canned_channel_panel",
    "canned_pose",
    "canned_binding",
    "canned_md",
    "canned_fep",
]
