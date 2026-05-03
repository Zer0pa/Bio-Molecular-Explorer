"""End-to-end run orchestration.

`run_compound(inchikey, ...)` exercises the full L1->L2.5->L2->L3->L4->L5 +
cardiac packet + reasoner pipeline for one compound on the CPU-side build,
writing every audit table, every KG runtime node, every replay command,
every reasoner tuple, and every offload manifest entry along the way.

This is what `zer0pa-biomolecular-explorer run-cardiac <compound>` invokes.
"""

from zer0pa_biomolecular_explorer.runs.cardiac_run import (
    CardiacRunResult,
    run_cardiac_compound,
    run_cardiac_wedge,
)
from zer0pa_biomolecular_explorer.runs.l6_orchestrated_run import L6RunResult, run_cardiac_via_l6_router
from zer0pa_biomolecular_explorer.runs.pathway1_run import (
    Pathway1RunResult,
    run_pathway1_cardiac_wedge,
    run_pathway1_compound,
)

__all__ = [
    "CardiacRunResult",
    "L6RunResult",
    "run_cardiac_compound",
    "run_cardiac_wedge",
    "run_cardiac_via_l6_router",
    "Pathway1RunResult",
    "run_pathway1_compound",
    "run_pathway1_cardiac_wedge",
]
