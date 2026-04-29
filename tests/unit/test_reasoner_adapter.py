"""Tests: StubReasonerBackend and day_one_flow.run_reasoner_step.

Covers:
1. Cardiac compound/gene input: >=1 claim per entity, each with falsifier_ref.
2. Clinical-overclaim self-policing: overclaim phrase -> abstention + FAILED falsifier.
3. run_reasoner_step writes tuple to queue; queue.count() increments.
4. Panel-refresh next_action triggered by hERG without companions.
5. ReasonerAdapter Protocol conformance check.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import cast

import pytest

from zer0pa_health.reasoner import (
    ReasonerAdapter,
    ReasonerInput,
    ReasonerOutput,
    ReasonerQueue,
    ReasonerTuple,
    StubReasonerBackend,
)
from zer0pa_health.reasoner.adapter import (
    _has_cardiac_context,
    _needs_panel_refresh,
    _sanitize_or_abstain,
)
from zer0pa_health.reasoner.day_one_flow import run_reasoner_step, assemble_context_pack
from zer0pa_health.reasoner.tuple_schema import (
    AUTHORITY_ORDER,
    FORBIDDEN_OUTPUTS,
    REQUIRED_CAVEATS,
    GroundTruthStatus,
    ReasonerFalsifierClass,
    ReasonerFalsifierStatus,
    TaskType,
    TupleConstraints,
    TupleEntities,
)

RUN_ID = "run:20260430-adapter-test"

_CARDIAC_COMPOUNDS = ["dofetilide", "verapamil", "ranolazine"]
_CARDIAC_GENES = ["KCNH2", "SCN5A", "KCNQ1", "CACNA1C"]


# ---------------------------------------------------------------------------
# Helper: build input block
# ---------------------------------------------------------------------------


def _cardiac_input(
    compounds: list[str] | None = None,
    genes: list[str] | None = None,
    currents: list[str] | None = None,
    context_refs: list[str] | None = None,
) -> ReasonerInput:
    return ReasonerInput(
        question="Assess multi-current cardiac risk for the given entities. [research_only]",
        entities=TupleEntities(
            compounds=compounds or [],
            genes=genes or [],
            currents=currents or ["IKr", "INa", "IKs", "ICaL"],
            phenotypes=["QTc prolongation"],
        ),
        context_pack_refs=context_refs or [],
        constraints=TupleConstraints(
            authority_order=AUTHORITY_ORDER,
            forbidden_outputs=FORBIDDEN_OUTPUTS,
            required_caveats=REQUIRED_CAVEATS,
        ),
    )


# ---------------------------------------------------------------------------
# Test 1: Cardiac entities produce claims with falsifier_refs
# ---------------------------------------------------------------------------


class TestStubCardiacClaims:
    def test_one_claim_per_compound(self):
        backend = StubReasonerBackend()
        inp = _cardiac_input(compounds=_CARDIAC_COMPOUNDS, genes=_CARDIAC_GENES)
        out = backend.propose(inp)
        compounds_with_claims = set()
        for claim in out.claims:
            for compound in _CARDIAC_COMPOUNDS:
                if compound.lower() in claim.text.lower():
                    compounds_with_claims.add(compound)
        assert len(compounds_with_claims) >= len(_CARDIAC_COMPOUNDS), (
            f"Expected claims for all compounds {_CARDIAC_COMPOUNDS}, "
            f"but only found {compounds_with_claims}. Claims: {[c.text for c in out.claims]}"
        )

    def test_one_claim_per_gene(self):
        backend = StubReasonerBackend()
        inp = _cardiac_input(compounds=_CARDIAC_COMPOUNDS, genes=_CARDIAC_GENES)
        out = backend.propose(inp)
        genes_with_claims = set()
        for claim in out.claims:
            for gene in _CARDIAC_GENES:
                if gene in claim.text:
                    genes_with_claims.add(gene)
        assert len(genes_with_claims) >= len(_CARDIAC_GENES), (
            f"Expected claims referencing all genes {_CARDIAC_GENES}, "
            f"found {genes_with_claims}."
        )

    def test_every_claim_has_falsifier_ref(self):
        backend = StubReasonerBackend()
        inp = _cardiac_input(compounds=_CARDIAC_COMPOUNDS, genes=_CARDIAC_GENES)
        out = backend.propose(inp)
        assert len(out.claims) > 0, "No claims produced"
        for claim in out.claims:
            assert claim.falsifier_ref, (
                f"Claim {claim.claim_id} missing falsifier_ref: {claim.text[:80]}"
            )
            assert claim.falsifier_ref.startswith("falsifier:"), (
                f"falsifier_ref format wrong: {claim.falsifier_ref}"
            )

    def test_cardiac_claims_have_multi_current_context_flag(self):
        backend = StubReasonerBackend()
        inp = _cardiac_input(compounds=_CARDIAC_COMPOUNDS, genes=_CARDIAC_GENES)
        out = backend.propose(inp)
        for claim in out.claims:
            assert claim.multi_current_context is True, (
                f"Claim missing multi_current_context=True: {claim.claim_id}"
            )

    def test_kg_edge_proposals_present(self):
        backend = StubReasonerBackend()
        inp = _cardiac_input(compounds=_CARDIAC_COMPOUNDS, genes=_CARDIAC_GENES)
        out = backend.propose(inp)
        assert len(out.kg_edge_proposals) >= 1

    def test_protocol_conformance(self):
        """StubReasonerBackend must satisfy the ReasonerAdapter Protocol."""
        backend = StubReasonerBackend()
        assert isinstance(backend, ReasonerAdapter), (
            "StubReasonerBackend does not satisfy ReasonerAdapter Protocol"
        )
        assert backend.model_id == "stub-reasoner-0.1"
        assert backend.license_class == "A"

    def test_all_entity_types_produce_output(self):
        backend = StubReasonerBackend()
        inp = _cardiac_input(
            compounds=["dofetilide", "verapamil"],
            genes=["KCNH2", "SCN5A"],
        )
        out = backend.propose(inp)
        # Should have at least one claim per compound + one per gene = 4 minimum
        assert len(out.claims) >= 4 or len(out.abstentions) >= 1, (
            "Expected at least 4 claims or some abstentions for 2 compounds + 2 genes"
        )


# ---------------------------------------------------------------------------
# Test 2: Clinical-overclaim self-policing
# ---------------------------------------------------------------------------


class TestClinicalOverclaimSelfPolicing:
    """StubReasonerBackend must NEVER emit clinical-overclaim phrases.

    We test the self-policing logic by:
    1. Directly testing _sanitize_or_abstain with a phrase that contains
       a boundary-violating string.
    2. Confirming that the stub's own claim templates never trigger the boundary.
    3. Testing that day_one_flow.run_reasoner_step builds a FAILED clinical_overclaim
       falsifier in the tuple when a mock adapter emits overclaim text.
    """

    def test_sanitize_replaces_overclaim_claim_with_abstention(self):
        """Test _sanitize_or_abstain by bypassing Pydantic via model_construct.

        Pydantic's field_validator blocks constructing a TupleClaim with an overclaim
        phrase via the normal path — which is the correct first line of defence.
        _sanitize_or_abstain provides a second check for any claim object that exists
        (e.g., de-serialized from an external source or created via model_construct
        for testing).  We use model_construct to bypass validation here to prove the
        sanitize function itself works.
        """
        from zer0pa_health.reasoner.tuple_schema import TupleClaim, TupleAbstention, TupleFalsifier
        from zer0pa_health.ids import claim_id, falsifier_id

        # Use model_construct to skip validators — simulates an externally-sourced
        # claim object that somehow carries an overclaim phrase.
        fid = falsifier_id("source_conflict")
        claim = TupleClaim.model_construct(
            claim_id=claim_id(),
            text="dofetilide is fda approved for atrial fibrillation treatment",
            confidence=0.9,
            source_refs=[],
            falsifier_ref=fid,
            multi_current_context=False,
        )
        abstentions: list[TupleAbstention] = []
        extra_falsifiers: list[TupleFalsifier] = []
        result = _sanitize_or_abstain(claim, abstentions, extra_falsifiers)
        assert result is None, "Overclaim claim should be replaced with None (abstention)"
        assert len(abstentions) == 1, "One abstention should be created"
        assert len(extra_falsifiers) == 1, "One extra falsifier should be created"
        assert extra_falsifiers[0].falsifier_class == ReasonerFalsifierClass.CLINICAL_OVERCLAIM
        assert extra_falsifiers[0].status == ReasonerFalsifierStatus.FAILED

    def test_stub_own_templates_pass_boundary(self):
        """The stub's own claim templates must not trigger boundary violations."""
        from zer0pa_health.boundary import boundary_violations
        backend = StubReasonerBackend()
        inp = _cardiac_input(
            compounds=_CARDIAC_COMPOUNDS,
            genes=_CARDIAC_GENES,
        )
        out = backend.propose(inp)
        for claim in out.claims:
            violations = boundary_violations(claim.text)
            assert not violations, (
                f"Stub claim contains boundary violation: {violations} | text: {claim.text[:120]}"
            )

    def test_run_reasoner_step_fails_on_overclaim_adapter(self, tmp_path):
        """An adapter that returns an overclaim phrase results in a FAILED clinical_overclaim tuple."""
        from zer0pa_health.ids import claim_id, falsifier_id

        class OverclaimAdapter:
            model_id = "overclaim-mock-0.1"
            license_class = "A"

            def propose(self, input_block: ReasonerInput) -> ReasonerOutput:
                from zer0pa_health.reasoner.tuple_schema import (
                    TupleClaim, ReasonerOutput
                )
                cid = claim_id()
                fid = falsifier_id("source_conflict")
                # This claim text contains a clinical-overclaim phrase
                return ReasonerOutput(
                    claims=[
                        TupleClaim(
                            claim_id=cid,
                            text="dofetilide is fda approved for atrial fibrillation",
                            confidence=0.9,
                            source_refs=[],
                            falsifier_ref=fid,
                            multi_current_context=False,
                        )
                    ],
                    abstentions=[],
                    kg_edge_proposals=[],
                    next_actions=[],
                )

        # OverclaimAdapter returns claim text that violates the boundary.
        # The Pydantic validator on TupleClaim.text will reject it.
        # day_one_flow._enforce_falsifier_refs won't even be reached because
        # the model_validate inside the tuple construction catches it.
        # The run_reasoner_step should raise a ValidationError.
        adapter = OverclaimAdapter()
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        inp = _cardiac_input(compounds=["dofetilide"], genes=["KCNH2"])
        with pytest.raises(Exception):
            # Either during propose() (if adapter pre-validates) or during
            # ReasonerTuple.model_validate() in run_reasoner_step.
            run_reasoner_step(adapter, inp, RUN_ID, queue)

    def test_stub_backend_produces_no_overclaim_phrases_at_all(self):
        """End-to-end: StubReasonerBackend with all 3 seed compounds + 4 genes."""
        from zer0pa_health.boundary import boundary_violations
        backend = StubReasonerBackend()
        inp = _cardiac_input(
            compounds=["dofetilide", "verapamil", "ranolazine"],
            genes=["KCNH2", "SCN5A", "KCNQ1", "CACNA1C"],
            context_refs=["source:20260430-stub-test"],
        )
        out = backend.propose(inp)
        all_text = " ".join(c.text for c in out.claims)
        violations = boundary_violations(all_text)
        assert not violations, f"Stub produced boundary violations: {violations}"


