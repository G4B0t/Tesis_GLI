from __future__ import annotations

import inspect
from math import pi

import numpy as np
import pytest

from gli.base_case import santos_50_70_80
from gli.events import EVENT_G_MOMENTUM_EQUILIBRIUM, stage_g_momentum_residual
from gli.initial_conditions import GRAVITY_M_S2, initial_stage_1
from gli.stage_ef_dynamic import StageEFResult
from gli.stage_fg_dynamic import (
    HIGH_VELOCITY_WARNING,
    santos_stage_43_film_return_rate_m3_s,
    simulate_stage_f_to_g,
    stage_43_equation_contract_residuals,
)


def _synthetic_source_consistent_f(params):
    gas = params.gas
    H = params.geometry.valve_depth_m
    r = params.geometry.tubing_diameter_m / 2.0
    At = pi * r**2
    y = 0.002
    h_l = 1.0
    Ab = pi * (r - y) ** 2
    rho_mean = 25.0
    rho_surface = (
        gas.gas_molar_mass_kg_mol * params.operating.surface_tubing_pressure_pa
        / (gas.z_ts * gas.gas_constant_j_mol_k * gas.temp_ts_k)
    )
    k_t3 = gas.z_t3 * gas.gas_constant_j_mol_k * gas.temp_t3_k / gas.gas_molar_mass_kg_mol
    pt3 = k_t3 * (2.0 * rho_mean - rho_surface)
    pt1 = pt3 + initial_stage_1(params)["rho_l"] * GRAVITY_M_S2 * h_l
    gas_mass = rho_mean * Ab * (H - h_l)
    one = lambda value: np.array([value], dtype=float)
    return StageEFResult(
        time_s=one(0.0),
        gas_density_kg_m3=one(rho_mean),
        tubing_pressure_pa=one(pt1),
        gas_velocity_m_s=one(10.0),
        film_thickness_m=one(y),
        film_velocity_m_s=one(0.0),
        gas_mass_kg=one(gas_mass),
        surface_gas_rate_kg_s=one(0.0),
        interfacial_shear_pa=one(0.0),
        film_volume_m3=one((At - Ab) * H),
        produced_film_volume_m3=one(0.2),
        entrained_volume_m3=one(0.0),
        reservoir_accumulated_m3=one(0.0),
        valve_open=np.array([False]),
        event_f_reached=True,
        event_f_time_s=0.0,
        gas_balance_relative_error=0.0,
        liquid_balance_relative_error=0.0,
        initial_state_source="synthetic source-consistent Stage 4.2 F fixture",
        fallback_volume_m3=one(0.0),
        corrected_certified=True,
        rhs_mode="santos_stage42",
        reservoir_inflow_valid=True,
        gas_pressure_at_liquid_top_pa=one(pt3),
        liquid_height_m=one(h_l),
        physical_lower_liquid_volume_m3=one(Ab * h_l),
        surface_gas_velocity_m_s=one(20.0),
        gas_momentum_condition_number=one(1.0),
        source_certification_status="SOURCE_CERTIFIED_A_TO_F",
    )


@pytest.fixture(scope="module")
def chain():
    params = santos_50_70_80()
    ef = _synthetic_source_consistent_f(params)
    snapshot = {name: value.copy() for name, value in {
        "time": ef.time_s,
        "pressure": ef.tubing_pressure_pa,
        "film": ef.film_volume_m3,
        "produced": ef.produced_film_volume_m3,
    }.items()}
    fg = simulate_stage_f_to_g(params, stage_e_f=ef, max_step_s=1.0)
    return params, ef, fg, snapshot


def test_stage_43_source_equation_contracts(chain):
    params, _ef, fg, _snapshot = chain
    residuals = stage_43_equation_contract_residuals(params, fg)
    assert set(residuals) == {"4.1.89", "4.1.94", "4.1.97", "4.1.107", "4.1.108"}
    assert max(residuals.values()) <= 1.0e-8


def test_santos_4195_film_return_closure():
    y, r, rho_l, mu_l = 0.003, 0.025, 900.0, 0.003
    expected = rho_l * 9.80665 * (2.0 * np.pi * r) * y**3 / (3.0 * mu_l)
    assert santos_stage_43_film_return_rate_m3_s(y, r, rho_l, mu_l) == pytest.approx(expected)


