from dataclasses import replace
import numpy as np
import pytest
from gli.base_case import santos_50_70_80
from gli.stage_cd_dynamic import simulate_stage_c_to_d
from gli.stage_de_dynamic import simulate_stage_d_to_e
from gli.geometry import tubing_area

@pytest.fixture(scope="module")
def chain():
    p=santos_50_70_80(); cd=simulate_stage_c_to_d(p,max_step_s=.5); de=simulate_stage_d_to_e(p,stage_c_d=cd,max_step_s=.5)
    return p,cd,de

def test_exact_continuity_and_boundary_switch_at_d(chain):
    p,cd,de=chain
    for a,b in [(cd.annulus_mass_kg[-1],de.annulus_mass_kg[0]),(cd.bubble_mass_kg[-1],de.bubble_mass_kg[0]),(cd.h_b_m[-1],de.h_b_m[0]),(cd.h_l_m[-1],de.h_l_m[0]),(cd.v_b_m_s[-1],de.v_b_m_s[0]),(cd.p_tubing_pa[-1],de.p_tubing_pa[0])]: assert b==pytest.approx(a,rel=1e-10)
    assert np.all(de.h_l_m==p.geometry.valve_depth_m)

def test_event_e_and_order(chain):
    p,cd,de=chain
    assert de.event_e_reached and de.h_b_m[-1]==pytest.approx(p.geometry.valve_depth_m,rel=1e-10)
    assert cd.h_b_m[-1]<cd.h_l_m[-1] and de.event_e_time_s>0

def test_independent_gas_and_liquid_inventories(chain):
    p,_,r=chain
    total=r.slug_volume_m3+r.film_volume_m3+r.fallback_volume_m3+r.produced_volume_m3
    expected=tubing_area(p.geometry.tubing_diameter_m)*p.geometry.initial_slug_length_m
    assert np.allclose(total,expected,rtol=1e-11) and r.liquid_balance_relative_error<1e-11
    assert r.gas_balance_relative_error<1e-12

def test_monotonicity_and_physical_valve_state(chain):
    _,_,r=chain
    assert np.all(np.diff(r.h_b_m)>=0) and np.all(np.diff(r.produced_volume_m3)>=0)
    assert np.all(np.diff(r.slug_volume_m3)<=1e-12) and np.all(r.liquid_rate_m3_s>=0)
    assert not r.valve_open[0] and not r.valve_open[-1]

def test_convergence(chain):
    p,cd,_=chain
    a=simulate_stage_d_to_e(p,stage_c_d=cd,max_step_s=1); b=simulate_stage_d_to_e(p,stage_c_d=cd,max_step_s=.2)
    assert abs(a.event_e_time_s-b.event_e_time_s)<1e-4
    assert abs(a.produced_volume_m3[-1]-b.produced_volume_m3[-1])<1e-6

def test_friction_sensitivity(chain):
    p,cd,base=chain
    low=replace(p,coefficients=replace(p.coefficients,liquid_friction_factor=.018)); high=replace(p,coefficients=replace(p.coefficients,liquid_friction_factor=.022))
    fast=simulate_stage_d_to_e(low,stage_c_d=cd,max_step_s=.5); slow=simulate_stage_d_to_e(high,stage_c_d=cd,max_step_s=.5)
    assert fast.event_e_time_s<base.event_e_time_s<slow.event_e_time_s

def test_liao_santos_validation_is_reported_without_calibration(chain):
    p,_,r=chain
    recovery=r.produced_volume_m3[-1]/(tubing_area(p.geometry.tubing_diameter_m)*p.geometry.initial_slug_length_m)
    assert .5<recovery<.9 and 20<r.event_e_time_s<60
