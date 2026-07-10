from math import exp, pi

import pytest

from gli.base_case import santos_50_70_80
from gli.events import gas_lift_valve_opened
from gli.initial_conditions import GRAVITY_M_S2, initial_stage_1
from gli.simulation import prepare_initial_cycle
from gli.units import inch_to_m, kgf_cm2_gauge_to_pa_absolute


def test_santos_table_5_5_and_operating_point():
    p = santos_50_70_80()
    assert (p.fluids.api, p.fluids.bsw_percent, p.fluids.gas_relative_density) == (40.0, 50.0, 0.70)
    assert (p.geometry.perforation_depth_m, p.geometry.valve_depth_m) == (1500.0, 1480.0)
    assert p.geometry.casing_outer_diameter_m == pytest.approx(inch_to_m(5.5))
    assert p.geometry.tubing_outer_diameter_m == pytest.approx(inch_to_m(2.375))
    assert p.operating.surface_tubing_pressure_pa == pytest.approx(kgf_cm2_gauge_to_pa_absolute(7.0))
    assert p.operating.injection_pressure_pa == pytest.approx(kgf_cm2_gauge_to_pa_absolute(70.0))
    assert (p.operating.initial_slug_over_static_height, p.operating.pto_over_pvo, p.operating.injected_over_reference_gas_volume) == (0.50, 0.70, 0.80)


def test_declared_geometry_is_consistent():
    g = santos_50_70_80().geometry
    expected = pi * (g.casing_inner_diameter_m**2 - g.tubing_outer_diameter_m**2) / 4.0
    assert g.annulus_cross_area_m2 == pytest.approx(expected)
    assert g.tubing_diameter_m < g.tubing_outer_diameter_m < g.casing_inner_diameter_m
    assert g.initial_slug_length_m == pytest.approx(0.5 * g.static_liquid_height_m)
    assert g.valve_depth_m <= g.perforation_depth_m


def test_initial_conditions_reproduce_santos_equations_5_1_to_5_12():
    p = santos_50_70_80()
    s = initial_stage_1(p)
    g = p.geometry
    gas = p.gas
    assert s['rho_l'] == pytest.approx(947.5364431487)
    assert s['p_to'] == pytest.approx(s['p_t3'] + s['rho_l'] * GRAVITY_M_S2 * g.initial_slug_length_m)
    assert s['p_vo'] == pytest.approx(s['p_to'] / 0.70)
    assert s['p_bt'] == pytest.approx(s['p_vo'] * (1.0 - p.valves.rv) + s['p_to'] * p.valves.rv)
    assert s['p_c2'] == pytest.approx(s['p_bt'])
    exponent = gas.gas_molar_mass_kg_mol * GRAVITY_M_S2 * g.valve_depth_m / (gas.z_tc * gas.gas_constant_j_mol_k * gas.temp_c1_k)
    assert s['p_c1'] == pytest.approx(s['p_c2'] / exp(exponent))
    assert s['p_c1'] < s['p_c2'] < s['p_vo']
    assert s['rho_c1'] < s['rho_c2'] and s['m_tc'] > 0.0


def test_stage_gate_stays_closed_at_initialization():
    prepared = prepare_initial_cycle(santos_50_70_80())
    assert prepared['stage_1_control']['resultant_force'] < 0.0
    assert not prepared['stage_1_valve_open']
    assert 'stage_2' not in prepared
    assert not gas_lift_valve_opened(-1.0)
    assert gas_lift_valve_opened(0.0)
    assert gas_lift_valve_opened(1.0)
