"""L1 stub adapter — CPU-side, canned outputs, backend=stub.

No RDKit is imported here. SMILES validation uses the regex-based
detect_invalid_smiles() from falsifiers.detectors. Real ligand
standardization (RDKit, OpenFE) will be the Runpod GPU adapter.

Adapter discipline
------------------
- Every envelope sets tool_adapter.backend = Backend.STUB
- Every envelope includes a stub_laundering falsifier item (PASS normally;
  FAIL if caller signals mechanism_escalation=True)
- Every method accepting SMILES runs detect_invalid_smiles()
- Numeric inputs are validated with detect_nan_or_nonfinite()
- run_id propagates from caller or is generated fresh
- audit_record_id, input_hash, output_hash are always set

Channel-panel discipline
------------------------
- channel_panel() always covers KCNH2, SCN5A, KCNQ1, CACNA1C
- hERG_only_overreach is checked inside channel_panel() and added to items
- explicit_absence list is built from genes with null/no_canned_value entries
"""

from __future__ import annotations

import math
from typing import Any

from zer0pa_health.boundary import RESEARCH_BOUNDARY
from zer0pa_health.contracts.l1 import (
    L1ChannelGene,
    L1ChannelPanelHypothesis,
    L1ChannelPanelInput,
    L1DockingInput,
    L1DockingOutput,
    L1FEPInput,
    L1FEPOutput,
    L1MDInput,
    L1MDOutput,
    L1MoleculeInput,
    L1Pose,
    L1TargetInput,
)
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
    detect_herg_only_overreach,
    detect_invalid_smiles,
    detect_nan_or_nonfinite,
    detect_stub_laundering,
)
from zer0pa_health.hashing import sha256_of_obj
from zer0pa_health.ids import audit_id, envelope_id, run_id as new_run_id
from zer0pa_health.layers.l1.canned import (
    canned_binding,
    canned_channel_panel,
    canned_fep,
    canned_md,
    canned_pose,
)

_ADAPTER_NAME = "l1-stub"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "stub_canned"

# Four-gene canonical panel required by PRD / hERG-only-overreach falsifier
_CANONICAL_PANEL_GENES = ("KCNH2", "SCN5A", "KCNQ1", "CACNA1C")


def _build_envelope(
    *,
    run_id: str,
    input_dict: dict[str, Any],
    output_dict: dict[str, Any],
    confidence_score: float,
    confidence_band: ConfidenceBand,
    confidence_basis: list[str],
    falsifier_items: list[EnvelopeFalsifierItem],
    input_refs: list[str] | None = None,
) -> LayerEnvelope:
    """Assemble a fully-formed L1 LayerEnvelope."""
    any_fail = any(item.status == FalsifierStatus.FAIL for item in falsifier_items)
    falsifier_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS

    return LayerEnvelope(
        run_id=run_id,
        layer=LayerName.L1,
        tool_adapter=ToolAdapter(
            name=_ADAPTER_NAME,
            version=_ADAPTER_VERSION,
            backend=Backend.STUB,
            engine=_ENGINE,
        ),
        input_refs=input_refs or [],
        output=output_dict,
        confidence=EnvelopeConfidence(
            score=confidence_score,
            band=confidence_band,
            basis=confidence_basis,
        ),
        falsifier=EnvelopeFalsifier(
            status=falsifier_status,
            items=falsifier_items,
        ),
        audit=EnvelopeAudit(
            audit_record_id=audit_id(),
            input_hash=sha256_of_obj(input_dict),
            output_hash=sha256_of_obj(output_dict),
            source_manifest_refs=[],
        ),
        back_edges=[],
    )


