"""P1.Target layer adapters.

Exports:
  P1TargetStubAdapter  — canned stub outputs from fixtures/pathway1/targets/*.json
  P1TargetToyAdapter   — deliberately different ordering (druggability DESC) to test plug-swap

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.
"""

from zer0pa_biomolecular_explorer.pathway1.layers.target.adapter import P1TargetStubAdapter
from zer0pa_biomolecular_explorer.pathway1.layers.target.toy_adapter import P1TargetToyAdapter

__all__ = ["P1TargetStubAdapter", "P1TargetToyAdapter"]
