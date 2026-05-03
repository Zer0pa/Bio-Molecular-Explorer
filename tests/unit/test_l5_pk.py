"""Tests for L5 pk_models — one_compartment_pk and tmax_analytic."""

from __future__ import annotations

import math

import pytest

from zer0pa_biomolecular_explorer.layers.l5.pk_models import one_compartment_pk, tmax_analytic


class TestTmaxAnalytic:
    def test_standard_values(self) -> None:
        """tmax_analytic(ke=0.1, ka=1.0) should be ~2.56 hours."""
        result = tmax_analytic(ke=0.1, ka=1.0)
        # ln(1.0/0.1) / (1.0 - 0.1) = ln(10) / 0.9 ≈ 2.302585 / 0.9 ≈ 2.5584
        assert abs(result - 2.5584) < 0.01, f"Expected ~2.56, got {result}"

    def test_finite(self) -> None:
        result = tmax_analytic(ke=0.1, ka=1.0)
        assert math.isfinite(result)

    def test_ka_equals_ke(self) -> None:
        """When ka == ke, returns 1/ke (limit form)."""
        result = tmax_analytic(ke=0.5, ka=0.5)
        assert abs(result - 2.0) < 1e-6

    def test_degenerate_zero(self) -> None:
        assert tmax_analytic(ke=0.0, ka=1.0) == 0.0
        assert tmax_analytic(ke=0.1, ka=0.0) == 0.0

    def test_positive_result(self) -> None:
        result = tmax_analytic(ke=0.05, ka=0.5)
        assert result > 0.0


class TestOneCompartmentPK:
    def _default_t(self) -> list[float]:
        return [float(h) for h in range(25)]  # 0..24 hours

    def test_returns_finite_arrays(self) -> None:
        result = one_compartment_pk(
            dose_mg=100.0,
            cl_l_per_h=10.0,
            vd_l=70.0,
            ka_per_h=1.0,
            fraction_unbound=0.5,
            t_hours=self._default_t(),
        )
        for v in result["c_total_ng_per_ml"]:
            assert math.isfinite(v), f"Non-finite value in c_total: {v}"
        for v in result["c_unbound_ng_per_ml"]:
            assert math.isfinite(v), f"Non-finite value in c_unbound: {v}"

    def test_cmax_positive(self) -> None:
        result = one_compartment_pk(
            dose_mg=100.0,
            cl_l_per_h=10.0,
            vd_l=70.0,
            ka_per_h=1.0,
            fraction_unbound=0.5,
            t_hours=self._default_t(),
        )
        assert result["cmax_ng_per_ml"] > 0.0

    def test_tmax_in_range(self) -> None:
        result = one_compartment_pk(
            dose_mg=100.0,
            cl_l_per_h=10.0,
            vd_l=70.0,
            ka_per_h=1.0,
            fraction_unbound=0.5,
            t_hours=self._default_t(),
        )
        assert 0.0 < result["tmax_h"] < 24.0

    def test_all_key_values_finite(self) -> None:
        result = one_compartment_pk(
            dose_mg=100.0,
            cl_l_per_h=10.0,
            vd_l=70.0,
            ka_per_h=1.0,
            fraction_unbound=0.5,
            t_hours=self._default_t(),
        )
        for key in ("cmax_ng_per_ml", "tmax_h", "auc_0_inf_ng_h_per_ml", "cmax_unbound_uM", "half_life_h"):
            assert math.isfinite(result[key]), f"{key} is not finite: {result[key]}"

    def test_correct_array_length(self) -> None:
        t = self._default_t()
        result = one_compartment_pk(
            dose_mg=100.0,
            cl_l_per_h=10.0,
            vd_l=70.0,
            ka_per_h=1.0,
            fraction_unbound=0.5,
            t_hours=t,
        )
        assert len(result["c_total_ng_per_ml"]) == len(t)
        assert len(result["c_unbound_ng_per_ml"]) == len(t)

    def test_unbound_fraction_applied(self) -> None:
        result = one_compartment_pk(
            dose_mg=100.0,
            cl_l_per_h=10.0,
            vd_l=70.0,
            ka_per_h=1.0,
            fraction_unbound=0.5,
            t_hours=self._default_t(),
        )
        # unbound should be fraction_unbound * total at each time point
        for ct, cu in zip(result["c_total_ng_per_ml"], result["c_unbound_ng_per_ml"]):
            assert abs(cu - ct * 0.5) < 1e-9

    def test_cmax_unbound_uM_positive(self) -> None:
        result = one_compartment_pk(
            dose_mg=100.0,
            cl_l_per_h=10.0,
            vd_l=70.0,
            ka_per_h=1.0,
            fraction_unbound=0.5,
            t_hours=self._default_t(),
        )
        assert result["cmax_unbound_uM"] > 0.0

    def test_zero_at_t0(self) -> None:
        result = one_compartment_pk(
            dose_mg=100.0,
            cl_l_per_h=10.0,
            vd_l=70.0,
            ka_per_h=1.0,
            fraction_unbound=0.5,
            t_hours=self._default_t(),
        )
        assert result["c_total_ng_per_ml"][0] == 0.0

    def test_half_life_formula(self) -> None:
        """half_life = ln(2) / ke = ln(2) * vd / cl."""
        result = one_compartment_pk(
            dose_mg=100.0,
            cl_l_per_h=10.0,
            vd_l=70.0,
            ka_per_h=1.0,
            fraction_unbound=0.5,
            t_hours=self._default_t(),
        )
        expected_t12 = math.log(2) * 70.0 / 10.0
        assert abs(result["half_life_h"] - expected_t12) < 1e-6

    def test_100_point_grid(self) -> None:
        """Test with 100-point 24h grid as used by adapter."""
        n_points = 100
        t_hours = [24.0 * i / (n_points - 1) for i in range(n_points)]
        result = one_compartment_pk(
            dose_mg=100.0,
            cl_l_per_h=10.0,
            vd_l=70.0,
            ka_per_h=1.0,
            fraction_unbound=0.5,
            t_hours=t_hours,
        )
        assert len(result["c_total_ng_per_ml"]) == 100
        assert all(math.isfinite(v) for v in result["c_total_ng_per_ml"])
        assert result["cmax_ng_per_ml"] > 0.0

    def test_empty_t_hours_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            one_compartment_pk(
                dose_mg=100.0,
                cl_l_per_h=10.0,
                vd_l=70.0,
                ka_per_h=1.0,
                fraction_unbound=0.5,
                t_hours=[],
            )
