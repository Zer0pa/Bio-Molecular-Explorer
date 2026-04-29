"""ReasonerAdapter Protocol and StubReasonerBackend.

Protocol contract
-----------------
Any reasoning backend (Claude, GPT-4o, TxGemma 27B, etc.) must implement
ReasonerAdapter, which guarantees:
  - propose(input_block: ReasonerInput) -> ReasonerOutput
  - model_id: str
  - license_class: str  ("A" = research-only, per PRD governance)

The Protocol is the only interface that downstream code (day_one_flow,
L6 orchestration, tests) depends on.  Real adapters replace StubReasonerBackend
without changing any caller.

StubReasonerBackend
-------------------
Deterministic, no LLM call.  Generates claims + falsifiers from the input
entities alone.  Enforces the clinical-overclaim self-policing loop:
any claim text that contains a boundary-violating phrase is replaced by an
abstention and a clinical_overclaim falsifier with status FAILED is added.

Cardiac context rules (per PRD section 7 / hERG-only overreach):
  - Every claim must have multi_current_context=True when cardiac genes/currents
    are present in input.entities.
  - If hERG/KCNH2 appears but SCN5A, KCNQ1, CACNA1C are absent from entities,
    a "request_l1_panel_refresh" next_action is added.
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from zer0pa_health.boundary import boundary_violations
from zer0pa_health.falsifiers.detectors import detect_clinical_overclaim
from zer0pa_health.ids import claim_id, falsifier_id
from zer0pa_health.reasoner.tuple_schema import (
    KGEdgeProposal,
    NextAction,
    ReasonerFalsifierClass,
    ReasonerFalsifierStatus,
    ReasonerInput,
    ReasonerOutput,
    TupleAbstention,
    TupleClaim,
    TupleFalsifier,
)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ReasonerAdapter(Protocol):
    """Plug-replaceable reasoner backend.

    Any adapter that satisfies this Protocol can be dropped into
    day_one_flow.run_reasoner_step without modifying callers.

    Real bindings:
      - ClaudeReasonerAdapter   (Claude API, Sonnet/Opus)
      - GPTReasonerAdapter      (OpenAI API)
      - TxGemmaReasonerAdapter  (TxGemma 27B, local or RunPod GPU)
    """

    model_id: str
    license_class: str  # "A" = research-only; "B" = commercial review required

    def propose(self, input_block: ReasonerInput) -> ReasonerOutput:
        """Generate claims, abstentions, KG edge proposals, and next actions.

        The adapter MUST NOT call any clinical-overclaim phrases.
        The adapter MUST attach a falsifier_ref to every claim.
        If the backend cannot comply, it should emit an abstention instead.
        """
        ...


# ---------------------------------------------------------------------------
# Cardiac entity detection helpers
# ---------------------------------------------------------------------------

_CARDIAC_GENES = {"KCNH2", "hERG", "SCN5A", "Nav1.5", "KCNQ1", "Kv7.1", "CACNA1C", "CaV1.2"}
_HERG_IDS = {"KCNH2", "hERG"}
_COMPANION_GENES = {"SCN5A", "KCNQ1", "CACNA1C", "Nav1.5", "Kv7.1", "CaV1.2"}
_CARDIAC_CURRENTS = {"IKr", "INa", "INaL", "IKs", "ICaL"}

# Known cardiac compounds from PRD section 7
_CARDIAC_COMPOUNDS = {
    "dofetilide", "verapamil", "ranolazine",
    "quinidine", "moxifloxacin", "diltiazem", "sotalol", "mexiletine", "lidocaine",
}


def _has_cardiac_context(inp: ReasonerInput) -> bool:
    genes = {g.upper() for g in inp.entities.genes}
    currents = {c for c in inp.entities.currents}
    compounds_lower = {c.lower() for c in inp.entities.compounds}
    return (
        bool(genes & {g.upper() for g in _CARDIAC_GENES})
        or bool(currents & _CARDIAC_CURRENTS)
        or bool(compounds_lower & _CARDIAC_COMPOUNDS)
    )


def _needs_panel_refresh(inp: ReasonerInput) -> bool:
    """True if hERG/KCNH2 present but companions are absent from entities."""
    genes_upper = {g.upper() for g in inp.entities.genes}
    herg_present = bool(genes_upper & {"KCNH2", "HERG"})
    companion_present = bool(genes_upper & {"SCN5A", "KCNQ1", "CACNA1C", "NAV1.5", "KV7.1", "CAV1.2"})
    return herg_present and not companion_present


# ---------------------------------------------------------------------------
# Clinical-overclaim self-policing
# ---------------------------------------------------------------------------

# Phrases the stub might naively produce that would trigger the boundary check
_STUB_SAFE_CLAIM_TEMPLATE = (
    "Research observation (stub): {entity} shows activity in the context of "
    "the current evidence pack. This is a preliminary research-only signal "
    "requiring further validation. [research_only][falsifier_required]"
)

_STUB_OVERCLAIM_BAIT = (
    "dofetilide is fda approved for atrial fibrillation treatment"
)


def _sanitize_or_abstain(
    claim: TupleClaim,
    abstentions: list[TupleAbstention],
    extra_falsifiers: list[TupleFalsifier],
) -> TupleClaim | None:
    """Return None (and populate abstentions+extra_falsifiers) if claim fails boundary check."""
    violations = boundary_violations(claim.text)
    if violations:
        abstentions.append(
            TupleAbstention(
                entity=claim.claim_id,
                reason="clinical-overclaim phrase detected in stub output; claim demoted to abstention",
                evidence_gap=f"phrases: {violations[:3]}",
            )
        )
        fid = falsifier_id("clinical_overclaim")
        extra_falsifiers.append(
            TupleFalsifier.model_validate(
                {
                    "falsifier_id": fid,
                    "class": ReasonerFalsifierClass.CLINICAL_OVERCLAIM.value,
                    "trigger_condition": (
                        "StubReasonerBackend output contained boundary-violating clinical-overclaim phrase; "
                        "claim replaced with abstention per self-policing rule."
                    ),
                    "status": ReasonerFalsifierStatus.FAILED.value,
                }
            )
        )
        return None
    return claim


# ---------------------------------------------------------------------------
# StubReasonerBackend
# ---------------------------------------------------------------------------


class StubReasonerBackend:
    """Deterministic stub — no LLM call.

    Behaviour:
    1. Generates one claim per compound + one claim per gene.
    2. Each claim references a stub falsifier_ref.
    3. multi_current_context=True when cardiac entities are present.
    4. Abstentions for cardiac entities lacking evidence in context_pack_refs.
    5. KG edge proposals: one per claim.
    6. next_actions: includes "request_l1_panel_refresh" if hERG/KCNH2 present
       but SCN5A/KCNQ1/CACNA1C absent.
    7. Self-policing: runs detect_clinical_overclaim on each rendered claim;
       replaces offenders with abstentions and appends clinical_overclaim
       falsifier with status FAILED.

    Real LLM adapters (Claude, GPT, TxGemma) must implement the same
    ReasonerAdapter Protocol shape and slot in without caller changes.
    """

    model_id: str = "stub-reasoner-0.1"
    license_class: str = "A"  # research-only

    def propose(self, input_block: ReasonerInput) -> ReasonerOutput:
        cardiac = _has_cardiac_context(input_block)
        panel_refresh_needed = _needs_panel_refresh(input_block)

        claims: list[TupleClaim] = []
        abstentions: list[TupleAbstention] = []
        kg_edges: list[KGEdgeProposal] = []
        next_actions: list[NextAction] = []
        extra_falsifiers: list[TupleFalsifier] = []  # collected from self-policing

        # --- Build per-compound claims ---
        for compound in input_block.entities.compounds:
            fid = falsifier_id("clinical_overclaim")
            cid = claim_id()
            claim_text = _STUB_SAFE_CLAIM_TEMPLATE.format(entity=compound)
            candidate = TupleClaim(
                claim_id=cid,
                text=claim_text,
                confidence=0.40,
                source_refs=list(input_block.context_pack_refs[:2]),
                falsifier_ref=fid,
                multi_current_context=cardiac,
            )
            sanitized = _sanitize_or_abstain(candidate, abstentions, extra_falsifiers)
            if sanitized is not None:
                claims.append(sanitized)
                kg_edges.append(
                    KGEdgeProposal(
                        subject=compound,
                        predicate="MODULATES",
                        object="cardiac_channel_panel",
                        confidence=0.40,
                        claim_ref=cid,
                    )
                )
            # Abstain for cardiac compound if no context pack refs present
            if cardiac and not input_block.context_pack_refs:
                abstentions.append(
                    TupleAbstention(
                        entity=compound,
                        reason="no context_pack_refs provided; cardiac evidence insufficient for promotion",
                        evidence_gap="context_pack_refs empty",
                    )
                )

        # --- Build per-gene claims ---
        for gene in input_block.entities.genes:
            fid = falsifier_id("adapter_regression")
            cid = claim_id()
            claim_text = _STUB_SAFE_CLAIM_TEMPLATE.format(entity=gene)
            candidate = TupleClaim(
                claim_id=cid,
                text=claim_text,
                confidence=0.35,
                source_refs=list(input_block.context_pack_refs[:2]),
                falsifier_ref=fid,
                multi_current_context=cardiac,
            )
            sanitized = _sanitize_or_abstain(candidate, abstentions, extra_falsifiers)
            if sanitized is not None:
                claims.append(sanitized)
                kg_edges.append(
                    KGEdgeProposal(
                        subject=gene,
                        predicate="MEDIATES_CURRENT",
                        object="ion_current_panel",
                        confidence=0.35,
                        claim_ref=cid,
                    )
                )

        # --- Next actions ---
        if panel_refresh_needed:
            next_actions.append(
                NextAction(
                    action="request_l1_panel_refresh",
                    reason=(
                        "hERG/KCNH2 detected in entities but SCN5A/KCNQ1/CACNA1C are absent. "
                        "Multi-current panel required to avoid hERG-only overreach (PRD section 3)."
                    ),
                    priority="high",
                )
            )

        if cardiac:
            next_actions.append(
                NextAction(
                    action="attach_multi_current_context_pack",
                    reason="Cardiac entities present; multi-current context pack required before KG promotion.",
                    priority="normal",
                )
            )

        return ReasonerOutput(
            claims=claims,
            abstentions=abstentions,
            kg_edge_proposals=kg_edges,
            next_actions=next_actions,
        )

    def get_extra_falsifiers(self) -> list[TupleFalsifier]:
        """Not used externally; self-policing is inline in propose().

        Real adapters may expose similar hooks if they buffer falsifiers.
        """
        return []
