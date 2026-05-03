"""L5 toy adapter — second, deliberately-different stub for plug-replaceability testing.

Same public interface as L5StubAdapter.process() but different PK defaults:
  - Different default PK parameters when using the same L5PKPDInput
  - Uses a different toy channel panel (multiplies known IC50 by 1.5 for toy)
  - Same SBML packet shape
  - Same cardiac_bridge interface
  - Same multi-current balance score sign convention
  - Same falsifier classes emitted

RESEARCH USE ONLY — not for clinical deployment, diagnosis, or prescribing.
"""

from __future__ import annotations

import json
import math
import pathlib
from typing import Any

from zer0pa_biomolecular_explorer.boundary import RESEARCH_BOUNDARY
from zer0pa_biomolecular_explorer.contracts.l5 import (
    L5ExposureProfile,
    L5PKModelKind,
    L5PKPDInput,
    L5PKPDOutput,
)
from zer0pa_biomolecular_explorer.envelope import (
    BackEdge,
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
    detect_codec_as_mechanism,
    detect_herg_only_overreach,
    detect_nan_or_nonfinite,
    detect_sbml_failure,
)
from zer0pa_biomolecular_explorer.hashing import sha256_of_obj
from zer0pa_biomolecular_explorer.ids import audit_id, run_id as new_run_id
from zer0pa_biomolecular_explorer.layers.l5.cardiac_bridge import (
    CANONICAL_GENES,
    cardiac_bridge,
    get_explicit_absence,
)
from zer0pa_biomolecular_explorer.layers.l5.pk_models import one_compartment_pk
from zer0pa_biomolecular_explorer.layers.l5.sbml import build_minimal_sbml_packet, sbml_roundtrip_ok

_ADAPTER_NAME = "l5-toy"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "toy_one_compartment_scaled_channel"

# Fixtures directory (same as stub)
_FIXTURES_DIR = pathlib.Path(__file__).parents[4] / "fixtures" / "compounds"

# TOY DIFFERENTIATOR: IC50 multiplier for the toy channel panel
_TOY_IC50_MULTIPLIER = 1.5


def _load_channel_panel_from_fixtures() -> dict[str, dict]:
    """Load channel panel fixtures (same logic as stub)."""
    result: dict[str, dict] = {}
    if not _FIXTURES_DIR.exists():
        return result
    for p in _FIXTURES_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            ik = data.get("inchikey")
            panel = data.get("channel_panel_canned")
            if ik and panel:
                result[ik] = panel
        except Exception:
            continue
    return result


def _scale_panel_ic50(panel: dict, multiplier: float) -> dict:
    """Return a copy of a channel panel dict with all ic50_uM values scaled by multiplier.

    TOY DIFFERENTIATOR: toy adapter uses IC50 values × 1.5 to produce different
    fractional block values while keeping identical schema.
    """
    scaled: dict = {}
    for gene_key, entry in panel.items():
        if isinstance(entry, dict):
            new_entry = dict(entry)
            ic50 = new_entry.get("ic50_uM")
            if ic50 is not None:
                new_entry["ic50_uM"] = float(ic50) * multiplier
            scaled[gene_key] = new_entry
        else:
            scaled[gene_key] = entry
    return scaled


