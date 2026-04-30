"""P1HandoffToyAdapter — second plug-replaceable handoff adapter.

Identical public interface and contract to P1HandoffStubAdapter.
Differences (for plug-replaceability / regression testing only):
  - engine = "toy_handoff_composer_v0",  name = "p1-handoff-toy"
  - Falsifier verdict order is reversed relative to the stub:
      hERG_only_overreach is checked FIRST, then the hard-fail group,
      so that the first falsifier_id in falsifier_refs differs from
      the stub adapter's ordering.  The verdict semantics are identical.
  - Stub Tanimoto = 0.70  (vs 0.50 in the stub adapter)
  - confidence_score = 0.60  (vs 0.65 in the stub adapter)

Schema contract is IDENTICAL to P1HandoffStubAdapter.
"""

from __future__ import annotations

from typing import Any

from zer0pa_health.boundary import RESEARCH_BOUNDARY
from zer0pa_health.contracts.l1 import L1ChannelGene, L1IonCurrent
from zer0pa_health.envelope import (
    Backend,
    ConfidenceBand,
    EnvelopeAudit,
    EnvelopeConfidence,
    EnvelopeFalsifier,
    EnvelopeFalsifierItem,
    FalsifierStatus,
    LayerEnvelope,
    LayerName,
    ToolAdapter,
)
from zer0pa_health.falsifiers.detectors import (
    detect_clinical_overclaim,
    detect_confidence_tier_overclaim,
    detect_herg_only_overreach,
    detect_ip_chemspace_drift,
    detect_missing_falsifier_ref,
    detect_synthesis_route_absent,
)
from zer0pa_health.hashing import sha256_of_obj
from zer0pa_health.ids import audit_id, run_id as new_run_id
from zer0pa_health.pathway1.contracts.p1_handoff import (
    P1HandoffInput,
    P1HandoffOutput,
    P1HandoffPacket,
    P1L1ChannelPanelInput,
    P1L1ChannelPanelTarget,
)
from zer0pa_health.pathway1.contracts.p1_optimize import P1OptimizedLead

_ADAPTER_NAME = "p1-handoff-toy"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "toy_handoff_composer_v0"

_CARDIAC_GENES: frozenset[str] = frozenset({"KCNH2", "SCN5A", "KCNQ1", "CACNA1C"})

_GENE_TO_CURRENT: dict[str, str] = {
    "KCNH2": "IKr",
    "SCN5A": "INaL",
    "KCNQ1": "IKs",
    "CACNA1C": "ICaL",
}

# Toy adapter: higher stub Tanimoto to test a different IP-drift boundary
_TOY_ZINC22_TANIMOTO = 0.70


def _build_cardiac_panel() -> P1L1ChannelPanelInput:
    targets = [
        P1L1ChannelPanelTarget(gene=gene, current=current)
        for gene, current in _GENE_TO_CURRENT.items()
    ]
    return P1L1ChannelPanelInput(targets=targets)


def _build_suggested_route(lead: P1OptimizedLead) -> str:
    n = len(lead.askcos_route_steps)
    if n == 0:
        return "Research-only route summary: 0 steps (no ASKCOS route generated)"
    first_smarts = lead.askcos_route_steps[0].rxn_smarts
    return f"Research-only route summary: {n} steps starting from {first_smarts}"


def _compute_verdict_toy(
    *,
    herg_overreach_item: EnvelopeFalsifierItem | None,
    tier_overclaim_item: EnvelopeFalsifierItem,
    route_absent_item: EnvelopeFalsifierItem,
    ip_drift_item: EnvelopeFalsifierItem,
    clinical_overclaim_item: EnvelopeFalsifierItem,
    missing_ref_item: EnvelopeFalsifierItem,
) -> str:
    """Toy adapter verdict: hERG overreach is evaluated FIRST (same semantics, different order)."""
    # Hard fails
    hard_fail_items = [
        tier_overclaim_item,
        route_absent_item,
        ip_drift_item,
        clinical_overclaim_item,
        missing_ref_item,
    ]
    if any(item.status == FalsifierStatus.FAIL for item in hard_fail_items):
        return "blocked"
    if herg_overreach_item is not None and herg_overreach_item.status == FalsifierStatus.FAIL:
        return "hold"
    return "pass"


