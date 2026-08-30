from __future__ import annotations

import numpy as np
import pytest

from gli.audit_stage_fg import run_corrected_a_to_g_chain
from gli.events import EVENT_G_MOMENTUM_EQUILIBRIUM, stage_g_momentum_residual
from gli.stage_fg_dynamic import (
    HIGH_VELOCITY_WARNING,
    santos_stage_43_film_return_rate_m3_s,
    simulate_stage_f_to_g,
    stage_43_equation_contract_residuals,
)


@pytest.fixture(scope="module")
def chain():
    values = run_corrected_a_to_g_chain(af_max_step_s=0.5, fg_max_step_s=0.5)
    ef = values[-2]
    snapshot = {
        "time": ef.time_s.copy(),
        "pressure": ef.tubing_pressure_pa.copy(),
        "film": ef.film_volume_m3.copy(),
        "produced": ef.produced_film_volume_m3.copy(),
    }
    return values, snapshot


def test_stage_43_source_equation_contracts(chain):
    values, _snapshot = chain
    params, fg = values[0], values[-1]
    residuals = stage_43_equation_contract_residuals(params, fg)
    assert set(residuals) == {"4.1.89", "4.1.94", "4.1.97", "4.1.107", "4.1.108"}
    assert max(residuals.values()) <= 1.0e-8


def test_santos_4195_film_return_closure():
    y, r, rho_l, mu_l = 0.003, 0.025, 900.0, 0.003
    expected = rho_l * 9.80665 * (2.0 * np.pi * r) * y**3 / (3.0 * mu_l)
    assert santos_stage_43_film_return_rate_m3_s(y, r, rho_l, mu_l) == pytest.approx(expected)


def test_f_initial_identity_continuity(chain):
    values, _snapshot = chain
    fg = values[-1]
    assert fg.continuity_passed
    assert all(item.passed for item in fg.continuity)
    assert max(item.absolute_error for item in fg.continuity) <= max(
        item.tolerance for item in fg.continuity
    )


def test_derivatives_produce_finite_trajectory(chain):
    values, _snapshot = chain
    fg = values[-1]
    arrays = (
        fg.bottom_gas_density_kg_m3,
        fg.gas_pressure_at_liquid_top_pa,
        fg.bottom_gas_pressure_pa,
        fg.liquid_height_m,
        fg.film_thickness_m,
        fg.film_return_rate_m3_s,
    )
    assert all(np.all(np.isfinite(array)) for array in arrays)


def test_physical_bounds_and_warning(chain):
    values, _snapshot = chain
    params, fg = values[0], values[-1]
    assert fg.physical_bounds_passed, fg.failed_physical_bounds
    assert np.all(fg.bottom_gas_pressure_pa > 0.0)
    assert np.all(fg.bottom_gas_density_kg_m3 > 0.0)
    assert np.all((fg.film_thickness_m >= 0.0) & (fg.film_thickness_m < params.geometry.tubing_diameter_m / 2.0))
    assert np.all((fg.liquid_height_m >= 0.0) & (fg.liquid_height_m < params.geometry.valve_depth_m))
    assert fg.scientific_warning == HIGH_VELOCITY_WARNING


def test_event_g_uses_santos_momentum_residual_and_legacy_is_diagnostic(chain):
    values, _snapshot = chain
    fg = values[-1]
    assert not fg.event_g_reached
    assert fg.event_identifier == EVENT_G_MOMENTUM_EQUILIBRIUM
    assert fg.momentum_residual_pa[0] > fg.momentum_residual_pa[-1] > 0.0
    assert len(fg.legacy_event_times_s) == 1
    assert 0.0 < fg.legacy_event_times_s[0] < fg.event_g_time_s


def test_momentum_residual_is_zero_velocity_limit():
    assert stage_g_momentum_residual(200.0, 100.0, 2.0, 5.0, 10.0) == 0.0


