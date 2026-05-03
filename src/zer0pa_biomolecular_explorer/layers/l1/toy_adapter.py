"""L1 toy adapter — second, deliberately-different stub for plug-replaceability testing.

Identical public interface as L1StubAdapter; different canned values:
  - Docking scores in the -6 to -4 kcal/mol band (vs -8 to -5 in the stub)
  - Pose count = 5 (vs 3 in the stub), clamped by n_poses as usual
  - Channel panel IC50 multiplier = 2x (values are 2x the stub's seed)
  - engine = "toy_canned_v0", name = "l1-toy"

Schema is IDENTICAL to L1StubAdapter output (same keys, same value types).
All falsifier classes emitted are identical to L1StubAdapter.
Same research_boundary. Same contract_version enforcement.

RESEARCH USE ONLY — not for clinical deployment, diagnosis, or prescribing.
"""

from __future__ import annotations

import hashlib
from typing import Any

from zer0pa_biomolecular_explorer.boundary import RESEARCH_BOUNDARY
from zer0pa_biomolecular_explorer.contracts.l1 import (
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
    detect_herg_only_overreach,
    detect_invalid_smiles,
    detect_nan_or_nonfinite,
    detect_stub_laundering,
)
from zer0pa_biomolecular_explorer.hashing import sha256_of_obj
from zer0pa_biomolecular_explorer.ids import audit_id, run_id as new_run_id

_ADAPTER_NAME = "l1-toy"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "toy_canned_v0"

# Four-gene canonical panel (same as StubAdapter)
_CANONICAL_PANEL_GENES = ("KCNH2", "SCN5A", "KCNQ1", "CACNA1C")

# Toy adapter differentiators:
#   - Docking scores: -6 to -4 kcal/mol (stub uses -8 to -5)
#   - Pose count: 5 (stub emits 3)
#   - IC50 multiplier: 2x (stub baseline)
#   - MD RMSD range: 0.20–0.50 nm (stub uses 0.10–0.40)
#   - FEP ddG range: -2 to 2 (stub: -3 to 3)

_TOY_DOCK_LO = -6.0   # kcal/mol
_TOY_DOCK_HI = -4.0   # kcal/mol
_TOY_N_POSES = 5
_TOY_IC50_MULTIPLIER = 2.0
_TOY_MD_RMSD_LO = 0.20
_TOY_MD_RMSD_HI = 0.50
_TOY_FEP_DDG_LO = -2.0
_TOY_FEP_DDG_HI = 2.0


def _seed_float(seed: str, salt: str, lo: float, hi: float) -> float:
    """Deterministic pseudo-random float in [lo, hi]."""
    h = hashlib.sha256(f"{seed}|{salt}".encode()).hexdigest()
    frac = int(h[:8], 16) / 0xFFFFFFFF
    return lo + frac * (hi - lo)


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
        ),
        back_edges=[],
    )


