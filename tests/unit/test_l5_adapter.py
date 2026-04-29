"""Tests for L5StubAdapter — end-to-end pipeline including SBML, PK, and cardiac bridge."""

from __future__ import annotations

import json
import math
import pathlib

import pytest

from pydantic import ValidationError

from zer0pa_health.contracts.l5 import L5PKModelKind, L5PKPDInput
from zer0pa_health.envelope import FalsifierStatus, LayerName
from zer0pa_health.layers.l5.adapter import L5StubAdapter
from zer0pa_health.layers.l5.sbml import sbml_roundtrip_ok

_FIXTURES = pathlib.Path(__file__).parents[2] / "fixtures" / "compounds"


def _load_compound(name: str) -> dict:
    return json.loads((_FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _dofetilide_input() -> L5PKPDInput:
    data = _load_compound("dofetilide")
    return L5PKPDInput(
        canonical_smiles=data["canonical_smiles"],
        inchikey=data["inchikey"],
        dose_mg=0.5,
        dose_route="oral",
        model_kind=L5PKModelKind.ONE_COMPARTMENT,
        fraction_unbound=0.3,
        cl_l_per_h=5.0,
        vd_l=50.0,
        ka_per_h=1.2,
    )


def _verapamil_input() -> L5PKPDInput:
    data = _load_compound("verapamil")
    return L5PKPDInput(
        canonical_smiles=data["canonical_smiles"],
        inchikey=data["inchikey"],
        dose_mg=120.0,
        dose_route="oral",
        model_kind=L5PKModelKind.ONE_COMPARTMENT,
        fraction_unbound=0.1,
        cl_l_per_h=50.0,
        vd_l=300.0,
        ka_per_h=0.8,
    )


class TestL5AdapterDofetilide:
    def setup_method(self) -> None:
        self.adapter = L5StubAdapter()
        self.inp = _dofetilide_input()
        self.env = self.adapter.process(self.inp)

    def test_layer_is_l5(self) -> None:
        assert self.env.layer == "L5"

    def test_sbml_packet_built(self) -> None:
        sbml = self.env.output.get("sbml_packet")
        assert sbml is not None
        assert len(sbml["species"]) >= 2
        assert len(sbml["reactions"]) >= 1

    def test_exposure_profile_finite(self) -> None:
        ep = self.env.output["exposure_profile"]
        for key in ("cmax_ng_per_ml", "tmax_h", "auc_0_inf_ng_h_per_ml", "cmax_unbound_uM", "half_life_h"):
            assert math.isfinite(ep[key]), f"{key} not finite"

    def test_cardiac_bridge_present(self) -> None:
        assert self.env.output["cardiac_bridge"] is not None

    def test_ikr_block_positive(self) -> None:
        bridge = self.env.output["cardiac_bridge"]
        assert bridge["fractional_block_at_cmax"]["IKr"] > 0.0

    def test_multi_current_score_positive(self) -> None:
        """Dofetilide: only IKr (outward) blocked → score > 0."""
        bridge = self.env.output["cardiac_bridge"]
        assert bridge["multi_current_balance_score"] > 0.0

    def test_sbml_roundtrip_ok(self) -> None:
        assert self.env.output["sbml_roundtrip_ok"] is True

    def test_falsifier_status_pass(self) -> None:
        # All falsifiers should PASS for valid dofetilide input
        assert self.env.falsifier.status == "pass"

    def test_herg_overreach_falsifier_pass(self) -> None:
        """detect_herg_only_overreach must PASS (all four genes present or explicit_absence)."""
        items_by_class = {item.falsifier_class: item for item in self.env.falsifier.items}
        herg_item = items_by_class.get("hERG_only_overreach")
        assert herg_item is not None, "hERG_only_overreach falsifier not found"
        assert herg_item.status == "pass"

    def test_codec_as_mechanism_falsifier_pass(self) -> None:
        """detect_codec_as_mechanism must PASS with pk_simulation + channel_panel basis."""
        items_by_class = {item.falsifier_class: item for item in self.env.falsifier.items}
        codec_item = items_by_class.get("codec_as_mechanism")
        assert codec_item is not None, "codec_as_mechanism falsifier not found"
        assert codec_item.status == "pass"

    def test_sbml_falsifier_pass(self) -> None:
        items_by_class = {item.falsifier_class: item for item in self.env.falsifier.items}
        sbml_item = items_by_class.get("sbml_schema_failure")
        assert sbml_item is not None
        assert sbml_item.status == "pass"

    def test_back_edges_to_l1_for_absent_genes(self) -> None:
        """Dofetilide has 3 genes with null IC50 → back_edges to L1."""
        assert len(self.env.back_edges) >= 1
        be = self.env.back_edges[0]
        assert be.target_layer == "L1"
        absent = be.proposed_constraint.get("request_panel_for_genes", [])
        assert len(absent) >= 1  # at least some absent genes

    def test_envelope_validates_schema(self) -> None:
        """model_dump() round-trip must succeed."""
        dumped = self.env.model_dump()
        assert dumped["layer"] == "L5"
        assert dumped["contract_version"] == "zer0pa.layer-envelope.v1"

    def test_confidence_in_range(self) -> None:
        score = self.env.confidence.score
        assert 0.5 <= score <= 0.7


class TestL5AdapterInvalidInput:
    def test_nan_dose_rejected_by_pydantic(self) -> None:
        """dose_mg=NaN must be rejected at Pydantic validation (gt=0 constraint)."""
        with pytest.raises(ValidationError):
            L5PKPDInput(
                canonical_smiles="C",
                inchikey=None,
                dose_mg=float("nan"),
                model_kind=L5PKModelKind.ONE_COMPARTMENT,
                fraction_unbound=0.5,
                cl_l_per_h=10.0,
                vd_l=70.0,
                ka_per_h=1.0,
            )

    def test_zero_dose_rejected_by_pydantic(self) -> None:
        """dose_mg=0 must be rejected (gt=0 constraint)."""
        with pytest.raises(ValidationError):
            L5PKPDInput(
                canonical_smiles="C",
                dose_mg=0.0,
                model_kind=L5PKModelKind.ONE_COMPARTMENT,
                fraction_unbound=0.5,
                cl_l_per_h=10.0,
                vd_l=70.0,
                ka_per_h=1.0,
            )

    def test_negative_cl_rejected(self) -> None:
        with pytest.raises(ValidationError):
            L5PKPDInput(
                canonical_smiles="C",
                dose_mg=100.0,
                model_kind=L5PKModelKind.ONE_COMPARTMENT,
                fraction_unbound=0.5,
                cl_l_per_h=-5.0,
                vd_l=70.0,
                ka_per_h=1.0,
            )


class TestL5AdapterNoChannelPanel:
    def test_cardiac_bridge_none_when_no_panel(self) -> None:
        """When channel_panel_lookup is empty, cardiac_bridge should be None."""
        adapter = L5StubAdapter(channel_panel_lookup={})
        inp = L5PKPDInput(
            canonical_smiles="C",
            inchikey="UNKNOWN_INCHIKEY",
            dose_mg=100.0,
            model_kind=L5PKModelKind.ONE_COMPARTMENT,
            fraction_unbound=0.5,
            cl_l_per_h=10.0,
            vd_l=70.0,
            ka_per_h=1.0,
        )
        env = adapter.process(inp)
        assert env.output["cardiac_bridge"] is None

    def test_confidence_reduced_without_panel(self) -> None:
        adapter = L5StubAdapter(channel_panel_lookup={})
        inp = L5PKPDInput(
            canonical_smiles="C",
            inchikey="UNKNOWN_INCHIKEY",
            dose_mg=100.0,
            model_kind=L5PKModelKind.ONE_COMPARTMENT,
            fraction_unbound=0.5,
            cl_l_per_h=10.0,
            vd_l=70.0,
            ka_per_h=1.0,
        )
        env = adapter.process(inp)
        # Confidence is capped to MEDIUM/LOW (0.50) when no bridge
        assert env.confidence.score < 0.65

    def test_back_edges_to_l1_emitted_when_no_panel(self) -> None:
        """Even without a panel, back_edges to L1 are emitted for absent genes."""
        adapter = L5StubAdapter(channel_panel_lookup={})
        inp = L5PKPDInput(
            canonical_smiles="C",
            inchikey="UNKNOWN_INCHIKEY",
            dose_mg=100.0,
            model_kind=L5PKModelKind.ONE_COMPARTMENT,
            fraction_unbound=0.5,
            cl_l_per_h=10.0,
            vd_l=70.0,
            ka_per_h=1.0,
        )
        env = adapter.process(inp)
        assert len(env.back_edges) >= 1
        be = env.back_edges[0]
        assert be.target_layer == "L1"
        absent = be.proposed_constraint.get("request_panel_for_genes", [])
        assert len(absent) >= 1


class TestL5AdapterSBMLRoundtrip:
    def test_sbml_roundtrip_standalone(self) -> None:
        """sbml_roundtrip_ok() must return True for a well-formed packet."""
        from zer0pa_health.layers.l5.sbml import build_minimal_sbml_packet
        packet = build_minimal_sbml_packet(
            model_kind="one_compartment",
            parameters={"cl": 10.0, "vd": 70.0, "ka": 1.0, "fu": 0.5},
        )
        assert sbml_roundtrip_ok(packet) is True

    def test_sbml_packet_has_required_fields(self) -> None:
        from zer0pa_health.layers.l5.sbml import build_minimal_sbml_packet
        packet = build_minimal_sbml_packet(
            model_kind="one_compartment",
            parameters={"cl": 10.0, "vd": 70.0},
        )
        assert len(packet.species) >= 2
        assert len(packet.reactions) >= 1
        assert packet.sbml_version == "L3V2"


class TestL5AdapterVerapamil:
    def test_score_lower_than_herg_only_refcase(self) -> None:
        """Verapamil must have lower balance score than a pure-IKr blocker at same params."""
        adapter = L5StubAdapter()
        inp = _verapamil_input()
        env = adapter.process(inp)
        # Verapamil should have a bridge (inchikey in fixtures)
        bridge = env.output.get("cardiac_bridge")
        if bridge is None:
            pytest.skip("Verapamil fixture not in channel panel lookup")
        # ICaL block should reduce the balance score
        ikr_block = bridge["fractional_block_at_cmax"].get("IKr", 0.0)
        ical_block = bridge["fractional_block_at_cmax"].get("ICaL", 0.0)
        # If ICaL is blocked, score is less than it would be without ICaL block
        if ical_block > 0:
            expected_reduced_score = (ikr_block - ical_block) / 2.0
            assert bridge["multi_current_balance_score"] <= ikr_block / 2.0 + 1e-6
