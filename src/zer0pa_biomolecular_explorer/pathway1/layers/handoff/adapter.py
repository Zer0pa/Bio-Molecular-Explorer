"""P1HandoffStubAdapter — CRO-ready candidate dossier composer.

Backend: stub (canned outputs).  Cardiac bridge: when target_gene is a member
of {KCNH2, SCN5A, KCNQ1, CACNA1C}, the adapter populates l1_channel_panel_input
with all four canonical cardiac genes mapped to their canonical ion currents.
Non-cardiac targets receive l1_channel_panel_input = None.

Falsifier pipeline (per-packet):
  1. detect_confidence_tier_overclaim
  2. detect_synthesis_route_absent
  3. detect_ip_chemspace_drift  (stub Tanimoto = 0.50, no purchase_agreement_ref)
  4. detect_clinical_overclaim  (on rendered packet text fields)
  5. detect_missing_falsifier_ref  (populated AFTER the above four so >= 1 ref exists)
  6. detect_hERG_only_overreach  (cardiac targets only)

Verdict at handoff:
  "blocked" — any of (confidence_tier_overclaim, synthesis_route_absent,
               ip_chemspace_drift, clinical_overclaim, missing_falsifier_ref) FAIL
  "hold"    — hERG_only_overreach FAIL  (cardiac only)
  "pass"    — no fails

RESEARCH USE ONLY. Not for diagnosis, treatment, prescribing, clinical deployment,
regulatory compliance, or drug-safety certification.
"""

from __future__ import annotations

import json
from typing import Any

