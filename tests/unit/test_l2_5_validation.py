"""Tests for L2.5 validation helpers: validate_rxnsmiles and validate_atom_map.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.
"""

from __future__ import annotations

import pytest

from zer0pa_biomolecular_explorer.layers.l2_5.validation import validate_atom_map, validate_rxnsmiles


# ---------------------------------------------------------------------------
# validate_rxnsmiles
# ---------------------------------------------------------------------------


class TestValidateRxnsmiles:
    def test_empty_string_fails(self):
        ok, reason = validate_rxnsmiles("")
        assert not ok
        assert "empty" in reason.lower()

    def test_none_type_fails(self):
        ok, reason = validate_rxnsmiles(None)  # type: ignore[arg-type]
        assert not ok

    def test_missing_arrow_fails(self):
        ok, reason = validate_rxnsmiles("CCO.CC")
        assert not ok
        assert ">>" in reason or "separator" in reason.lower() or "reactants" in reason.lower()

    def test_single_arrow_fails(self):
        # Only one ">" not enough for reactants>reagents>products without ">>"
        ok, reason = validate_rxnsmiles("CCO>CCN")
        assert not ok

    def test_empty_reactants_side_fails(self):
        ok, reason = validate_rxnsmiles(">>CCO")
        assert not ok
        assert "reactants" in reason.lower() or "empty" in reason.lower()

    def test_empty_products_side_fails(self):
        ok, reason = validate_rxnsmiles("CCO>>")
        assert not ok
        assert "products" in reason.lower() or "empty" in reason.lower()

    def test_unbalanced_parens_fails(self):
        ok, reason = validate_rxnsmiles("C(C>>CC")
        assert not ok
        assert "paren" in reason.lower() or "unbalanced" in reason.lower()

    def test_unbalanced_brackets_fails(self):
        ok, reason = validate_rxnsmiles("[CH3>>CC")
        assert not ok
        assert "bracket" in reason.lower() or "unbalanced" in reason.lower()

    def test_simple_double_arrow_passes(self):
        ok, reason = validate_rxnsmiles("CCO>>CC.O")
        assert ok, f"Expected pass, got: {reason}"

    def test_three_part_format_passes(self):
        ok, reason = validate_rxnsmiles("CCO>H2O>CC.O")
        assert ok, f"Expected pass, got: {reason}"

    def test_atom_mapped_rxnsmiles_passes(self):
        rxn = "[CH3:1][NH2:2].[Cl:3][CH2:4]>>[CH3:1][NH:2][CH2:4]"
        ok, reason = validate_rxnsmiles(rxn)
        assert ok, f"Expected pass, got: {reason}"

    def test_complex_real_shaped_rxnsmiles_passes(self):
        rxn = (
            "CN(C)S(=O)(=O)c1ccc(N)cc1.ClCCOc2ccc(CCN(C)S(=O)(=O)C)cc2"
            ">>"
            "CN(C)S(=O)(=O)c1ccc(NCCOc2ccc(CCN(C)S(=O)(=O)C)cc2)cc1"
        )
        ok, reason = validate_rxnsmiles(rxn)
        assert ok, f"Expected pass, got: {reason}"


# ---------------------------------------------------------------------------
# validate_atom_map
# ---------------------------------------------------------------------------


class TestValidateAtomMap:
    def test_empty_string_fails(self):
        ok, reason = validate_atom_map("")
        assert not ok
        assert "empty" in reason.lower()

    def test_none_type_fails(self):
        ok, reason = validate_atom_map(None)  # type: ignore[arg-type]
        assert not ok

    def test_no_arrow_fails(self):
        ok, reason = validate_atom_map("CCO")
        assert not ok

    def test_no_atom_map_indices_fails(self):
        # Valid RXNSMILES format but no :N] patterns anywhere
        ok, reason = validate_atom_map("CCO>>CC.O")
        assert not ok
        assert "atom-map" in reason.lower() or "indices" in reason.lower()

    def test_atom_map_only_on_reactants_fails(self):
        # Indices in reactants but not in products
        ok, reason = validate_atom_map("[CH3:1][NH2:2]>>CC")
        assert not ok
        assert "product" in reason.lower() or "indices" in reason.lower()

    def test_atom_map_only_on_products_fails(self):
        # Indices in products but not in reactants
        ok, reason = validate_atom_map("CCO>>[CH3:1][NH2:2]")
        assert not ok
        assert "reactant" in reason.lower() or "indices" in reason.lower()

    def test_disjoint_indices_fails(self):
        # Reactants have :1, :2; products have :3, :4 — no overlap
        ok, reason = validate_atom_map("[C:1][N:2]>>[C:3][N:4]")
        assert not ok
        assert "shared" in reason.lower() or "tracked" in reason.lower() or "indices" in reason.lower()

    def test_valid_simple_atom_mapped_passes(self):
        # Minimal valid: index :1 appears on both sides
        ok, reason = validate_atom_map("[CH3:1][NH2:2]>>[CH3:1][NH:2][CH2:3]")
        assert ok, f"Expected pass, got: {reason}"

    def test_valid_three_part_format_passes(self):
        ok, reason = validate_atom_map("[CH3:1][NH2:2]>H2O>[CH3:1][NH:2][CH2:3]")
        assert ok, f"Expected pass, got: {reason}"

    def test_dofetilide_step_atom_map_passes(self):
        # Step from dofetilide fixture (simplified)
        rxn = (
            "[CH3:1][N:2]([CH3:3])[S:4](=[O:5])(=[O:6])[c:7]1[cH:8][cH:9][c:10]([NH2:11])[cH:12][cH:13]1"
            ">>"
            "[CH3:1][N:2]([CH3:3])[S:4](=[O:5])(=[O:6])[c:7]1[cH:8][cH:9][c:10]([NH:11][CH2:15])[cH:12][cH:13]1"
        )
        ok, reason = validate_atom_map(rxn)
        assert ok, f"Expected pass, got: {reason}"

    def test_multiple_shared_indices_passes(self):
        ok, reason = validate_atom_map(
            "[C:1][C:2][N:3]>>[C:1][C:2][N:3][C:4]"
        )
        assert ok, f"Expected pass, got: {reason}"
