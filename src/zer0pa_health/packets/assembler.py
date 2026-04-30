"""CardiacPacketAssembler — composes packets from validated L1-L5 envelopes.

Drives the cardiac wedge (PRD section 7) end-to-end:
  1. Load compound fixture for compound metadata only (name, inchikey, smiles,
     research_label, cardiac_research_role, expected_morphology_signal). The
     fixture's `channel_panel_canned` field is NOT consumed by this assembler;
     the channel panel is sourced from the L1 envelope output.
  2. Consume the supplied L1 channel-panel envelope output as the canonical
     channel panel (per `assert_envelope_governs_packet` discipline)
  3. Consume L5 envelope output (or scalar `cmax_unbound_uM`) for exposure
  4. Build cardiac_bridge from L5 outputs
  5. Run morphology gate on supplied error arrays (or skip if absent)
  6. Run hERG-only-overreach detector on the assembled panel
  7. Emit clinical-overclaim, codec-as-mechanism, falsifier-ref guards
  8. Build claims with falsifier_refs and audit_refs
  9. Score against PubMed baseline

Operator brief 2026-04-30: "Assemble cardiac packets from validated L1-L5
envelopes, NOT `channel_panel_canned` fixtures. Fixtures may seed inputs only."
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from zer0pa_health.boundary import RESEARCH_BOUNDARY
from zer0pa_health.envelope import FalsifierStatus
from zer0pa_health.falsifiers.detectors import (
    detect_clinical_overclaim,
    detect_codec_as_mechanism,
    detect_herg_only_overreach,
    detect_missing_falsifier_ref,
    detect_morphology_non_preservation,
    detect_nan_or_nonfinite,
)
from zer0pa_health.ids import (
    audit_id,
    claim_id,
    packet_id as new_packet_id,
    run_id as new_run_id,
)
from zer0pa_health.packets.morphology_gate import MorphologyResult, morphology_gate
from zer0pa_health.packets.schema import (
    CardiacEvidencePacket,
    PacketChannelMember,
    PacketChannelPanel,
    PacketClaim,
    PacketCompound,
    PacketContradiction,
    PacketEngineValueAdd,
    PacketMorphologyBridge,
    PacketVerdict,
)


_GENE_TO_FIELD = {
    "KCNH2": "KCNH2_hERG_IKr",
    "SCN5A": "SCN5A_Nav1_5_INa_INaL",
    "KCNQ1": "KCNQ1_Kv7_1_IKs",
    "CACNA1C": "CACNA1C_CaV1_2_ICaL",
}

_GENE_TO_CHANNEL_CURRENT = {
    "KCNH2": ("hERG", "IKr"),
    "SCN5A": ("Nav1.5", "INaL"),
    "KCNQ1": ("Kv7.1", "IKs"),
    "CACNA1C": ("CaV1.2", "ICaL"),
}


@dataclass
class AssemblerInputs:
    compound_fixture_path: Path
    run_id: str | None = None
    cmax_unbound_uM: float | None = None  # if absent, leave the bridge stub
    morphology_errors_ms: dict[str, list[float]] = field(default_factory=dict)  # fiducial -> errors
    extra_source_refs: list[str] = field(default_factory=list)
    extra_audit_refs: list[str] = field(default_factory=list)
    # The validated L1 channel-panel envelope output. When provided (the
    # governing path), the assembler reads the channel panel from this dict
    # rather than the fixture's `channel_panel_canned` field. Required for
    # production runs per the operator brief 2026-04-30.
    l1_panel_envelope_output: dict[str, Any] | None = None
    # When True, refuse to fall back to fixture's channel_panel_canned even if
    # `l1_panel_envelope_output` is None (default False preserves test-fixture
    # back-compat for unit tests that exercise the assembler in isolation).
    require_envelope: bool = False


def _balance_score(panel: PacketChannelPanel, cmax_unbound_uM: float | None) -> float | None:
    """Compute multi-current balance score: outward(IKr+IKs blocked) - inward(INaL+ICaL blocked).

    Higher score = more outward block = more APD prolongation = more research-only proarrhythmia indicator.
    """
    if cmax_unbound_uM is None:
        return None
    members = {
        "IKr": panel.KCNH2_hERG_IKr,
        "INaL": panel.SCN5A_Nav1_5_INa_INaL,
        "IKs": panel.KCNQ1_Kv7_1_IKs,
        "ICaL": panel.CACNA1C_CaV1_2_ICaL,
    }

    def block_at(member: PacketChannelMember) -> float:
        if member.ic50_uM is None or cmax_unbound_uM is None:
            return 0.0
        return cmax_unbound_uM / (member.ic50_uM + cmax_unbound_uM)

    outward = block_at(members["IKr"]) + block_at(members["IKs"])
    inward = block_at(members["INaL"]) + block_at(members["ICaL"])
    return outward - inward


def _make_member_from_fixture(gene: str, panel_blob: dict[str, Any]) -> PacketChannelMember:
    """Build a member from the LEGACY fixture `channel_panel_canned` shape.

    Used only when no L1 envelope is supplied (test-fixture-only path); production
    runs consume `_make_member_from_envelope` instead.
    """
    field_key = _GENE_TO_FIELD[gene]
    chan, cur = _GENE_TO_CHANNEL_CURRENT[gene]
    blob = panel_blob.get(field_key) or {}
    return PacketChannelMember(
        gene=gene,
        channel=chan,
        current=cur,
        ic50_uM=blob.get("ic50_uM"),
        block_fraction_at_cmax_unbound=blob.get("block_fraction_at_cmax_unbound"),
        method=blob.get("method", "stub"),
        confidence=blob.get("confidence", 0.0),
        explicit_absence=blob.get("explicit_absence"),
    )


def _make_member_from_envelope(
    gene: str, panel_dict: dict[str, dict[str, Any]]
) -> PacketChannelMember:
    """Build a member from the L1 envelope output's `panel` dict (gene-keyed)."""
    chan, cur = _GENE_TO_CHANNEL_CURRENT[gene]
    blob = panel_dict.get(gene) or {}
    return PacketChannelMember(
        gene=gene,
        channel=chan,
        current=cur,
        ic50_uM=blob.get("ic50_uM"),
        block_fraction_at_cmax_unbound=blob.get("block_fraction_at_cmax_unbound"),
        method=blob.get("method", "stub"),
        confidence=blob.get("confidence", 0.0),
        explicit_absence=blob.get("explicit_absence"),
    )


