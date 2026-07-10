import numpy as np
import pytest

from gli.base_case import santos_50_70_80
from gli.initial_conditions import initial_stage_1
from gli.stage1_dynamic import casing_pressure_ratio, simulate_stage_1
from gli.validation_stage1 import compare_figure_5_1_ab


@pytest.fixture(scope="module")
def result():
    return simulate_stage_1(santos_50_70_80(), max_step_s=0.25)


def test_annulus_mass_is_conserved(result):
    assert result.opened
    assert result.mass_balance_relative_error < 1.0e-5
    assert result.annulus_gas_mass_kg[-1] > result.annulus_gas_mass_kg[0]


def test_pressure_mass_and_density_are_monotonic(result):
    for values in (result.annulus_gas_mass_kg, result.p_c1_pa,
                   result.p_c2_pa, result.rho_c1_kg_m3,
                   result.rho_c2_kg_m3, result.resultant_force_n):
        assert np.all(np.diff(values) >= -1.0e-9)
    assert np.all(result.standard_gas_rate_m3_s > 0.0)
    assert np.all(np.diff(result.standard_gas_rate_m3_s) <= 1.0e-9)


def test_event_time_converges_with_step_refinement():
    params = santos_50_70_80()
    coarse = simulate_stage_1(params, max_step_s=2.0, rtol=1e-7)
    medium = simulate_stage_1(params, max_step_s=1.0, rtol=1e-8)
    fine = simulate_stage_1(params, max_step_s=0.5, rtol=1e-9)
    assert abs(medium.opening_time_s - fine.opening_time_s) < 1.0e-4
    assert abs(coarse.opening_time_s - fine.opening_time_s) < 1.0e-3


def test_solution_is_physically_feasible_at_event_b(result):
    params = santos_50_70_80()
    initial = initial_stage_1(params)
    assert result.resultant_force_n[0] < 0.0
    assert abs(result.resultant_force_n[-1]) < 1.0e-6
    assert result.p_c2_pa[-1] == pytest.approx(initial["p_vo"], rel=1e-8)
    assert np.all(result.p_c1_pa < result.p_c2_pa)
    assert np.all(result.p_c2_pa < params.operating.injection_pressure_pa)
    assert np.all(result.rho_c1_kg_m3 > 0.0)
    assert np.all(result.rho_c2_kg_m3 > 0.0)
    ratio = result.p_c2_pa[-1] / result.p_c1_pa[-1]
    assert ratio == pytest.approx(casing_pressure_ratio(params))


def test_figure_5_1_comparison_is_reported_not_fitted(result):
    comparison = compare_figure_5_1_ab(result)
    assert comparison.pressure_rmse_kgf_cm2 < 2.5
    assert comparison.simulated_b_time_s > comparison.reference_b_time_s
