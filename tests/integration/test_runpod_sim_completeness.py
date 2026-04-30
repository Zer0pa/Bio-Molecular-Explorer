"""Tests for the remaining runpod-sim adapters: TxGemma reasoner + Parsl-shaped dispatcher."""

from __future__ import annotations

from zer0pa_health.orchestration import NoOpDispatcher, RunpodSimDispatcher
from zer0pa_health.reasoner.adapter import StubReasonerBackend
from zer0pa_health.reasoner.tuple_schema import (
    ReasonerInput,
    TupleConstraints,
    TupleEntities,
)
from zer0pa_health.runpod_sim import TxGemmaRunpodSimAdapter


def _build_input(compound: str = "dofetilide") -> ReasonerInput:
    return ReasonerInput(
        question=f"Research observation request: multi-current panel for {compound}",
        entities=TupleEntities(
            compounds=[compound],
            genes=["KCNH2", "SCN5A", "KCNQ1", "CACNA1C"],
            currents=["IKr", "INaL", "IKs", "ICaL"],
            phenotypes=["QT/QTc"],
        ),
        context_pack_refs=["source:FDA_E14_S7B", "source:FDA_CiPA"],
        constraints=TupleConstraints(),
    )


# ---------- TxGemma reasoner sim ----------


def test_txgemma_runpod_sim_emits_claims_with_falsifier_refs():
    sim = TxGemmaRunpodSimAdapter()
    out = sim.propose(_build_input("dofetilide"))
    assert len(out.claims) >= 1
    for c in out.claims:
        assert c.falsifier_ref is not None
        assert c.multi_current_context is True


def test_txgemma_runpod_sim_no_clinical_overclaim_in_claims():
    """The sim must NOT emit clinical-overclaim phrases."""
    from zer0pa_health.boundary import boundary_violations

    sim = TxGemmaRunpodSimAdapter()
    out = sim.propose(_build_input("verapamil"))
    for c in out.claims:
        assert not boundary_violations(c.text), (
            f"clinical-overclaim phrases in claim: {c.text}"
        )


def test_txgemma_runpod_sim_emits_abstentions_for_ungrounded_genes():
    sim = TxGemmaRunpodSimAdapter()
    out = sim.propose(_build_input("ranolazine"))
    # Sim should abstain on at least one cardiac gene (under-grounded by stub)
    cardiac_abstentions = [
        a for a in out.abstentions
        if any(g in a.entity for g in ("KCNH2", "SCN5A", "KCNQ1", "CACNA1C"))
    ]
    assert len(cardiac_abstentions) >= 1 or len(out.claims) >= 4


def test_txgemma_runpod_sim_kg_edge_proposals_present():
    sim = TxGemmaRunpodSimAdapter()
    out = sim.propose(_build_input("dofetilide"))
    assert len(out.kg_edge_proposals) >= 1
    for e in out.kg_edge_proposals:
        assert e.subject.startswith("compound:")
        assert e.object.startswith("current:")
        assert e.predicate == "MODULATES"


def test_txgemma_runpod_sim_license_flag():
    """License class is E (Gemma 2 + Health AI Developer Foundations terms must be verified)."""
    sim = TxGemmaRunpodSimAdapter()
    assert sim.license_class == "E"
    assert sim.backend == "runpod_gpu"


def test_txgemma_runpod_sim_plug_compatible_with_stub_reasoner():
    """The sim and stub backends must produce structurally compatible output."""
    sim = TxGemmaRunpodSimAdapter()
    stub = StubReasonerBackend()
    inp = _build_input("dofetilide")
    out_sim = sim.propose(inp)
    out_stub = stub.propose(inp)
    # Both must have non-empty claims OR non-empty abstentions
    assert len(out_sim.claims) + len(out_sim.abstentions) >= 1
    assert len(out_stub.claims) + len(out_stub.abstentions) >= 1
    # next_actions list shape consistent
    for action in out_sim.next_actions:
        assert action.action  # non-empty


# ---------- RunpodSimDispatcher ----------


def test_runpod_sim_dispatcher_progresses_through_states():
    d = RunpodSimDispatcher()
    handle = d.submit(lambda x: x + 1, 41)
    # First poll: queued
    r1 = d.poll(handle)
    assert r1["status"] == "queued"
    # Second poll: running
    r2 = d.poll(handle)
    assert r2["status"] == "running"
    # Third poll: done
    r3 = d.poll(handle)
    assert r3["status"] == "done"
    assert r3["output"] == 42


def test_runpod_sim_dispatcher_wait_returns_output():
    d = RunpodSimDispatcher()
    handle = d.submit(lambda x: x * 2, 21)
    output = d.wait(handle, timeout_s=5.0)
    assert output == 42


def test_runpod_sim_dispatcher_handle_is_runpod_sim_backend():
    d = RunpodSimDispatcher()
    handle = d.submit(lambda: 1)
    assert handle.backend == "runpod_sim"


def test_runpod_sim_dispatcher_error_in_function_propagates():
    import pytest as _pytest

    d = RunpodSimDispatcher()
    handle = d.submit(lambda: 1 / 0)
    with _pytest.raises(RuntimeError):
        d.wait(handle, timeout_s=5.0)


def test_runpod_sim_dispatcher_interface_compatible_with_noop():
    """RunpodSimDispatcher must support the same call shape as NoOpDispatcher."""
    noop = NoOpDispatcher()
    sim = RunpodSimDispatcher()
    fn = lambda: 99
    handle_a = noop.submit(fn)
    handle_b = sim.submit(fn)
    assert noop.wait(handle_a) == 99
    assert sim.wait(handle_b, timeout_s=5.0) == 99