class P1HandoffToyAdapter:
    """Toy handoff adapter — identical interface to P1HandoffStubAdapter.

    Use for plug-replaceability regression testing.  Different engine name,
    slightly different falsifier-check order (hERG first), and different
    stub Tanimoto value.  The output schema is identical.
    """

    def process(
        self,
        input: P1HandoffInput,
        *,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        rid = run_id or new_run_id()
        input_dict = input.model_dump()

        packets: list[P1HandoffPacket] = []
        all_falsifier_items: list[EnvelopeFalsifierItem] = []

        is_cardiac = input.target_gene in _CARDIAC_GENES

        for lead_dict in input.leads:
            lead = P1OptimizedLead.model_validate(lead_dict)
            packet, items = self._build_packet(lead, input, is_cardiac)
            packets.append(packet)
            all_falsifier_items.extend(items)

        handoff_output = P1HandoffOutput(
            pathway1_run_id=input.pathway1_run_id,
            target_id=input.target_id,
            n_packets=len(packets),
            packets=packets,
        )
        output_dict: dict[str, Any] = handoff_output.model_dump()

        any_fail = any(
            item.status == FalsifierStatus.FAIL for item in all_falsifier_items
        )
        falsifier_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS

        return LayerEnvelope(
            run_id=rid,
            layer=LayerName.P1_HANDOFF,
            tool_adapter=ToolAdapter(
                name=_ADAPTER_NAME,
                version=_ADAPTER_VERSION,
                backend=Backend.STUB,
                engine=_ENGINE,
            ),
            input_refs=[input.pathway1_run_id],
            output=output_dict,
            confidence=EnvelopeConfidence(
                score=0.60,
                band=ConfidenceBand.MEDIUM,
                basis=["stub_handoff_composer", "cardiac_bridge"],
            ),
            falsifier=EnvelopeFalsifier(
                status=falsifier_status,
                items=all_falsifier_items,
            ),
            audit=EnvelopeAudit(
                audit_record_id=audit_id(),
                input_hash=sha256_of_obj(input_dict),
                output_hash=sha256_of_obj(output_dict),
                source_manifest_refs=input.audit_refs,
            ),
            back_edges=[],
        )

    def _build_packet(
        self,
        lead: P1OptimizedLead,
        input: P1HandoffInput,
        is_cardiac: bool,
    ) -> tuple[P1HandoffPacket, list[EnvelopeFalsifierItem]]:
        items: list[EnvelopeFalsifierItem] = []

        # Toy order: hERG overreach FIRST (cardiac only), then hard-fail group
        herg_item: EnvelopeFalsifierItem | None = None
        l1_panel: P1L1ChannelPanelInput | None = None

        if is_cardiac:
            l1_panel = _build_cardiac_panel()
            panel_genes = [t.gene for t in l1_panel.targets]
            herg_item = detect_herg_only_overreach(
                panel_genes_present=panel_genes,
                explicit_absence=[],
            )
            items.append(herg_item)

        # Then the standard hard-fail checks
        tier_item = detect_confidence_tier_overclaim(
            assigned_tier=lead.confidence_tier,
            distinct_model_count=lead.distinct_models_count,
        )
        items.append(tier_item)

        route_item = detect_synthesis_route_absent(
            sa_score=lead.synthetic_accessibility,
            askcos_route_steps=lead.askcos_route_steps,
        )
        items.append(route_item)

        ip_item = detect_ip_chemspace_drift(
            candidate_smiles=lead.smiles,
            best_zinc22_tanimoto=_TOY_ZINC22_TANIMOTO,
            zinc22_catalogue_id=None,
            purchase_agreement_ref=None,
        )
        items.append(ip_item)

        suggested_route = _build_suggested_route(lead)
        stub_provenance_note = (
            "All values are stub canned outputs; "
            "mechanism escalation requires Runpod-real simulation."
        )
        text_blob = " ".join(
            p for p in [suggested_route, stub_provenance_note] if p
        )
        clinical_item = detect_clinical_overclaim(text_blob)
        items.append(clinical_item)

        falsifier_refs_so_far = [item.falsifier_id for item in items]
        missing_ref_item = detect_missing_falsifier_ref(falsifier_refs_so_far)
        items.append(missing_ref_item)

        verdict = _compute_verdict_toy(
            herg_overreach_item=herg_item,
            tier_overclaim_item=tier_item,
            route_absent_item=route_item,
            ip_drift_item=ip_item,
            clinical_overclaim_item=clinical_item,
            missing_ref_item=missing_ref_item,
        )

        all_falsifier_refs = [item.falsifier_id for item in items]

        kg_node_refs: list[str] = [input.target_id]
        if input.target_gene:
            kg_node_refs.append(f"gene:{input.target_gene}")
        kg_node_refs.extend(input.audit_refs)

        packet = P1HandoffPacket(
            pathway1_run_id=input.pathway1_run_id,
            candidate_id=lead.lead_id,
            smiles=lead.smiles,
            target_id=input.target_id,
            target_gene=input.target_gene,
            predicted_pIC50=lead.predicted_pIC50,
            binding_affinity_source="stub_optimizer",
            admet=lead.admet_panel,
            selectivity_score=lead.selectivity_score,
            synthetic_accessibility=lead.synthetic_accessibility,
            estimated_synthesis_steps=len(lead.askcos_route_steps),
            suggested_route=suggested_route,
            confidence_tier=lead.confidence_tier,  # type: ignore[arg-type]
            generation_method=getattr(lead, "generation_method", "stub"),
            iteration_number=lead.iteration_number,
            parent_scaffold=lead.parent_scaffold,
            audit_refs=input.audit_refs if input.audit_refs else ["stub_audit_ref"],
            kg_node_refs=kg_node_refs,
            source_manifest_refs=input.audit_refs,
            l1_channel_panel_input=l1_panel,
            pains_alert=False,
            structural_alert_flags=[],
            zinc22_purchasable_analogue=None,
            is_cardiac_target=is_cardiac,
            verdict_at_handoff=verdict,  # type: ignore[arg-type]
            falsifier_refs=all_falsifier_refs,
            distinct_models_count=lead.distinct_models_count,
            stub_provenance_note=stub_provenance_note,
        )

        return packet, items