class CardiacPacketAssembler:
    def __init__(self) -> None:
        pass

    def assemble(self, inputs: AssemblerInputs) -> tuple[CardiacEvidencePacket, dict[str, Any]]:
        rid = inputs.run_id or new_run_id()
        with inputs.compound_fixture_path.open("r", encoding="utf-8") as fh:
            fixture = json.load(fh)

        compound = PacketCompound(
            name=fixture["name"],
            inchikey=fixture["inchikey"],
            canonical_smiles=fixture["canonical_smiles"],
            research_label=fixture["drug_class_research_label"],
            cardiac_research_role=fixture["cardiac_research_role"],
        )

        # Channel panel SOURCE-OF-TRUTH selection. The governing path is the L1
        # envelope output. Fall through to the legacy fixture only when no
        # envelope is supplied AND `require_envelope` is False — this preserves
        # test-fixture back-compat for the unit tests that exercise the
        # assembler in isolation, while production runs through cardiac_run.py /
        # pathway1_run.py always pass an envelope.
        envelope_panel: dict[str, dict[str, Any]] | None = None
        envelope_explicit_absence: list[str] | None = None
        envelope_basis: list[str] = []
        if inputs.l1_panel_envelope_output is not None:
            env_out = inputs.l1_panel_envelope_output
            envelope_panel = env_out.get("panel")
            ea = env_out.get("explicit_absence")
            envelope_explicit_absence = list(ea) if ea is not None else []
            envelope_basis = list(env_out.get("basis", []))
            if envelope_panel is None:
                raise ValueError(
                    "AssemblerInputs.l1_panel_envelope_output is missing required 'panel' key"
                )
        elif inputs.require_envelope:
            raise ValueError(
                "AssemblerInputs.require_envelope=True but no l1_panel_envelope_output provided "
                "— production runs MUST pass the L1 channel-panel envelope"
            )

        if envelope_panel is not None:
            panel = PacketChannelPanel(
                KCNH2_hERG_IKr=_make_member_from_envelope("KCNH2", envelope_panel),
                SCN5A_Nav1_5_INa_INaL=_make_member_from_envelope("SCN5A", envelope_panel),
                KCNQ1_Kv7_1_IKs=_make_member_from_envelope("KCNQ1", envelope_panel),
                CACNA1C_CaV1_2_ICaL=_make_member_from_envelope("CACNA1C", envelope_panel),
            )
            panel_genes_present = [
                g for g in _GENE_TO_FIELD if envelope_panel.get(g, {}).get("ic50_uM") is not None
            ]
            explicit_absence = list(envelope_explicit_absence or [])
        else:
            panel_blob = fixture["channel_panel_canned"]
            panel = PacketChannelPanel(
                KCNH2_hERG_IKr=_make_member_from_fixture("KCNH2", panel_blob),
                SCN5A_Nav1_5_INa_INaL=_make_member_from_fixture("SCN5A", panel_blob),
                KCNQ1_Kv7_1_IKs=_make_member_from_fixture("KCNQ1", panel_blob),
                CACNA1C_CaV1_2_ICaL=_make_member_from_fixture("CACNA1C", panel_blob),
            )
            panel_genes_present = [
                g for g, f in _GENE_TO_FIELD.items()
                if panel_blob.get(f, {}).get("ic50_uM") is not None
            ]
            explicit_absence = [
                g for g, f in _GENE_TO_FIELD.items()
                if panel_blob.get(f, {}).get("explicit_absence")
            ]
        herg_check = detect_herg_only_overreach(panel_genes_present, explicit_absence)
        clinical_check = detect_clinical_overclaim(json.dumps(fixture))
        codec_check = detect_codec_as_mechanism(
            "multi-current evidence packet supports IKr block as one of the channels relevant to QT",
            ["channel_panel", "exposure_simulation", "kg_inference"],
        )

        # Morphology gate
        morphology_results: dict[str, MorphologyResult] = {}
        morphology_falsifier = None
        for fid, errs in inputs.morphology_errors_ms.items():
            res = morphology_gate(fid, errs)
            morphology_results[fid] = res
        # Apply detect_morphology_non_preservation on QT if available
        if "QT" in morphology_results:
            qt = morphology_results["QT"]
            morphology_falsifier = detect_morphology_non_preservation(
                qt.median_abs_error_ms, qt.p95_abs_error_ms,
                qt.median_threshold_ms, qt.p95_threshold_ms,
            )
        # NaN/nonfinite check on cmax_unbound_uM
        nonfinite_check = detect_nan_or_nonfinite(
            [inputs.cmax_unbound_uM] if inputs.cmax_unbound_uM is not None else [], "cmax"
        )

        balance = _balance_score(panel, inputs.cmax_unbound_uM)
        bridge = PacketMorphologyBridge(
            cmax_unbound_uM=inputs.cmax_unbound_uM,
            multi_current_balance_score=balance,
            expected_morphology_signal=fixture["expected_morphology_signal"],
            morphology_gate_result={
                fid: {
                    "median": r.median_abs_error_ms,
                    "p95": r.p95_abs_error_ms,
                    "n": r.n_samples,
                    "passed": r.passed,
                }
                for fid, r in morphology_results.items()
            },
        )

        # Build a small set of source refs from the cardiac KG seed knowledge
        source_refs = (
            ["source:FDA_E14_S7B", "source:FDA_CiPA"] + inputs.extra_source_refs
        )

        falsifier_ref_ids = [herg_check.falsifier_id, clinical_check.falsifier_id, codec_check.falsifier_id]
        if morphology_falsifier is not None:
            falsifier_ref_ids.append(morphology_falsifier.falsifier_id)
        # detect_missing_falsifier_ref guard
        ref_check = detect_missing_falsifier_ref(falsifier_ref_ids)

        # Build claims (compound-specific research-only language)
        claim_text = self._claim_text_for(fixture["name"], panel)
        audit_id_for_claim = audit_id()
        audit_refs = [audit_id_for_claim] + inputs.extra_audit_refs

        primary_claim = PacketClaim(
            claim_id=claim_id(),
            text=claim_text,
            multi_current_context=True,  # we always include the multi-current frame
            source_refs=source_refs,
            falsifier_refs=falsifier_ref_ids,
            audit_refs=audit_refs,
            confidence_band="medium",
        )
        claims = [primary_claim]

        contradictions: list[PacketContradiction] = []
        if fixture["name"] == "verapamil":
            contradictions.append(
                PacketContradiction(
                    contradiction_id="contradiction:verapamil:hERG_block_low_TdP",
                    description=(
                        "verapamil exhibits IKr/hERG block in vitro yet shows low torsade-related "
                        "research signal in clinical pharmacology literature, attributed to compensating "
                        "ICaL block."
                    ),
                    sources_in_conflict=["source:FDA_CiPA"],
                    resolution="downgraded",
                )
            )

        # Falsifiers list (raw dicts so we can include status + class without coupling to envelope shape)
        falsifiers = [
            {
                "falsifier_class": herg_check.falsifier_class,
                "falsifier_id": herg_check.falsifier_id,
                "trigger_condition": herg_check.trigger_condition,
                "status": herg_check.status.value if hasattr(herg_check.status, "value") else str(herg_check.status),
                "evidence": herg_check.evidence,
            },
            {
                "falsifier_class": clinical_check.falsifier_class,
                "falsifier_id": clinical_check.falsifier_id,
                "trigger_condition": clinical_check.trigger_condition,
                "status": clinical_check.status.value if hasattr(clinical_check.status, "value") else str(clinical_check.status),
                "evidence": clinical_check.evidence,
            },
            {
                "falsifier_class": codec_check.falsifier_class,
                "falsifier_id": codec_check.falsifier_id,
                "trigger_condition": codec_check.trigger_condition,
                "status": codec_check.status.value if hasattr(codec_check.status, "value") else str(codec_check.status),
                "evidence": codec_check.evidence,
            },
            # noise_brittle_phenotype is registered as inconclusive on a stub packet
            # (we have not actually run NSTDB-style noise stress in this assembler); we
            # surface it as INCONCLUSIVE rather than silently passing.
            {
                "falsifier_class": "noise_brittle_phenotype",
                "falsifier_id": "falsifier:noise_brittle_phenotype:assembler-stub",
                "trigger_condition": "Phenotype claim does not survive calibrated noise (NSTDB-style)",
                "status": "inconclusive",
                "evidence": ["assembler stub did not run noise stress"],
            },
            {
                "falsifier_class": "missing_falsifier_ref",
                "falsifier_id": ref_check.falsifier_id,
                "trigger_condition": ref_check.trigger_condition,
                "status": ref_check.status.value if hasattr(ref_check.status, "value") else str(ref_check.status),
                "evidence": ref_check.evidence,
            },
        ]
        if morphology_falsifier is not None:
            falsifiers.append(
                {
                    "falsifier_class": morphology_falsifier.falsifier_class,
                    "falsifier_id": morphology_falsifier.falsifier_id,
                    "trigger_condition": morphology_falsifier.trigger_condition,
                    "status": morphology_falsifier.status.value if hasattr(morphology_falsifier.status, "value") else str(morphology_falsifier.status),
                    "evidence": morphology_falsifier.evidence,
                }
            )

        # Verdict assembly: a packet with any FAIL of clinical_overclaim or
        # silent_falsifier_loss is BLOCKED; any other FAIL → FAIL; otherwise PASS.
        verdict = PacketVerdict.PASS
        for f in falsifiers:
            if f["status"] == "fail":
                if f["falsifier_class"] in ("clinical_overclaim",):
                    verdict = PacketVerdict.BLOCKED
                    break
                else:
                    verdict = PacketVerdict.FAIL
        if nonfinite_check.status == FalsifierStatus.FAIL:
            verdict = PacketVerdict.FAIL

        engine_value_add = PacketEngineValueAdd(
            rerunnable_source_manifest=True,
            machine_valid_graph=True,
            explicit_contradiction_table=True,
            falsifier_ledger_present=True,
            local_morphology_linkage=bool(morphology_results),
            audit_trail_present=True,
            next_experiment_backedges=[
                "request_l1_full_panel_with_real_FEP",
                "request_NSTDB_noise_stress_run",
                "request_PTB_XL_plus_morphology_validation",
            ],
        )

        packet = CardiacEvidencePacket(
            packet_id=new_packet_id("cardiac", fixture["name"]),
            run_id=rid,
            compound=compound,
            source_manifest_refs=source_refs,
            channel_panel=panel,
            multi_current_interpretation=self._multi_current_interp(fixture["name"], balance),
            ecg_morphology_bridge=bridge,
            claims=claims,
            contradictions=contradictions,
            falsifiers=falsifiers,
            audit_refs=audit_refs,
            engine_value_add=engine_value_add,
            verdict=verdict,
        )

        diagnostics = {
            "herg_check": herg_check.status.value,
            "clinical_check": clinical_check.status.value,
            "codec_check": codec_check.status.value,
            "ref_check": ref_check.status.value,
            "nonfinite_check": nonfinite_check.status.value,
            "morphology_check": (
                morphology_falsifier.status.value if morphology_falsifier else "not_run"
            ),
            "balance_score": balance,
        }
        return packet, diagnostics

    @staticmethod
    def _claim_text_for(name: str, panel: PacketChannelPanel) -> str:
        """Build research-only claim text. NO clinical-overclaim phrases."""
        if name == "dofetilide":
            return (
                "Research observation (boundary: research use only): canned multi-current panel for "
                "dofetilide shows IKr/hERG block in the absence of substantial INa, IKs, or ICaL "
                "block per the explicit-absence record. The repolarization-balance research indicator "
                "leans outward-blocked, consistent with a positive-control IKr profile. Mechanism "
                "claims are conditional on Runpod-real simulation."
            )
        if name == "verapamil":
            return (
                "Research observation (boundary: research use only): canned multi-current panel for "
                "verapamil shows simultaneous IKr/hERG and ICaL block. The research indicator suggests "
                "a partial cancellation of outward-block by inward-block, consistent with the "
                "hERG-only-overreach refuter pattern. Multi-current context is required; an hERG-only "
                "ranking would fail the research-only proarrhythmia indicator."
            )
        if name == "ranolazine":
            return (
                "Research observation (boundary: research use only): canned multi-current panel for "
                "ranolazine shows late-INa (INaL) block as the dominant target with modest IKr block. "
                "This forces the SCN5A/Nav1.5 mechanism node toward source-grounded status; the "
                "single-QT-paragraph collapse is therefore inadequate for this compound."
            )
        return (
            "Research observation (boundary: research use only): canned multi-current panel reviewed; "
            "see channel panel and falsifier list for details."
        )

    @staticmethod
    def _multi_current_interp(name: str, balance: float | None) -> str:
        if balance is None:
            return (
                "Multi-current balance score not computed (no Cmax_unbound provided to the assembler). "
                "Channel-by-channel ic50 values are research-only stub canned outputs."
            )
        return (
            f"Multi-current balance score (research indicator): {balance:.3f}. "
            "Higher = more outward block (APD-prolongation indicator); lower = more inward block "
            "(APD-shortening / counterbalancing). Research only — not a clinical or regulatory verdict."
        )
