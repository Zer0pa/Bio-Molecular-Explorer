"""Tests for L5 cardiac_bridge — exposure-channel bridge sign convention.

Sign convention (documented in cardiac_bridge.py docstring):
    multi_current_balance_score = (outward_block) - (inward_block) / 2.0
    HIGHER score = more outward block = more APD prolongation = higher research risk.
    LOWER score = more inward block offset = lower research APD-prolongation indicator.

Key test cases:
  - Dofetilide: only IKr (outward) blocked → score > 0
  - Verapamil:  IKr (outward) + ICaL (inward) blocked → score LOWER than dofetilide
  - Ranolazine: IKr (outward) + INaL (inward) blocked → score reflects INaL inward offset
"""

from __future__ import annotations

import json
import pathlib

import pytest

from zer0pa_biomolecular_explorer.contracts.l5 import L5ChannelExposureBridge
from zer0pa_biomolecular_explorer.layers.l5.cardiac_bridge import cardiac_bridge, get_explicit_absence

_FIXTURES = pathlib.Path(__file__).parents[2] / "fixtures" / "compounds"


def _load_compound(name: str) -> dict:
    return json.loads((_FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


class TestCardiacBridgeDofetilide:
    def setup_method(self) -> None:
        data = _load_compound("dofetilide")
        self.panel = data["channel_panel_canned"]
        # Use a Cmax_unbound that gives ~65% IKr block at ic50=0.005 µM
        # C = 0.005 * 0.65 / (1 - 0.65) ≈ 0.00929 µM
        self.cmax_uM = 0.00929

    def test_ikr_block_positive(self) -> None:
        result = cardiac_bridge(self.cmax_uM, self.panel)
        assert result.fractional_block_at_cmax["IKr"] > 0.0

    def test_other_channels_zero(self) -> None:
        result = cardiac_bridge(self.cmax_uM, self.panel)
        # IKs, INaL, ICaL all have ic50=None → fractional_block = 0.0
        assert result.fractional_block_at_cmax["IKs"] == 0.0
        assert result.fractional_block_at_cmax["INaL"] == 0.0
        assert result.fractional_block_at_cmax["ICaL"] == 0.0

    def test_balance_score_positive(self) -> None:
        """Dofetilide: only outward (IKr) blocked → score > 0."""
        result = cardiac_bridge(self.cmax_uM, self.panel)
        assert result.multi_current_balance_score is not None
        assert result.multi_current_balance_score > 0.0

    def test_score_around_ikr_block_fraction(self) -> None:
        """Score ~ IKr_block / 2 (only outward term present, divided by 2)."""
        result = cardiac_bridge(self.cmax_uM, self.panel)
        ikr_block = result.fractional_block_at_cmax["IKr"]
        expected_score = ikr_block / 2.0  # outward_sum=ikr_block, inward_sum=0
        assert abs(result.multi_current_balance_score - expected_score) < 1e-6

    def test_explicit_absence_reported(self) -> None:
        result = cardiac_bridge(self.cmax_uM, self.panel)
        absent = get_explicit_absence(result)
        # Three genes have ic50_uM=null
        assert len(absent) == 3

    def test_score_in_bounds(self) -> None:
        result = cardiac_bridge(self.cmax_uM, self.panel)
        assert -1.0 <= result.multi_current_balance_score <= 1.0


class TestCardiacBridgeVerapamil:
    def setup_method(self) -> None:
        data = _load_compound("verapamil")
        self.panel = data["channel_panel_canned"]
        # Cmax_unbound_uM = 0.3 µM (moderate concentration)
        self.cmax_uM = 0.3

    def test_ikr_block_positive(self) -> None:
        result = cardiac_bridge(self.cmax_uM, self.panel)
        assert result.fractional_block_at_cmax["IKr"] > 0.0

    def test_ical_block_positive(self) -> None:
        """Verapamil has ic50=0.10 µM for ICaL → block > 0."""
        result = cardiac_bridge(self.cmax_uM, self.panel)
        assert result.fractional_block_at_cmax["ICaL"] > 0.0

    def test_score_lower_than_dofetilide(self) -> None:
        """Verapamil's ICaL inward block offsets IKr outward block → lower score."""
        vera_result = cardiac_bridge(self.cmax_uM, self.panel)
        # Compare to a dofetilide-like scenario at same cmax (only IKr block, same panel ic50)
        dof_panel = {
            "KCNH2_hERG_IKr": {"ic50_uM": 0.5},  # same IKr ic50 as verapamil
            "SCN5A_Nav1_5_INa_INaL": {"ic50_uM": None},
            "KCNQ1_Kv7_1_IKs": {"ic50_uM": None},
            "CACNA1C_CaV1_2_ICaL": {"ic50_uM": None},  # no ICaL block
        }
        dof_result = cardiac_bridge(self.cmax_uM, dof_panel)
        assert vera_result.multi_current_balance_score < dof_result.multi_current_balance_score

    def test_score_in_bounds(self) -> None:
        result = cardiac_bridge(self.cmax_uM, self.panel)
        assert -1.0 <= result.multi_current_balance_score <= 1.0


class TestCardiacBridgeRanolazine:
    def setup_method(self) -> None:
        data = _load_compound("ranolazine")
        self.panel = data["channel_panel_canned"]
        # Cmax_unbound_uM = 3.0 µM (within therapeutic range)
        self.cmax_uM = 3.0

    def test_ikr_block_positive(self) -> None:
        result = cardiac_bridge(self.cmax_uM, self.panel)
        assert result.fractional_block_at_cmax["IKr"] > 0.0

    def test_inal_block_positive(self) -> None:
        """Ranolazine ic50=6.0 µM for INaL → block > 0 at 3 µM."""
        result = cardiac_bridge(self.cmax_uM, self.panel)
        assert result.fractional_block_at_cmax["INaL"] > 0.0

    def test_score_reflects_inal_inward_offset(self) -> None:
        """Ranolazine INaL block (inward) reduces score vs pure IKr-only blocker."""
        result = cardiac_bridge(self.cmax_uM, self.panel)
        # Score = (IKr + IKs - INaL - ICaL) / 2
        # With INaL block contributing negatively, score < pure-IKr case
        pure_ikr_panel = {
            "KCNH2_hERG_IKr": {"ic50_uM": 12.0},  # same as ranolazine
            "SCN5A_Nav1_5_INa_INaL": {"ic50_uM": None},
            "KCNQ1_Kv7_1_IKs": {"ic50_uM": None},
            "CACNA1C_CaV1_2_ICaL": {"ic50_uM": None},
        }
        pure_result = cardiac_bridge(self.cmax_uM, pure_ikr_panel)
        assert result.multi_current_balance_score < pure_result.multi_current_balance_score

    def test_score_in_bounds(self) -> None:
        result = cardiac_bridge(self.cmax_uM, self.panel)
        assert -1.0 <= result.multi_current_balance_score <= 1.0


class TestCardiacBridgeEdgeCases:
    def test_zero_cmax(self) -> None:
        """At cmax=0, all fractional blocks must be 0."""
        panel = {
            "KCNH2_hERG_IKr": {"ic50_uM": 0.5},
            "SCN5A_Nav1_5_INa_INaL": {"ic50_uM": 5.0},
            "KCNQ1_Kv7_1_IKs": {"ic50_uM": 10.0},
            "CACNA1C_CaV1_2_ICaL": {"ic50_uM": 1.0},
        }
        result = cardiac_bridge(0.0, panel)
        for current, block in result.fractional_block_at_cmax.items():
            assert block == 0.0, f"{current} block should be 0 at cmax=0"
        assert result.multi_current_balance_score == 0.0

    def test_very_high_cmax(self) -> None:
        """At very high cmax, all blocks approach 1.0."""
        panel = {
            "KCNH2_hERG_IKr": {"ic50_uM": 0.001},
            "SCN5A_Nav1_5_INa_INaL": {"ic50_uM": 0.001},
            "KCNQ1_Kv7_1_IKs": {"ic50_uM": 0.001},
            "CACNA1C_CaV1_2_ICaL": {"ic50_uM": 0.001},
        }
        result = cardiac_bridge(1000.0, panel)
        for current, block in result.fractional_block_at_cmax.items():
            assert block > 0.99, f"{current} block should approach 1.0 at high cmax"

    def test_empty_panel_gives_zero_score(self) -> None:
        """Empty panel: all genes absent → all blocks 0, score = 0."""
        result = cardiac_bridge(1.0, {})
        assert result.multi_current_balance_score == 0.0
        absent = get_explicit_absence(result)
        assert len(absent) == 4  # all four canonical genes absent

    def test_result_is_pydantic_model(self) -> None:
        panel = {"KCNH2_hERG_IKr": {"ic50_uM": 1.0}}
        result = cardiac_bridge(0.5, panel)
        assert isinstance(result, L5ChannelExposureBridge)
