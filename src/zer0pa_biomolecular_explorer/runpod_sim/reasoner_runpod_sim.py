"""Reasoner Runpod-sim adapter — simulates TxGemma 27B GPU-real reasoner.

The real `TxGemmaReasonerAdapter` will replace this at cutover (loading TxGemma
27B onto an A100/H100 with the proper Gemma 2 / Health AI Developer Foundations
license verification). Until then, this CPU-side sim emits a tuple shaped
exactly like what the GPU-real adapter would return.
"""

from __future__ import annotations

import hashlib
from typing import Any

from zer0pa_biomolecular_explorer.boundary import boundary_violations
from zer0pa_biomolecular_explorer.reasoner.adapter import (
    ReasonerAdapter,
    ReasonerInput,
    ReasonerOutput,
)
from zer0pa_biomolecular_explorer.reasoner.tuple_schema import (
    KGEdgeProposal,
    NextAction,
    TupleAbstention,
    TupleClaim,
)


def _seed(*parts: str, lo: float, hi: float) -> float:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    n = int(h[:8], 16) / 0xFFFFFFFF
    return lo + (hi - lo) * n


class TxGemmaRunpodSimAdapter:
    """CPU-side simulation of the TxGemma 27B GPU reasoner.

    Same `ReasonerAdapter` Protocol as `StubReasonerBackend`. The cutover
    replaces this sim with the real TxGemma adapter (which will load the
    27B weights onto a Runpod GPU). Until then, this returns deterministic
    stub-shaped output so the reasoner tuple queue fills with realistic-shape
    GPU-tagged tuples for cutover-acceptance testing.

    license_class is "E" (Gemma 2 + Health AI Developer Foundations terms
    must be verified before commercial deployment).
    """

    model_id = "txgemma-27b-runpod-sim"
    license_class = "E"
    backend = "runpod_gpu"

    def propose(self, input_block: ReasonerInput) -> ReasonerOutput:
        compounds = input_block.entities.compounds
        genes = input_block.entities.genes
        currents = input_block.entities.currents

        falsifier_id = f"falsifier:txgemma_sim:{compounds[0] if compounds else 'unknown'}"

        claims: list[TupleClaim] = []
        for compound in compounds:
            claim_text = (
                f"Research observation (boundary: research use only, txgemma_sim): "
                f"the multi-current evidence panel for {compound} indicates a "
                f"non-trivial repolarization-balance signal across "
                f"{', '.join(genes[:3]) if genes else 'the panel genes'}. "
                f"Mechanism interpretation is conditional on Runpod-real simulation."
            )
            # Self-policing: never emit clinical-overclaim phrases
            if not boundary_violations(claim_text):
                claims.append(
                    TupleClaim(
                        claim_id=f"claim:txgemma_sim:{compound}",
                        text=claim_text,
                        confidence=_seed(compound, "claim_conf", lo=0.6, hi=0.85),
                        source_refs=list(input_block.context_pack_refs),
                        falsifier_ref=falsifier_id,
                        multi_current_context=True,
                    )
                )

        abstentions: list[TupleAbstention] = []
        for gene in genes:
            if gene not in {"KCNH2", "SCN5A", "KCNQ1", "CACNA1C"}:
                continue
            if not any(c.text and gene in c.text for c in claims):
                abstentions.append(
                    TupleAbstention(
                        entity=f"gene:{gene}",
                        reason=(
                            f"txgemma_sim: insufficient grounding for {gene}; "
                            f"awaiting curated channel-panel input or Runpod-real simulation."
                        ),
                        evidence_gap="no_canned_channel_panel_data",
                    )
                )

        kg_edges: list[KGEdgeProposal] = []
        for compound in compounds:
            for current in currents[:2]:
                kg_edges.append(
                    KGEdgeProposal(
                        subject=f"compound:{compound}",
                        predicate="MODULATES",
                        object=f"current:{current}",
                        confidence=_seed(compound, current, "edge_conf", lo=0.5, hi=0.75),
                        source_ref="txgemma_sim",
                    )
                )

        next_actions: list[NextAction] = [
            NextAction(
                action="request_l1_full_panel_with_real_FEP",
                reason="Run L1 channel panel on Runpod with real OpenFE/Boltz-2.",
                priority="normal",
            )
        ]
        if "KCNH2" in genes and not all(g in genes for g in ("SCN5A", "KCNQ1", "CACNA1C")):
            next_actions.append(
                NextAction(
                    action="request_panel_for_genes",
                    reason="hERG present but multi-current panel incomplete; request the rest.",
                    priority="high",
                )
            )

        return ReasonerOutput(
            claims=claims,
            abstentions=abstentions,
            kg_edge_proposals=kg_edges,
            next_actions=next_actions,
        )


_PROTOCOL: ReasonerAdapter = TxGemmaRunpodSimAdapter()  # type: ignore[assignment]
