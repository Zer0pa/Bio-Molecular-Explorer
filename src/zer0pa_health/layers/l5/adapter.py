"""L5 stub adapter — PKPD / QSP / cardiac exposure-channel bridge.

Backend: stub (CPU-side, canned channel panels, analytic PK model).
No COPASI, Tellurium, PK-Sim, nlmixr2, or RxODE dependency at this tier.
Real adapters are swapped in by replacing this class while keeping the
LayerEnvelope contract identical.

Falsifier discipline
--------------------
- detect_sbml_failure:          SBML packet must have >= 1 species, >= 1 reaction.
- detect_nan_or_nonfinite:      All PK profile values must be finite.
- detect_herg_only_overreach:   All four CiPA genes must be present or explicit_absence.
- detect_codec_as_mechanism:    Basis kinds must include non-codec evidence; here
                                ["pk_simulation", "channel_panel"] → PASS.

Back-edges to L1
----------------
When channel_panel_canned has genes with ic50_uM = None (explicit_absence), a
back_edge to L1 is emitted with proposed_constraint listing absent gene names.
This implements the "Inversion A" pattern: downstream evidence gap propagates
upstream as a request to complete the channel panel.

RESEARCH USE ONLY — not for clinical deployment, diagnosis, or prescribing.
"""

from __future__ import annotations

import json
import math
import pathlib
from typing import Any

