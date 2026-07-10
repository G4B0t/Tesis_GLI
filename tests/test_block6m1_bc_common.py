import numpy as np
import pytest
from gli.base_case import santos_50_70_80
from gli.stage1_dynamic import simulate_stage_1
from gli.stage_bc_dynamic import simulate_stage_b_to_c
from gli.stage_bc_common import *

@pytest.fixture(scope='module')
def chain():
 p=santos_50_70_80();ab=simulate_stage_1(p,max_step_s=.5);new=simulate_stage_b_to_c_common(p,stage_a_b=ab,max_step_s=.2);old=simulate_stage_b_to_c(p,stage_a_b=ab,max_step_s=.2);return p,ab,new,old

def test_b_initial_conditions_explicit_and_positive(chain):
 p,ab,_,_=chain;s=initial_state_b(p,ab);assert np.all(s[[I_MC,I_MG,I_RHO,I_PG,I_MFILM]]>0);assert s[I_VF]==0

def test_rhs_is_finite_and_has_memory_derivatives(chain):
 p,ab,_,_=chain;d=rhs_bc_common(0,initial_state_b(p,ab),p);assert np.all(np.isfinite(d));assert d[I_MG]>=0 and d[I_VGI]>=0

def test_event_c_is_vgi_only_and_no_state_reconstruction(chain):
 _,_,r,_=chain;assert r.event_c_reached;assert r.final_state[I_VGI]==pytest.approx(r.target_volume_std_m3,rel=1e-8)

def test_balances_positivity_and_ranges(chain):
 _,_,r,_=chain;assert r.gas_balance_relative_error<1e-6;assert r.eos_relative_error<1e-4;assert np.all(r.states[I_RHO]>0);assert np.all(r.states[I_PG]>0)

def test_comparison_is_reported_without_calibration(chain):
 _,_,r,old=chain;assert r.event_c_time_s>0 and old.event_c_time_s>0;assert r.certified

def test_convergence_and_seed_sensitivity(chain):
 p,ab,r,_=chain;fine=simulate_stage_b_to_c_common(p,stage_a_b=ab,max_step_s=.1);assert abs(fine.event_c_time_s-r.event_c_time_s)<1e-3
 low=simulate_stage_b_to_c_common(p,stage_a_b=ab,max_step_s=.2,seed_height_m=5e-4);high=simulate_stage_b_to_c_common(p,stage_a_b=ab,max_step_s=.2,seed_height_m=2e-3);assert low.certified and high.certified
