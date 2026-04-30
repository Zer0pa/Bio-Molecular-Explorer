"""P1.Structure layer adapters.

Exports:
    P1StructureStubAdapter  — backend=stub, deterministic canned values.
    P1StructureToyAdapter   — backend=stub, alternate deterministic seed values.
"""

from zer0pa_health.pathway1.layers.structure.adapter import P1StructureStubAdapter
from zer0pa_health.pathway1.layers.structure.toy_adapter import P1StructureToyAdapter

__all__ = [
    "P1StructureStubAdapter",
    "P1StructureToyAdapter",
]
