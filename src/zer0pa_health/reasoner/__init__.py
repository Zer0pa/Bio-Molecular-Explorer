"""Reasoner module — self-bootstrapping tuple queue and adapter.

Exports
-------
ReasonerTuple           — PRD section 8 canonical tuple (Pydantic model)
ReasonerInput           — Input block (also the adapter's propose() argument)
ReasonerOutput          — Output block (returned by adapter.propose())
ReasonerQueue           — Append-only JSONL queue for tuples
ReasonerAdapter         — Protocol — plug-replaceable adapter interface
StubReasonerBackend     — Deterministic stub (no LLM) implementing ReasonerAdapter

Usage
-----
::

    from zer0pa_health.reasoner import (
        ReasonerTuple, ReasonerQueue, ReasonerAdapter, StubReasonerBackend
    )
    from zer0pa_health.reasoner.tuple_schema import ReasonerInput, TaskType
    from zer0pa_health.reasoner.day_one_flow import run_reasoner_step

Research boundary: all tuples are research-only.
See PRD section 8 for the canonical tuple schema and fine-tune counting rules.
"""

from zer0pa_health.reasoner.adapter import ReasonerAdapter, StubReasonerBackend
from zer0pa_health.reasoner.queue import ReasonerQueue
from zer0pa_health.reasoner.tuple_schema import (
    ReasonerInput,
    ReasonerOutput,
    ReasonerTuple,
)

__all__ = [
    "ReasonerTuple",
    "ReasonerInput",
    "ReasonerOutput",
    "ReasonerQueue",
    "ReasonerAdapter",
    "StubReasonerBackend",
]
