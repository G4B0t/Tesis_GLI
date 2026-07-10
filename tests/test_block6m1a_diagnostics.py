import pytest
from gli.base_case import santos_50_70_80
from gli.stage1_dynamic import simulate_stage_1
from gli.stage_bc_common import initial_state_b,rhs_bc_common,simulate_stage_b_to_c_common,I_VF,I_Y
from gli.block6m1a_diagnostics import *

@pytest.fixture(scope='module')
def data():
 p=santos_50_70_80();a=simulate_stage_1(p,max_step_s=.5);r=simulate_stage_b_to_c_common(p,stage_a_b=a,max_step_s=.1);return p,a,r

def test_b_condition_and_minimum_film_geometry(data):
 p,a,_=data;s=initial_state_b(p,a);af,dh=film_geometry(p.geometry.tubing_diameter_m,s[I_Y]);assert s[I_VF]==0 and af>0 and dh>0 and s[I_Y]>0

def test_instantaneous_inventory_is_algebraically_decomposed(data):
 p,a,_=data;s=initial_state_b(p,a);d=rhs_bc_common(0,s,p);x=instantaneous_liquid_residual(s,d,p)
 assert x['inventory_rate_m3_s']==pytest.approx(x['moving_slug_boundary_m3_s']+x['film_geometry_m3_s']+x['fallback_ledger_m3_s']+x['produced_m3_s'])
 assert x['residual_m3_s']==pytest.approx(x['inventory_rate_m3_s']-x['reservoir_rate_m3_s'])

def test_momentum_terms_have_acceleration_scale_and_darcy_convention(data):
 p,a,_=data;s=initial_state_b(p,a);x=decompose_film_momentum(s,p)
 assert x.total_m_s2==pytest.approx(x.gravity_m_s2+x.pressure_gradient_m_s2+x.wall_shear_m_s2+x.interfacial_shear_m_s2+x.inertia_m_s2+x.area_m_s2)
 assert x.hydraulic_diameter_m>0 and x.darcy_factor>0

def test_short_time_evolution_exposes_problem_without_masking(data):
 p,a,r=data;assert diagnose_result(r,p)['first_out_of_range'] is None