class L1ToyAdapter:
    """L1 toy adapter — deliberately different canned values, identical schema.

    Public methods: ligand, target, dock, md, fep, channel_panel
    (same signatures as L1StubAdapter).

    Differences from L1StubAdapter:
      - engine = "toy_canned_v0", name = "l1-toy"
      - Docking scores in -6 to -4 kcal/mol band
      - Poses = 5 instead of 3
      - IC50 values 2x the stub seed
      - MD RMSD range 0.20-0.50 nm
      - FEP ddG range -2 to 2 kcal/mol

    Schema (output keys and types) is identical to L1StubAdapter.
    Falsifier classes emitted are identical.
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
        rid = run_id or new_run_id()
        input_dict = inp.model_dump()

        items: list[EnvelopeFalsifierItem] = []

        smiles_item = detect_invalid_smiles(inp.smiles)
        items.append(smiles_item)

        stub_item = detect_stub_laundering(
            backend="stub",
            claim_kind="ligand_standardisation",
            mechanism_escalation=mechanism_escalation,
        )
        items.append(stub_item)

        # Same output keys as stub; toy uses "toy_canned_output" in basis
        output_dict: dict[str, Any] = {
            "smiles_input": inp.smiles,
            "standardised_smiles": inp.smiles,
            "inchikey": inp.inchikey or "UNKNOWN_TOY",
            "name": inp.name or "unnamed",
            "basis": ["toy_canned_output"],
            "smiles_valid": smiles_item.status == FalsifierStatus.PASS,
        }

        return _build_envelope(
            run_id=rid,
            input_dict=input_dict,
            output_dict=output_dict,
            confidence_score=0.42,
            confidence_band=ConfidenceBand.LOW,
            confidence_basis=["toy_canned_output", "no_rdkit_standardisation"],
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
            "structure_ref": inp.structure_ref or "toy_structure",
            "resolution_angstrom": None,
            "structure_basis": "stub",
            "basis": ["toy_canned_output"],
        }

        return _build_envelope(
            run_id=rid,
            input_dict=input_dict,
            output_dict=output_dict,
            confidence_score=0.42,
            confidence_band=ConfidenceBand.LOW,
            confidence_basis=["toy_canned_output"],
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
        rid = run_id or new_run_id()
        input_dict = inp.model_dump()

        items: list[EnvelopeFalsifierItem] = []

        smiles_item = detect_invalid_smiles(inp.molecule.smiles)
        items.append(smiles_item)

        stub_item = detect_stub_laundering(
            backend="stub",
            claim_kind="docking",
            mechanism_escalation=mechanism_escalation,
        )
        items.append(stub_item)

        inchikey = inp.molecule.inchikey or "UNKNOWN_TOY"
        gene = inp.target.gene if isinstance(inp.target.gene, str) else inp.target.gene.value

        # Generate 5 toy poses (different values than stub's 3)
        toy_poses_raw = []
        for i in range(_TOY_N_POSES):
            conf = _seed_float(inchikey, f"{gene}|toy_pose_conf_{i}", 0.35, 0.65)
            score = _seed_float(inchikey, f"{gene}|toy_pose_score_{i}", _TOY_DOCK_LO, _TOY_DOCK_HI)
            toy_poses_raw.append(
                {
                    "pose_index": i,
                    "confidence": round(conf, 3),
                    "estimated_binding_kcal_mol": round(score, 3),
                    "structure_basis": "stub",
                }
            )

        n = min(inp.n_poses, len(toy_poses_raw))
        poses = [
            L1Pose(
                pose_index=p["pose_index"],
                confidence=p["confidence"],
                estimated_binding_kcal_mol=p["estimated_binding_kcal_mol"],
                structure_basis="stub",
            )
            for p in toy_poses_raw[:n]
        ]

        docking_out = L1DockingOutput(
            molecule_inchikey=inchikey,
            target_gene=inp.target.gene,
            target_current=inp.target.current,
            poses=poses,
            structure_confidence=0.42,
            binding_confidence=0.42,
        )
        output_dict = docking_out.model_dump()
        output_dict["basis"] = ["toy_canned_output"]

        return _build_envelope(
            run_id=rid,
            input_dict=input_dict,
            output_dict=output_dict,
            confidence_score=0.42,
            confidence_band=ConfidenceBand.MEDIUM,
            confidence_basis=["toy_canned_output"],
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
        rid = run_id or new_run_id()
        input_dict = inp.model_dump()

        items: list[EnvelopeFalsifierItem] = []

        smiles_item = detect_invalid_smiles(inp.molecule.smiles)
        items.append(smiles_item)

        nan_item = detect_nan_or_nonfinite([inp.sim_ns], context="sim_ns")
        items.append(nan_item)

        stub_item = detect_stub_laundering(
            backend="stub",
            claim_kind="md_simulation",
            mechanism_escalation=mechanism_escalation,
        )
        items.append(stub_item)

        inchikey = inp.molecule.inchikey or "UNKNOWN_TOY"
        gene = inp.target.gene if isinstance(inp.target.gene, str) else inp.target.gene.value

        rmsd = _seed_float(inchikey, f"{gene}|toy_md_rmsd", _TOY_MD_RMSD_LO, _TOY_MD_RMSD_HI)
        conv = _seed_float(inchikey, f"{gene}|toy_md_conv", 0.35, 0.65)

        md_out = L1MDOutput(
            molecule_inchikey=inchikey,
            target_gene=inp.target.gene,
            rmsd_nm=round(rmsd, 4),
            convergence_metric=round(conv, 4),
            n_frames=50,  # different from stub (100)
        )
        output_dict = md_out.model_dump()
        output_dict["basis"] = ["toy_canned_output"]

        return _build_envelope(
            run_id=rid,
            input_dict=input_dict,
            output_dict=output_dict,
            confidence_score=0.42,
            confidence_band=ConfidenceBand.MEDIUM,
            confidence_basis=["toy_canned_output"],
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
        rid = run_id or new_run_id()
        input_dict = inp.model_dump()

        items: list[EnvelopeFalsifierItem] = []

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

        ddg = _seed_float(
            inchikey_a + inchikey_b, f"{gene}|toy_fep_ddg", _TOY_FEP_DDG_LO, _TOY_FEP_DDG_HI
        )
        unc = _seed_float(
            inchikey_a + inchikey_b, f"{gene}|toy_fep_unc", 0.2, 1.2
        )

        fep_out = L1FEPOutput(
            ddg_kcal_mol=round(ddg, 3),
            ddg_uncertainty_kcal_mol=round(unc, 3),
            convergence_ok=True,
            method=inp.method,
        )
        output_dict = fep_out.model_dump()
        output_dict["basis"] = ["toy_canned_output"]

        return _build_envelope(
            run_id=rid,
            input_dict=input_dict,
            output_dict=output_dict,
            confidence_score=0.42,
            confidence_band=ConfidenceBand.MEDIUM,
            confidence_basis=["toy_canned_output"],
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
        """Multi-current channel panel — toy values; 2x IC50 multiplier vs stub."""
        rid = run_id or new_run_id()
        input_dict: dict[str, Any] = {
            "targets": inp.model_dump()["targets"],
            "ligand_smiles": ligand_smiles,
            "ligand_inchikey": ligand_inchikey,
        }

        items: list[EnvelopeFalsifierItem] = []

        smiles_item = detect_invalid_smiles(ligand_smiles)
        items.append(smiles_item)

        stub_item = detect_stub_laundering(
            backend="stub",
            claim_kind="channel_panel",
            mechanism_escalation=mechanism_escalation,
        )
        items.append(stub_item)

        panel: dict[str, dict[str, float | None]] = {}
        explicit_absence: list[str] = []
        seed = ligand_inchikey or "UNKNOWN_TOY"

        for gene in _CANONICAL_PANEL_GENES:
            # Toy: IC50 is 2x the seed-based value (different from stub which has None)
            # Use a deterministic float in [1.0, 20.0] (2x stub's [0.5, 10.0] effective range)
            ic50 = round(
                _seed_float(seed, f"{gene}|toy_ic50", 1.0, 20.0), 3
            )
            conf = round(
                _seed_float(seed, f"{gene}|toy_panel_conf", 0.35, 0.55), 3
            )
            panel[gene] = {"ic50_uM": ic50, "confidence": conf}

        # hERG-only-overreach check
        panel_genes_present = [g for g in panel if panel[g].get("ic50_uM") is not None]
        herg_item = detect_herg_only_overreach(
            panel_genes_present=panel_genes_present,
            explicit_absence=explicit_absence,
        )
        items.append(herg_item)

        hypothesis = L1ChannelPanelHypothesis(
            molecule_inchikey=ligand_inchikey or "UNKNOWN_TOY",
            panel=panel,
            multi_current_balance_score=_compute_toy_balance_score(panel),
        )
        output_dict = hypothesis.model_dump()
        output_dict["explicit_absence"] = explicit_absence
        output_dict["basis"] = ["toy_canned_output"]

        return _build_envelope(
            run_id=rid,
            input_dict=input_dict,
            output_dict=output_dict,
            confidence_score=0.48,
            confidence_band=ConfidenceBand.MEDIUM,
            confidence_basis=["toy_canned_output", "multi_current_panel"],
            falsifier_items=items,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_toy_balance_score(panel: dict[str, dict[str, float | None]]) -> float | None:
    """Toy multi-current balance score (same formula as stub but different input values)."""
    try:
        herg_ic50 = panel.get("KCNH2", {}).get("ic50_uM")
        ical_ic50 = panel.get("CACNA1C", {}).get("ic50_uM")
        if herg_ic50 is None and ical_ic50 is None:
            return 0.0
        herg_block = (1.0 / herg_ic50 if herg_ic50 else 0.0)
        ical_block = (1.0 / ical_ic50 if ical_ic50 else 0.0)
        raw = (ical_block - herg_block) / max(ical_block + herg_block, 1e-9)
        return float(max(-1.0, min(1.0, raw)))
    except (TypeError, ZeroDivisionError, ValueError):
        return 0.0
