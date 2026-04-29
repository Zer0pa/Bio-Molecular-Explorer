"""L2.5 retrosynthesis layer — stub adapter, validators, and fixture routes.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.

Adapter hierarchy
-----------------
L25StubAdapter      — CPU-side, canned fixture routes, backend=stub  (default)
AiZynthFinder       — Parked; requires AiZynthFinder installation
ASKCOS USPTO/Pistachio — Parked; requires ASKCOS installation

Swap is controlled by backend flag only; envelope contract is identical.

Note on Reaxys:
  ASKCOS Reaxys model is CC BY-NC 4.0.
  The license_drift falsifier triggers if policy == ASKCOS_REAXYS.
  Default policy is AIZYNTHFINDER_DEFAULT (no license restriction).
"""

from zer0pa_health.layers.l2_5.adapter import L25StubAdapter
from zer0pa_health.layers.l2_5.validation import validate_atom_map, validate_rxnsmiles

__all__ = [
    "L25StubAdapter",
    "validate_rxnsmiles",
    "validate_atom_map",
]
