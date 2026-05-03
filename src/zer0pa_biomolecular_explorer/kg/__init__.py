"""Knowledge Graph core (PRD section 6).

Schema lives in `schema.py`. The store is JSONL on disk (no Neo4j on the
originating Mac, no Docker). NetworkX is used for in-memory graph operations.
"""

from zer0pa_biomolecular_explorer.kg.schema import (
    NodeType,
    EdgeType,
    KGNode,
    KGEdge,
    HARD_KG_CONSTRAINTS,
)
from zer0pa_biomolecular_explorer.kg.store import KGStore
from zer0pa_biomolecular_explorer.kg.validator import KGValidator, KGValidationError

__all__ = [
    "NodeType",
    "EdgeType",
    "KGNode",
    "KGEdge",
    "HARD_KG_CONSTRAINTS",
    "KGStore",
    "KGValidator",
    "KGValidationError",
]
