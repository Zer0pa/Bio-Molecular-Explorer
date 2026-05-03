"""Tests: ReasonerQueue — round-trip enqueue/iter and status counters.

PRD section 8: queue append, iteration, fine-tune counting rules.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from zer0pa_biomolecular_explorer.ids import falsifier_id, tuple_id, utc_now_iso
from zer0pa_biomolecular_explorer.reasoner.queue import ReasonerQueue
from zer0pa_biomolecular_explorer.reasoner.tuple_schema import (
    AUTHORITY_ORDER,
    FORBIDDEN_OUTPUTS,
    REQUIRED_CAVEATS,
    GroundTruthStatus,
    GroundTruthType,
    ReasonerFalsifierClass,
    ReasonerFalsifierStatus,
    ReasonerInput,
    ReasonerOutput,
    ReasonerTuple,
    TaskType,
    TupleAbstention,
    TupleAudit,
    TupleClaim,
    TupleConstraints,
    TupleEntities,
    TupleFalsifier,
    TupleGroundTruth,
)

RUN_ID = "run:20260430-testqueue"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tuple(
    fstatus: ReasonerFalsifierStatus = ReasonerFalsifierStatus.PASSED,
    gt_status: GroundTruthStatus = GroundTruthStatus.AVAILABLE,
    fclass: ReasonerFalsifierClass = ReasonerFalsifierClass.SOURCE_CONFLICT,
    gt_type: GroundTruthType | None = None,
) -> ReasonerTuple:
    fid = falsifier_id(fclass.value)
    cid = "claim:20260430-deadbeef"
    return ReasonerTuple(
        tuple_id=tuple_id(),
        schema_version="reasoner_tuple.v1",
        created_at_utc=utc_now_iso(),
        run_id=RUN_ID,
        task_type=TaskType.EVIDENCE_PACKET,
        input=ReasonerInput(
            question="Test question for queue round-trip.",
            entities=TupleEntities(compounds=["dofetilide"], genes=["KCNH2"]),
            context_pack_refs=[],
            constraints=TupleConstraints(
                authority_order=AUTHORITY_ORDER,
                forbidden_outputs=FORBIDDEN_OUTPUTS,
                required_caveats=REQUIRED_CAVEATS,
            ),
        ),
        output=ReasonerOutput(
            claims=[
                TupleClaim(
                    claim_id=cid,
                    text="Research observation (stub): dofetilide shows IKr inhibition. [research_only]",
                    confidence=0.75,
                    source_refs=[],
                    falsifier_ref=fid,
                    multi_current_context=True,
                )
            ],
            abstentions=[],
            kg_edge_proposals=[],
            next_actions=[],
        ),
        falsifier=TupleFalsifier.model_validate(
            {
                "falsifier_id": fid,
                "class": fclass.value,
                "trigger_condition": "Test trigger condition.",
                "status": fstatus.value,
            }
        ),
        ground_truth=TupleGroundTruth(
            status=gt_status,
            type=(
                gt_type
                if gt_type is not None
                else (GroundTruthType.SOURCE_ANCHOR if gt_status == GroundTruthStatus.AVAILABLE else None)
            ),
            source_refs=[],
        ),
        audit=TupleAudit(
            prompt_hash="sha256:" + "a" * 64,
            context_hash="sha256:" + "b" * 64,
            output_hash="sha256:" + "c" * 64,
            license_flags=["A"],
        ),
    )


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------


class TestReasonerQueueRoundTrip:
    def test_enqueue_single_tuple_and_iter(self, tmp_path):
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        t = _make_tuple()
        queue.enqueue(t)
        results = list(queue.iter())
        assert len(results) == 1
        assert results[0].tuple_id == t.tuple_id
        assert results[0].schema_version == "reasoner_tuple.v1"

    def test_enqueue_multiple_tuples_preserves_order(self, tmp_path):
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        ids = []
        for _ in range(5):
            t = _make_tuple()
            queue.enqueue(t)
            ids.append(t.tuple_id)
        results = list(queue.iter())
        assert len(results) == 5
        assert [r.tuple_id for r in results] == ids

    def test_iter_on_empty_queue_returns_nothing(self, tmp_path):
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        results = list(queue.iter())
        assert results == []

    def test_count_returns_correct_number(self, tmp_path):
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        assert queue.count() == 0
        for i in range(3):
            queue.enqueue(_make_tuple())
        assert queue.count() == 3

    def test_queue_file_is_valid_jsonl(self, tmp_path):
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        t = _make_tuple()
        queue.enqueue(t)
        queue_file = tmp_path / "runs" / RUN_ID / "tuples.jsonl"
        assert queue_file.exists()
        with queue_file.open() as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["schema_version"] == "reasoner_tuple.v1"

    def test_different_run_ids_are_isolated(self, tmp_path):
        q1 = ReasonerQueue(queue_path=tmp_path, run_id="run:20260430-aaa")
        q2 = ReasonerQueue(queue_path=tmp_path, run_id="run:20260430-bbb")
        q1.enqueue(_make_tuple())
        q1.enqueue(_make_tuple())
        q2.enqueue(_make_tuple())
        assert q1.count() == 2
        assert q2.count() == 1

    def test_roundtrip_preserves_falsifier_class(self, tmp_path):
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        t = _make_tuple(fclass=ReasonerFalsifierClass.CLINICAL_OVERCLAIM)
        queue.enqueue(t)
        result = next(iter(queue.iter()))
        assert result.falsifier.falsifier_class == ReasonerFalsifierClass.CLINICAL_OVERCLAIM


# ---------------------------------------------------------------------------
# Status counter tests
# ---------------------------------------------------------------------------


class TestReasonerQueueCounters:
    def test_count_by_status_empty(self, tmp_path):
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        counts = queue.count_by_status()
        assert counts == {}

    def test_count_by_status_mixed(self, tmp_path):
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        queue.enqueue(_make_tuple(fstatus=ReasonerFalsifierStatus.PASSED))
        queue.enqueue(_make_tuple(fstatus=ReasonerFalsifierStatus.PASSED))
        queue.enqueue(_make_tuple(fstatus=ReasonerFalsifierStatus.FAILED))
        queue.enqueue(_make_tuple(fstatus=ReasonerFalsifierStatus.INCONCLUSIVE))
        counts = queue.count_by_status()
        assert counts["passed"] == 2
        assert counts["failed"] == 1
        assert counts["inconclusive"] == 1

    def test_count_passed_for_finetune(self, tmp_path):
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        # eligible: passed + available
        queue.enqueue(_make_tuple(
            fstatus=ReasonerFalsifierStatus.PASSED,
            gt_status=GroundTruthStatus.AVAILABLE,
        ))
        # eligible: passed + ground_truth.type == human_adjudication (status pending)
        queue.enqueue(_make_tuple(
            fstatus=ReasonerFalsifierStatus.PASSED,
            gt_status=GroundTruthStatus.PENDING,
            gt_type=GroundTruthType.HUMAN_ADJUDICATION,
        ))
        # not eligible: passed but pending ground truth
        queue.enqueue(_make_tuple(
            fstatus=ReasonerFalsifierStatus.PASSED,
            gt_status=GroundTruthStatus.PENDING,
        ))
        # not eligible: failed
        queue.enqueue(_make_tuple(
            fstatus=ReasonerFalsifierStatus.FAILED,
            gt_status=GroundTruthStatus.AVAILABLE,
        ))
        assert queue.count_passed_for_finetune() == 2

    def test_count_negative_for_finetune_failed_status(self, tmp_path):
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        queue.enqueue(_make_tuple(fstatus=ReasonerFalsifierStatus.FAILED))
        queue.enqueue(_make_tuple(fstatus=ReasonerFalsifierStatus.PASSED))
        assert queue.count_negative_for_finetune() == 1

    def test_count_negative_for_finetune_clinical_overclaim_class(self, tmp_path):
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        # clinical_overclaim class counts as negative regardless of status
        queue.enqueue(_make_tuple(
            fstatus=ReasonerFalsifierStatus.PASSED,
            fclass=ReasonerFalsifierClass.CLINICAL_OVERCLAIM,
        ))
        queue.enqueue(_make_tuple(
            fstatus=ReasonerFalsifierStatus.PASSED,
            fclass=ReasonerFalsifierClass.SOURCE_CONFLICT,
        ))
        assert queue.count_negative_for_finetune() == 1

    def test_count_negative_deduplicates_double_qualifiers(self, tmp_path):
        """A tuple with failed status AND clinical_overclaim class should be counted once."""
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        queue.enqueue(_make_tuple(
            fstatus=ReasonerFalsifierStatus.FAILED,
            fclass=ReasonerFalsifierClass.CLINICAL_OVERCLAIM,
        ))
        # Counts as 1 (failed status already satisfies OR condition)
        assert queue.count_negative_for_finetune() == 1

    def test_counters_zero_on_empty(self, tmp_path):
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        assert queue.count_passed_for_finetune() == 0
        assert queue.count_negative_for_finetune() == 0
