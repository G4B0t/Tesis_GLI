import pytest
from gli.base_case import santos_50_70_80
from gli.stage1_dynamic import simulate_stage_1
from gli.stage_bc_common import simulate_stage_b_to_c_common
from gli.stage_cd_common import simulate_stage_c_to_d_common
from gli.audit_block6m2v import event_table,trajectory_rmse,valve_case_audit

@pytest.fixture(scope='module')
def chain():
 p=santos_50_70_80();a=simulate_stage_1(p,max_step_s=.5);b=simulate_stage_b_to_c_common(p,stage_a_b=a,max_step_s=.5);c=simulate_stage_c_to_d_common(p,stage_b_c_common=b,max_step_s=.5);return p,a,b,c

def test_figure_time_is_absolute_and_event_error_is_not_origin_shift(chain):
 rows=event_table(*chain[1:]);assert rows[-1].absolute_s==pytest.approx(549.5014847,rel=2e-7);assert rows[-1].error_s>250;assert rows[-1].duration_s==pytest.approx(490.0673025,rel=2e-7)

def test_quantitative_rmse_exposes_velocity_and_position_discrepancy(chain):
 r=trajectory_rmse(*chain);assert r['pc1']>3 and r['h_l']>300 and r['v_l']>2

def test_santos_valve_parameters_are_not_misclassified_as_measured(chain):
 a=valve_case_audit(chain[0]);assert not a['quantitatively_validated'];assert 'proxy' in a['bellows_area_status']

def test_explicit_friction_sensitivity_preserves_conservation(chain):
 p,_,b,_=chain;c=simulate_stage_c_to_d_common(p,stage_b_c_common=b,max_step_s=2,friction_scale=.8);assert c.certified and c.gas_balance_relative_error<1e-6 and c.liquid_balance_relative_error<1e-6
