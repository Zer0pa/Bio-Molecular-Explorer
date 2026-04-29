"""L6 — Orchestration contracts.

Inputs: all envelopes, KG, audit, falsifier ledger.
Outputs: state transitions, backedges, packets, decisions, reasoner tuples.
Replaceable tools: LangGraph, Prefect, Parsl, Claude, GPT, TxGemma, stubs.

L6 is where the falsification engine actually routes. It does NOT just chain forward
through L1->L2->L3. It promotes, downgrades, reroutes, blocks, and propagates back-edges
to upstream layers based on falsifier state.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class L6Decision(str, Enum):
    PROMOTE = "promote"
    DOWNGRADE = "downgrade"
    REROUTE = "reroute"
    BLOCK = "block"
    BACKEDGE = "backedge"
    HOLD = "hold"


class L6StateTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_layer: str
    to_layer: str
    decision: L6Decision
    rationale: str
    triggered_by: list[str] = Field(
        default_factory=list,
        description="List of falsifier_ids or audit_record_ids that triggered the transition.",
    )


class L6OrchestrationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    seed_compounds_inchikeys: list[str]
    target_packet: str = Field(
        default="cardiac_evidence_packet_v0_1",
        description="Identifier of the packet kind to assemble end-of-pipeline.",
    )


class L6OrchestrationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    transitions: list[L6StateTransition]
    decisions_total: int
    backedges_propagated: int
    packets_emitted: list[str] = Field(default_factory=list)
    reasoner_tuples_emitted: int = 0
    fatal_falsifiers_blocked_export: list[str] = Field(default_factory=list)
