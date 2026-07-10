from dataclasses import replace
import numpy as np
import pytest
from gli.base_case import santos_50_70_80
from gli.stage1_dynamic import simulate_stage_1
from gli.stage_bc_dynamic import simulate_stage_b_to_c
from gli.stage_cd_dynamic import simulate_stage_c_to_d
from gli.validation_stage_cd import compare_event_d

@pytest.fixture(scope='module')
def chain():
    p=santos_50_70_80(); ab=simulate_stage_1(p,max_step_s=.5); bc=simulate_stage_b_to_c(p,stage_a_b=ab,max_step_s=.5); cd=simulate_stage_c_to_d(p,stage_b_c=bc,max_step_s=.5)
    return p,ab,bc,cd

def test_exact_continuity_at_c_without_reinitialization(chain):
    _,_,bc,cd=chain
    for a,b in [(bc.annulus_mass_kg[-1],cd.annulus_mass_kg[0]),(bc.bubble_mass_kg[-1],cd.bubble_mass_kg[0]),(bc.h_b_m[-1],cd.h_b_m[0]),(bc.h_l_m[-1],cd.h_l_m[0]),(bc.slug_velocity_m_s[-1],cd.v_l_m_s[0]),(bc.p_c1_pa[-1],cd.p_c1_pa[0]),(bc.p_bubble_pa[-1],cd.p_tubing_pa[0])]:
        assert b==pytest.approx(a,rel=1e-12,abs=1e-12)

def test_event_d_and_order_are_correct(chain):
    p,ab,bc,cd=chain
    assert cd.event_d_reached and cd.h_l_m[-1]==pytest.approx(p.geometry.valve_depth_m,rel=1e-10)
    assert 0<ab.opening_time_s<ab.opening_time_s+bc.event_c_time_s<ab.opening_time_s+bc.event_c_time_s+cd.event_d_time_s
    assert cd.h_b_m[-1]<cd.h_l_m[-1]

def test_independent_gas_and_liquid_invariants(chain):
    _,_,_,cd=chain
    assert cd.gas_balance_relative_error<1e-12
    assert cd.liquid_balance_relative_error<1e-12
    assert np.allclose(cd.annulus_mass_kg+cd.bubble_mass_kg,(cd.annulus_mass_kg+cd.bubble_mass_kg)[0],rtol=1e-12)
    assert np.all(np.diff(cd.fallback_volume_m3)>=-1e-10)

def test_physical_feasibility_and_valve_operation(chain):
    p,_,_,cd=chain
    assert np.all(cd.annulus_mass_kg>0) and np.all(cd.bubble_mass_kg>0)
    assert np.all(cd.p_c2_pa>=cd.p_tubing_pa) and np.all(cd.p_bottom_pa>=cd.p_tubing_pa)
    assert np.all(cd.v_l_m_s>0) and np.all(cd.v_b_m_s>=cd.v_l_m_s)
    assert np.all(cd.film_thickness_m>0) and np.all(cd.film_thickness_m<.5*p.geometry.tubing_diameter_m)
    assert cd.valve_open[0] and not cd.valve_open[-1]
    assert np.all(cd.gl_mass_rate_kg_s>=0)
    assert np.all(cd.gl_mass_rate_kg_s[~cd.valve_open]==0)

def test_event_d_time_converges(chain):
    p,_,bc,_=chain
    coarse=simulate_stage_c_to_d(p,stage_b_c=bc,max_step_s=1.0); medium=simulate_stage_c_to_d(p,stage_b_c=bc,max_step_s=.5); fine=simulate_stage_c_to_d(p,stage_b_c=bc,max_step_s=.2)
    assert abs(coarse.event_d_time_s-fine.event_d_time_s)<5e-5
    assert abs(medium.event_d_time_s-fine.event_d_time_s)<3e-6

def test_friction_sensitivity_is_physical(chain):
    p,_,bc,base=chain
    low=replace(p,coefficients=replace(p.coefficients,liquid_friction_factor=.018)); high=replace(p,coefficients=replace(p.coefficients,liquid_friction_factor=.022))
    fast=simulate_stage_c_to_d(low,stage_b_c=bc,max_step_s=1.0); slow=simulate_stage_c_to_d(high,stage_b_c=bc,max_step_s=1.0)
    assert fast.event_d_time_s<base.event_d_time_s<slow.event_d_time_s
    assert slow.event_d_time_s/fast.event_d_time_s<1.25

def test_santos_figures_5_1_to_5_4_validation_band(chain):
    _,ab,bc,cd=chain; c=compare_event_d(ab,bc,cd)
    assert abs(c.absolute_time_s-c.reference_time_s)/c.reference_time_s<.25
    assert abs(c.pc1_kgf_cm2-c.reference_pc1_kgf_cm2)<2.0
    assert abs(c.pwf_kgf_cm2-c.reference_pwf_kgf_cm2)<5.0
    assert abs(c.h_b_m-c.reference_h_b_m)/c.reference_h_b_m<.15
    assert abs(c.v_l_m_s-c.reference_v_l_m_s)/c.reference_v_l_m_s<.40
    assert abs(c.v_b_m_s-c.reference_v_b_m_s)/c.reference_v_b_m_s<.40
