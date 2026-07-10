import numpy as np
import pytest
from gli.base_case import santos_50_70_80
from gli.stage1_dynamic import simulate_stage_1
from gli.stage_bc_common import *
from gli.block6m1a_diagnostics import decompose_film_momentum,instantaneous_liquid_residual

@pytest.fixture(scope='module')
def data():
 p=santos_50_70_80();a=simulate_stage_1(p,max_step_s=.5);r=simulate_stage_b_to_c_common(p,stage_a_b=a,max_step_s=.1);return p,a,r

def test_wall_shear_opposes_both_directions(data):
 p,a,_=data;s=initial_state_b(p,a)
 for v,expected in [(1.,-1),(-1.,1)]:
  s[I_VF]=v;x=decompose_film_momentum(s,p);assert np.sign(x.wall_shear_m_s2)==expected

def test_all_momentum_terms_sum_to_rhs(data):
 p,a,_=data;s=initial_state_b(p,a);s[I_VF]=.2;d=rhs_bc_common(0,s,p);x=decompose_film_momentum(s,p)
 assert d[I_VF]==pytest.approx(x.total_m_s2,rel=1e-10,abs=1e-10)

def test_differential_liquid_conservation_and_ledger(data):
 p,a,_=data;s=initial_state_b(p,a);s[I_VF]=-1.;d=rhs_bc_common(0,s,p);x=instantaneous_liquid_residual(s,d,p)
 assert x['residual_m3_s']==pytest.approx(0,abs=1e-12)
 assert x['fallback_ledger_m3_s']>0

def test_short_time_physical_and_event_c(data):
 _,_,r=data;assert r.event_c_reached;assert np.all(r.states[I_RHO]>0) and np.all(r.states[I_PG]>0)
 assert np.max(np.abs(r.states[I_VF]))<10

def test_corrected_candidate_gates(data):
 _,_,r=data;assert r.gas_balance_relative_error<1e-6 and r.liquid_balance_relative_error<1e-6 and r.eos_relative_error<1e-5;assert r.certified

def test_convergence(data):
 p,a,r=data;coarse=simulate_stage_b_to_c_common(p,stage_a_b=a,max_step_s=.2);assert abs(coarse.event_c_time_s-r.event_c_time_s)<1e-3
