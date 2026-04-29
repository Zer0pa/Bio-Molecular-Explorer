"""ReasonerQueue — append-only JSONL queue for ReasonerTuples.

Queue path layout:
    <queue_path>/runs/<run_id>/tuples.jsonl

Each line is a JSON-encoded ReasonerTuple (model_dump_json).
Iteration is read-only and yields deserialized ReasonerTuple objects.

Fine-tune counting rules (PRD section 8):
- count_passed_for_finetune:  falsifier.status == "passed" AND
                               (ground_truth.status == "available" OR
                                ground_truth.type == "human_adjudication")
- count_negative_for_finetune: falsifier.status == "failed" OR
                                falsifier.class == "clinical_overclaim"

Note: PRD section 8 lists `human_adjudication` as a `ground_truth.type` value
and `available` as a `ground_truth.status` value. Either signal makes a tuple
fine-tune-positive eligible.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from zer0pa_health.reasoner.tuple_schema import (
    GroundTruthStatus,
    GroundTruthType,
    ReasonerFalsifierClass,
    ReasonerFalsifierStatus,
    ReasonerTuple,
)


class ReasonerQueue:
    """Append-only JSONL queue for ReasonerTuples.

    Usage::

        queue = ReasonerQueue(queue_path=Path("reasoner_queue"))
        queue.enqueue(t)
        for t in queue.iter():
            print(t.tuple_id)
    """

    def __init__(self, queue_path: Path, run_id: str = "run:default") -> None:
        """Initialise the queue.

        Args:
            queue_path: Root directory for queue storage.
            run_id:     The run_id whose subdirectory holds tuples.jsonl.
                        Defaults to "run:default" for convenience in tests.
        """
        self._run_id = run_id
        self._dir = queue_path / "runs" / run_id
        self._dir.mkdir(parents=True, exist_ok=True)
        self._file = self._dir / "tuples.jsonl"

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def enqueue(self, t: ReasonerTuple) -> None:
        """Append a validated tuple to the queue (one JSON line)."""
        with self._file.open("a", encoding="utf-8") as fh:
            fh.write(t.model_dump_json(by_alias=True) + "\n")

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def iter(self) -> Iterable[ReasonerTuple]:
        """Yield all tuples in insertion order."""
        if not self._file.exists():
            return
        with self._file.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                yield ReasonerTuple.model_validate(raw)

    def count(self) -> int:
        """Return total number of tuples in the queue."""
        if not self._file.exists():
            return 0
        return sum(1 for line in self._file.open("r", encoding="utf-8") if line.strip())

    # ------------------------------------------------------------------
    # Aggregations
    # ------------------------------------------------------------------

    def count_by_status(self) -> dict[str, int]:
        """Return {falsifier_status: count} across all tuples."""
        counts: dict[str, int] = defaultdict(int)
        for t in self.iter():
            counts[t.falsifier.status.value] += 1
        return dict(counts)

    def count_passed_for_finetune(self) -> int:
        """Count tuples eligible as fine-tune positives.

        Condition: falsifier.status == "passed" AND
                   (ground_truth.status == "available" OR
                    ground_truth.type == "human_adjudication").
        """
        count = 0
        for t in self.iter():
            if t.falsifier.status != ReasonerFalsifierStatus.PASSED:
                continue
            if (
                t.ground_truth.status == GroundTruthStatus.AVAILABLE
                or t.ground_truth.type == GroundTruthType.HUMAN_ADJUDICATION
            ):
                count += 1
        return count

    def count_negative_for_finetune(self) -> int:
        """Count tuples eligible as fine-tune negatives.

        Condition: falsifier.status == "failed" OR
                   falsifier.class == "clinical_overclaim".
        """
        count = 0
        for t in self.iter():
            if (
                t.falsifier.status == ReasonerFalsifierStatus.FAILED
                or t.falsifier.falsifier_class == ReasonerFalsifierClass.CLINICAL_OVERCLAIM
            ):
                count += 1
        return count
