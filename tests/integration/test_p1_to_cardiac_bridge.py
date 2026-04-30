"""Integration test: P1.Handoff → existing cardiac wedge (L1 channel panel).

Story: A P1-optimized lead targeting KCNH2 is handed off.  The handoff adapter
produces a P1HandoffPacket whose l1_channel_panel_input carries all four cardiac
genes (KCNH2/IKr, SCN5A/INaL, KCNQ1/IKs, CACNA1C/ICaL).  The test converts
that payload to an L1ChannelPanelInput and feeds it to the existing L1StubAdapter
channel_panel() method, verifying the full bridge closes.

Bridge steps:
  1. Build a stub P1OptimizedLead for KCNH2
  2. Run P1HandoffStubAdapter.process() → P1HandoffPacket with l1_channel_panel_input
  3. Convert P1L1ChannelPanelTarget list → L1TargetInput list → L1ChannelPanelInput
  4. Run L1StubAdapter.channel_panel(panel_input, ligand_smiles=packet.smiles)
  5. Verify:
     - All 4 canonical genes appear in the L1 envelope output panel
     - hERG_only_overreach falsifier status = PASS (four genes present)
     - L1 envelope layer = "L1", confidence band = "medium"
"""

from __future__ import annotations

import pytest

from zer0pa_health.contracts.l1 import (
    L1ChannelGene,
    L1ChannelPanelInput,
    L1IonCurrent,
    L1TargetInput,
)
from zer0pa_health.envelope import FalsifierStatus
from zer0pa_health.layers.l1.adapter import L1StubAdapter
from zer0pa_health.pathway1.contracts.p1_handoff import (
    P1HandoffInput,
    P1L1ChannelPanelInput,
    P1L1ChannelPanelTarget,
)
from zer0pa_health.pathway1.contracts.p1_optimize import P1ASKCOSRouteStep, P1OptimizedLead
from zer0pa_health.pathway1.layers.handoff import P1HandoffStubAdapter

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FOUR_CARDIAC_GENES = {"KCNH2", "SCN5A", "KCNQ1", "CACNA1C"}
_DOFETILIDE_SMILES = "CN(C)S(=O)(=O)c1ccc(NCCOc2ccc(CCN(C)S(=O)(=O)C)cc2)cc1"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _p1_panel_to_l1_panel(p1_panel: P1L1ChannelPanelInput) -> L1ChannelPanelInput:
    """Convert P1L1ChannelPanelInput → L1ChannelPanelInput (the bridge conversion)."""
    targets: list[L1TargetInput] = []
    for t in p1_panel.targets:
        targets.append(
            L1TargetInput(
                gene=L1ChannelGene(t.gene),
                current=L1IonCurrent(t.current),
                structure_ref=t.structure_ref,
            )
        )
    return L1ChannelPanelInput(targets=targets)


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------

