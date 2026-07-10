import numpy as np
import pytest
from gli.base_case import santos_50_70_80
from gli.stage1_dynamic import simulate_stage_1
from gli.stage_bc_common import simulate_stage_b_to_c_common,I_HB,I_HL,I_VG,I_VL,I_VF,I_Y
from gli.stage_cd_common import _cd_terms_santos,simulate_stage_c_to_d_common
from gli.geometry import tubing_area

@pytest.fixture(scope='module')
def chain():
 p=santos_50_70_80();a=simulate_stage_1(p,max_step_s=.5);b=simulate_stage_b_to_c_common(p,stage_a_b=a,max_step_s=.5);old=simulate_stage_c_to_d_common(p,stage_b_c_common=b,max_step_s=.5);new=simulate_stage_c_to_d_common(p,stage_b_c_common=b,max_step_s=.5,rhs_mode='santos_corrected');return p,a,b,old,new

def test_corrected_rhs_separates_kinematics_and_reservoir_feed(chain):
 p,_,b,_,_=chain;d=_cd_terms_santos(b.final_state,p,True)[0];assert d[I_HL]==pytest.approx(b.final_state[I_VL]);assert d[I_HB]==pytest.approx(b.final_state[I_VG])

def test_santos_film_mass_equation_4135_closes_instantaneously(chain):
 p,_,b,_,_=chain;s=b.final_state;d=_cd_terms_santos(s,p,True)[0];r=p.geometry.tubing_diameter_m/2;At=tubing_area(2*r);Ab=np.pi*(r-s[I_Y])**2;Af=At-Ab
 residual=2*np.pi*(r-s[I_Y])*s[I_HB]*d[I_Y]+Af*s[I_VF]-p.operating.reservoir_liquid_rate_m3_s;assert abs(residual)<1e-12

def test_candidate_improves_event_and_velocity_but_fails_global_gate(chain):
 p,a,b,old,new=chain;assert new.event_d_time_s<old.event_d_time_s;assert not new.certified;assert new.liquid_balance_relative_error>1e-2

def test_no_silent_switch_to_candidate_in_api_default(chain):
 _,_,_,old,_=chain;assert old.certified and old.event_d_time_s==pytest.approx(490.0673025,rel=2e-7)