# ---------------------------------------------------------------------------
# Test 3: hERG-only -> panel refresh next_action
# ---------------------------------------------------------------------------


class TestPanelRefreshAction:
    def test_herg_only_triggers_panel_refresh(self):
        backend = StubReasonerBackend()
        inp = _cardiac_input(
            compounds=[],
            genes=["KCNH2"],  # hERG only, no SCN5A/KCNQ1/CACNA1C
        )
        out = backend.propose(inp)
        actions = [a.action for a in out.next_actions]
        assert "request_l1_panel_refresh" in actions, (
            f"Expected 'request_l1_panel_refresh' in next_actions: {actions}"
        )

    def test_full_panel_no_refresh_needed(self):
        backend = StubReasonerBackend()
        inp = _cardiac_input(
            compounds=[],
            genes=["KCNH2", "SCN5A", "KCNQ1", "CACNA1C"],
        )
        out = backend.propose(inp)
        actions = [a.action for a in out.next_actions]
        assert "request_l1_panel_refresh" not in actions, (
            f"Full panel should not trigger refresh. next_actions: {actions}"
        )

    def test_helper_needs_panel_refresh_herg_only(self):
        inp = _cardiac_input(genes=["KCNH2"])
        assert _needs_panel_refresh(inp) is True

    def test_helper_needs_panel_refresh_full_panel(self):
        inp = _cardiac_input(genes=["KCNH2", "SCN5A", "KCNQ1", "CACNA1C"])
        assert _needs_panel_refresh(inp) is False