class L5ToyAdapter:
    """L5 toy adapter — 1.5× IC50 scaling in channel panel, identical schema.

    Produces a LayerEnvelope containing:
      - L5SBMLPacket (same stub minimal SBML as stub)
      - L5ExposureProfile (same analytic 1-compartment PK)
      - L5ChannelExposureBridge (IC50 values × 1.5 → different fractional blocks)

    Parameters
    ----------
    channel_panel_lookup:
        Optional dict mapping inchikey → channel_panel_canned blob.
        If None, loads from fixtures/compounds/*.json automatically.
    """

    def __init__(self, channel_panel_lookup: dict[str, dict] | None = None) -> None:
        if channel_panel_lookup is None:
            self._panel_lookup = _load_channel_panel_from_fixtures()
        else:
            self._panel_lookup = channel_panel_lookup

    def process(
        self,
        input: L5PKPDInput,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        rid = run_id or new_run_id()
        input_dict = input.model_dump()
        items: list[EnvelopeFalsifierItem] = []

        # (a) Build SBML packet (same as stub)
        sbml_params = {
            "cl": input.cl_l_per_h,
            "vd": input.vd_l,
            "ka": input.ka_per_h,
            "fu": input.fraction_unbound,
            "dose_mg": input.dose_mg,
        }
        sbml_packet = build_minimal_sbml_packet(
            model_kind=input.model_kind.value,
            parameters=sbml_params,
        )

        # (b) detect_sbml_failure
        sbml_item = detect_sbml_failure(sbml_packet, required_species=1, required_reactions=1)
        items.append(sbml_item)

        # (c) Exposure profile (same analytic 1-compartment; same parameters)
        n_points = 100
        t_hours = [24.0 * i / (n_points - 1) for i in range(n_points)]
        pk_result = one_compartment_pk(
            dose_mg=input.dose_mg,
            cl_l_per_h=input.cl_l_per_h,
            vd_l=input.vd_l,
            ka_per_h=input.ka_per_h,
            fraction_unbound=input.fraction_unbound,
            t_hours=t_hours,
        )

        # (d) detect_nan_or_nonfinite
        key_values = [
            pk_result["cmax_ng_per_ml"],
            pk_result["tmax_h"],
            pk_result["auc_0_inf_ng_h_per_ml"],
            pk_result["cmax_unbound_uM"],
            pk_result["half_life_h"],
        ]
        nan_item = detect_nan_or_nonfinite(key_values, context="l5_toy_pk_profile")
        items.append(nan_item)
        nan_arr_item = detect_nan_or_nonfinite(pk_result["c_total_ng_per_ml"], context="toy_c_total")
        items.append(nan_arr_item)

        exposure_profile = L5ExposureProfile(
            cmax_ng_per_ml=pk_result["cmax_ng_per_ml"],
            tmax_h=pk_result["tmax_h"],
            auc_0_inf_ng_h_per_ml=pk_result["auc_0_inf_ng_h_per_ml"],
            cmax_unbound_uM=pk_result["cmax_unbound_uM"],
            half_life_h=pk_result["half_life_h"],
        )

        # (e) Cardiac bridge with TOY IC50 scaling
        bridge_result = None
        canned_panel: dict | None = None
        explicit_absence: list[str] = []

        if input.inchikey and input.inchikey in self._panel_lookup:
            raw_panel = self._panel_lookup[input.inchikey]
            # TOY DIFFERENTIATOR: scale IC50 × 1.5 before computing fractional block
            canned_panel = _scale_panel_ic50(raw_panel, _TOY_IC50_MULTIPLIER)
            bridge_result = cardiac_bridge(
                cmax_unbound_uM=pk_result["cmax_unbound_uM"],
                channel_panel_canned=canned_panel,
            )
            explicit_absence = get_explicit_absence(bridge_result)
        else:
            explicit_absence = list(CANONICAL_GENES)

        # (f) detect_herg_only_overreach
        if canned_panel is not None:
            panel_genes_present = [
                g.split("_")[0]
                for g, entry in canned_panel.items()
                if isinstance(entry, dict) and entry.get("ic50_uM") is not None
            ]
            absence_gene_symbols = [g.split("_")[0] for g in explicit_absence]
        else:
            panel_genes_present = []
            absence_gene_symbols = ["SCN5A", "KCNQ1", "CACNA1C"]

        herg_item = detect_herg_only_overreach(
            panel_genes_present=panel_genes_present,
            explicit_absence=absence_gene_symbols,
        )
        items.append(herg_item)

        # (g) detect_codec_as_mechanism
        codec_item = detect_codec_as_mechanism(
            claim_text="exposure-channel bridge supports IKr block mechanism",
            basis_kinds=["pk_simulation", "channel_panel"],
        )
        items.append(codec_item)

        # Roundtrip check
        roundtrip_ok = sbml_roundtrip_ok(sbml_packet)

        # Build L5PKPDOutput
        output_obj = L5PKPDOutput(
            canonical_smiles=input.canonical_smiles,
            model_kind=input.model_kind,
            sbml_packet=sbml_packet,
            exposure_profile=exposure_profile,
            cardiac_bridge=bridge_result,
            sbml_roundtrip_ok=roundtrip_ok,
        )
        output_dict: dict[str, Any] = output_obj.model_dump()
        output_dict["basis"] = ["one_compartment_pk_analytic", "toy_channel_bridge_with_scaled_ic50"]

        # Confidence
        if bridge_result is not None:
            confidence_score = 0.55   # toy: slightly lower than stub's 0.60
            confidence_band = ConfidenceBand.MEDIUM
        else:
            confidence_score = 0.45
            confidence_band = ConfidenceBand.LOW

        # Back-edges to L1 for absent channel genes
        back_edges: list[BackEdge] = []
        if explicit_absence:
            absent_gene_symbols = list({g.split("_")[0] for g in explicit_absence})
            back_edges.append(
                BackEdge(
                    target_layer=LayerName.L1,
                    reason=(
                        "L5 toy cardiac bridge found missing IC50 data for channel genes: "
                        f"{sorted(absent_gene_symbols)}. Request multi-current panel expansion."
                    ),
                    proposed_constraint={
                        "request_panel_for_genes": sorted(absent_gene_symbols),
                    },
                    triggered_by_falsifier_id=herg_item.falsifier_id,
                )
            )

        any_fail = any(item.status == FalsifierStatus.FAIL for item in items)
        falsifier_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS

        return LayerEnvelope(
            run_id=rid,
            layer=LayerName.L5,
            tool_adapter=ToolAdapter(
                name=_ADAPTER_NAME,
                version=_ADAPTER_VERSION,
                backend=Backend.STUB,
                engine=_ENGINE,
            ),
            input_refs=[],
            output=output_dict,
            confidence=EnvelopeConfidence(
                score=confidence_score,
                band=confidence_band,
                basis=[
                    "one_compartment_pk_analytic",
                    "toy_channel_bridge_with_scaled_ic50",
                ],
            ),
            falsifier=EnvelopeFalsifier(
                status=falsifier_status,
                items=items,
            ),
            audit=EnvelopeAudit(
                audit_record_id=audit_id(),
                input_hash=sha256_of_obj(input_dict),
                output_hash=sha256_of_obj(output_dict),
                source_manifest_refs=[],
            ),
            back_edges=back_edges,
            research_boundary=RESEARCH_BOUNDARY,
        )
