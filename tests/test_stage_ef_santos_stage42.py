from __future__ import annotations

from math import pi

import numpy as np
import pytest

from gli.audit_block6m4_ef import build_corrected_e_state
from gli.base_case import santos_50_70_80
from gli.block6p_parameters import FrictionClosure, friction_factor
from gli.geometry import tubing_area
from gli.initial_conditions import GRAVITY_M_S2, initial_stage_1
from gli.reservoir import reservoir_inflow_from_pt1
from gli.stage_ef_dynamic import (
    Stage42InitialStateIncompatibility,
    audit_stage_42_initial_state,
    default_stage_ef_parameters,
    santos_stage_42_derivatives,
    simulate_stage_e_to_f,
)
from gli.stage_fg_dynamic import simulate_stage_f_to_g


def _consistent_stage42_state():
    params = santos_50_70_80()
    gas = params.gas
    rho_surface = (
        gas.gas_molar_mass_kg_mol * params.operating.surface_tubing_pressure_pa
        / (gas.z_ts * gas.gas_constant_j_mol_k * gas.temp_ts_k)
    )
    k_t3 = gas.z_t3 * gas.gas_constant_j_mol_k * gas.temp_t3_k / gas.gas_molar_mass_kg_mol
    rho_l = initial_stage_1(params)["rho_l"]
    h_l = 1.0
    rho_g = 25.0
    pt3 = k_t3 * (2.0 * rho_g - rho_surface)
    pt1 = pt3 + rho_l * GRAVITY_M_S2 * h_l
    return params, np.array([h_l, pt1, pt3, rho_g, 2.0, 10.0, 0.002])


def test_stage42_source_equation_residuals_are_independent_and_scaled():
    params, state = _consistent_stage42_state()
    derivative, diagnostics = santos_stage_42_derivatives(params, state)
    h_l, pt1, _pt3, rho_g, vf, vg, y = state
    dh, dpt1, dpt3, drho, dvf, dvg, dy = derivative
    H = params.geometry.valve_depth_m
    D = params.geometry.tubing_diameter_m
    r = D / 2.0
    At = tubing_area(D)
    Ab = pi * (r - y) ** 2
    Af = At - Ab
    Lg = H - h_l
    rho_l = initial_stage_1(params)["rho_l"]
    rho_surface = diagnostics["rho_surface"]
    vgs = 2.0 * vg
    closure = default_stage_ef_parameters()
    friction_closure = FrictionClosure(closure.roughness)
    gas_diameter = 2.0 * (r - y)
    fg, _ = friction_factor(
        max(rho_g * abs(vg) * gas_diameter / 1.1e-5, 1e-9), gas_diameter, friction_closure
    )
    film_diameter = 4.0 * Af / (2.0 * pi * r + 2.0 * pi * (r - y))
    ff, _ = friction_factor(
        max(rho_l * abs(vf) * film_diameter / params.fluids.liquid_viscosity_pa_s, 1e-9),
        film_diameter,
        friction_closure,
    )
    qres = reservoir_inflow_from_pt1(params, pt1, rho_l).rate_m3_s
    gas = params.gas
    k_t3 = gas.z_t3 * gas.gas_constant_j_mol_k * gas.temp_t3_k / gas.gas_molar_mass_kg_mol

    residuals = {
        # 4.1.76 and 4.1.87: m3/s.
        "4.1.76": 2.0 * pi * H * (r - y) * dy + vf * Af,
        "4.1.87": Ab * dh - 2.0 * pi * (r - y) * h_l * dy - qres,
        # 4.1.80: m3/s2.
        "4.1.80": (
            Af * (dvf + GRAVITY_M_S2)
            + 2.0 * pi * (r - y)
            * (vf * dy - fg * rho_g * vg**2 * Lg / (8.0 * rho_l * H))
            + ff * vf**2 * pi * r / 4.0
            - Af * (pt1 - params.operating.surface_tubing_pressure_pa) / (rho_l * H)
        ),
        # 4.1.83: kg/(m2 s); 4.1.84, .89 and .90: Pa/s.
        "4.1.83": Lg * (drho - 2.0 * rho_g * dy / (r - y)) - rho_g * dh + rho_surface * vgs,
        "4.1.84": (
            dpt3
            - (fg * vg**2 * Lg / (2.0 * D) + Lg * GRAVITY_M_S2) * drho
            - fg * rho_g * vg * Lg * dvg / D
            + (fg * rho_g * vg**2 / (2.0 * D) + rho_g * GRAVITY_M_S2) * dh
        ),
        "4.1.89": dpt1 - dpt3 - rho_l * GRAVITY_M_S2 * dh,
        "4.1.90": dpt3 - 2.0 * k_t3 * drho,
    }
    scales = {
        "4.1.76": max(abs(vf * Af), 1e-12),
        "4.1.80": max(abs(Af * GRAVITY_M_S2), 1e-12),
        "4.1.83": max(abs(rho_surface * vgs), 1e-12),
        "4.1.84": max(abs(dpt3), 1.0),
        "4.1.87": max(abs(qres), 1e-12),
        "4.1.89": max(abs(dpt1), 1.0),
        "4.1.90": max(abs(dpt3), 1.0),
    }
    normalized = {name: abs(value) / scales[name] for name, value in residuals.items()}
    assert set(normalized) == {"4.1.76", "4.1.80", "4.1.83", "4.1.84", "4.1.87", "4.1.89", "4.1.90"}
    assert max(normalized.values()) <= 1.0e-10
    assert diagnostics["condition_number"] < 10.0