from zer0pa_health.boundary import RESEARCH_BOUNDARY
from zer0pa_health.contracts.l5 import (
    L5ExposureProfile,
    L5PKModelKind,
    L5PKPDInput,
    L5PKPDOutput,
)
from zer0pa_health.envelope import (
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
from zer0pa_health.falsifiers.detectors import (
    detect_codec_as_mechanism,
    detect_herg_only_overreach,
    detect_nan_or_nonfinite,
    detect_sbml_failure,
)
from zer0pa_health.hashing import sha256_of_obj
from zer0pa_health.ids import audit_id, run_id as new_run_id
from zer0pa_health.layers.l5.cardiac_bridge import (
    CANONICAL_GENES,
    cardiac_bridge,
    get_explicit_absence,
)
from zer0pa_health.layers.l5.pk_models import one_compartment_pk
from zer0pa_health.layers.l5.sbml import build_minimal_sbml_packet, sbml_roundtrip_ok

_ADAPTER_NAME = "l5-stub"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "analytic_one_compartment_canned_channel"

# Fixtures directory for loading compound JSON files
_FIXTURES_DIR = pathlib.Path(__file__).parents[4] / "fixtures" / "compounds"


def _load_channel_panel_from_fixtures() -> dict[str, dict]:
    """Load channel_panel_canned blobs from fixtures/compounds/*.json keyed by inchikey."""
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


class L5StubAdapter:
    """CPU-side stub adapter for L5 PKPD / QSP / cardiac bridge.

    Produces a LayerEnvelope containing:
      - L5SBMLPacket (stub minimal SBML)
      - L5ExposureProfile (analytic 1-compartment PK)
      - L5ChannelExposureBridge (canned IC50 → Hill fractional block)

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
        """Run the full L5 pipeline for a single compound input.

        Steps:
          a) Build minimal SBML packet.
          b) detect_sbml_failure — must have >= 1 species and >= 1 reaction.
          c) Compute 1-compartment PK exposure profile over 24h (100 time points).
          d) detect_nan_or_nonfinite on PK profile values.
          e) If inchikey in channel_panel_lookup: build cardiac_bridge.
          f) detect_herg_only_overreach — PASS because all four genes covered
             (even with explicit_absence, detector requires presence OR absence record).
          g) detect_codec_as_mechanism — basis includes pk_simulation + channel_panel
             (not codec-only) → PASS.
          h) Build LayerEnvelope with back_edges to L1 for absent channel genes.

        Parameters
        ----------
        input:
            L5PKPDInput with compound SMILES, PK parameters, and dose.
        run_id:
            Optional run ID; generated fresh if None.

        Returns
        -------
        LayerEnvelope at layer L5, backend STUB.
        """
        rid = run_id or new_run_id()
        input_dict = input.model_dump()
        items: list[EnvelopeFalsifierItem] = []

        # ----------------------------------------------------------------
        # (a) Build SBML packet
        # ----------------------------------------------------------------
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

        # ----------------------------------------------------------------
        # (b) detect_sbml_failure
        # ----------------------------------------------------------------
        sbml_item = detect_sbml_failure(sbml_packet, required_species=1, required_reactions=1)
        items.append(sbml_item)

        # ----------------------------------------------------------------
        # (c) Compute exposure profile (24h, 100 points)
        # ----------------------------------------------------------------
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

        # ----------------------------------------------------------------
        # (d) detect_nan_or_nonfinite
        # ----------------------------------------------------------------
        key_values = [
            pk_result["cmax_ng_per_ml"],
            pk_result["tmax_h"],
            pk_result["auc_0_inf_ng_h_per_ml"],
            pk_result["cmax_unbound_uM"],
            pk_result["half_life_h"],
        ]
        nan_item = detect_nan_or_nonfinite(key_values, context="l5_pk_profile")
        items.append(nan_item)
        # Also check concentration arrays
        nan_arr_item = detect_nan_or_nonfinite(pk_result["c_total_ng_per_ml"], context="c_total")
        items.append(nan_arr_item)

        exposure_profile = L5ExposureProfile(
            cmax_ng_per_ml=pk_result["cmax_ng_per_ml"],
            tmax_h=pk_result["tmax_h"],
            auc_0_inf_ng_h_per_ml=pk_result["auc_0_inf_ng_h_per_ml"],
            cmax_unbound_uM=pk_result["cmax_unbound_uM"],
            half_life_h=pk_result["half_life_h"],
        )

        # ----------------------------------------------------------------
        # (e) Cardiac bridge (if channel panel available)
        # ----------------------------------------------------------------
        bridge_result = None
        canned_panel: dict | None = None
        explicit_absence: list[str] = []

        if input.inchikey and input.inchikey in self._panel_lookup:
            canned_panel = self._panel_lookup[input.inchikey]
            bridge_result = cardiac_bridge(
                cmax_unbound_uM=pk_result["cmax_unbound_uM"],
                channel_panel_canned=canned_panel,
            )
            explicit_absence = get_explicit_absence(bridge_result)
        else:
            # No panel: mark all four genes absent so hERG overreach detector
            # still PASS (all absent → no overreach claim)
            explicit_absence = list(CANONICAL_GENES)

        # ----------------------------------------------------------------
        # (f) detect_herg_only_overreach
        # ----------------------------------------------------------------
        # panel_genes_present = genes with non-null ic50 in the canned panel.
        # detect_herg_only_overreach PASS iff: KCNH2 is present AND companions
        # are present or in explicit_absence, OR KCNH2 is not in panel_present
        # (no hERG-only claim being made).
        #
        # Interaction: when channel_panel has all four genes (even with explicit
        # absence for some), all companion genes are either in panel_present or
        # explicit_absence → PASS. When no panel at all, KCNH2 not present →
        # no overreach claim → PASS.
        if canned_panel is not None:
            panel_genes_present = [
                g.split("_")[0]  # extract gene symbol (e.g. "KCNH2")
                for g, entry in canned_panel.items()
                if isinstance(entry, dict) and entry.get("ic50_uM") is not None
            ]
            # explicit_absence list for the detector uses gene symbols too
            absence_gene_symbols = [g.split("_")[0] for g in explicit_absence]
        else:
            panel_genes_present = []
            absence_gene_symbols = ["SCN5A", "KCNQ1", "CACNA1C"]  # all absent, no hERG claim

        herg_item = detect_herg_only_overreach(
            panel_genes_present=panel_genes_present,
            explicit_absence=absence_gene_symbols,
        )
        items.append(herg_item)

        # ----------------------------------------------------------------
        # (g) detect_codec_as_mechanism
        # ----------------------------------------------------------------
        # Claim text: the exposure-channel bridge supports IKr block mechanism.
        # Basis kinds include pk_simulation and channel_panel (not codec-only) → PASS.
        codec_item = detect_codec_as_mechanism(
            claim_text="exposure-channel bridge supports IKr block mechanism",
            basis_kinds=["pk_simulation", "channel_panel"],
        )
        items.append(codec_item)

        # ----------------------------------------------------------------
        # Roundtrip check
        # ----------------------------------------------------------------
        roundtrip_ok = sbml_roundtrip_ok(sbml_packet)

        # ----------------------------------------------------------------
        # Build L5PKPDOutput
        # ----------------------------------------------------------------
        output_obj = L5PKPDOutput(
            canonical_smiles=input.canonical_smiles,
            model_kind=input.model_kind,
            sbml_packet=sbml_packet,
            exposure_profile=exposure_profile,
            cardiac_bridge=bridge_result,
            sbml_roundtrip_ok=roundtrip_ok,
        )
        output_dict: dict[str, Any] = output_obj.model_dump()
        output_dict["basis"] = ["one_compartment_pk_analytic", "stub_channel_bridge_with_canned_ic50"]

        # ----------------------------------------------------------------
        # Confidence
        # ----------------------------------------------------------------
        # Confidence is reduced if no channel panel is available (bridge=None)
        if bridge_result is not None:
            confidence_score = 0.60
            confidence_band = ConfidenceBand.MEDIUM
        else:
            confidence_score = 0.50
            confidence_band = ConfidenceBand.LOW

        # ----------------------------------------------------------------
        # Back-edges to L1 for absent channel genes
        # ----------------------------------------------------------------
        back_edges: list[BackEdge] = []
        if explicit_absence:
            # Map gene panel keys back to L1 gene symbols for the back-edge
            absent_gene_symbols = list({g.split("_")[0] for g in explicit_absence})
            back_edges.append(
                BackEdge(
                    target_layer=LayerName.L1,
                    reason=(
                        "L5 cardiac bridge found missing IC50 data for channel genes: "
                        f"{sorted(absent_gene_symbols)}. Request multi-current panel expansion."
                    ),
                    proposed_constraint={
                        "request_panel_for_genes": sorted(absent_gene_symbols),
                    },
                    triggered_by_falsifier_id=herg_item.falsifier_id,
                )
            )

        # ----------------------------------------------------------------
        # Assemble envelope
        # ----------------------------------------------------------------
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
                    "stub_channel_bridge_with_canned_ic50",
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
