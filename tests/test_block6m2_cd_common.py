import numpy as np
import pytest
from gli.base_case import santos_50_70_80
from gli.stage1_dynamic import simulate_stage_1
from gli.stage_bc_common import simulate_stage_b_to_c_common
from gli.stage_cd_common import *

@pytest.fixture(scope='module')
def chain():
 p=santos_50_70_80();a=simulate_stage_1(p,max_step_s=.5);b=simulate_stage_b_to_c_common(p,stage_a_b=a,max_step_s=.5);c=simulate_stage_c_to_d_common(p,stage_b_c_common=b,max_step_s=.5);return p,b,c

def test_exact_c_continuity_and_motor_control(chain):
 _,b,c=chain;assert np.allclose(c.states[:,0],b.final_state,rtol=0,atol=1e-10);assert c.continuity_error<1e-10

def test_glv_control_has_internal_closure_latch_and_no_reopening(chain):
 _,_,c=chain
 if c.closure_reached:
  idx=np.flatnonzero(~c.glv_open)[0];assert not c.glv_open[idx:].any();assert np.all(c.glv_mass_rate_kg_s[idx:]==0)
 else:
  # Santos {50,70,80}: the mechanical opening force remains positive at D.
  assert c.glv_open.all() and np.min(c.glv_force_n)>0

def test_balances_ranges_and_order(chain):
 p,_,c=chain;assert c.gas_balance_relative_error<1e-6 and c.liquid_balance_relative_error<1e-6 and c.eos_relative_error<1e-5
 assert np.all(c.states[I_RHO]>0) and np.all(c.states[I_PG]>0);assert np.all(c.states[I_HB]<c.states[I_HL]+1e-9);assert np.max(abs(c.states[I_VF]))<10

def test_event_d_and_rigidity(chain):
 p,_,c=chain;assert c.event_d_reached and c.states[I_HL,-1]==pytest.approx(p.geometry.valve_depth_m,rel=1e-8);assert c.stiffness_ratio>1e3

def test_convergence(chain):
 p,b,c=chain;fine=simulate_stage_c_to_d_common(p,stage_b_c_common=b,max_step_s=.25);assert abs(fine.event_d_time_s-c.event_d_time_s)<1e-2