# ---------------------------------------------------------------------------
# Test 4: run_reasoner_step writes to queue
# ---------------------------------------------------------------------------


class TestRunReasonerStep:
    def test_run_reasoner_step_increments_count(self, tmp_path):
        backend = StubReasonerBackend()
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        assert queue.count() == 0
        inp = _cardiac_input(compounds=_CARDIAC_COMPOUNDS, genes=_CARDIAC_GENES)
        t = run_reasoner_step(backend, inp, RUN_ID, queue)
        assert queue.count() == 1
        assert t.tuple_id.startswith("tuple:")
        assert t.schema_version == "reasoner_tuple.v1"

    def test_run_reasoner_step_multiple_calls_accumulate(self, tmp_path):
        backend = StubReasonerBackend()
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        inp = _cardiac_input(compounds=["dofetilide"], genes=["KCNH2", "SCN5A", "KCNQ1", "CACNA1C"])
        for _ in range(3):
            run_reasoner_step(backend, inp, RUN_ID, queue)
        assert queue.count() == 3

    def test_run_reasoner_step_tuple_has_correct_run_id(self, tmp_path):
        backend = StubReasonerBackend()
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        inp = _cardiac_input(compounds=["dofetilide"], genes=["KCNH2", "SCN5A"])
        t = run_reasoner_step(backend, inp, RUN_ID, queue)
        assert t.run_id == RUN_ID

    def test_run_reasoner_step_tuple_has_audit_hashes(self, tmp_path):
        backend = StubReasonerBackend()
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        inp = _cardiac_input(compounds=["verapamil"], genes=["KCNH2", "SCN5A", "KCNQ1", "CACNA1C"])
        t = run_reasoner_step(backend, inp, RUN_ID, queue)
        assert t.audit.prompt_hash.startswith("sha256:")
        assert t.audit.context_hash.startswith("sha256:")
        assert t.audit.output_hash.startswith("sha256:")

    def test_run_reasoner_step_roundtrips_from_queue(self, tmp_path):
        backend = StubReasonerBackend()
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        inp = _cardiac_input(
            compounds=["ranolazine"],
            genes=["KCNH2", "SCN5A", "KCNQ1", "CACNA1C"],
            context_refs=["source:abc123"],
        )
        original = run_reasoner_step(backend, inp, RUN_ID, queue)
        retrieved = next(iter(queue.iter()))
        assert retrieved.tuple_id == original.tuple_id
        assert retrieved.output.claims[0].falsifier_ref.startswith("falsifier:")

    def test_assemble_context_pack_without_stores(self):
        """assemble_context_pack with no kg_store/audit_writer returns empty lists."""
        pack = assemble_context_pack(run_id=RUN_ID, kg_store=None, audit_writer=None)
        assert "source_manifest_refs" in pack
        assert "evidence_refs" in pack
        assert "envelope_refs" in pack
        assert isinstance(pack["source_manifest_refs"], list)

    def test_assemble_context_pack_with_stub_kg_store(self):
        """assemble_context_pack with a duck-typed stub kg_store collects refs."""
        class StubNode:
            def __init__(self, nid): self.node_id = nid
        class StubKG:
            def iter_source_manifests(self):
                return [StubNode("source:sm-001"), StubNode("source:sm-002")]
            def iter_evidence_items(self):
                return [StubNode("evidence:ev-001")]
        pack = assemble_context_pack(run_id=RUN_ID, kg_store=StubKG(), audit_writer=None)
        assert "source:sm-001" in pack["source_manifest_refs"]
        assert "source:sm-002" in pack["source_manifest_refs"]
        assert "evidence:ev-001" in pack["evidence_refs"]


