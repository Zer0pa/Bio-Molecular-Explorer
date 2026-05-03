"""P1.Handoff layer adapters — CRO-ready dossier composer + cardiac bridge.

Exports:
    P1HandoffStubAdapter  — stub canned handoff composer with full falsifier suite
    P1HandoffToyAdapter   — second plug with same interface, different verdict order
"""

from zer0pa_biomolecular_explorer.pathway1.layers.handoff.adapter import P1HandoffStubAdapter
from zer0pa_biomolecular_explorer.pathway1.layers.handoff.toy_adapter import P1HandoffToyAdapter

__all__ = ["P1HandoffStubAdapter", "P1HandoffToyAdapter"]