class L1StubAdapter:
    """CPU-side stub adapter for L1 molecular simulation.

    Returns canned outputs shaped to the L1 contract. Does NOT import RDKit.
    Swap to real physics simulation by replacing this adapter with
    OpenFERunpodAdapter (see openfe_runpod_stub.py) — envelope contract is identical.

    All methods accept an optional run_id keyword. If None, a fresh run_id is
    generated via ids.run_id(). The same run_id is used in the envelope, audit,
    and any falsifier ledger entries.
    """

    # ------------------------------------------------------------------
    # ligand()
    # ------------------------------------------------------------------

    def ligand(
        self,
        inp: L1MoleculeInput,
        *,
        mechanism_escalation: bool = False,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        """Standardise ligand (stub: validate SMILES, return canned descriptors)."""
        rid = run_id or new_run_id()
        input_dict = inp.model_dump()

        items: list[EnvelopeFalsifierItem] = []

        # SMILES validation
        smiles_item = detect_invalid_smiles(inp.smiles)
        items.append(smiles_item)

        # Stub laundering
        stub_item = detect_stub_laundering(
            backend="stub",
            claim_kind="ligand_standardisation",
            mechanism_escalation=mechanism_escalation,
        )
        items.append(stub_item)

        output_dict: dict[str, Any] = {
            "smiles_input": inp.smiles,
            "standardised_smiles": inp.smiles,  # stub: identity transform
            "inchikey": inp.inchikey or "UNKNOWN_STUB",
            "name": inp.name or "unnamed",
            "basis": ["stub_canned_output"],
            "smiles_valid": smiles_item.status == FalsifierStatus.PASS,
        }

        return _build_envelope(
            run_id=rid,
            input_dict=input_dict,
            output_dict=output_dict,
            confidence_score=0.45,
            confidence_band=ConfidenceBand.LOW,
            confidence_basis=["stub_canned_output", "no_rdkit_standardisation"],
            falsifier_items=items,
        )

    # ------------------------------------------------------------------
    # target()
    # ------------------------------------------------------------------

    def target(
        self,
        inp: L1TargetInput,
        *,
        mechanism_escalation: bool = False,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        """Resolve target structure (stub: return placeholder structure metadata)."""
        rid = run_id or new_run_id()
        input_dict = inp.model_dump()

        items: list[EnvelopeFalsifierItem] = []

        stub_item = detect_stub_laundering(
            backend="stub",
            claim_kind="target_resolution",
            mechanism_escalation=mechanism_escalation,
        )
        items.append(stub_item)

        output_dict: dict[str, Any] = {
            "gene": inp.gene,
            "current": inp.current,
            "structure_ref": inp.structure_ref or "stub_structure",
            "resolution_angstrom": None,
            "structure_basis": "stub",
            "basis": ["stub_canned_output"],
        }

        return _build_envelope(
            run_id=rid,
            input_dict=input_dict,
            output_dict=output_dict,
            confidence_score=0.45,
            confidence_band=ConfidenceBand.LOW,
            confidence_basis=["stub_canned_output"],
            falsifier_items=items,
        )

    # ------------------------------------------------------------------
    # dock()
    # ------------------------------------------------------------------

    def dock(
        self,
        inp: L1DockingInput,
        *,
        mechanism_escalation: bool = False,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        """Docking (stub: return canned poses from fixtures or generated stub poses)."""
        rid = run_id or new_run_id()
        input_dict = inp.model_dump()

        items: list[EnvelopeFalsifierItem] = []

        # SMILES validation
        smiles_item = detect_invalid_smiles(inp.molecule.smiles)
        items.append(smiles_item)

        # Stub laundering
        stub_item = detect_stub_laundering(
            backend="stub",
            claim_kind="docking",
            mechanism_escalation=mechanism_escalation,
        )
        items.append(stub_item)

        inchikey = inp.molecule.inchikey or "UNKNOWN_STUB"
        gene = inp.target.gene if isinstance(inp.target.gene, str) else inp.target.gene.value
        raw_poses = canned_pose(inchikey, gene)

        # Clamp to n_poses requested (stub: always returns 3, limit by request)
        n = min(inp.n_poses, len(raw_poses))
        poses = [
            L1Pose(
                pose_index=p["pose_index"],
                confidence=p["confidence"],
                estimated_binding_kcal_mol=p["estimated_binding_kcal_mol"],
                structure_basis="stub",
            )
            for p in raw_poses[:n]
        ]

        docking_out = L1DockingOutput(
            molecule_inchikey=inchikey,
            target_gene=inp.target.gene,
            target_current=inp.target.current,
            poses=poses,
            structure_confidence=0.45,
            binding_confidence=0.45,
        )
        output_dict = docking_out.model_dump()
        output_dict["basis"] = ["stub_canned_output"]

        return _build_envelope(
            run_id=rid,
            input_dict=input_dict,
            output_dict=output_dict,
            confidence_score=0.45,
            confidence_band=ConfidenceBand.MEDIUM,
            confidence_basis=["stub_canned_output"],
            falsifier_items=items,
        )

    # ------------------------------------------------------------------
    # md()
    # ------------------------------------------------------------------

    def md(
        self,
        inp: L1MDInput,
        *,
        mechanism_escalation: bool = False,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        """Molecular dynamics (stub: return canned RMSD and convergence values)."""
        rid = run_id or new_run_id()
        input_dict = inp.model_dump()

        items: list[EnvelopeFalsifierItem] = []

        # SMILES validation
        smiles_item = detect_invalid_smiles(inp.molecule.smiles)
        items.append(smiles_item)

        # Numeric validation on sim_ns
        nan_item = detect_nan_or_nonfinite([inp.sim_ns], context="sim_ns")
        items.append(nan_item)

        stub_item = detect_stub_laundering(
            backend="stub",
            claim_kind="md_simulation",
            mechanism_escalation=mechanism_escalation,
        )
        items.append(stub_item)

        inchikey = inp.molecule.inchikey or "UNKNOWN_STUB"
        gene = inp.target.gene if isinstance(inp.target.gene, str) else inp.target.gene.value
        md_data = canned_md(inchikey, gene)

        md_out = L1MDOutput(
            molecule_inchikey=inchikey,
            target_gene=inp.target.gene,
            rmsd_nm=md_data["rmsd_nm"],
            convergence_metric=md_data["convergence_metric"],
            n_frames=md_data["n_frames"],
        )
        output_dict = md_out.model_dump()
        output_dict["basis"] = ["stub_canned_output"]

        return _build_envelope(
            run_id=rid,
            input_dict=input_dict,
            output_dict=output_dict,
            confidence_score=0.45,
            confidence_band=ConfidenceBand.MEDIUM,
            confidence_basis=["stub_canned_output"],
            falsifier_items=items,
        )

    # ------------------------------------------------------------------
    # fep()
    # ------------------------------------------------------------------

    def fep(
        self,
        inp: L1FEPInput,
        *,
        mechanism_escalation: bool = False,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        """Free energy perturbation (stub: return canned ΔΔG values)."""
        rid = run_id or new_run_id()
        input_dict = inp.model_dump()

        items: list[EnvelopeFalsifierItem] = []

        # SMILES validation for both ligands
        smiles_a = detect_invalid_smiles(inp.ligand_a.smiles)
        smiles_b = detect_invalid_smiles(inp.ligand_b.smiles)
        items.extend([smiles_a, smiles_b])

        stub_item = detect_stub_laundering(
            backend="stub",
            claim_kind="fep_simulation",
            mechanism_escalation=mechanism_escalation,
        )
        items.append(stub_item)

        inchikey_a = inp.ligand_a.inchikey or "UNKNOWN_A"
        inchikey_b = inp.ligand_b.inchikey or "UNKNOWN_B"
        gene = inp.target.gene if isinstance(inp.target.gene, str) else inp.target.gene.value
        fep_data = canned_fep(inchikey_a, inchikey_b, gene)

        fep_out = L1FEPOutput(
            ddg_kcal_mol=fep_data["ddg_kcal_mol"],
            ddg_uncertainty_kcal_mol=fep_data["uncertainty_kcal_mol"],
            convergence_ok=fep_data["convergence_ok"],
            method=inp.method,
        )
        output_dict = fep_out.model_dump()
        output_dict["basis"] = ["stub_canned_output"]

        return _build_envelope(
            run_id=rid,
            input_dict=input_dict,
            output_dict=output_dict,
            confidence_score=0.45,
            confidence_band=ConfidenceBand.MEDIUM,
            confidence_basis=["stub_canned_output"],
            falsifier_items=items,
        )

    # ------------------------------------------------------------------
    # channel_panel()
    # ------------------------------------------------------------------

    def channel_panel(
        self,
        inp: L1ChannelPanelInput,
        ligand_smiles: str,
        *,
        mechanism_escalation: bool = False,
        run_id: str | None = None,
        ligand_inchikey: str | None = None,
    ) -> LayerEnvelope:
        """Multi-current channel panel (stub: covers KCNH2, SCN5A, KCNQ1, CACNA1C).

        Requirement: ALL FOUR canonical genes must be present or listed in
        explicit_absence. The hERG_only_overreach falsifier is run inside this
        method and its result is included in the envelope items.

        Uses canned compound fixtures when inchikey matches a known fixture,
        otherwise generates deterministic stub values.
        """
        rid = run_id or new_run_id()
        input_dict: dict[str, Any] = {
            "targets": inp.model_dump()["targets"],
            "ligand_smiles": ligand_smiles,
            "ligand_inchikey": ligand_inchikey,
        }

        items: list[EnvelopeFalsifierItem] = []

        # SMILES validation
        smiles_item = detect_invalid_smiles(ligand_smiles)
        items.append(smiles_item)

        # Stub laundering
        stub_item = detect_stub_laundering(
            backend="stub",
            claim_kind="channel_panel",
            mechanism_escalation=mechanism_escalation,
        )
        items.append(stub_item)

        # Build the panel covering all four required genes
        panel: dict[str, dict[str, float | None]] = {}
        explicit_absence: list[str] = []

        if ligand_inchikey:
            try:
                canned = canned_channel_panel(ligand_inchikey)
                # canned is gene -> dict with ic50_uM, block_fraction, confidence, method, etc.
                # We preserve the full set of fields the downstream packet assembler needs,
                # so that the L1 envelope is the single source of truth for the channel panel.
                #
                # `explicit_absence` membership is faithful to the FIXTURE'S flag — we do
                # NOT derive it from numeric presence. A gene with `block_fraction=0.0`
                # AND `explicit_absence` set (e.g., verapamil's SCN5A) is genuinely absent
                # of meaningful INaL block; the flag is the source of truth.
                for gene in _CANONICAL_PANEL_GENES:
                    if gene in canned:
                        entry = canned[gene]
                        absence_flag = entry.get("explicit_absence")
                        panel[gene] = {
                            "ic50_uM": entry.get("ic50_uM"),
                            "block_fraction_at_cmax_unbound": entry.get(
                                "block_fraction_at_cmax_unbound"
                            ),
                            "method": entry.get("method", "stub"),
                            "confidence": entry.get("confidence", 0.0),
                            "source_refs": list(entry.get("source_refs", [])),
                            "explicit_absence": absence_flag,
                        }
                        if absence_flag:
                            explicit_absence.append(gene)
                    else:
                        panel[gene] = _empty_panel_entry()
                        explicit_absence.append(gene)
            except KeyError:
                # No fixture for this inchikey — generate deterministic stubs
                _fill_stub_panel(ligand_inchikey or "UNKNOWN", panel, explicit_absence)
        else:
            _fill_stub_panel("UNKNOWN", panel, explicit_absence)

        # Always ensure all four genes present
        for gene in _CANONICAL_PANEL_GENES:
            if gene not in panel:
                panel[gene] = _empty_panel_entry()
                if gene not in explicit_absence:
                    explicit_absence.append(gene)

        # hERG-only-overreach check
        panel_genes_present = [g for g in panel if panel[g].get("ic50_uM") is not None]
        herg_item = detect_herg_only_overreach(
            panel_genes_present=panel_genes_present,
            explicit_absence=explicit_absence,
        )
        items.append(herg_item)

        # Build hypothesis output
        hypothesis = L1ChannelPanelHypothesis(
            molecule_inchikey=ligand_inchikey or "UNKNOWN_STUB",
            panel=panel,
            multi_current_balance_score=_compute_balance_score(panel),
        )
        output_dict = hypothesis.model_dump()
        output_dict["explicit_absence"] = explicit_absence
        output_dict["basis"] = ["stub_canned_output"]

        return _build_envelope(
            run_id=rid,
            input_dict=input_dict,
            output_dict=output_dict,
            confidence_score=0.50,
            confidence_band=ConfidenceBand.MEDIUM,
            confidence_basis=["stub_canned_output", "multi_current_panel"],
            falsifier_items=items,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _empty_panel_entry() -> dict[str, Any]:
    """Empty panel entry shape — preserves the full schema downstream assemblers expect."""
    return {
        "ic50_uM": None,
        "block_fraction_at_cmax_unbound": None,
        "method": "stub",
        "confidence": 0.0,
        "source_refs": [],
        "explicit_absence": "no_canned_value_pending_lookup",
    }


def _fill_stub_panel(
    seed: str,
    panel: dict[str, dict[str, Any]],
    explicit_absence: list[str],
) -> None:
    """Fill panel with deterministic stub values (no fixture available)."""
    from zer0pa_health.layers.l1.canned import _seed_float  # noqa: PLC0415
    for gene in _CANONICAL_PANEL_GENES:
        if gene not in panel:
            conf = _seed_float(seed, gene, "panel_conf", 0.40, 0.60)
            entry = _empty_panel_entry()
            entry["confidence"] = round(conf, 3)
            panel[gene] = entry
            explicit_absence.append(gene)


def _compute_balance_score(panel: dict[str, dict[str, float | None]]) -> float | None:
    """Rough multi-current balance score from stub panel (research-only indicator).

    HIGHER = more outward-current block relative to inward-current block
             = greater APD-prolongation tendency in research-only multi-current
             models. NOT a clinical or safety claim in any direction.
    LOWER  = more inward-current block relative to outward
             = APD-prolongation tendency reduced in the same research models.

    For stub data with only confidence available, returns 0.0.
    See `layers/l5/cardiac_bridge.py` for the canonical formula.
    """
    # With stub data, use ic50_uM presence as proxy
    # Lower IC50 = more block
    try:
        herg_ic50 = panel.get("KCNH2", {}).get("ic50_uM")
        ical_ic50 = panel.get("CACNA1C", {}).get("ic50_uM")
        if herg_ic50 is None and ical_ic50 is None:
            return 0.0
        herg_block = (1.0 / herg_ic50 if herg_ic50 else 0.0)
        ical_block = (1.0 / ical_ic50 if ical_ic50 else 0.0)
        # Positive if ICaL block counterbalances IKr block (verapamil-like)
        raw = (ical_block - herg_block) / max(ical_block + herg_block, 1e-9)
        # Clamp to [-1, 1]
        return float(max(-1.0, min(1.0, raw)))
    except (TypeError, ZeroDivisionError, ValueError):
        return 0.0