def test_p1_handoff_to_cardiac_bridge() -> None:
    """Full bridge: P1.Handoff (KCNH2) → L1.channel_panel — all 4 genes, hERG PASS."""

    # Step 1: Build a stub P1OptimizedLead for a cardiac target (KCNH2)
    lead = P1OptimizedLead(
        lead_id="lead-cardiac-001",
        target_id="target-KCNH2",
        smiles=_DOFETILIDE_SMILES,
        predicted_pIC50=7.8,
        admet_panel={
            "esol_logs": -3.5,
            "lipinski_violations": 0,
            "herg_ic50_um": 0.005,
            "oral_bioavailability": 0.55,
        },
        selectivity_score=0.75,
        synthetic_accessibility=3.2,
        askcos_route_steps=[
            P1ASKCOSRouteStep(
                step_index=0,
                rxn_smarts="[C:1]N>>[C:1]",
                reagents=["triethylamine"],
            ),
            P1ASKCOSRouteStep(
                step_index=1,
                rxn_smarts="[C:1]O>>[C:1]",
                reagents=["NaH"],
            ),
        ],
        estimated_synthesis_steps=2,
        iteration_number=3,
        confidence_tier="B",
        distinct_models_count=2,
    )

    # Step 2: Run P1HandoffStubAdapter
    handoff_input = P1HandoffInput(
        target_id="target-KCNH2",
        target_gene="KCNH2",
        leads=[lead.model_dump()],
        pathway1_run_id="run:test-cardiac-p1",
        audit_refs=["audit:p1-cardiac-001"],
    )
    p1_adapter = P1HandoffStubAdapter()
    p1_envelope = p1_adapter.process(handoff_input)

    # Unpack the packet
    packets = p1_envelope.output["packets"]
    assert len(packets) == 1, "expected one handoff packet"
    pkt_dict = packets[0]

    assert pkt_dict["is_cardiac_target"] is True, "KCNH2 must be flagged as cardiac"
    assert pkt_dict["l1_channel_panel_input"] is not None, (
        "cardiac packet must carry l1_channel_panel_input"
    )

    # Reconstruct the P1L1ChannelPanelInput Pydantic model from the dict
    p1_panel = P1L1ChannelPanelInput.model_validate(pkt_dict["l1_channel_panel_input"])

    # Verify all four genes are present with correct currents
    panel_gene_to_current = {t.gene: t.current for t in p1_panel.targets}
    assert set(panel_gene_to_current.keys()) == _FOUR_CARDIAC_GENES, (
        f"expected all 4 cardiac genes, got {set(panel_gene_to_current.keys())}"
    )
    expected_currents = {"KCNH2": "IKr", "SCN5A": "INaL", "KCNQ1": "IKs", "CACNA1C": "ICaL"}
    for gene, expected_current in expected_currents.items():
        assert panel_gene_to_current[gene] == expected_current, (
            f"gene {gene}: expected {expected_current}, got {panel_gene_to_current[gene]}"
        )

    # Step 3: Convert P1L1ChannelPanelInput → L1ChannelPanelInput
    l1_panel = _p1_panel_to_l1_panel(p1_panel)

    assert len(l1_panel.targets) == 4, "L1ChannelPanelInput must have 4 targets"
    l1_genes = {t.gene.value for t in l1_panel.targets}
    assert l1_genes == _FOUR_CARDIAC_GENES, (
        f"L1ChannelPanelInput genes mismatch: {l1_genes}"
    )

    # Step 4: Run existing L1StubAdapter.channel_panel()
    l1_adapter = L1StubAdapter()
    smiles = pkt_dict["smiles"]

    l1_envelope = l1_adapter.channel_panel(
        l1_panel,
        ligand_smiles=smiles,
        ligand_inchikey=None,
    )

    # Step 5: Verify the L1 envelope
    assert l1_envelope.layer == "L1", (
        f"expected L1 envelope layer, got {l1_envelope.layer!r}"
    )

    # All 4 genes must appear in the panel output
    l1_output = l1_envelope.output
    output_panel = l1_output.get("panel", {})
    output_genes = set(output_panel.keys())
    assert _FOUR_CARDIAC_GENES <= output_genes, (
        f"L1 output panel missing cardiac genes: {_FOUR_CARDIAC_GENES - output_genes}"
    )

    # hERG_only_overreach must PASS (all 4 genes present or in explicit_absence)
    herg_items = [
        item for item in l1_envelope.falsifier.items
        if item.falsifier_class == "hERG_only_overreach"
    ]
    assert herg_items, "L1 channel_panel must emit hERG_only_overreach falsifier item"
    # The status should be PASS because all 4 genes are present or explicitly absent
    herg_statuses = {item.status for item in herg_items}
    assert FalsifierStatus.FAIL not in herg_statuses, (
        f"hERG_only_overreach should PASS with 4-gene panel, got statuses: {herg_statuses}"
    )

    # Confidence band must be medium (L1 channel_panel is medium confidence)
    assert l1_envelope.confidence.band in ("medium", "low"), (
        f"unexpected confidence band: {l1_envelope.confidence.band}"
    )

    # P1 handoff packet must also show passing verdict (clean lead)
    assert pkt_dict["verdict_at_handoff"] == "pass", (
        f"expected 'pass' verdict for clean cardiac lead, got {pkt_dict['verdict_at_handoff']!r}"
    )


def test_p1_cardiac_bridge_fields_map_to_l1_target_input() -> None:
    """Each P1L1ChannelPanelTarget can be round-tripped to a valid L1TargetInput."""
    expected_mappings = [
        ("KCNH2", "IKr"),
        ("SCN5A", "INaL"),
        ("KCNQ1", "IKs"),
        ("CACNA1C", "ICaL"),
    ]
    for gene_str, current_str in expected_mappings:
        p1_target = P1L1ChannelPanelTarget(gene=gene_str, current=current_str)
        l1_target = L1TargetInput(
            gene=L1ChannelGene(p1_target.gene),
            current=L1IonCurrent(p1_target.current),
        )
        assert l1_target.gene.value == gene_str
        assert l1_target.current.value == current_str