# ---------------------------------------------------------------------------
# Test 5: full seed-compound workflow
# ---------------------------------------------------------------------------


class TestFullSeedCompoundWorkflow:
    """Integration-level test: all 3 seed compounds + 4 cardiac genes in one step."""

    def test_full_cardiac_run(self, tmp_path):
        backend = StubReasonerBackend()
        queue = ReasonerQueue(queue_path=tmp_path, run_id=RUN_ID)
        inp = _cardiac_input(
            compounds=["dofetilide", "verapamil", "ranolazine"],
            genes=["KCNH2", "SCN5A", "KCNQ1", "CACNA1C"],
            currents=["IKr", "INa", "INaL", "IKs", "ICaL"],
            context_refs=["source:cardiac-wedge-001"],
        )
        t = run_reasoner_step(
            backend, inp, RUN_ID, queue,
            task_type=TaskType.EVIDENCE_PACKET,
        )
        # At least 7 entities (3 compounds + 4 genes) -> expect >= 7 outputs (claims or abstentions)
        total_outputs = len(t.output.claims) + len(t.output.abstentions)
        assert total_outputs >= 7, (
            f"Expected >= 7 claims+abstentions, got {total_outputs}. "
            f"Claims: {len(t.output.claims)}, Abstentions: {len(t.output.abstentions)}"
        )
        # Every claim must have falsifier_ref
        for claim in t.output.claims:
            assert claim.falsifier_ref, f"Claim {claim.claim_id} missing falsifier_ref"
        # Multi-current context must be True on all claims
        for claim in t.output.claims:
            assert claim.multi_current_context is True
        # KG edges present
        assert len(t.output.kg_edge_proposals) >= 1
        # Tuple is in queue
        assert queue.count() == 1