def test_stage42_uses_variable_gas_length_and_separate_lower_inventory():
    params, state = _consistent_stage42_state()
    _derivative, diagnostics = santos_stage_42_derivatives(params, state)
    H = params.geometry.valve_depth_m
    assert diagnostics["gas_length"] == pytest.approx(H - state[0])
    assert diagnostics["gas_mass"] == pytest.approx(state[3] * diagnostics["Ab"] * (H - state[0]))
    assert diagnostics["lower_liquid_volume"] == pytest.approx(diagnostics["Ab"] * state[0])


@pytest.fixture(scope="module")
def incompatible_e():
    params, *_prefix, de = build_corrected_e_state(max_step_s=0.5)
    return params, de, audit_stage_42_initial_state(params, de)


def test_actual_e_state_is_not_projected_to_hide_eos_conflict(incompatible_e):
    params, de, audit = incompatible_e
    assert audit.liquid_height_m == 0.0
    assert audit.hydrostatic_residual_pa == 0.0
    assert audit.gas_density_from_inventory_kg_m3 == pytest.approx(40.3394280292, rel=1e-9)
    assert audit.gas_density_from_eos_kg_m3 == pytest.approx(23.3773629133, rel=1e-9)
    assert audit.eos_density_relative_residual == pytest.approx(0.7255764980, rel=1e-9)
    assert audit.gas_volume_required_by_eos_m3 > audit.maximum_geometric_gas_volume_m3
    assert not audit.compatible
    with pytest.raises(Stage42InitialStateIncompatibility, match="NOT_SOURCE_CERTIFIED_A_TO_F"):
        simulate_stage_e_to_f(params, stage_d_e=de, rhs_mode="santos_corrected")


def test_milestone15_reference_cannot_enter_fg_or_claim_source_certification(incompatible_e):
    params, de, _audit = incompatible_e
    reference = simulate_stage_e_to_f(
        params, stage_d_e=de, rhs_mode="milestone15_corrected", max_step_s=0.01
    )
    assert reference.event_f_reached
    assert not reference.corrected_certified
    assert reference.source_certification_status == "NOT_SOURCE_CERTIFIED_A_TO_F"
    assert reference.liquid_height_m is None
    with pytest.raises(ValueError, match="corrected, certified terminal F state"):
        simulate_stage_f_to_g(params, stage_e_f=reference)
