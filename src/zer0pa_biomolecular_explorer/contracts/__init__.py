"""Per-layer interface contracts.

Each module exports `Input` and `Output` Pydantic models for that layer.
Cross-layer code depends ONLY on these models plus the universal envelope.
Tool/adapter implementations import from this package; they NEVER define their
own contract types. This is what makes the plug-replaceability invariant testable.
"""

from zer0pa_biomolecular_explorer.contracts import l1, l2, l2_5, l3, l4, l5, l6

__all__ = ["l1", "l2", "l2_5", "l3", "l4", "l5", "l6"]
