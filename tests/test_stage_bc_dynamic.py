import numpy as np
import pytest

from gli.base_case import santos_50_70_80
from gli.initial_conditions import initial_stage_1
from gli.reference_gas import injected_gas_target_std_m3, liao_reference_gas_volume_std_m3
from gli.stage1_dynamic import simulate_stage_1
from gli.stage_bc_dynamic import simulate_stage_b_to_c


@pytest.fixture(scope="module")
def params(): return santos_50_70_80()


@pytest.fixture(scope="module")
def ab(params): return simulate_stage_1(params,max_step_s=0.5)


@pytest.fixture(scope="module")
def bc(params,ab): return simulate_stage_b_to_c(params,stage_a_b=ab,max_step_s=0.2)


def test_liao_reference_volume_and_80_percent_target(params):
    vgref=liao_reference_gas_volume_std_m3(params)
    vgi=injected_gas_target_std_m3(params)
    assert vgref == pytest.approx(162.2962359343)
    assert vgi == pytest.approx(0.8*vgref)


def test_state_is_continuous_at_b(params,ab,bc):
    assert bc.p_c1_pa[0] == pytest.approx(ab.p_c1_pa[-1],rel=2e-7)
    assert bc.p_c2_pa[0] == pytest.approx(ab.p_c2_pa[-1],rel=2e-7)
    assert bc.annulus_mass_kg[0]+bc.bubble_mass_kg[0] == pytest.approx(ab.annulus_gas_mass_kg[-1],rel=1e-12)
    assert bc.p_bubble_pa[0] == pytest.approx(initial_stage_1(params)["p_to"],rel=1e-10)


def test_event_c_closes_motor_at_target_volume(bc):
    assert bc.event_c_reached
    assert bc.injected_volume_std_m3[-1] == pytest.approx(bc.target_volume_std_m3,rel=1e-9)
    assert bc.injected_volume_std_m3[-1] > bc.injected_volume_std_m3[0]


def test_gas_and_liquid_balances_close(bc):
    assert bc.gas_balance_relative_error < 1e-8
    assert bc.liquid_balance_relative_error < 1e-12


def test_stage_bc_is_physically_feasible_and_stops_before_d(params,bc):
    assert np.all(bc.annulus_mass_kg>0) and np.all(bc.bubble_mass_kg>0)
    assert np.all(bc.p_c1_pa>0) and np.all(bc.p_c2_pa>=bc.p_bubble_pa)
    assert np.all(bc.gl_mass_rate_kg_s>=0) and np.all(bc.motor_rate_std_m3_s>0)
    assert np.all(bc.h_b_m<bc.h_l_m)
    assert bc.h_l_m[-1] < params.geometry.valve_depth_m
    assert np.all(bc.slug_velocity_m_s>=0)
    assert np.all(bc.film_thickness_m>0)
    assert np.all(bc.film_thickness_m<0.5*params.geometry.tubing_diameter_m)


def test_event_c_time_converges(params,ab):
    coarse=simulate_stage_b_to_c(params,stage_a_b=ab,max_step_s=0.5)
    medium=simulate_stage_b_to_c(params,stage_a_b=ab,max_step_s=0.2)
    fine=simulate_stage_b_to_c(params,stage_a_b=ab,max_step_s=0.1)
    assert abs(coarse.event_c_time_s-fine.event_c_time_s)<1e-6
    assert abs(medium.event_c_time_s-fine.event_c_time_s)<1e-7