def test_event_g_crosses_in_descending_direction(chain):
    values, _snapshot = chain
    fg = values[-1]
    assert fg.event_direction == -1.0
    assert not fg.event_direction_verified
    assert fg.momentum_residual_pa[-2] > fg.momentum_residual_pa[-1]


def test_gas_and_liquid_mass_balances_close(chain):
    values, _snapshot = chain
    fg = values[-1]
    assert fg.gas_balance_normalized_residual <= 1.0e-8
    assert fg.liquid_balance_normalized_residual <= 1.0e-8
    assert fg.gas_balance_absolute_residual_kg >= 0.0
    assert fg.liquid_balance_absolute_residual_m3 >= 0.0


def test_film_returns_to_bottom_with_separate_provenance(chain):
    values, _snapshot = chain
    _params, fg = values[0], values[-1]
    assert fg.film_returned_volume_m3[-1] > 0.0
    assert fg.film_volume_m3[-1] < fg.film_volume_m3[0]
    assert fg.bottom_liquid_volume_m3[-1] > fg.bottom_liquid_volume_m3[0]
    assert np.allclose(fg.produced_liquid_volume_m3, fg.produced_liquid_volume_m3[0])
    actual_reservoir = fg.reservoir_accumulated_m3[-1] - fg.reservoir_accumulated_m3[0]
    trapezoid_reservoir = np.trapezoid(fg.reservoir_rate_m3_s, fg.time_s)
    assert actual_reservoir == pytest.approx(trapezoid_reservoir, rel=2.0e-5)
    assert np.ptp(fg.reservoir_rate_m3_s) > 0.0
    assert not fg.reservoir_inflow_valid
    assert "INVALID_REVERSE_FLOW_FOR_LINEAR_IPR" in fg.reservoir_inflow_statuses


def test_numerical_convergence_against_stricter_configuration(chain):
    values, _snapshot = chain
    params, ef, baseline = values[0], values[-2], values[-1]
    strict = simulate_stage_f_to_g(
        params,
        stage_e_f=ef,
        max_step_s=0.25,
        rtol=1.0e-9,
        atol=1.0e-11,
    )
    comparisons = (
        (baseline.event_g_time_s, strict.event_g_time_s),
        (baseline.bottom_gas_pressure_pa[-1], strict.bottom_gas_pressure_pa[-1]),
        (baseline.gas_pressure_at_liquid_top_pa[-1], strict.gas_pressure_at_liquid_top_pa[-1]),
        (baseline.liquid_height_m[-1], strict.liquid_height_m[-1]),
        (baseline.fallback_volume_m3[-1], strict.fallback_volume_m3[-1]),
    )
    for coarse, refined in comparisons:
        assert abs(coarse - refined) / max(abs(refined), 1.0e-12) <= 1.0e-5


def test_a_to_f_regression_objects_are_not_mutated_by_fg(chain):
    values, snapshot = chain
    ef = values[-2]
    assert np.array_equal(ef.time_s, snapshot["time"])
    assert np.array_equal(ef.tubing_pressure_pa, snapshot["pressure"])
    assert np.array_equal(ef.film_volume_m3, snapshot["film"])
    assert np.array_equal(ef.produced_film_volume_m3, snapshot["produced"])
    assert ef.corrected_certified and ef.event_f_reached


def test_internal_a_to_g_orchestration_and_reproducibility(chain):
    values, _snapshot = chain
    params, ef, first = values[0], values[-2], values[-1]
    second = simulate_stage_f_to_g(params, stage_e_f=ef, max_step_s=0.5)
    assert not first.event_g_reached
    assert first.event_g_time_s == pytest.approx(second.event_g_time_s, rel=1.0e-12)
    assert first.bottom_gas_pressure_pa[-1] == pytest.approx(second.bottom_gas_pressure_pa[-1], rel=1.0e-12)
    assert first.legacy_event_times_s == pytest.approx(second.legacy_event_times_s, rel=1.0e-12)
    assert first.event_g_time_s > 0.0