def test_f_initial_identity_continuity_includes_spatial_state(chain):
    _params, _ef, fg, _snapshot = chain
    assert fg.continuity_passed
    assert {item.name for item in fg.continuity} >= {
        "liquid_height", "pressure_t1", "pressure_t3", "lower_liquid_volume",
        "mean_gas_density", "gas_inventory",
    }
    assert all(item.passed for item in fg.continuity)


def test_derivatives_and_physical_bounds(chain):
    params, _ef, fg, _snapshot = chain
    assert fg.physical_bounds_passed, fg.failed_physical_bounds
    assert np.all(np.isfinite(fg.bottom_gas_density_kg_m3))
    assert np.all(fg.bottom_gas_pressure_pa > 0.0)
    assert np.all((fg.liquid_height_m >= 0.0) & (fg.liquid_height_m < params.geometry.valve_depth_m))
    assert fg.scientific_warning == HIGH_VELOCITY_WARNING


def test_event_g_is_unchanged_and_horizon_is_not_reported_as_event(chain):
    _params, _ef, fg, _snapshot = chain
    assert not fg.event_g_reached
    assert fg.event_identifier == EVENT_G_MOMENTUM_EQUILIBRIUM
    assert fg.event_g_time_s is None
    assert fg.integration_end_time_s == pytest.approx(1200.0)
    assert fg.momentum_residual_pa[0] > fg.momentum_residual_pa[-1] > 0.0
    assert not fg.event_direction_verified


def test_momentum_residual_is_zero_velocity_limit():
    assert stage_g_momentum_residual(200.0, 100.0, 2.0, 5.0, 10.0) == 0.0


def test_gas_liquid_balances_and_dynamic_ipr(chain):
    _params, _ef, fg, _snapshot = chain
    assert fg.gas_balance_normalized_residual <= 1.0e-8
    assert fg.liquid_balance_normalized_residual <= 1.0e-8
    assert fg.reservoir_inflow_valid
    assert np.min(fg.reservoir_rate_m3_s) >= 0.0
    assert np.ptp(fg.reservoir_rate_m3_s) > 0.0


def test_numerical_convergence_against_stricter_configuration(chain):
    params, ef, baseline, _snapshot = chain
    strict = simulate_stage_f_to_g(params, stage_e_f=ef, max_step_s=0.5, rtol=1e-9, atol=1e-11)
    assert strict.event_g_time_s is None
    comparisons = (
        (baseline.integration_end_time_s, strict.integration_end_time_s),
        (baseline.bottom_gas_pressure_pa[-1], strict.bottom_gas_pressure_pa[-1]),
        (baseline.gas_pressure_at_liquid_top_pa[-1], strict.gas_pressure_at_liquid_top_pa[-1]),
        (baseline.liquid_height_m[-1], strict.liquid_height_m[-1]),
    )
    for coarse, refined in comparisons:
        assert abs(coarse - refined) / max(abs(refined), 1e-12) <= 1e-5


def test_fg_does_not_reconstruct_spatial_state_from_ledgers():
    source = inspect.getsource(simulate_stage_f_to_g)
    assert "(reservoir0 + fallback0) / Ab0" not in source
    assert "2.0 * mean_rho0 - rho_surface" not in source
    assert "physical_lower_liquid_volume_m3" in source


def test_f_input_is_not_mutated_and_run_is_reproducible(chain):
    params, ef, first, snapshot = chain
    assert np.array_equal(ef.time_s, snapshot["time"])
    assert np.array_equal(ef.tubing_pressure_pa, snapshot["pressure"])
    assert np.array_equal(ef.film_volume_m3, snapshot["film"])
    assert np.array_equal(ef.produced_film_volume_m3, snapshot["produced"])
    second = simulate_stage_f_to_g(params, stage_e_f=ef, max_step_s=1.0)
    assert second.event_g_time_s is None
    assert first.integration_end_time_s == second.integration_end_time_s
    assert first.bottom_gas_pressure_pa[-1] == pytest.approx(second.bottom_gas_pressure_pa[-1], rel=1e-12)
