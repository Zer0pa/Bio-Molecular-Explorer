"""Day-one flow: assemble context pack, run reasoner, build + enqueue tuple.

This module is a pure-function layer between:
  - L6 orchestration (which calls assemble_context_pack)
  - ReasonerAdapter (which calls propose())
  - ReasonerQueue (which persists the tuple)

Real LLM bindings (Claude, GPT-4o, TxGemma 27B) slot in by implementing
the ReasonerAdapter Protocol and replacing StubReasonerBackend in the
run_reasoner_step call.  No caller changes required.

Day-one flow (PRD section 8):
1. L6 assembles a context pack from KG, audit, source manifests, prior
   envelopes, and falsifier state.
2. ReasonerAdapter.propose() is called with the assembled input block.
3. Each claim is validated: must have a falsifier_ref.  Claims without refs
   are downgraded to abstentions with a missing_falsifier_ref falsifier.
4. A ReasonerTuple is built, validated, and enqueued.
5. The tuple is returned to L6 for KG promotion and audit recording.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from zer0pa_health.falsifiers.detectors import detect_clinical_overclaim
from zer0pa_health.hashing import sha256_of_obj
from zer0pa_health.ids import falsifier_id, tuple_id, utc_now_iso
from zer0pa_health.reasoner.tuple_schema import (
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
    TupleFalsifier,
    TupleGroundTruth,
)

if TYPE_CHECKING:
    from zer0pa_health.reasoner.adapter import ReasonerAdapter
    from zer0pa_health.reasoner.queue import ReasonerQueue


# ---------------------------------------------------------------------------
# Context pack assembly
# ---------------------------------------------------------------------------


def assemble_context_pack(
    run_id: str,
    kg_store: Any | None = None,
    audit_writer: Any | None = None,
) -> dict[str, list[str]]:
    """Collect context pack references for the reasoner's input block.

    Pulls from three sources (all optional at day-one; real integrations
    replace the stub paths):

    1. KG nodes: SourceManifest and EvidenceItem IDs from kg_store
       (expected duck-type: kg_store.iter_source_manifests() and
       kg_store.iter_evidence_items()).
    2. Audit source_manifest table: source IDs from audit_writer
       (expected duck-type: audit_writer.source_manifest_ids()).
    3. Prior envelopes: any envelope IDs already logged for this run_id.

    Returns a dict with keys:
      "source_manifest_refs"  — SourceManifest IDs
      "evidence_refs"         — EvidenceItem IDs
      "envelope_refs"         — LayerEnvelope run-scoped refs
    """
    source_refs: list[str] = []
    evidence_refs: list[str] = []
    envelope_refs: list[str] = []

    # KG store
    if kg_store is not None:
        if hasattr(kg_store, "iter_source_manifests"):
            for node in kg_store.iter_source_manifests():
                nid = getattr(node, "node_id", None) or getattr(node, "id", None)
                if nid:
                    source_refs.append(str(nid))
        if hasattr(kg_store, "iter_evidence_items"):
            for item in kg_store.iter_evidence_items():
                iid = getattr(item, "node_id", None) or getattr(item, "id", None)
                if iid:
                    evidence_refs.append(str(iid))

    # Audit writer source manifest IDs
    if audit_writer is not None:
        if hasattr(audit_writer, "source_manifest_ids"):
            for sid in audit_writer.source_manifest_ids():
                source_refs.append(str(sid))
        if hasattr(audit_writer, "envelope_ids_for_run"):
            for eid in audit_writer.envelope_ids_for_run(run_id):
                envelope_refs.append(str(eid))

    return {
        "source_manifest_refs": source_refs,
        "evidence_refs": evidence_refs,
        "envelope_refs": envelope_refs,
    }


# ---------------------------------------------------------------------------
# Missing-falsifier-ref guard
# ---------------------------------------------------------------------------


def _enforce_falsifier_refs(output: ReasonerOutput) -> ReasonerOutput:
    """Downgrade claims without a falsifier_ref to abstentions.

    This is the missing_falsifier_ref guard at the reasoner level.
    Any claim that reaches this point without a falsifier_ref gets
    replaced by an abstention; the claim is not lost from the audit trail
    (it lands in abstentions.reason).
    """
    good_claims = []
    extra_abstentions = list(output.abstentions)

    for claim in output.claims:
        if not claim.falsifier_ref or not claim.falsifier_ref.strip():
            extra_abstentions.append(
                TupleAbstention(
                    entity=claim.claim_id,
                    reason=(
                        "missing_falsifier_ref guard: claim downgraded to abstention "
                        "because falsifier_ref was absent. "
                        f"Original claim text: {claim.text[:120]}"
                    ),
                    evidence_gap="no falsifier_ref attached",
                )
            )
        else:
            good_claims.append(claim)

    return ReasonerOutput(
        claims=good_claims,
        abstentions=extra_abstentions,
        kg_edge_proposals=output.kg_edge_proposals,
        next_actions=output.next_actions,
    )


# ---------------------------------------------------------------------------
# Build top-level falsifier for the tuple
# ---------------------------------------------------------------------------


def _build_tuple_falsifier(
    output: ReasonerOutput,
    adapter_model_id: str,
) -> TupleFalsifier:
    """Derive a single top-level TupleFalsifier from the output state.

    Priority:
    1. If any claim text contains a clinical overclaim -> clinical_overclaim FAILED
    2. If any claim lacks a falsifier_ref (shouldn't happen after guard, but check) ->
       adapter_regression FAILED
    3. If adapter is stub -> adapter_regression PASSED (informational)
    4. Default -> adapter_regression PASSED
    """
    # Check for any clinical overclaim in rendered output
    all_text = " ".join(c.text for c in output.claims)
    oc_item = detect_clinical_overclaim(all_text)
    from zer0pa_health.envelope import FalsifierStatus
    if oc_item.status == FalsifierStatus.FAIL:
        return TupleFalsifier.model_validate(
            {
                "falsifier_id": falsifier_id("clinical_overclaim"),
                "class": ReasonerFalsifierClass.CLINICAL_OVERCLAIM.value,
                "trigger_condition": (
                    "Output text contains clinical-overclaim phrase after self-policing loop; "
                    f"adapter={adapter_model_id}"
                ),
                "status": ReasonerFalsifierStatus.FAILED.value,
            }
        )

    # Check for any missing falsifier refs that survived the guard
    missing = [c for c in output.claims if not c.falsifier_ref]
    if missing:
        return TupleFalsifier.model_validate(
            {
                "falsifier_id": falsifier_id("adapter_regression"),
                "class": ReasonerFalsifierClass.ADAPTER_REGRESSION.value,
                "trigger_condition": (
                    f"{len(missing)} claims survived the falsifier_ref guard without a ref"
                ),
                "status": ReasonerFalsifierStatus.FAILED.value,
            }
        )

    # All good
    fclass = (
        ReasonerFalsifierClass.ADAPTER_REGRESSION.value
        if "stub" in adapter_model_id.lower()
        else ReasonerFalsifierClass.SOURCE_CONFLICT.value
    )
    return TupleFalsifier.model_validate(
        {
            "falsifier_id": falsifier_id(fclass),
            "class": fclass,
            "trigger_condition": (
                f"Routine adapter output check; adapter={adapter_model_id}. "
                "No violations detected."
            ),
            "status": ReasonerFalsifierStatus.PASSED.value,
        }
    )


# ---------------------------------------------------------------------------
# Main orchestration entry point
# ---------------------------------------------------------------------------


def run_reasoner_step(
    adapter: "ReasonerAdapter",
    input_block: ReasonerInput,
    run_id: str,
    queue: "ReasonerQueue",
    task_type: TaskType = TaskType.EVIDENCE_PACKET,
    ground_truth_status: GroundTruthStatus = GroundTruthStatus.NOT_AVAILABLE,
    ground_truth_type: GroundTruthType | None = None,
    ground_truth_source_refs: list[str] | None = None,
) -> ReasonerTuple:
    """Execute one reasoner step, build the tuple, validate it, enqueue it.

    Args:
        adapter:       Any ReasonerAdapter implementation.
        input_block:   Assembled ReasonerInput (from assemble_context_pack).
        run_id:        Current run identifier.
        queue:         ReasonerQueue to append to.
        task_type:     PRD section 8 task_type enum value.
        ground_truth_*: Ground truth metadata for the tuple.

    Returns:
        The validated ReasonerTuple that was enqueued.

    Notes:
        - Real LLM calls (Claude, GPT, TxGemma) bind onto ReasonerAdapter and
          replace StubReasonerBackend.
        - This function is the only place where tuples are built; all callers
          must go through here so the falsifier_ref guard is always applied.
    """
    # 1. Call adapter
    raw_output: ReasonerOutput = adapter.propose(input_block)

    # 2. Enforce falsifier refs (missing_falsifier_ref guard)
    output = _enforce_falsifier_refs(raw_output)

    # 3. Derive top-level tuple falsifier
    tuple_falsifier = _build_tuple_falsifier(output, adapter.model_id)

    # 4. Compute audit hashes
    input_dump = input_block.model_dump()
    output_dump = output.model_dump()
    prompt_hash = sha256_of_obj(input_dump)
    context_hash = sha256_of_obj(input_dump.get("context_pack_refs", []))
    output_hash = sha256_of_obj(output_dump)

    audit = TupleAudit(
        prompt_hash=prompt_hash,
        context_hash=context_hash,
        output_hash=output_hash,
        license_flags=[adapter.license_class],
    )

    # 5. Build ground truth block
    ground_truth = TupleGroundTruth(
        status=ground_truth_status,
        type=ground_truth_type,
        source_refs=ground_truth_source_refs or [],
    )

    # 6. Assemble and validate the full tuple
    t = ReasonerTuple(
        tuple_id=tuple_id(),
        schema_version="reasoner_tuple.v1",
        created_at_utc=utc_now_iso(),
        run_id=run_id,
        task_type=task_type,
        input=input_block,
        output=output,
        falsifier=tuple_falsifier,
        ground_truth=ground_truth,
        audit=audit,
    )

    # 7. Enqueue
    queue.enqueue(t)

    return t