from zer0pa_biomolecular_explorer.boundary import RESEARCH_BOUNDARY
from zer0pa_biomolecular_explorer.contracts.l1 import L1ChannelGene, L1IonCurrent
from zer0pa_biomolecular_explorer.envelope import (
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
from zer0pa_biomolecular_explorer.falsifiers.detectors import (
    detect_clinical_overclaim,
    detect_confidence_tier_overclaim,
    detect_herg_only_overreach,
    detect_ip_chemspace_drift,
    detect_missing_falsifier_ref,
    detect_synthesis_route_absent,
)
from zer0pa_biomolecular_explorer.hashing import sha256_of_obj
from zer0pa_biomolecular_explorer.ids import audit_id, run_id as new_run_id
from zer0pa_biomolecular_explorer.pathway1.contracts.p1_handoff import (
    P1HandoffInput,
    P1HandoffOutput,
    P1HandoffPacket,
    P1L1ChannelPanelInput,
    P1L1ChannelPanelTarget,
)
from zer0pa_biomolecular_explorer.pathway1.contracts.p1_optimize import P1OptimizedLead

_ADAPTER_NAME = "p1-handoff-stub"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "stub_handoff_composer"

# Cardiac gene set and current mapping
_CARDIAC_GENES: frozenset[str] = frozenset({"KCNH2", "SCN5A", "KCNQ1", "CACNA1C"})

_GENE_TO_CURRENT: dict[str, str] = {
    "KCNH2": "IKr",
    "SCN5A": "INaL",
    "KCNQ1": "IKs",
    "CACNA1C": "ICaL",
}


def _build_cardiac_panel() -> P1L1ChannelPanelInput:
    """Build the canonical four-gene cardiac panel (P1→L1 bridge)."""
    targets = [
        P1L1ChannelPanelTarget(gene=gene, current=current)
        for gene, current in _GENE_TO_CURRENT.items()
    ]
    return P1L1ChannelPanelInput(targets=targets)


def _packet_text_blob(suggested_route: str | None, stub_provenance_note: str) -> str:
    """Concatenate text fields that can carry clinical-overclaim language."""
    parts = []
    if suggested_route:
        parts.append(suggested_route)
    if stub_provenance_note:
        parts.append(stub_provenance_note)
    return " ".join(parts)


def _build_suggested_route(lead: P1OptimizedLead) -> str:
    """Compose a research-only route summary from ASKCOS steps.

    Deliberately avoids any clinical-overclaim language.  The output is
    sufficient for a CRO to understand the synthetic strategy at a glance.
    """
    n = len(lead.askcos_route_steps)
    if n == 0:
        return f"Research-only route summary: 0 steps (no ASKCOS route generated)"
    first_smarts = lead.askcos_route_steps[0].rxn_smarts if lead.askcos_route_steps else "N/A"
    return (
        f"Research-only route summary: {n} steps "
        f"starting from {first_smarts}"
    )


def _compute_verdict(
    *,
    tier_overclaim_item: EnvelopeFalsifierItem,
    route_absent_item: EnvelopeFalsifierItem,
    ip_drift_item: EnvelopeFalsifierItem,
    clinical_overclaim_item: EnvelopeFalsifierItem,
    missing_ref_item: EnvelopeFalsifierItem,
    herg_overreach_item: EnvelopeFalsifierItem | None,
) -> str:
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


class P1HandoffStubAdapter:
    """Stub CRO-ready handoff adapter.

    Public interface:
        process(input: P1HandoffInput, *, run_id=None) -> LayerEnvelope

    Cardiac bridge: packet.l1_channel_panel_input carries a P1L1ChannelPanelInput
    whose .targets list has all four cardiac genes (KCNH2/IKr, SCN5A/INaL,
    KCNQ1/IKs, CACNA1C/ICaL).  Callers bridge into L1 by converting each
    P1L1ChannelPanelTarget → L1TargetInput and building an L1ChannelPanelInput.
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
                score=0.65,
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
        """Build one P1HandoffPacket and collect its falsifier items."""
        items: list[EnvelopeFalsifierItem] = []

        # ── Step 1: Confidence-tier overclaim ──────────────────────────
        tier_item = detect_confidence_tier_overclaim(
            assigned_tier=lead.confidence_tier,
            distinct_model_count=lead.distinct_models_count,
        )
        items.append(tier_item)

        # ── Step 2: Synthesis route absent ─────────────────────────────
        route_item = detect_synthesis_route_absent(
            sa_score=lead.synthetic_accessibility,
            askcos_route_steps=lead.askcos_route_steps,
        )
        items.append(route_item)

        # ── Step 3: IP / chemspace drift (stub Tanimoto = 0.50) ────────
        ip_item = detect_ip_chemspace_drift(
            candidate_smiles=lead.smiles,
            best_zinc22_tanimoto=0.50,
            zinc22_catalogue_id=None,
            purchase_agreement_ref=None,
        )
        items.append(ip_item)

        # ── Step 4: Collect falsifier_ids before missing-ref check ─────
        falsifier_refs_so_far = [item.falsifier_id for item in items]

        # ── Step 5: Clinical overclaim check (on route / provenance text)
        suggested_route = _build_suggested_route(lead)
        stub_provenance_note = (
            "All values are stub canned outputs; "
            "mechanism escalation requires Runpod-real simulation."
        )
        text_blob = _packet_text_blob(suggested_route, stub_provenance_note)
        clinical_item = detect_clinical_overclaim(text_blob)
        items.append(clinical_item)
        falsifier_refs_so_far.append(clinical_item.falsifier_id)

        # ── Step 6: Missing falsifier ref (must have >= 1 ref) ─────────
        missing_ref_item = detect_missing_falsifier_ref(falsifier_refs_so_far)
        items.append(missing_ref_item)

        # ── Step 7: hERG-only overreach (cardiac targets only) ─────────
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

        # ── Verdict ─────────────────────────────────────────────────────
        verdict = _compute_verdict(
            tier_overclaim_item=tier_item,
            route_absent_item=route_item,
            ip_drift_item=ip_item,
            clinical_overclaim_item=clinical_item,
            missing_ref_item=missing_ref_item,
            herg_overreach_item=herg_item,
        )

        # ── Final falsifier_refs list (all ids collected) ───────────────
        all_falsifier_refs = [item.falsifier_id for item in items]

        # ── Build kg_node_refs ──────────────────────────────────────────
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
